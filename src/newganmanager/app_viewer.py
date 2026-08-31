"""底部 Viewer 区：按 UID 预览球员信息与当前头像，支持单个球员换脸

UI 组件：查询与替换业务委托给 PlayerService，本类只负责展示与事件回调。
球员数据与映射数据由 MainTab（ReplaceFacesService）持有，
通过构造时传入的 main_tab 引用读取。
"""
import logging

import toga
from toga.style import Pack
from travertino.constants import COLUMN, ROW

from .services.player_service import PlayerService


class PlayerViewer:
    def __init__(self, app, main_tab):
        """
        Args:
            app: NewGANManager 应用实例
            main_tab: MainTab 实例（提供 rtf_data / mapping_data / save_backup）
        """
        self.app = app
        self.main_tab = main_tab
        self.logger = logging.getLogger("NewGAN App")
        self.player_service = PlayerService(app.profile_manager, logger=self.logger)

        # 头像预览区
        self.rep_img = toga.ImageView(toga.Image("resources/favicon-400×400.png"), style=Pack(width=180, height=180, margin=10))
        self.img_path = toga.Label(text="Image Path: ", style=Pack(margin=5))
        preview_box = toga.Box(
            children=[self.rep_img, self.img_path],
            style=Pack(direction=COLUMN, width=200)
        )

        # 球员信息行 1：UID / 国籍 / 第二国籍 / 姓名
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

        # 球员信息行 2：头发 / 发色 / 种族码 / 肤色 / 是否随机人
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

        # 球员信息行 3：俱乐部 / 年龄 / 身高 / 体重
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

        # 单人换脸行：图片路径 / Browse / Replace it
        self.img_input = toga.TextInput(placeholder="Image to replace...", style=Pack(margin=5, flex=1))
        self.img_button = toga.Button(
            text="Browse",
            on_press=self._action_open_image_dialog,
            style=Pack(margin=5)
        )
        self.replace_it_button = toga.Button(
            text="Replace it",
            on_press=self._replace_it,
            style=Pack(margin=5)
        )
        row_box4 = toga.Box(
            children=[self.img_input, self.img_button, self.replace_it_button],
            style=Pack(direction=ROW, margin=5)
        )
        detail_box = toga.Box(
            children=[row_box1, row_box2, row_box3, toga.Divider(), row_box4],
            style=Pack(direction=COLUMN, margin=5, flex=1)
        )
        self.viewer_box = toga.Box(
            children=[preview_box, detail_box],
            style=Pack(direction=ROW, flex=1)
        )

    async def _action_open_image_dialog(self, widget):
        """选择用于单人替换的图片文件"""
        try:
            dialog = toga.OpenFileDialog(title="Select image file", multiple_select=False, file_types=["png", "jpg", "jpeg"])
            fname = await self.app.main_window.dialog(dialog)
            if fname is not None:
                fname = str(fname)
                self.logger.info("Select image file...")
                self.img_input.value = fname
                self.logger.info(f"Image file: {fname}")
        except Exception:
            self.logger.error("Fatal error in main loop", exc_info=True)

    def _on_preview_uid_confirm(self, widget, **kwargs):
        uid = self.uid_info.value.strip()
        if not uid:
            self.logger.warning("The UID to be previewed is empty")
            return
        if not self.app.profile_manager.cur_group:
            self.logger.warning("No current group selected, cannot preview")
            return
        self.logger.info(f"Previewing UID: {uid}")
        # 重置显示内容
        self.img_path.text = "Image Path: ...\\..."
        self.rep_img.image = toga.Image("resources/favicon-400×400.png")
        ethnicity = None
        image_name = None
        # 首先在最近一次批量替换的 mapping_data 中查找
        mapping_data = self.main_tab.replace_service.mapping_data
        mapped_player = self.player_service.find_mapped_player(uid, mapping_data)
        if mapped_player:
            # mapping_data format: [uid, ethnicity, image_filename]
            self.uid_info.value = mapped_player[0]
            ethnicity = mapped_player[1]
            image_name = mapped_player[2]
            self.img_path.text = f"{ethnicity}\\{image_name}"
        # 如果在 mapping_data 中未找到，则从当前组的 config.xml 中查找
        if ethnicity is None or image_name is None:
            self.logger.info(f"UID {uid} not found in mapping_data, checking XML file")
            xml_hit = self.player_service.find_xml_image(uid)
            if xml_hit:
                ethnicity, image_name = xml_hit
                self.img_path.text = f"{ethnicity}\\{image_name}"
            else:
                self.logger.warning(f"UID {uid} not found in config.xml file")
        # 如果找到了种族和图片名称，则加载图片
        if ethnicity is not None and image_name is not None:
            self.logger.info(f"Loading image for UID {uid}: {ethnicity}/{image_name}")
            image_file = self.player_service.resolve_image_file(ethnicity, image_name)
            if image_file:
                self.rep_img.image = toga.Image(image_file)
            else:
                self.logger.warning(f"Image file not found for UID {uid}")
                self.rep_img.image = toga.Image("resources/favicon-400×400.png")
        # 获取球员详细信息从最近一次解析的 rtf_data
        rtf_data = self.main_tab.replace_service.rtf_data
        player = self.player_service.find_rtf_player(uid, rtf_data)
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
            self.logger.warning(
                f"Player details not found in RTF data for UID: {uid}" if rtf_data
                else "No RTF data available for previewing player details")

    async def _replace_it(self, widget):
        uid = self.uid_info.value.strip()
        image_path = self.img_input.value.strip()
        self.logger.info(f"Replacing UID: {uid} with image: {image_path}")
        parsed = self.player_service.parse_image_path(image_path)  # (image_pack, image)
        if uid and image_path and parsed:
            image_pack, image = parsed
            try:
                self.player_service.replace_single_face(
                    uid, image_pack, image, self.main_tab.save_backup.value)
                # 同步内存中的映射缓存
                if self.player_service.update_mapping_cache(
                        uid, image_pack, image, self.main_tab.replace_service.mapping_data):
                    self.logger.info(f"Updated mapping data for UID: {uid}")
                await self.app.show_info(f"Successfully replaced UID: {uid} with {image_pack}/{image}")
            except Exception as e:
                await self.app.throw_error(f"Error replacing face for UID {uid}: {e}")
        else:
            self.logger.warning("UID or valid image path is empty")
            await self.app.throw_error("Please provide both UID and valid image path")
