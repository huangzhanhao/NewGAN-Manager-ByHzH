import toga
from toga.style import Pack
from travertino.constants import COLUMN, ROW
import os
import asyncio
from .core.Mapper import Mapper
from .core.RtfParser import RtfParser
from .core.XmlParser import XmlParser
from .core.Reporter import Reporter
from .core.SourceSelection import SourceSelection


class MainTab:
    def __init__(self, app):
        self.app = app
        # Create main box without margin to avoid layout issues
        # 创建主框但不添加边距以避免布局问题
        self.main_tab_box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        # Create UI sections with specified label width
        label_width = 110
        button_width = 70

        # TOP Profiles - Create Profile
        self.create_label = toga.Label(text="Create Profile: ", style=Pack(width=label_width, margin=5))
        self.create_input = toga.TextInput(placeholder="Enter your profile name", style=Pack(direction=ROW, margin=5, flex=1))
        self.create_button = toga.Button(text="Create", on_press=self._create_profile, style=Pack(width=button_width, margin=5))

        self.create_box = toga.Box(
            children=[self.create_label, self.create_input, self.create_button],
            style=Pack(direction=ROW, align_items='center')
        )
        self.main_tab_box.add(self.create_box)

        # TOP Profiles - Select Profile
        self.select_label = toga.Label(text="Select Profile: ", style=Pack(width=label_width, margin=5))
        self.profile_list = SourceSelection(
            items=list(self.app.profile_manager.config["Profile"].keys()),
            on_change=self._set_profile_status,
            style=Pack(direction=ROW, margin=5, flex=1)
        )
        self.profile_list.value = self.app.profile_manager.cur_prf  # Current profile 当前配置文件
        self.delete_button = toga.Button(text="Delete", on_press=self._delete_profile, style=Pack(width=button_width, margin=5))

        self.sel_box = toga.Box(
            children=[self.select_label, self.profile_list, self.delete_button],
            style=Pack(direction=ROW)
        )
        self.main_tab_box.add(self.sel_box)

        # MID Path selections - Images Directory
        self.dir_label = toga.Label(text="Images Directory: ", style=Pack(width=label_width, margin=5))
        self.dir_input = toga.TextInput(
            readonly=True,
            value=self.app.profile_manager.prf_cfg['img_dir'],
            style=Pack(direction=ROW, margin=5, flex=1)
        )
        self.dir_button = toga.Button(
            text="Browse",
            on_press=self.action_select_folder_dialog,
            enabled=False,
            style=Pack(width=button_width, margin=5)
        )

        self.dir_box = toga.Box(
            children=[self.dir_label, self.dir_input, self.dir_button],
            style=Pack(direction=ROW)
        )
        self.main_tab_box.add(self.dir_box)

        # MID Path selections - RTF File
        self.rtf_label = toga.Label(text="RTF File: ", style=Pack(width=label_width, margin=5))
        self.rtf_input = toga.TextInput(
            readonly=True,
            value=self.app.profile_manager.prf_cfg['rtf'],
            style=Pack(direction=ROW, margin=5, flex=1)
        )
        self.rtf_button = toga.Button(
            text="Browse",
            on_press=self.action_open_file_dialog,
            enabled=False,
            style=Pack(width=button_width, margin=5)
        )

        self.rtf_box = toga.Box(
            children=[self.rtf_label, self.rtf_input, self.rtf_button],
            style=Pack(direction=ROW)
        )
        self.main_tab_box.add(self.rtf_box)

        # Generation mode selection
        self.mode_label = toga.Label(text="Mode: ", style=Pack(width=label_width, margin=5))

        self.mode_info_label = toga.Label(
            text=app.mode_info.get("Preserve"),
            style=Pack(margin=5, flex=1)
        )

        self.mode_selection = SourceSelection(
            items=list(app.mode_info.keys()),
            value="Preserve",# Set default mode 设置默认模式
            on_change=self.update_mode_info_by_selection,
            style=Pack(direction=ROW, width=label_width, margin=5)
        )

        self.allow_duplicates = toga.Switch(
            text="Allow Duplicates?",
            value=True,
            style=Pack(margin=5)
        )

        # Create mode selection box with children
        self.mode_box = toga.Box(
            children=[self.mode_label, self.mode_selection, self.mode_info_label, self.allow_duplicates],
            style=Pack(direction=ROW)
        )
        self.main_tab_box.add(self.mode_box)

        # BOTTOM Generation
        self.generate_button = toga.Button(
            text="Replace Faces",
            on_press=self._replace_faces,
            enabled=False,
            style=Pack(margin=5)
        )

        self.status_label = toga.Label(
            text="",
            style=Pack(flex=0.2, margin=5)
        )
        self.progress_bar = toga.ProgressBar(
            max=100,
            style=Pack(flex=0.8, margin=5)
        )

        self.status_progress_box = toga.Box(
            children=[self.progress_bar, self.status_label],
            style=Pack(direction=ROW)
        )

        # Create generation box with children
        self.gen_box = toga.Box(
            children=[self.generate_button, self.status_progress_box],
            style=Pack(direction=COLUMN, flex=1)
        )
        self.main_tab_box.add(self.gen_box)

    def set_btns(self, value=True):
        """
        Set button enabled states
        设置按钮启用状态

        Args:
            value: Button enabled state 按钮启用状态
        """
        if not all([self.generate_button, self.dir_button, self.rtf_button]):
            return

        if self.app.profile_manager and self.app.profile_manager.cur_prf == "No Profile":
            self.generate_button.enabled = False
            self.dir_button.enabled = False
            self.rtf_button.enabled = False
        elif self.app.profile_manager and (
            self.app.profile_manager.prf_cfg.get("img_dir", "") == ""
            or self.app.profile_manager.prf_cfg.get("rtf", "") == ""
        ):
            self.generate_button.enabled = False
            self.dir_button.enabled = value
            self.rtf_button.enabled = value
        else:
            self.generate_button.enabled = value
            self.dir_button.enabled = value
            self.rtf_button.enabled = value

    def _create_profile(self, widget):
        """
        Create profile (internal method)
        创建配置文件 (内部方法)

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
        name = self.create_input.value
        if not name or not name.strip():
            self.app.throw_error("The Profile is Null!")
            return
        self.app.profile_manager.create_profile(name)
        self.profile_list.add_item(name)
        self.profile_list.value = name
        self.create_input.value = None
        self._refresh_inp(True)
        self.set_btns(True)

    def _delete_profile(self, widget):
        """
        Delete profile (internal method)
        删除配置文件 (内部方法)

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
        prf = self.profile_list.value
        result = self.app.profile_manager.delete_profile(prf)
        if not result:
            # 处理删除失败的情况，显示错误信息
            self.app.throw_error("Can't delete 'No Profile'")
            return
        self.profile_list.remove_item(prf)
        self.profile_list.value = "No Profile"
        self._refresh_inp(True)
        self.set_btns(False)

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
            self.set_btns(True)
            self.app.profile_manager.config_manager.save_config(
                str(self.app.paths.app)+"/.user/cfg.json", 
                self.app.profile_manager.config
            )

    def _refresh_inp(self, clear=False):
        if clear:
            self.dir_input.value = None
            self.rtf_input.value = None
        else:
            self.dir_input.value = self.app.profile_manager.prf_cfg['img_dir']
            self.rtf_input.value = self.app.profile_manager.prf_cfg['rtf']
        self.app.logger.debug(
            "Refresh InputText. Dir_input: %s, Rtf_input: %s",
            self.dir_input.value,
            self.dir_input.value,
        )

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
                self.app.profile_manager.config_manager.save_config(
                    str(self.app.paths.app) + "/.user/" + self.app.profile_manager.cur_prf + ".json", 
                    self.app.profile_manager.prf_cfg
                )
                self.set_btns(True)
            self.set_btns(True)
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
                self.app.profile_manager.config_manager.save_config(
                    str(self.app.paths.app) + "/.user/" + self.app.profile_manager.cur_prf + ".json", 
                    self.app.profile_manager.prf_cfg
                )
            else:
                self.app.profile_manager.prf_cfg["rtf"] = ""
                self.rtf_input.value = ""
                self.app.profile_manager.config_manager.save_config(
                    str(self.app.paths.app) + "/.user/" + self.app.profile_manager.cur_prf + ".json", 
                    self.app.profile_manager.prf_cfg
                )
            self.set_btns(True)
        except Exception:
            self.app.logger.error("Fatal error in main loop", exc_info=True)
            pass

    def update_mode_info_by_selection(self, widget):
        self.mode_info_label.text = self.app.mode_info.get(widget.value, "Unknown mode")
        self.app.logger.debug("Updating mode info label: {}".format(self.app.mode_info.get(widget.value, "Unknown mode")))

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
            await self.app.throw_error("The RTF file doesn't exist!")
            self.progress_bar.stop()
            self.app.profile_manager.prf_cfg['rtf'] = ''
            return
        if not os.path.isdir(img_dir):
            await self.app.throw_error("The image directory doesn't exist!")
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
                dialog = toga.QuestionDialog("Missing Directory", "Folder '{}' is missing in the image directory. Do you want to create it and continue?".format(fp_dir))
                user_choose = await self.app.main_window.dialog(dialog)
                self.app.logger.debug("Question window: Missing Directory.   Folder '{}' is missing in the image directory. Do you want to create it and continue?".format(fp_dir))
                self.app.logger.debug("User choose: {}".format(user_choose))
                if user_choose:
                    try:
                        os.makedirs(os.path.join(img_dir, fp_dir), exist_ok=True)
                        self.app.logger.info("Created directory: {}".format(fp_dir))
                        continue
                    except Exception as e:
                        await self.app.throw_error("Failed to create directory {}: {}".format(fp_dir, str(e)))
                        self.progress_bar.stop()
                        return
                else:
                    # User chose not to create the directory, show error and stop
                    # 用户选择不创建目录，显示错误并停止
                    await self.app.throw_error("Folder {} is missing in the image directory".format(fp_dir))
                    self.progress_bar.stop()
                    return

        self.app.logger.info("rtf: {}".format(rtf))
        self.app.logger.info("img_dir: {}".format(img_dir))
        self.app.logger.info("profile: {}".format(profile))
        self.app.logger.info("mode: {}".format(mode))
        self.set_btns(False)
        self.progress_bar.start()
        self.status_label.text = "Parsing RTF"
        await asyncio.sleep(0.1)
        rtf_parser = RtfParser()
        if not rtf_parser.check_rtf_valid(rtf):
            await self.app.throw_error("The RTF file is invalid!")
            self.progress_bar.stop()
            return
        rtf_data = rtf_parser.parse_rtf(rtf)
        self.progress_bar.value += 20
        self.status_label.text = "Map player to ethnicity"
        await asyncio.sleep(0.1)
        mapping_data = Mapper(img_dir, self.app.profile_manager).generate_mapping(rtf_data, mode, self.allow_duplicates)
        self.progress_bar.value += 60
        self.status_label.text = "Generate config.xml"
        await asyncio.sleep(0.1)
        try:
            self.app.profile_manager.write_xml(mapping_data)
        except FileNotFoundError as e:
            self.app.logger.error(f"Configuration template file not found: {e}")
            await self.app.throw_error(f"Configuration template file not found: {e}")
            self.progress_bar.stop()
            return
        except PermissionError as e:
            self.app.logger.error(f"Permission denied when accessing files: {e}")
            await self.app.throw_error(f"Permission denied when accessing files: {e}")
            self.progress_bar.stop()
            return
        except Exception as e:
            self.app.logger.error(f"Unexpected error while writing XML: {e}")
            await self.app.throw_error(f"Unexpected error while writing XML: {e}")
            self.progress_bar.stop()
            return
        # save profile metadata (used pics and config.xml)
        # 保存配置文件元数据（使用的图片和config.xml）
        self.status_label.text = "Save metadata for profile"
        self.progress_bar.value += 10
        await asyncio.sleep(0.1)
        self.app.profile_manager.config_manager.save_config(
            str(self.app.paths.app)+"/.user/"+profile+".json", 
            self.app.profile_manager.prf_cfg
        )
        self.progress_bar.value += 10
        await asyncio.sleep(0.1)
        self.status_label.text = "Finished! :)"
        await asyncio.sleep(0.1)
        await self.app.show_info("Finished! :)")
        self.progress_bar.stop()
        self.progress_bar.value = 0
        self.status_label.text = ''
        self.set_btns(True)
