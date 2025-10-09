import re
import logging


class XmlParser:
    def __init__(self):
        self.uid_regex = re.compile(r'graphics/pictures/person/((?:r-)?\d{4,})/portrait')
        self.eth_img_regex = re.compile(r'(?<=from=")[^"]+(?=" to)')
        self.logger = logging.getLogger("NewGAN App")

    def parse_xml(self, path):
        """解析XML文件，提取用户ID、种族和图片路径"""
        result_data = {}
        try:
            with open(path, 'r', encoding="UTF-8") as xml:
                self.logger.info(f"Parsing config.xml file...")
                count = 0
                for line in xml:
                    uid_match = self.uid_regex.search(line)
                    if uid_match:
                        count += 1
                        uid = uid_match.group(1).strip()
                        eth_img_match = self.eth_img_regex.search(line)
                        if eth_img_match:
                            eth_img = eth_img_match.group(0).strip().split("/")
                            if len(eth_img) >= 2:
                                result_data[uid] = {
                                    "uid": uid,
                                    "ethnicity": eth_img[0],
                                    "image": eth_img[1]
                                }
                                self.logger.debug(f"Parsing XML {count} record: {result_data[uid]}")
        except FileNotFoundError:
            self.logger.error(f"File not found: {path}")
        except Exception as e:
            self.logger.error(f"Error occurred while processing config.xml file: {str(e)}")
        self.logger.info(f"Completed parsing config.xml, found {len(result_data)} records")
        return result_data

    def get_imgpath_from_uid(self, path, uid):
        """根据用户ID获取图片路径"""
        try:
            with open(path, 'r', encoding="UTF-8") as xml:
                for line in xml:
                    uid_match = self.uid_regex.search(line)
                    if uid_match and uid_match.group(1).strip() == uid:
                        eth_img_match = self.eth_img_regex.search(line)
                        if eth_img_match:
                            return eth_img_match.group(0).strip()
        except FileNotFoundError:
            self.logger.error(f"File not found: {path}")
        except Exception as e:
            self.logger.error(f"Error occurred while processing get_imgpath_from_uid: {str(e)}")
        return None
