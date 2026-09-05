# 模块名沿用 core 包统一的 PascalCase 约定（FaceMapper.py / XmlParser.py / ProfileManager.py ...），
# 与 pylint 默认的 snake_case 模块名规则冲突，故仅豁免该检查项。
# pylint: disable=invalid-name
"""RTF 球员名单解析：校验 RTF 格式、提取球员数据、把中文国籍翻译为英文三字码。

RTF 名单由 Football Manager 导出，每行是一条以 ``|`` 分隔的记录::

    | UID       | Nat       | 2nd Nat   | Name       |  |  |  |
    | 2000472008| ESP       | USA       | Pepe Sáenz | 1| 12| 1|

部分名单还额外带 7 个附加列（肤色码、Face、俱乐部、年龄、身高、体重、是否随机人）。

用法::

    parser = RtfParser()
    if parser.check_rtf_valid(path):
        players = parser.parse_rtf(path)
"""

import json
import logging
import os
import re
from itertools import islice
from typing import cast

# pylint: enable=invalid-name

# 基础列数：UID / 主要国籍 / 第二国籍 / 姓名 / 头发长度 / 头发颜色 / 种族代码
BASE_FIELD_COUNT = 7
# 附加列的起始下标（肤色码、Face、俱乐部、年龄、身高、体重、是否随机人）
ADDITIONAL_FIELD_START = 7
# 带附加列时的总列数
DETAILED_FIELD_COUNT = 14
# 附加列中「身高」「体重」的下标，导出时可能混入零宽空格
HEIGHT_INDEX = 11
WEIGHT_INDEX = 12
# 附加列中「是否随机人」的下标
RANDOM_FLAG_INDEX = 13
# 表示「非随机人（真实球员）」的取值，命中则去掉 UID 的 r- 前缀
NON_NEWGAN_FLAGS = ("No", "否")
# 随机人 UID 前缀
NEWGAN_UID_PREFIX = "r-"
# 身高/体重中可能出现的零宽空格
ZERO_WIDTH_SPACE = "\u200b"
# 种族（肤色）代码的合法区间
ETHNICITY_MIN = 0
ETHNICITY_MAX = 10
# 校验 RTF 头部时最多读取的行数
VALIDATE_LINE_LIMIT = 20


class RtfParser:
    """解析 NewGAN 替换流程使用的 RTF 球员名单"""

    def __init__(self) -> None:
        self.rtf_data: list[list[str]] = []
        self.rtf_language: str = "English"
        self.is_rtf_valid: bool = False
        # 国籍翻译表的缓存，形如 (语言, {中文国籍: 英文三字码})，None 表示尚未加载
        self._translation_cache: tuple[str, dict[str, str]] | None = None
        self.logger: logging.Logger = logging.getLogger("NewGAN App")
        # 英文名单正则：字段均由前后 "|" 符号包围
        # VERBOSE 模式会忽略模式中的空白并把 # 之后的内容视为注释，便于逐段说明
        self.rtf_regex: re.Pattern[str] = re.compile(
            r"""
            \|\s*[0-9]{4,}\s*\|      # UID字段(前后都有"|"符号)
            \s*[A-Z]{3}\s*\|         # 主要国籍字段(前后都有"|"符号)
            (\s*([A-Z]{3})?\s*\|)?   # 可选的第二国籍字段(前后都有"|"符号)
            \s*[^|]+\s*\|            # 姓名字段(前后都有"|"符号)
            \s*[\d]+\s*\|            # 头发长度字段(前后都有"|"符号)
            \s*[\d]+\s*\|            # 头发颜色字段(前后都有"|"符号)
            \s*[\d]+\s*\|            # 种族字段(前后都有"|"符号)
            """,
            re.VERBOSE,
        )
        # 中文名单正则：国籍列为中文
        self.rtf_regex_chn: re.Pattern[str] = re.compile(
            r"""
            \|\s*[0-9]{4,}\s*\|      # 编号字段(前后都有"|"符号)
            \s*[\u4e00-\u9fff]+\s*\| # 国籍/地区籍字段(前后都有"|"符号)
            \s*[\u4e00-\u9fff]*\s*\| # 第二国籍/地区籍字段(前后都有"|"符号)
            \s*[^|]+\s*\|            # 姓名字段(前后都有"|"符号)
            \s*[\d]+\s*\|            # 头发长度字段(前后都有"|"符号)
            \s*[\d]+\s*\|            # 头发颜色字段(前后都有"|"符号)
            \s*[\d]+\s*\|            # 种族字段(前后都有"|"符号)
            """,
            re.VERBOSE,
        )

    def parse_rtf(self, path: str, filter_newgan: bool = True) -> list[list[str]]:
        """
        解析RTF文件，提取球员数据
        字段顺序：UID, 主要国籍, 第二国籍, 姓名, 头发长度, 头发颜色, 种族代码
        Args:
            path (str): RTF文件的路径
            filter_newgan (bool): 是否过滤掉非NewGAN球员，默认为True
        Returns:
            list: 包含球员信息的列表，每个球员信息是一个包含以下元素的列表：
                  [UID, 主要国籍, 第二国籍, 姓名, 头发长度, 头发颜色, 种族代码] 或
                  [UID, 主要国籍, 第二国籍, 姓名, 头发长度, 头发颜色, 种族代码, 肤色代码, 面部, 俱乐部, 年龄, 身高, 体重, 是否为随机人]
        """
        # 首先验证RTF文件格式
        if not self.is_rtf_valid:
            self.logger.error("Parsing RTF file... The RTF file format is invalid, "
                              + "please check the RTF file first.")
            return []
        # 重置数据
        self.rtf_data = []
        try:
            with open(path, "r", encoding="UTF-8") as rtf:
                self.logger.info("Parsing RTF file...")
                for line_no, line in enumerate(rtf, start=1):
                    # 跳过空行
                    if not line.strip():
                        continue
                    record = self._parse_line(line, line_no, filter_newgan)
                    if record is not None:
                        self.rtf_data.append(record)
            self.logger.info("Completed parsing RTF file, with a total of %s valid records",
                             len(self.rtf_data))
        except FileNotFoundError:
            self.logger.error("RTF file not found: %s", path)
            raise
        except UnicodeDecodeError:
            self.logger.error("Encoding error in RTF file: %s", path)
            raise
        except Exception as exc:
            self.logger.error("Unexpected error while parsing RTF file: %s", exc)
            raise
        # 如果没有找到有效数据
        if not self.rtf_data:
            self.logger.warning("Parsing RTF file... No valid player data found in the RTF file!")
        # 确保返回英文数据
        self.rtf_data = self.translate_rtf_data_to_english(self.rtf_data)
        return self.rtf_data

    def _parse_line(self, line: str, line_no: int, filter_newgan: bool) -> list[str] | None:
        """把一行 RTF 数据转换为球员记录

        Args:
            line (str): RTF 文件的一行原始文本
            line_no (int): 行号，仅用于日志定位
            filter_newgan (bool): 是否过滤掉非 NewGAN 球员

        Returns:
            list | None: 球员记录；该行不是有效数据行或被过滤时返回 None
        """
        # 使用正则匹配有效数据行
        if not (self.rtf_regex.search(line) or self.rtf_regex_chn.search(line)):
            return None
        # 分割字段并去除空白，但保留空值字段
        fields = [field.strip() for field in line.split("|")]
        # 移除第一个和最后一个空字段（来自行首行尾的分隔符）
        fields = fields[1:-1] if len(fields) >= 2 else []
        # 验证字段数量
        if len(fields) < BASE_FIELD_COUNT:
            self.logger.warning(
                "Parsing RTF file %s line: contains only %s fields "
                + "but less than %s fields - skipping",
                line_no, len(fields), BASE_FIELD_COUNT)
            return None
        uid, primary_nat, sec_nat, player_name, hair_length, hair_color, ethnicity_code = (
            fields[:BASE_FIELD_COUNT])
        # 验证UID
        if not uid.isdigit():
            self.logger.info("Parsing RTF file %s line: the uid field(%s) is invalid - skipping",
                             line_no, uid)
            return None
        # 默认为随机人编号，添加r-前缀
        uid = NEWGAN_UID_PREFIX + uid
        # 验证种族（肤色）代码
        if not self._is_valid_ethnicity(ethnicity_code):
            self.logger.info(
                "Parsing RTF file %s line: the ethnicity field(%s) is out of "
                + "range (%s-%s) - skipping",
                line_no, ethnicity_code, ETHNICITY_MIN, ETHNICITY_MAX)
            return None
        # 创建基础数据记录
        record = [uid, primary_nat, sec_nat, player_name, hair_length, hair_color, ethnicity_code]
        # 处理附加字段（如果有）
        if len(fields) >= DETAILED_FIELD_COUNT:
            return self._append_additional_fields(record, fields, line_no, filter_newgan)
        self.logger.debug("Parsing RTF file %s line basically: %s", line_no, record)
        return record

    @staticmethod
    def _is_valid_ethnicity(ethnicity_code: str) -> bool:
        """判断种族（肤色）代码是否为 0-10 之间的整数"""
        return (ethnicity_code.isdigit()
                and ETHNICITY_MIN <= int(ethnicity_code) <= ETHNICITY_MAX)

    def _append_additional_fields(self, record: list[str], fields: list[str],
                                  line_no: int, filter_newgan: bool) -> list[str] | None:
        """为基础记录追加附加列

        Args:
            record (list): 已解析出的 7 个基础字段
            fields (list): 该行切分出的全部字段
            line_no (int): 行号，仅用于日志定位
            filter_newgan (bool): 是否过滤掉非 NewGAN 球员

        Returns:
            list | None: 追加了附加列的完整记录；该行被过滤时返回 None
        """
        # 处理身高、体重列中可能的零宽空格字符
        for index in (HEIGHT_INDEX, WEIGHT_INDEX):
            fields[index] = fields[index].replace(ZERO_WIDTH_SPACE, "")
        # 从附加字段判断是否属于随机人，非随机人需要处理UID中的"r-"前缀
        if any(flag in fields[RANDOM_FLAG_INDEX] for flag in NON_NEWGAN_FLAGS):
            record[0] = record[0].removeprefix(NEWGAN_UID_PREFIX)
            if filter_newgan:
                self.logger.debug(
                    "Parsing RTF file %s line: filter out non-NewGAN players - skipping", line_no)
                return None
        # 添加详细数据
        detailed_data = record + fields[ADDITIONAL_FIELD_START:]
        self.logger.debug("Parsing RTF file %s line in detail: %s", line_no, detailed_data)
        return detailed_data

    def check_rtf_valid(self, path: str) -> bool:
        """
        验证RTF文件格式是否正确

        英文数据库的RTF文件应包含类似以下格式的行：
        | UID       | Nat  | 2nd Nat | Name          |    |    |   |
        | ---------------------------------------------------------|
        | 2000472008| ESP  | USA     | Pepe Sáenz    | 1  | 12 | 1 |
        | 2002161479| BRA  |         | José·Milhomem | 1  | 16 | 3 |
        | 2002161482| BRA  |         | Juvenal Morais| 1  | 5  | 1 |

        中文数据库的RTF文件应包含类似以下格式的行：
        | 编号      | 国籍/地区籍 | 第二国籍 | 姓名             |    |    |   |
        | --------------------------------------------------------------|
        | 2002075172| 美国     |        | 扎克·布劳顿      | 3  | 9  | 0 |
        | 2002075152| 美国     |        | 哈尔特·哈勒      | 1  | 12 | 0 |
        | 2002072431| 孟加拉   | 美国   | Tayab Hasan Hasan| 1 | 16 | 4 |

        Args:
            path (str): RTF文件的路径

        Returns:
            bool: 格式正确返回 True，否则返回 False

        Raises:
            OSError: 文件不存在（FileNotFoundError）、无权限（PermissionError）等
                读写错误会向上传播，由调用方向用户给出更精确的提示
        """
        # 重置验证状态
        self.is_rtf_valid = False
        self.rtf_language = "Unknown"
        try:
            # 打开RTF文件进行读取，仅取开头的若干行做格式判定
            with open(path, "r", encoding="UTF-8") as rtf:
                rtf_data = "".join(islice(rtf, VALIDATE_LINE_LIMIT))
        except UnicodeDecodeError as exc:
            self.logger.error("Encoding error while validating RTF file: %s", exc)
            return False
        # 检查RTF数据是否匹配预期的格式模式
        if self.rtf_regex.search(rtf_data):
            self.rtf_language = "English"
            self.logger.info("The RTF file format is correct, "
                             + "and the RTF file data language is: %s", self.rtf_language)
            self.is_rtf_valid = True
        elif self.rtf_regex_chn.search(rtf_data):
            self.rtf_language = "简体中文"
            self.logger.info("RTF文件格式正确，RTF文件数据语言为: %s", self.rtf_language)
            self.is_rtf_valid = True
        else:
            self.logger.error("The RTF file is invalid or cannot be recognized.")
        return self.is_rtf_valid

    def translate_rtf_data_to_english(self, rtf_data: list[list[str]]) -> list[list[str]]:
        """将传入的rtf_data数据的主要国籍以及第二国籍字段翻译为英文

        Args:
            rtf_data (list): parse_rtf 解析出的球员记录列表

        Returns:
            list: 国籍已替换为英文三字码的记录列表；无需翻译或缺少翻译表时原样返回
        """
        if self.rtf_language == "English":
            self.logger.info("The RTF data language is English, "
                             + "and does not need to be translated.")
            return rtf_data
        # 检查翻译映射表是否为空
        tr_map = self._load_translation_map()
        if not tr_map:
            self.logger.error("The nationality translation JSON is empty!")
            return rtf_data
        translated_data: list[list[str]] = []
        self.logger.info("Translating RTF data from %s to English...", self.rtf_language)
        for record in rtf_data:
            # 字段顺序: [0]UID, [1]主要国籍, [2]第二国籍, [3]姓名, [4]头发长度, [5]头发颜色, [6]种族代码...
            uid = record[0]
            primary = record[1]
            second = record[2]
            # 翻译主要国籍和第二国籍，保持其他字段不变
            tr_primary = tr_map.get(primary.strip(), primary)
            tr_second = tr_map.get(second.strip(), second) if second else ""
            translated_data.append([uid, tr_primary, tr_second] + record[3:])
            self.logger.debug("Translating UID %s: '%s'->'%s', '%s'->'%s'",
                              uid, primary, tr_primary, second, tr_second)
        self.logger.info("Completed translating %s records from RTF data.", len(translated_data))
        return translated_data

    def _load_translation_map(self) -> dict[str, str]:
        """读取并缓存国籍翻译表

        Returns:
            dict: 语言到英文三字码的映射；读取失败时返回空字典
        """
        cache = self._translation_cache
        if cache is not None and cache[0] == self.rtf_language:
            return cache[1]
        translation_json_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), ".config", "nat_translation.json")
        try:
            with open(translation_json_path, "r", encoding="utf-8") as file:
                self.logger.info("Loading translation file: %s", translation_json_path)
                # JSON 结构是 {语言: {中文国籍: 英文三字码}}
                translation_data = cast(
                    "dict[str, dict[str, str]]", json.load(file))
        except FileNotFoundError as exc:
            self.logger.error("The nationality translation JSON not found: %s", exc)
            return {}
        except json.JSONDecodeError as exc:
            self.logger.error("Decoding error in nationality translation JSON: %s", exc)
            return {}
        # 初始化并缓存翻译映射表
        tr_map = translation_data.get(self.rtf_language, {})
        self._translation_cache = (self.rtf_language, tr_map)
        return tr_map
