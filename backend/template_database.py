"""
Template database models and management（SQLite 遗留）。

模板预览运行时数据已迁至 PostgreSQL ``document_templates``（见 ``backend.document_templates_store``）。
本模块保留供 ``scripts/migrate_sqlite_templates_to_pg_document_templates.py`` 等读取 ``templates.db``；
新部署的业务 API 不应再依赖 ``init_db()``。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Template(Base):
    """Template metadata model."""
    
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))
    metadata_json = Column("metadata", JSON)
    
    fields = relationship("TemplateField", back_populates="template", cascade="all, delete-orphan")
    versions = relationship("TemplateVersion", back_populates="template", cascade="all, delete-orphan")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "file_path": self.file_path,
            "description": self.description,
            "version": self.version,
            "parent_template_id": self.parent_template_id,
            "status": self.status,
            "file_size": self.file_size,
            "file_size_human": self.file_size_human,
            "mime_type": self.mime_type,
            "original_filename": self.original_filename,
            "thumbnail_path": self.thumbnail_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "metadata": self.metadata_json,
            "fields": [field.to_dict() for field in self.fields],
        }


class TemplateField(Base):
    """Template field definition model."""
    
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
    
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
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
    """Template version history model."""
    
    __tablename__ = "template_versions"
    
    id = Column(String(36), primary_key=True)
    template_id = Column(String(36), ForeignKey("templates.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    change_log = Column(Text)
    file_path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100))
    
    template = relationship("Template", back_populates="versions")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "version": self.version,
            "change_log": self.change_log,
            "file_path": self.file_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
        }


def get_db_path() -> Path:
    """Get database file path."""
    db_dir = os.environ.get("FHD_DB_DIR", "").strip()
    if db_dir and os.path.isdir(db_dir):
        return Path(db_dir)
    
    fallback_dirs = [Path("e:/FHD/424"), Path("e:/FHD/xcagi"), Path.cwd()]
    for d in fallback_dirs:
        if d.is_dir():
            return d
    
    return Path.cwd()


def get_db_url() -> str:
    """Get database connection URL."""
    db_path = get_db_path() / "templates.db"
    return f"sqlite:///{db_path}"


def init_db() -> None:
    """Initialize database tables."""
    engine = create_engine(get_db_url())
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(engine)


def get_session():
    """Get database session."""
    engine = create_engine(get_db_url())
    Session = sessionmaker(bind=engine)
    return Session()


def create_template(template_data: dict[str, Any]) -> Template:
    """Create a new template record."""
    session = get_session()
    try:
        template = Template(
            id=template_data["id"],
            name=template_data["name"],
            type=template_data["type"],
            file_path=template_data["file_path"],
            description=template_data.get("description"),
            version=template_data.get("version", 1),
            parent_template_id=template_data.get("parent_template_id"),
            status=template_data.get("status", "pending"),
            file_size=template_data.get("file_size"),
            file_size_human=template_data.get("file_size_human"),
            mime_type=template_data.get("mime_type"),
            original_filename=template_data.get("original_filename"),
            thumbnail_path=template_data.get("thumbnail_path"),
            created_by=template_data.get("created_by"),
            metadata_json=template_data.get("metadata"),
        )
        session.add(template)
        session.commit()
        session.refresh(template)
        return template
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def create_template_field(field_data: dict[str, Any]) -> TemplateField:
    """Create a new template field record."""
    session = get_session()
    try:
        field = TemplateField(
            id=field_data["id"],
            template_id=field_data["template_id"],
            field_name=field_data["field_name"],
            field_type=field_data["field_type"],
            display_name=field_data.get("display_name"),
            required=field_data.get("required", False),
            default_value=field_data.get("default_value"),
            validation_rules=field_data.get("validation_rules"),
            mapping_config=field_data.get("mapping_config"),
            sort_order=field_data.get("sort_order", 0),
        )
        session.add(field)
        session.commit()
        session.refresh(field)
        return field
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def create_template_version(version_data: dict[str, Any]) -> TemplateVersion:
    """Create a new template version record."""
    session = get_session()
    try:
        version = TemplateVersion(
            id=version_data["id"],
            template_id=version_data["template_id"],
            version=version_data["version"],
            change_log=version_data.get("change_log"),
            file_path=version_data["file_path"],
            created_by=version_data.get("created_by"),
        )
        session.add(version)
        session.commit()
        session.refresh(version)
        return version
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_template_by_id(template_id: str) -> Template | None:
    """Get template by ID."""
    session = get_session()
    try:
        template = session.query(Template).filter(Template.id == template_id).first()
        if template:
            session.refresh(template, ["fields"])
        return template
    except Exception:
        return None
    finally:
        session.close()


def list_templates(
    template_type: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Template]:
    """List templates with filters."""
    session = get_session()
    try:
        query = session.query(Template)
        
        if template_type:
            query = query.filter(Template.type == template_type)
        if status:
            query = query.filter(Template.status == status)
        
        query = query.order_by(Template.created_at.desc())
        query = query.offset(offset).limit(limit)
        
        templates = query.all()
        for template in templates:
            session.refresh(template, ["fields"])
        
        return templates
    except Exception:
        return []
    finally:
        session.close()


def update_template(template_id: str, update_data: dict[str, Any]) -> Template | None:
    """Update template."""
    session = get_session()
    try:
        template = session.query(Template).filter(Template.id == template_id).first()
        if not template:
            return None
        
        for key, value in update_data.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        session.commit()
        session.refresh(template)
        return template
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def delete_template(template_id: str) -> bool:
    """Delete template (soft delete by setting status)."""
    session = get_session()
    try:
        template = session.query(Template).filter(Template.id == template_id).first()
        if not template:
            return False
        
        template.status = "deleted"
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_template_fields(template_id: str) -> list[TemplateField]:
    """Get all fields for a template."""
    session = get_session()
    try:
        fields = session.query(TemplateField).filter(
            TemplateField.template_id == template_id
        ).order_by(TemplateField.sort_order).all()
        return fields
    except Exception:
        return []
    finally:
        session.close()


def update_template_fields(template_id: str, fields_data: list[dict[str, Any]]) -> list[TemplateField]:
    """Update template fields (replaces all existing fields)."""
    session = get_session()
    try:
        existing_fields = session.query(TemplateField).filter(
            TemplateField.template_id == template_id
        ).all()
        
        for field in existing_fields:
            session.delete(field)
        
        new_fields = []
        for field_data in fields_data:
            field = TemplateField(
                id=field_data.get("id") or f"field_{len(new_fields)}",
                template_id=template_id,
                field_name=field_data["field_name"],
                field_type=field_data["field_type"],
                display_name=field_data.get("display_name"),
                required=field_data.get("required", False),
                default_value=field_data.get("default_value"),
                validation_rules=field_data.get("validation_rules"),
                mapping_config=field_data.get("mapping_config"),
                sort_order=field_data.get("sort_order", 0),
            )
            session.add(field)
            new_fields.append(field)
        
        session.commit()
        for field in new_fields:
            session.refresh(field)
        
        return new_fields
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
