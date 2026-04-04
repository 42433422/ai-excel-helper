# -*- coding: utf-8 -*-
"""
标签模板生成技能 — 实现已迁移至 app.services.skills.label_template_generator（单一源码）。

此处仅做重导出，供 app.infrastructure.skills 与 routes/skills 等历史导入路径使用。
"""

from app.services.skills.label_template_generator.label_template_generator import (  # noqa: F401
    LabelTemplateGeneratorSkill,
    analyze_image,
    extract_text_with_ocr,
    generate_template_code,
    get_label_template_generator_skill,
)

__all__ = [
    "LabelTemplateGeneratorSkill",
    "analyze_image",
    "extract_text_with_ocr",
    "generate_template_code",
    "get_label_template_generator_skill",
]
