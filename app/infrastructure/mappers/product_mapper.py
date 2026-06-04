from typing import Any

from app.db.models import Product as ProductModel
from app.domain.product.entities import Product
from app.domain.value_objects import ModelNumber, Money


def product_to_domain(db_model: ProductModel) -> Product:
    return Product(
        id=db_model.id,
        model_number=ModelNumber(db_model.model_number) if db_model.model_number else None,
        name=db_model.name or "",
        specification=db_model.specification or "",
        price=Money(db_model.price or 0),
        quantity=db_model.quantity or 0,
        description=db_model.description or "",
        category=db_model.category or "",
        brand=db_model.brand or "",
        unit=db_model.unit or "个",
        is_active=bool(db_model.is_active),
        created_at=db_model.created_at,
        updated_at=db_model.updated_at,
    )


def product_to_db(product: Product) -> dict[str, Any]:
    return {
        "name": product.name,
        "model_number": str(product.model_number) if product.model_number else None,
        "specification": product.specification,
        "price": product.price.amount,
        "quantity": product.quantity,
        "description": product.description,
        "category": product.category,
        "brand": product.brand,
        "unit": product.unit,
        "is_active": 1 if product.is_active else 0,
    }
