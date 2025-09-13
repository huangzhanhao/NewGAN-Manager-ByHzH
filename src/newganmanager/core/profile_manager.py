from .config_manager import Config_Manager
import os
import logging
from shutil import copyfileobj
import shutil


class Profile_Manager(Config_Manager):
    def __init__(self, name, root_dir):
        """
        Initialize the Profile Manager  初始化配置文件管理器

        Args:
            name (str): Profile name to load initially  要初始加载的配置文件名
            root_dir (str): Root directory of the application   应用程序的根目录
        """
        super().__init__()
        # Load user configuration file  加载用户配置文件
        self.config = self.load_config(root_dir + "/.user/cfg.json")
        # Load profile-specific configuration file  加载特定的配置文件
        self.prf_cfg = self.load_config(root_dir + "/.user/" + name + ".json")
        # Load ethnic configuration file  加载民族配置文件
        self.eth_cfg = self.load_config(root_dir + "/.config/eth_cfg.json")
        # Set current profile name  设置当前配置文件名
        self.cur_prf = name
        # Set application root directory  设置应用程序根目录
        self.root_dir = root_dir

        self.logger = logging.getLogger("NewGAN App")

        self.config_manager = Config_Manager()

    def migrate_config(self):
        """
        Migrate configuration files from old format to new format

        This method checks for old configuration files in the legacy "../.config/" directory,
        and migrates them to the new structure in the ".user/" and ".config/" directories.
        It handles profile data, XML files, and JSON configuration files.

        The migration process:
        1. Checks if old config file exists
        2. Extracts profile information
        3. Saves profile data to new location
        4. Updates old config file
        5. Moves XML and JSON profile files
        6. Removes old config directory
        """
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
        """
        Delete a profile by name    根据名称删除配置文件

        Args:
            name (str): Name of the profile to delete   要删除的配置文件名

        Returns:
            bool: True if deletion was successful, False otherwise  如果删除成功则返回True，否则返回False
        """
        # self.logger.info("Delete profile: {}".format(name))
        if name == "No Profile":
            # self.logger.info("Can't delete no profile")
            return False
        del self.config["Profile"][name]
        try:
            os.remove(self.prf_cfg["img_dir"] + "config.xml")
        except OSError:
            pass
        try:
            os.remove(self.root_dir + "/.user/" + name + ".json")
            os.remove(self.root_dir + "/.user/" + name + ".xml")
        except OSError:
            pass
        self.save_config(self.root_dir + "/.user/eth_cfg.json", self.config)
        self.load_profile("No Profile")
        return True

    def create_profile(self, name):
        """
        Create a new profile with the given name    创建一个具有给定名称的新配置文件

        Args:
            name (str): Name of the profile to create   要创建的配置文件名
        """
        # self.logger.info("Create new profile: {}".format(name))
        self.config["Profile"][name] = False
        self.save_config(self.root_dir + "/.user/cfg.json", self.config)
        self.save_config(
            self.root_dir + "/.user/" + name + ".json",
            {"imgs": {}, "ethnics": {}, "img_dir": "", "rtf": ""},
        )
        try:
            with open(self.root_dir + "/.user/" + name + ".xml", "a"):
                pass
        except OSError:
            pass
        self.load_profile(name)

    def load_profile(self, name):
        """
        Load a profile by name and update active profile    加载指定名称的配置文件并更新当前活动配置文件

        Args:
            name (str): Name of the profile to load         要加载的配置文件名
        """
        # 获取当前配置文件的图像目录，用于后续保存配置文件
        deact_img_dir = self.prf_cfg["img_dir"]
        # 加载新配置文件的配置信息
        self.prf_cfg = self.load_config(self.root_dir + "/.user/" + name + ".json")
        # 获取新配置文件的图像目录，用于后续加载配置文件
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
        # 更新当前配置文件名称
        self.cur_prf = name

    def write_xml(self, data):
        """
        Write XML configuration file with player mappings   写入包含球员映射的XML配置文件

        Args:
            data (list): List of player mapping data    球员映射数据列表

        Returns:
            list: List of XML strings that were written 已写入的XML字符串列表
        """
        try:
            template_path = os.path.join(self.root_dir, ".config", "config_template")
            with open(template_path, "r", encoding="UTF-8") as fp:
                config_template = fp.read()
                xml_string = []
            for dat in data:
                xml_string.append(
                    '<record from="{}" to="graphics/pictures/person/r-{}/portrait"/>'.format(
                        dat[1] + "/" + dat[2], dat[0]
                    )
                )
            xml_players = "\n".join(xml_string)
            xml_config = config_template.replace("[players]", xml_players)
            config_path = os.path.join(self.prf_cfg["img_dir"], "config.xml")
            with open(config_path, "w", encoding="UTF-8") as fp:
                fp.write(xml_config)
            return xml_string
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Configuration template file not found: {e}")
        except PermissionError as e:
            raise PermissionError(f"Permission denied when accessing files: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error while writing XML: {e}")

    def swap_xml(self, deact_name, act_name, deact_img_dir, act_img_dir):
        """
        Swap XML files between deactivated and activated profiles
        在停用和激活的配置文件之间交换XML文件

        Args:
            deact_name (str): Name of the profile being deactivated         要停用的配置文件名
            act_name (str): Name of the profile being activated             要激活的配置文件名
            deact_img_dir (str): Image directory of deactivated profile     停用配置文件的图像目录
            act_img_dir (str): Image directory of activated profile         激活配置文件的图像目录
        """
        # 保存当前停用配置文件的config.xml
        deact_config_path = deact_img_dir + "config.xml"
        deact_user_path = self.root_dir + "/.user/" + deact_name + ".xml"
        if os.path.isfile(deact_config_path):
            try:
                with open(deact_user_path, "wb") as output, open(
                    deact_config_path, "rb"
                ) as input:
                    copyfileobj(input, output)
            except (OSError, IOError) as e:
                raise Exception(
                    f"Failed to save deactivated profile config from {deact_config_path} to {deact_user_path}: {str(e)}"
                )
        # 恢复目标激活配置文件的config.xml
        act_config_path = act_img_dir + "config.xml"
        act_user_path = self.root_dir + "/.user/" + act_name + ".xml"
        if os.path.isfile(act_config_path):
            try:
                with open(act_config_path, "wb") as output, open(
                    act_user_path, "rb"
                ) as input:
                    copyfileobj(input, output)
            except (OSError, IOError) as e:
                raise Exception(
                    f"Failed to restore activated profile config from {act_user_path} to {act_config_path}: {str(e)}"
                )

    def get_ethnic(self, nation):
        """
        Get ethnic group for a given nation
        获取指定国家对应的民族组

        Args:
            nation (str): Nation code to look up
                          要查询的国家代码

        Returns:
            str or None: Ethnic group name or None if not found
                      民族组名称，如果未找到则返回None
        """
        return self.eth_cfg["Ethnics"].get(nation, None)
