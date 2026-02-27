import sqlite3
from datetime import datetime

db_path = r'C:\Users\Administrator\Desktop\新建文件夹 (4)\AI助手\products.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT order_number, created_at FROM orders 
    ORDER BY created_at DESC 
    LIMIT 1
""")
latest_order = cursor.fetchone()
conn.close()

today = datetime.now()
year = today.strftime("%y")
month = today.strftime("%m")
year_month = f"{year}-{month}"

if latest_order:
    latest_order_number = latest_order[0]
    print(f"Latest order number: {latest_order_number}")
    parts = latest_order_number.split('-')
    print(f"Parts: {parts}, length: {len(parts)}")
    
    if len(parts) >= 3:
        sequence_match = parts[2].split('A')[0]
        sequence = int(sequence_match) if sequence_match.isdigit() else 1
    else:
        sequence = 1
        print(f"Order number format is non-standard, using default sequence")
else:
    latest_order_number = f"{year}-{month}-00001A"
    sequence = 1

next_sequence = sequence + 1
next_order_number = f"{year}-{month}-{next_sequence:05d}A"

print(f"Current sequence: {sequence}")
print(f"Next order number: {next_order_number}")
