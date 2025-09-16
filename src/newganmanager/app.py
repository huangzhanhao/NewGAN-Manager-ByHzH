"""
NewGAN Replacement Management Tool - 重构版
"""

# import asyncio

import toga

from toga.style import Pack
from travertino.constants import COLUMN, ROW
import os
import logging
import shutil
from .core.ConfigManager import ConfigManager
from .core.ProfileManager import ProfileManager

from .core.Mapper import Mapper
from .core.RtfParser import RtfParser
from .core.Reporter import Reporter
from .core.XmlParser import XmlParser
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
        super().__init__(
            formal_name="NewGAN Manager",
            app_id="com.fm.newganmanager",
            home_page="https://github.com/huangzhanhao/NewGAN-Manager-ByHzH",
        )

        self.logger = logging.getLogger("NewGAN App")
        # Initialize instance attributes
        # Initialize instance attributes with type annotations
        # 使用类型注解初始化实例属性
        self.facepack_dirs: set[str] = set()
        self.mode_info: dict[str, str] = {}
        self.profile_manager: ProfileManager | None = None
        self.main_tab: MainTab | None = None
        self.log_tab: LogTab | None = None
        self.profile_tab: toga.Box | None = None
        self.option_container: toga.OptionContainer | None = None
        self.main_window: toga.MainWindow | None = None
        # self.prfsel_box: toga.Box | None = None
        # self.prfsel_lst: toga.Selection | None = None
        # self.dir_inp: toga.TextInput | None = None
        # self.dir_btn: toga.Button | None = None
        # self.rtf_inp: toga.TextInput | None = None
        # self.rtf_btn: toga.Button | None = None
        # self.genmde_lab: toga.Label | None = None
        # self.genmdeinfo_lab: toga.Label | None = None
        # self.gendup: toga.Switch | None = None
        # self.genmde_lst: toga.Selection | None = None
        # self.gen_btn: toga.Button | None = None
        # self.gen_lab: toga.Label | None = None
        # self.gen_prg: toga.ProgressBar | None = None

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

        # Setup application data and profile
        # 设置应用程序数据和配置文件
        self._setup_application_data()

        # Define facepack directories set and mode info dictionary
        # 定义头像包目录集合和模式说明字典
        self.facepack_dirs = {
            "African",
            "Asian",
            "Caucasian",
            "Central European",
            "EECA",
            "Italmed",
            "MENA",
            "MESA",
            "SAMed",
            "Scandinavian",
            "Seasian",
            "South American",
            "SpanMed",
            "YugoGreek",
        }
        self.mode_info = {
            "Overwrite": "Overwrites already replaced faces",
            "Preserve": "Preserves already replaced faces",
            "Generate": "Generates mapping from scratch.",
        }

        # Setup application menu
        # 设置应用程序菜单
        self._setup_menu()

        # Set Discord Webhook URL for reporting functionality
        # 设置Discord Webhook地址用于报告功能
        # self.hook = "https://discord.com/api/webhooks/796137178328989768/ETMNtPVb-PHuZPayC5G5MZD24tdDi5jmG6jAgjZXg0FDOXjy-VIabATXPco05qLIr4ro"

        # Create main tab
        self.main_tab = MainTab(self)
        self.profile_tab = toga.Box()

        # Create option container and add tabs
        # 创建选项卡容器并添加标签页
        self.option_container = toga.OptionContainer(style=Pack(margin=(10,30), align_items="center"))
        self.option_container.content.append("Main", self.main_tab.main_tab_box)
        self.option_container.content.append("Profile", self.profile_tab)
        self.option_container.content.append("Log", self.log_tab.log_tab_box)

        # Create and show main window
        # 创建并显示主窗口
        self.main_window = toga.MainWindow(title=self.formal_name, size=(1000, 600))
        self.main_window.content = self.option_container
        self.main_window.show()

        # Enable buttons and finalize startup
        # 启用按钮并完成启动
        self.main_tab.set_btns(True)

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
                default_config_path = os.path.join(
                    app_path, ".user", "default_cfg.json"
                )
                shutil.copyfile(default_config_path, user_config_path)

            # Load current profile and migrate old config
            # 加载当前配置文件并迁移旧版配置
            self.logger.info("Loading current profile")
            self.profile_manager = ProfileManager(
                ConfigManager().get_latest_prf(user_config_path), app_path
            )
            self.profile_manager.migrate_config()
            # Store reference to config manager for backward compatibility
            self.profile_manager.config_manager = ConfigManager()
        except Exception as e:
            self.logger.error("Failed to setup application data: {}".format(e))

    def _setup_menu(self):
        """
        Setup application menu
        设置应用程序菜单
        """
        # CREATE MENUBAR
        # 创建菜单栏

        def open_usage_links(command: toga.Command, **kwargs) -> bool:
            self.open_link("https://www.youtube.com/watch?v=iJqZNp0nomM")
            self.open_link("https://www.bilibili.com/video/BV1ew411h759")
            return True

        usage = toga.Command(
            open_usage_links,
            text="User Guide",
            group=toga.Group.HELP,
            section=1,
        )

        def open_troubleshooting(command, **kwargs):
            self.open_link("https://github.com/Maradonna90/NewGAN-Manager/wiki/Troubleshooting")
            return True

        troubleshooting = toga.Command(
            open_troubleshooting,
            text="Troubleshooting",
            group=toga.Group.HELP,
            section=2,
        )

        def open_faq(command, **kwargs):
            self.open_link("https://github.com/Maradonna90/NewGAN-Manager/wiki/FAQ")
            return True

        faq = toga.Command(
            open_faq,
            text="FAQ",
            group=toga.Group.HELP,
            section=3,
        )

        def open_discord(command, **kwargs):
            self.open_link("https://discord.gg/UfRpJVc")
            return True

        discord = toga.Command(
            open_discord,
            text="Discord",
            group=toga.Group.HELP,
            section=4,
        )

        self.commands.add(usage, troubleshooting, discord, faq)

    def open_link(self, url):
        """
        Open link in browser
        在浏览器中打开链接

        Args:
            url: URL to open 要打开的URL
        """
        webbrowser.open(url)

    async def throw_error(self, msg):
        self.logger.debug("Error window: {}".format(msg))
        dialog = toga.ErrorDialog("Error",msg)
        await  self.main_window.dialog(dialog)

    async def show_info(self, msg):
        self.logger.debug("Info window: {}".format(msg))
        dialog = toga.InfoDialog("Info", msg)
        await self.main_window.dialog(dialog)

    def on_exit(self):
        """
        Handle application exit event
        处理应用程序退出事件
        """
        # Log application exit information
        # 记录应用程序退出信息
        if hasattr(self, "logger"):
            self.logger.info(
                "Application is exiting...\n-----------------------------------------"
            )
        return super().on_exit()

    # No usage
    async def check_for_update(self):
        try:
            r = requests.get(
                "https://raw.githubusercontent.com/Maradonna90/NewGAN-Manager/master/version",
                timeout=10,
            )
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
                await self.show_info("There is a new version. Please Update!")
                self.open_link(
                    "https://github.com/Maradonna90/NewGAN-Manager/releases/latest"
                )
        except AttributeError:
            self.logger.info("Version attribute not available")
