import os
import glob
import logging
import shutil
from shutil import copyfileobj
from datetime import datetime
from .ConfigManager import ConfigManager

class ProfileManager(ConfigManager):
    def __init__(self, name, root_dir):
        super().__init__()
        self.config = self.load_config(root_dir + "/.user/cfg.json")  # Load user configuration file  加载用户配置文件
        self.prf_cfg = self.load_config(root_dir + "/.user/" + name + ".json")  # Load profile-specific configuration file  加载特定的配置文件
        self.eth_cfg = self.load_config(root_dir + "/.config/eth_cfg.json")  # Load ethnic configuration file  加载民族配置文件
        self.cur_prf = name  # Set current profile name  设置当前配置文件名
        self.root_dir = root_dir  # Set root directory  设置根目录
        self.logger = logging.getLogger("NewGAN App")

    def migrate_config(self):
        if os.path.isfile("../.config/eth_cfg.json"):
            old_cfg = self.load_config("../.config/eth_cfg.json")
            if "Profile" in old_cfg:
                profiles = {}
                profiles["Profile"] = old_cfg["Profile"]
                self.save_config(self.root_dir + "/.user/cfg.json", profiles)
                del old_cfg["Profile"]
                self.save_config(self.root_dir + "/.config/eth_cfg.json", old_cfg)
                for profile in profiles["Profile"].keys():
                    with open(
                        self.root_dir + "/.user/" + profile + ".xml", "wb"
                    ) as output, open("../.config/" + profile + ".xml", "rb") as input:
                        copyfileobj(input, output)
                        os.remove("../.config/" + profile + ".xml")
                    with open(
                        self.root_dir + "/.user/" + profile + ".json", "wb"
                    ) as output, open("../.config/" + profile + ".json", "rb") as input:
                        copyfileobj(input, output)
                        os.remove("../.config/" + profile + ".json")
                shutil.rmtree("../.config/")

    def delete_profile(self, name):
        if name == "No Profile":
            self.logger.warning("Can't delete no profile")
            return False
        # 删除配置文件
        del self.config["Profile"][name]
        # try:
        #     os.remove(self.prf_cfg['img_dir']+"config.xml")
        # except OSError:
        #     self.logger.error(f"Error deleting config.xml, path: {self.prf_cfg['img_dir']+'config.xml'}")
        #     pass
        try:
            os.remove(self.root_dir + "/.user/" + name + ".json")
            os.remove(self.root_dir + "/.user/" + name + ".xml")
        except OSError as e:
            self.logger.error(f"Error deleting profile files: {e}")
            pass
        self.save_config(self.root_dir + "/.user/cfg.json", self.config)
        self.load_profile("No Profile")
        self.logger.info(f"Delete profile: {name}")
        return True

    def create_profile(self, name):
        self.config["Profile"][name] = True
        self.save_config(self.root_dir + "/.user/cfg.json", self.config)
        self.save_config(
            self.root_dir + "/.user/" + name + ".json",
            {"imgs": {}, "ethnics": {}, "img_dir": "", "rtf": ""},
        )
        try:
            with open(self.root_dir + "/.user/" + name + ".xml", "a"):
                self.load_profile(name)
                self.logger.info(f"Create new profile: {name}")
        except OSError:
            self.logger.error(f"Error creating profile file for: {name}")
            pass

    def load_profile(self, name):
        deact_img_dir = self.prf_cfg["img_dir"]
        self.prf_cfg = self.load_config(self.root_dir + "/.user/" + name + ".json")
        act_img_dir = self.prf_cfg["img_dir"]
        # 交换当前配置文件和新配置文件的XML配置
        self.swap_xml(self.cur_prf, name, deact_img_dir, act_img_dir)
        # 遍历所有配置文件，将当前配置文件设为激活状态，其他设为非激活状态
        for key in self.config["Profile"].keys():
            if key == name:
                # 将新配置文件设为激活状态
                self.config["Profile"][key] = True
            else:
                # 将其他配置文件设为非激活状态
                self.config["Profile"][key] = False
        self.cur_prf = name

    def _save_backup_config_xml(self, config_path):
        """
        Backup config.xml file and maintain only 10 most recent backups
        Args:
            config_path (str): Path to the config.xml file to backup
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = os.path.join(self.prf_cfg["img_dir"], f"config备份_{timestamp}.xml")
        shutil.copy2(config_path, backup_path)
        # 最多保存10个备份文件，如果超过则删除最旧的备份
        backup_pattern = os.path.join(self.prf_cfg["img_dir"], "config备份_*.xml")
        backup_files = glob.glob(backup_pattern)
        if len(backup_files) > 10:
            backup_files.sort()
            files_to_remove = len(backup_files) - 10
            for i in range(files_to_remove):
                os.remove(backup_files[i])

    def write_xml(self, data, save_backup=True):
        """
        Write config.xml file with player mappings
        Args:
            data (list): List of player mapping data
            save_backup (bool): Whether to backup the original config.xml before writing
        Returns:
            list: List of XML strings that were written
        """
        config_path = os.path.join(self.prf_cfg["img_dir"], "config.xml")
        template_path = os.path.join(self.root_dir, ".config", "config_template")
        try:
            # Backup original config.xml if needed
            if save_backup and os.path.isfile(config_path):
                self._save_backup_config_xml(config_path)
            with open(template_path, "r", encoding="UTF-8") as fp:
                config_template = fp.read()
                xml_string = []
            for dat in data:
                xml_string.append(f'<record from="{dat[1]}/{dat[2]}" to="graphics/pictures/person/{dat[0]}/portrait"/>')
            xml_players = "\n                ".join(xml_string)
            xml_config = config_template.replace("[players]", xml_players)
            config_path = os.path.join(self.prf_cfg["img_dir"], "config.xml")
            with open(config_path, "w", encoding="UTF-8") as fp:
                fp.write(xml_config)
            return xml_string
        except FileNotFoundError:
            self.logger.error(f"Config_template file not found: {template_path}")
            raise
        except PermissionError as e:
            self.logger.error(f"Permission denied when accessing config.xml file: {e}")
            raise
        except OSError as e:
            self.logger.error(f"OS error occurred while writing config.xml file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error while writing config.xml file: {e}")
            raise

    def single_replacement_in_xml(self, player, save_backup=True):
        if not isinstance(player, (list, tuple)) or len(player) != 3:
            raise ValueError("Player must be a list or tuple with exactly three elements.")
        config_path = os.path.join(self.prf_cfg["img_dir"], "config.xml")
        uid = player[0]
        pack = player[1]
        image = player[2]
        target_substring = f'to="graphics/pictures/person/{uid}/portrait"'
        new_line = f'\n                <record from="{pack}/{image}" to="graphics/pictures/person/{uid}/portrait"/>'
        if not os.path.exists(config_path):
            self.logger.warning(f"config.xml not found at {config_path} - skipping")
            return
        try:
            # Backup original config.xml if needed
            if save_backup:
                self._save_backup_config_xml(config_path)
            with open(config_path, "r", encoding="UTF-8") as f:
                lines = f.readlines()
            # Replace the first matching line
            replaced = False
            for i, line in enumerate(lines):
                if target_substring in line:
                    lines[i] = new_line + '\n'  # readlines() keeps newlines, so preserve it
                    self.logger.info(f"Replaced uid:{uid} 's face to {pack}/{image} line in {config_path}")
                    replaced = True
                    break
            if not replaced:
                self.logger.info(f"No line found containing {uid} in {config_path}")
            # Write back
            with open(config_path, "w", encoding="UTF-8") as f:
                f.writelines(lines)
        except PermissionError as e:
            self.logger.error(f"Permission denied when accessing config.xml file: {e}")
            raise
        except OSError as e:
            self.logger.error(f"OS error occurred while reading/writing config.xml file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error while swapping XML files: {e}")
            raise

    def swap_xml(self, deact_name, act_name, deact_img_dir, act_img_dir):
        """
        Swap XML files between deactivated and activated profiles           在停用和激活的配置文件之间交换XML文件
        Args:
            deact_name (str): Name of the profile being deactivated         要停用的配置文件名
            act_name (str): Name of the profile being activated             要激活的配置文件名
            deact_img_dir (str): Image directory of deactivated profile     停用配置文件的图像目录
            act_img_dir (str): Image directory of activated profile         激活配置文件的图像目录
        """
        try:
            if os.path.isfile(deact_img_dir+"config.xml"):
                with open(self.root_dir+'/.user/'+deact_name+'.xml', 'wb') as output, open(deact_img_dir+'config.xml', 'rb') as input:
                    copyfileobj(input, output)
            if os.path.isfile(act_img_dir+"config.xml"):
                with open(act_img_dir+'config.xml', 'wb') as output, open(self.root_dir+'/.user/'+act_name+'.xml', 'rb') as input:
                    copyfileobj(input, output)
        except (IOError, OSError) as e:
            self.logger.error(f"Error swapping XML files: {e}")

    def get_ethnic(self, nation):
        return self.eth_cfg["Ethnics"].get(nation, None)
