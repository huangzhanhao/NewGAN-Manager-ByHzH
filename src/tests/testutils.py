"""测试基架：把 testing_data 复制到临时目录，避免污染 git 跟踪的固定数据"""
import os
import shutil
import sys
import tempfile

# 让测试能直接 import core 模块（与 CI 的 unittest discover -s src/tests 兼容）
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "newganmanager"))

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
TESTING_DATA = os.path.join(TESTS_DIR, "testing_data")


def copy_testing_data():
    """把 testing_data 完整复制到临时目录，返回副本路径；调用方负责清理"""
    tmp = tempfile.mkdtemp(prefix="newgan_test_")
    dst = os.path.join(tmp, "testing_data")
    shutil.copytree(TESTING_DATA, dst)
    return dst


def make_facepack(root, ethnicities):
    """创建临时头像包目录：每个种族目录下生成 N 张假图片文件

    Args:
        root: 头像包根目录
        ethnicities: {目录名: 图片数量}，图片名为 e0.png, e1.png, ...
    Returns:
        root（调用方负责清理其父目录）
    """
    for eth, count in ethnicities.items():
        eth_dir = os.path.join(root, eth)
        os.makedirs(eth_dir, exist_ok=True)
        for i in range(count):
            with open(os.path.join(eth_dir, f"e{i}.png"), "wb") as fp:
                fp.write(b"\x89PNG\r\n\x1a\n")  # PNG magic bytes，仅占位
    return root
