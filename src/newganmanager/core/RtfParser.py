from itertools import islice
import json
import logging
import re
import os
from turtle import st


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

    def parse_rtf(self, path):
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
        # if not self.check_rtf_valid(path):
        #     self.logger.error("无效的RTF文件格式")
        #     return []
        
        # 重置数据
        self.rtf_data = []
        
        try:
            line_count = 0
            with open(path, "r", encoding="UTF-8") as rtf:
                self.logger.info(f"正在处理RTF文件: ")
                for line in rtf:
                    line_count += 1
                    
                    # 跳过空行
                    if not line.strip():
                        continue
                    
                    # 使用正则匹配有效数据行
                    if self.rtf_regex.search(line) or self.rtf_regex_chn.search(line):
                        try:
                            # 分割字段并去除空白，但保留空值字段
                            fields = [f.strip() for f in line.split("|")]
                            # 移除第一个和最后一个空字段（来自行首行尾的分隔符）
                            fields = fields[1:-1] if len(fields) >= 2 else []
                            
                            # 验证字段数量
                            if len(fields) < 7:
                                self.logger.warning(f"行 {line_count}: 字段不足 ({len(fields)}/7) - 跳过")
                                continue
                            
                            # 提取核心字段（按新顺序）
                            uid = fields[0]
                            primary_nat = fields[1]
                            sec_nat = fields[2] if len(fields) > 2 else ""
                            player_name = fields[3] if len(fields) > 3 else ""
                            hair_length = fields[4] if len(fields) > 4 else ""
                            hair_color = fields[5] if len(fields) > 5 else ""
                            skin_code = fields[6] if len(fields) > 6 else ""
                            
                            # 验证UID
                            if not uid.isdigit():
                                self.logger.info(f"行 {line_count}: 无效的UID - 跳过")
                                continue
                            else:
                                # 默认为随机人编号，添加r-前缀
                                uid = str("r-" + uid)
                            
                            # 验证肤色代码
                            skin_code_valid = True
                            try:
                                skin_code_int = int(skin_code)
                                if skin_code_int < 0 or skin_code_int > 10:
                                    self.logger.info(f"行 {line_count}: 肤色代码超出范围(0-10) - 跳过")
                                    skin_code_valid = False
                            except ValueError:
                                self.logger.info(f"行 {line_count}: 肤色代码必须为整数 - 跳过")
                                skin_code_valid = False
                            
                            if not skin_code_valid:
                                continue
                            
                            # 创建基础数据记录（按新顺序）
                            base_data = [
                                uid,
                                primary_nat,
                                sec_nat,
                                player_name,
                                hair_length,
                                hair_color,
                                skin_code
                            ]
                            
                            # 处理附加字段（如果有）
                            if len(fields) > 7:
                                # 处理可能的零宽空格字符
                                if len(fields) >12 and ("\u200b" in fields[11] or "\u200b" in fields[12]):
                                    fields[11] = fields[11].replace("\u200b", "")
                                    fields[12] = fields[12].replace("\u200b", "")
                                # 从附加字段判断是否属于随机人，处理UID中的"r-"前缀
                                if len(fields) > 13 and ("No" in fields[13] or "否" in fields[13]):
                                    base_data[0] = uid.replace("r-", "")  # 更新UID
                                # 提取附加字段
                                additional_fields = fields[7:]
                                # 创建详细数据记录
                                detailed_data = base_data + additional_fields
                                self.rtf_data.append(detailed_data)
                                self.logger.debug(f"添加详细数据: {detailed_data}")
                            else:
                                # 添加基础数据
                                self.rtf_data.append(base_data)
                                self.logger.debug(f"添加基础数据: {base_data}")
                                
                        except ValueError as ve:
                            self.logger.error(f"行 {line_count}: {str(ve)} - 跳过")
                        except Exception as e:
                            self.logger.error(f"行 {line_count}: 处理错误 - {str(e)}")
            
            self.logger.info(f"成功处理 {len(self.rtf_data)} 条有效记录")
            
        except FileNotFoundError:
            self.logger.error(f"RTF文件未找到: {path}")
            return []
        except UnicodeDecodeError:
            self.logger.error(f"RTF文件编码错误: {path}, 请检查文件编码格式")
            return []
        except Exception as e:
            self.logger.error(f"处理RTF文件时发生错误: {path}, 错误信息: {str(e)}")
            return []

        # 如果没有找到有效数据
        if not self.rtf_data:
            msg = "RTF文件中未找到有效的球员数据"
            self.logger.warning(msg)

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
            self.logger.info(f"The RTF file format is correct, and the RTF file data language is: {self.rtf_language}")
            self.is_rtf_valid = True
            return self.is_rtf_valid

        elif self.rtf_regex_chn.search(rtf_data):
            self.rtf_language = "简体中文"
            self.logger.info(f"RTF文件格式正确，RTF文件数据语言为: {self.rtf_language}")
            self.is_rtf_valid = True
            return self.is_rtf_valid

        else:
            self.logger.error("The RTF file is invalid and cannot be recognized.")
            self.is_rtf_valid = False

        return self.is_rtf_valid

    def translate_rtf_data_to_english(self, rtf_data):
        """
        将传入的rtf_data数据翻译为英文
        字段顺序为 [UID, 主要国籍, 第二国籍, 姓名, 头发长度, 头发颜色, 种族代码, ...]

        Args:
            rtf_data (list): 需要翻译的RTF数据列表

        Returns:
            list: 翻译后的rtf_data
        """
        if self.rtf_language == "English":
            self.logger.info("当前RTF数据语言为英文，无需翻译")
            return rtf_data
        # 检查是否已有缓存且语言匹配，避免重复加载翻译文件
        if not hasattr(self, '_translation_cache') or self._translation_cache.get('language') != self.rtf_language:
            translation_json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".config", "translation.json")
            tr_map = {}
            try:
                with open(translation_json_path, "r", encoding="utf-8") as file:
                    self.logger.info(f"加载翻译文件: {translation_json_path}")
                    translation_data = json.load(file)
                    tr_map = translation_data.get(self.rtf_language, {})
                    # 初始化并缓存翻译映射表
                    self._translation_cache = {
                        'language': self.rtf_language,
                        'map': tr_map
                    }
            except FileNotFoundError:
                self.logger.error(f"翻译映射表文件未找到: {translation_json_path}")
                return rtf_data
            except json.JSONDecodeError:
                self.logger.error(f"翻译映射表文件解析失败: {translation_json_path}")
                return rtf_data
        else:
            # 使用缓存的翻译映射表，避免重复加载翻译文件
            tr_map = self._translation_cache['map']

        # 检查翻译映射表是否为空
        if not tr_map:
            self.logger.error("翻译映射表为空!")
            return rtf_data

        translated_data = []
        for record in rtf_data:
            try:
                # 字段顺序: [0]UID, [1]主要国籍, [2]第二国籍, [3]姓名, [4]头发长度, [5]头发颜色, [6]种族代码...
                uid = record[0]
                primary = record[1]
                second = record[2]
                # 翻译主要国籍和第二国籍
                tr_primary = tr_map.get(primary.strip(), primary)
                tr_second = tr_map.get(second.strip(), second) if second else ""
                # 创建翻译后的记录，保持其他字段不变
                translated_record = [
                    uid,
                    tr_primary,
                    tr_second
                ] + record[3:]  # 姓名、头发长度、头发颜色、肤色代码等其他字段保持不变
                translated_data.append(translated_record)
                self.logger.debug(f"翻译UID {uid}: '{primary}'->'{tr_primary}', '{second}'->'{tr_second}'")            
            except IndexError:
                self.logger.error(f"rtf记录格式错误: {record}")
            except Exception as e:
                self.logger.error(f"翻译rtf记录时出错: {str(e)}")

        self.logger.info(f"成功将 {len(translated_data)} 条记录翻译为英文")
        return translated_data
