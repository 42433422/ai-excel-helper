# XCAGI 系统故障排查手册

> 版本：1.0.0  
> 最后更新：2026-03-17  
> 适用范围：XCAGI 系统开发、运维人员

---

## 目录

- [第一章 排查基础](#第一章 - 排查基础)
  - [1.1 日志系统](#11-日志系统)
  - [1.2 调试工具](#12-调试工具)
  - [1.3 监控指标](#13-监控指标)
- [第二章 常见问题排查](#第二章 - 常见问题排查)
  - [2.1 数据库问题](#21-数据库问题)
  - [2.2 缓存问题](#22-缓存问题)
  - [2.3 异步任务问题](#23-异步任务问题)
  - [2.4 前端问题](#24-前端问题)
  - [2.5 API 接口问题](#25-api-接口问题)
- [第三章 性能问题排查](#第三章 - 性能问题排查)
  - [3.1 慢查询排查](#31-慢查询排查)
  - [3.2 内存泄漏排查](#32-内存泄漏排查)
  - [3.3 接口响应慢排查](#33-接口响应慢排查)
- [第四章 典型错误及解决方案](#第四章 - 典型错误及解决方案)
- [第五章 应急处理流程](#第五章 - 应急处理流程)
  - [5.1 系统回滚流程](#51-系统回滚流程)
  - [5.2 数据恢复流程](#52-数据恢复流程)
  - [5.3 服务重启流程](#53-服务重启流程)

---

## 第一章 排查基础

### 1.1 日志系统

#### 1.1.1 日志位置

XCAGI 系统使用统一的日志管理，所有日志文件位于 `logs` 目录下：

```
E:\FHD\XCAGI\data\logs\
├── debug_ndjson.log    # NDJSON 格式调试日志
└── app.log             # 应用主日志（如配置）
```

**日志目录获取方式：**

```python
from app.utils.path_utils import get_log_dir
log_dir = get_log_dir()
# 输出：E:\FHD\XCAGI\data\logs
```

#### 1.1.2 日志级别说明

| 级别 | 说明 | 使用场景 |
|------|------|----------|
| `DEBUG` | 调试信息 | 详细的技术调试信息 |
| `INFO` | 一般信息 | 系统正常运行信息 |
| `WARNING` | 警告信息 | 可能影响系统的问题 |
| `ERROR` | 错误信息 | 系统错误但可继续运行 |
| `CRITICAL` | 严重错误 | 系统无法继续运行 |

#### 1.1.3 查看日志方法

**Windows PowerShell 实时查看日志：**

```powershell
# 实时查看调试日志
Get-Content E:\FHD\XCAGI\data\logs\debug_ndjson.log -Wait -Tail 50

# 查看最近 100 行错误日志
Get-Content E:\FHD\XCAGI\data\logs\debug_ndjson.log -Tail 100 | Select-String "ERROR|CRITICAL"

# 查看特定时间的日志
Get-Content E:\FHD\XCAGI\data\logs\debug_ndjson.log | Select-String "2026-03-17"
```

**使用 Python 解析 NDJSON 日志：**

```python
import json
from pathlib import Path

log_file = Path("E:/FHD/XCAGI/data/logs/debug_ndjson.log")

with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            entry = json.loads(line)
            print(f"[{entry.get('timestamp')}] {entry.get('message')}")
        except json.JSONDecodeError:
            continue
```

#### 1.1.4 日志配置

日志配置位于 [`app/config.py`](file:///e:/FHD/XCAGI/app/config.py#L37-L39)：

```python
# 日志配置
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**修改日志级别：**

```bash
# 开发环境设置为 DEBUG
$env:LOG_LEVEL="DEBUG"

# 生产环境设置为 WARNING
$env:LOG_LEVEL="WARNING"
```

### 1.2 调试工具

#### 1.2.1 Flask 调试模式

开发环境自动启用调试模式，配置位于 [`run.py`](file:///e:/FHD/XCAGI/run.py#L16-L25)：

```python
app.run(
    host="0.0.0.0",
    port=5000,
    debug=True,  # 启用调试模式
    threaded=True
)
```

**调试模式特性：**
- 代码自动重载
- 交互式调试器
- 详细错误页面

#### 1.2.2 Swagger API 文档

访问 API 文档：http://localhost:5000/apidocs

**用途：**
- 查看 API 接口定义
- 在线测试 API
- 查看请求/响应示例

#### 1.2.3 数据库调试

**查看 SQLite 数据库：**

```powershell
# 使用 SQLite 命令行
sqlite3 E:\FHD\XCAGI\products.db

# 查看所有表
.tables

# 查看表结构
.schema products

# 查询数据
SELECT * FROM products LIMIT 10;
```

**使用 Python 检查数据库：**

```python
from app.db.session import get_db

with get_db() as db:
    # 执行查询
    results = db.execute("SELECT * FROM products LIMIT 5").fetchall()
    print(results)
```

#### 1.2.4 网络请求调试

**浏览器开发者工具：**

1. 按 `F12` 打开开发者工具
2. 切换到 `Network` 标签
3. 筛选 XHR/Fetch 请求
4. 查看请求详情（Headers、Response、Timing）

**使用 curl 测试 API：**

```bash
# 测试产品列表 API
curl -X GET http://localhost:5000/api/products

# 带参数测试
curl -X GET "http://localhost:5000/api/products?keyword=test&page=1"

# POST 请求
curl -X POST http://localhost:5000/api/products ^
  -H "Content-Type: application/json" ^
  -d "{\"product_name\":\"测试产品\",\"price\":99.99}"
```

### 1.3 监控指标

#### 1.3.1 系统资源监控

**CPU 使用率：**

```powershell
# 查看进程 CPU 使用率
Get-Process python | Select-Object Id, CPU, WorkingSet

# 持续监控
while ($true) {
    Get-Process python | Select-Object Id, CPU, WorkingSet
    Start-Sleep -Seconds 2
}
```

**内存使用率：**

```powershell
# 查看 Python 进程内存
Get-Process python | Select-Object Id, WorkingSet, VirtualMemorySize

# 转换为 MB
Get-Process python | Select-Object Id, 
    @{N="Mem(MB)";E={[math]::Round($_.WorkingSet/1MB, 2)}}
```

#### 1.3.2 数据库监控

**数据库文件大小：**

```powershell
# 查看所有数据库文件大小
Get-Item E:\FHD\XCAGI\*.db | Select-Object Name, Length, LastWriteTime
```

**数据库连接状态：**

```python
from app.db.session import get_db
import logging

logger = logging.getLogger(__name__)

try:
    with get_db() as db:
        # 测试连接
        db.execute("SELECT 1").fetchone()
        logger.info("数据库连接正常")
except Exception as e:
    logger.error(f"数据库连接失败：{e}")
```

#### 1.3.3 Redis 缓存监控

**检查 Redis 服务状态：**

```powershell
# 检查 Redis 端口
netstat -ano | findstr :6379

# 使用 redis-cli 检查
redis-cli ping
# 应返回：PONG

# 查看 Redis 信息
redis-cli info
```

**缓存命中率监控：**

```python
from flask_caching import Cache
from app.extensions import cache

# 获取缓存统计
stats = cache.cache._stats
print(f"命中：{stats.get('hits', 0)}, 未命中：{stats.get('misses', 0)}")
```

#### 1.3.4 Celery 任务监控

**查看 Celery Worker 状态：**

```powershell
# 启动 Celery Worker
python celery_app.py worker -l info

# 查看任务队列
celery -A celery_app inspect active

# 查看已注册任务
celery -A celery_app inspect registered
```

**任务执行日志：**

```python
# 在任务中添加日志
from app.extensions import celery_app
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def my_task():
    logger.info("任务开始执行")
    try:
        # 任务逻辑
        logger.info("任务执行成功")
    except Exception as e:
        logger.exception(f"任务执行失败：{e}")
        raise
```

---

## 第二章 常见问题排查

### 2.1 数据库问题

#### 2.1.1 问题：数据库文件锁定

**现象：**
```
sqlite3.OperationalError: database is locked
```

**原因：**
- 多个进程同时写入数据库
- 数据库连接未正确关闭
- 事务未提交或回滚

**排查步骤：**

1. **检查数据库文件锁定状态：**
```powershell
# 查看是否有进程锁定数据库文件
Handle.exe products.db
# 需要下载 Sysinternals Suite 中的 Handle 工具
```

2. **检查代码中的数据库连接：**
```python
# 错误示例：连接未关闭
db = SessionLocal()
results = db.query(Product).all()
# 忘记 db.close()

# 正确示例：使用上下文管理器
from app.db.session import get_db

with get_db() as db:
    results = db.query(Product).all()
# 自动关闭连接
```

3. **启用 WAL 模式提高并发：**
```python
from db import get_db_path
import sqlite3

db_path = get_db_path()
conn = sqlite3.connect(db_path)
conn.execute("PRAGMA journal_mode=WAL")
conn.close()
```

**解决方案：**

```python
# 方案 1：确保所有连接都正确关闭
from contextlib import contextmanager
from app.db.session import SessionLocal

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()  # 确保关闭

# 方案 2：增加超时时间
from sqlalchemy import create_engine

engine = create_engine(
    f"sqlite:///{db_path}",
    connect_args={"timeout": 30}  # 增加超时时间到 30 秒
)
```

#### 2.1.2 问题：表不存在

**现象：**
```
sqlalchemy.exc.OperationalError: no such table: products
```

**原因：**
- 数据库未初始化
- 数据库迁移未执行
- 使用了错误的数据库文件

**排查步骤：**

1. **检查数据库文件是否存在：**
```powershell
Test-Path E:\FHD\XCAGI\products.db
# 返回 True 表示存在
```

2. **查看数据库中的表：**
```powershell
sqlite3 E:\FHD\XCAGI\products.db ".tables"
```

3. **检查数据库初始化代码：**
```python
# app/__init__.py
from db import initialize_databases, init_wechat_tasks_table

# 确保在 create_app 中调用
initialize_databases()
init_wechat_tasks_table()
```

**解决方案：**

```python
# 方案 1：手动初始化数据库
from db import initialize_databases

initialize_databases()
print("数据库初始化完成")

# 方案 2：使用 Alembic 迁移
# 升级数据库到最新版本
alembic upgrade head

# 查看当前版本
alembic current

# 方案 3：检查模型定义
from app.db.models import Product
from app.db.base import Base
from db import get_engine

# 创建所有表
Base.metadata.create_all(bind=get_engine())
```

#### 2.1.3 问题：查询性能慢

**现象：**
- 接口响应时间超过 2 秒
- 日志中出现慢查询

**排查步骤：**

1. **启用 SQL 查询日志：**
```python
# app/config.py
SQLALCHEMY_ECHO = True  # 输出所有 SQL 语句
```

2. **分析慢查询：**
```python
import time
from app.db.session import get_db
from app.db.models import Product

start = time.time()

with get_db() as db:
    # 低效查询示例
    products = db.query(Product).all()
    for p in products:
        print(p.name)

end = time.time()
print(f"查询耗时：{end - start:.3f}秒")
```

3. **使用 EXPLAIN 分析查询计划：**
```sql
-- 在 SQLite 中
EXPLAIN QUERY PLAN SELECT * FROM products WHERE name LIKE '%test%';
```

**解决方案：**

```python
# 方案 1：添加索引
# alembic/versions/xxx_add_indexes.py
def upgrade():
    op.create_index('ix_products_name', 'products', ['name'])
    op.create_index('ix_products_category', 'products', ['category'])

# 方案 2：优化查询
# 低效
products = db.query(Product).filter(Product.name.like('%keyword%')).all()

# 高效（使用全文索引）
products = db.query(Product).filter(
    Product.name.like('keyword%')  # 前缀匹配
).all()

# 方案 3：分页查询
products = db.query(Product).limit(20).offset(0).all()
```

### 2.2 缓存问题

#### 2.2.1 问题：缓存未命中

**现象：**
- 相同请求每次都查询数据库
- Redis 日志中没有命中记录

**原因：**
- 缓存键不一致
- 缓存过期时间设置过短
- Redis 服务未启动

**排查步骤：**

1. **检查 Redis 服务状态：**
```powershell
redis-cli ping
# 应返回 PONG
```

2. **查看缓存配置：**
```python
# app/extensions.py
cache = Cache(config={"CACHE_TYPE": "RedisCache"})

# app/config.py
CACHE_REDIS_URL = "redis://localhost:6379/0"
```

3. **测试缓存功能：**
```python
from flask_caching import Cache
from app.extensions import cache
from flask import Flask

app = Flask(__name__)
cache.init_app(app)

with app.app_context():
    # 设置缓存
    cache.set('test_key', 'test_value', timeout=60)
    
    # 获取缓存
    value = cache.get('test_key')
    print(f"缓存值：{value}")
```

**解决方案：**

```python
# 方案 1：正确设置缓存键
from flask_caching import Cache

@cache.cached(timeout=300, key_prefix='products_list')
def get_products():
    # 查询数据库
    return products

# 方案 2：使用缓存装饰器
@cache.memoize(timeout=300)
def get_product_by_id(product_id):
    # 查询数据库
    return product

# 方案 3：手动管理缓存
from app.extensions import cache

def get_products_with_cache():
    # 尝试从缓存获取
    products = cache.get('products_list')
    
    if products is None:
        # 缓存未命中，查询数据库
        products = query_products_from_db()
        # 写入缓存
        cache.set('products_list', products, timeout=300)
    
    return products
```

#### 2.2.2 问题：缓存污染

**现象：**
- 缓存数据与实际数据不一致
- 更新后仍然显示旧数据

**原因：**
- 数据更新后未清除缓存
- 缓存键设计不合理
- 缓存过期时间过长

**排查步骤：**

1. **检查缓存清除逻辑：**
```python
# 错误示例：更新后未清除缓存
def update_product(product_id, data):
    product = db.query(Product).get(product_id)
    product.name = data['name']
    db.commit()
    # 忘记清除缓存

# 正确示例
def update_product(product_id, data):
    product = db.query(Product).get(product_id)
    product.name = data['name']
    db.commit()
    
    # 清除缓存
    cache.delete(f'product_{product_id}')
    cache.delete('products_list')
```

**解决方案：**

```python
# 方案 1：使用缓存失效装饰器
from flask_caching import Cache

cache = Cache()

@cache.cached(timeout=300, key_prefix='product_{product_id}')
def get_product(product_id):
    return db.query(Product).get(product_id)

@cache.cache.memoize(timeout=300)
def get_product_memoized(product_id):
    return db.query(Product).get(product_id)

def update_product(product_id, data):
    product = db.query(Product).get(product_id)
    product.name = data['name']
    db.commit()
    
    # 清除缓存
    cache.delete_memoized(get_product_memoized, product_id)

# 方案 2：批量清除缓存
def clear_product_cache():
    """清除所有产品相关缓存"""
    cache.delete('products_list')
    cache.delete('products_total')
    # 可以添加更多缓存键

# 方案 3：使用版本号管理缓存
def get_products_cache_key():
    version = cache.get('products_cache_version') or 0
    return f'products_v{version}'

def invalidate_products_cache():
    version = cache.get('products_cache_version') or 0
    cache.set('products_cache_version', version + 1)
```

#### 2.2.3 问题：Redis 连接失败

**现象：**
```
redis.exceptions.ConnectionError: Error 10061 connecting to localhost:6379
```

**原因：**
- Redis 服务未启动
- Redis 端口被防火墙阻止
- 配置错误的 Redis URL

**排查步骤：**

1. **检查 Redis 服务状态：**
```powershell
# Windows 检查服务
Get-Service Redis

# 检查端口
netstat -ano | findstr :6379

# 启动 Redis
redis-server --service-start
```

2. **测试 Redis 连接：**
```powershell
redis-cli -h localhost -p 6379 ping
```

3. **检查应用配置：**
```python
# app/config.py
CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL", "redis://localhost:6379/0")
```

**解决方案：**

```python
# 方案 1：添加连接重试
from redis import Redis
from redis.exceptions import ConnectionError
import time

def get_redis_connection():
    max_retries = 3
    for i in range(max_retries):
        try:
            redis_client = Redis.from_url(
                "redis://localhost:6379/0",
                socket_connect_timeout=5
            )
            redis_client.ping()
            return redis_client
        except ConnectionError as e:
            if i == max_retries - 1:
                raise
            time.sleep(2 ** i)  # 指数退避

# 方案 2：使用连接池
from redis import ConnectionPool

pool = ConnectionPool.from_url(
    "redis://localhost:6379/0",
    max_connections=50,
    socket_connect_timeout=5
)

# 方案 3：降级处理
from flask_caching import Cache

def init_cache_with_fallback(app):
    try:
        cache = Cache(config={
            "CACHE_TYPE": "RedisCache",
            "CACHE_REDIS_URL": "redis://localhost:6379/0"
        })
        cache.init_app(app)
        cache.cache._client.ping()
    except Exception:
        # Redis 不可用，降级为内存缓存
        cache = Cache(config={"CACHE_TYPE": "SimpleCache"})
        cache.init_app(app)
    return cache
```

### 2.3 异步任务问题

#### 2.3.1 问题：Celery Worker 未启动

**现象：**
- 任务一直处于 PENDING 状态
- 日志显示任务未执行

**原因：**
- Celery Worker 进程未运行
- Broker 配置错误
- 任务路由配置错误

**排查步骤：**

1. **检查 Celery Worker 状态：**
```powershell
# 启动 Worker
python celery_app.py worker -l info

# 检查 Worker 是否运行
Get-Process | Where-Object {$_.Name -like "*celery*"}
```

2. **查看 Celery 配置：**
```python
# celery_app.py
celery_app.conf.update(
    broker_url="redis://localhost:6379/1",
    result_backend="redis://localhost:6379/2",
)
```

3. **测试任务派发：**
```python
from app.tasks.wechat_tasks import scan_wechat_messages

# 同步执行
result = scan_wechat_messages.delay(limit=5)
print(f"任务 ID: {result.id}")

# 获取结果
print(f"任务状态：{result.status}")
```

**解决方案：**

```python
# 方案 1：正确启动 Worker
# 开发环境
python celery_app.py worker -l info --pool=solo

# 生产环境
celery -A celery_app worker -l info -c 4

# 方案 2：配置自动发现
# celery_app.py
celery_app.autodiscover_tasks(['app.tasks'])

# 方案 3：添加任务路由
celery_app.conf.task_routes = {
    'app.tasks.wechat_tasks.*': {'queue': 'wechat'},
    'app.tasks.shipment_tasks.*': {'queue': 'shipment'},
}

# 启动特定队列的 Worker
celery -A celery_app worker -Q wechat -l info
```

#### 2.3.2 问题：任务执行失败

**现象：**
```
Task app.tasks.wechat_tasks.process_wechat_message raised exception
```

**原因：**
- 任务代码逻辑错误
- 依赖服务不可用
- 数据格式不正确

**排查步骤：**

1. **查看任务日志：**
```powershell
# Worker 日志会显示详细错误
# 查找类似以下的错误信息
[ERROR/MainProcess] Task handler raised error
```

2. **检查任务定义：**
```python
# app/tasks/wechat_tasks.py
@celery_app.task(bind=True, max_retries=3)
def process_wechat_message(self, message_data):
    try:
        # 任务逻辑
        pass
    except Exception as e:
        logger.exception(f"处理失败：{e}")
        # 重试
        self.retry(exc=e, countdown=60)
```

3. **手动执行任务测试：**
```python
from app.tasks.wechat_tasks import process_wechat_message

# 直接调用（同步）
test_data = {"message_id": "test123"}
try:
    result = process_wechat_message(test_data)
    print(f"执行结果：{result}")
except Exception as e:
    print(f"执行失败：{e}")
```

**解决方案：**

```python
# 方案 1：完善异常处理
@celery_app.task(bind=True, max_retries=3)
def process_wechat_message(self, message_data):
    try:
        from app.services.wechat_task_service import WechatTaskService
        service = WechatTaskService()
        result = service.process_message(message_data.get("id"))
        return result
    except KeyError as e:
        logger.error(f"数据格式错误：{e}")
        # 数据错误不重试
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception(f"处理失败：{e}")
        # 重试
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

# 方案 2：添加任务超时
@celery_app.task(bind=True, max_retries=3, time_limit=300)
def long_running_task(self):
    # 任务必须在 300 秒内完成
    pass

# 方案 3：记录任务结果
@celery_app.task(bind=True)
def process_with_result(self, data):
    try:
        result = process_data(data)
        # 保存结果到数据库
        save_task_result(self.request.id, result)
        return result
    except Exception as e:
        # 保存错误信息
        save_task_error(self.request.id, str(e))
        raise
```

#### 2.3.3 问题：任务堆积

**现象：**
- 队列中有大量待处理任务
- Worker 处理速度跟不上任务产生速度

**原因：**
- Worker 数量不足
- 任务处理时间过长
- 任务产生速度过快

**排查步骤：**

1. **查看队列长度：**
```powershell
# 查看活跃任务
celery -A celery_app inspect active

# 查看队列统计
celery -A celery_app inspect stats
```

2. **监控任务处理时间：**
```python
from celery.signals import task_received, task_succeeded
import time
import logging

logger = logging.getLogger(__name__)

@task_received.connect
def task_received_handler(sender=None, **kwargs):
    logger.info(f"任务接收：{sender.name}")

@task_succeeded.connect
def task_succeeded_handler(sender=None, retval=None, **kwargs):
    logger.info(f"任务完成：{sender.name}, 结果：{retval}")
```

**解决方案：**

```python
# 方案 1：增加 Worker 数量
# 启动多个 Worker 进程
celery -A celery_app worker -c 4 -l info  # 4 个并发

# 方案 2：优化任务处理
@celery_app.task(bind=True)
def optimize_task(self, data):
    # 批量处理
    batch_size = 100
    for i in range(0, len(data), batch_size):
        batch = data[i:i+batch_size]
        process_batch(batch)

# 方案 3：任务限流
celery_app.conf.task_default_rate_limit = '10/m'  # 每分钟最多 10 个任务

# 方案 4：使用定时任务
celery_app.conf.beat_schedule = {
    'cleanup-old-tasks': {
        'task': 'app.tasks.wechat_tasks.cleanup_old_tasks',
        'schedule': 86400.0,  # 每天执行一次
    },
}
```

### 2.4 前端问题

#### 2.4.1 问题：API 请求失败

**现象：**
- 浏览器控制台显示 CORS 错误
- Network 面板显示 404 或 500 错误

**原因：**
- CORS 配置错误
- API 路径错误
- 后端服务未启动

**排查步骤：**

1. **检查浏览器控制台：**
```javascript
// F12 -> Console
// 查看错误信息
// 常见错误：
// - Access to fetch at 'http://localhost:5000/api/products' from origin 'http://localhost:3000' has been blocked by CORS policy
// - GET http://localhost:5000/api/products 404 (NOT FOUND)
```

2. **检查 Network 请求：**
```
F12 -> Network -> 筛选 XHR
查看：
- Request URL: 请求地址是否正确
- Request Method: GET/POST 是否正确
- Status Code: 状态码
- Response: 响应内容
```

3. **验证后端服务：**
```powershell
# 测试 API 是否可访问
curl http://localhost:5000/api/products

# 检查服务状态
netstat -ano | findstr :5000
```

**解决方案：**

```python
# 方案 1：配置 CORS
# app/__init__.py
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://localhost:5173"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# 方案 2：前端代理配置
# frontend/vite.config.js
export default {
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
}

# 方案 3：前端错误处理
// frontend/src/api/index.js
async function request(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('请求失败:', error);
    throw error;
  }
}
```

#### 2.4.2 问题：页面加载缓慢

**现象：**
- 首屏加载时间超过 3 秒
- 资源文件加载慢

**原因：**
- 资源文件过大
- 未启用压缩
- 网络请求过多

**排查步骤：**

1. **使用 Performance 面板分析：**
```
F12 -> Performance -> 录制 -> 刷新页面
查看：
- Loading: 资源加载时间
- Rendering: 渲染时间
- Scripting: 脚本执行时间
```

2. **检查资源大小：**
```
F12 -> Network -> 刷新页面
查看：
- 每个文件的大小
- 加载时间
- 是否有失败的资源
```

3. **检查 bundle 大小：**
```powershell
cd frontend
npm run build
# 查看输出的文件大小
```

**解决方案：**

```javascript
// 方案 1：代码分割
// frontend/src/App.vue
const ProductsView = defineAsyncComponent(() => 
  import('./views/ProductsView.vue')
);

// 方案 2：启用 Gzip 压缩
# Nginx 配置
gzip on;
gzip_types text/plain text/css application/json application/javascript;
gzip_min_length 1000;

// 方案 3：图片懒加载
// frontend/src/components/ProductImage.vue
<template>
  <img 
    :data-src="imageUrl" 
    loading="lazy" 
    class="lazy-load"
  />
</template>

// 方案 4：使用 CDN
// vite.config.js
export default {
  build: {
    rollupOptions: {
      external: ['vue', 'vue-router'],
      output: {
        globals: {
          vue: 'Vue',
          'vue-router': 'VueRouter'
        }
      }
    }
  }
}
```

#### 2.4.3 问题：Vue 组件渲染错误

**现象：**
- 页面显示空白
- 控制台显示组件渲染错误

**原因：**
- 组件数据未正确传递
- 生命周期钩子使用错误
- 响应式数据未正确定义

**排查步骤：**

1. **使用 Vue DevTools：**
```
安装 Vue DevTools 扩展
F12 -> Vue -> Components
查看：
- 组件树结构
- 组件数据（Props、Data）
- 事件监听器
```

2. **检查控制台错误：**
```javascript
// 常见错误：
// - Cannot read property 'xxx' of undefined
// - Property "xxx" was accessed during render but is not defined on instance
// - Invalid prop: type check failed
```

3. **添加调试日志：**
```javascript
// frontend/src/components/ProductList.vue
export default {
  props: {
    products: Array
  },
  created() {
    console.log('组件创建，props:', this.products);
  },
  render() {
    console.log('组件渲染，products:', this.products);
    return h('div', this.products.map(p => h('span', p.name)));
  }
}
```

**解决方案：**

```vue
<!-- 方案 1：正确定义响应式数据 -->
<template>
  <div class="product-list">
    <div v-for="product in products" :key="product.id">
      {{ product.name }}
    </div>
  </div>
</template>

<script>
export default {
  props: {
    products: {
      type: Array,
      required: true,
      default: () => []
    }
  },
  data() {
    return {
      loading: false,
      error: null
    }
  },
  async created() {
    this.loading = true;
    try {
      const response = await this.$api.getProducts();
      this.products = response.data;
    } catch (error) {
      this.error = error.message;
    } finally {
      this.loading = false;
    }
  }
}
</script>

<!-- 方案 2：使用计算属性 -->
<script>
export default {
  computed: {
    filteredProducts() {
      if (!this.products) return [];
      return this.products.filter(p => p.is_active);
    }
  }
}
</script>

<!-- 方案 3：添加错误边界 -->
<template>
  <div>
    <div v-if="loading">加载中...</div>
    <div v-else-if="error">错误：{{ error }}</div>
    <div v-else-if="products.length === 0">暂无数据</div>
    <ProductList v-else :products="products" />
  </div>
</template>
```

### 2.5 API 接口问题

#### 2.5.1 问题：404 Not Found

**现象：**
```json
{
  "success": false,
  "message": "未找到资源"
}
```

**原因：**
- 路由未注册
- URL 路径错误
- HTTP 方法错误

**排查步骤：**

1. **查看已注册的路由：**
```python
# 在 Python 中查看所有路由
from app import create_app

app = create_app()
with app.app_context():
    for rule in app.url_map.iter_rules():
        print(f"{rule.methods} {rule.rule}")
```

2. **检查蓝图注册：**
```python
# app/routes/__init__.py
def register_blueprints(app):
    from .products import products_bp
    from .customers import customers_bp
    from .excel_extract import excel_extract_bp
    
    app.register_blueprint(products_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(excel_extract_bp)
```

3. **使用 Swagger 文档验证：**
```
访问 http://localhost:5000/apidocs
查看 API 路径是否正确
```

**解决方案：**

```python
# 方案 1：正确注册路由
# app/routes/products.py
from flask import Blueprint

products_bp = Blueprint('products', __name__, url_prefix='/api/products')

@products_bp.route('', methods=['GET'])
def get_products():
    return jsonify({"success": True})

# app/routes/__init__.py
def register_blueprints(app):
    from .products import products_bp
    app.register_blueprint(products_bp)

# 方案 2：添加 404 错误处理
# app/routes/errors.py
from flask import jsonify

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "message": "资源不存在"
        }), 404

# 方案 3：使用 Flask-RESTful 规范路由
from flask_restful import Resource, Api

api = Api(app)

class ProductList(Resource):
    def get(self):
        return {"success": True, "data": []}

api.add_resource(ProductList, '/api/products')
```

#### 2.5.2 问题：500 Internal Server Error

**现象：**
```json
{
  "success": false,
  "message": "服务器内部错误"
}
```

**原因：**
- 代码逻辑错误
- 数据库操作失败
- 依赖服务异常

**排查步骤：**

1. **查看应用日志：**
```powershell
Get-Content E:\FHD\XCAGI\data\logs\debug_ndjson.log -Tail 50 -Wait
```

2. **启用详细错误信息：**
```python
# 开发环境
app.config['PROPAGATE_EXCEPTIONS'] = True
```

3. **使用 try-except 捕获异常：**
```python
from flask import jsonify
import logging

logger = logging.getLogger(__name__)

@products_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    try:
        from app.services.products_service import ProductsService
        service = ProductsService()
        result = service.get_product(product_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.exception(f"获取产品失败：{e}")
        return jsonify({
            "success": False,
            "message": f"查询失败：{str(e)}"
        }), 500
```

**解决方案：**

```python
# 方案 1：全局异常处理
from flask import jsonify
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    @app.errorhandler(Exception)
    def handle_exception(e):
        # 记录日志
        app.logger.exception(f"未处理的异常：{e}")
        
        # HTTP 异常
        if isinstance(e, HTTPException):
            return jsonify({
                "success": False,
                "message": e.description
            }), e.code
        
        # 其他异常
        return jsonify({
            "success": False,
            "message": "服务器内部错误"
        }), 500

# 方案 2：自定义异常类
class AppException(Exception):
    def __init__(self, message, status_code=500):
        self.message = message
        self.status_code = status_code

@app.errorhandler(AppException)
def handle_app_exception(error):
    return jsonify({
        "success": False,
        "message": error.message
    }), error.status_code

# 方案 3：添加请求验证
from functools import wraps

def validate_request(schema):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, jsonify
            
            data = request.get_json()
            if not data:
                return jsonify({
                    "success": False,
                    "message": "请求数据不能为空"
                }), 400
            
            # 验证数据格式
            for key, value_type in schema.items():
                if key not in data:
                    return jsonify({
                        "success": False,
                        "message": f"缺少必需字段：{key}"
                    }), 400
                if not isinstance(data[key], value_type):
                    return jsonify({
                        "success": False,
                        "message": f"字段类型错误：{key}"
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 使用示例
@products_bp.route('', methods=['POST'])
@validate_request({'product_name': str, 'price': (int, float)})
def create_product():
    data = request.json
    # 处理逻辑
```

#### 2.5.3 问题：请求参数验证失败

**现象：**
```json
{
  "success": false,
  "message": "请提供 file_path 参数"
}
```

**原因：**
- 缺少必需参数
- 参数类型错误
- 参数格式不正确

**排查步骤：**

1. **检查 API 文档：**
```
访问 Swagger 文档查看必需参数
http://localhost:5000/apidocs
```

2. **使用 curl 测试：**
```bash
# 正确的请求
curl -X POST http://localhost:5000/api/excel/data/extract ^
  -H "Content-Type: application/json" ^
  -d "{\"file_path\": \"E:/test.xlsx\"}"

# 缺少必需参数
curl -X POST http://localhost:5000/api/excel/data/extract ^
  -H "Content-Type: application/json" ^
  -d "{}"
```

**解决方案：**

```python
# 方案 1：使用 Marshmallow 验证
from marshmallow import Schema, fields, validates, ValidationError

class ExtractRequestSchema(Schema):
    file_path = fields.Str(required=True)
    sheet_name = fields.Str()
    header_row = fields.Int(missing=1)
    
    @validates('file_path')
    def validate_file_path(self, value):
        if not os.path.exists(value):
            raise ValidationError('文件不存在')

# 在路由中使用
@excel_extract_bp.route("/extract", methods=["POST"])
def extract_from_excel():
    schema = ExtractRequestSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({
            "success": False,
            "message": err.messages
        }), 400
    
    # 使用验证后的数据
    result, status = _extract_from_excel(data['file_path'])
    return jsonify(result), status

# 方案 2：使用 Pydantic 验证
from pydantic import BaseModel, Field, validator

class ExtractRequest(BaseModel):
    file_path: str = Field(..., description="文件路径")
    sheet_name: str | None = None
    header_row: int = Field(default=1, ge=1)
    
    @validator('file_path')
    def file_must_exist(cls, v):
        if not os.path.exists(v):
            raise ValueError('文件不存在')
        return v

# 在路由中使用
@excel_extract_bp.route("/extract", methods=["POST"])
def extract_from_excel():
    try:
        data = ExtractRequest(**request.json)
    except ValueError as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 400
    
    result, status = _extract_from_excel(data.file_path)
    return jsonify(result), status
```

---

## 第三章 性能问题排查

### 3.1 慢查询排查

#### 3.1.1 识别慢查询

**方法 1：启用 SQLAlchemy 日志**

```python
# app/config.py
SQLALCHEMY_ECHO = True  # 输出所有 SQL
SQLALCHEMY_RECORD_QUERIES = True  # 记录查询
```

**方法 2：使用性能分析器**

```python
from sqlalchemy import event
import time
import logging

logger = logging.getLogger(__name__)

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 1.0:  # 超过 1 秒的查询
        logger.warning(f"慢查询：{total:.3f}s - {statement}")
```

**方法 3：分析查询执行计划**

```python
from app.db.session import get_db

with get_db() as db:
    # 使用 EXPLAIN
    result = db.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM products WHERE name LIKE '%test%'"
    ).fetchall()
    
    for row in result:
        print(row)
```

#### 3.1.2 优化慢查询

**问题 1：缺少索引**

```sql
-- 查看现有索引
SELECT name FROM sqlite_master WHERE type='index';

-- 添加索引
CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_shipment_created ON shipment_records(created_at);
```

**问题 2：N+1 查询问题**

```python
# 错误示例：N+1 查询
products = db.query(Product).all()
for product in products:
    # 每次循环都查询数据库
    units = db.query(PurchaseUnit).filter(
        PurchaseUnit.product_id == product.id
    ).all()

# 正确示例：使用 JOIN
from sqlalchemy.orm import joinedload

products = db.query(Product).options(
    joinedload(Product.purchase_units)
).all()
```

**问题 3：LIKE 查询优化**

```python
# 低效：全表扫描
products = db.query(Product).filter(
    Product.name.like('%keyword%')
).all()

# 高效：使用全文索引
# 1. 创建 FTS 虚拟表
db.execute("""
    CREATE VIRTUAL TABLE products_fts USING fts5(name, description)
""")

# 2. 同步数据
db.execute("""
    INSERT INTO products_fts(rowid, name, description)
    SELECT id, name, description FROM products
""")

# 3. 使用 FTS 查询
results = db.execute("""
    SELECT * FROM products_fts WHERE products_fts MATCH 'keyword'
""").fetchall()
```

### 3.2 内存泄漏排查

#### 3.2.1 检测内存泄漏

**方法 1：使用 tracemalloc**

```python
import tracemalloc
import logging

logger = logging.getLogger(__name__)

def start_memory_tracking():
    tracemalloc.start()
    
def print_memory_usage():
    current, peak = tracemalloc.get_traced_memory()
    logger.info(f"当前内存：{current / 1024 / 1024:.2f} MB")
    logger.info(f"峰值内存：{peak / 1024 / 1024:.2f} MB")
    
    # 显示占用内存最多的 10 个位置
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    logger.info("内存占用 Top 10:")
    for stat in top_stats[:10]:
        logger.info(stat)

def stop_memory_tracking():
    print_memory_usage()
    tracemalloc.stop()

# 使用示例
start_memory_tracking()
# ... 执行代码 ...
print_memory_usage()
stop_memory_tracking()
```

**方法 2：使用 memory_profiler**

```bash
# 安装
pip install memory-profiler
```

```python
from memory_profiler import profile

@profile
def my_func():
    # 可能的内存泄漏代码
    data = []
    for i in range(10000):
        data.append({'id': i, 'data': 'x' * 1000})
    return data
```

#### 3.2.2 常见内存泄漏场景

**场景 1：全局变量积累数据**

```python
# 错误示例
global_cache = []

def process_data(data):
    global global_cache
    global_cache.append(data)  # 无限增长
    return result

# 正确示例
from collections import OrderedDict

class LRUCache:
    def __init__(self, max_size=1000):
        self.cache = OrderedDict()
        self.max_size = max_size
    
    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def set(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

global_cache = LRUCache(max_size=1000)
```

**场景 2：未关闭的数据库连接**

```python
# 错误示例
def get_all_products():
    db = SessionLocal()
    products = db.query(Product).all()
    # 忘记 db.close()
    return products

# 正确示例
def get_all_products():
    with get_db() as db:
        products = db.query(Product).all()
    return products
```

**场景 3：循环引用**

```python
# 错误示例
class Node:
    def __init__(self):
        self.parent = None
        self.children = []
    
    def add_child(self, child):
        child.parent = self  # 循环引用
        self.children.append(child)

# 正确示例
import weakref

class Node:
    def __init__(self):
        self._parent = None
        self.children = []
    
    @property
    def parent(self):
        return self._parent() if self._parent else None
    
    @parent.setter
    def parent(self, node):
        self._parent = weakref.ref(node)
```

### 3.3 接口响应慢排查

#### 3.3.1 性能分析

**方法 1：使用 Flask-Profiler**

```bash
pip install flask-profiler
```

```python
# app/__init__.py
def create_app():
    app = Flask(__name__)
    
    # 配置性能分析
    app.config['FLASK_PROFILER'] = {
        "enabled": app.config['DEBUG'],
        "storage": {
            "engine": "sqlite",
            "FILE": "/tmp/flask_profiler.db"
        },
        "basicAuth": {
            "enabled": False
        }
    }
    
    from flask_profiler import init
    init(app)
    
    return app
```

**方法 2：自定义性能中间件**

```python
from flask import request, g
import time
import logging

logger = logging.getLogger(__name__)

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        if elapsed > 1.0:  # 超过 1 秒
            logger.warning(
                f"慢请求：{request.method} {request.path} "
                f"耗时：{elapsed:.3f}s"
            )
    return response
```

#### 3.3.2 优化接口响应

**优化 1：异步处理耗时操作**

```python
# 错误示例：同步处理
@products_bp.route('/import', methods=['POST'])
def import_products():
    file = request.files['file']
    # 直接处理大文件，阻塞请求
    process_large_file(file)
    return jsonify({"success": True})

# 正确示例：异步处理
from app.tasks.shipment_tasks import process_import_file

@products_bp.route('/import', methods=['POST'])
def import_products():
    file = request.files['file']
    file_path = save_file(file)
    
    # 派发异步任务
    task = process_import_file.delay(file_path)
    
    return jsonify({
        "success": True,
        "task_id": task.id
    })
```

**优化 2：使用缓存**

```python
from flask_caching import Cache
from app.extensions import cache

@products_bp.route('', methods=['GET'])
@cache.cached(timeout=300, key_prefix='products_list')
def get_products():
    # 查询数据库
    service = ProductsService()
    result = service.get_products()
    return jsonify(result)
```

**优化 3：分页和限制**

```python
# 错误示例：返回所有数据
@products_bp.route('', methods=['GET'])
def get_products():
    products = db.query(Product).all()  # 可能返回数万条
    return jsonify({"data": products})

# 正确示例：分页
@products_bp.route('', methods=['GET'])
def get_products():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)  # 限制最大 100
    
    pagination = db.query(Product).paginate(
        page=page, 
        per_page=per_page,
        error_out=False
    )
    
    return jsonify({
        "data": pagination.items,
        "total": pagination.total,
        "page": page,
        "per_page": per_page
    })
```

**优化 4：使用数据库连接池**

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# 配置连接池
engine = create_engine(
    f"sqlite:///{db_path}",
    poolclass=QueuePool,
    pool_size=20,           # 连接池大小
    max_overflow=40,        # 最大溢出连接数
    pool_timeout=30,        # 获取连接超时
    pool_recycle=1800,      # 连接回收时间（秒）
    pool_pre_ping=True,     # 使用前检查连接
)
```

---

## 第四章 典型错误及解决方案

### 4.1 数据库错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `sqlite3.OperationalError: database is locked` | 数据库被锁定 | 1. 检查未关闭的连接<br>2. 启用 WAL 模式<br>3. 增加超时时间 |
| `sqlalchemy.exc.OperationalError: no such table` | 表不存在 | 1. 运行数据库迁移<br>2. 检查模型定义<br>3. 确认数据库文件 |
| `sqlite3.DatabaseError: disk I/O error` | 磁盘 I/O 错误 | 1. 检查磁盘空间<br>2. 检查文件权限<br>3. 检查磁盘健康状态 |
| `sqlalchemy.exc.IntegrityError: UNIQUE constraint failed` | 唯一约束冲突 | 1. 检查重复数据<br>2. 添加数据验证<br>3. 使用 upsert 操作 |

### 4.2 Redis 错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `redis.exceptions.ConnectionError: Error 10061` | Redis 服务未启动 | 1. 启动 Redis 服务<br>2. 检查防火墙<br>3. 验证配置 |
| `redis.exceptions.TimeoutError: Timeout` | 连接超时 | 1. 增加超时时间<br>2. 检查网络<br>3. 优化 Redis 性能 |
| `redis.exceptions.MemoryError: Command # memory` | 内存不足 | 1. 清理过期 key<br>2. 增加内存限制<br>3. 使用 LRU 策略 |

### 4.3 Celery 错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `celery.exceptions.PendingDeprecationWarning` | 版本兼容性 | 1. 更新 Celery 版本<br>2. 修改配置语法 |
| `kombu.exceptions.OperationalError: Error 10061` | Broker 不可用 | 1. 启动 Redis<br>2. 检查 Broker URL<br>3. 添加重试机制 |
| `celery.exceptions.MaxRetriesExceededError` | 超过最大重试次数 | 1. 增加重试次数<br>2. 修复根本问题<br>3. 添加告警 |

### 4.4 Flask 错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `werkzeug.exceptions.NotFound: 404 Not Found` | 路由不存在 | 1. 检查路由注册<br>2. 验证 URL 路径<br>3. 检查 HTTP 方法 |
| `werkzeug.exceptions.InternalServerError: 500` | 服务器内部错误 | 1. 查看日志<br>2. 启用调试模式<br>3. 添加异常处理 |
| `flask_cors.extension.CORSNotRunningError` | CORS 未配置 | 1. 安装 flask-cors<br>2. 配置 CORS<br>3. 检查 origins 设置 |

### 4.5 前端错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `Access to fetch has been blocked by CORS policy` | CORS 策略阻止 | 1. 配置后端 CORS<br>2. 使用代理服务器<br>3. 检查 origins |
| `TypeError: Cannot read property 'xxx' of undefined` | 数据未定义 | 1. 添加默认值<br>2. 检查 API 响应<br>3. 使用可选链 |
| `ReferenceError: xxx is not defined` | 变量未定义 | 1. 检查变量声明<br>2. 检查作用域<br>3. 检查导入语句 |

---

## 第五章 应急处理流程

### 5.1 系统回滚流程

#### 5.1.1 代码回滚

**场景：** 新版本上线后出现严重 bug

**步骤：**

```powershell
# 1. 停止当前服务
# 如果使用 IIS Express 或其他服务管理器，先停止服务

# 2. 切换到上一个稳定版本
cd E:\FHD\XCAGI
git log --oneline -10  # 查看最近的提交
git checkout <stable_commit_hash>

# 3. 恢复依赖
pip install -r requirements.txt

# 4. 回滚数据库（如果需要）
alembic downgrade -1  # 回滚一个版本
# 或
alembic downgrade <target_version>

# 5. 重启服务
python run.py
```

#### 5.1.2 数据库回滚

**场景：** 数据错误或数据损坏

**步骤：**

```powershell
# 1. 备份当前数据库（即使损坏也要备份）
Copy-Item E:\FHD\XCAGI\products.db E:\FHD\XCAGI\products.db.backup.corrupt

# 2. 从备份恢复
Copy-Item E:\FHD\XCAGI\products.db.backup E:\FHD\XCAGI\products.db

# 3. 验证数据
sqlite3 E:\FHD\XCAGI\products.db "SELECT COUNT(*) FROM products;"

# 4. 重启应用
python run.py
```

#### 5.1.3 配置回滚

**场景：** 配置错误导致系统异常

**步骤：**

```powershell
# 1. 查看当前配置
Get-Content E:\FHD\XCAGI\app\config.py

# 2. 恢复配置文件
git checkout HEAD -- app/config.py

# 3. 验证配置
python -c "from app.config import Config; print(Config.LOG_LEVEL)"

# 4. 重启应用
python run.py
```

### 5.2 数据恢复流程

#### 5.2.1 从备份恢复

**前提：** 有定期备份机制

**步骤：**

```powershell
# 1. 停止应用
# 确保没有进程正在使用数据库

# 2. 找到最近的备份
Get-ChildItem E:\FHD\XCAGI\*.backup | Sort-Object LastWriteTime -Descending | Select-Object -First 5

# 3. 恢复数据库
$backup_file = "E:\FHD\XCAGI\products.db.backup.20260317"
$db_file = "E:\FHD\XCAGI\products.db"

Copy-Item $db_file "$db_file.corrupt"  # 备份损坏的数据库
Copy-Item $backup_file $db_file

# 4. 验证恢复
sqlite3 $db_file ".tables"
sqlite3 $db_file "SELECT COUNT(*) FROM products;"

# 5. 重启应用
python run.py
```

#### 5.2.2 使用 SQLite 恢复工具

**场景：** 数据库文件损坏

**步骤：**

```powershell
# 1. 尝试导出 SQL
sqlite3 products.db ".dump" > recovery.sql

# 2. 创建新数据库
sqlite3 products_new.db < recovery.sql

# 3. 验证新数据库
sqlite3 products_new.db ".tables"
sqlite3 products_new.db "SELECT COUNT(*) FROM products;"

# 4. 替换原数据库
Move-Item products.db products.db.old
Move-Item products_new.db products.db
```

#### 5.2.3 恢复特定数据

**场景：** 误删除部分数据

**步骤：**

```python
# 1. 从备份数据库导出删除的数据
import sqlite3

# 连接备份数据库
backup_conn = sqlite3.connect('products.db.backup')
backup_cursor = backup_conn.cursor()

# 查询要恢复的数据
backup_cursor.execute("""
    SELECT * FROM products 
    WHERE created_at > '2026-03-16'
""")
deleted_data = backup_cursor.fetchall()

# 2. 恢复到生产数据库
prod_conn = sqlite3.connect('products.db')
prod_cursor = prod_conn.cursor()

# 插入数据
for row in deleted_data:
    try:
        prod_cursor.execute("""
            INSERT OR IGNORE INTO products 
            (id, name, price, description, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, row)
    except sqlite3.IntegrityError:
        print(f"跳过已存在的记录：{row[0]}")

prod_conn.commit()
prod_conn.close()
backup_conn.close()

print(f"恢复了 {len(deleted_data)} 条记录")
```

### 5.3 服务重启流程

#### 5.3.1 开发环境重启

**步骤：**

```powershell
# 1. 停止当前服务
# 在运行 run.py 的终端按 Ctrl+C

# 2. 清理 Python 进程
Get-Process python | Where-Object {$_.Path -like "*XCAGI*"} | Stop-Process -Force

# 3. 清理缓存文件
Remove-Item E:\FHD\XCAGI\app\__pycache__\* -Recurse -Force
Remove-Item E:\FHD\XCAGI\*.db-shm -Force
Remove-Item E:\FHD\XCAGI\*.db-wal -Force

# 4. 重启服务
cd E:\FHD\XCAGI
python run.py
```

#### 5.3.2 Celery Worker 重启

**步骤：**

```powershell
# 1. 停止 Worker
# 在 Worker 终端按 Ctrl+C

# 2. 清理 Worker 进程
Get-Process | Where-Object {$_.Name -like "*celery*"} | Stop-Process -Force

# 3. 清理 Redis 队列（可选）
redis-cli FLUSHDB  # 警告：这会清空当前数据库

# 4. 重启 Worker
python celery_app.py worker -l info --pool=solo
```

#### 5.3.3 完全重启（所有服务）

**步骤：**

```powershell
# 1. 停止所有 Python 进程
Get-Process python | Stop-Process -Force

# 2. 停止 Redis 服务
redis-server --service-stop

# 3. 等待 5 秒
Start-Sleep -Seconds 5

# 4. 启动 Redis 服务
redis-server --service-start

# 5. 验证 Redis
redis-cli ping

# 6. 启动 Flask 应用
cd E:\FHD\XCAGI
Start-Process python -ArgumentList "run.py"

# 7. 启动 Celery Worker
Start-Process python -ArgumentList "celery_app.py worker -l info --pool=solo"

# 8. 验证服务
Start-Sleep -Seconds 5
curl http://localhost:5000/api/tools/test
```

#### 5.3.4 重启检查清单

重启后验证以下项目：

- [ ] Flask 应用正常启动（无错误日志）
- [ ] 数据库连接正常
- [ ] Redis 服务正常
- [ ] Celery Worker 正常运行
- [ ] API 接口可访问
- [ ] 前端页面可访问
- [ ] 核心功能测试通过

**验证脚本：**

```python
# verify_startup.py
import requests
import sys

def check_service(url, name):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✓ {name} 正常")
            return True
        else:
            print(f"✗ {name} 异常：{response.status_code}")
            return False
    except Exception as e:
        print(f"✗ {name} 失败：{e}")
        return False

checks = [
    ("http://localhost:5000/api/tools/test", "工具 API"),
    ("http://localhost:5000/api/products", "产品 API"),
    ("http://localhost:5000/apidocs", "Swagger 文档"),
]

all_passed = all(check_service(url, name) for url, name in checks)

if not all_passed:
    sys.exit(1)

print("\n✓ 所有服务启动正常")
```

---

## 附录

### A. 常用命令速查

```powershell
# 日志查看
Get-Content E:\FHD\XCAGI\data\logs\debug_ndjson.log -Wait -Tail 50

# 数据库检查
sqlite3 E:\FHD\XCAGI\products.db ".tables"

# Redis 检查
redis-cli ping
redis-cli info

# 进程管理
Get-Process python
Get-Process | Where-Object {$_.Name -like "*celery*"}

# 网络检查
netstat -ano | findstr :5000
netstat -ano | findstr :6379

# 服务重启
python run.py
python celery_app.py worker -l info --pool=solo
```

### B. 配置文件位置

| 配置文件 | 路径 | 说明 |
|---------|------|------|
| 应用配置 | `app/config.py` | Flask 应用配置 |
| Celery 配置 | `celery_app.py` | Celery 任务配置 |
| 路由配置 | `app/routes/__init__.py` | 蓝图注册 |
| 扩展配置 | `app/extensions.py` | Flask 扩展 |
| 数据库模型 | `app/db/models/` | ORM 模型定义 |

### C. 关键目录结构

```
E:\FHD\XCAGI\
├── app/                      # 应用代码
│   ├── config.py            # 配置文件
│   ├── routes/              # 路由定义
│   ├── services/            # 业务逻辑
│   ├── tasks/               # Celery 任务
│   └── utils/               # 工具函数
├── data/
│   └── logs/                # 日志文件
│       └── debug_ndjson.log
├── data/                    # 数据文件
│   └── *.db                 # SQLite 数据库
├── frontend/                # 前端代码
├── templates/               # HTML 模板
├── celery_app.py           # Celery 配置
└── run.py                  # 启动脚本
```

### D. 紧急联系人

- 技术支持：查看项目 README.md
- 问题反馈：提交 GitHub Issue
- 文档更新：更新此文件并提交 PR

---

**文档版本历史：**

| 版本 | 日期 | 更新内容 | 作者 |
|------|------|---------|------|
| 1.0.0 | 2026-03-17 | 初始版本 | XCAGI 团队 |
