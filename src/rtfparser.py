import re


class RTF_Parser:
    def __init__(self):
        pass

    def parse_rtf(self, path):
        """
        解析RTF文件，提取球员数据

        Args:
            path (str): RTF文件的路径

        Returns:
            list: 包含球员信息的列表，每个球员信息是一个包含以下元素的列表：
                  [UID, 主要国籍, 第二国籍, 肤色代码]
        """
        # 编译正则表达式用于匹配至少4位数字的UID
        UID_regex = re.compile(r"([0-9]){4,}")
        result_data = []

        # 以UTF-8编码打开RTF文件
        rtf = open(path, "r", encoding="UTF-8")
        # self.logger.info(rtf)
        rtf_data = []

        # 逐行读取文件，筛选包含UID的行
        for line in rtf:
            if UID_regex.search(line):
                # self.logger.info(line.strip())
                # 将包含UID的行添加到rtf_data列表中
                rtf_data.append(line.strip())

        # 处理每一行球员数据
        for newgen in rtf_data:
            # 使用管道符分割行数据
            data_fields = newgen.split("|")
            # 提取第二国籍（索引为3），并去除首尾空格
            sec_nat = data_fields[3].strip()
            # 如果第二国籍为空字符串，则设为None
            if sec_nat == "":
                sec_nat = None

            # 将处理后的球员数据添加到结果列表中
            # 数据包括：[UID, 主要国籍, 第二国籍, 肤色代码]
            result_data.append(
                [
                    data_fields[1].strip(),  # UID（索引1）
                    data_fields[2].strip(),  # 主要国籍（索引2）
                    sec_nat,  # 第二国籍（已处理）
                    data_fields[7].strip(),  # 肤色代码（索引7）
                ]
            )
        # 关闭文件
        rtf.close()
        # 返回解析后的球员数据列表
        return result_data

    def is_rtf_valid(self, path):
        """
        验证RTF文件格式是否正确

        RTF文件应包含类似以下格式的行：
        | UID       | Nat       | 2nd Nat   | Name                            |           |           |           |
        | 2000472008| ESP       | BAS       | Pepe Sáenz                      | 1         | 12        | 1         |

        正则表达式各部分说明：
        (\|\s*[0-9]{4,}\s*)            - 匹配UID字段（至少4位数字）
        (\|\s*([A-Z]{3})*\s*)+         - 匹配国家代码字段（3个大写字母）
        (\|[\s*\w*\.*\-*]+)            - 匹配名称字段（可包含字母、数字、空格、点和连字符）
        (\|[\s*\d+]+){3}               - 匹配后面3个数值字段
        \|                             - 结尾的管道符
        """
        # 使用原始字符串避免转义警告
        rtf_regex = re.compile(r'(\|\s*[0-9]{4,}\s*)'
                               r'(\|\s*([A-Z]{3})*\s*)+'
                               r'(\|[\s*\w*\.*\-*]+)'
                               r'(\|[\s*\d+]+){3}\|')
        rtf = open(path, 'r', encoding="UTF-8")
        rtf_data = rtf.read()
        rtf.close()
        if rtf_regex.search(rtf_data):
            return True
        return False
