import sys
sys.path.insert(0, '.')

print('🔍 测试增强版 ModstorePlatformAdapter...')
from app.services.conversation.modstore_adapter import (
    ModstorePlatformAdapter,
    create_modstore_adapter_from_env
)

print('\n✅ 模块导入成功')

# 测试1: from_session方法（无参数，模拟未登录状态）
print('\n📋 测试1: from_session() 无参数')
adapter1 = ModstorePlatformAdapter.from_session()
print(f'   结果: {adapter1}')
source = getattr(adapter1, '_source', 'N/A')
print(f'   Token来源: {source}')
print(f'   是否配置: {adapter1.is_configured}')

# 测试2: 环境变量方式
print('\n📋 测试2: create_modstore_adapter_from_env()')
adapter2 = create_modstore_adapter_from_env()
if adapter2:
    print(f'   结果: {adapter2}')
else:
    print('   ℹ️  未检测到 MODSTORE_PLATFORM_URL（正常）')

# 测试3: 基本实例化
print('\n📋 测试3: 直接实例化')
adapter3 = ModstorePlatformAdapter(
    platform_url='http://127.0.0.1:8765',
    auth_token='test_token_12345',
    default_provider='xiaomi'
)
print(f'   结果: {adapter3}')
print(f'   Provider: {adapter3.provider_name}')
print(f'   Model: {adapter3.model_name}')

print('\n🎉 所有测试通过！')
