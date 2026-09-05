"""FaceMapper 单元测试：correct_ethnic 种族修正全分支、Generate 模式映射与取消。

correct_ethnic 是纯逻辑函数，直接覆盖 0-10 全部分支；
generate_mapping 使用 testutils.make_facepack() 构造临时头像包验证映射行为。
"""
import os
import shutil
import tempfile
import threading
import unittest

import testutils
from core.FaceMapper import FaceMapper
from core.ProfileManager import ProfileManager

# 球员样例字段：UID, 主国籍, 第二国籍, 姓名, 发长, 发色, 种族码
_PLAYER = ["r-2000000001", "ENG", "", "Test Player", "1", "5", "0"]


class CorrectEthnicTest(unittest.TestCase):
    """correct_ethnic 对种族码 0-10 的修正逻辑（纯函数，不依赖头像包）"""

    def setUp(self):
        # correct_ethnic 不需要真实头像包，用最小临时目录即可实例化
        self.tmp_root = tempfile.mkdtemp(prefix="newgan_fm_")
        eth_dir = os.path.join(self.tmp_root, "Caucasian")
        os.makedirs(eth_dir)
        with open(os.path.join(eth_dir, "e0.png"), "wb") as fp:
            fp.write(b"\x89PNG\r\n\x1a\n")
        self.mapper = FaceMapper(self.tmp_root, prf_manager=None)

    def tearDown(self):
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_code_0_scandinavian_first(self):
        player = list(_PLAYER)
        player[6] = "0"
        self.assertEqual(self.mapper.correct_ethnic(player, "Caucasian", "Scandinavian"), "Scandinavian")

    def test_code_0_caucasian_fallback_central_european(self):
        player = list(_PLAYER)
        player[6] = "0"
        self.assertEqual(self.mapper.correct_ethnic(player, "Central European", "Caucasian"), "Caucasian")
        self.assertEqual(self.mapper.correct_ethnic(player, "African", "MENA"), "Central European")

    def test_code_1_hits_specific_ethnics(self):
        player = list(_PLAYER)
        player[6] = "1"
        for eth in ("Caucasian", "EECA", "Italmed", "SAMed", "SpanMed", "YugoGreek", "South American"):
            self.assertEqual(self.mapper.correct_ethnic(player, eth, ""), eth)
        self.assertEqual(self.mapper.correct_ethnic(player, "African", "MENA"), "Central European")

    def test_code_2_mesa_or_mena(self):
        player = list(_PLAYER)
        player[6] = "2"
        self.assertEqual(self.mapper.correct_ethnic(player, "MENA", "MESA"), "MESA")
        self.assertEqual(self.mapper.correct_ethnic(player, "MENA", "African"), "MENA")

    def test_code_6_samed_or_african(self):
        player = list(_PLAYER)
        player[6] = "6"
        self.assertEqual(self.mapper.correct_ethnic(player, "African", "SAMed"), "SAMed")
        self.assertEqual(self.mapper.correct_ethnic(player, "African", "MENA"), "African")

    def test_code_8_seasian_or_african(self):
        player = list(_PLAYER)
        player[6] = "8"
        self.assertEqual(self.mapper.correct_ethnic(player, "Seasian", "African"), "Seasian")
        self.assertEqual(self.mapper.correct_ethnic(player, "MESA", "African"), "African")

    def test_code_3_and_9_south_american_or_african(self):
        for code in ("3", "9"):
            player = list(_PLAYER)
            player[6] = code
            self.assertEqual(self.mapper.correct_ethnic(player, "South American", "African"), "South American")
            self.assertEqual(self.mapper.correct_ethnic(player, "MESA", "African"), "African")

    def test_code_4_5_7_fixed_ethnics(self):
        player = list(_PLAYER)
        player[6] = "4"
        self.assertEqual(self.mapper.correct_ethnic(player, "African", "African"), "MESA")
        player[6] = "5"
        self.assertEqual(self.mapper.correct_ethnic(player, "African", "African"), "Seasian")
        player[6] = "7"
        self.assertEqual(self.mapper.correct_ethnic(player, "African", "African"), "South American")

    def test_code_10_priority_and_asian_fallback(self):
        player = list(_PLAYER)
        player[6] = "10"
        self.assertEqual(self.mapper.correct_ethnic(player, "Asian", "MESA"), "MESA")
        self.assertEqual(self.mapper.correct_ethnic(player, "Asian", "Seasian"), "Seasian")
        self.assertEqual(self.mapper.correct_ethnic(player, "Asian", "South American"), "South American")
        self.assertEqual(self.mapper.correct_ethnic(player, "Caucasian", "African"), "Asian")


class GenerateMappingTest(unittest.TestCase):
    """generate_mapping 的 Generate 模式：种族修正、图片选择、取消标志"""

    def setUp(self):
        # 真实 ProfileManager（读取测试数据 eth_cfg.json），构造头像包
        self.tmp_data = testutils.copy_testing_data()
        self.prf = ProfileManager("No Profile", root_dir=self.tmp_data, data_dir=self.tmp_data)
        facepack_root = os.path.join(os.path.dirname(self.tmp_data), "facepack")
        self.facepack_root = testutils.make_facepack(
            facepack_root,
            {"Caucasian": 5, "MESA": 5, "African": 5},
        )
        self.mapper = FaceMapper(self.facepack_root, self.prf)

    def tearDown(self):
        shutil.rmtree(os.path.dirname(self.tmp_data), ignore_errors=True)

    def test_generate_mode_mapping(self):
        """Generate 模式：按种族码修正种族并生成映射"""
        rtf_data = [
            ["r-2000000001", "ENG", "", "Player One", "1", "5", "0"],   # Caucasian
            ["r-2000000002", "KSA", "", "Player Two", "1", "5", "2"],   # MESA
            ["r-2000000003", "NGA", "", "Player Three", "1", "5", "3"],  # African
        ]
        mapping = self.mapper.generate_mapping(rtf_data, "Generate")
        self.assertEqual(len(mapping), 3)
        by_uid = {m[0]: m for m in mapping}
        self.assertEqual(by_uid["r-2000000001"][1], "Caucasian")
        self.assertEqual(by_uid["r-2000000002"][1], "MESA")
        self.assertEqual(by_uid["r-2000000003"][1], "African")
        # 每张映射都选到了实际存在的图片
        for m in mapping:
            self.assertIn(m[2], self.mapper.faces_map[m[1]])

    def test_generate_mode_no_duplicates(self):
        """Generate + 不允许重复：同一池中图片不重复使用"""
        rtf_data = [
            ["r-2000000001", "ENG", "", "Player One", "1", "5", "0"],
            ["r-2000000002", "USA", "", "Player Two", "1", "5", "0"],
            ["r-2000000003", "SCO", "", "Player Three", "1", "5", "0"],
        ]
        mapping = self.mapper.generate_mapping(rtf_data, "Generate", duplicates=False)
        self.assertEqual(len(mapping), 3)
        images = [m[2] for m in mapping]
        self.assertEqual(len(images), len(set(images)), "不允许重复时图片不应重复")

    def test_generate_mode_cancel_event(self):
        """cancel_event 置位后映射中断并返回 None"""
        rtf_data = [
            ["r-2000000001", "ENG", "", "Player One", "1", "5", "0"],
            ["r-2000000002", "KSA", "", "Player Two", "1", "5", "2"],
        ]
        evt = threading.Event()
        evt.set()
        self.assertIsNone(self.mapper.generate_mapping(rtf_data, "Generate", cancel_event=evt))


if __name__ == "__main__":
    unittest.main()
