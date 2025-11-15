import logging
import os
import platform
import subprocess
import asyncio
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
        # Start UI log processing with asyncio
        # 使用 asyncio 启动UI日志处理
        self.ui_log_queue = asyncio.Queue()
        self._ui_update_task = None
        self._start_ui_log_processing()

    def _start_ui_log_processing(self):
        """启动UI日志处理任务"""
        if self._ui_update_task is None:
            self._ui_update_task = asyncio.create_task(self._process_ui_logs_task())

    async def _process_ui_logs_task(self):
        """异步处理日志队列的任务 - 批量处理模式"""
        ui_queue = self.app.log_manager.get_ui_queue()
        batch_interval = 0.05  # 50ms 批处理间隔
        while True:
            try:
                # 收集一批日志记录
                batch_records = []
                start_time = asyncio.get_event_loop().time()
                # 在批处理时间窗口内尽可能多地收集日志
                while (asyncio.get_event_loop().time() - start_time) < batch_interval:
                    try:
                        # 非阻塞地尝试获取日志记录
                        record = await asyncio.wait_for(ui_queue.get(), timeout=0.001)
                        batch_records.append(record)
                        # 限制单次批处理的最大数量，防止内存溢出
                        if len(batch_records) >= 100:
                            break
                    except asyncio.TimeoutError:
                        # 队列为空，稍作等待
                        await asyncio.sleep(0.001)
                        break
                # 处理收集到的日志记录
                if batch_records:
                    # 更新log_store
                    for record in batch_records:
                        if len(self.log_store) >= self.max_log_store:
                            self.log_store.pop(0)
                        self.log_store.append(record)
                    # 批量更新UI
                    if hasattr(self, 'log_area') and self.log_area:
                        await self._add_logs_batch_to_area(batch_records)
            except Exception as e:
                self.logger.error(f"Error in log processing task: {e}")
                await asyncio.sleep(0.1)

    async def _add_logs_batch_to_area(self, records):
        """批量添加日志到显示区域"""
        if not hasattr(self, 'log_area') or not self.log_area:
            return
        # 检查是否需要显示这些日志
        filtered_formatted_logs = []
        for record in records:
            if self._filter_log(record):
                formatted_log = self.app.log_manager.formatter.format(record)
                filtered_formatted_logs.append(formatted_log)
        if not filtered_formatted_logs:
            return
        # 批量更新文本内容
        current_text = self.log_area.value
        new_logs_text = "\n".join(filtered_formatted_logs)
        if current_text:
            updated_text = current_text + "\n" + new_logs_text
        else:
            updated_text = new_logs_text
        # 限制显示的日志行数以提高性能
        max_display_lines = 8000  # 最多显示8000行
        lines = updated_text.split('\n')
        if len(lines) > max_display_lines:
            lines = lines[-max_display_lines:]
            updated_text = '\n'.join(lines)
        self.log_area.value = updated_text
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
