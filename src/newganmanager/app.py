import asyncio
import toga
from toga.style import Pack
import os
import shutil
import logging
import webbrowser
import requests
from .core.ProfileManager import ProfileManager
from .app_log_tab import LogTab
from .app_main_tab import MainTab
from .app_profile_tab import ProfileTab
from .core.NewGanLogManager import NewGanLogManager
from .services.profile_service import ProfileService


def main():
    return NewGANManager()


class NewGANManager(toga.App):

    def __init__(self):
        super().__init__(
            formal_name="NewGAN Manager",
            app_id="com.fm.newganmanager",
            home_page="https://github.com/huangzhanhao/NewGAN-Manager-ByHzH",
        )

        self.logger = logging.getLogger("NewGAN App")
        # 用户数据目录：优先应用目录下 data/（便携式，用户好找）；
        # 应用目录不可写时回退平台标准数据目录（paths.data）
        self.user_data_dir = self._resolve_user_data_dir()
        self.log_manager = NewGanLogManager(self.user_data_dir)
        # Initialize instance attributes with type annotations
        # 使用类型注解初始化实例属性
        self.facepack_dirs: set[str] = set()
        self.mode_info: dict[str, str] = {}
        self.profile_manager: ProfileManager | None = None
        self.profile_service: ProfileService | None = None
        self.main_tab: MainTab | None = None
        self.log_tab: LogTab | None = None
        self.profile_tab: ProfileTab | None = None
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

        # 创建业务服务（供各标签页回调使用）
        self.profile_service = ProfileService(self.profile_manager, logger=self.logger)

        # Create tab
        self.main_tab = MainTab(self)
        self.profile_tab = ProfileTab(self)
        self.log_tab = LogTab(self)

        # Create option container and add tabs
        # 创建选项卡容器并添加标签页
        self.option_container = toga.OptionContainer(style=Pack(margin=(10,30), align_items="center"))
        self.option_container.content.append("Main", self.main_tab.main_tab_box)
        self.option_container.content.append("Profile", self.profile_tab.profile_tab_box)
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
    def _resolve_user_data_dir(self):
        """确定用户数据目录：
        优先使用应用目录下的 data/（便携式，用户数据随安装目录走、好找）；
        应用目录不可写（如安装在 Program Files 等受保护位置）时，
        回退到平台标准用户数据目录 paths.data，避免启动即写失败。
        """
        app_dir = str(self.paths.app)
        try:
            probe = os.path.join(app_dir, ".write_probe")
            with open(probe, "w", encoding="utf-8") as fp:
                fp.write("")
            os.remove(probe)
            return os.path.join(app_dir, "data")
        except OSError:
            return str(self.paths.data)

    def _setup_application_data(self):
        """
        Setup application directories and configuration files
        设置应用程序目录和配置文件

        应用资源（.config 只读配置）留在应用目录；
        应用自带模板（.user）只作种子；
        用户运行时数据（.user、日志）写入 self.user_data_dir。
        """
        app_path = str(self.paths.app)
        data_path = self.user_data_dir
        try:
            user_dir = os.path.join(data_path, ".user")
            os.makedirs(user_dir, exist_ok=True)
            app_user_dir = os.path.join(app_path, ".user")
            user_config_path = os.path.join(user_dir, "cfg.json")

            # 1) 旧版布局迁移（仅当目标位置尚无用户数据）：
            #    先迁移旧版写在应用目录 .user 的数据，再迁移 paths.data 下的数据
            if not os.path.isfile(user_config_path):
                for legacy in (app_user_dir, os.path.join(str(self.paths.data), ".user")):
                    if os.path.normpath(legacy) == os.path.normpath(user_dir):
                        continue
                    if os.path.isfile(os.path.join(legacy, "cfg.json")):
                        shutil.copytree(legacy, user_dir, dirs_exist_ok=True)
                        self.logger.info(f"Migrated user data from {legacy} to {user_dir}")
                        break

            # 2) 用应用目录模板补齐缺失文件（幂等：仅补缺失项，含 No Profile.json 等）
            if os.path.isdir(app_user_dir):
                for fname in os.listdir(app_user_dir):
                    src = os.path.join(app_user_dir, fname)
                    dst = os.path.join(user_dir, fname)
                    if os.path.isfile(src) and not os.path.isfile(dst):
                        shutil.copyfile(src, dst)
                        self.logger.info(f"Copied default template: {fname}")

            # 3) default_cfg.json → cfg.json（用户配置文件的正式名）
            default_cfg = os.path.join(user_dir, "default_cfg.json")
            if os.path.isfile(default_cfg) and not os.path.isfile(user_config_path):
                shutil.copyfile(default_cfg, user_config_path)
                self.logger.info("Created cfg.json from default_cfg.json template")

            # Load current profile
            # 加载当前配置文件
            self.logger.info("Loading current profile")
            self.profile_manager = ProfileManager(
                ProfileManager.get_latest_prf(user_config_path),
                app_path,
                data_path,
            )
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

    def run_async(self, coro):
        """在异步循环中执行协程（fire-and-forget），供同步回调触发 async 对话框"""
        return asyncio.create_task(coro)

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

    async def ask_confirm(self, title, message):
        """弹确认对话框，返回用户是否确认（供业务层注入）"""
        self.logger.debug(f"Ask confirm: {title}")
        dialog = toga.QuestionDialog(title, message)
        if self.main_window is not None:
            return await self.main_window.dialog(dialog)
        return False

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
