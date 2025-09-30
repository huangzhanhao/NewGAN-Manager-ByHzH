import logging
import os
import random
from .XmlParser import XmlParser


class Mapper:
    def __init__(self, img_dir, prf_manager):
        self.img_dir = img_dir
        self.profile_manager = prf_manager
        self.eth_map = {}
        eth_dirs = [f.name for f in os.scandir(img_dir) if f.is_dir()]
        for dir in eth_dirs:
            dir_imgs = set([f.name.split('.')[0] for f in os.scandir(img_dir+dir) if f.is_file()])
            self.eth_map[dir] = dir_imgs

        logger = logging.getLogger('NewGAN App')
        self.logger = logger

    def generate_mapping(self, rtf_data, mode, duplicates=False):
        mapping = []
        prf_imgs = []
        xml_data = {}

        if mode in ["Preserve", "Overwrite"]:
            xml_parser = XmlParser()
            xml_data = xml_parser.parse_xml(self.img_dir+"config.xml")
            prf_imgs = self.get_xml_images(xml_data)

            if not duplicates:
                for eth in self.eth_map:
                    self.eth_map[eth] = self.eth_map[eth] - set(prf_imgs)

        for i, player in enumerate(rtf_data):
            p_ethnic = None
            n2_ethnic = None
            if player[2]:
                n2_ethnic = self.profile_manager.get_ethnic(player[2])
            n1_ethnic = self.profile_manager.get_ethnic(player[1])
            if n1_ethnic is None:
                self.logger.info("Mapping for {} is missing. Skipping player {}".format(player[1], player[0]))
                continue
            self.logger.info("{}/{}: {}, {}, {}".format(i+1, len(rtf_data), player, n1_ethnic, n2_ethnic))
            # if player is in config.xml and we use preserver or overwrite handle it properly
            if player[0] in xml_data:
                if mode == "Preserve":
                    self.logger.info("Preserve: {} {} {}".format(player[0], xml_data[player[0]]["ethnicity"], xml_data[player[0]]["image"]))
                    continue
                elif mode == "Overwrite":
                    prf_imgs.remove(xml_data[player[0]]["image"])
                    del xml_data[player[0]]
            if player[6] == "1":
                if "Scandinavian" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "South American"
                if "Seasian" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "South American"
                if "Central European" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "South American"
                if "Caucasian" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "South American"
                if "African" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "South American"
                if "Asian" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "South American"
                if "MENA" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "South American"
                if "MESA" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "South American"
                if "EECA" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "EECA"
                if "Italmed" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "Italmed"
                if "SAMed" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "SAMed"
                if "SpanMed" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "SpanMed"
                if "YugoGreek" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "YugoGreek"
                if "South American" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "South American"
            elif player[6] in ["3", "6", "7", "8", "9"]:
                # SAMed with 7 is light-skinned
                if "SAMed" == n1_ethnic and player[6] == "7":
                    p_ethnic = "SAMed"
                # South American with 7 is light-skinned
                elif "South American" == n1_ethnic and player[6] == "7":
                    p_ethnic = "South American"
                else:
                    p_ethnic = "African"
            elif player[6] == "10":
                if "South American" == n1_ethnic:
                    p_ethnic = "South American"
                else:
                    p_ethnic = "Asian"
            elif player[6] == "2":
                p_ethnic = "MENA"
                if "MESA" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "MESA"
            elif player[6] == "5":
                p_ethnic = "Seasian"
            elif player[6] == "0":
                p_ethnic = "Central European"
                if "Scandinavian" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "Scandinavian"
                elif "Caucasian" in [n1_ethnic, n2_ethnic]:
                    p_ethnic = "Caucasian"
            elif player[6] == "4":
                p_ethnic = "MESA"

            # 确保p_ethnic不为None
            if p_ethnic is None:
                self.logger.error(f"无法确定球员 {player[0]} 的人种分类，跳过该球员")
                continue
                
            # 检查人种分类是否有效
            if p_ethnic not in self.eth_map:
                self.logger.error(f"人种分类 '{p_ethnic}' 无效或未配置图片目录，跳过球员 {player[0]}")
                continue
                
            # 基于人种分类选择图片
            player_img = self.pick_image(p_ethnic, duplicates)
            if player_img is None:
                self.logger.info("人种分类 {} 没有可用面部图片，跳过球员 {}".format(p_ethnic, player[0]))
                continue
                
            prf_imgs.append(player_img)
            mapping.append([player[0], p_ethnic, player_img])
        if mode in ["Overwrite", "Preserve"]:
            self.post_rtf_hook(mapping, prf_imgs, xml_data)
        return mapping

    def get_xml_images(self, xml_data):
        return [i["image"] for i in xml_data.values()]

    def pick_image(self, ethnicity, duplicates=False):
        selection_pool = self.eth_map[ethnicity]
        if len(selection_pool) == 0:
            return None
        choice = random.choice(tuple(selection_pool))

        if not duplicates:
            selection_pool.remove(choice)

        return choice

    def post_rtf_hook(self, mapping, prf_imgs, xml_data):
        for uid, values in xml_data.items():
            p_ethnic = values["ethnicity"]
            player_img = values["image"]
            mapping.append([uid, p_ethnic, player_img])
