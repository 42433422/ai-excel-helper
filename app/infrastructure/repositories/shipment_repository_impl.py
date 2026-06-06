from app.db.models import ShipmentRecord
from app.db.session import get_db
from app.domain.shipment.aggregates import Shipment
from app.domain.value_objects import ContactInfo, OrderNumber
from app.infrastructure.mappers.shipment_mapper import shipment_to_db, shipment_to_domain
from app.infrastructure.repositories.shipment_repository import ShipmentRepository


class SQLAlchemyShipmentRepository(ShipmentRepository):
    """发货单仓储 SQLAlchemy 实现"""

    def _to_domain(self, db_record: ShipmentRecord) -> Shipment:
        """将数据库记录转换为领域对象"""
        return shipment_to_domain(db_record)

    def _to_db_model(self, shipment: Shipment) -> dict:
        """将领域对象转换为数据库模型"""
        return shipment_to_db(shipment)

    def save(self, shipment: Shipment) -> Shipment:
        """保存发货单"""
        with get_db() as db:
            if shipment.id:
                existing = db.query(ShipmentRecord).filter(ShipmentRecord.id == shipment.id).first()
                if existing:
                    for key, value in self._to_db_model(shipment).items():
                        setattr(existing, key, value)
                    db.commit()
                    db.refresh(existing)
                    return self._to_domain(existing)

            db_record = ShipmentRecord(**self._to_db_model(shipment))
            db.add(db_record)
            db.commit()
            db.refresh(db_record)
            shipment.id = db_record.id
            return shipment

    def find_by_id(self, shipment_id: int) -> Shipment | None:
        """根据 ID 查询发货单"""
        with get_db() as db:
            record = db.query(ShipmentRecord).filter(ShipmentRecord.id == shipment_id).first()
            return self._to_domain(record) if record else None

    def find_by_order_number(self, order_number: str) -> Shipment | None:
        """根据订单号查询发货单"""
        try:
            shipment_id = int(order_number)
            return self.find_by_id(shipment_id)
        except ValueError:
            return None

    def find_all(self, page: int = 1, per_page: int = 20) -> list[Shipment]:
        """查询所有发货单（分页）"""
        with get_db() as db:
            offset = (page - 1) * per_page
            records = (
                db.query(ShipmentRecord)
                .order_by(ShipmentRecord.created_at.desc())
                .limit(per_page)
                .offset(offset)
                .all()
            )
            return [self._to_domain(r) for r in records]

    def find_by_unit(self, unit_name: str) -> list[Shipment]:
        """根据购买单位查询发货单"""
        with get_db() as db:
            records = (
                db.query(ShipmentRecord)
                .filter(ShipmentRecord.purchase_unit == unit_name)
                .order_by(ShipmentRecord.created_at.desc())
                .all()
            )
            return [self._to_domain(r) for r in records]

    def delete(self, shipment_id: int) -> bool:
        """删除发货单"""
        with get_db() as db:
            record = db.query(ShipmentRecord).filter(ShipmentRecord.id == shipment_id).first()
            if record:
                db.delete(record)
                db.commit()
                return True
            return False

    def count(self) -> int:
        """统计发货单总数"""
        with get_db() as db:
            return db.query(ShipmentRecord).count()
