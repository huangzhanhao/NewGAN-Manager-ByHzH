import re
import logging


class XmlParser:
    def __init__(self):
        """初始化XML解析器，编译正则表达式"""
        self.uid_regex = re.compile(r'graphics/pictures/person/((?:r-)?\d{4,})/portrait')
        self.eth_img_regex = re.compile(r'(?<=from=")[^"]+(?=" to)')
        self.logger = logging.getLogger("NewGAN App")

    def parse_xml(self, path):
        """
        解析XML文件，提取用户ID、种族和图片路径
        :param path: XML文件路径
        :return: 包含用户信息的字典
        """
        result_data = {}
        try:
            with open(path, 'r', encoding="UTF-8") as xml:
                self.logger.info(f"开始解析XML文件: ")
                for line in xml:
                    try:
                        uid_match = self.uid_regex.search(line)
                        if uid_match:
                            uid = uid_match.group(1).strip()
                            print(uid_match)
                            print(uid)
                            eth_img_match = self.eth_img_regex.search(line)
                            if eth_img_match:
                                eth_img = eth_img_match.group(0).strip().split("/")
                                if len(eth_img) >= 2:
                                    result_data[uid] = {
                                        "uid": uid,
                                        "ethnicity": eth_img[0],
                                        "image": eth_img[1]
                                    }
                                    self.logger.debug(f"解析uid={uid}信息: {result_data[uid]}")
                    except Exception as e:
                        self.logger.warning(f"解析行时出错: {line[:50]}... 错误: {str(e)}")
                        continue

        except FileNotFoundError:
            self.logger.error(f"文件未找到: {path}")
        except Exception as e:
            self.logger.error(f"处理文件时发生错误: {str(e)}")
        finally:
            self.logger.info(f"已完成解析{path}内容，共找到{len(result_data)}条记录")
            return result_data

    def get_imgpath_from_uid(self, path, uid):
        """
        根据用户ID获取图片路径
        :param path: XML文件路径
        :param uid: 用户ID
        :return: 图片路径或None
        """
        try:
            with open(path, 'r', encoding="UTF-8") as xml:
                for line in xml:
                    try:
                        uid_match = self.uid_regex.search(line)
                        if uid_match and uid_match.group(1).strip() == uid:
                            eth_img_match = self.eth_img_regex.search(line)
                            if eth_img_match:
                                return eth_img_match.group(0).strip()
                    except Exception as e:
                        self.logger.warning(f"解析行时出错: {line[:50]}... 错误: {str(e)}")
                        continue

        except FileNotFoundError:
            self.logger.error(f"文件未找到: {path}")
        except Exception as e:
            self.logger.error(f"处理文件时发生错误: {str(e)}")
        
        return None
