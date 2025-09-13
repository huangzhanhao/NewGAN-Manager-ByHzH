import toga


class SourceSelection(toga.Selection):
    """
    Custom dropdown selection component that extends toga.Selection functionality
    自定义的下拉选择组件，扩展了toga.Selection功能
    """
    def __init__(self, id=None, style=None, items=None, on_change=None, enabled=True):
        """
        Initialize the SourceSelection component
        初始化SourceSelection组件

        Args:
            id: Component ID 组件ID
            style: Component style 组件样式
            items: List of selection items 选择项列表
            on_change: Change callback function 变更回调函数
            enabled: Whether the component is enabled 是否启用组件
        """
        super().__init__(id=id, style=style, items=items, on_change=on_change, enabled=enabled)

    def add_item(self, item):
        """
        Add a selection item
        添加选择项

        Args:
            item: Item to be added 要添加的项
        """
        self._items.append(item)

    def remove_item(self, item):
        """
        Remove a selection item
        移除选择项

        Args:
            item: Item to be removed 要移除的项
        """
        row = self._items.find(item)
        self._items.remove(row)