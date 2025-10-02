import logging
from .RtfParser import RtfParser
from .Mapper import Mapper
from .ProfileManager import ProfileManager


class ReplaceFaceHandler:
    def __init__(self, profile_manager: ProfileManager):
        self.profile_manager = profile_manager
        self.logger = logging.getLogger("NewGAN App")

    def replace_faces(self, rtf_file: str, img_dir: str, profile: str, mode: str, allow_duplicates: bool = False, progress_value: int = 20) -> bool:
        """
        替换面部图片的核心方法
        
        Args:
            rtf_file: RTF文件路径
            img_dir: 图片目录路径
            profile: 配置文件名称
            mode: 处理模式（Preserve/Overwrite/Generate）
            allow_duplicates: 是否允许重复使用图片
            progress_value: 进展值
            
        Returns:
            bool: 是否成功完成替换
        """
        try:
            self.logger.info("开始替换头像图片")
            self.logger.info(f"RTF文件: {rtf_file}")
            self.logger.info(f"图片目录: {img_dir}")
            self.logger.info(f"配置文件: {profile}")
            self.logger.info(f"处理模式: {mode}")
            self.logger.info(f"允许重复: {allow_duplicates}")

            # 1. 使用RtfParser解析RTF文件
            rtf_parser = RtfParser()
            
            if not rtf_parser.check_rtf_valid(rtf_file):
                self.logger.error(f"RTF文件格式无效: {rtf_file}")
                return False

            rtf_data = rtf_parser.parse_rtf(rtf_file)
            if not rtf_data:
                return False

            # 2. 使用Mapper生成映射数据
            mapper = Mapper(img_dir, self.profile_manager)
            mapping_data = mapper.generate_mapping(rtf_data, mode, allow_duplicates)
            if not mapping_data:
                return False

            # 3. 将映射数据写入config.xml文件
            self.profile_manager.write_xml(mapping_data)
            self.logger.info(f"成功写入config.xml文件，包含 {len(mapping_data)} 条映射记录")
            self.logger.info("头像图片替换完成")
            return True

        except Exception as e:
            self.logger.error(f"替换头像图片时发生错误: {str(e)}")
            return False