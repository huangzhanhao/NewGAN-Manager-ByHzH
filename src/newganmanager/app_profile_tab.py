"""Profile 标签页：展示当前档的所有组（头像包目录），支持切换当前组、删除组

组以头像包目录为标识，在 Main 标签页选择新目录执行替换时自动创建。
组管理业务委托给 ProfileService，本类只负责 UI 展示与事件回调。
"""
import logging

import toga
from toga.style import Pack
from travertino.constants import COLUMN, ROW


class ProfileTab:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("NewGAN App")
        self.profile_tab_box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        self.profile_label = toga.Label("", style=Pack(margin=5, flex=1))
        title_row = toga.Box(
            children=[toga.Label("Profile: ", style=Pack(margin=5)), self.profile_label],
            style=Pack(direction=ROW, align_items="center"),
        )
        self.profile_tab_box.add(title_row)

        self.profile_tab_box.add(
            toga.Label("Facepack Groups:", style=Pack(margin=(10, 5, 5, 5)))
        )
        self.groups_box = toga.Box(style=Pack(direction=COLUMN, margin=5))
        self.profile_tab_box.add(self.groups_box)

        self.refresh()

    def refresh(self):
        """根据当前 Profile 重建组列表；在 Profile 增删/切换后调用"""
        pm = self.app.profile_manager
        self.profile_label.text = pm.cur_prf if pm else "-"
        self.groups_box.clear()
        if not pm:
            return
        groups = pm.list_groups()
        if not groups:
            self.groups_box.add(
                toga.Label(
                    "No facepack group in this profile. "
                    "Pick an image directory in the Main tab to create one.",
                    style=Pack(margin=5),
                )
            )
            return
        for img_dir in groups:
            self.groups_box.add(self._build_group_row(pm, img_dir))

    def _build_group_row(self, pm, img_dir):
        rtf = pm.get_group_rtf(img_dir)
        dir_input = toga.TextInput(readonly=True, value=img_dir, style=Pack(margin=5, flex=1))
        rtf_input = toga.TextInput(readonly=True, value=rtf, style=Pack(margin=5, flex=1))
        is_cur = pm.cur_group == img_dir
        select_btn = toga.Button(
            text="Current" if is_cur else "Select",
            on_press=(lambda w, d=img_dir: self._select_group(d)) if not is_cur else None,
            style=Pack(margin=5),
        )
        delete_btn = toga.Button(
            text="Delete",
            on_press=lambda w, d=img_dir: self._delete_group(d),
            style=Pack(margin=5),
        )
        return toga.Box(
            children=[dir_input, rtf_input, select_btn, delete_btn],
            style=Pack(direction=ROW, align_items="center"),
        )

    def _select_group(self, img_dir):
        if self.app.profile_service.set_current_group(img_dir):
            self.logger.info(f"Switch current group: {img_dir}")
            self.refresh()
            self.app.main_tab.refresh()

    def _delete_group(self, img_dir):
        if self.app.profile_service.delete_group(img_dir):
            self.logger.info(f"Delete group: {img_dir}")
            self.refresh()
            self.app.main_tab.refresh()
