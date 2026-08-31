"""球员预览与单人换脸的业务逻辑（不依赖任何 UI 框架）

负责查询 UID 对应的头像映射、球员资料，以及在 config.xml 中执行单条替换。
UI 层（PlayerViewer）只负责把查询结果展示到控件、把用户输入交给本服务。
"""
import logging
import os
import re

from ..core.XmlParser import XmlParser

_IMAGE_EXTS = (".png", ".jpg", ".jpeg")


class PlayerService:
    """球员预览 / 单人换脸的业务服务"""

    def __init__(self, profile_manager, logger: logging.Logger | None = None):
        self.pm = profile_manager
        self.logger = logger or logging.getLogger("NewGAN App")

    # ------------------------------------------------------------------ #
    # 预览查询
    # ------------------------------------------------------------------ #
    def find_mapped_player(self, uid, mapping_data):
        """在最近一次批量替换的映射结果中按 UID 查找球员

        Returns:
            list | None: mapping 记录 [uid, ethnicity, image_filename] 或 None
        """
        if not mapping_data:
            return None
        return next(
            (p for p in mapping_data
             if p and len(p) > 0 and (p[0] == uid or p[0] == "r-" + uid)),
            None,
        )

    def find_xml_image(self, uid):
        """从当前组的 config.xml 查询 UID 对应的头像

        Returns:
            tuple[str, str] | None: (种族, 图片名) 或 None
        """
        if not self.pm.cur_group:
            return None
        img_path = XmlParser().get_imgpath_from_uid(
            os.path.join(self.pm.cur_group, "config.xml"), uid
        )
        if not img_path:
            return None
        parts = img_path.split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
        return None

    def find_rtf_player(self, uid, rtf_data):
        """在最近一次解析的 RTF 名单中按 UID 查找球员资料

        Returns:
            list | None: 球员记录 [UID, 主要国籍, ...] 或 None
        """
        if not rtf_data:
            return None
        return next(
            (p for p in rtf_data
             if p and len(p) > 0 and (p[0] == uid or p[0] == "r-" + uid)),
            None,
        )

    def resolve_image_file(self, ethnicity, image_name):
        """在当前组的种族子目录中查找实际图片文件

        Returns:
            str | None: 完整图片路径（含扩展名）或 None
        """
        if not self.pm.cur_group:
            return None
        img_base = os.path.join(self.pm.cur_group, ethnicity, image_name)
        for ext in _IMAGE_EXTS:
            if os.path.isfile(img_base + ext):
                return img_base + ext
        return None

    # ------------------------------------------------------------------ #
    # 单人换脸
    # ------------------------------------------------------------------ #
    def parse_image_path(self, image_path):
        """从图片完整路径反推 (头像包子目录, 图片名)；格式不合法返回 None"""
        match = re.search(
            r"[\\/]+([^\\/]+)[\\/]+([^\\/]+)\.(?:png|jpg|jpeg)$", image_path
        )
        if not match:
            return None
        return match.group(1), match.group(2)

    def replace_single_face(self, uid, image_pack, image, save_backup) -> None:
        """对当前组的 config.xml 做单条替换（只改匹配 UID 的那一行）

        Raises:
            ValueError: 当前没有选中组
        """
        if not self.pm.cur_group:
            raise ValueError("No current group selected")
        player = [uid, image_pack, image]
        XmlParser().single_replacement_in_xml(
            player, self.pm.cur_group, self.pm.logger, save_backup
        )

    def update_mapping_cache(self, uid, image_pack, image, mapping_data) -> bool:
        """单人换脸后同步内存中的映射缓存；命中返回 True"""
        if not mapping_data:
            return False
        for p in mapping_data:
            if p and len(p) > 0 and p[0] == uid:
                p[1] = image_pack
                p[2] = image
                return True
        return False
