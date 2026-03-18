# -*- coding: utf-8 -*-
"""
自动数据库迁移脚本

将旧数据库的数据迁移到新数据库结构中
"""
import sqlite3
import os
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)


def find_old_database():
    """查找旧数据库文件"""
    # 优先使用产品文件夹中的数据库
    product_db = r"E:\FHD\产品文件夹\customer_products_final_corrected.db"
    if os.path.exists(product_db):
        return product_db
    
    possible_paths = [
        r"E:\FHD\AI 助手\products.db",
        r"E:\FHD\AI 助手 2\products.db",
        r"E:\FHD\XCAGI\old_products.db",
        r"C:\Users\Public\XCAGI\products.db",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # 搜索 FHD 目录下所有 products.db 文件
    fhd_dir = r"E:\FHD"
    if os.path.exists(fhd_dir):
        for root, dirs, files in os.walk(fhd_dir):
            if "products.db" in files:
                db_path = os.path.join(root, "products.db")
                # 排除当前使用的数据库
                if not db_path.endswith(r"XCAGI\products.db"):
                    return db_path
    
    return None


def get_table_info(cursor, table_name):
    """获取表结构信息"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [(row[1], row[2]) for row in cursor.fetchall()]


def migrate_customers(old_conn, new_conn):
    """迁移客户数据"""
    try:
        old_cursor = old_conn.cursor()
        new_cursor = new_conn.cursor()
        
        # 检查旧数据库是否有 customers 表
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
        if not old_cursor.fetchone():
            logger.info("旧数据库中没有 customers 表，跳过迁移")
            return 0
        
        # 获取新表的列结构
        new_cursor.execute(f"PRAGMA table_info(customers)")
        new_columns = [row[1] for row in new_cursor.fetchall()]
        
        # 获取旧表的列结构
        old_cursor.execute(f"PRAGMA table_info(customers)")
        old_columns = [row[1] for row in old_cursor.fetchall()]
        
        # 列名映射（从旧数据库到新数据库）
        column_mapping = {
            'customer_id': 'id',           # 旧数据库用 customer_id，新数据库用 id
            '客户名称': 'customer_name',     # 中文列名映射到英文列名
            '联系人': 'contact_person',
            '电话': 'contact_phone',
            '地址': 'contact_address',
            '创建时间': 'created_at',
            '更新时间': 'updated_at'
        }
        
        # 获取旧表数据
        old_cursor.execute("SELECT * FROM customers")
        rows = old_cursor.fetchall()
        
        if not rows:
            logger.info("customers 表为空，无需迁移")
            return 0
        
        # 获取旧表列名
        old_cursor.execute(f"PRAGMA table_info(customers)")
        old_column_names = [row[1] for row in old_cursor.fetchall()]
        
        # 找出可以映射的列
        mapped_columns = []
        for old_col in old_column_names:
            new_col = column_mapping.get(old_col, old_col)  # 如果没有映射，则使用原列名
            if new_col in new_columns:  # 只有当新表中有对应列时才包含
                mapped_columns.append((old_col, new_col))
        
        if not mapped_columns:
            logger.error("新旧表结构完全不同，无法迁移")
            return 0
        
        # 准备 SQL 插入语句
        new_col_names = [new_col for _, new_col in mapped_columns]
        placeholders = ','.join(['?' for _ in new_col_names])
        columns_str = ','.join(new_col_names)
        
        count = 0
        for row in rows:
            try:
                # 将行数据转换为字典
                row_dict = dict(zip(old_column_names, row))
                
                # 根据映射关系提取值
                values = []
                for old_col, new_col in mapped_columns:
                    values.append(row_dict.get(old_col))
                
                new_cursor.execute(
                    f"INSERT OR IGNORE INTO customers ({columns_str}) VALUES ({placeholders})",
                    values
                )
                count += 1
            except Exception as e:
                logger.warning(f"插入客户记录失败：{e}")
        
        new_conn.commit()
        logger.info(f"成功迁移 {count} 条客户记录")
        return count
        
    except Exception as e:
        logger.error(f"迁移 customers 表失败：{e}")
        return 0


def migrate_purchase_units(old_conn, new_conn):
    """迁移购买单位数据"""
    try:
        old_cursor = old_conn.cursor()
        new_cursor = new_conn.cursor()
        
        # 检查旧数据库是否有 purchase_units 表
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='purchase_units'")
        has_purchase_units_table = old_cursor.fetchone() is not None
        
        migrated_count = 0
        
        # 如果有 purchase_units 表，先迁移表中的数据
        if has_purchase_units_table:
            # 获取旧表数据
            old_cursor.execute("SELECT * FROM purchase_units")
            rows = old_cursor.fetchall()
            
            if rows:
                # 获取列名
                old_cursor.execute(f"PRAGMA table_info(purchase_units)")
                columns = [row[1] for row in old_cursor.fetchall()]
                
                # 插入新表
                placeholders = ','.join(['?' for _ in columns])
                columns_str = ','.join(columns)
                
                for row in rows:
                    try:
                        new_cursor.execute(
                            f"INSERT OR IGNORE INTO purchase_units ({columns_str}) VALUES ({placeholders})",
                            row
                        )
                        migrated_count += 1
                    except Exception as e:
                        logger.warning(f"插入购买单位记录失败：{e}")
                
                new_conn.commit()
                logger.info(f"从 purchase_units 表迁移了 {migrated_count} 条记录")
        else:
            logger.info("旧数据库中没有 purchase_units 表")
        
        # 从 shipment_records 表中提取购买单位
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shipment_records'")
        if old_cursor.fetchone():
            # 获取所有不同的购买单位
            old_cursor.execute("SELECT DISTINCT purchase_unit FROM shipment_records WHERE purchase_unit IS NOT NULL")
            old_units = [row[0] for row in old_cursor.fetchall()]
            
            if old_units:
                # 获取新数据库中已有的购买单位
                new_cursor.execute("SELECT unit_name FROM purchase_units")
                existing_units = [row[0] for row in new_cursor.fetchall()]
                
                # 找出缺失的购买单位
                missing_units = set(old_units) - set(existing_units)
                
                if missing_units:
                    logger.info(f"发现 {len(missing_units)} 个新的购买单位")
                    # 插入缺失的购买单位
                    for unit in missing_units:
                        try:
                            new_cursor.execute(
                                "INSERT INTO purchase_units (unit_name, contact_person, contact_phone, address, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
                                (unit, '', '', '', 1)
                            )
                            migrated_count += 1
                        except Exception as e:
                            logger.warning(f"插入购买单位失败 {unit}: {e}")
                    
                    new_conn.commit()
                    logger.info(f"从 shipment_records 提取并插入了 {len(missing_units)} 个购买单位")
        
        logger.info(f"总共迁移了 {migrated_count} 个购买单位")
        return migrated_count
        
    except Exception as e:
        logger.error(f"迁移 purchase_units 失败：{e}")
        return 0


def migrate_products(old_conn, new_conn):
    """迁移产品数据"""
    try:
        old_cursor = old_conn.cursor()
        new_cursor = new_conn.cursor()
        
        # 检查旧数据库是否有 products 表
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
        if not old_cursor.fetchone():
            logger.info("旧数据库中没有 products 表，跳过迁移")
            return 0
        
        # 获取旧表数据
        old_cursor.execute("SELECT * FROM products")
        rows = old_cursor.fetchall()
        
        if not rows:
            logger.info("products 表为空，无需迁移")
            return 0
        
        # 获取旧表的列
        old_cursor.execute(f"PRAGMA table_info(products)")
        old_columns = [row[1] for row in old_cursor.fetchall()]
        
        # 获取新表的列
        new_cursor.execute(f"PRAGMA table_info(products)")
        new_columns = [row[1] for row in new_cursor.fetchall()]
        
        logger.info(f"旧表列：{old_columns}")
        logger.info(f"新表列：{new_columns}")
        
        # 列名映射（从旧数据库到新数据库）
        column_mapping = {
            'product_id': 'id',
            '产品型号': 'model_number',
            '产品名称': 'name',
            ' 规格_KG': 'specification',
            '数量_KG': 'quantity',
            '单价': 'price',
            '金额': 'amount',
            '单号': 'order_number',
            '记录顺序': 'sort_order',
            '来源': 'source',
            '创建时间': 'created_at',
            '更新时间': 'updated_at'
        }
        
        # 找出可以映射的列
        mapped_columns = []
        for old_col in old_columns:
            new_col = column_mapping.get(old_col, old_col)
            if new_col in new_columns:
                mapped_columns.append((old_col, new_col))
        
        # 检查是否有客户 ID 字段（注意可能有空格或无空格），用于填充 unit 字段
        # 可能的列名变体：'客户 ID', ' 客户 ID', '客户 ID ' 等
        customer_id_col = None
        for col in old_columns:
            # 去除空格后匹配（使用 Unicode 编码避免输入法自动添加空格）
            col_stripped = col.strip()
            # \u5ba2\u6237ID = 客户 ID（无空格）
            if col_stripped == '\u5ba2\u6237ID':
                customer_id_col = col
                break
        
        has_customer_id = customer_id_col is not None
        
        # 如果有客户 ID 字段，需要加载客户名称映射
        customer_map = {}
        if has_customer_id and customer_id_col:
            old_cursor.execute("SELECT customer_id, 客户名称 FROM customers")
            for row in old_cursor.fetchall():
                customer_map[row[0]] = row[1]
            logger.info(f"加载了 {len(customer_map)} 个客户名称映射，使用列名：{customer_id_col}")
        
        if not mapped_columns:
            logger.error("新旧表结构完全不同，无法迁移")
            return 0
        
        # 准备 SQL 插入语句
        new_col_names = [new_col for _, new_col in mapped_columns]
        
        # 如果需要填充 unit 字段，添加到列中
        if has_customer_id and 'unit' in new_columns:
            if 'unit' not in new_col_names:
                new_col_names.append('unit')
        
        placeholders = ','.join(['?' for _ in new_col_names])
        columns_str = ','.join(new_col_names)
        
        migrated_count = 0
        for row in rows:
            try:
                # 将行数据转换为字典
                row_dict = dict(zip(old_columns, row))
                
                # 根据映射关系提取值
                values = []
                for old_col, new_col in mapped_columns:
                    values.append(row_dict.get(old_col))
                
                # 如果有客户 ID 字段，添加对应的客户名称到 unit 字段
                if has_customer_id and customer_id_col and 'unit' in new_columns:
                    customer_id = row_dict.get(customer_id_col)
                    unit_name = customer_map.get(customer_id, '') if customer_id else ''
                    if 'unit' not in [col for _, col in mapped_columns]:
                        values.append(unit_name)
                
                new_cursor.execute(
                    f"INSERT OR IGNORE INTO products ({columns_str}) VALUES ({placeholders})",
                    values
                )
                migrated_count += 1
            except Exception as e:
                logger.warning(f"插入产品记录失败：{e}")
        
        new_conn.commit()
        logger.info(f"成功迁移 {migrated_count} 条产品记录")
        return migrated_count
        
    except Exception as e:
        logger.error(f"迁移 products 表失败：{e}")
        return 0


def migrate_shipment_records(old_conn, new_conn):
    """迁移发货记录数据"""
    try:
        old_cursor = old_conn.cursor()
        new_cursor = new_conn.cursor()
        
        # 检查旧数据库是否有 shipment_records 表
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shipment_records'")
        if not old_cursor.fetchone():
            logger.info("旧数据库中没有 shipment_records 表，跳过迁移")
            return 0
        
        # 获取旧表数据
        old_cursor.execute("SELECT * FROM shipment_records")
        rows = old_cursor.fetchall()
        
        if not rows:
            logger.info("shipment_records 表为空，无需迁移")
            return 0
        
        # 获取列名
        old_cursor.execute(f"PRAGMA table_info(shipment_records)")
        old_columns = [row[1] for row in old_cursor.fetchall()]
        
        # 获取新表的列
        new_cursor.execute(f"PRAGMA table_info(shipment_records)")
        new_columns = [row[1] for row in new_cursor.fetchall()]
        
        # 找出共同的列
        common_columns = [col for col in old_columns if col in new_columns]
        
        if not common_columns:
            logger.error("新旧表结构完全不同，无法迁移")
            return 0
        
        # 插入新表
        placeholders = ','.join(['?' for _ in common_columns])
        columns_str = ','.join(common_columns)
        
        count = 0
        for row in rows:
            try:
                # 构建行数据
                row_dict = dict(zip(old_columns, row))
                row_data = [row_dict.get(col) for col in common_columns]
                
                new_cursor.execute(
                    f"INSERT OR IGNORE INTO shipment_records ({columns_str}) VALUES ({placeholders})",
                    row_data
                )
                count += 1
            except Exception as e:
                logger.warning(f"插入发货记录失败：{e}")
        
        new_conn.commit()
        logger.info(f"成功迁移 {count} 条发货记录")
        return count
        
    except Exception as e:
        logger.error(f"迁移 shipment_records 表失败：{e}")
        return 0


def migrate_all_tables(old_conn, new_conn):
    """迁移所有表"""
    logger.info("=" * 60)
    logger.info("开始数据库迁移")
    logger.info("=" * 60)
    
    # 迁移各个表
    total_migrated = 0
    
    logger.info("\n迁移 customers 表...")
    total_migrated += migrate_customers(old_conn, new_conn)
    
    logger.info("\n迁移 purchase_units 表...")
    total_migrated += migrate_purchase_units(old_conn, new_conn)
    
    logger.info("\n迁移 products 表...")
    total_migrated += migrate_products(old_conn, new_conn)
    
    logger.info("\n迁移 shipment_records 表...")
    total_migrated += migrate_shipment_records(old_conn, new_conn)
    
    logger.info("\n" + "=" * 60)
    logger.info(f"数据库迁移完成！共迁移 {total_migrated} 条记录")
    logger.info("=" * 60)
    
    return total_migrated


def main():
    """主函数"""
    # 新数据库路径
    new_db_path = Path(__file__).parent / "products.db"
    
    if not os.path.exists(new_db_path):
        logger.error(f"新数据库不存在：{new_db_path}")
        return False
    
    # 查找旧数据库
    old_db_path = find_old_database()
    
    if not old_db_path:
        logger.error("未找到旧数据库文件")
        logger.info("请在代码中指定旧数据库路径")
        return False
    
    logger.info(f"找到旧数据库：{old_db_path}")
    logger.info(f"新数据库：{new_db_path}")
    
    try:
        # 连接数据库
        old_conn = sqlite3.connect(old_db_path)
        new_conn = sqlite3.connect(new_db_path)
        
        # 执行迁移
        success = migrate_all_tables(old_conn, new_conn)
        
        # 关闭连接
        old_conn.close()
        new_conn.close()
        
        return success > 0
        
    except Exception as e:
        logger.error(f"迁移失败：{e}")
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
