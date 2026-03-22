from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.db.base import Base


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String)
    specification = Column(String)
    unit = Column(String, default="个")
    quantity = Column(Float, default=0)
    unit_price = Column(Float, default=0)
    supplier = Column(String)
    warehouse_location = Column(String)
    min_stock = Column(Float, default=0)
    max_stock = Column(Float, default=0)
    description = Column(String)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
