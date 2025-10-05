import logging
import os
import random
from .XmlParser import XmlParser

class FaceMapper:
    def __init__(self, img_dir, prf_manager):
        self.img_dir = img_dir
        self.profile_manager = prf_manager
        self.eth_map = {}
        # 记录img_dir目录下所有子目录(种族分类)名称
        eth_dirs = [f.name for f in os.scandir(img_dir) if f.is_dir()]
        # 记录每个种族分类文件夹中的图片名称(不含扩展名)
        for dir in eth_dirs:
            dir_imgs = set([f.name.split('.')[0] for f in os.scandir(img_dir + dir) if f.is_file()])
            self.eth_map[dir] = dir_imgs
        self.logger = logging.getLogger('NewGAN App')

    def generate_mapping(self, rtf_data, mode, duplicates=True):
        """根据RTF数据生成球员面部图片映射关系
        
        Args:
            rtf_data: 球员数据列表
            mode (str): 处理模式，可选 "Preserve", "Overwrite" 或 "Generate"
            duplicates (bool): 是否允许重复使用图片，默认为True
            
        Returns:
            list: 包含球员ID、人种和图片文件名的映射列表
        """
        mapping = []
        xml_data = {}
        prf_imgs = []

        # 处理Preserve和Overwrite模式，先读取现有config.xml文件
        if mode in ["Preserve", "Overwrite"]:
            xml_parser = XmlParser()
            xml_data = xml_parser.parse_xml(os.path.join(self.img_dir, "config.xml"))
            prf_imgs = self.get_xml_images(xml_data)
            if not duplicates and mode == "Preserve":
                for eth in self.eth_map:
                    self.eth_map[eth] = self.eth_map[eth] - set(prf_imgs)
        self.logger.info(f"开始构建'球员-图片'映射关系，模式: {mode}...")
        # 根据模式选择处理方式
        if mode == "Preserve":
            mapping = self._process_preserve_mode(rtf_data, xml_data, duplicates)
        elif mode == "Overwrite":
            mapping = self._process_overwrite_mode(rtf_data, xml_data, duplicates)
        else:  # Generate模式
            mapping = self._process_generate_mode(rtf_data, duplicates)
                    
        self.logger.info(f"完成构建'球员-图片'映射关系，共 {len(mapping)}条记录")
        return mapping

    def correct_ethnic(self, player, temp_eth1, temp_eth2):
        """根据角色肤色代码修正种族分类
        
        Args:
            player: 角色数据
            temp_eth1: 临时种族1（基于主要国籍）
            temp_eth2: 临时种族2（基于第二国籍）
            
        Returns:
            str: 修正后的种族分类
        """
        skin_code = player[6]
        p_ethnic = temp_eth1  # 默认值
        
        if skin_code == "0":
            if "Scandinavian" in [temp_eth1, temp_eth2]:
                p_ethnic = "Scandinavian"
            elif "Caucasian" in [temp_eth1, temp_eth2]:
                p_ethnic = "Caucasian"
            else:
                p_ethnic = "Central European"
        elif skin_code in ["1"]:
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
        elif skin_code == "2":
            p_ethnic = "MESA" if "MESA" in [temp_eth1, temp_eth2] else "MENA"
        elif skin_code in ["3", "6", "8", "9"]:
            if "SAMed" in [temp_eth1, temp_eth2] and skin_code == "6":
                p_ethnic = "SAMed"
            elif "Seasian" in [temp_eth1, temp_eth2] and skin_code == "8":
                p_ethnic = "Seasian"
            elif "South American" in [temp_eth1, temp_eth2] and skin_code in ["3", "9"]:
                p_ethnic = "South American"
            else:
                p_ethnic = "African"
        elif skin_code == "4":
            p_ethnic = "MESA"
        elif skin_code == "5":
            p_ethnic = "Seasian"
        elif skin_code == "7":
            p_ethnic = "South American"
        elif skin_code == "10":
            if "MESA" in [temp_eth1, temp_eth2]:
                p_ethnic = "MESA"
            elif "Seasian" in [temp_eth1, temp_eth2]:
                p_ethnic = "Seasian"
            elif "South American" in [temp_eth1, temp_eth2]:
                p_ethnic = "South American"
            else:
                p_ethnic = "Asian"

        return p_ethnic

    def _process_preserve_mode(self, rtf_data, xml_data, duplicates):
        """处理Preserve模式逻辑"""
        mapping = []
        # 过滤掉XML中已存在的球员
        filtered_rtf = [p for p in rtf_data if p[0] not in xml_data]
        
        for player in filtered_rtf:
            player_mapping = self._build_player_mapping(player, duplicates)
            if player_mapping:
                mapping.append(player_mapping)
                
        # 添加XML中所有球员
        self.logger.debug(f"Preserve模式保留原有XML球员映射，共 {len(xml_data)} 条记录")
        for uid, values in xml_data.items():
            mapping.append([uid, values["ethnicity"], values["image"]])
            
        return mapping

    def _process_overwrite_mode(self, rtf_data, xml_data, duplicates):
        """处理Overwrite模式逻辑"""
        mapping = []
        
        for player in rtf_data:
            player_mapping = self._build_player_mapping(player, duplicates)
            if player_mapping:
                mapping.append(player_mapping)
                # 从XML数据中移除已处理的球员
                if player[0] in xml_data:
                    del xml_data[player[0]]
        
        # 添加剩余的XML球员
        self.logger.debug(f"Overwrite模式保留未处理的XML球员映射，共 {len(xml_data)} 条记录")
        for uid, values in xml_data.items():
            mapping.append([uid, values["ethnicity"], values["image"]])
            
        return mapping

    def _process_generate_mode(self, rtf_data, duplicates):
        """处理Generate模式逻辑"""
        return [self._build_player_mapping(p, duplicates) for p in rtf_data
                if self._build_player_mapping(p, duplicates) is not None]

    def _build_player_mapping(self, player, duplicates):
        """为单个球员构建映射关系"""
        # 获取临时种族分类
        n2_ethnic = self.profile_manager.get_ethnic(player[2]) if player[2] else None
        n1_ethnic = self.profile_manager.get_ethnic(player[1])
        
        if n1_ethnic is None:
            self.logger.warning(f"球员 {player[0]} 的主要国籍 {player[1]} 无对应种族映射，跳过")
            return None

        # 修正种族分类
        p_ethnic = self.correct_ethnic(player, n1_ethnic, n2_ethnic)
        if p_ethnic is None:
            self.logger.error(f"无法确定球员 {player[0]} 的种族分类，跳过")
            return None
            
        if p_ethnic not in self.eth_map:
            self.logger.error(f"种族分类 '{p_ethnic}' 无效，跳过球员 {player[0]}")
            return None
            
        # 获取图片池并选择图片
        image_pools = self._get_image_pool(p_ethnic, player[1])
        player_img = self.pick_image_from_pools(image_pools, duplicates)
        if player_img is None:
            self.logger.warning(f"人种分类 {p_ethnic} 无可用图片，跳过球员 {player[0]}")
            return None
        
        self.logger.debug(f"构建'球员-图片'映射关系: [{player[0]}, {p_ethnic}, {player_img}]")
        return [player[0], p_ethnic, player_img]

    def _get_image_pool(self, ethnicity, nationality):
        """获取优先级图片池：国籍文件夹 > 国籍+种族文件夹 > 默认池

        Returns:
            list: 优先级图片池列表
        """
        pools = []
        # 1. 国籍文件夹
        if nationality in self.eth_map and self.eth_map[nationality]:
            pools.append(self.eth_map[nationality])

        # 2. 种族文件夹
        if ethnicity in self.eth_map and self.eth_map[ethnicity]:
            pools.append(self.eth_map[ethnicity])

        # 3. 默认池：当国籍文件夹和种族文件夹都未包含在self.eth_map集合时，添加self.eth_map所有的文件夹到图片池
        if nationality not in self.eth_map and ethnicity not in self.eth_map:
            for eth in self.eth_map:
                pools.append(self.eth_map[eth])
        
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
        """从指定种族分类中选择一张图片（兼容旧版）"""
        return self.pick_image_from_pools([self.eth_map[ethnicity]], duplicates)

    def get_xml_images(self, xml_data):
        """从XML数据中提取已使用的图片列表"""
        return [i["image"] for i in xml_data.values()]
