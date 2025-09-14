import re


class XmlParser:
    def __init__(self):
        self.uid_regex = re.compile(r'graphics/pictures/person/(?:r-)?([0-9]{4,})/portrait')
        self.eth_img_regex = re.compile(r'((?<=from=\").*(?=\" to))')

    def parse_xml(self, path):
        result_data = {}
        try:
            with open(path, 'r', encoding="UTF-8") as xml:
                for line in xml:
                    uid_match = self.uid_regex.search(line)
                    if uid_match:
                        uid = uid_match.group(1).strip()
                        eth_img_match = self.eth_img_regex.search(line)
                        if eth_img_match:
                            eth_img = eth_img_match.group(0).strip().split("/")
                            # 添加了对分割结果的长度检查，确保数组访问安全
                            if len(eth_img) >= 2:
                                img = eth_img[1]
                                eth = eth_img[0]
                                result_data[uid] = {"ethnicity": eth, "image": img}
        except FileNotFoundError:
            # 文件未找到，返回空字典
            pass
        except Exception:
            # 其他异常，返回空字典
            pass
        return result_data

    def get_imgpath_from_uid(self, path, uid):
        try:
            with open(path, 'r', encoding="UTF-8") as xml:
                for line in xml:
                    uid_match = self.uid_regex.search(line)
                    if uid_match and uid_match.group(1).strip() == uid:
                        eth_img_match = self.eth_img_regex.search(line)
                        if eth_img_match:
                            return eth_img_match.group(0).strip()
        except FileNotFoundError:
            # 文件未找到，返回None
            pass
        except Exception:
            # 其他异常，返回None
            pass
        return None
