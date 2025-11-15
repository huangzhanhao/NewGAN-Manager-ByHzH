import os
import logging
import shutil
from shutil import copyfileobj
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
