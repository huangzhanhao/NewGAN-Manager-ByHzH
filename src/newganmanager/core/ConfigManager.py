import json


class ConfigManager:
    def __init__(self):
        pass

    def load_config(self, path):
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                return data
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {path}")

    def save_config(self, path, data):
        try:
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {path}")
        except PermissionError:
            raise PermissionError(f"Permission denied when writing to profile file: {path}")
        except TypeError:
            raise TypeError(f"Profile file is not JSON serializable: {path}")

    def get_latest_prf(self, path):
        """
        Get the latest active profile from configuration    从配置中获取最新的活动配置文件

        Args:
            path (str): Path to the configuration file  配置文件路径

        Returns:
            str or None: Name of the latest active profile, or None if no active profile found
            最新的活动配置文件名称，如果未找到活动配置文件则返回None
        """
        try:
            cfg = self.load_config(path)
            for k, v in cfg["Profile"].items():
                if v:
                    return k
            return None
        except Exception:
            return None
