import sqlite3
import os
import sys
sys.path.insert(0, 'e:/FHD/XCAGI')
from app.db.session import get_db
from app.db.models import Product

# Source DBs directory
SOURCE_DIR = 'e:/FHD/424'
UNIT_DBS = [
    '七彩乐园.db', '中江博郡家私.db', '侯雪梅.db', '半岛风情.db', '半岛风情外.db',
    '博旺家私.db', '名品_晶美鑫_.db', '国邦_钟志勇.db', '奔奔熊鞋柜.db', '宗南家私.db',
    '宜榢.db', '小火洋.db', '志泓家私.db', '杜克旗.db', '杰妮熊.db', '温总.db',
    '澜宇.db', '蕊芯家私.db', '蕊芯家私1.db', '迎扬电视墙.db', '金汉武.db',
    '金汉武_宾驰_.db', '金汉武三江源.db', '金汉武鼎丰_国邦.db', '鑫顺.db', '陈鑫强.db'
]

def get_unit_name(db_name):
    """Extract unit name from DB file name, e.g. '温总.db' -> '温总'"""
    return db_name.replace('.db', '')

def import_from_unit_db(db_path, unit_name):
    """Import products from a unit-specific DB"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get all products from source
    cur.execute('SELECT model_number, name, specification, price, quantity, description, category, brand FROM products')
    products = cur.fetchall()
    conn.close()

    imported = 0
    skipped = 0

    with get_db() as db:
        for (model_number, name, specification, price, quantity, description, category, brand) in products:
            # Check if product with same model_number already exists
            existing = db.query(Product).filter(Product.model_number == model_number).first()
            if existing:
                # Update existing product's unit if different
                if existing.unit != unit_name:
                    existing.unit = unit_name
                    db.commit()
                    imported += 1
                else:
                    skipped += 1
            else:
                # Create new product
                new_product = Product(
                    model_number=model_number,
                    name=name,
                    specification=specification or '',
                    price=price or 0.0,
                    quantity=quantity or 0,
                    description=description or '',
                    category=category or '',
                    brand=brand or '',
                    unit=unit_name,
                    is_active=True
                )
                db.add(new_product)
                db.commit()
                imported += 1

    return imported, skipped

def main():
    total_imported = 0
    total_skipped = 0

    for db_name in sorted(UNIT_DBS):
        db_path = os.path.join(SOURCE_DIR, db_name)
        if not os.path.exists(db_path):
            print(f'SKIP: {db_name} (not found)')
            continue

        unit_name = get_unit_name(db_name)
        print(f'Processing {db_name}...', end=' ')

        try:
            imported, skipped = import_from_unit_db(db_path, unit_name)
            print(f'imported={imported}, skipped={skipped}')
            total_imported += imported
            total_skipped += skipped
        except Exception as e:
            print(f'ERROR: {e}')

    print(f'\n=== Summary ===')
    print(f'Total imported: {total_imported}')
    print(f'Total skipped (already existed): {total_skipped}')

if __name__ == '__main__':
    main()
