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
from typing import cast


# 配置结构类型别名
GroupCfg = dict[str, str]                     # 组配置，如 {"rtf": "..."}
GroupsMap = dict[str, GroupCfg]               # 组字典：img_dir -> 组配置
PrfCfg = dict[str, str | None | GroupsMap]    # Profile 配置：cur_group / groups
GlobalCfg = dict[str, dict[str, bool]]        # cfg.json：{"Profile": {档名: 激活标记}}


class ProfileManager:
    def __init__(self, name: str | None, root_dir: str, data_dir: str | None = None) -> None:
        """
        Args:
            name (str): 当前 Profile 名称（None 时回退到 "No Profile"）
            root_dir (str): 应用资源目录（.config 下的只读配置随程序分发）
            data_dir (str): 用户数据目录（.user 运行时数据，来自 paths.data；
                            缺省时与 root_dir 相同，兼容旧布局/测试）
        """
        self.logger: logging.Logger = logging.getLogger("NewGAN App")
        self.root_dir: str = root_dir
        self.data_dir: str = data_dir if data_dir is not None else root_dir
        try:
            self.config: GlobalCfg = cast(GlobalCfg, self.load_config(self.user_path("cfg.json")))
        except FileNotFoundError:
            self.logger.warning("cfg.json missing, creating default config")
            self.config = {"Profile": {"No Profile": True}}
            self.save_config(self.user_path("cfg.json"), self.config)
        self.eth_cfg: dict[str, dict[str, str]] = cast(
            dict[str, dict[str, str]],
            self.load_config(os.path.join(root_dir, ".config", "eth_cfg.json")),
        )
        self.cur_prf: str = name or "No Profile"  # 当前 Profile 名
        self.prf_cfg: PrfCfg = self._load_profile_cfg(self.cur_prf)
        self.cur_group: str | None = self._pick_cur_group()  # 当前组 = 头像包目录

    # ------------------------------------------------------------------ #
    # JSON 读写（通用工具，供各业务复用）
    # ------------------------------------------------------------------ #
    @staticmethod
    def load_config(path: str) -> object:
        try:
            with open(path, "r", encoding="utf-8") as fp:
                return cast(object, json.load(fp))
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {path}")
        except json.JSONDecodeError:
            # 配置文件损坏（如进程崩溃导致写入中断）：备份损坏文件后按缺失处理，
            # 由调用方（如 __init__）回退默认配置，避免启动即抛错且无恢复手段
            corrupt_path = path + ".corrupt"
            try:
                _ = shutil.copyfile(path, corrupt_path)
            except OSError:
                pass
            raise FileNotFoundError(
                f"Config file corrupted, backed up to {corrupt_path}: {path}"
            )

    @staticmethod
    def save_config(path: str, data: object) -> None:
        # 原子写入：先写同目录临时文件再 os.replace 替换，
        # 进程中途崩溃或断电不会留下截断损坏的正式配置文件
        tmp_path = path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {path}")
        except PermissionError:
            raise PermissionError(f"Permission denied when saving config file: {path}")
        except TypeError:
            raise TypeError(f"Config data is not JSON serializable: {path}")

    @staticmethod
    def get_latest_prf(path: str) -> str | None:
        """从 cfg.json 中获取当前激活的 Profile 名称"""
        try:
            cfg = cast(GlobalCfg, ProfileManager.load_config(path))
            for k, v in cfg.get("Profile", {}).items():
                if v:
                    return k
            return None
        except Exception:
            return None

    def _load_profile_cfg(self, name: str) -> PrfCfg:
        """加载 Profile 配置；缺失时兜底创建空配置，旧版单档格式自动升级为多组格式"""
        path = self.user_path(name + ".json")
        try:
            cfg = cast(PrfCfg, self.load_config(path))
        except FileNotFoundError:
            # 当前 Profile 配置文件缺失（全新安装/数据目录不完整）：以空配置兜底并落盘
            self.logger.warning(f"Profile config missing, creating default: {name}")
            cfg: PrfCfg = {"cur_group": None, "groups": {}}
            self.save_config(path, cfg)
            return cfg
        if self._is_legacy_profile(cfg):
            cfg = self._upgrade_legacy_profile(name, cfg)
        return cfg

    @staticmethod
    def _is_legacy_profile(cfg: object) -> bool:
        """旧版单档结构：含 img_dir 字段且无 groups 字段"""
        return isinstance(cfg, dict) and "img_dir" in cfg and "groups" not in cfg

    def _upgrade_legacy_profile(self, name: str, cfg: PrfCfg) -> PrfCfg:
        """旧版单档数据 → 新版多组数据：
        旧: {"imgs": {...}, "ethnics": {...}, "img_dir": "X", "rtf": "Y"} + .user/<name>.xml 单档快照
        新: {"cur_group": "X", "groups": {"X": {"rtf": "Y"}}} + .user/<name>/<sanitized>.xml 组快照
        """
        self.logger.info(f"Upgrading legacy profile config: {name}")
        img_dir = self.norm_dir(str(cfg.get("img_dir") or ""))
        rtf = str(cfg.get("rtf") or "")
        # 独立 groups 变量：直接写入，避免对 new_cfg 中可能为 None 的值做下标访问
        new_groups: GroupsMap = {}
        new_cfg: PrfCfg = {"cur_group": img_dir or None, "groups": new_groups}
        if img_dir:
            new_groups[img_dir] = {"rtf": rtf}
        # 迁移旧单档快照 .user/<name>.xml → 新版组快照 .user/<name>/<sanitized_img_dir>.xml
        old_snap = self.user_path(name + ".xml")
        if img_dir and os.path.isfile(old_snap):
            new_snap = self.group_xml_path(name, img_dir)
            os.makedirs(os.path.dirname(new_snap), exist_ok=True)
            _ = shutil.move(old_snap, new_snap)
            self.logger.info(f"Migrated legacy profile snapshot: {old_snap} -> {new_snap}")
        self.save_config(self.user_path(name + ".json"), new_cfg)
        self.logger.info(f"Upgraded legacy profile: {name}")
        return new_cfg

    def user_path(self, filename: str) -> str:
        """返回用户数据目录（data_dir/.user）下指定文件的路径"""
        return os.path.join(self.data_dir, ".user", filename)

    # ------------------------------------------------------------------ #
    # 路径辅助
    # ------------------------------------------------------------------ #
    @staticmethod
    def norm_dir(img_dir: str) -> str:
        """规范化头像包目录路径（统一分隔符与尾部斜杠），保证同一目录只对应一个组"""
        if not img_dir:
            return img_dir
        return os.path.normpath(img_dir) + os.sep

    @staticmethod
    def _sanitize(text: str) -> str:
        """把字符串中的路径非法字符替换为下划线，用于拼文件名"""
        return re.sub(r'[\\/:*?"<>|]', "_", text).strip() or "default"

    def group_xml_path(self, profile: str, img_dir: str) -> str:
        """返回某 Profile 某组的映射备份文件路径：.user/<profile>/<sanitized_img_dir>.xml"""
        return self.user_path(
            os.path.join(self._sanitize(profile), self._sanitize(img_dir) + ".xml")
        )

    # ------------------------------------------------------------------ #
    # 组管理（组 = 头像包目录）
    # ------------------------------------------------------------------ #
    def _groups(self) -> GroupsMap:
        """返回当前 Profile 的组字典；缺失或非 dict 时初始化为空 dict 并写回，
        保证调用方始终拿到 dict（避免对可能为 None 的值做 keys/in/iter/下标/get 操作）"""
        groups = self.prf_cfg.get("groups")
        if not isinstance(groups, dict):
            groups = {}
            self.prf_cfg["groups"] = groups
        return groups

    def list_groups(self) -> list[str]:
        """返回当前 Profile 的所有组（头像包目录列表）"""
        return list(self._groups().keys())

    def _pick_cur_group(self) -> str | None:
        """根据 prf_cfg 中的 cur_group 记录恢复当前组，失效则回退到第一个组"""
        groups = self._groups()
        cur = self.prf_cfg.get("cur_group")
        if isinstance(cur, str) and cur in groups:
            return cur
        return next(iter(groups), None)

    def ensure_group(self, img_dir: str) -> str | None:
        """执行替换前调用：若 img_dir 是新头像包目录则自动建组，并设为当前组"""
        img_dir = self.norm_dir(img_dir)
        if not img_dir:
            return None
        groups = self._groups()
        if img_dir not in groups:
            groups[img_dir] = {"rtf": ""}
            self.logger.info(f"Auto-created group for new facepack dir: {img_dir}")
        _ = self.set_cur_group(img_dir)
        return img_dir

    def set_cur_group(self, img_dir: str) -> bool:
        """把当前组切换到指定头像包目录，并持久化"""
        img_dir = self.norm_dir(img_dir)
        if img_dir not in self._groups():
            return False
        self.cur_group = img_dir
        self.prf_cfg["cur_group"] = img_dir
        self.save_config(self.user_path(self.cur_prf + ".json"), self.prf_cfg)
        return True

    def delete_group(self, img_dir: str) -> bool:
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
    def get_group_rtf(self, img_dir: str) -> str:
        img_dir = self.norm_dir(img_dir)
        return self._groups().get(img_dir, {}).get("rtf", "")

    def get_cur_rtf(self) -> str:
        if not self.cur_group:
            return ""
        return self._groups()[self.cur_group].get("rtf", "")

    def set_cur_rtf(self, rtf: str) -> bool:
        if not self.cur_group:
            return False
        self._groups()[self.cur_group]["rtf"] = rtf
        self.save_config(self.user_path(self.cur_prf + ".json"), self.prf_cfg)
        return True

    # ------------------------------------------------------------------ #
    # Profile 管理
    # ------------------------------------------------------------------ #
    def create_profile(self, name: str) -> None:
        """创建新 Profile：注册到 cfg.json、生成空配置，并切换过去"""
        self.config["Profile"][name] = True
        self.save_config(self.user_path("cfg.json"), self.config)
        self.save_config(self.user_path(name + ".json"), {"cur_group": None, "groups": {}})
        self.load_profile(name)
        self.logger.info(f"Create new profile: {name}")

    def delete_profile(self, name: str) -> bool:
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

    def load_profile(self, name: str) -> None:
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

    def _save_group_xml(self, profile: str, img_dir: str) -> None:
        """把 img_dir/config.xml 保存到 profile 对应组的备份文件"""
        src = os.path.join(img_dir, "config.xml")
        dst = self.group_xml_path(profile, img_dir)
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            _ = shutil.copyfile(src, dst)
            self.logger.debug(f"Saved group xml: {src} -> {dst}")

    def _restore_group_xml(self, profile: str, img_dir: str) -> None:
        """把 profile 对应组的备份文件写回 img_dir/config.xml"""
        src = self.group_xml_path(profile, img_dir)
        dst = os.path.join(img_dir, "config.xml")
        if os.path.isfile(src):
            if os.path.isdir(img_dir):
                _ = shutil.copyfile(src, dst)
                self.logger.debug(f"Restored group xml: {src} -> {dst}")
            else:
                # 头像包目录已不存在（如换了盘/目录被删）：保留快照，跳过恢复
                self.logger.warning(f"Skip restoring group xml, image dir missing: {img_dir}")

    # ------------------------------------------------------------------ #
    # 民族配置
    # ------------------------------------------------------------------ #
    def get_ethnic(self, nation: str) -> str | None:
        return self.eth_cfg["Ethnics"].get(nation, None)
