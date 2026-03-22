"""
工具函数测试
"""

import pytest
import os
from app.utils.path_utils import get_data_dir, get_base_dir, ensure_dir


class TestPathUtils:
    """路径工具测试"""

    def test_get_data_dir(self):
        data_dir = get_data_dir()
        assert data_dir is not None
        assert isinstance(data_dir, str)

    def test_get_base_dir(self):
        base_dir = get_base_dir()
        assert base_dir is not None
        assert os.path.exists(base_dir)

    def test_ensure_dir(self):
        test_dir = os.path.join(get_data_dir(), "test_dir_" + str(os.getpid()))
        try:
            result = ensure_dir(test_dir)
            assert os.path.exists(test_dir)
        finally:
            if os.path.exists(test_dir):
                os.rmdir(test_dir)