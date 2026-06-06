"""
MOD Package Management - ZIP packaging, signing, and verification
"""

import hashlib
import json
import logging
import os
import zipfile
from typing import Any

from app.utils.time import utc_now_iso_z

logger = logging.getLogger(__name__)


class ModPackageError(Exception):
    """MOD 打包/解包错误"""


class ModSignatureError(Exception):
    """MOD 签名验证错误"""


def compute_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """计算文件哈希值"""
    hash_func = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def compute_directory_hash(dir_path: str, algorithm: str = "sha256") -> str:
    """计算目录内所有文件的组合哈希值"""
    hash_func = hashlib.new(algorithm)

    file_hashes = []
    for root, _, files in os.walk(dir_path):
        for filename in sorted(files):
            if filename.startswith("."):
                continue
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, dir_path)
            file_hash = compute_file_hash(file_path, algorithm)
            hash_func.update(f"{rel_path}:{file_hash}".encode())

    return hash_func.hexdigest()


class ModPackage:
    """MOD 打包与解包工具"""

    def __init__(self, mod_path: str):
        self.mod_path = os.path.abspath(mod_path)
        self.manifest_path = os.path.join(self.mod_path, "manifest.json")

        if not os.path.isdir(self.mod_path):
            raise ModPackageError(f"MOD 目录不存在：{self.mod_path}")

        if not os.path.isfile(self.manifest_path):
            raise ModPackageError(f"manifest.json 不存在：{self.manifest_path}")

        with open(self.manifest_path, encoding="utf-8") as f:
            self.manifest = json.load(f)

        self.mod_id = self.manifest.get("id", "")
        self.version = self.manifest.get("version", "1.0.0")

        if not self.mod_id:
            raise ModPackageError("manifest.json 缺少必填字段 'id'")

    def create_package(
        self,
        output_dir: str,
        include_signature: bool = True,
        private_key: str | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> str:
        """
        创建 MOD ZIP 包

        Args:
            output_dir: 输出目录
            include_signature: 是否包含签名
            private_key: 私钥路径（用于签名）
            exclude_patterns: 排除的文件模式列表

        Returns:
            生成的 ZIP 文件路径
        """
        os.makedirs(output_dir, exist_ok=True)

        package_name = f"{self.mod_id}-{self.version}.xcmod"
        package_path = os.path.join(output_dir, package_name)

        default_excludes = {
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".git",
            ".gitignore",
            "*.log",
            ".env",
            ".venv",
            "node_modules",
            "dist",
            "*.zip",
            "*.xcmod",
        }

        if exclude_patterns:
            default_excludes.update(exclude_patterns)

        with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(self.mod_path):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, self.mod_path)

                    if self._should_exclude(rel_path, default_excludes):
                        logger.debug(f"Excluding: {rel_path}")
                        continue

                    arcname = os.path.join(self.mod_id, rel_path)
                    zipf.write(file_path, arcname)
                    logger.debug(f"Added: {arcname}")

            if include_signature:
                signature_data = self._generate_signature(private_key)
                zipf.writestr(
                    "META-INF/signature.json",
                    json.dumps(signature_data, indent=2, ensure_ascii=False),
                )

        logger.info(f"MOD package created: {package_path}")
        return package_path

    def _should_exclude(self, rel_path: str, patterns: set) -> bool:
        """检查文件是否应该被排除"""
        import fnmatch

        for pattern in patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            if fnmatch.fnmatch(os.path.basename(rel_path), pattern):
                return True
            if pattern in rel_path.split(os.sep):
                return True

        return False

    def _generate_signature(self, private_key: str | None = None) -> dict[str, Any]:
        """生成 MOD 签名"""
        content_hash = compute_directory_hash(self.mod_path)

        signature = {
            "version": "1.0",
            "algorithm": "sha256",
            "content_hash": content_hash,
            "timestamp": utc_now_iso_z(),
            "signer": os.environ.get("XCAGI_MOD_SIGNER", "unknown"),
        }

        if private_key:
            try:
                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import padding

                with open(private_key, "rb") as f:
                    key = serialization.load_pem_private_key(
                        f.read(),
                        password=None,
                    )

                message = content_hash.encode("utf-8")
                sig = key.sign(
                    message,
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )

                import base64

                signature["signature"] = base64.b64encode(sig).decode("utf-8")
                signature["key_algorithm"] = "RSA-PKCS1v15"
            except ImportError:
                logger.warning("cryptography 库未安装，使用无签名模式")
                signature["signature"] = ""
            except Exception as e:
                logger.error(f"签名生成失败：{e}")
                signature["signature"] = ""
        else:
            signature["signature"] = ""
            signature["warning"] = "未提供私钥，签名缺失"

        return signature

    @classmethod
    def extract_package(
        cls,
        package_path: str,
        target_dir: str,
        verify_signature: bool = True,
    ) -> tuple[str, dict[str, Any]]:
        """
        解压 MOD 包

        Args:
            package_path: MOD 包路径
            target_dir: 目标目录
            verify_signature: 是否验证签名

        Returns:
            (解压后的 MOD 路径，元数据)
        """
        if not os.path.isfile(package_path):
            raise ModPackageError(f"MOD 包不存在：{package_path}")

        if not zipfile.is_zipfile(package_path):
            raise ModPackageError(f"不是有效的 ZIP 文件：{package_path}")

        os.makedirs(target_dir, exist_ok=True)

        with zipfile.ZipFile(package_path, "r") as zipf:
            zipf.extractall(target_dir)

            signature_file = "META-INF/signature.json"
            if signature_file in zipf.namelist():
                if verify_signature:
                    cls._verify_package_signature(target_dir, zipf)
            else:
                if verify_signature:
                    logger.warning(f"MOD 包缺少签名文件：{package_path}")

        manifest_path = os.path.join(target_dir, "manifest.json")
        if not os.path.isfile(manifest_path):
            raise ModPackageError("MOD 包缺少 manifest.json")

        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        mod_id = manifest.get("id", "")
        if not mod_id:
            raise ModPackageError("manifest.json 缺少 'id' 字段")

        mod_path = os.path.join(target_dir, mod_id)
        if os.path.isdir(mod_path):
            extracted_path = mod_path
        else:
            extracted_path = target_dir

        logger.info(f"MOD package extracted: {extracted_path}")
        return extracted_path, manifest

    @classmethod
    def _verify_package_signature(cls, extract_dir: str, zipf: zipfile.ZipFile) -> bool:
        """验证 MOD 包签名"""
        try:
            signature_data = json.loads(zipf.read("META-INF/signature.json").decode("utf-8"))

            stored_hash = signature_data.get("content_hash", "")
            signature = signature_data.get("signature", "")

            if not signature:
                logger.warning("MOD 包未签名")
                return False

            computed_hash = compute_directory_hash(extract_dir)

            if computed_hash != stored_hash:
                raise ModSignatureError("MOD 内容哈希不匹配，可能被篡改")

            public_key_path = os.environ.get("XCAGI_MOD_PUBLIC_KEY")
            if public_key_path and os.path.isfile(public_key_path):
                import base64

                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import padding

                with open(public_key_path, "rb") as f:
                    public_key = serialization.load_pem_public_key(f.read())

                sig = base64.b64decode(signature)
                public_key.verify(
                    sig,
                    stored_hash.encode("utf-8"),
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
                logger.info("MOD signature verified successfully")
                return True
            else:
                logger.info("MOD 哈希验证通过（未进行签名验证）")
                return True

        except ModSignatureError:
            raise
        except Exception as e:
            logger.error(f"签名验证失败：{e}")
            return False

    def get_package_info(self) -> dict[str, Any]:
        """获取 MOD 包信息"""
        return {
            "id": self.mod_id,
            "name": self.manifest.get("name", ""),
            "version": self.version,
            "author": self.manifest.get("author", ""),
            "description": self.manifest.get("description", ""),
            "dependencies": self.manifest.get("dependencies", {}),
            "file_size": os.path.getsize(self.manifest_path),
        }
