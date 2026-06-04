from app.db.models import Material as MaterialModel
from app.domain.product.entities import Product  # placeholder if needed


def material_to_domain(db_model: MaterialModel):
    # Minimal mapping; expand as needed.
    return {
        "id": db_model.id,
        "material_code": db_model.material_code,
        "name": db_model.name,
        "specification": db_model.specification,
        "unit": db_model.unit,
        "quantity": db_model.quantity,
        "unit_price": db_model.unit_price,
    }
