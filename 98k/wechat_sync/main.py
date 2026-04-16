"""
微信数据库解密与消息同步 - 一键启动工具
整合密钥提取、数据库解密、消息同步全流程
"""
import os
import sys
import argparse
import subprocess
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, save_config, update_config


def print_banner():
    """打印启动横幅"""
    print("=" * 70)
    print("  微信数据库解密与消息同步系统")
    print("  WeChat DB Decrypt & Message Sync Tool")
    print("=" * 70)
    print()


def check_dependencies():
    """检查依赖是否安装"""
    required = ['pycryptodome', 'zstandard', 'pymem', 'psutil']
    missing = []
    
    for pkg in required:
        try:
            if pkg == 'pycryptodome':
                __import__('Crypto')
            elif pkg == 'zstandard':
                __import__('zstandard')
            elif pkg == 'pymem':
                __import__('pymem')
            elif pkg == 'psutil':
                __import__('psutil')
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print("[!] 缺少依赖包，请先安装:")
        print(f"    pip install {' '.join(missing)}")
        return False
    return True


def extract_keys(args):
    """提取微信数据库密钥"""
    print("[*] 开始提取微信数据库密钥...")
    print("    (需要管理员/root权限)\n")
    
    from key_extractor import main as extract_main
    extract_main()


def decrypt_all(args):
    """解密所有数据库"""
    print("[*] 开始解密所有微信数据库...\n")
    
    from db_decryptor import decrypt_all_databases
    from config import load_config
    
    config = load_config()
    keys_file = config.get('keys_file', 'all_keys.json')
    db_dir = config.get('wechat_db_dir', '')
    out_dir = config.get('decrypted_dir', 'decrypted')
    
    if not os.path.exists(keys_file):
        print(f"[!] 密钥文件不存在: {keys_file}")
        print("    请先运行: python main.py extract")
        return
    
    if not db_dir:
        print("[!] 未配置微信数据目录")
        return
    
    success, failed = decrypt_all_databases(keys_file, db_dir, out_dir)
    print(f"\n[*] 解密完成: {success} 成功, {failed} 失败")


def sync_messages(args):
    """启动消息同步服务"""
    from message_sync import MessageSync
    
    sync = MessageSync()
    
    if args.once:
        # 执行一次同步
        print("[*] 执行单次同步...")
        sync.run_once()
    elif args.stats:
        # 显示统计
        stats = sync.local_db.get_stats()
        print("=" * 60)
        print("  同步统计")
        print("=" * 60)
        for key, value in stats.items():
            print(f"  {key}: {value}")
    elif args.search:
        # 搜索消息
        results = sync.local_db.search_messages(args.search, limit=args.limit)
        print(f"[*] 搜索 '{args.search}' 找到 {len(results)} 条结果:")
        for msg in results:
            print(f"  [{msg['create_time_str']}] {msg['chat_name']}: {msg['content'][:80]}")
    elif args.recent:
        # 显示最近消息
        messages = sync.local_db.get_recent_messages(limit=args.limit)
        print(f"[*] 最近 {len(messages)} 条消息:")
        for msg in messages:
            print(f"  [{msg['create_time_str']}] {msg['chat_name']}: {msg['content'][:80]}")
    else:
        # 持续运行
        sync.run_continuous()


def setup_config(args):
    """配置系统"""
    from config import load_config, save_config
    
    config = load_config()
    
    print("=" * 60)
    print("  系统配置")
    print("=" * 60)
    print()
    
    # 显示当前配置
    print("当前配置:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    print()
    
    if args.reset:
        # 重置配置
        from config import DEFAULT_CONFIG
        save_config(DEFAULT_CONFIG)
        print("[*] 配置已重置为默认值")
        return
    
    if args.key and args.value:
        # 设置特定配置项
        config[args.key] = args.value
        save_config(config)
        print(f"[*] 已设置 {args.key} = {args.value}")
        return
    
    # 交互式配置
    print("请输入新的配置值 (直接回车保持原值):")
    
    wechat_db_dir = input(f"微信数据目录 [{config.get('wechat_db_dir', '')}]: ").strip()
    if wechat_db_dir:
        config['wechat_db_dir'] = wechat_db_dir
    
    poll_interval = input(f"轮询间隔(ms) [{config.get('poll_interval_ms', 100)}]: ").strip()
    if poll_interval:
        config['poll_interval_ms'] = int(poll_interval)
    
    local_db_path = input(f"本地数据库路径 [{config.get('local_db_path', '')}]: ").strip()
    if local_db_path:
        config['local_db_path'] = local_db_path
    
    save_config(config)
    print("\n[*] 配置已保存")


def auto_setup():
    """自动设置流程"""
    print_banner()
    
    if not check_dependencies():
        return
    
    from config import load_config
    from key_extractor import get_wechat_db_dir
    
    config = load_config()
    
    # 自动检测微信数据目录
    if not config.get('wechat_db_dir'):
        db_dir = get_wechat_db_dir()
        if db_dir:
            print(f"[*] 自动检测到微信数据目录: {db_dir}")
            update_config('wechat_db_dir', db_dir)
        else:
            print("[!] 未能自动检测微信数据目录")
            db_dir = input("请手动输入微信数据目录 (db_storage): ").strip()
            if db_dir:
                update_config('wechat_db_dir', db_dir)
    
    print("\n[*] 自动设置完成!")
    print("[*] 接下来请执行:")
    print("    1. python main.py extract  - 提取密钥")
    print("    2. python main.py sync     - 启动消息同步")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='微信数据库解密与消息同步工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 自动设置
  python main.py auto
  
  # 提取密钥
  python main.py extract
  
  # 解密所有数据库
  python main.py decrypt
  
  # 启动消息同步服务
  python main.py sync
  
  # 执行一次同步
  python main.py sync --once
  
  # 查看统计
  python main.py sync --stats
  
  # 搜索消息
  python main.py sync --search "关键词"
  
  # 配置系统
  python main.py config
  python main.py config --key poll_interval_ms --value 200
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # auto 命令
    auto_parser = subparsers.add_parser('auto', help='自动设置')
    
    # extract 命令
    extract_parser = subparsers.add_parser('extract', help='提取微信数据库密钥')
    
    # decrypt 命令
    decrypt_parser = subparsers.add_parser('decrypt', help='解密所有数据库')
    
    # sync 命令
    sync_parser = subparsers.add_parser('sync', help='消息同步服务')
    sync_parser.add_argument('--once', action='store_true', help='执行一次同步')
    sync_parser.add_argument('--stats', action='store_true', help='显示统计')
    sync_parser.add_argument('--search', type=str, help='搜索消息')
    sync_parser.add_argument('--recent', action='store_true', help='显示最近消息')
    sync_parser.add_argument('--limit', type=int, default=20, help='结果数量限制')
    
    # config 命令
    config_parser = subparsers.add_parser('config', help='系统配置')
    config_parser.add_argument('--key', type=str, help='配置项名称')
    config_parser.add_argument('--value', type=str, help='配置项值')
    config_parser.add_argument('--reset', action='store_true', help='重置配置')
    
    args = parser.parse_args()
    
    if args.command == 'auto':
        auto_setup()
    elif args.command == 'extract':
        print_banner()
        extract_keys(args)
    elif args.command == 'decrypt':
        print_banner()
        decrypt_all(args)
    elif args.command == 'sync':
        sync_messages(args)
    elif args.command == 'config':
        setup_config(args)
    else:
        print_banner()
        parser.print_help()
        print("\n[*] 首次使用请运行: python main.py auto")


if __name__ == '__main__':
    main()
