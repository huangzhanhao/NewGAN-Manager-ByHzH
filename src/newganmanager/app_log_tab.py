import logging
import toga
from toga.style import Pack
from travertino.constants import COLUMN, ROW
import threading
import os
import subprocess
import platform


import queue

class QueueHandler(logging.Handler):
    """自定义Handler将日志记录放入队列"""
    def __init__(self, queue):
        super().__init__()
        self.queue = queue
        
    def emit(self, record):
        """将日志记录放入队列"""
        try:
            self.queue.put(record)
        except Exception:
            self.handleError(record)

class LogTab:
    """
    Log tab UI components and functionality
    日志标签页UI组件和功能
    """

    def __init__(self, app):
        """
        Initialize log tab UI and logging system with enhanced features
        初始化日志标签页UI和日志系统，包含增强功能

        Args:
            app: Application instance 应用实例
        """
        self.app = app  # Application instance 应用实例
        
        # Log storage and queue
        # 日志存储和队列
        self.log_store = []  # Store log records for filtering 存储日志记录用于筛选
        self.max_log_store = 10000  # Max logs to keep in memory 内存中最大日志数量
        self.log_queue = queue.Queue(maxsize=5000)  # Thread-safe log queue 线程安全日志队列
        self.current_log_level = logging.INFO  # Default log level 默认日志级别
        self.show_only_current_level = False  # 单选框状态：是否只显示当前级别
        
        # Start log processing thread
        # 启动日志处理线程
        self.log_thread = threading.Thread(target=self._process_logs, daemon=True)
        self.log_thread.start()

        # Store log file path for easy access
        # 存储日志文件路径以便访问
        self.log_file_path = str(self.app.paths.app) + "/newgan.log"

        # Initialize logger for the application
        # 为应用程序初始化logger
        self.app.logger = logging.getLogger("NewGAN App")

        # Enhanced logging setup with improved formatter
        # 使用改进的格式化器进行增强的日志设置
        self.formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(module)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Set default log level to INFO
        # 设置默认日志级别为INFO
        self.app.logger.setLevel(logging.DEBUG)

        # 创建文件处理器用于在日志处理线程中写入日志文件
        try:
            self.file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
            self.file_handler.setFormatter(self.formatter)
        except Exception as e:
            print(f"Warning: Could not create file handler: {e}")
            self.file_handler = None

        # Log application startup information
        # 记录应用启动信息
        self.app.logger.info(
            "Starting Application\n-----------------------------------------"
        )
        self.app.logger.info(str(self.app.paths.app))

        # Setup top row with label, log level selector, open file button, and clear button
        # 顶部行包含标签、日志级别选择器、打开文件按钮和清除按钮
        self.log_label = toga.Label("Application Log:", style=Pack(margin=5, flex=1))

        self.open_logfile_button = toga.Button(
            text="Open Log File", on_press=self._open_log_file, style=Pack(margin=5)
        )

        self.clear_logarea_button = toga.Button(
            text="Clear Logs", on_press=self._clear_logs, style=Pack(margin=5)
        )
        
        # 创建单选框组件
        self.level_switch = toga.Switch(
            text='only show logLevel:',
            value=False,
            on_change=self._on_show_level_changed,
            style=Pack(margin=5)
        )

        # Add log level selector
        # 添加日志级别选择器
        self.log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.level_selector = toga.Selection(
            items=self.log_levels,
            value="INFO",
            on_change=self._on_log_level_changed,
            style=Pack(margin=5, width=120)
        )
        
        # Update top row
        # 更新顶部行
        self.top_row = toga.Box(
            children=[
                self.log_label,
                self.level_switch,
                self.level_selector,
                self.open_logfile_button,
                self.clear_logarea_button
            ],
            style=Pack(direction=ROW, align_items="center"),
        )

        # Setup log area
        # 设置日志区域
        self.log_area = toga.MultilineTextInput(
            readonly=True, flex=1, style=Pack(margin=5)
        )

        # Setup container box
        # 设置容器框
        self.log_tab_box = toga.Box(
            children=[self.top_row, self.log_area],
            style=Pack(direction=COLUMN, margin=5),
        )

        # 添加自定义QueueHandler
        queue_handler = QueueHandler(self.log_queue)
        queue_handler.setLevel(logging.DEBUG)
        self.app.logger.addHandler(queue_handler)

    def _process_logs(self):
        """日志处理线程主函数"""
        while True:
            try:
                # 从队列获取日志记录
                record = self.log_queue.get(timeout=0.5)
                
                # 存储日志记录
                self._store_log(record)
                
                # 更新UI
                self._update_ui([record])
                
                # 写入日志文件
                if self.file_handler:
                    try:
                        self.file_handler.emit(record)
                    except Exception as e:
                        print(f"Error writing to log file: {e}")
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in log processing thread: {e}")
                

    def _store_log(self, record):
        """存储日志记录"""
        if len(self.log_store) >= self.max_log_store:
            self.log_store.pop(0)
        self.log_store.append(record)
        
    def _update_ui(self, records):
        """更新UI显示"""
        if not hasattr(self, "log_area") or not self.log_area:
            return
            
        # 根据单选框状态应用筛选级别
        if self.show_only_current_level:
            # 只显示当前级别的日志
            filtered_records = [
                record for record in records
                if record.levelno == self.current_log_level
            ]
        else:
            # 显示当前级别及以上的日志
            filtered_records = [
                record for record in records
                if record.levelno >= self.current_log_level
            ]
        
        if not filtered_records:
            return
            
            # 记录日志筛选模式变化
            level_mode = "EXACT" if self.show_only_current_level else "LEVEL_AND_ABOVE"
            self.app.logger.info(f"Log filter changed: level={selected}, mode={level_mode}")
        log_text = "\n".join(self.formatter.format(record) for record in filtered_records)
        
        # 安全更新UI
        def update():
            self.log_area.value += log_text + "\n"
            self.log_area.scroll_to_bottom()
            
        if hasattr(self.app, "loop") and self.app.loop:
            self.app.loop.call_soon_threadsafe(update)
            
    def _on_log_level_changed(self, widget):
        """当日志级别改变时回调"""
        selected = self.level_selector.value
        if selected and isinstance(selected, str):
            self.current_log_level = getattr(logging, selected)
            self.log_area.value = ""  # Clear current display
            # 刷新所有日志显示
            self._update_ui(self.log_store)
        
    def _on_show_level_changed(self, widget):
        """当单选框状态改变时回调"""
        self.show_only_current_level = widget.value
        # 刷新所有日志显示
        self.log_area.value = ""
        self._update_ui(self.log_store)
        
    def _open_log_file(self, widget):
        """
        Open the log file
        打开日志文件

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
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
                self.app.logger.warning("Log file not found or not accessible")
        except Exception as e:
            # Log the error but don't disrupt the application
            # 记录错误但不干扰应用程序
            self.app.logger.error(f"Failed to open log file: {e}")

    def _clear_logs(self, widget):
        """
        Clear only the GUI log area
        清除GUI日志区域

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
        self.log_area.value = ""
