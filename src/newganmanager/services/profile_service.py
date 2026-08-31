"""Profile 与组管理的业务编排层（不依赖任何 UI 框架）

统一封装 Profile（存档）的创建/删除/切换，以及组（头像包目录）的
切换/删除/路径设置。UI 层只负责收集参数与刷新展示，业务规则全部收敛于此。
"""
import logging

from ..core.ProfileManager import ProfileManager


class ProfileService:
    """Profile / 组管理的业务服务"""

    def __init__(self, profile_manager: ProfileManager, logger: logging.Logger | None = None):
        self.pm = profile_manager
        self.logger = logger or logging.getLogger("NewGAN App")

    # ------------------------------------------------------------------ #
    # Profile 管理
    # ------------------------------------------------------------------ #
    def create_profile(self, name) -> bool:
        """创建新档并切换过去；名为空时返回 False"""
        if not name or not name.strip():
            self.logger.warning("Create profile failed: empty name")
            return False
        self.pm.create_profile(name)
        return True

    def delete_profile(self, name) -> bool:
        """删除档；'No Profile' 不可删，返回 False"""
        return self.pm.delete_profile(name)

    def switch_profile(self, name) -> bool:
        """切换到指定档，并持久化激活标记到 cfg.json"""
        if not name:
            return False
        self.pm.load_profile(name)
        self.pm.save_config(self.pm.user_path("cfg.json"), self.pm.config)
        self.logger.info(f"Switched profile: {name}")
        return True

    # ------------------------------------------------------------------ #
    # 组（头像包目录）管理
    # ------------------------------------------------------------------ #
    def select_image_directory(self, img_dir) -> bool:
        """选择头像包目录：新目录自动建组并设为当前组"""
        return self.pm.ensure_group(img_dir) is not None

    def set_current_rtf(self, rtf) -> bool:
        """把 RTF 名单写入当前组"""
        return self.pm.set_cur_rtf(rtf)

    def set_current_group(self, img_dir) -> bool:
        """切换当前组"""
        return self.pm.set_cur_group(img_dir)

    def delete_group(self, img_dir) -> bool:
        """删除组（连同其映射备份）"""
        return self.pm.delete_group(img_dir)
