
"""
深圳奇士美定制 PRO Mod - 问答包管理器
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_QA_PACKAGES = {
    "default": {
        "id": "default",
        "name": "深圳奇士美标准问答包",
        "description": "深圳奇士美油漆业务标准问答模板",
        "opening_line": "您好这里是深圳奇士美油漆，欢迎订购！请问您是哪个购买单位呢？",
        "qa_pairs": [
            {
                "question": "你们有什么油漆产品？",
                "answer": "我们主要经营各类工业油漆、木器漆、防腐漆等，请问您需要哪种类型的产品？"
            },
            {
                "question": "价格怎么样？",
                "answer": "我们的产品价格根据不同规格和数量有所不同，请问您需要多少量呢？我可以给您详细报价。"
            },
            {
                "question": "可以送货吗？",
                "answer": "可以的，我们提供送货上门服务，请问您的收货地址是哪里？"
            },
            {
                "question": "有现货吗？",
                "answer": "大部分产品都有现货，请问您具体需要什么产品？我帮您确认库存情况。"
            }
        ],
        "created_at": "2026-03-30",
        "updated_at": "2026-03-30"
    }
}


class QAPackageManager:
    """问答包管理器"""

    def __init__(self, mod_path: str):
        self._mod_path = Path(mod_path)
        self._data_dir = self._mod_path / "data"
        self._qa_file = self._data_dir / "qa_packages.json"
        self._packages: Dict[str, dict] = {}
        self._init_data()

    def _init_data(self):
        """初始化数据目录和文件"""
        try:
            self._data_dir.mkdir(exist_ok=True)
            
            if not self._qa_file.exists():
                self._save_packages(_DEFAULT_QA_PACKAGES)
                logger.info(f"[奇士美 PRO] 创建默认问答包: {self._qa_file}")
            else:
                self._load_packages()
                logger.info(f"[奇士美 PRO] 加载问答包: {len(self._packages)} 个")
        except Exception as e:
            logger.error(f"[奇士美 PRO] 问答包初始化失败: {e}")
            self._packages = _DEFAULT_QA_PACKAGES.copy()

    def _load_packages(self):
        """从文件加载问答包"""
        try:
            with open(self._qa_file, "r", encoding="utf-8") as f:
                self._packages = json.load(f)
        except Exception as e:
            logger.error(f"[奇士美 PRO] 加载问答包失败: {e}")
            self._packages = _DEFAULT_QA_PACKAGES.copy()

    def _save_packages(self, packages: Optional[Dict[str, dict]] = None):
        """保存问答包到文件"""
        try:
            data = packages if packages is not None else self._packages
            with open(self._qa_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[奇士美 PRO] 保存问答包失败: {e}")
            raise

    def get_all_packages(self) -> List[dict]:
        """获取所有问答包"""
        return list(self._packages.values())

    def get_package(self, package_id: str) -> Optional[dict]:
        """获取单个问答包"""
        return self._packages.get(package_id)

    def create_package(self, package_data: dict) -> dict:
        """创建新问答包"""
        from datetime import datetime
        
        package_id = package_data.get("id", f"package_{int(datetime.now().timestamp())}")
        now = datetime.now().isoformat()
        
        package = {
            "id": package_id,
            "name": package_data.get("name", "未命名问答包"),
            "description": package_data.get("description", ""),
            "opening_line": package_data.get("opening_line", ""),
            "qa_pairs": package_data.get("qa_pairs", []),
            "created_at": now,
            "updated_at": now
        }
        
        self._packages[package_id] = package
        self._save_packages()
        logger.info(f"[奇士美 PRO] 创建问答包: {package_id}")
        return package

    def update_package(self, package_id: str, package_data: dict) -> Optional[dict]:
        """更新问答包"""
        if package_id not in self._packages:
            return None
        
        from datetime import datetime
        
        package = self._packages[package_id].copy()
        
        if "name" in package_data:
            package["name"] = package_data["name"]
        if "description" in package_data:
            package["description"] = package_data["description"]
        if "opening_line" in package_data:
            package["opening_line"] = package_data["opening_line"]
        if "qa_pairs" in package_data:
            package["qa_pairs"] = package_data["qa_pairs"]
        
        package["updated_at"] = datetime.now().isoformat()
        
        self._packages[package_id] = package
        self._save_packages()
        logger.info(f"[奇士美 PRO] 更新问答包: {package_id}")
        return package

    def delete_package(self, package_id: str) -> bool:
        """删除问答包"""
        if package_id not in self._packages:
            return False
        
        del self._packages[package_id]
        self._save_packages()
        logger.info(f"[奇士美 PRO] 删除问答包: {package_id}")
        return True

    def reset_package(self, package_id: str) -> Optional[dict]:
        """重置问答包为默认"""
        if package_id == "default" and "default" in _DEFAULT_QA_PACKAGES:
            self._packages[package_id] = _DEFAULT_QA_PACKAGES["default"].copy()
            self._save_packages()
            logger.info(f"[奇士美 PRO] 重置问答包: {package_id}")
            return self._packages[package_id]
        return None


_qa_manager = None


def get_qa_package_manager() -> QAPackageManager:
    """获取问答包管理器单例"""
    global _qa_manager
    if _qa_manager is None:
        mod_path = Path(__file__).parent.parent
        _qa_manager = QAPackageManager(str(mod_path))
    return _qa_manager

# 4243342

