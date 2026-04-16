import os
import shutil

def fix_sqlalchemy_config():
    """修复SQLAlchemy配置，使用正确的数据库"""
    
    print("🔧 修复SQLAlchemy配置")
    print("=" * 60)
    
    # 源数据库（我们添加了购买单位数据的数据库）
    source_db = "e:/FHD/424/customers.db"
    
    # 目标数据库（后端实际使用的数据库）
    target_db = "e:/FHD/xcagi/customers.db"
    
    # 检查源数据库是否存在
    if not os.path.exists(source_db):
        print(f"❌ 源数据库不存在: {source_db}")
        return False
    
    print(f"📁 源数据库: {source_db}")
    print(f"📁 目标数据库: {target_db}")
    
    # 方案1: 复制源数据库到目标位置
    print("\n💡 方案1: 复制源数据库到目标位置")
    
    try:
        # 确保目标目录存在
        os.makedirs(os.path.dirname(target_db), exist_ok=True)
        
        # 复制数据库文件
        shutil.copy2(source_db, target_db)
        
        print(f"✅ 数据库复制成功")
        print(f"   从 {source_db}")
        print(f"   到 {target_db}")
        
        # 验证复制结果
        import sqlite3
        conn = sqlite3.connect(target_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM purchase_units WHERE is_active = 1")
        count = cursor.fetchone()[0]
        
        cursor.execute("SELECT id, unit_name FROM purchase_units WHERE is_active = 1 ORDER BY unit_name")
        units = cursor.fetchall()
        
        print(f"📊 目标数据库活跃购买单位: {count} 个")
        print("🏷️ 购买单位列表:")
        for unit in units:
            print(f"  - ID: {unit[0]}, 名称: {unit[1]}")
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库复制失败: {e}")
        
        # 方案2: 修改SQLAlchemy配置
        print("\n💡 方案2: 修改SQLAlchemy配置")
        
        # 检查是否可以修改数据库路径配置
        config_file = "e:/FHD/xcagi/app/db/init_db.py"
        
        if os.path.exists(config_file):
            print(f"📄 可以修改配置文件: {config_file}")
            print("   修改get_db_path函数，返回正确的数据库路径")
        
        return False

def check_backend_after_fix():
    """修复后检查后端API"""
    
    print("\n🔍 修复后检查后端API")
    print("=" * 60)
    
    import requests
    import time
    
    base_url = "http://127.0.0.1:8000"
    
    # 等待后端重启
    print("⏳ 等待后端重启...")
    time.sleep(3)
    
    # 检查API响应
    try:
        response = requests.get(f"{base_url}/api/customers", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            customers = data.get("data", [])
            
            print(f"📊 /api/customers 返回 {len(customers)} 个客户")
            
            if customers:
                print("📋 客户列表:")
                for customer in customers:
                    print(f"  - ID: {customer['id']}, 名称: {customer['customer_name']}")
            
            # 检查是否返回了正确的数据
            expected_customers = ["半岛风情", "半岛家具", "测试单位1", "测试单位2", "测试单位3"]
            actual_customers = [c['customer_name'] for c in customers]
            
            if set(expected_customers).issubset(set(actual_customers)):
                print("✅ 后端API现在返回正确的购买单位数据！")
            else:
                print("❌ 后端API仍然返回错误的数据")
                
        else:
            print(f"❌ API请求失败，状态码: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 检查后端API失败: {e}")

def restart_backend_service():
    """重启后端服务"""
    
    print("\n🔧 重启后端服务")
    print("=" * 60)
    
    # 检查后端进程
    import subprocess
    
    try:
        # 查找后端进程
        result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe"], 
                              capture_output=True, text=True)
        
        if "run.py" in result.stdout:
            print("🔍 找到运行中的后端进程")
            
            # 结束进程
            subprocess.run(["taskkill", "/F", "/IM", "python.exe"], capture_output=True)
            print("✅ 已结束后端进程")
        
        # 重新启动后端
        print("🚀 重新启动后端服务...")
        
        # 在新的终端中启动后端
        subprocess.Popen(["python", "e:/FHD/xcagi/run.py"], 
                        cwd="e:/FHD/xcagi",
                        creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        print("✅ 后端服务已重启")
        
    except Exception as e:
        print(f"❌ 重启后端服务失败: {e}")
        print("💡 请手动重启后端服务")

if __name__ == "__main__":
    # 修复数据库配置
    success = fix_sqlalchemy_config()
    
    if success:
        print("\n🎯 下一步:")
        print("1. 重启后端服务")
        print("2. 检查后端API是否返回正确的数据")
        print("3. 刷新前端页面验证客户列表")
        
        # 询问是否重启后端
        print("\n💡 需要重启后端服务才能使修改生效")
        print("   请手动重启后端服务，或者运行以下命令:")
        print("   cd e:/FHD/xcagi")
        print("   python run.py")
        
    else:
        print("\n❌ 修复失败，需要手动处理")
        print("💡 建议方案:")
        print("1. 手动复制数据库文件")
        print("2. 或者修改SQLAlchemy配置")
        print("3. 重启后端服务")