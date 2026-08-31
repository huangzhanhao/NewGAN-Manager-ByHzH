import logging

import toga
from toga.style import Pack
from travertino.constants import COLUMN, ROW

from .app_replace_service import ReplaceFacesService
from .app_viewer import PlayerViewer
from .core.SourceSelection import SourceSelection


class MainTab:
    """主标签页：Profile 管理、路径选择、模式与开关、替换执行入口

    业务编排委托给 ReplaceFacesService，底部球员预览/单人换脸委托给 PlayerViewer。
    """

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("NewGAN App")
        self.main_tab_box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        # 替换流程控制器（持有最近一次 rtf_data / mapping_data 供 Viewer 读取）
        self.replace_service = ReplaceFacesService(app)

        # Create UI sections with specified label width
        label_width = 110
        button_width = 70

        # Add UI components for "Create Profile"
        create_label = toga.Label(text="Create Profile: ", style=Pack(width=label_width, margin=5))
        self.create_input = toga.TextInput(placeholder="Enter your profile name", style=Pack(margin=5, flex=1))
        self.create_button = toga.Button(text="Create", on_press=self._create_profile, style=Pack(width=button_width, margin=5))
        create_box = toga.Box(
            children=[create_label, self.create_input, self.create_button],
            style=Pack(direction=ROW, align_items='center')
        )
        self.main_tab_box.add(create_box)

        # Add UI components for "Select Profile"
        select_label = toga.Label(text="Select Profile: ", style=Pack(width=label_width, margin=5))
        self.profile_list = SourceSelection(
            items=list(self.app.profile_manager.config["Profile"].keys()),
            value=self.app.profile_manager.cur_prf or "No Profile",
            on_change=self._set_profile_status,
            style=Pack(direction=ROW, margin=5, flex=1)
        )
        self.delete_button = toga.Button(text="Delete", on_press=self._delete_profile, style=Pack(width=button_width, margin=5))
        sel_box = toga.Box(
            children=[select_label, self.profile_list, self.delete_button],
            style=Pack(direction=ROW)
        )
        self.main_tab_box.add(sel_box)

        # Add UI components for "Images Directory"
        dir_label = toga.Label(text="Images Directory: ", style=Pack(width=label_width, margin=5))
        self.dir_input = toga.TextInput(
            readonly=True,
            value=self.app.profile_manager.prf_cfg['img_dir'],
            style=Pack(margin=5, flex=1)
        )
        self.dir_button = toga.Button(
            text="Browse",
            on_press=self._action_select_folder_dialog,
            enabled=False,
            style=Pack(width=button_width, margin=5)
        )
        dir_box = toga.Box(
            children=[dir_label, self.dir_input, self.dir_button],
            style=Pack(direction=ROW)
        )
        self.main_tab_box.add(dir_box)

        # Add UI components for "RTF File"
        rtf_label = toga.Label(text="RTF File: ", style=Pack(width=label_width, margin=5))
        self.rtf_input = toga.TextInput(
            readonly=True,
            value=self.app.profile_manager.prf_cfg['rtf'],
            style=Pack(margin=5, flex=1)
        )
        self.rtf_button = toga.Button(
            text="Browse",
            on_press=self._action_open_file_dialog,
            enabled=False,
            style=Pack(width=button_width, margin=5)
        )
        rtf_box = toga.Box(
            children=[rtf_label, self.rtf_input, self.rtf_button],
            style=Pack(direction=ROW)
        )
        self.main_tab_box.add(rtf_box)

        # Add UI components for "Mode Box"
        mode_label = toga.Label(text="Mode: ", style=Pack(width=label_width, margin=5))
        self.mode_info_label = toga.Label(
            text=app.mode_info.get("Preserve"),
            style=Pack(margin=5, flex=1)
        )
        self.mode_selection = SourceSelection(
            items=list(app.mode_info.keys()),
            value="Preserve",  # default mode 默认模式
            on_change=self.update_mode_info_by_selection,
            style=Pack(direction=ROW, width=label_width, margin=5)
        )
        self.allow_duplicates = toga.Switch(
            text="Allow Duplicates",
            value=True,
            style=Pack(margin=5)
        )
        self.isNewGAN = toga.Switch(
            text="only for NewGAN players",
            value=True,
            style=Pack(margin=5)
        )
        self.save_backup = toga.Switch(
            text="Save backup of config.xml",
            value=True,
            style=Pack(margin=5)
        )
        mode_box = toga.Box(
            children=[mode_label, self.mode_selection, self.mode_info_label, self.allow_duplicates, self.isNewGAN, self.save_backup],
            style=Pack(direction=ROW)
        )
        self.main_tab_box.add(mode_box)

        # Add UI components for "Replacer Box"
        self.replace_faces_button = toga.Button(
            text="Replace Faces",
            on_press=self._replace_faces,
            enabled=False,
            style=Pack(flex=0.8, margin=5)
        )
        self.cancel_button = toga.Button(
            text="Cancel",
            on_press=self._cancel_replace_faces,
            enabled=False,
            style=Pack(visibility="hidden", flex=0.2, margin=5)
        )
        replayce_box = toga.Box(
            children=[self.replace_faces_button, self.cancel_button],
            style=Pack(direction=ROW)
        )
        self.progress_bar = toga.ProgressBar(
            max=100,
            style=Pack(flex=0.8, margin=5)
        )
        self.status_label = toga.Label(
            text="",
            style=Pack(flex=0.2, margin=5)
        )
        status_progress_box = toga.Box(
            children=[self.progress_bar, self.status_label],
            style=Pack(direction=ROW)
        )
        replacer_box = toga.Box(
            children=[replayce_box, status_progress_box],
            style=Pack(direction=COLUMN)
        )
        self.main_tab_box.add(replacer_box, toga.Divider(style=Pack(margin=10)))

        # Add UI components for "Viewer Box"（拆分至 PlayerViewer）
        self.viewer = PlayerViewer(self.app, self)
        self.main_tab_box.add(self.viewer.viewer_box)

    def set_btns(self, value=True):
        """
        根据当前配置文件状态和输入设置来设置按钮的启用状态
        Set button enabled states based on current profile status and input settings

        此方法控制界面中三个主要按钮的启用状态:
        1. Replace Faces 按钮 - 执行头像替换操作
        2. Browse 按钮 (图片目录) - 选择图片目录
        3. Browse 按钮 (RTF文件) - 选择RTF文件

        按钮启用逻辑:
        - 如果当前配置文件为 "No Profile"，则所有按钮都禁用
        - 如果图片目录或RTF文件路径为空，则只能启用浏览按钮，禁用执行按钮
        - 其他情况下，根据传入的value参数设置所有按钮的启用状态

        Args:
            value (bool): 按钮的启用状态，默认为True
                         Button enabled state, default is True
        """
        if not all([self.replace_faces_button, self.dir_button, self.rtf_button]):
            return
        if self.app.profile_manager and self.app.profile_manager.cur_prf == "No Profile":
            # 当前为"No Profile"配置文件时，禁用所有按钮
            self.replace_faces_button.enabled = False
            self.dir_button.enabled = False
            self.rtf_button.enabled = False
        elif self.app.profile_manager and (
            self.app.profile_manager.prf_cfg.get("img_dir", "") == ""
            or self.app.profile_manager.prf_cfg.get("rtf", "") == ""
        ):
            # 当前配置文件缺少必要路径信息时，禁用执行按钮，启用浏览按钮
            self.replace_faces_button.enabled = False
            self.dir_button.enabled = value
            self.rtf_button.enabled = value
        else:
            # 所有条件满足时，根据value参数设置所有按钮状态
            self.replace_faces_button.enabled = value
            self.dir_button.enabled = value
            self.rtf_button.enabled = value

    def _create_profile(self, widget):
        name = self.create_input.value
        if not name or not name.strip():
            self.app.throw_error("The Profile is Null!")
            return
        try:
            self.app.profile_manager.create_profile(name)
            self.profile_list.add_item(name)
            self.profile_list.value = name
            self.create_input.value = None
            self._refresh_input_text(True)
            self.set_btns(True)
        except Exception as e:
            self.logger.error(f"Error while creating profile: {e}")
            self.app.throw_error(f"Error creating profile: {e}")

    def _delete_profile(self, widget):
        prf = self.profile_list.value
        result = self.app.profile_manager.delete_profile(prf)
        if not result:
            self.app.throw_error("Can't delete 'No Profile'")
            return
        self.profile_list.remove_item(prf)
        self.profile_list.value = "No Profile"
        self._refresh_input_text(clear=True)
        self.set_btns(False)

    def _set_profile_status(self, e):
        self.logger.info(f"switch profile: {e.value}")
        if e.value is None:
            self.logger.info(f"catch none {self.app.profile_manager.cur_prf}")
        else:
            name = e.value
            self.app.profile_manager.load_profile(name)
            self._refresh_input_text()
            self.set_btns(True)
            self.app.profile_manager.save_config(
                self.app.profile_manager.user_path("cfg.json"),
                self.app.profile_manager.config
            )

    def _refresh_input_text(self, clear=False):
        if clear:
            self.dir_input.value = None
            self.rtf_input.value = None
        else:
            self.dir_input.value = self.app.profile_manager.prf_cfg['img_dir']
            self.rtf_input.value = self.app.profile_manager.prf_cfg['rtf']
        self.logger.debug(f"Refresh InputText. Dir_input: {self.dir_input.value}, Rtf_input: {self.rtf_input.value}")

    async def _action_select_folder_dialog(self, widget):
        self.logger.info("Select images folder...")
        try:
            dialog = toga.SelectFolderDialog(title="Select image root folder")
            path_name = await self.app.main_window.dialog(dialog)
            if path_name:
                path_name = str(path_name)
                self.dir_input.value = path_name + "/"
                self.app.profile_manager.prf_cfg["img_dir"] = path_name + "/"
                self.app.profile_manager.save_config(
                    self.app.profile_manager.user_path(self.app.profile_manager.cur_prf + ".json"),
                    self.app.profile_manager.prf_cfg
                )
                self.set_btns(True)
            self.set_btns(True)
        except Exception:
            self.logger.error("Fatal error in main loop", exc_info=True)

    async def _action_open_file_dialog(self, widget):
        try:
            if widget == self.rtf_button:
                # RTF文件按钮触发的逻辑
                dialog = toga.OpenFileDialog(title="Open RTF file", multiple_select=False, file_types=["rtf"])
                fname = await self.app.main_window.dialog(dialog)
                if fname is not None:
                    fname = str(fname)
                    self.logger.info("Select RTF file...")
                    self.rtf_input.value = fname
                    self.app.profile_manager.prf_cfg["rtf"] = fname
                    self.logger.info(f"RTF file: {fname}")
                    self.app.profile_manager.save_config(
                        self.app.profile_manager.user_path(self.app.profile_manager.cur_prf + ".json"),
                        self.app.profile_manager.prf_cfg
                    )
                    self.set_btns(True)
        except Exception:
            self.logger.error("Fatal error in main loop", exc_info=True)

    def update_mode_info_by_selection(self, widget):
        self.mode_info_label.text = self.app.mode_info.get(widget.value, "Unknown mode")
        self.logger.debug(f"Updating mode info label: {self.app.mode_info.get(widget.value, 'Unknown mode')}")

    async def _replace_faces(self, widget):
        self.logger.info("Start Replace Faces")
        # 初始化UI状态
        self.cancel_button.enabled = True
        self.cancel_button.style.update(visibility="visible")
        self.progress_bar.value = 0
        self.status_label.text = ''
        self.set_btns(False)
        # 获取配置参数
        rtf = self.app.profile_manager.prf_cfg['rtf']
        img_dir = self.app.profile_manager.prf_cfg['img_dir']
        profile = self.app.profile_manager.cur_prf
        mode = str(self.mode_selection.value) if self.mode_selection.value else "Preserve"
        self.logger.info(f"rtf: {rtf}")
        self.logger.info(f"img_dir: {img_dir}")
        self.logger.info(f"profile: {profile}")
        self.logger.info(f"mode: {mode}")
        # 执行主流程（取消通过 threading.Event 传导到工作线程）
        result = await self.replace_service.run(
            rtf, img_dir, profile, mode,
            filter_newgan=self.isNewGAN.value,
            allow_duplicates=self.allow_duplicates.value,
            save_backup=self.save_backup.value,
            on_progress=self._update_progress,
        )
        if result == "finished":
            await self.app.show_info("Finished! :)")
        elif result == "cancelled":
            self.status_label.text = "Cancelled"
        self._cleanup_after_replace()

    def _cleanup_after_replace(self):
        """清理替换任务完成后的UI状态"""
        self.cancel_button.enabled = False
        self.cancel_button.style.update(visibility="hidden")
        self.set_btns(True)
        self.progress_bar.stop()

    def _update_progress(self, status, value):
        """更新进度条和状态标签的辅助方法"""
        self.status_label.text = status
        self.progress_bar.value = value

    async def _cancel_replace_faces(self, widget):
        """取消正在进行的替换任务：置位取消标志，工作线程会在映射循环中中断"""
        if self.cancel_button.enabled:
            self.status_label.text = "Cancelling..."
            self.replace_service.request_cancel()
