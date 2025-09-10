import logging
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


class LogTab:
    """
    Log tab UI components and functionality
    日志标签页UI组件和功能
    """
    def __init__(self, app):
        """
        Initialize log tab UI
        初始化日志标签页UI

        Args:
            app: Application instance 应用实例
        """
        self.app = app  # Application instance 应用实例

        # Logging setup
        # 日志设置
        formatter = logging.Formatter("%(asctime)s | %(name)s: %(message)s")
        self.app.logger.setLevel(logging.DEBUG)

        # Create FileHandler to update the log area in newgan.log
        # 创建文件处理器以更新newgan.log中的日志
        fh = logging.FileHandler(str(self.app.paths.app)+'/newgan.log')
        fh.setFormatter(formatter)
        self.app.logger.addHandler(fh)

        # Create StreamHandler to update the log area in the GUI
        # 创建流处理器以更新GUI中的日志
        gui_handler = logging.StreamHandler(self)
        gui_handler.setFormatter(formatter)
        self.app.logger.addHandler(gui_handler)

        # Setup top row with label and clear button
        # 顶部行包含标签和清除按钮
        self.log_label = toga.Label(
            "Application Log:", 
            style=Pack(margin=5, flex=1)
        )
        self.clear_button = toga.Button(
            text="Clear Logs", 
            on_press=self._clear_logs,
            style=Pack(margin=5)
        )
        
        self.top_row = toga.Box(
            children=[self.log_label, self.clear_button],
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

    def write(self, text):
        """
        Write log text
        写入日志文本

        Args:
            text: Text to write 要写入的文本
        """
        # Ensure UI updates happen on the main thread
        # 确保UI更新在主线程中进行
        if hasattr(self, 'log_area') and self.log_area:
            self.log_area.value += text
            self.log_area.scroll_to_bottom()

    def flush(self):
        """
        Flush log stream
        刷新日志流
        """
        # 在GUI应用中，确保界面更新
        if hasattr(self, 'log_area') and self.log_area:
            # 强制刷新GUI显示
            self.app.loop.call_soon_threadsafe(
                lambda: self.log_area.refresh() if hasattr(self.log_area, 'refresh') else None
            )


    def _clear_logs(self, widget):
        """
        Clear the log area
        清除日志区域

        Args:
            widget: The widget that triggered the event 触发事件的组件
        """
        self.log_area.value = ""