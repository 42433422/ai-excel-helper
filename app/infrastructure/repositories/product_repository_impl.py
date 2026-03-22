from datetime import datetime
from typing import List, Optional

from app.db.models import Product as ProductModel
from app.db.session import get_db
from app.domain.product.entities import Product
from app.domain.value_objects import ModelNumber, Money
from app.infrastructure.repositories.product_repository import ProductRepository


class SQLAlchemyProductRepository(ProductRepository):
    """产品仓储 SQLAlchemy 实现"""
    
    def _to_domain(self, db_model: ProductModel) -> Product:
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
    
    def _to_db_model(self, product: Product) -> dict:
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
    
    def save(self, product: Product) -> Product:
        with get_db() as db:
            if product.id:
                existing = db.query(ProductModel).filter(ProductModel.id == product.id).first()
                if existing:
                    for key, value in self._to_db_model(product).items():
                        setattr(existing, key, value)
                    existing.updated_at = datetime.now()
                    db.commit()
                    db.refresh(existing)
                    return self._to_domain(existing)

            db_model = ProductModel(**self._to_db_model(product))
            db.add(db_model)
            db.commit()
            db.refresh(db_model)
            return self._to_domain(db_model)

    def create(self, product: Product) -> Product:
        return self.save(product)

    def find_by_id(self, product_id: int) -> Optional[Product]:
        with get_db() as db:
            model = db.query(ProductModel).filter(ProductModel.id == product_id).first()
            return self._to_domain(model) if model else None
    
    def find_all(self, page: int = 1, per_page: int = 20, **kwargs) -> tuple:
        with get_db() as db:
            offset = (page - 1) * per_page
            query = db.query(ProductModel)

            unit_name = kwargs.get('unit_name')
            if unit_name:
                query = query.filter(ProductModel.unit == unit_name)

            keyword = kwargs.get('keyword')
            if keyword:
                keyword_pattern = f"%{keyword}%"
                from sqlalchemy import or_
                query = query.filter(
                    or_(
                        ProductModel.name.like(keyword_pattern),
                        ProductModel.model_number.like(keyword_pattern)
                    )
                )

            total = query.count()
            models = query.order_by(
                ProductModel.id.desc()
            ).limit(per_page).offset(offset).all()
            return [self._to_domain(m) for m in models], total
    
    def find_by_model_number(self, model_number: str) -> Optional[Product]:
        with get_db() as db:
            model = db.query(ProductModel).filter(
                ProductModel.model_number == model_number
            ).first()
            return self._to_domain(model) if model else None
    
    def find_by_name(self, name: str) -> List[Product]:
        with get_db() as db:
            models = db.query(ProductModel).filter(
                ProductModel.name.like(f"%{name}%")
            ).all()
            return [self._to_domain(m) for m in models]
    
    def delete(self, product_id: int) -> bool:
        with get_db() as db:
            model = db.query(ProductModel).filter(ProductModel.id == product_id).first()
            if model:
                db.delete(model)
                db.commit()
                return True
            return False
    
    def count(self) -> int:
        with get_db() as db:
            return db.query(ProductModel).count()
