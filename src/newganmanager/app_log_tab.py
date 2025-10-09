import logging
import os
import platform
import queue
import subprocess
import threading
import toga
from toga.style import Pack
from travertino.constants import COLUMN, ROW


class LogTab:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("NewGAN App")
        self.log_store = []  # Store log records for filtering 存储日志记录用于筛选
        self.max_log_store = 10000  # Max logs to keep in memory 内存中最大日志数量
        self.log_file_path = str(app.paths.app) + "/newgan.log"  # 日志文件路径

        # Setup top row with label, isOnly switch, log level selector, open file button, and clear button
        # 设置顶部行包含标签、isOnly开关、日志级别选择器、打开文件按钮和清除按钮
        log_label = toga.Label("Application Log:", style=Pack(margin=5, flex=1))

        # 创建单选框组件
        self.isOnly_switch = toga.Switch(
            text='only show this level:',
            value=False,
            on_change=self._on_switch_or_selector_change,
            style=Pack(margin=5)
        )
        # 添加日志级别选择器
        self.log_level_selector = toga.Selection(
            items=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            value="INFO",
            on_change=self._on_switch_or_selector_change,
            style=Pack(margin=5, width=120)
        )
        # self.log_level_selector.value = "INFO"  # 默认选择INFO级别，以触发_filter_logs方法
        self.open_logfile_button = toga.Button(
            text="Open Log File", on_press=self._open_log_file, style=Pack(margin=5)
        )
        self.clear_logarea_button = toga.Button(
            text="Clear Logs", on_press=self._clear_logs, style=Pack(margin=5)
        )
        top_row = toga.Box(
            children=[
                log_label,
                self.isOnly_switch,
                self.log_level_selector,
                self.open_logfile_button,
                self.clear_logarea_button
            ],
            style=Pack(direction=ROW, align_items="center"),
        )
        
        # 设置日志区域
        self.log_area = toga.MultilineTextInput(
            readonly=True, flex=1, style=Pack(margin=5)
        )
        self.log_tab_box = toga.Box(
            children=[top_row, self.log_area],
            style=Pack(direction=COLUMN, margin=5),
        )
        
        self.level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        # Start UI log processing thread
        # 启动UI日志处理线程
        self.ui_log_thread = threading.Thread(target=self._process_ui_logs, daemon=True)
        self.ui_log_thread.start()

    def _process_ui_logs(self):
        """该方法在单独的线程中运行，持续监听ThreadedLogging实例的UI日志队列，并将日志记录保存到log_store中
        """
        # 获取UI队列
        ui_queue = self.app.log_manager.get_ui_queue()
        while True:
            try:
                # 从UI队列获取日志记录
                record = ui_queue.get(timeout=0.5)  # 设置超时以允许线程定期检查
                # 将日志记录存储到log_store中，限制最大数量为10000
                if len(self.log_store) >= self.max_log_store:
                    self.log_store.pop(0)
                self.log_store.append(record)
                # 使用 GUI 线程安全的方式更新 UI
                if hasattr(self, 'log_area') and self.log_area:
                    self.app.loop.call_soon_threadsafe(
                        self._add_log_to_area, record
                    )
            except queue.Empty:
                # 队列为空时继续循环
                continue
            except Exception as e:
                print(f"Error in UI log processing thread: {e}")

    def _add_log_to_area(self, record):
        if not self._filter_log(record):  # 筛选日志记录
            return
        self.log_area.value += f"{self.app.log_manager.formatter.format(record)}\n"
        self.log_area.scroll_to_bottom()

    def _filter_log(self, record):
        """根据组件设置筛选日志记录"""
        if not hasattr(self, "log_area") or not self.log_area or record is None:
            return False
        selected_level = self.level_map.get(str(self.log_level_selector.value), logging.INFO)
        if self.isOnly_switch.value:
            # 只显示当前级别的日志
            return record.levelno == selected_level
        else:
            # 显示当前级别及以上的日志
            return record.levelno >= selected_level

    async def _on_switch_or_selector_change(self, widget):
        """根据组件设置筛选log_store中的日志"""
        if not hasattr(self, "log_area") or not self.log_area:
            return
        self.log_area.value = ""
        filtered_logs = []
        # 根据单选框状态应用筛选级别
        for record in self.log_store:
            if not self._filter_log(record):  # 筛选日志记录
                continue
            filtered_logs.append(self.app.log_manager.formatter.format(record))
        self.log_area.value = "\n".join(filtered_logs) + "\n"
        self.log_area.scroll_to_bottom()
    def _open_log_file(self, widget):
        """当打开日志文件按钮点击时回调"""
        try:
            if self.log_file_path and os.path.exists(self.log_file_path):
                system_name = platform.system()
                if system_name == "Windows":
                    # Windows: use notepad or default text editor
                    # Windows: 使用记事本或默认文本编辑器
                    os.startfile(self.log_file_path)
                elif system_name == "Darwin":  # macOS
                    # macOS: use open command
                    # macOS: 使用open命令
                    subprocess.run(["open", self.log_file_path])
                else:  # Linux and others
                    # Linux: use xdg-open
                    # Linux: 使用xdg-open
                    subprocess.run(["xdg-open", self.log_file_path])
            else:
                self.logger.warning("Log file not found or not accessible")
        except Exception as e:
            self.logger.error(f"Failed to open log file: {e}")

    def _clear_logs(self, widget):
        """当清除日志按钮点击时回调"""
        self.log_area.value = ""