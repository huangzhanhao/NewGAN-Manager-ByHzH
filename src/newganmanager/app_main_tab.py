import asyncio
import os
import logging
import toga
from toga.style import Pack
from travertino.constants import COLUMN, ROW
from .core.FaceMapper import FaceMapper
from .core.RtfParser import RtfParser
from .core.SourceSelection import SourceSelection


class MainTab:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("NewGAN App")
        self.main_tab_box = toga.Box(style=Pack(direction=COLUMN, margin=10))

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
            value="Preserve",# default mode 默认模式
            on_change=self.update_mode_info_by_selection,
            style=Pack(direction=ROW, width=label_width, margin=5)
        )
        self.allow_duplicates = toga.Switch(
            text="Allow Duplicates",
            value=True,
            style=Pack(margin=5)
        )
        self.filter_NewGAN = toga.Switch(
            text="Filter NewGAN players",
            value=True,
            style=Pack(margin=5)
        )
        self.save_backup = toga.Switch(
            text="Save backup of config.xml",
            value=True,
            style=Pack(margin=5)
        )
        mode_box = toga.Box(
            children=[mode_label, self.mode_selection, self.mode_info_label, self.allow_duplicates, self.filter_NewGAN, self.save_backup],
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
            on_press=None,  # To be implemented
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

        # Add UI components for "Viewer Box"
        self.rep_img = toga.ImageView(toga.Image("resources/apple-touch-icon.png"), style=Pack(width=180, height=180, margin=10))
        self.img_path = toga.Label(text="Image Path: ", style=Pack(margin=5))
        preview_box = toga.Box(
            children=[self.rep_img, self.img_path],
            style=Pack(direction=COLUMN, width=200)
        )
        self.uid_label = toga.Label(text="UID: ", style=Pack(margin=(5, 0)))
        self.uid_info = toga.TextInput(on_confirm=self._on_preview_uid_confirm, style=Pack(margin=(5, 0)))
        self.nat1_label = toga.Label(text="  Nation: ", style=Pack(margin=(5, 0)))
        self.nat1_info = toga.TextInput(style=Pack(width=50, margin=(5, 0)))
        self.nat2_label = toga.Label(text="  2nd Nation: ", style=Pack(margin=(5, 0)))
        self.nat2_info = toga.TextInput(style=Pack(width=50, margin=(5, 0)))
        self.name_label = toga.Label(text="  Player Name: ", style=Pack(margin=(5, 0)))
        self.name_info = toga.TextInput(style=Pack(margin=(5, 0), flex=1))
        row_box1 = toga.Box(
            children=[self.uid_label, self.uid_info, self.nat1_label, self.nat1_info, self.nat2_label, self.nat2_info, self.name_label, self.name_info],
            style=Pack(direction=ROW)
        )
        self.hair_label = toga.Label(text="Hair: ", style=Pack(margin=(5, 0)))
        self.hair_info = toga.TextInput(style=Pack(width=50, margin=(5, 0)))
        self.hair_color_label = toga.Label(text="  Hair Color: ", style=Pack(margin=(5, 0)))
        self.hair_color_info = toga.TextInput(style=Pack(width=50, margin=(5, 0)))
        self.ethnicity_label = toga.Label(text="  Ethnicity Code: ", style=Pack(margin=(5, 0)))
        self.ethnicity_info = toga.TextInput(style=Pack(width=50, margin=(5, 0)))
        self.skin_label = toga.Label(text="  Skin Code: ", style=Pack(margin=(5, 0)))
        self.skin_info = toga.TextInput(style=Pack(width=50, margin=(5, 0)))
        self.isNewGAN_label = toga.Label(text="  isNewGAN: ", style=Pack(margin=(5, 0)))
        self.isNewGAN_info = toga.TextInput(style=Pack(width=50, margin=(5, 0)))
        row_box2 = toga.Box(
            children=[self.hair_label, self.hair_info, self.hair_color_label, self.hair_color_info, self.ethnicity_label, self.ethnicity_info, self.skin_label, self.skin_info, self.isNewGAN_label, self.isNewGAN_info],
            style=Pack(direction=ROW)
        )
        self.club_label = toga.Label(text="Club: ", style=Pack(margin=(5, 0)))
        self.club_info = toga.TextInput(style=Pack(margin=(5, 0), flex=1))
        self.age_label = toga.Label(text="  Age: ", style=Pack(margin=(5, 0)))
        self.age_info = toga.TextInput(style=Pack(margin=(5, 0)))
        self.height_label = toga.Label(text="  Height: ", style=Pack(margin=(5, 0)))
        self.height_info = toga.TextInput(style=Pack(margin=(5, 0)))
        self.weight_label = toga.Label(text="  Weight: ", style=Pack(margin=(5, 0)))
        self.weight_info = toga.TextInput(style=Pack(margin=(5, 0)))
        row_box3 = toga.Box(
            children=[self.club_label, self.club_info, self.age_label, self.age_info, self.height_label, self.height_info, self.weight_label, self.weight_info],
            style=Pack(direction=ROW)
        )
        detail_box = toga.Box(
            children=[row_box1, row_box2, row_box3],
            style=Pack(direction=COLUMN, margin=5, flex=1)
        )
        self.viewer_box = toga.Box(
            children=[preview_box, detail_box],
            style=Pack(direction=ROW, flex=1)
        )
        self.main_tab_box.add(self.viewer_box)

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
                str(self.app.paths.app)+"/.user/cfg.json", 
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
                    str(self.app.paths.app) + "/.user/" + self.app.profile_manager.cur_prf + ".json", 
                    self.app.profile_manager.prf_cfg
                )
                self.set_btns(True)
            self.set_btns(True)
        except Exception:
            self.logger.error("Fatal error in main loop", exc_info=True)
            pass

    async def _action_open_file_dialog(self, widget):
        self.logger.info("Select RTF file...")
        try:
            dialog = toga.OpenFileDialog(title="Open RTF file", multiple_select=False, file_types=["rtf"])
            fname = await self.app.main_window.dialog(dialog)
            if fname is not None:
                fname = str(fname)
                self.rtf_input.value = fname
                self.app.profile_manager.prf_cfg["rtf"] = fname
                self.logger.info(f"RTF file: {fname}")
                self.app.profile_manager.save_config(
                    str(self.app.paths.app) + "/.user/" + self.app.profile_manager.cur_prf + ".json", 
                    self.app.profile_manager.prf_cfg
                )
            self.set_btns(True)
        except Exception:
            self.logger.error("Fatal error in main loop", exc_info=True)
            pass

    def update_mode_info_by_selection(self, widget):
        self.mode_info_label.text = self.app.mode_info.get(widget.value, "Unknown mode")
        self.logger.debug(f"Updating mode info label: {self.app.mode_info.get(widget.value, 'Unknown mode')}")

    async def _validate_rtf_file(self, rtf_path, rtf_parser):
        try:
            # 验证RTF文件格式
            if not rtf_parser.check_rtf_valid(rtf_path):
                await self.app.throw_error("The RTF file is invalid!")
                return False
        except FileNotFoundError:
            self.logger.error(f"RTF file doesn't exist: {rtf_path}")
            await self.app.throw_error("The RTF file doesn't exist!")
            return False
        except PermissionError:
            self.logger.error(f"Permission denied to access RTF file: {rtf_path}")
            await self.app.throw_error("Permission denied to access the RTF file!")
            return False
        except Exception as e:
            self.logger.error(f"Error while validating RTF file: {e}")
            await self.app.throw_error(f"Error while validating RTF file: {e}")
            return False
        return True

    async def _validate_image_directory(self, img_dir):
        if not os.path.isdir(img_dir):
            await self.app.throw_error("The image directory doesn't exist!")
            self.app.profile_manager.prf_cfg['img_dir'] = ''
            self.set_btns()
            return False
        # 检查图像目录是否包含所有需要的子文件夹
        img_dirs = set()
        for entry in os.scandir(img_dir):
            if entry.is_dir():
                img_dirs.add(entry.name)
        for fp_dir in self.app.facepack_dirs:
            if fp_dir not in img_dirs:
                # 询问用户是否要创建缺失的目录
                self.logger.info(f"Folder '{fp_dir}' is missing in the image directory")
                dialog = toga.QuestionDialog("Missing Directory", f"Folder '{fp_dir}' is missing in the image directory. Do you want to create it and continue?")
                user_choose = await self.app.main_window.dialog(dialog)
                if user_choose:
                    try:
                        os.makedirs(os.path.join(img_dir, fp_dir), exist_ok=True)
                        self.logger.info(f"Created directory: {fp_dir}")
                        continue
                    except Exception as e:
                        await self.app.throw_error(f"Failed to create directory {fp_dir}: {e}")
                        return False
                else:
                    # 用户选择不创建目录，显示提示错误对话框并返回False
                    self.logger.error(f"Folder '{fp_dir}' is missing in the image directory, and user chose not to create it.")
                    await self.app.throw_error(f"Folder {fp_dir} is missing in the image directory")
                    return False
        return True

    async def _replace_faces(self, widget):
        self.logger.info("Start Replace Faces")
        self.cancel_button.enabled = True
        # self.cancel_button.style=Pack(visibility="visible", flex=0.2, margin=5)
        self.cancel_button.style.update(visibility="visible")
        self.progress_bar.value = 0
        self.status_label.text = ''
        rtf = self.app.profile_manager.prf_cfg['rtf']
        img_dir = self.app.profile_manager.prf_cfg['img_dir']
        profile = self.app.profile_manager.cur_prf
        mode = str(self.mode_selection.value) if self.mode_selection.value else "Preserve"
        self.logger.info(f"rtf: {rtf}")
        self.logger.info(f"img_dir: {img_dir}")
        self.logger.info(f"profile: {profile}")
        self.logger.info(f"mode: {mode}")
        self.set_btns(False)

        self.progress_bar.start()
        self.status_label.text = "Parsing RTF file..."
        await asyncio.sleep(0.1)
        rtf_parser = RtfParser()
        # Validate RTF file
        if not await self._validate_rtf_file(rtf, rtf_parser):
            self.app.profile_manager.prf_cfg['rtf'] = ''
            self.rtf_input.value = ''
            self.set_btns()
            self.progress_bar.stop()
            return
        # Validate image directory
        if not await self._validate_image_directory(img_dir):
            self.progress_bar.stop()
            return
        self.progress_bar.value += 10
        try:
            self.rtf_data = rtf_parser.parse_rtf(rtf, self.filter_NewGAN.value)
        except FileNotFoundError as e:
            self.logger.error(f"RTF file not found: {e}")
            await self.app.throw_error(f"RTF file not found: {e}")
            self.progress_bar.stop()
            return
        except UnicodeDecodeError as e:
            self.logger.error(f"Error decoding RTF file: {e}")
            await self.app.throw_error(f"Error decoding RTF file: {e}")
            self.progress_bar.stop()
            return
        except ValueError as e:
            self.logger.error(f"Error parsing RTF file: {e}")
            await self.app.throw_error(f"Error parsing RTF file: {e}")
            self.progress_bar.stop()
            return
        except Exception as e:
            self.logger.error(f"Error parsing RTF file: {e}")
            await self.app.throw_error(f"Error parsing RTF file: {e}")
            self.progress_bar.stop()
            return
        self.progress_bar.value += 20
        self.status_label.text = "Mapping player to image..."
        await asyncio.sleep(0.1)
        self.mapping_data = FaceMapper(img_dir, self.app.profile_manager).generate_mapping(self.rtf_data, mode, self.allow_duplicates.value)
        self.progress_bar.value += 60
        self.status_label.text = "Generating config.xml..."
        await asyncio.sleep(0.1)
        try:
            self.app.profile_manager.write_xml(self.mapping_data, self.save_backup.value)
        except FileNotFoundError as e:
            self.logger.error(f"Configuration template file not found: {e}")
            await self.app.throw_error(f"Configuration template file not found: {e}")
            self.progress_bar.stop()
            return
        except PermissionError as e:
            self.logger.error(f"Permission denied when accessing files: {e}")
            await self.app.throw_error(f"Permission denied when accessing files: {e}")
            self.progress_bar.stop()
            return
        except Exception as e:
            self.logger.error(f"Unexpected error while writing XML: {e}")
            await self.app.throw_error(f"Unexpected error while writing XML: {e}")
            self.progress_bar.stop()
            return
        # save profile metadata
        # 保存配置文件元数据
        self.status_label.text = "Save metadata for profile"
        self.progress_bar.value += 10
        await asyncio.sleep(0.1)
        self.app.profile_manager.save_config(
            str(self.app.paths.app)+"/.user/"+profile+".json", 
            self.app.profile_manager.prf_cfg
        )
        self.progress_bar.value += 10
        await asyncio.sleep(0.1)
        self.status_label.text = "Finished! :)"
        await self.app.show_info("Finished! :)")
        self.progress_bar.stop()
        self.cancel_button.enabled = False
        self.cancel_button.style.update(visibility="hidden")
        self.set_btns(True)

    def _on_preview_uid_confirm(self, widget, **kwargs):
        uid = self.uid_info.value.strip()
        if not uid:
            self.logger.warning("The UID to be previewed is empty")
        else:
            self.logger.info(f"Previewing UID: {uid}")
            if hasattr(self, 'mapping_data') and self.mapping_data:
                if isinstance(self.mapping_data, list) and len(self.mapping_data) > 0:
                    mapped_player = next((p for p in self.mapping_data if p and len(p) > 0 and (p[0] == uid or p[0] == "r-" + uid)), None)
                    if mapped_player:
                        # mapping_data format: [uid, ethnicity, image_filename]
                        self.uid_info.value = mapped_player[0]
                        self.img_path.text = f"{mapped_player[1]}\\{mapped_player[2]}"
                        # 支持多种图片格式 (png, jpg, jpeg)
                        img_base = os.path.join(self.app.profile_manager.prf_cfg['img_dir'], mapped_player[1], mapped_player[2])
                        for ext in ['.png', '.jpg', '.jpeg']:
                            image_file = img_base + ext
                            if os.path.isfile(image_file):
                                self.rep_img.image = toga.Image(image_file)
                                break
                            else:
                                self.rep_img.image = toga.Image("resources/apple-touch-icon.png")
            else:
                self.logger.warning("No mapping data available for previewing player details")
                self.img_path.text = "Image Path: no found"
                self.rep_img.image = toga.Image("resources/apple-touch-icon.png")
            # Then get player details from rtf_data
            if hasattr(self, 'rtf_data') and self.rtf_data:
                # Each list in rtf_data: [UID, primary_nat, sec_nat, name, hair_length, hair_color, ethnicity_code, ...]
                player = next((p for p in self.rtf_data if p and len(p) > 0 and (p[0] == uid or p[0] == "r-" + uid)), None)
                if player:
                    # [0]UID, [1]primary_nat, [2]sec_nat, [3]name, [4]hair_length, 
                    # [5]hair_color, [6]ethnicity_code, [7]skin_code, [8]face_id, [9]club, 
                    # [10]age, [11]height, [12]weight, [13]is_NewGAN
                    self.nat1_info.value = player[1] if len(player) > 1 else ''
                    self.nat2_info.value = player[2] if len(player) > 2 else ''
                    self.name_info.value = player[3] if len(player) > 3 else ''
                    self.hair_info.value = player[4] if len(player) > 4 else ''
                    self.hair_color_info.value = player[5] if len(player) > 5 else ''
                    self.ethnicity_info.value = player[6] if len(player) > 6 else ''
                    if len(player) > 7:
                        self.skin_info.value = player[7] if len(player) > 7 else ''
                        self.club_info.value = player[9] if len(player) > 9 else ''
                        self.age_info.value = player[10] if len(player) > 10 else ''
                        self.height_info.value = player[11] if len(player) > 11 else ''
                        self.weight_info.value = player[12] if len(player) > 12 else ''
                        self.isNewGAN_info.value = player[13] if len(player) > 13 else ''
            else:
                self.logger.warning("No RTF data available for previewing player details")
        return