"""
NewGAN Replacement Management Tool - 重构版
"""

import asyncio

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import os
import logging
import shutil
from .core.config_manager import Config_Manager
from .core.profile_manager import Profile_Manager
from .core.mapper import Mapper
from .core.rtfparser import RTF_Parser
from .core.reporter import Reporter
from .core.xmlparser import XML_Parser
from .app_log_tab import LogTab
from .app_main_tab import MainTab
import webbrowser
import requests


def main():
    return NewGANManager()


class NewGANManager(toga.App):

    def __init__(self):
        """
        Initialize the NewGANManager application
        初始化NewGANManager应用
        """
        super().__init__(formal_name = "NewGAN Manager",app_id = "com.fm.newganmanager",home_page="https://github.com/huangzhanhao/NewGAN-Manager-ByHzH")
        self.logger = logging.getLogger("NewGAN App")  # 初始化logger属性

    def startup(self):
        """
        Construct and show the Toga application.
        构建并显示Toga应用程序

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        通常，您会将应用程序添加到主内容框中。
        然后我们创建一个主窗口（名称与应用程序匹配），并显示主窗口。
        """

        # Initialization Log Tab
        # 初始化日志标签页
        self.log_tab = LogTab(self)

        # Log application startup information
        # 记录应用启动信息
        self.logger.info("Starting Application\n------------------------------------------------")
        self.logger.info(str(self.paths.app))

        # Setup application data and profile
        # 设置应用程序数据和配置文件
        self._setup_application_data()

        # Define facepack directories set and mode info dictionary
        # 定义头像包目录集合和模式说明字典
        self.facepack_dirs = {"African", "Asian", "Caucasian", "Central European", "EECA", "Italmed", "MENA", "MESA",
                              "SAMed", "Scandinavian", "Seasian", "South American", "SpanMed", "YugoGreek"}
        self.mode_info = {"Overwrite": "Overwrites already replaced faces",
                          "Preserve":  "Preserves already replaced faces",
                          "Generate": "Generates mapping from scratch."}

        # Setup application menu
        # 设置应用程序菜单
        self._setup_menu()

        # Set Discord Webhook URL for reporting functionality
        # 设置Discord Webhook地址用于报告功能
        self.hook = "https://discord.com/api/webhooks/796137178328989768/ETMNtPVb-PHuZPayC5G5MZD24tdDi5jmG6jAgjZXg0FDOXjy-VIabATXPco05qLIr4ro"

        # Create main tab
        self.main_tab = MainTab(self)
        
        # Create option container and add tabs
        # 创建选项卡容器并添加标签页
        option_container = toga.OptionContainer()
        option_container.content.append("Main", self.main_tab.main_tab_box)
        profile_tab = toga.Box()
        option_container.content.append("Profile", profile_tab)
        option_container.content.append("Log", self.log_tab.log_tab_box)

        # Create and show main window
        # 创建并显示主窗口
        self.main_window = toga.MainWindow(title=self.formal_name, size=(1000, 600))
        self.main_window.content = option_container
        self.main_window.show()

        # Enable buttons and finalize startup
        # 启用按钮并完成启动
        self.set_btns(True)
        
        # Store references for backward compatibility
        # 存储引用以保持向后兼容性
        self.profile_section = self.main_tab.profile_section
        self.path_section = self.main_tab.path_section
        self.gen_section = self.main_tab.gen_section
        self.prfsel_box = self.profile_section.sel_box  # Profile selection box 配置文件选择框
        self.prfsel_lst = self.profile_section.selection_list  # Profile list 配置文件列表
        self.dir_inp = self.path_section.dir_input  # Directory create_input 目录输入
        self.dir_btn = self.path_section.dir_button  # Directory button 目录按钮
        self.rtf_inp = self.path_section.rtf_input  # RTF input RTF输入
        self.rtf_btn = self.path_section.rtf_button  # RTF button RTF按钮
        self.genmde_lab = self.gen_section.mode_label  # Generation mode label 生成模式标签
        self.genmdeinfo_lab = self.gen_section.mode_info_label  # Generation mode info label 生成模式信息标签
        self.gendup = self.gen_section.allow_duplicates  # Allow duplicates 允许重复
        self.genmde_lst = self.gen_section.mode_selection  # Generation mode list 生成模式列表
        self.gen_btn = self.gen_section.generate_button  # Generate button 生成按钮
        self.gen_lab = self.gen_section.status_label  # Status label 状态标签
        self.gen_prg = self.gen_section.progress_bar  # Progress bar 进度条
        
        return option_container

    def _setup_application_data(self):
        """
        Setup application directories and configuration files
        设置应用程序目录和配置文件
        """
        app_path = str(self.paths.app)
        try:
            # Create config directory and initialize user config file (if not exists)
            # 创建配置目录并初始化用户配置文件（如不存在）
            os.makedirs(os.path.join(app_path, ".config"), exist_ok=True)
            user_config_path = os.path.join(app_path, ".user", "cfg.json")
            if not os.path.isfile(user_config_path):
                default_config_path = os.path.join(app_path, ".user", "default_cfg.json")
                shutil.copyfile(default_config_path, user_config_path)

            # Load current profile and migrate old config
            # 加载当前配置文件并迁移旧版配置
            self.logger.info("Loading current profile")
            self.profile_manager = Profile_Manager(Config_Manager().get_latest_prf(user_config_path), app_path)
            self.profile_manager.migrate_config()
            # Store reference to config manager for backward compatibility
            self.profile_manager.config_manager = Config_Manager()
        except Exception as e:
            self.logger.error("Failed to setup application data: {}".format(e))

    def _setup_menu(self):
        """
        Setup application menu
        设置应用程序菜单
        """
        # CREATE MENUBAR
        # 创建菜单栏

        usage = toga.Command(
            lambda e=None: [self.open_link("https://www.youtube.com/watch?v=iJqZNp0nomM"),
                            self.open_link("https://www.bilibili.com/video/BV1ew411h759")],
            text='User Guide',
            group=toga.Group.HELP,
            section=1
        )

        troubleshooting = toga.Command(
            lambda e=None, u="https://github.com/Maradonna90/NewGAN-Manager/wiki/Troubleshooting": self.open_link(u),
            text='Troubleshooting',
            group=toga.Group.HELP,
            section=2
        )

        faq = toga.Command(
            lambda e=None, u="https://github.com/Maradonna90/NewGAN-Manager/wiki/FAQ": self.open_link(u),
            text='FAQ',
            group=toga.Group.HELP,
            section=3
        )

        discord = toga.Command(
            lambda e=None, u="https://discord.gg/UfRpJVc": self.open_link(u),
            text='Discord',
            group=toga.Group.HELP,
            section=4
        )

        self.commands.add( usage, troubleshooting, discord, faq)

    def open_link(self, url):
        """
        Open link in browser
        在浏览器中打开链接

        Args:
            url: URL to open 要打开的URL
        """
        webbrowser.open(url)

    def set_btns(self, value):
        """
        Set button enabled states
        设置按钮启用状态

        Args:
            value: Button enabled state 按钮启用状态
        """
        if self.profile_manager and self.profile_manager.cur_prf == "No Profile":
            self.gen_btn.enabled = False
            self.dir_btn.enabled = False
            self.rtf_btn.enabled = False
            # self.rep_btn.enabled = False
        elif self.profile_manager and (
            self.profile_manager.prf_cfg.get("img_dir", "") == ""
            or self.profile_manager.prf_cfg.get("rtf", "") == ""
        ):
            self.gen_btn.enabled = False
            self.dir_btn.enabled = value
            self.rtf_btn.enabled = value
            # self.rep_btn.enabled = value
        else:
            self.gen_btn.enabled = value
            self.dir_btn.enabled = value
            self.rtf_btn.enabled = value
            # self.rep_btn.enabled = value

    async def _throw_error(self, msg):
        """
        Throw error message (async internal method)
        抛出错误信息 (异步内部方法)

        Args:
            msg: Error message 错误信息
        """
        self.logger.info("Error window: {}".format(msg))
        dialog = toga.ErrorDialog(title="Error", message=msg)
        await self.main_window.dialog(dialog)

    async def _show_info(self, msg):
        """
        Show information (async internal method)
        显示信息 (异步内部方法)

        Args:
            msg: Message content 信息内容
        """
        self.logger.info("Info window: {}".format(msg))
        dialog = toga.InfoDialog(title="Info", message=msg)
        info = await self.main_window.dialog(dialog)
        return info

    #No usage
    async def check_for_update(self):
        try:
            r = requests.get("https://raw.githubusercontent.com/Maradonna90/NewGAN-Manager/master/version", timeout=10)
            r.raise_for_status()  # Raise an exception for bad status codes
        except requests.exceptions.Timeout:
            self.logger.info("check update timeout exceeded!")
            return
        except requests.exceptions.RequestException as e:
            self.logger.info("check update request failed: {}".format(e))
            return
        except Exception as e:
            self.logger.info("check update unexpected error: {}".format(e))
            return

        try:
            if r.text.strip() != self.version:
                await self._show_info("There is a new version. Please Update!")
                self.open_link("https://github.com/Maradonna90/NewGAN-Manager/releases/latest")
        except AttributeError:
            self.logger.info("Version attribute not available")