import logging
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import threading
import time
import os
import subprocess
import platform


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
        
        # Initialize buffer for performance optimization
        # 初始化缓冲区用于性能优化
        self.log_buffer = []
        self.buffer_lock = threading.Lock()
        
        # Store log file path for easy access
        # 存储日志文件路径以便访问
        self.log_file_path = str(self.app.paths.app) + '/newgan.log'
        
        # Initialize logger for the application
        # 为应用程序初始化logger
        self.app.logger = logging.getLogger("NewGAN App")
        
        # Enhanced logging setup with improved formatter
        # 使用改进的格式化器进行增强的日志设置
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(module)s:%(lineno)d - %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Set default log level to INFO
        # 设置默认日志级别为INFO
        self.app.logger.setLevel(logging.INFO)

        # Create FileHandler to update the log area in newgan.log
        # 创建文件处理器以更新newgan.log中的日志
        try:
            # self.log_file_path = str(self.app.paths.app) + '/newgan.log'
            fh = logging.FileHandler(self.log_file_path)
            fh.setFormatter(formatter)
            self.app.logger.addHandler(fh)
        except Exception as e:
            print(f"Warning: Could not create file handler: {e}")

        # Create StreamHandler to update the log area in the GUI
        # 创建流处理器以更新GUI中的日志
        try:
            gui_handler = logging.StreamHandler(self)
            gui_handler.setFormatter(formatter)
            self.app.logger.addHandler(gui_handler)
        except Exception as e:
            print(f"Warning: Could not create GUI handler: {e}")
        
        # Log application startup information
        # 记录应用启动信息
        self.app.logger.info("Starting Application\n-----------------------------------------")
        self.app.logger.info(str(self.app.paths.app))

        # Setup top row with label, open file button, and clear button
        # 顶部行包含标签、打开文件按钮和清除按钮
        self.log_label = toga.Label(
            "Application Log:", 
            style=Pack(margin=5, flex=1)
        )
        
        self.open_logfile_button = toga.Button(
            text="Open Log File", 
            on_press=self._open_log_file,
            style=Pack(margin=5)
        )
        
        self.clear_button = toga.Button(
            text="Clear Logs", 
            on_press=self._clear_logs,
            style=Pack(margin=5)
        )
        
        self.top_row = toga.Box(
            children=[self.log_label, self.open_logfile_button, self.clear_button],
            style=Pack(direction=ROW, align_items='center')
        )

        # Setup log area
        # 设置日志区域
        self.log_area = toga.MultilineTextInput(
            readonly=True, 
            flex=1,
            style=Pack(margin=5)
        )

        # Setup container box
        # 设置容器框
        self.log_tab_box = toga.Box(
            children=[self.top_row, self.log_area],
            style=Pack(direction=COLUMN, margin=5)
        )
        
        # Start buffer flush timer for performance optimization
        # 启动缓冲区刷新定时器用于性能优化
        self._start_buffer_timer()

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

    def _start_buffer_timer(self):
        """
        Start the buffer flush timer for performance optimization
        启动缓冲区刷新定时器用于性能优化
        """
        def timer_func():
            while True:
                time.sleep(0.5)  # Flush every 500ms
                self._flush_buffer()
        
        timer_thread = threading.Thread(target=timer_func, daemon=True)
        timer_thread.start()

    def _flush_buffer(self):
        """
        Flush the log buffer to the GUI
        将日志缓冲区刷新到GUI
        """
        try:
            with self.buffer_lock:
                if self.log_buffer and hasattr(self, 'log_area') and self.log_area:
                    # Join all buffered messages
                    # 合并所有缓冲的消息
                    buffered_text = ''.join(self.log_buffer)
                    if buffered_text:
                        self.log_area.value += buffered_text
                        self.log_area.scroll_to_bottom()
                    self.log_buffer.clear()
        except Exception as e:
            # Silently handle errors to avoid disrupting the application
            # 静默处理错误以避免干扰应用程序
            pass

    def write(self, text):
        """
        Write log text with buffering and exception handling
        带有缓冲和异常处理的写入日志文本

        Args:
            text: Text to write 要写入的文本
        """
        try:
            # Add to buffer for performance optimization
            # 添加到缓冲区以进行性能优化
            with self.buffer_lock:
                self.log_buffer.append(text)
                
            # For critical messages, flush immediately
            # 对于关键消息，立即刷新
            if "ERROR" in text or "CRITICAL" in text:
                self._flush_buffer()
                
        except Exception as e:
            # If buffering fails, try direct write as fallback
            # 如果缓冲失败，尝试直接写入作为后备
            try:
                if hasattr(self, 'log_area') and self.log_area:
                    self.log_area.value += text
                    self.log_area.scroll_to_bottom()
            except Exception:
                # If GUI log display fails, ensure file logging still works
                # 如果GUI日志显示失败，确保文件日志仍然正常工作
                pass

    def flush(self):
        """
        Flush log stream with exception handling
        带有异常处理的刷新日志流
        """
        try:
            # Flush the buffer
            # 刷新缓冲区
            self._flush_buffer()
            
            # Force GUI refresh if available
            # 如果可用，强制刷新GUI
            if hasattr(self, 'log_area') and self.log_area:
                try:
                    if hasattr(self.app, 'loop') and self.app.loop:
                        self.app.loop.call_soon_threadsafe(
                            lambda: self.log_area.refresh() if hasattr(self.log_area, 'refresh') else None
                        )
                except Exception:
                    # If thread-safe call fails, continue silently
                    # 如果线程安全调用失败，静默继续
                    pass
        except Exception as e:
            # Silently handle flush errors
            # 静默处理刷新错误
            pass


    def _clear_logs(self, widget):
        """
        Clear only the GUI log area
        清除GUI日志区域

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
        self.log_area.value = ""