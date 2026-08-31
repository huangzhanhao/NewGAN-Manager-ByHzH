import os
import logging
import shutil
from shutil import copyfileobj
from .ConfigManager import ConfigManager

class ProfileManager(ConfigManager):
    def __init__(self, name, root_dir, data_dir=None):
        """
        Args:
            name (str): 当前 Profile 名称
            root_dir (str): 应用资源目录（.config 下的只读配置随程序分发）
            data_dir (str): 用户数据目录（.user 运行时数据，来自 paths.data；
                            缺省时与 root_dir 相同，兼容旧布局/测试）
        """
        super().__init__()
        self.root_dir = root_dir
        self.data_dir = data_dir if data_dir is not None else root_dir
        self.config = self.load_config(self.user_path("cfg.json"))  # Load user configuration file  加载用户配置文件
        self.prf_cfg = self.load_config(self.user_path(name + ".json"))  # Load profile-specific configuration file  加载特定的配置文件
        self.eth_cfg = self.load_config(os.path.join(root_dir, ".config", "eth_cfg.json"))  # Load ethnic configuration file  加载民族配置文件
        self.cur_prf = name  # Set current profile name  设置当前配置文件名
        self.logger = logging.getLogger("NewGAN App")

    def user_path(self, filename):
        """返回用户数据目录（data_dir/.user）下指定文件的路径"""
        return os.path.join(self.data_dir, ".user", filename)

    def migrate_config(self):
        if os.path.isfile("../.config/eth_cfg.json"):
            old_cfg = self.load_config("../.config/eth_cfg.json")
            if "Profile" in old_cfg:
                profiles = {}
                profiles["Profile"] = old_cfg["Profile"]
                self.save_config(self.user_path("cfg.json"), profiles)
                del old_cfg["Profile"]
                self.save_config(os.path.join(self.root_dir, ".config", "eth_cfg.json"), old_cfg)
                for profile in profiles["Profile"].keys():
                    with open(
                        self.user_path(profile + ".xml"), "wb"
                    ) as output, open("../.config/" + profile + ".xml", "rb") as input:
                        copyfileobj(input, output)
                        os.remove("../.config/" + profile + ".xml")
                    with open(
                        self.user_path(profile + ".json"), "wb"
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
        try:
            os.remove(self.user_path(name + ".json"))
            os.remove(self.user_path(name + ".xml"))
        except OSError as e:
            self.logger.error(f"Error deleting profile files: {e}")
            pass
        self.save_config(self.user_path("cfg.json"), self.config)
        self.load_profile("No Profile")
        self.logger.info(f"Delete profile: {name}")
        return True

    def create_profile(self, name):
        self.config["Profile"][name] = True
        self.save_config(self.user_path("cfg.json"), self.config)
        self.save_config(
            self.user_path(name + ".json"),
            {"imgs": {}, "ethnics": {}, "img_dir": "", "rtf": ""},
        )
        try:
            with open(self.user_path(name + ".xml"), "a"):
                self.load_profile(name)
                self.logger.info(f"Create new profile: {name}")
        except OSError:
            self.logger.error(f"Error creating profile file for: {name}")
            pass

    def load_profile(self, name):
        deact_img_dir = self.prf_cfg["img_dir"]
        self.prf_cfg = self.load_config(self.user_path(name + ".json"))
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
                with open(self.user_path(deact_name + '.xml'), 'wb') as output, open(deact_img_dir+'config.xml', 'rb') as input:
                    copyfileobj(input, output)
            if os.path.isfile(act_img_dir+"config.xml"):
                with open(act_img_dir+'config.xml', 'wb') as output, open(self.user_path(act_name + '.xml'), 'rb') as input:
                    copyfileobj(input, output)
        except (IOError, OSError) as e:
            self.logger.error(f"Error swapping XML files: {e}")

    def get_ethnic(self, nation):
        return self.eth_cfg["Ethnics"].get(nation, None)
