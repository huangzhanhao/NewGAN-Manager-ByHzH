from itertools import islice
import json
import logging
import re
import os


class RtfParser:
    def __init__(self):
        self.rtf_data = []
        self.rtf_language = "English"
        self.is_rtf_valid = False
        # 使用原始字符串避免转义警告
        # 正则表达式按照字段由前后"|"符号包围的逻辑设计
        self.UID_regex = re.compile(r"\|\s*[0-9]{4,}\s*\|")
        self.english_nat_regex = re.compile(r"^([A-Z]{3}|N/A|\s*)$")
        self.chinese_nat_regex = re.compile(r"\s*[\u4e00-\u9fff]+\s*")
        self.rtf_regex = re.compile(
            r"\|\s*[0-9]{4,}\s*\|"                  # UID字段(前后都有"|"符号)
            r"\s*[A-Z]{3}\s*\|"                     # 主要国籍字段(前后都有"|"符号)
            r"(\s*([A-Z]{3})?\s*\|)?"               # 可选的第二国籍字段(前后都有"|"符号)
            r"\s*[^|]+\s*\|"                        # 姓名字段(前后都有"|"符号)
            r"\s*[\d]+\s*\|"                        # 头发长度字段(前后都有"|"符号)
            r"\s*[\d]+\s*\|"                        # 头发颜色字段(前后都有"|"符号)
            r"\s*[\d]+\s*\|"                        # 人种肤色字段(前后都有"|"符号)
        )
        # 添加新的正则表达式用于匹配包含中文的RTF文件
        self.rtf_regex_chn = re.compile(
            r"\|\s*[0-9]{4,}\s*\|"                  # 编号字段(前后都有"|"符号)
            r"\s*[\u4e00-\u9fff]+\s*\|"             # 国籍/地区籍字段(前后都有"|"符号)
            r"\s*[\u4e00-\u9fff]*\s*\|"             # 第二国籍/地区籍字段(前后都有"|"符号)
            r"\s*[^|]+\s*\|"                        # 姓名字段(前后都有"|"符号)
            r"\s*[\d]+\s*\|"                        # 头发长度字段(前后都有"|"符号)
            r"\s*[\d]+\s*\|"                        # 头发颜色字段(前后都有"|"符号)
            r"\s*[\d]+\s*\|"                        # 人种肤色字段(前后都有"|"符号)
        )        
        self.logger = logging.getLogger("NewGAN App") 

    def parse_rtf(self, path):
        """
        解析RTF文件，提取球员数据

        Args:
            path (str): RTF文件的路径

        Returns:
            list: 包含球员信息的列表，每个球员信息是一个包含以下元素的列表：
                  [UID, 主要国籍, 第二国籍, 肤色代码] 或
                  [UID, 主要国籍, 第二国籍, 肤色代码, 是否为随机人, 面部, 俱乐部, 年龄, 身高, 体重]
        """
        # 先检查RTF文件有效性并确定语言
        self.check_rtf_valid(path)

        # 以UTF-8编码打开RTF文件并读取所有行
        with open(path, "r", encoding="UTF-8") as rtf:
            rtf_lines = rtf.readlines()

        # 筛选包含至少4位数字UID的有效数据行
        valid_lines = [line.strip() for line in rtf_lines if self.UID_regex.search(line)]

        # 处理每一行有效数据
        for line in valid_lines:
            # 使用管道符分割字段，并移除首尾空白字符
            fields = [f.strip() for f in line.split("|") if f]

            # 以下进行更详细的数据格式验证
            # 验证字段数量 - 我们需要至少7个字段
            if len(fields) < 7:
                msg = f"数据行缺少必要字段, 字段数量: {len(fields)}, 字段内容: {fields}"
                self.logger.error(msg)
                continue

            # 提取UID
            uid = fields[0]
            if not uid.isdigit():
                msg = f"无效的UID: {uid}"
                self.logger.error(msg)
                continue

            # 提取并验证主要国籍
            primary_nat = fields[1] if isinstance(fields[1], str) else ""
            if primary_nat == "" or (not self.english_nat_regex.match(primary_nat) and not self.chinese_nat_regex.match(primary_nat)):
                msg = f"无效的主要国籍代码: {primary_nat}"
                self.logger.warning(msg)

            # 提取并验证第二国籍
            sec_nat = fields[2] if isinstance(fields[2], str) else ""
            if not self.english_nat_regex.match(sec_nat) and not self.chinese_nat_regex.match(sec_nat):
                msg = f"无效的第二国籍代码: {sec_nat}"
                self.logger.warning(msg)

            # 提取并验证肤色代码
            skin_code = fields[6]
            if int(skin_code) < 0 or int(skin_code) > 10:
                msg = f"无效的肤色代码: {skin_code}"
                self.logger.error(uid)
                self.logger.error(msg)
                continue

            # 添加验证通过的数据
            base_data = [
                uid,
                primary_nat,
                sec_nat,
                skin_code
            ]

            # 处理附加字段
            if len(fields) > 7:
                # 对于新的游戏view模板，加入处理附加字段以应用新功能
                """
                新的view模板如下：
                | 编号        | 国籍/地区籍 | 第二国籍/地区籍 | 姓名              |      |      |      |      | 是否为随机人 | 面部  | 俱乐部       | 年龄  | 身高    | 体重  | 
                | ----------------------------------------------------------------------------------------------------------------------------------------------| 
                | 2000167433 | USA       | ARG          | Maximo Carrizo   | 1    | 12   | 0    | 5    | 否         |      |             | 20   | 165厘米 | 66公斤| 
                """

                # 根据模板，提取额外字段
                player_name = fields[3] if isinstance(fields[3], str) and not "" else ""
                hair_length = fields[4] if fields[4] != "" else ""
                hair_color = fields[5] if fields[5] != "" else ""
                is_random_person = fields[8] if len(fields) > 8 and fields[8] != "" else ""
                face = fields[9] if len(fields) > 9 and fields[9] != "" else ""
                club = fields[10] if len(fields) > 10 and fields[10] != "" else ""
                age = fields[11] if len(fields) > 11 and fields[11] != "" else ""
                height = fields[12] if len(fields) > 12 and fields[12] != "" else ""
                weight = fields[13] if len(fields) > 13 and fields[13] != "" else ""

                # 添加所有字段到结果数据
                detailed_data = [uid,
                primary_nat,
                sec_nat,
                skin_code, player_name, hair_length, hair_color, is_random_person, face, club, age, height, weight]
                self.rtf_data.append(detailed_data)
                self.logger.info("RTF数据: detailed_data", )
            else:
                # 只添加基本数据
                self.rtf_data.append(base_data)
                # self.logger.info("RTF数据: {}".format(base_data))

        # 如果没有找到有效数据
        if not self.rtf_data:
            msg = "RTF文件中未找到有效的球员数据"
            self.logger.warning(msg)

        # 确保返回英文数据
        # self.rtf_data = self.translate_rtf_data_to_english(self.rtf_data)
        return self.translate_rtf_data_to_english(self.rtf_data)

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
            # 确保路径字符串正确编码，路径编码使用utf-8
            normalized_path = path.encode('utf-8').decode('utf-8')
            with open(normalized_path, 'r', encoding="UTF-8") as rtf:
                # 读取rtf文件的前20行
                rtf_data = ''.join(islice(rtf, 20))
        except FileNotFoundError:
            self.logger.error(f"RTF file not found: {path}")
            return False
        except TypeError:
            self.logger.error(f"Invalid path type provided for RTF file: {path}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error while reading RTF file: {path}, Error: {str(e)}")
            return False

        # 检查RTF数据是否匹配预期的格式模式
        if self.rtf_regex.search(rtf_data) :
            self.rtf_language = "English"
            self.logger.info("The RTF file format is correct, and the RTF file data language is： %s", self.rtf_language)
            self.is_rtf_valid = True
            return self.is_rtf_valid

        elif self.rtf_regex_chn.search(rtf_data):
            self.rtf_language = "简体中文"
            self.logger.info("RTF文件格式正确，RTF文件数据语言为： %s", self.rtf_language)
            self.is_rtf_valid = True
            return self.is_rtf_valid

        else:
            self.logger.error("The RTF file is invalid and cannot be recognized.")
            self.is_rtf_valid = False

        return self.is_rtf_valid

    def translate_rtf_data_to_english(self, rtf_data):
        """
        将传入的rtf_data数据翻译为英文

        Args:
            rtf_data (list): 需要翻译的RTF数据列表

        Returns:
            list: 翻译后的rtf_data
        """
        if self.rtf_language == "English":
            self.logger.info("当前RTF数据语言为%s，无需翻译。" % self.rtf_language)
            return rtf_data

        translation_json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".config", "translation.json")
        try:
            with open(translation_json_path, "r", encoding="utf-8") as file:
                self.logger.info("Loading translation file from: %s", translation_json_path)
                translation_data = json.load(file)
                if self.rtf_language == "简体中文":
                    sim_map = translation_data.get("简体中文", {})
                    self.logger.info("Get translation data keys: %s", list(translation_data.keys()))
        except FileNotFoundError:
            self.logger.error("Translation mapping table file not found.")
            return rtf_data
        except json.JSONDecodeError:
            self.logger.error("Translation mapping table file parsing failed.")
            return rtf_data

        # 翻译数据：只翻译主要国籍(索引1)和第二国籍(索引2)，其他字段保持不变
        translated_data = []
        for record in rtf_data:
            # 期望 record 格式为 [UID, primary_nat, second_nat_or_None, name, hair_length, hair_color, eth_code, ...]
            uid = record[0] if len(record) > 0 else record
            primary = record[1] if len(record) > 1 else None
            second = record[2] if len(record) > 2 else None
            # 其他字段（姓名、头发长度、头发颜色、肤色代码等）保持不变
            rest = record[3:] if len(record) > 3 else []
            self.logger.info("Processing record: primary=%s, second=%s", primary, second)

            # 处理主要国籍
            if not isinstance(primary, str):
                tr_primary = primary
            elif primary != "":
                tr_primary = sim_map.get(primary.strip(), primary)
                self.logger.info("Translating primary nat: '%s' to '%s'", primary, tr_primary)
            else:
                tr_primary = ""

            # 处理第二国籍
            if not isinstance(second, str):
                tr_second = second
            elif second != "":
                tr_second = sim_map.get(second.strip(), second)
                self.logger.info("Translating second nat: '%s' to '%s'", second, tr_second)
            else:
                tr_second = ""

            # def translate_nat(nat, sim_map):
            #     if not isinstance(nat, str) or nat == "":
            #         return nat if nat != "" else ""
            #     return sim_map.get(nat.strip(), nat)
            #
            # tr_primary = translate_nat(primary, sim_map)
            # tr_second = translate_nat(second, sim_map)

            translated_record = [uid, tr_primary, tr_second] + rest
            translated_data.append(translated_record)

        self.logger.info("RTF data has been successfully translated into English!")
        return translated_data
