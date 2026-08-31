import toga
from toga.style import Pack
import os
import shutil
import logging
import webbrowser
import requests
from .core.ConfigManager import ConfigManager
from .core.ProfileManager import ProfileManager
# from .core.FaceMapper import FaceMapper
# from .core.RtfParser import RtfParser
# from .core.XmlParser import XmlParser
from .app_log_tab import LogTab
from .app_main_tab import MainTab
from .core.NewGanLogManager import NewGanLogManager


def main():
    return NewGANManager()


class NewGANManager(toga.App):

    def __init__(self):
        super().__init__(
            formal_name="NewGAN Manager",
            app_id="com.fm.newganmanager",
            home_page="https://github.com/huangzhanhao/NewGAN-Manager-ByHzH",
        )

        # 运行时数据（日志、.user）写入各平台标准用户数据目录，而不是应用目录
        self.log_manager = NewGanLogManager(self.paths.data)
        self.logger = logging.getLogger("NewGAN App")
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

        # Create tab
        self.main_tab = MainTab(self)
        self.profile_tab = toga.Box()
        self.log_tab = LogTab(self)

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

        # Log application startup information
        # 记录应用启动信息
        self.logger.info("Starting Application\n-------------------------------------------")
        self.logger.info(f"Application Path: {str(self.paths.app)}")
    def _setup_application_data(self):
        """
        Setup application directories and configuration files
        设置应用程序目录和配置文件

        应用资源（.config 只读配置）留在应用目录；
        用户运行时数据（.user）写入 paths.data 指向的用户数据目录。
        """
        app_path = str(self.paths.app)
        data_path = str(self.paths.data)
        try:
            user_dir = os.path.join(data_path, ".user")
            os.makedirs(user_dir, exist_ok=True)
            app_user_dir = os.path.join(app_path, ".user")
            user_config_path = os.path.join(user_dir, "cfg.json")

            if not os.path.isfile(user_config_path):
                old_user_cfg = os.path.join(app_user_dir, "cfg.json")
                if os.path.isfile(old_user_cfg):
                    # 从旧版布局（应用目录下的 .user）整体迁移用户数据
                    shutil.copytree(app_user_dir, user_dir, dirs_exist_ok=True)
                    self.logger.info(f"Migrated user data from {app_user_dir} to {user_dir}")
                else:
                    # 首次运行：从应用目录复制全部默认模板文件
                    if os.path.isdir(app_user_dir):
                        for fname in os.listdir(app_user_dir):
                            src = os.path.join(app_user_dir, fname)
                            dst = os.path.join(user_dir, fname)
                            if os.path.isfile(src) and not os.path.isfile(dst):
                                shutil.copyfile(src, dst)
                                self.logger.info(f"Copied default template: {fname}")
                    # default_cfg.json → cfg.json（用户配置文件的正式名）
                    default_cfg = os.path.join(user_dir, "default_cfg.json")
                    if os.path.isfile(default_cfg) and not os.path.isfile(user_config_path):
                        shutil.copyfile(default_cfg, user_config_path)
                        self.logger.info("Created cfg.json from default_cfg.json template")

            # Load current profile
            # 加载当前配置文件
            self.logger.info("Loading current profile")
            self.profile_manager = ProfileManager(
                ConfigManager().get_latest_prf(user_config_path),
                app_path,
                data_path,
            )
            self.profile_manager.migrate_config()
        except Exception as e:
            self.logger.error(f"Failed to setup application data: {e}", exc_info=True)
            # 不吞异常：UI 启动时 profile_manager 为 None 会导致后续 MainTab 崩溃，
            # 这里至少让错误可见，方便排查
            raise

    def _setup_menu(self):
        """
        Setup application menu
        设置应用程序菜单
        """

        def open_usage_links(command: toga.Command, **kwargs) -> bool:
            webbrowser.open("https://www.youtube.com/watch?v=iJqZNp0nomM")
            webbrowser.open("https://www.bilibili.com/video/BV1ew411h759")
            return True

        usage = toga.Command(
            open_usage_links,
            text="User Guide",
            group=toga.Group.HELP,
            section=1,
        )

        def open_troubleshooting(command, **kwargs):
            webbrowser.open("https://github.com/Maradonna90/NewGAN-Manager/wiki/Troubleshooting")
            return True

        troubleshooting = toga.Command(
            open_troubleshooting,
            text="Troubleshooting",
            group=toga.Group.HELP,
            section=2,
        )

        def open_faq(command, **kwargs):
            webbrowser.open("https://github.com/Maradonna90/NewGAN-Manager/wiki/FAQ")
            return True

        faq = toga.Command(
            open_faq,
            text="FAQ",
            group=toga.Group.HELP,
            section=3,
        )

        def open_discord(command, **kwargs):
            webbrowser.open("https://discord.gg/UfRpJVc")
            return True

        discord = toga.Command(
            open_discord,
            text="Discord",
            group=toga.Group.HELP,
            section=4,
        )

        self.commands.add(usage, troubleshooting, discord, faq)

    async def throw_error(self, msg):
        self.logger.error(f"Error window: {msg}")
        dialog = toga.ErrorDialog("Error", msg)
        if self.main_window is not None:
            await self.main_window.dialog(dialog)

    async def show_info(self, msg):
        self.logger.info(f"Info window: {msg}")
        dialog = toga.InfoDialog("Info", msg)
        if self.main_window is not None:
            await self.main_window.dialog(dialog)

    def on_exit(self):
        """当应用程序退出时执行"""
        if hasattr(self, "logger"):
            self.logger.info("Application is exiting...\n-------------------------------------------")
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
            self.logger.info(f"check update request failed: {e}")
            return
        except Exception as e:
            self.logger.info(f"check update unexpected error: {e}")
            return
        try:
            if r.text.strip() != self.version:
                await self.show_info("There is a new version. Please Update!")
                webbrowser.open(
                    "https://github.com/Maradonna90/NewGAN-Manager/releases/latest"
                )
        except AttributeError:
            self.logger.info("Version attribute not available")
