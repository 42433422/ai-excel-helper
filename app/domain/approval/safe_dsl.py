"""
Safe DSL for Approval Conditions

This module provides a secure way to evaluate condition expressions for approval
workflows without using dangerous eval() or exec(). It uses Python's ast module
with a strict whitelist of allowed operations to prevent code injection attacks.

Supported syntax examples:
- amount > 50000
- quantity > 100 AND unit_price > 10.0
- priority = 'high' OR amount > 10000
- (amount > 5000 AND department = 'sales')

DO NOT use this for complex business logic that requires external function calls.
"""

import ast
import logging
import operator
from typing import Any

logger = logging.getLogger(__name__)


class SafeEvaluationError(Exception):
    """Raised when an unsafe expression is detected."""

    pass


# Whitelisted AST node types
ALLOWED_NODES = {
    ast.Expression,
    ast.BoolOp,
    ast.BinOp,
    ast.UnaryOp,
    ast.Compare,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.Num,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Str,  # For older Python compatibility
}

# Whitelisted operators
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.Not: operator.not_,
}

# Whitelisted variable names that can be used in conditions
ALLOWED_VARIABLES = {
    "amount",
    "quantity",
    "unit_price",
    "total_price",
    "priority",
    "department",
    "user_role",
    "customer_type",
    "order_value",
    "risk_level",
    "approval_count",
    "True",
    "False",
    "None",
    "true",
    "false",
    "null",
}


class SafeExpressionEvaluator:
    """
    Secure evaluator for approval condition expressions.

    Uses AST parsing with strict validation to ensure only safe operations
    are performed. Prevents arbitrary code execution.
    """

    def __init__(self, context: dict[str, Any]):
        self.context = context or {}
        self.logger = logging.getLogger(__name__)

    def evaluate(self, expression: str) -> bool:
        """
        Safely evaluate a condition expression against the provided context.

        Args:
            expression: String expression like "amount > 50000 AND priority = 'high'"

        Returns:
            Boolean result of the condition

        Raises:
            SafeEvaluationError: If expression is invalid or unsafe
        """
        if not expression or not isinstance(expression, str):
            return True  # Empty condition always passes

        expression = expression.strip()
        if not expression:
            return True

        try:
            # Parse the expression to AST
            tree = ast.parse(expression, mode="eval")

            # Validate the AST for safety
            self._validate_ast(tree)

            # Evaluate the AST safely
            result = self._eval_node(tree.body)
            self.logger.debug(f"Evaluated condition '{expression}' -> {result}")
            return bool(result)

        except SafeEvaluationError as e:
            self.logger.warning(f"Unsafe condition expression: {expression} - {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to evaluate condition '{expression}': {e}")
            raise SafeEvaluationError(f"Invalid condition expression: {expression}") from e

    def _validate_ast(self, node: ast.AST) -> None:
        """Recursively validate that all AST nodes are in the allowed set."""
        if type(node) not in ALLOWED_NODES:
            raise SafeEvaluationError(f"Disallowed AST node type: {type(node).__name__}")

        for child in ast.iter_child_nodes(node):
            self._validate_ast(child)

        # Additional validation for Name nodes (variables)
        if isinstance(node, ast.Name):
            if node.id not in ALLOWED_VARIABLES and node.id not in self.context:
                raise SafeEvaluationError(
                    f"Disallowed variable: {node.id}. " f"Allowed: {ALLOWED_VARIABLES}"
                )

    def _eval_node(self, node: ast.AST) -> Any:
        """Safely evaluate an AST node."""
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # Legacy
            return node.n
        elif isinstance(node, ast.Str):  # Legacy
            return node.s
        elif isinstance(node, ast.Name):
            if node.id in self.context:
                return self.context[node.id]
            elif node.id in ("True", "true"):
                return True
            elif node.id in ("False", "false"):
                return False
            elif node.id in ("None", "null"):
                return None
            else:
                raise SafeEvaluationError(f"Unknown variable: {node.id}")

        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_type = type(node.op)
            if op_type in OPERATORS:
                try:
                    return OPERATORS[op_type](left, right)
                except (TypeError, ZeroDivisionError) as e:
                    raise SafeEvaluationError(f"Operation error: {e}") from e
            raise SafeEvaluationError(f"Unsupported binary operator: {op_type}")

        elif isinstance(node, ast.Compare):
            # Handle comparisons like a > b, a == b, etc.
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator)
                op_type = type(op)
                if op_type in OPERATORS:
                    if not OPERATORS[op_type](left, right):
                        return False
                else:
                    raise SafeEvaluationError(f"Unsupported comparison operator: {op_type}")
                left = right  # For chained comparisons
            return True

        elif isinstance(node, ast.BoolOp):
            values = [self._eval_node(value) for value in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            elif isinstance(node.op, ast.Or):
                return any(values)
            raise SafeEvaluationError(f"Unsupported boolean operator: {type(node.op)}")

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_type = type(node.op)
            if op_type in OPERATORS:
                return OPERATORS[op_type](operand)
            raise SafeEvaluationError(f"Unsupported unary operator: {op_type}")

        raise SafeEvaluationError(f"Unsupported AST node: {type(node).__name__}")


def evaluate_condition(expression: str, context: dict[str, Any]) -> bool:
    """
    Convenience function to evaluate a condition.

    This is the main entry point for approval condition evaluation.
    """
    evaluator = SafeExpressionEvaluator(context)
    return evaluator.evaluate(expression)


# Update ApprovalFlowNode to use the safe evaluator
def should_trigger_condition(node, context: dict[str, Any]) -> bool:
    """
    Helper method to be added to ApprovalFlowNode.
    Evaluates condition_expression safely.
    """
    if not hasattr(node, "condition_expression") or not node.condition_expression:
        return True

    try:
        return evaluate_condition(node.condition_expression, context)
    except SafeEvaluationError as e:
        logger.warning(
            f"Condition evaluation failed for node {getattr(node, 'id', 'unknown')}: {e}"
        )
        return False  # Fail closed for safety
    except Exception as e:
        logger.error(f"Unexpected error evaluating condition: {e}")
        return False
