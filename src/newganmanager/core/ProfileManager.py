"""Profile 管理：一个 Profile = 一个游戏存档的一套独立配置，内部包含多个"组"。

组（group）以头像包目录（img_dir）为唯一标识，每组包含：
- img_dir : 头像包目录（组的 key）
- rtf     : 该头像包对应的 FM 导出名单文件
- 映射备份 : .user/<profile>/<sanitized_img_dir>.xml，保存该目录 config.xml 的内容

游戏只认头像包目录下的 config.xml。切换 Profile 时，通过 swap_xml
把旧档各组的 config.xml 保存回各自的备份文件，再把新档各组的备份恢复进目录。
"""
import json
import logging
import os
import re
import shutil


class ProfileManager:
    def __init__(self, name, root_dir, data_dir=None):
        """
        Args:
            name (str): 当前 Profile 名称（None 时回退到 "No Profile"）
            root_dir (str): 应用资源目录（.config 下的只读配置随程序分发）
            data_dir (str): 用户数据目录（.user 运行时数据，来自 paths.data；
                            缺省时与 root_dir 相同，兼容旧布局/测试）
        """
        self.logger = logging.getLogger("NewGAN App")
        self.root_dir = root_dir
        self.data_dir = data_dir if data_dir is not None else root_dir
        try:
            self.config = self.load_config(self.user_path("cfg.json"))  # 用户全局配置（档列表 + 激活标记）
        except FileNotFoundError:
            self.logger.warning("cfg.json missing, creating default config")
            self.config = {"Profile": {"No Profile": True}}
            self.save_config(self.user_path("cfg.json"), self.config)
        self.eth_cfg = self.load_config(os.path.join(root_dir, ".config", "eth_cfg.json"))  # 民族配置（只读）
        self.cur_prf = name or "No Profile"  # 当前 Profile 名
        self.prf_cfg = self._load_profile_cfg(self.cur_prf)
        self.cur_group = self._pick_cur_group()  # 当前组 = 头像包目录

    # ------------------------------------------------------------------ #
    # JSON 读写（通用工具，供各业务复用）
    # ------------------------------------------------------------------ #
    @staticmethod
    def load_config(path):
        try:
            with open(path, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {path}")

    @staticmethod
    def save_config(path, data):
        try:
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {path}")
        except PermissionError:
            raise PermissionError(f"Permission denied when saving config file: {path}")
        except TypeError:
            raise TypeError(f"Config data is not JSON serializable: {path}")

    @staticmethod
    def get_latest_prf(path):
        """从 cfg.json 中获取当前激活的 Profile 名称"""
        try:
            cfg = ProfileManager.load_config(path)
            for k, v in cfg.get("Profile", {}).items():
                if v:
                    return k
            return None
        except Exception:
            return None

    def _load_profile_cfg(self, name):
        """加载 Profile 配置；缺失时兜底创建空配置，旧版单档格式自动升级为多组格式"""
        path = self.user_path(name + ".json")
        try:
            cfg = self.load_config(path)
        except FileNotFoundError:
            # 当前 Profile 配置文件缺失（全新安装/数据目录不完整）：以空配置兜底并落盘
            self.logger.warning(f"Profile config missing, creating default: {name}")
            cfg = {"cur_group": None, "groups": {}}
            self.save_config(path, cfg)
            return cfg
        if self._is_legacy_profile(cfg):
            cfg = self._upgrade_legacy_profile(name, cfg)
        return cfg

    @staticmethod
    def _is_legacy_profile(cfg):
        """旧版单档结构：含 img_dir 字段且无 groups 字段"""
        return isinstance(cfg, dict) and "img_dir" in cfg and "groups" not in cfg

    def _upgrade_legacy_profile(self, name, cfg):
        """旧版单档数据 → 新版多组数据：
        旧: {"imgs": {...}, "ethnics": {...}, "img_dir": "X", "rtf": "Y"} + .user/<name>.xml 单档快照
        新: {"cur_group": "X", "groups": {"X": {"rtf": "Y"}}} + .user/<name>/<sanitized>.xml 组快照
        """
        self.logger.info(f"Upgrading legacy profile config: {name}")
        img_dir = self.norm_dir(cfg.get("img_dir") or "")
        rtf = cfg.get("rtf") or ""
        new_cfg = {"cur_group": img_dir or None, "groups": {}}
        if img_dir:
            new_cfg["groups"][img_dir] = {"rtf": rtf}
        # 迁移旧单档快照 .user/<name>.xml → 新版组快照 .user/<name>/<sanitized_img_dir>.xml
        old_snap = self.user_path(name + ".xml")
        if img_dir and os.path.isfile(old_snap):
            new_snap = self.group_xml_path(name, img_dir)
            os.makedirs(os.path.dirname(new_snap), exist_ok=True)
            shutil.move(old_snap, new_snap)
            self.logger.info(f"Migrated legacy profile snapshot: {old_snap} -> {new_snap}")
        self.save_config(self.user_path(name + ".json"), new_cfg)
        self.logger.info(f"Upgraded legacy profile: {name}")
        return new_cfg

    def user_path(self, filename):
        """返回用户数据目录（data_dir/.user）下指定文件的路径"""
        return os.path.join(self.data_dir, ".user", filename)

    # ------------------------------------------------------------------ #
    # 路径辅助
    # ------------------------------------------------------------------ #
    @staticmethod
    def norm_dir(img_dir):
        """规范化头像包目录路径（统一分隔符与尾部斜杠），保证同一目录只对应一个组"""
        if not img_dir:
            return img_dir
        return os.path.normpath(img_dir) + os.sep

    @staticmethod
    def _sanitize(text):
        """把字符串中的路径非法字符替换为下划线，用于拼文件名"""
        return re.sub(r'[\\/:*?"<>|]', "_", text).strip() or "default"

    def group_xml_path(self, profile, img_dir):
        """返回某 Profile 某组的映射备份文件路径：.user/<profile>/<sanitized_img_dir>.xml"""
        return self.user_path(
            os.path.join(self._sanitize(profile), self._sanitize(img_dir) + ".xml")
        )

    # ------------------------------------------------------------------ #
    # 组管理（组 = 头像包目录）
    # ------------------------------------------------------------------ #
    def _groups(self):
        return self.prf_cfg.setdefault("groups", {})

    def list_groups(self):
        """返回当前 Profile 的所有组（头像包目录列表）"""
        return list(self._groups().keys())

    def _pick_cur_group(self):
        """根据 prf_cfg 中的 cur_group 记录恢复当前组，失效则回退到第一个组"""
        groups = self._groups()
        cur = self.prf_cfg.get("cur_group")
        if cur in groups:
            return cur
        return next(iter(groups), None)

    def ensure_group(self, img_dir):
        """执行替换前调用：若 img_dir 是新头像包目录则自动建组，并设为当前组"""
        img_dir = self.norm_dir(img_dir)
        if not img_dir:
            return None
        groups = self._groups()
        if img_dir not in groups:
            groups[img_dir] = {"rtf": ""}
            self.logger.info(f"Auto-created group for new facepack dir: {img_dir}")
        self.set_cur_group(img_dir)
        return img_dir

    def set_cur_group(self, img_dir):
        """把当前组切换到指定头像包目录，并持久化"""
        img_dir = self.norm_dir(img_dir)
        if img_dir not in self._groups():
            return False
        self.cur_group = img_dir
        self.prf_cfg["cur_group"] = img_dir
        self.save_config(self.user_path(self.cur_prf + ".json"), self.prf_cfg)
        return True

    def delete_group(self, img_dir):
        """删除组及其映射备份；若删除的是当前组，则切换到剩余组的第一个"""
        img_dir = self.norm_dir(img_dir)
        groups = self._groups()
        if img_dir not in groups:
            return False
        del groups[img_dir]
        xml_path = self.group_xml_path(self.cur_prf, img_dir)
        if os.path.isfile(xml_path):
            os.remove(xml_path)
        if self.cur_group == img_dir:
            self.cur_group = next(iter(groups), None)
            self.prf_cfg["cur_group"] = self.cur_group
        self.save_config(self.user_path(self.cur_prf + ".json"), self.prf_cfg)
        self.logger.info(f"Deleted group: {img_dir}")
        return True

    # 组的 rtf 读写
    def get_group_rtf(self, img_dir):
        img_dir = self.norm_dir(img_dir)
        return self._groups().get(img_dir, {}).get("rtf", "")

    def get_cur_rtf(self):
        if not self.cur_group:
            return ""
        return self._groups()[self.cur_group].get("rtf", "")

    def set_cur_rtf(self, rtf):
        if not self.cur_group:
            return False
        self._groups()[self.cur_group]["rtf"] = rtf
        self.save_config(self.user_path(self.cur_prf + ".json"), self.prf_cfg)
        return True

    # ------------------------------------------------------------------ #
    # Profile 管理
    # ------------------------------------------------------------------ #
    def create_profile(self, name):
        """创建新 Profile：注册到 cfg.json、生成空配置，并切换过去"""
        self.config["Profile"][name] = True
        self.save_config(self.user_path("cfg.json"), self.config)
        self.save_config(self.user_path(name + ".json"), {"cur_group": None, "groups": {}})
        self.load_profile(name)
        self.logger.info(f"Create new profile: {name}")

    def delete_profile(self, name):
        """删除 Profile：移除注册、删除配置文件与映射备份目录，并切回 No Profile"""
        if name == "No Profile":
            self.logger.warning("Can't delete no profile")
            return False
        del self.config["Profile"][name]
        try:
            os.remove(self.user_path(name + ".json"))
            xml_dir = self.user_path(self._sanitize(name))
            if os.path.isdir(xml_dir):
                shutil.rmtree(xml_dir)
        except OSError as e:
            self.logger.error(f"Error deleting profile files: {e}")
        self.save_config(self.user_path("cfg.json"), self.config)
        self.load_profile("No Profile")
        self.logger.info(f"Delete profile: {name}")
        return True

    def load_profile(self, name):
        """切换 Profile：先保存旧档所有组的 config.xml，再恢复新档所有组的映射"""
        old_name = self.cur_prf
        # 1. 保存旧档每个组的 config.xml 到其备份文件
        for img_dir in self.list_groups():
            self._save_group_xml(old_name, img_dir)
        # 2. 加载新档配置（旧版单档格式在此自动升级）
        self.prf_cfg = self._load_profile_cfg(name)
        # 3. 恢复新档每个组的备份到对应头像包目录
        for img_dir in self.list_groups():
            self._restore_group_xml(name, img_dir)
        # 4. 更新激活标记与当前状态
        for key in self.config["Profile"].keys():
            self.config["Profile"][key] = (key == name)
        self.cur_prf = name
        self.cur_group = self._pick_cur_group()

    def _save_group_xml(self, profile, img_dir):
        """把 img_dir/config.xml 保存到 profile 对应组的备份文件"""
        src = os.path.join(img_dir, "config.xml")
        dst = self.group_xml_path(profile, img_dir)
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            self.logger.debug(f"Saved group xml: {src} -> {dst}")

    def _restore_group_xml(self, profile, img_dir):
        """把 profile 对应组的备份文件写回 img_dir/config.xml"""
        src = self.group_xml_path(profile, img_dir)
        dst = os.path.join(img_dir, "config.xml")
        if os.path.isfile(src):
            if os.path.isdir(img_dir):
                shutil.copyfile(src, dst)
                self.logger.debug(f"Restored group xml: {src} -> {dst}")
            else:
                # 头像包目录已不存在（如换了盘/目录被删）：保留快照，跳过恢复
                self.logger.warning(f"Skip restoring group xml, image dir missing: {img_dir}")

    # ------------------------------------------------------------------ #
    # 民族配置
    # ------------------------------------------------------------------ #
    def get_ethnic(self, nation):
        return self.eth_cfg["Ethnics"].get(nation, None)
