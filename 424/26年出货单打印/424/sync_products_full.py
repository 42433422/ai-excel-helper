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
    return db_name.replace('.db', '')

def clear_and_import():
    """Clear all products and re-import from unit DBs"""
    total_added = 0

    with get_db() as db:
        # Clear all existing products
        db.query(Product).delete()
        db.commit()
        print('Cleared all existing products')

        for db_name in sorted(UNIT_DBS):
            db_path = os.path.join(SOURCE_DIR, db_name)
            if not os.path.exists(db_path):
                print(f'SKIP: {db_name} (not found)')
                continue

            unit_name = get_unit_name(db_name)
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute('SELECT model_number, name, specification, price, quantity, description, category, brand FROM products')
            products = cur.fetchall()
            conn.close()

            added = 0
            for (model_number, name, specification, price, quantity, description, category, brand) in products:
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
                added += 1

            db.commit()
            print(f'{db_name}: added {added} products')
            total_added += added

    print(f'\nTotal added: {total_added}')

if __name__ == '__main__':
    clear_and_import()
