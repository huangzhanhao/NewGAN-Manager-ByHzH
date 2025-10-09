import logging
import logging.handlers
import queue
import os

class UIHandler(logging.Handler):
    """Handler that forwards log records to a UI queue."""
    def __init__(self, ui_queue: queue.Queue):
        super().__init__()
        self.ui_queue = ui_queue

    def emit(self, record: logging.LogRecord):
        try:
            # Put the record into the UI queue for the LogTab to consume
            self.ui_queue.put(record)
        except Exception:
            self.handleError(record)

class NewGanLogManager:
    def __init__(self, root_dir) -> None:
        self.log_file = os.path.join(str(root_dir), "newgan.log")
        self.max_bytes = int(10 * 1024 * 1024)
        self.backup_count = int(3)
        self.log_level = logging.DEBUG
        self.log_queue = queue.Queue(-1)
        self.ui_queue = queue.Queue(-1)  # queue for UI log records
        self.formatter = logging.Formatter("| %(asctime)s | %(name)s | %(levelname)s | %(module)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",)
        self.listener = None
        
        try:
            # 初始化日志系统
            self._setup_logging()
            print(f"日志系统已启动，日志文件路径: {self.log_file}")
        except Exception as e:
            # 如果初始化失败，确保清理资源
            self.shutdown()
            raise RuntimeError(f"日志系统初始化失败: {e}")
    
    def _setup_logging(self):
        # 配置名为"NewGAN App"的日志记录器
        logger = logging.getLogger("NewGAN App")
        logger.setLevel(self.log_level)

        # 移除所有现有处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 添加队列处理器
        queue_handler = logging.handlers.QueueHandler(self.log_queue)
        queue_handler.setLevel(self.log_level)
        # queue_handler.setFormatter(self.formatter)
        logger.addHandler(queue_handler)

        # 创建日志目录
        log_dir = os.path.dirname(self.log_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # 配置文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(self.formatter)

        # 创建UI处理器
        ui_handler = UIHandler(self.ui_queue)
        ui_handler.setLevel(self.log_level)
        ui_handler.setFormatter(self.formatter)

        # 创建并启动QueueListener，它会在内部创建线程处理日志
        self.listener = logging.handlers.QueueListener(
            self.log_queue,
            file_handler,  # 添加日志文件处理器
            ui_handler,    # 添加日志UI处理器
            respect_handler_level=True
        )
        self.listener.start()
    
    def get_ui_queue(self) -> queue.Queue:
        """获取UI队列，供LogTab使用"""
        return self.ui_queue
    
    def shutdown(self):
        try:
            if hasattr(self, 'listener') and self.listener:
                self.listener.stop()
                if hasattr(self.listener, 'handlers'):
                    for handler in self.listener.handlers:
                        handler.close()
            print("NewGAN Manager日志系统已关闭")
        except Exception as e:
            print(f"关闭日志系统时发生错误: {e}")