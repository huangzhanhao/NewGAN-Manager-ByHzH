"""
NewGAN Replacement Management Tool - 重构版
"""

import asyncio

import toga
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

        # Initialize logging section first
        # 首先初始化日志部分
        self.log_section = LogSection(self)

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

        # Initialize GUI interface
        # 初始化GUI界面
        self.logger.info("Creating GUI")
        self.main_box = toga.Box()  # Main interface box 主界面框
        self.logger.info("Created main box")

        # Setup application menu
        # 设置应用程序菜单
        self._setup_menu()

        # Set Discord Webhook URL for reporting functionality
        # 设置Discord Webhook地址用于报告功能
        self.hook = "https://discord.com/api/webhooks/796137178328989768/ETMNtPVb-PHuZPayC5G5MZD24tdDi5jmG6jAgjZXg0FDOXjy-VIabATXPco05qLIr4ro"

        # Create UI sections with specified label width
        # 使用指定标签宽度创建UI部分
        # label_width = 125  # Label width 标签宽度

        # TOP Profiles
        # 顶部 配置文件
        self.profile_section = ProfileSection(self, label_width=125, button_width=75)
        self.main_box.add(self.profile_section.box)
        self.main_box.add(self.profile_section.sel_box)

        # MID Path selections
        # 中部 资源路径选择
        self.path_section = PathSelectionSection(self, label_width=125, button_width=75)
        self.main_box.add(self.path_section.dir_box)
        self.main_box.add(self.path_section.rtf_box)

        # Store references for backward compatibility
        # 存储引用以保持向后兼容性
        self.prfsel_box = self.profile_section.sel_box  # Profile selection box 配置文件选择框
        self.prfsel_lst = self.profile_section.selection_list  # Profile list 配置文件列表
        self.dir_inp = self.path_section.dir_input  # Directory input 目录输入
        self.dir_btn = self.path_section.dir_button  # Directory button 目录按钮
        self.rtf_inp = self.path_section.rtf_input  # RTF input RTF输入
        self.rtf_btn = self.path_section.rtf_button  # RTF button RTF按钮

        # Generation mode selection
        # 生成模式选择
        self.gen_section = GenerationSection(self, label_width=125)
        self.main_box.add(self.gen_section.mode_box)

        # Store references for backward compatibility
        # 存储引用以保持向后兼容性
        self.genmde_lab = self.gen_section.mode_label  # Generation mode label 生成模式标签
        self.genmdeinfo_lab = self.gen_section.mode_info_label  # Generation mode info label 生成模式信息标签
        self.gendup = self.gen_section.allow_duplicates  # Allow duplicates 允许重复
        self.genmde_lst = self.gen_section.mode_selection  # Generation mode list 生成模式列表
        self.gen_btn = self.gen_section.generate_button  # Generate button 生成按钮
        self.gen_lab = self.gen_section.status_label  # Status label 状态标签
        self.gen_prg = self.gen_section.progress_bar  # Progress bar 进度条

        # BOTTOM Generation
        # 底部 生成
        self.main_box.add(self.gen_section.gen_box)

        # Report bad image
        # 报告不良图像
        self.report_section = ReportSection(self, label_width=125)
        # self.main_box.add(self.report_section.box)

        # Store references for backward compatibility
        # 存储引用以保持向后兼容性
        self.rep_lab = self.report_section.uid_label  # Report label 报告标签
        self.rep_inp = self.report_section.uid_input  # Report input 报告输入
        self.rep_img = self.report_section.image_view  # Report image 报告图像
        self.rep_btn = self.report_section.report_button  # Report button 报告按钮

        # Add log section to main box
        # 将日志区域添加到主框中
        self.main_box.add(self.log_section.box)

        # Store references for backward compatibility
        # 存储引用以保持向后兼容性
        self.log_area = self.log_section.area  # Log area 日志区域

        # Finalize UI configuration
        # 完成UI配置
        self.main_box.style.update(direction=COLUMN, margin=30, align_items='center')

        # Create and show main window
        # 创建并显示主窗口
        self.main_window = toga.MainWindow(title=self.formal_name, size=(1000, 600))
        self.main_window.content = self.main_box
        self.main_window.show()

        # Enable buttons and finalize startup
        # 启用按钮并完成启动
        self.set_btns(True)

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
        except Exception as e:
            self.logger.error("Failed to setup application data: {}".format(e))

    def _setup_menu(self):
        """
        Setup application menu
        设置应用程序菜单
        """
        # CREATE MENUBAR
        # 创建菜单栏
        logs_group = toga.Group("Logs", parent=None, order=80)
        check_logs = toga.Command(
            lambda e=None: setattr(self.main_window, 'content', self.path_section.dir_box),
            text='Check Logs',
            group=logs_group
        )

        check_logs_file = toga.Command(
            lambda e=None: setattr(self.main_window, "content", self.log_section.box),
            text="Check Logs file",
            group=logs_group,
        )

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

        self.commands.add(check_logs, check_logs_file, usage, troubleshooting, discord, faq)

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
            self.rep_btn.enabled = False
        elif self.profile_manager and (
            self.profile_manager.prf_cfg.get("img_dir", "") == ""
            or self.profile_manager.prf_cfg.get("rtf", "") == ""
        ):
            self.gen_btn.enabled = False
            self.dir_btn.enabled = value
            self.rtf_btn.enabled = value
            self.rep_btn.enabled = value
        else:
            self.gen_btn.enabled = value
            self.dir_btn.enabled = value
            self.rtf_btn.enabled = value
            self.rep_btn.enabled = value

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

    async def check_for_update(self):
        """
        Check for updates (async method)
        检查更新 (异步方法)
        """
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


class SourceSelection(toga.Selection):
    """
    Custom dropdown selection component that extends toga.Selection functionality
    自定义的下拉选择组件，扩展了toga.Selection功能
    """
    def __init__(self, id=None, style=None, items=None, on_change=None, enabled=True):
        """
        Initialize the SourceSelection component
        初始化SourceSelection组件
        
        Args:
            id: Component ID 组件ID
            style: Component style 组件样式
            items: List of selection items 选择项列表
            on_change: Change callback function 变更回调函数
            enabled: Whether the component is enabled 是否启用组件
        """
        super().__init__(id=id, style=style, items=items, on_change=on_change, enabled=enabled)

    def add_item(self, item):
        """
        Add a selection item
        添加选择项

        Args:
            item: Item to be added 要添加的项
        """
        self._items.append(item)

    def remove_item(self, item):
        """
        Remove a selection item
        移除选择项

        Args:
            item: Item to be removed 要移除的项
        """
        row = self._items.find(item)
        self._items.remove(row)


class ProfileSection:
    """
    Profile section UI components and functionality
    配置文件部分UI组件和功能
    """
    def __init__(self, app, label_width, button_width):
        """
        Initialize profile section UI
        初始化配置文件部分UI

        Args:
            app: Application instance 应用实例
            label_width: Label width 标签宽度
            button_width: Button width 按钮宽度
        """
        self.app = app  # Application instance 应用实例
        self.label_width = label_width  # Label width 标签宽度
        self.button_width = button_width  # Button width 按钮宽度
        self.box = toga.Box()  # Create profile box 创建配置文件框
        self.sel_box = toga.Box()  # Selection profile box 选择配置文件框
        self.input = toga.TextInput(placeholder="Enter your profile name")  # Text input field 输入框
        self.create_label = toga.Label(text="Create Profile: ")  # Create profile label 创建配置文件标签
        self.select_label = toga.Label(text="Select Profile: ")  # Select profile label 选择配置文件标签
        self.selection_list = SourceSelection(items=list(self.app.profile_manager.config["Profile"].keys()), on_change=self._set_profile_status)  # Profile selection list 配置文件选择列表
        self.selection_list.value = self.app.profile_manager.cur_prf  # Current profile 当前配置文件
        self.create_button = toga.Button(text="Create", on_press=self._create_profile)  # Create button 创建按钮
        self.delete_button = toga.Button(text="Delete", on_press=self._delete_profile)  # Delete button 删除按钮

        # Setup profile creation box
        # 设置创建配置文件框
        self.box.add(self.create_label)
        self.box.add(self.input)
        self.box.add(self.create_button)
        self.create_label.style.update(width=self.label_width)
        self.create_button.style.update(width=self.button_width)
        self.input.style.update(direction=ROW, margin=(0, 20), flex=1)

        # Setup profile selection box
        # 设置选择配置文件框
        self.sel_box.add(self.select_label)
        self.sel_box.add(self.selection_list)
        self.sel_box.add(self.delete_button)
        self.select_label.style.update(width=self.label_width)
        self.delete_button.style.update(width=self.button_width)
        self.selection_list.style.update(direction=ROW, margin=(0, 20), flex=1)

        # Setup box styles
        # 设置框样式
        self.box.style.update(margin_bottom=10)
        self.sel_box.style.update(margin_bottom=10)

    def _create_profile(self, widget):
        """
        Create profile (internal method)
        创建配置文件 (内部方法)

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
        name = self.input.value
        if not name or not name.strip():
            self.app._throw_error("The Profile is Null!")
            return
        self.app.profile_manager.create_profile(name)
        self.selection_list.add_item(name)
        self.selection_list.value = name
        self.input.value = None
        self._refresh_inp(True)
        self.app.set_btns(True)

    def _delete_profile(self, widget):
        """
        Delete profile (internal method)
        删除配置文件 (内部方法)

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
        prf = self.selection_list.value
        result = self.app.profile_manager.delete_profile(prf)
        if not result:
            # 处理删除失败的情况，显示错误信息
            self.app._throw_error("Can't delete 'No Profile'")
            return
        self.selection_list.remove_item(prf)
        self.selection_list.value = "No Profile"
        self._refresh_inp(True)
        self.app.set_btns(False)

    def _set_profile_status(self, e):
        """
        Set profile status (internal method)
        设置配置文件状态 (内部方法)

        Args:
            e: Event object 事件对象
        """
        self.app.logger.info("switch profile: {}".format(e.value))
        if e.value is None:
            self.app.logger.info("catch none {}".format(self.app.profile_manager.cur_prf))
        elif e.value == self.app.profile_manager.cur_prf:
            self.app.logger.info("catch same values")

        else:
            name = e.value
            self.app.profile_manager.load_profile(name)
            self._refresh_inp()
            self.app.set_btns(True)
            Config_Manager().save_config(str(self.app.paths.app)+"/.user/cfg.json", self.app.profile_manager.config)

    def _refresh_inp(self, clear=False):
        """
        Refresh input buttons (internal method)
        刷新输入按钮 (内部方法)

        Args:
            clear: Whether to clear inputs 是否清空输入
        """
        self.app.logger.info("Refresh Input Buttons")
        if clear:
            self.app.dir_inp.value = None
            self.app.rtf_inp.value = None
        else:
            self.app.dir_inp.value = self.app.profile_manager.prf_cfg['img_dir']
            self.app.rtf_inp.value = self.app.profile_manager.prf_cfg['rtf']


class PathSelectionSection:
    """
    Path selection section UI components and functionality
    资源路径选择部分UI组件和功能
    """
    def __init__(self, app, label_width, button_width):
        """
        Initialize path selection section UI
        初始化资源路径选择部分UI
        
        Args:
            app: Application instance 应用实例
            label_width: Label width 标签宽度
            button_width: Button width 按钮宽度
        """
        self.app = app  # Application instance 应用实例
        self.label_width = label_width  # Label width 标签宽度
        self.button_width = button_width  # Button width 按钮宽度

        # Directory selection components
        # 目录选择组件
        self.dir_box = toga.Box()  # Directory selection box 目录选择框
        self.dir_label = toga.Label(text="Images Directory: ")  # Directory selection label 目录选择标签
        self.dir_input = toga.TextInput(readonly=True, value=self.app.profile_manager.prf_cfg['img_dir'])  # Directory input field 目录输入框
        self.dir_button = toga.Button(text="Browse",on_press=self.action_select_folder_dialog,enabled=False)  # Directory selection button 目录选择按钮

        # RTF file selection components
        # RTF文件选择组件
        self.rtf_box = toga.Box()  # RTF file box RTF文件框
        self.rtf_label = toga.Label(text="RTF File: ")  # RTF file label RTF文件标签
        self.rtf_input = toga.TextInput(readonly=True, value=self.app.profile_manager.prf_cfg['rtf'])  # RTF file input field RTF文件输入框
        self.rtf_button = toga.Button(text="Browse", on_press=self.action_open_file_dialog, enabled=False)  # RTF file selection button RTF文件选择按钮

        # Setup directory selection UI
        # 设置目录选择UI
        self.dir_box.add(self.dir_label)
        self.dir_box.add(self.dir_input)
        self.dir_box.add(self.dir_button)
        self.dir_label.style.update(width=self.label_width)
        self.dir_button.style.update(width=self.button_width)
        self.dir_input.style.update(direction=ROW, margin=(0, 20), flex=1)

        # Setup RTF file selection UI
        # 设置RTF文件选择UI
        self.rtf_box.add(self.rtf_label)
        self.rtf_box.add(self.rtf_input)
        self.rtf_box.add(self.rtf_button)
        self.rtf_label.style.update(width=self.label_width)
        self.rtf_button.style.update(width=self.button_width)
        self.rtf_input.style.update(direction=ROW, margin=(0, 20), flex=1)

        # Setup box styles
        # 设置框样式
        self.dir_box.style.update(margin_bottom=10)
        self.rtf_box.style.update(margin_bottom=10)

    async def action_select_folder_dialog(self, widget):
        """
        Action for select folder dialog (async method)
        选择文件夹对话框操作 (异步方法)

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
        self.app.logger.info("Select Folder...")
        try:
            dialog = toga.SelectFolderDialog(title="Select image root folder")
            path_name = await self.app.main_window.dialog(dialog)
            if path_name:
                path_name = str(path_name)
                self.app.logger.info(path_name)
                self.dir_input.value = path_name + "/"
                self.app.profile_manager.prf_cfg["img_dir"] = path_name + "/"
                Config_Manager().save_config(str(self.app.paths.app) + "/.user/" + self.app.profile_manager.cur_prf + ".json", self.app.profile_manager.prf_cfg)
                self.app.set_btns(True)
            self.app.set_btns(True)
        except Exception:
            self.app.logger.error("Fatal error in main loop", exc_info=True)
            pass

    async def action_open_file_dialog(self, widget):
        """
        Action for open file dialog (async method)
        打开文件对话框操作 (异步方法)

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
        self.app.logger.info("Select File...")
        try:
            dialog = toga.OpenFileDialog(title="Open RTF file", multiple_select=False, file_types=["rtf"])
            fname = await self.app.main_window.dialog(dialog)
            self.app.logger.info("Created file-dialog")
            if fname is not None:
                fname = str(fname)
                self.rtf_input.value = fname
                self.app.profile_manager.prf_cfg["rtf"] = fname
                self.app.logger.info("RTF file: " + fname)
                Config_Manager().save_config(str(self.app.paths.app) + "/.user/" + self.app.profile_manager.cur_prf + ".json", self.app.profile_manager.prf_cfg)
            else:
                self.app.profile_manager.prf_cfg["rtf"] = ""
                self.rtf_input.value = ""
                Config_Manager().save_config(str(self.app.paths.app) + "/.user/" + self.app.profile_manager.cur_prf + ".json", self.app.profile_manager.prf_cfg)
            self.app.set_btns(True)
        except Exception:
            self.app.logger.error("Fatal error in main loop", exc_info=True)
            pass


class GenerationSection:
    """
    Generation section UI components and functionality
    生成部分UI组件和功能
    """
    def __init__(self, app, label_width):
        """
        Initialize generation section UI
        初始化生成部分UI
        
        Args:
            app: Application instance 应用实例
            label_width: Label width 标签宽度
        """
        self.app = app  # Application instance 应用实例
        self.label_width = label_width  # Label width 标签宽度

        # Mode selection components
        # 模式选择框组件
        self.mode_box = toga.Box()  # Mode selection box 模式选择框
        self.mode_label = toga.Label(text="Mode: ")  # Mode label 模式标签
        self.mode_info_label = toga.Label(text=app.mode_info["Generate"])  # Mode info label 模式信息标签
        self.allow_duplicates = toga.Switch(text="Allow Duplicates?", value=True)  # Allow duplicates switch 允许重复开关
        self.mode_selection = SourceSelection(items=list(app.mode_info.keys()),on_change=self.update_label)  # Mode selection list 模式选择列表
        self.mode_selection.value = "Generate"  # Default mode 默认模式

        # Generation components
        # 生成框组件
        self.gen_box = toga.Box()  # Generation box 生成框
        self.generate_button = toga.Button(text="Replace Faces", on_press=self._replace_faces, enabled=False)  # Replace faces button 替换面部按钮
        self.status_label = toga.Label(text="")  # Status label 状态标签
        self.progress_bar = toga.ProgressBar(max=100)  # Progress bar 进度条

        # Setup mode selection UI
        # 设置模式选择框UI
        self.mode_box.add(self.mode_label)
        self.mode_box.add(self.mode_selection)
        self.mode_box.add(self.mode_info_label)
        self.mode_box.add(self.allow_duplicates)
        self.mode_label.style.update(width=self.label_width, margin_top=7)
        self.mode_info_label.style.update(margin_top=7)
        self.mode_selection.style.update(direction=ROW, margin=(0, 20), flex=1)
        self.allow_duplicates.style.update(margin_top=7, margin_left=20)
        self.mode_box.style.update(margin_bottom=20)

        # Setup generation UI
        # 设置生成UI
        self.gen_box.add(self.generate_button)
        self.gen_box.add(self.status_label)
        self.gen_box.add(self.progress_bar)
        self.progress_bar.style.update(width=570, align_items="center")
        self.status_label.style.update(margin_top=10, margin_bottom=10, width=100, align_items="center")
        self.gen_box.style.update(direction=COLUMN, align_items='center')

    def update_label(self, widget):
        """
        Update label
        更新标签

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
        self.app.logger.info("Updating generation label")
        self.mode_info_label.text = self.app.mode_info[widget.value]

    async def _replace_faces(self, widget):
        """
        Replace faces (async internal method)
        替换头像 (异步内部方法)

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
        self.app.logger.info("Start Replace Faces")
        rtf = self.app.profile_manager.prf_cfg['rtf']
        img_dir = self.app.profile_manager.prf_cfg['img_dir']
        profile = self.app.profile_manager.cur_prf
        mode = self.mode_selection.value
        if not os.path.isfile(rtf):
            await self.app._throw_error("The RTF file doesn't exist!")
            self.progress_bar.stop()
            self.app.profile_manager.prf_cfg['rtf'] = ''
            return
        if not os.path.isdir(img_dir):
            await self.app._throw_error("The image directory doesn't exist!")
            self.progress_bar.stop()
            self.app.profile_manager.prf_cfg['img_dir'] = ''
            return

        # Check if valid image_directory contains all the needed subfolders
        # 检查有效的图像目录是否包含所有需要的子文件夹
        img_dirs = set()
        for entry in os.scandir(img_dir):
            if entry.is_dir():
                img_dirs.add(entry.name)
        for fp_dir in self.app.facepack_dirs:
            if fp_dir not in img_dirs:
                # Ask user if they want to create the missing directory
                # 询问用户是否要创建缺失的目录
                dialog = toga.QuestionDialog(title="Missing Directory", message="Folder '{}' is missing in the image directory. Do you want to create it and continue?".format(fp_dir))
                user_choose = await self.app.main_window.dialog(dialog)

                # User chose to create the directory
                # 用户选择创建目录
                if user_choose:
                    try:
                        os.makedirs(os.path.join(img_dir, fp_dir), exist_ok=True)
                        self.app.logger.info("Created directory: {}".format(fp_dir))
                        continue
                    except Exception as e:
                        await self.app._throw_error("Failed to create directory {}: {}".format(fp_dir, str(e)))
                        self.progress_bar.stop()
                        return
                else:
                    # User chose not to create the directory, show error and stop
                    # 用户选择不创建目录，显示错误并停止
                    await self.app._throw_error("Folder {} is missing in the image directory".format(fp_dir))
                    self.progress_bar.stop()
                    return

        self.app.logger.info("rtf: {}".format(rtf))
        self.app.logger.info("img_dir: {}".format(img_dir))
        self.app.logger.info("profile: {}".format(profile))
        self.app.logger.info("mode: {}".format(mode))
        self.app.set_btns(False)
        self.progress_bar.start()
        self.status_label.text =  "Parsing RTF"
        await asyncio.sleep(0.1)
        rtf_parser = RTF_Parser()
        if not rtf_parser.is_rtf_valid(rtf):
            await self.app._throw_error("The RTF file is invalid!")
            self.progress_bar.stop()
            return
        rtf_data = rtf_parser.parse_rtf(rtf)
        self.progress_bar.value += 20
        self.status_label.text = "Map player to ethnicity"
        await asyncio.sleep(0.1)
        mapping_data = Mapper(img_dir, self.app.profile_manager).generate_mapping(rtf_data, mode, self.app.gendup.value)
        self.progress_bar.value += 60
        self.status_label.text = "Generate config.xml"
        await asyncio.sleep(0.1)
        try:
            self.app.profile_manager.write_xml(mapping_data)
        except FileNotFoundError as e:
            self.app.logger.error(f"Configuration template file not found: {e}")
            await self.app._throw_error(f"Configuration template file not found: {e}")
            self.progress_bar.stop()
            return
        except PermissionError as e:
            self.app.logger.error(f"Permission denied when accessing files: {e}")
            await self.app._throw_error(f"Permission denied when accessing files: {e}")
            self.progress_bar.stop()
            return
        except Exception as e:
            self.app.logger.error(f"Unexpected error while writing XML: {e}")
            await self.app._throw_error(f"Unexpected error while writing XML: {e}")
            self.progress_bar.stop()
            return
        # save profile metadata (used pics and config.xml)
        # 保存配置文件元数据（使用的图片和config.xml）
        self.status_label.text = "Save metadata for profile"
        self.progress_bar.value += 10
        await asyncio.sleep(0.1)
        Config_Manager().save_config(str(self.app.paths.app)+"/.user/"+profile+".json", self.app.profile_manager.prf_cfg)
        self.progress_bar.value += 10
        await asyncio.sleep(0.1)
        self.status_label.text = "Finished! :)"
        await asyncio.sleep(0.1)
        await self.app._show_info("Finished! :)")
        self.progress_bar.stop()
        self.progress_bar.value = 0
        self.status_label.text = ''
        self.app.set_btns(True)


class ReportSection:
    """
    Report section UI components and functionality
    报告部分UI组件和功能
    """
    def __init__(self, app, label_width):
        """
        Initialize report section UI
        初始化报告部分UI

        Args:
            app: Application instance 应用实例
            label_width: Label width 标签宽度
        """
        self.app = app  # Application instance 应用实例
        self.label_width = label_width  # Label width 标签宽度
        self.box = toga.Box()  # Report box 报告框
        self.uid_label = toga.Label(text="Player UID: ")  # Player UID label 玩家UID标签
        self.uid_input = toga.TextInput(on_change=self.change_image)  # UID input field UID输入框
        self.image_view = toga.ImageView(toga.Image("resources/logo.png"))  # Image view 图像视图
        self.report_button = toga.Button(text="Report",on_press=self.send_report,enabled=False)  # Report button 报告按钮

        self.box.add(self.uid_label)
        self.box.add(self.uid_input)
        self.box.add(self.image_view)
        self.box.add(self.report_button)
        self.uid_label.style.update(width=self.label_width, margin_top=10)
        self.uid_input.style.update(direction=ROW, margin=(0, 20), flex=1)
        self.image_view.style.update(height=180, width=180)
        self.box.style.update(margin_top=20)

    def change_image(self, id):
        """
        Change image preview
        更改图像预览

        Args:
            id: Input component 输入组件
        """
        self.app.logger.info("try to change image preview")
        uid = id.value
        if len(uid) >= 7:
            try:
                img_path = XML_Parser().get_imgpath_from_uid(self.app.profile_manager.prf_cfg['img_dir']+"config.xml", uid)
                img_path = self.app.profile_manager.prf_cfg['img_dir']+img_path+".png"
                self.image_view.image = toga.Image(img_path)
                self.app.logger.info("change image preview to: {}".format(img_path))
            except Exception as e:
                self.app.logger.info("changing image preview failed!")
                self.app.logger.info(e)
                return
        return

    async def send_report(self, e):
        """
        Send report (async method)
        发送报告 (异步方法)

        Args:
            e: Event object 事件对象
        """
        uid = self.uid_input.value
        if len(uid) >= 7:
            rep = Reporter(self.app.hook, self.app.profile_manager.prf_cfg['img_dir']+"config.xml")
            res = rep.send_report(uid)
            if res:
                await self.app._show_info("Thanks for Reporting!")
                self.image_view.image = toga.Image("resources/logo.png")
                self.uid_input.value = ""
            else:
                await self.app._throw_error("Player with ID {} doesn't exist!".format(uid))
                self.image_view.image = toga.Image("resources/logo.png")
                self.uid_input.value = ""


class LogSection:
    """
    Log section UI components and functionality
    日志部分UI组件和功能
    """
    def __init__(self, app):
        """
        Initialize log section UI
        初始化日志部分UI

        Args:
            app: Application instance 应用实例
        """
        self.app = app  # Application instance 应用实例

        # Logging setup
        # 日志设置
        formatter = logging.Formatter("%(asctime)s | %(name)s: %(message)s")
        self.app.logger.setLevel(logging.DEBUG)

        # Create FileHandler to update the log area in newgan.log
        # 创建文件处理器以更新newgan.log中的日志
        fh = logging.FileHandler(str(self.app.paths.app)+'/newgan.log')
        fh.setFormatter(formatter)
        self.app.logger.addHandler(fh)

        # Create StreamHandler to update the log area in the GUI
        # 创建流处理器以更新GUI中的日志
        gui_handler = logging.StreamHandler(self)
        gui_handler.setFormatter(formatter)
        self.app.logger.addHandler(gui_handler)

        # Setup top row
        # 设置顶部行
        # Top row with label and clear button
        # 顶部行包含标签和清除按钮
        self.top_row = toga.Box()  # Top row 顶部行
        self.label = toga.Label("Application Log:")  # Log label 日志标签
        self.clear_button = toga.Button(text="Clear Logs", on_press=self._clear_logs)  # Clear logs button 清除日志按钮
        self.top_row.add(self.label)
        self.top_row.add(self.clear_button)
        self.label.style.update(margin_top=10, margin_bottom=5, flex=1)
        self.clear_button.style.update(margin_top=10, margin_bottom=5, margin_left=10)
        self.top_row.style.update(direction=ROW, align_items='center')

        # Setup log area
        # 设置日志区域
        self.area = toga.MultilineTextInput(readonly=True, flex=1)  # Log multiline text input 日志多行文本输入框
        self.area.style.update(margin_bottom=10, height=150)

        # Setup container box
        # 设置容器框
        self.box = toga.Box()  # Container box 容器框
        self.box.style.update(direction=COLUMN, margin_top=10)
        self.box.add(self.top_row)
        self.box.add(self.area)

    def write(self, text):
        """
        Write log text
        写入日志文本

        Args:
            text: Text to write 要写入的文本
        """
        # Ensure UI updates happen on the main thread
        # 确保UI更新在主线程中进行
        if hasattr(self, 'area') and self.area:
            self.area.value += text
            self.area.scroll_to_bottom()

    def flush(self):
        """
        Flush log stream
        刷新日志流
        """
        pass
        
    def _clear_logs(self, widget):
        """
        Clear the log area for GUI
        清空日志区域

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
        self.area.value = ""
