import re
import logging
import os
import glob
import shutil
from shutil import copyfileobj
from datetime import datetime


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
            raise
        except Exception as e:
            self.logger.error(f"Error while parsing config.xml file: {e}")
            raise
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

    def _save_backup_config_xml(self, config_path, img_dir, logger):
        """
        Backup config.xml file and maintain only 10 most recent backups
        Args:
            config_path (str): Path to the config.xml file to backup
            img_dir (str): Image directory for storing backups
            logger (Logger): Logger instance for logging
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = os.path.join(img_dir, f"config备份_{timestamp}.xml")
        shutil.copy2(config_path, backup_path)
        # 最多保存10个备份文件，如果超过则删除最旧的备份
        backup_pattern = os.path.join(img_dir, "config备份_*.xml")
        backup_files = glob.glob(backup_pattern)
        if len(backup_files) > 10:
            backup_files.sort()
            files_to_remove = len(backup_files) - 10
            for i in range(files_to_remove):
                os.remove(backup_files[i])

    def write_xml(self, data, img_dir, root_dir, logger, save_backup=True):
        """
        Write config.xml file with player mappings
        Args:
            data (list): List of player mapping data
            img_dir (str): Image directory path
            root_dir (str): Root directory path
            logger (Logger): Logger instance for logging
            save_backup (bool): Whether to backup the original config.xml before writing
        Returns:
            list: List of XML strings that were written
        """
        config_path = os.path.join(img_dir, "config.xml")
        template_path = os.path.join(root_dir, ".config", "config_template")
        try:
            # Backup original config.xml if needed
            if save_backup and os.path.isfile(config_path):
                self._save_backup_config_xml(config_path, img_dir, logger)
            with open(template_path, "r", encoding="UTF-8") as fp:
                config_template = fp.read()
                xml_string = []
            for dat in data:
                xml_string.append(f'<record from="{dat[1]}/{dat[2]}" to="graphics/pictures/person/{dat[0]}/portrait"/>')
            xml_players = "\n                ".join(xml_string)
            xml_config = config_template.replace("[players]", xml_players)
            config_path = os.path.join(img_dir, "config.xml")
            with open(config_path, "w", encoding="UTF-8") as fp:
                fp.write(xml_config)
            return xml_string
        except FileNotFoundError:
            logger.error(f"Config_template file not found: {template_path}")
            raise
        except PermissionError as e:
            logger.error(f"Permission denied when accessing config.xml file: {e}")
            raise
        except OSError as e:
            logger.error(f"OS error occurred while writing config.xml file: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while writing config.xml file: {e}")
            raise

    def single_replacement_in_xml(self, player, img_dir, logger, save_backup=True):
        if not isinstance(player, (list, tuple)) or len(player) != 3:
            raise ValueError("Player must be a list or tuple with exactly three elements.")
        config_path = os.path.join(img_dir, "config.xml")
        uid = player[0]
        pack = player[1]
        image = player[2]
        target_substring = f'to="graphics/pictures/person/{uid}/portrait"'
        new_line = f'\n                <record from="{pack}/{image}" to="graphics/pictures/person/{uid}/portrait"/>'
        if not os.path.exists(config_path):
            logger.warning(f"config.xml not found at {config_path} - skipping")
            return
        try:
            # Backup original config.xml if needed
            if save_backup:
                self._save_backup_config_xml(config_path, img_dir, logger)
            with open(config_path, "r", encoding="UTF-8") as f:
                lines = f.readlines()
            # Replace the first matching line
            replaced = False
            for i, line in enumerate(lines):
                if target_substring in line:
                    lines[i] = new_line + '\n'  # readlines() keeps newlines, so preserve it
                    logger.info(f"Replaced uid:{uid} 's face to {pack}/{image} line in {config_path}")
                    replaced = True
                    break
            if not replaced:
                logger.info(f"No line found containing {uid} in {config_path}")
            # Write back
            with open(config_path, "w", encoding="UTF-8") as f:
                f.writelines(lines)
        except PermissionError as e:
            logger.error(f"Permission denied when accessing config.xml file: {e}")
            raise
        except OSError as e:
            logger.error(f"OS error occurred while reading/writing config.xml file: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while swapping XML files: {e}")
            raise
