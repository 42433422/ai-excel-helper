# -*- coding: utf-8 -*-
"""
RASA NLU 模型训练脚本

使用方法:
    python train_rasa_model.py

训练完成后，模型会保存在 rasa/models/ 目录下
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RASA_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(RASA_DIR)
MODELS_DIR = os.path.join(RASA_DIR, "models")


def check_rasa_installed():
    """检查 RASA 是否已安装"""
    try:
        import rasa
        logger.info(f"RASA 版本: {rasa.__version__}")
        return True
    except ImportError:
        logger.error("RASA 未安装，请运行: pip install rasa")
        return False


def train_nlu_model(config_path: str, nlu_data: str, output: str, force: bool = False):
    """
    训练 RASA NLU 模型

    Args:
        config_path: config.yml 路径
        nlu_data: nlu.yml 路径
        output: 输出目录
        force: 是否强制重新训练
    """
    cmd = [
        sys.executable, "-m", "rasa", "train", "nlu",
        "--config", config_path,
        "--nlu", nlu_data,
        "--output", output
    ]

    if force:
        cmd.append("--force")

    logger.info(f"执行命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("模型训练成功!")
            logger.info(result.stdout)
        else:
            logger.error("模型训练失败!")
            logger.error(result.stderr)
            return False
        return True
    except Exception as e:
        logger.error(f"训练过程出错: {e}")
        return False


def test_nlu_model(model_path: str):
    """
    测试 NLU 模型

    Args:
        model_path: 模型路径
    """
    test_messages = [
        "生成发货单",
        "查看客户列表",
        "你好",
        "不要生成发货单",
        "打印标签",
    ]

    cmd = [
        sys.executable, "-m", "rasa", "parse",
        "--model", model_path,
        "--text"
    ]

    logger.info("\n测试 NLU 模型:")

    for msg in test_messages:
        logger.info(f"\n输入: {msg}")
        try:
            result = subprocess.run(
                cmd + [msg],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info(f"输出: {result.stdout}")
            else:
                logger.error(f"错误: {result.stderr}")
        except Exception as e:
            logger.error(f"测试失败: {e}")


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("RASA NLU 模型训练脚本")
    logger.info("=" * 50)

    if not check_rasa_installed():
        sys.exit(1)

    config_path = os.path.join(RASA_DIR, "config.yml")
    nlu_data = os.path.join(RASA_DIR, "data", "nlu.yml")

    if not os.path.exists(config_path):
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)

    if not os.path.exists(nlu_data):
        logger.error(f"训练数据不存在: {nlu_data}")
        sys.exit(1)

    os.makedirs(MODELS_DIR, exist_ok=True)

    logger.info(f"\n配置: {config_path}")
    logger.info(f"训练数据: {nlu_data}")
    logger.info(f"输出目录: {MODELS_DIR}")

    success = train_nlu_model(config_path, nlu_data, MODELS_DIR, force=True)

    if success:
        logger.info("\n训练完成! 可以使用以下方式加载模型:")
        logger.info("1. 嵌入式模式:")
        logger.info(f"   rasa_nlu_service = RasaNLUService(model_path='{MODELS_DIR}/<model_name>')")
        logger.info("2. 服务器模式:")
        logger.info("   rasa run --enable-api --models models/")
        logger.info("   然后调用: RasaNLUService(rasa_url='http://localhost:5005', use_server=True)")


if __name__ == "__main__":
    main()
