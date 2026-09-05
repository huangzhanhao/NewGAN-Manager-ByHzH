"""RtfParser 单元测试：格式验证、基础/14列解析、UID 前缀、种族码校验、中文翻译。

测试数据全部来自 testutils.copy_testing_data() 的临时副本，避免污染
git 跟踪的 testing_data 固定文件（对应 TODO.md 任务 8 的修复方式）。
"""
import os
import shutil
import unittest

import testutils
from core.RtfParser import RtfParser

# 14 列扩展格式（英文）样例行：UID, 主国籍, 第二国籍, 姓名, 发长, 发色, 种族码,
# 肤色码, Face, 俱乐部, 年龄, 身高, 体重, 是否随机人
_14COL_ENGLISH = (
    "| 2000000001| ENG       |           | Test Player One   | 1         | 5         | 1         |"
    " 4         | Face     | Club     | 20        | 180       | 75        | 是         |\n"
    "| 2000000002| ENG       |           | Test Player Two   | 1         | 5         | 1         |"
    " 4         | Face     | Club     | 21        | 175\u200b       | 70        | 否         |\n"
)

_14COL_ENGLISH_NO_FILTER = (
    "| 2000000003| ENG       |           | Test Player Three | 1         | 5         | 1         |"
    " 4         | Face     | Club     | 22        | 170       | 68        | No         |\n"
)


class RtfParserValidityTest(unittest.TestCase):
    """check_rtf_valid 的格式与语言判定"""

    def setUp(self):
        self.tmp_data = testutils.copy_testing_data()
        self.parser = RtfParser()

    def tearDown(self):
        shutil.rmtree(os.path.dirname(self.tmp_data), ignore_errors=True)

    def test_check_rtf_valid_english(self):
        path = os.path.join(self.tmp_data, "test_simple.rtf")
        self.assertTrue(self.parser.check_rtf_valid(path))
        self.assertEqual(self.parser.rtf_language, "English")

    def test_check_rtf_valid_chinese(self):
        path = os.path.join(self.tmp_data, "test_chnName.rtf")
        self.assertTrue(self.parser.check_rtf_valid(path))
        self.assertEqual(self.parser.rtf_language, "简体中文")

    def test_check_rtf_valid_rejects_garbage(self):
        path = os.path.join(self.tmp_data, "garbage.rtf")
        with open(path, "w", encoding="utf-8") as fp:
            fp.write("this is not an rtf file\nno uid or nationality columns\n")
        self.assertFalse(self.parser.check_rtf_valid(path))


class RtfParserParseTest(unittest.TestCase):
    """parse_rtf 的解析行为"""

    def setUp(self):
        self.tmp_data = testutils.copy_testing_data()
        self.parser = RtfParser()

    def tearDown(self):
        shutil.rmtree(os.path.dirname(self.tmp_data), ignore_errors=True)

    def _write_rtf(self, filename, content):
        path = os.path.join(self.tmp_data, filename)
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(content)
        return path

    def test_parse_rtf_english_basic(self):
        """7 列基础格式：UID 加 r- 前缀、字段顺序正确"""
        path = os.path.join(self.tmp_data, "test_simple.rtf")
        self.assertTrue(self.parser.check_rtf_valid(path))
        data = self.parser.parse_rtf(path)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0][0], "r-1915714540")
        self.assertEqual(data[0][1], "ESP")
        self.assertEqual(data[0][2], "BAS")
        self.assertEqual(data[0][3], "Javi Alonso")
        self.assertEqual(data[0][6], "1")

    def test_parse_rtf_chinese_translates_nationality(self):
        """中文 RTF：国籍被 nat_translation.json 翻译为英文三字码"""
        path = os.path.join(self.tmp_data, "test_chnName.rtf")
        self.assertTrue(self.parser.check_rtf_valid(path))
        data = self.parser.parse_rtf(path)
        self.assertGreater(len(data), 50)
        nationalities = {record[1] for record in data}
        self.assertIn("USA", nationalities)   # 美国
        self.assertIn("BRA", nationalities)   # 巴西
        self.assertIn("CHN", nationalities)   # 中国
        self.assertIn("KOR", nationalities)   # 韩国

    def test_parse_rtf_skips_invalid_uid(self):
        """非纯数字 UID 的行被跳过"""
        content = (
            "| UID       | Nat       | 2nd Nat   | Name       |           |           |           |\n"
            "| abc12345  | ENG       |           | Bad UID    | 1         | 5         | 0         |\n"
            "| 2000000002| ENG       |           | Good UID   | 1         | 5         | 0         |\n"
        )
        path = self._write_rtf("invalid_uid.rtf", content)
        self.assertTrue(self.parser.check_rtf_valid(path))
        data = self.parser.parse_rtf(path)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0][0], "r-2000000002")

    def test_parse_rtf_skips_out_of_range_ethnicity(self):
        """种族码越界（>10）的行被跳过"""
        content = (
            "| UID       | Nat       | 2nd Nat   | Name       |           |           |           |\n"
            "| 2000000001| ENG       |           | Bad Ethnic | 1         | 5         | 11        |\n"
            "| 2000000002| ENG       |           | Good       | 1         | 5         | 3         |\n"
        )
        path = self._write_rtf("bad_ethnicity.rtf", content)
        self.assertTrue(self.parser.check_rtf_valid(path))
        data = self.parser.parse_rtf(path)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0][0], "r-2000000002")

    def test_parse_rtf_14_columns_filter_newgan(self):
        """14 列格式：'否' 的非随机人去掉 r- 前缀；filter_newgan=True 时整条过滤"""
        header = (
            "| UID       | Nat       | 2nd Nat   | Name       |           |           |           |\n"
        )
        path = self._write_rtf("14col.rtf", header + _14COL_ENGLISH)
        self.assertTrue(self.parser.check_rtf_valid(path))
        # filter_newgan=True：第 2 行（否）被过滤
        data = self.parser.parse_rtf(path, filter_newgan=True)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0][0], "r-2000000001")  # 是 → 保留 r- 前缀
        # 保留行 14 个字段完整（索引 11 = 身高，含零宽空格的行已被过滤）
        self.assertEqual(data[0][11], "180")

    def test_parse_rtf_14_columns_keep_non_newgan(self):
        """filter_newgan=False：'否'/'No' 的非随机人保留且 UID 无 r- 前缀"""
        header = (
            "| UID       | Nat       | 2nd Nat   | Name       |           |           |           |\n"
        )
        path = self._write_rtf("14col_nofilter.rtf", header + _14COL_ENGLISH + _14COL_ENGLISH_NO_FILTER)
        self.assertTrue(self.parser.check_rtf_valid(path))
        data = self.parser.parse_rtf(path, filter_newgan=False)
        self.assertEqual(len(data), 3)
        self.assertEqual(data[1][0], "2000000002")  # 否 → 无前缀
        self.assertEqual(data[2][0], "2000000003")  # No → 无前缀
        # 保留行身高/体重中的零宽空格（\u200b）被清理
        self.assertEqual(data[1][11], "175")

    def test_parse_rtf_requires_valid_check_first(self):
        """未先 check_rtf_valid 直接解析返回空列表"""
        path = os.path.join(self.tmp_data, "test_simple.rtf")
        self.assertEqual(self.parser.parse_rtf(path), [])


if __name__ == "__main__":
    unittest.main()
