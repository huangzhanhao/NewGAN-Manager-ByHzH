import json


class ConfigManager:
    def __init__(self):
        pass

    def load_config(self, path):
        """
        Load configuration from a JSON file             从JSON文件加载配置

        Args:
            path (str): Path to the configuration file  配置文件路径

        Returns:
            dict: Configuration data                    配置数据

        Raises:
            FileNotFoundError: If the configuration file doesn't exist      如果配置文件不存在
        """
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                return data
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {path}")

    def save_config(self, path, data):
        """
        Save configuration data to a JSON file          将配置数据保存到JSON文件

        Args:
            path (str): Path to the configuration file  配置文件路径
            data (dict): Configuration data to save     要保存的配置数据

        Raises:
            FileNotFoundError: If the configuration file doesn't exist    如果配置文件不存在
            PermissionError: If there's no permission to write to the file          如果没有写入文件的权限
            TypeError: If the data is not JSON serializable                         如果数据不是JSON可序列化的
        """
        try:
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
        except FileNotFoundError:
            raise FileNotFoundError("Configuration file not found")
        except PermissionError:
            raise PermissionError("Permission denied when writing to file")
        except TypeError:
            raise TypeError("Data is not JSON serializable")

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
            return None  # No active profile found
        except (KeyError, TypeError):
            # Handle case where "Profile" key doesn't exist in config or cfg is not a dict
            return None
        except Exception:
            # Handle any other unexpected errors
            return None
