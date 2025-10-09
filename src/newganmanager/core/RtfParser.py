
import json
import re
import os
import logging
from itertools import islice


class RtfParser:
    def __init__(self):
        self.rtf_data = []
        self.rtf_language = "English"
        self.is_rtf_valid = False
        # 使用原始字符串避免转义警告
        # 正则表达式按照字段由前后"|"符号包围的逻辑设计
        self.rtf_regex = re.compile(
            r"\|\s*[0-9]{4,}\s*\|"                  # UID字段(前后都有"|"符号)
            r"\s*[A-Z]{3}\s*\|"                     # 主要国籍字段(前后都有"|"符号)
            r"(\s*([A-Z]{3})?\s*\|)?"               # 可选的第二国籍字段(前后都有"|"符号)
            r"\s*[^|]+\s*\|"                        # 姓名字段(前后都有"|"符号)
            r"\s*[\d]+\s*\|"                        # 头发长度字段(前后都有"|"符号)
            r"\s*[\d]+\s*\|"                        # 头发颜色字段(前后都有"|"符号)
            r"\s*[\d]+\s*\|"                        # 种族字段(前后都有"|"符号)
        )
        # 添加新的正则表达式用于匹配包含中文的RTF文件
        self.rtf_regex_chn = re.compile(
            r"\|\s*[0-9]{4,}\s*\|"                  # 编号字段(前后都有"|"符号)
            r"\s*[\u4e00-\u9fff]+\s*\|"             # 国籍/地区籍字段(前后都有"|"符号)
            r"\s*[\u4e00-\u9fff]*\s*\|"             # 第二国籍/地区籍字段(前后都有"|"符号)
            r"\s*[^|]+\s*\|"                        # 姓名字段(前后都有"|"符号)
            r"\s*[\d]+\s*\|"                        # 头发长度字段(前后都有"|"符号)
            r"\s*[\d]+\s*\|"                        # 头发颜色字段(前后都有"|"符号)
            r"\s*[\d]+\s*\|"                        # 种族字段(前后都有"|"符号)
        )
        self.logger = logging.getLogger("NewGAN App")

    def parse_rtf(self, path, filter_newgan=True):
        """
        解析RTF文件，提取球员数据
        字段顺序：UID, 主要国籍, 第二国籍, 姓名, 头发长度, 头发颜色, 种族代码

        Args:
            path (str): RTF文件的路径

        Returns:
            list: 包含球员信息的列表，每个球员信息是一个包含以下元素的列表：
                  [UID, 主要国籍, 第二国籍, 姓名, 头发长度, 头发颜色, 种族代码] 或
                  [UID, 主要国籍, 第二国籍, 姓名, 头发长度, 头发颜色, 种族代码, 肤色代码, 面部, 俱乐部, 年龄, 身高, 体重, 是否为随机人]
        """
        # 验证RTF文件格式
        if not self.is_rtf_valid:
            self.logger.error("Parsing RTF file... The RTF file format is invalid, please check the RTF file first.")
            return []
        
        # 重置数据
        self.rtf_data = []
        
        try:
            line_count = 0
            with open(path, "r", encoding="UTF-8") as rtf:
                self.logger.info(f"Parsing RTF file...")
                for line in rtf:
                    line_count += 1
                    
                    # 跳过空行
                    if not line.strip():
                        continue
                    
                    # 使用正则匹配有效数据行
                    if self.rtf_regex.search(line) or self.rtf_regex_chn.search(line):
                        # 分割字段并去除空白，但保留空值字段
                        fields = [f.strip() for f in line.split("|")]
                        # 移除第一个和最后一个空字段（来自行首行尾的分隔符）
                        fields = fields[1:-1] if len(fields) >= 2 else []
                        
                        # 验证字段数量
                        if len(fields) < 7:
                            self.logger.warning(f"Parsing RTF file {line_count} line: contains only {len(fields)} fields but less than 7 fields - skipping")
                            continue
                        else:
                            # 提取核心字段
                            uid = fields[0]
                            primary_nat = fields[1]
                            sec_nat = fields[2]
                            player_name = fields[3]
                            hair_length = fields[4]
                            hair_color = fields[5]
                            ethnicity_code = fields[6]

                        # 验证UID
                        if not uid.isdigit():
                            self.logger.info(f"Parsing RTF file {line_count} line: the uid field({uid}) is invalid - skipping")
                            continue
                        else:
                            # 默认为随机人编号，添加r-前缀
                            uid = str("r-" + uid)
                        
                        # 验证种族（肤色）代码
                        if not ethnicity_code.isdigit() or int(ethnicity_code) < 0 or int(ethnicity_code) > 10:
                            self.logger.info(f"Parsing RTF file {line_count} line: the ethnicity field({ethnicity_code}) is out of range (0-10) - skipping")
                            continue
                        
                        # 创建基础数据记录
                        base_data = [
                            uid,
                            primary_nat,
                            sec_nat,
                            player_name,
                            hair_length,
                            hair_color,
                            ethnicity_code
                        ]
                        
                        # 处理附加字段（如果有）
                        if len(fields) == 14:
                            # 处理可能的零宽空格字符
                            if "\u200b" in fields[11] or "\u200b" in fields[12]:
                                fields[11] = fields[11].replace("\u200b", "")
                                fields[12] = fields[12].replace("\u200b", "")
                            # 从附加字段判断是否属于随机人，处理UID中的"r-"前缀
                            if "No" in fields[13] or "否" in fields[13]:
                                base_data[0] = uid.replace("r-", "")
                                if filter_newgan:
                                    self.logger.debug(f"Parsing RTF file {line_count} line: filter out non-NewGAN players - skipping")
                                    continue
                            # 提取附加字段
                            additional_fields = fields[7:]
                            # 添加详细数据
                            detailed_data = base_data + additional_fields
                            self.rtf_data.append(detailed_data)
                            self.logger.debug(f"Parsing RTF file {line_count} line in detail: {detailed_data}")
                        else:
                            # 添加基础数据
                            self.rtf_data.append(base_data)
                            self.logger.debug(f"Parsing RTF file {line_count} line basically: {base_data}")
            self.logger.info(f"Completed parsing RTF file, with a total of {len(self.rtf_data)} valid records")
        except UnicodeDecodeError as e:
            self.logger.error(f"The RTF file encoding error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error while parsing RTF file: {e}")
            return []

        # 如果没有找到有效数据
        if not self.rtf_data:
            self.logger.warning("Parsing RTF file... No valid player data found in the RTF file!")

        # 确保返回英文数据
        self.rtf_data = self.translate_rtf_data_to_english(self.rtf_data)
        return self.rtf_data

    def check_rtf_valid(self, path):
        """
        验证RTF文件格式是否正确

        英文数据库的RTF文件应包含类似以下格式的行：
        | UID       | Nat       | 2nd Nat   | Name             |           |           |           |
        | -----------------------------------------------------------------------------------------|
        | 2000472008| ESP       | USA       | Pepe Sáenz       | 1         | 12        | 1         |
        | -----------------------------------------------------------------------------------------|
        | 2002161479| BRA       |           | José·Milhomem    | 1         | 16        | 3         |
        | -----------------------------------------------------------------------------------------|
        | 2002161482| BRA       |           | Juvenal Morais   | 1         | 5         | 1         |

        中文数据库的RTF文件应包含类似以下格式的行：
        | 编号       | 国籍/地区籍   | 第二国籍/地区籍 | 姓名                    |           |           |          |
        | ---------------------------------------------------------------------------------------------------|
        | 2002075172| 美国         |             | 扎克·布劳顿               | 3         | 9         | 0        |
        | ---------------------------------------------------------------------------------------------------|
        | 2002075152| 美国         |             | 哈尔特·哈勒               | 1         | 12        | 0        |
        | ---------------------------------------------------------------------------------------------------|
        | 2002072431| 孟加拉       | 美国         | Tayab Hasan Hasan       | 1         | 16        | 4        |
        """

        try:
            # 重置验证状态
            self.is_rtf_valid = False
            self.rtf_language = "Unknown"
            # 打开RTF文件进行读取，确保文件路径字符串正确编码（使用utf-8）
            normalized_path = path.encode('utf-8').decode('utf-8')
            with open(normalized_path, 'r', encoding="UTF-8") as rtf:
                # 读取RTF文件的前20行进行验证
                rtf_data = ''.join(islice(rtf, 20))
            # 检查RTF数据是否匹配预期的格式模式
            if self.rtf_regex.search(rtf_data) :
                self.rtf_language = "English"
                self.logger.info(f"The RTF file format is correct, and the RTF file data language is: {self.rtf_language}")
                self.is_rtf_valid = True
            elif self.rtf_regex_chn.search(rtf_data):
                self.rtf_language = "简体中文"
                self.logger.info(f"RTF文件格式正确，RTF文件数据语言为: {self.rtf_language}")
                self.is_rtf_valid = True
            else:
                self.logger.error("The RTF file is invalid or cannot be recognized.")
                self.is_rtf_valid = False
        except UnicodeDecodeError as e:
            self.logger.error(f"RTF file encoding error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error while validating RTF file: {e}")
            return False
        return self.is_rtf_valid

    def translate_rtf_data_to_english(self, rtf_data):
        """将传入的rtf_data数据的主要国籍以及第二国籍字段翻译为英文"""
        if self.rtf_language == "English":
            self.logger.info("The RTF data language is English, and does not need to be translated.")
            return rtf_data
        if not hasattr(self, '_translation_cache') or self._translation_cache.get('language') != self.rtf_language:
            translation_json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".config", "nat_translation.json")
            tr_map = {}
            try:
                with open(translation_json_path, "r", encoding="utf-8") as file:
                    self.logger.info(f"Loading translation file: {translation_json_path}")
                    translation_data = json.load(file)
                    tr_map = translation_data.get(self.rtf_language, {})
                    # 初始化并缓存翻译映射表
                    self._translation_cache = {
                        'language': self.rtf_language,
                        'map': tr_map
                    }
            except FileNotFoundError as e:
                self.logger.error(f"The nationality translation JSON not found: {e}")
                return rtf_data
            except json.JSONDecodeError as e:
                self.logger.error(f"The nationality translation JSON decoding error: {e}")
                return rtf_data
        else:
            tr_map = self._translation_cache['map']

        # 检查翻译映射表是否为空
        if not tr_map:
            self.logger.error("The nationality translation JSON is empty!")
            return rtf_data

        translated_data = []
        self.logger.info(f"Translating RTF data from {self.rtf_language} to English...")
        for record in rtf_data:
            # 字段顺序: [0]UID, [1]主要国籍, [2]第二国籍, [3]姓名, [4]头发长度, [5]头发颜色, [6]种族代码...
            uid = record[0]
            primary = record[1]
            second = record[2]
            # 翻译主要国籍和第二国籍，保持其他字段不变
            tr_primary = tr_map.get(primary.strip(), primary)
            tr_second = tr_map.get(second.strip(), second) if second else ""
            translated_record = [
                uid,
                tr_primary,
                tr_second
            ] + record[3:]  # 姓名、头发长度、头发颜色、肤色代码等其他字段保持不变
            translated_data.append(translated_record)
            self.logger.debug(f"Translating UID {uid}: '{primary}'->'{tr_primary}', '{second}'->'{tr_second}'")

        self.logger.info(f"Completed translating {len(translated_data)} records from RTF data.")
        return translated_data
