from app.db.session import get_db
from app.db.models.material import Material

with get_db() as db:
    total = db.query(Material).filter(Material.is_active == 1).count()
    print(f'Total active materials: {total}')

    # Get some sample IDs
    materials = db.query(Material).filter(Material.is_active == 1).limit(5).all()
    print(f'\nFirst {len(materials)} materials:')
    for m in materials:
        print(f'  ID={m.id}, name={m.name}')