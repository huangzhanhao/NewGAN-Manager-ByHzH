import os
import random
import logging
from .XmlParser import XmlParser

class FaceMapper:
    def __init__(self, img_dir, prf_manager):
        self.img_dir = img_dir
        self.profile_manager = prf_manager
        self.faces_map = {}
        # 记录img_dir目录下所有子目录(种族分类)名称
        eth_dirs = [f.name for f in os.scandir(img_dir) if f.is_dir()]
        # 记录每个种族分类文件夹中的图片名称(不含扩展名)
        for dir in eth_dirs:
            dir_imgs = set([f.name.split('.')[0] for f in os.scandir(os.path.join(img_dir, dir)) if f.is_file()])
            self.faces_map[dir] = dir_imgs
        self.logger = logging.getLogger("NewGAN App")

    def generate_mapping(self, rtf_data, mode, duplicates=True, cancel_event=None):
        """根据RTF数据生成球员面部图片映射关系
        Args:
            rtf_data: 球员数据列表
            mode (str): 处理模式，可选 "Preserve", "Overwrite" 或 "Generate"
            duplicates (bool): 是否允许重复使用图片，默认为True
            cancel_event (threading.Event): 取消标志，置位后中断映射并返回None
        Returns:
            list: 包含球员ID、图像包和图像文件名的映射列表；被取消时返回None
        """
        def is_cancelled():
            return cancel_event is not None and cancel_event.is_set()

        mapping = []
        xml_data = {}
        prf_imgs = []
        if is_cancelled():
            self.logger.info("Mapping cancelled by user before start")
            return None
        # 处理Preserve和Overwrite模式，先读取现有config.xml文件
        if mode in ["Preserve", "Overwrite"]:
            xml_parser = XmlParser()
            xml_data = xml_parser.parse_xml(os.path.join(self.img_dir, "config.xml"))
            prf_imgs = self.get_xml_images(xml_data)
            if not duplicates and mode == "Preserve":
                for eth in self.faces_map:
                    self.faces_map[eth] = self.faces_map[eth] - set(prf_imgs)
        self.logger.info(f"Starting to build 'player-image' mapping, mode: {mode}...")
        # 根据模式选择处理方式
        if mode == "Preserve":
            mapping = self._process_preserve_mode(rtf_data, xml_data, duplicates, cancel_event)
        elif mode == "Overwrite":
            mapping = self._process_overwrite_mode(rtf_data, xml_data, duplicates, cancel_event)
        else:  # Generate模式
            mapping = self._process_generate_mode(rtf_data, duplicates, cancel_event)
        if mapping is None:
            return None
        self.logger.info(f"Completed building the 'player-image' mapping relationship, with a total of {len(mapping)} records")
        return mapping

    def correct_ethnic(self, player, temp_eth1, temp_eth2):
        """根据player的种族代码进行修正种族分类
        Args:
            player: 角色数据
            temp_eth1: 临时种族1（基于主要国籍）
            temp_eth2: 临时种族2（基于第二国籍）
        Returns:
            str: 修正后的种族分类
        """
        ethnicity_code = player[6]
        p_ethnic = temp_eth1  # 默认值
        
        if ethnicity_code == "0":
            if "Scandinavian" in [temp_eth1, temp_eth2]:
                p_ethnic = "Scandinavian"
            elif "Caucasian" in [temp_eth1, temp_eth2]:
                p_ethnic = "Caucasian"
            else:
                p_ethnic = "Central European"
        elif ethnicity_code in ["1"]:
            if "Caucasian" in [temp_eth1, temp_eth2]:
                p_ethnic = "Caucasian"
            elif "EECA" in [temp_eth1, temp_eth2]:
                p_ethnic = "EECA"
            elif "Italmed" in [temp_eth1, temp_eth2]:
                p_ethnic = "Italmed"
            elif "SAMed" in [temp_eth1, temp_eth2]:
                p_ethnic = "SAMed"
            elif "SpanMed" in [temp_eth1, temp_eth2]:
                p_ethnic = "SpanMed"
            elif "YugoGreek" in [temp_eth1, temp_eth2]:
                p_ethnic = "YugoGreek"
            elif "South American" in [temp_eth1, temp_eth2]:
                p_ethnic = "South American"
            else:
                p_ethnic = "Central European"
        elif ethnicity_code == "2":
            p_ethnic = "MESA" if "MESA" in [temp_eth1, temp_eth2] else "MENA"
        elif ethnicity_code in ["3", "6", "8", "9"]:
            if "SAMed" in [temp_eth1, temp_eth2] and ethnicity_code == "6":
                p_ethnic = "SAMed"
            elif "Seasian" in [temp_eth1, temp_eth2] and ethnicity_code == "8":
                p_ethnic = "Seasian"
            elif "South American" in [temp_eth1, temp_eth2] and ethnicity_code in ["3", "9"]:
                p_ethnic = "South American"
            else:
                p_ethnic = "African"
        elif ethnicity_code == "4":
            p_ethnic = "MESA"
        elif ethnicity_code == "5":
            p_ethnic = "Seasian"
        elif ethnicity_code == "7":
            p_ethnic = "South American"
        elif ethnicity_code == "10":
            if "MESA" in [temp_eth1, temp_eth2]:
                p_ethnic = "MESA"
            elif "Seasian" in [temp_eth1, temp_eth2]:
                p_ethnic = "Seasian"
            elif "South American" in [temp_eth1, temp_eth2]:
                p_ethnic = "South American"
            else:
                p_ethnic = "Asian"
        return p_ethnic

    def _process_preserve_mode(self, rtf_data, xml_data, duplicates, cancel_event=None):
        """处理Preserve模式逻辑"""
        mapping = []
        # 过滤掉XML中已存在的球员
        filtered_rtf = [p for p in rtf_data if p[0] not in xml_data]
        for player in filtered_rtf:
            if cancel_event is not None and cancel_event.is_set():
                self.logger.info("Mapping cancelled by user")
                return None
            player_to_mapping = self._build_player_mapping(player, duplicates)
            if player_to_mapping:
                mapping.append(player_to_mapping)
        self.logger.info(f"The 'Preserve' mode builds new 'player-image' mappings, with a total of {len(mapping)} new records.")
        # 添加XML中所有球员
        self.logger.info(f"The 'Preserve' mode preserves the 'player-image' mapping in the original XML file, with a total of {len(xml_data)} records.")
        for uid, values in xml_data.items():
            mapping.append([uid, values["ethnicity"], values["image"]])
        return mapping

    def _process_overwrite_mode(self, rtf_data, xml_data, duplicates, cancel_event=None):
        """处理Overwrite模式逻辑"""
        mapping = []
        for player in rtf_data:
            if cancel_event is not None and cancel_event.is_set():
                self.logger.info("Mapping cancelled by user")
                return None
            player_to_mapping = self._build_player_mapping(player, duplicates)
            if player_to_mapping:
                mapping.append(player_to_mapping)
                # 从XML数据中移除已处理的球员
                if player[0] in xml_data:
                    del xml_data[player[0]]
        self.logger.info(f"The 'Overwrite' mode rebuilds new 'player-image' mappings for players that existing in original XML file, with a total of {len(mapping)} new records.")
        # 添加剩余的XML球员
        self.logger.info(f"The 'Overwrite' mode preserves unprocessed 'player-image' mapping from the original XML file, with a total of {len(xml_data)} records.")
        for uid, values in xml_data.items():
            mapping.append([uid, values["ethnicity"], values["image"]])
        return mapping

    def _process_generate_mode(self, rtf_data, duplicates, cancel_event=None):
        """处理Generate模式逻辑"""
        mapper = []
        for player in rtf_data:
            if cancel_event is not None and cancel_event.is_set():
                self.logger.info("Mapping cancelled by user")
                return None
            # 每个球员只构建一次映射（此前写法在条件与取值处各调用一次，
            # 关闭 Allow Duplicates 时会导致图片池被过度消耗）
            player_to_mapping = self._build_player_mapping(player, duplicates)
            if player_to_mapping is not None:
                mapper.append(player_to_mapping)
        self.logger.info(f"The 'Generate' mode builds 'player-image' mappings in the new XML file, with a total of {len(mapper)} records.")
        return mapper

    def _build_player_mapping(self, player, duplicates):
        """为单个球员构建映射关系"""
        # 获取临时种族分类
        n2_ethnic = self.profile_manager.get_ethnic(player[2]) if player[2] else None
        n1_ethnic = self.profile_manager.get_ethnic(player[1])
        if n1_ethnic is None:
            self.logger.warning(f"Player {player[0]}'s primary nationality {player[1]} is None - skipping")
            return None
        # 修正种族分类
        p_ethnic = self.correct_ethnic(player, n1_ethnic, n2_ethnic)
        if p_ethnic is None:
            self.logger.error(f"Unable to determine the ethnicity of player {player[0]} - skipping")
            return None
        if p_ethnic not in self.faces_map:
            self.logger.error(f"Player {player[0]}'s ethnicity '{p_ethnic}' is not in face pack - skipping")
            return None
        # 获取图片池并选择图片
        image_pools = self._get_image_pool(p_ethnic, player[1])
        player_img = self.pick_image_from_pools(image_pools, duplicates)
        if player_img is None:
            self.logger.warning(f"Player {player[0]}'s ethnicity pack {image_pools} has no available images - skipping")
            return None
        self.logger.debug(f"Builded 'player-image' mapping: [ {player[0]} - {p_ethnic} - {player_img} ]")
        return [player[0], p_ethnic, player_img]

    def _get_image_pool(self, ethnicity, nationality):
        """获取优先级图片池：国籍文件夹 > 国籍+种族文件夹 > 默认池"""
        pools = []
        # 1. 国籍文件夹
        if nationality in self.faces_map and self.faces_map[nationality]:
            pools.append(self.faces_map[nationality])
        # 2. 种族文件夹
        if ethnicity in self.faces_map and self.faces_map[ethnicity]:
            pools.append(self.faces_map[ethnicity])
        # 3. 默认池：当国籍文件夹和种族文件夹都未包含在头像包(self.face_map集合)内时，添加self.face_map所有的文件夹到图片池
        if nationality not in self.faces_map and ethnicity not in self.faces_map:
            for eth in self.faces_map:
                pools.append(self.faces_map[eth])
        return pools

    def pick_image_from_pools(self, pools, duplicates):
        """从多个图片池中选择一张图片"""
        for pool in pools:
            if pool:  # 检查池是否非空
                choice = random.choice(tuple(pool))
                if not duplicates:
                    pool.remove(choice)
                return choice
        return None
        
    def pick_image(self, ethnicity, duplicates):
        """从指定种族分类中选择一张图片(兼容旧版)"""
        try:
            return self.pick_image_from_pools([self.faces_map[ethnicity]], duplicates)
        except KeyError:
            self.logger.error(f"Ethnicity '{ethnicity}' not found in face_map")
            return None

    def get_xml_images(self, xml_data):
        """从XML数据中提取已使用的图片列表"""
        return [i["image"] for i in xml_data.values()]
