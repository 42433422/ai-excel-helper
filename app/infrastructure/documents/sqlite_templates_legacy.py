"""SQLite ``templates.db`` ORM 定义（遗留迁移脚本专用，新业务勿依赖）。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

from app.utils.time import utc_now_naive

Base = declarative_base()


class Template(Base):
    __tablename__ = "templates"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)
    file_path = Column(String(512), nullable=False)
    description = Column(Text)
    version = Column(Integer, default=1)
    parent_template_id = Column(String(36))
    status = Column(String(20), default="pending")
    file_size = Column(Integer)
    file_size_human = Column(String(20))
    mime_type = Column(String(100))
    original_filename = Column(String(255))
    thumbnail_path = Column(String(512))
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)
    created_by = Column(String(100))
    metadata_json = Column("metadata", JSON)

    fields = relationship("TemplateField", back_populates="template", cascade="all, delete-orphan")
    versions = relationship(
        "TemplateVersion", back_populates="template", cascade="all, delete-orphan"
    )


class TemplateField(Base):
    __tablename__ = "template_fields"

    id = Column(String(36), primary_key=True)
    template_id = Column(String(36), ForeignKey("templates.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(255), nullable=False)
    field_type = Column(String(50), nullable=False)
    display_name = Column(String(255))
    required = Column(Boolean, default=False)
    default_value = Column(String(512))
    validation_rules = Column(JSON)
    mapping_config = Column(JSON)
    sort_order = Column(Integer, default=0)

    template = relationship("Template", back_populates="fields")

    __table_args__ = ({"sqlite_autoincrement": True},)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "template_id": self.template_id,
            "field_name": self.field_name,
            "field_type": self.field_type,
            "display_name": self.display_name,
            "required": self.required,
            "default_value": self.default_value,
            "validation_rules": self.validation_rules,
            "mapping_config": self.mapping_config,
            "sort_order": self.sort_order,
        }


class TemplateVersion(Base):
    __tablename__ = "template_versions"

    id = Column(String(36), primary_key=True)
    template_id = Column(String(36), ForeignKey("templates.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    change_log = Column(Text)
    file_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=utc_now_naive)
    created_by = Column(String(100))

    template = relationship("Template", back_populates="versions")


def get_db_path() -> Path:
    db_dir = os.environ.get("FHD_DB_DIR", "").strip()
    if db_dir and os.path.isdir(db_dir):
        return Path(db_dir)
    for d in (Path("e:/FHD/424"), Path("e:/FHD/xcagi"), Path.cwd()):
        if d.is_dir():
            return d
    return Path.cwd()
