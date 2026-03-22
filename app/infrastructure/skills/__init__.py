# -*- coding: utf-8 -*-
"""
Skills 注册与管理服务

提供技能的注册、发现和调用接口
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SkillRegistry:
    """技能注册表"""

    def __init__(self):
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    def register(self, skill_id: str, skill_info: Dict[str, Any]) -> None:
        """
        注册一个技能

        Args:
            skill_id: 技能唯一标识
            skill_info: 技能信息字典，包含:
                - name: 技能名称
                - description: 技能描述
                - module: 技能模块路径
                - class_name: 技能类名
                - keywords: 触发关键词列表
                - parameters: 参数定义
        """
        self._skills[skill_id] = skill_info
        logger.info(f"技能注册成功: {skill_id} - {skill_info.get('name', '')}")

    def get(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取技能信息"""
        return self._skills.get(skill_id)

    def list_all(self) -> List[Dict[str, Any]]:
        """列出所有已注册的技能"""
        return [
            {
                "id": skill_id,
                "name": info.get("name", ""),
                "description": info.get("description", ""),
                "keywords": info.get("keywords", []),
                "category": info.get("category", "general")
            }
            for skill_id, info in self._skills.items()
        ]

    def find_by_keyword(self, keyword: str) -> List[str]:
        """根据关键词查找技能"""
        matched = []
        for skill_id, info in self._skills.items():
            keywords = info.get("keywords", [])
            if any(keyword.lower() in kw.lower() for kw in keywords):
                matched.append(skill_id)
        return matched

    def initialize(self) -> None:
        """初始化技能注册表"""
        if self._initialized:
            return

        skills_dir = Path(__file__).parent
        if not skills_dir.exists():
            logger.warning(f"Skills目录不存在: {skills_dir}")
            self._initialized = True
            return

        for skill_folder in skills_dir.iterdir():
            if not skill_folder.is_dir():
                continue

            skill_id = skill_folder.name
            skill_md = skill_folder / "SKILL.md"

            if not skill_md.exists():
                continue

            try:
                with open(skill_md, 'r', encoding='utf-8') as f:
                    content = f.read()

                metadata = self._parse_skill_md(content)
                if metadata:
                    metadata["module_path"] = str(skill_folder)
                    self.register(skill_id, metadata)
                    logger.info(f"加载技能定义: {skill_id}")
            except Exception as e:
                logger.error(f"加载技能失败 {skill_id}: {e}")

        self._initialized = True

    def _parse_skill_md(self, content: str) -> Optional[Dict[str, Any]]:
        """解析SKILL.md文件，提取元数据"""
        lines = content.strip().split('\n')
        metadata = {
            "keywords": [],
            "category": "general"
        }

        if not lines or not lines[0].startswith('---'):
            return None

        in_frontmatter = True
        frontmatter_lines = []

        for line in lines[1:]:
            if in_frontmatter:
                if line.strip() == '---':
                    in_frontmatter = False
                    continue
                frontmatter_lines.append(line)
            else:
                break

        for line in frontmatter_lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip().strip('"').strip("'")

                if key == 'name':
                    metadata['name'] = value
                elif key == 'description':
                    metadata['description'] = value

        description_section = '\n'.join(lines[len(frontmatter_lines) + 2:])
        if 'When to Use This Skill' in description_section:
            section = description_section.split('When to Use This Skill')[1].split('#')[0]
            triggers = []
            for line in section.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    triggers.append(line[2:].strip())
                elif line.startswith('* '):
                    triggers.append(line[2:].strip())
            metadata['keywords'] = triggers

        return metadata if metadata.get('name') else None


_skill_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """获取技能注册表单例"""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
        _skill_registry.initialize()
    return _skill_registry


def execute_skill(skill_id: str, **params) -> Dict[str, Any]:
    """
    执行指定技能

    Args:
        skill_id: 技能标识
        **params: 技能参数

    Returns:
        技能执行结果
    """
    registry = get_skill_registry()
    skill_info = registry.get(skill_id)

    if not skill_info:
        return {
            "success": False,
            "error": f"未找到技能: {skill_id}"
        }

    module_path = skill_info.get("module_path", "")
    module_name = skill_id.replace('-', '_')

    try:
        if module_name == "excel_analyzer":
            from .excel_analyzer.excel_template_analyzer import get_excel_analyzer_skill
            skill = get_excel_analyzer_skill()
            return skill.execute(**params)
        elif module_name == "excel_toolkit":
            from .excel_toolkit.excel_toolkit import get_excel_toolkit_skill
            skill = get_excel_toolkit_skill()
            return skill.execute(**params)
        elif module_name == "label_template_generator":
            from .label_template_generator.label_template_generator import (
                get_label_template_generator_skill,
            )
            skill = get_label_template_generator_skill()
            return skill.execute(**params)
        else:
            return {
                "success": False,
                "error": f"未知技能类型：{skill_id}"
            }
    except Exception as e:
        logger.error(f"执行技能失败 {skill_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }