"""ProfileManager 配置文件读写测试：原子写入、损坏容错与默认配置回退。

对应 findings.json PM3 verifier：
"写入过程中断后 cfg.json 仍可正常解析或自动回退"。
"""
import json
import os
import shutil
import tempfile
import unittest

import testutils
from core.ProfileManager import ProfileManager


class SaveConfigAtomicWriteTest(unittest.TestCase):
    """save_config 原子写入：正常写入、覆盖旧文件、不留 .tmp 残留"""

    def setUp(self):
        self.tmp_root = tempfile.mkdtemp(prefix="newgan_pm_")
        self.cfg_path = os.path.join(self.tmp_root, "cfg.json")

    def tearDown(self):
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_save_writes_valid_json_without_tmp_leftover(self):
        ProfileManager.save_config(self.cfg_path, {"Profile": {"No Profile": True}})
        self.assertTrue(os.path.isfile(self.cfg_path))
        # 原子写入完成后临时文件必须被 os.replace 消费掉
        self.assertFalse(os.path.isfile(self.cfg_path + ".tmp"))
        with open(self.cfg_path, encoding="utf-8") as fp:
            self.assertEqual(json.load(fp), {"Profile": {"No Profile": True}})

    def test_save_overwrites_existing_file(self):
        ProfileManager.save_config(self.cfg_path, {"a": 1})
        ProfileManager.save_config(self.cfg_path, {"a": 2})
        with open(self.cfg_path, encoding="utf-8") as fp:
            self.assertEqual(json.load(fp), {"a": 2})
        self.assertFalse(os.path.isfile(self.cfg_path + ".tmp"))


class LoadConfigCorruptionTest(unittest.TestCase):
    """load_config 容错：损坏文件备份为 .corrupt 后按缺失处理"""

    def setUp(self):
        self.tmp_root = tempfile.mkdtemp(prefix="newgan_pm_")
        self.cfg_path = os.path.join(self.tmp_root, "cfg.json")

    def tearDown(self):
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_load_missing_file_raises_filenotfound(self):
        with self.assertRaises(FileNotFoundError):
            ProfileManager.load_config(self.cfg_path)

    def test_load_corrupt_file_backs_up_and_raises_filenotfound(self):
        # 模拟进程崩溃留下的截断 JSON
        with open(self.cfg_path, "w", encoding="utf-8") as fp:
            fp.write('{"Profile": {"No Profile": tru')
        with self.assertRaises(FileNotFoundError):
            ProfileManager.load_config(self.cfg_path)
        # 损坏文件被备份，原始文件保留供人工排查
        self.assertTrue(os.path.isfile(self.cfg_path + ".corrupt"))
        self.assertTrue(os.path.isfile(self.cfg_path))


class InitFallbackTest(unittest.TestCase):
    """ProfileManager 初始化：cfg.json 缺失或损坏时回退默认配置并落盘"""

    def setUp(self):
        self.tmp_data = testutils.copy_testing_data()

    def tearDown(self):
        shutil.rmtree(os.path.dirname(self.tmp_data), ignore_errors=True)

    def test_init_creates_default_config_when_cfg_missing(self):
        cfg_path = os.path.join(self.tmp_data, ".user", "cfg.json")
        os.remove(cfg_path)
        pm = ProfileManager("No Profile", root_dir=self.tmp_data, data_dir=self.tmp_data)
        self.assertEqual(pm.config, {"Profile": {"No Profile": True}})
        # 回退的默认配置已原子落盘
        with open(cfg_path, encoding="utf-8") as fp:
            self.assertEqual(json.load(fp), {"Profile": {"No Profile": True}})

    def test_init_falls_back_when_cfg_corrupt(self):
        cfg_path = os.path.join(self.tmp_data, ".user", "cfg.json")
        with open(cfg_path, "w", encoding="utf-8") as fp:
            fp.write('{"Profile": {"No Profile": ')
        pm = ProfileManager("No Profile", root_dir=self.tmp_data, data_dir=self.tmp_data)
        self.assertEqual(pm.config, {"Profile": {"No Profile": True}})
        # 损坏文件已备份，未丢失证据
        self.assertTrue(os.path.isfile(cfg_path + ".corrupt"))


if __name__ == "__main__":
    unittest.main()
