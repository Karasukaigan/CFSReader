# ./src/comics_list.py
from PySide6.QtWidgets import QListWidget, QMenu, QListWidgetItem
from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtGui import QPixmap, QIcon
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import os
import pyperclip
from dotenv import get_key

class CustomComicsList(QListWidget):
    def __init__(self, comics_dir, parent=None, i18n=None):
        super().__init__(parent)

        self.comics_dir = comics_dir
        self.i18n = i18n
        self.enable_thumb = str(get_key(".env", "ENABLE_THUMB") or False).lower() in ('true', '1', 'yes', 'on')
        self.thumb_size = self._split_ints(get_key(".env", "THUMB_SIZE")) or [100, 150]
        self.thumb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "thumbnails")
        if not os.path.exists(self.thumb_dir):
            os.makedirs(self.thumb_dir, exist_ok=True)

        self.executor = ThreadPoolExecutor(max_workers=4)  # Create thread pool
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)
        self.setIconSize(QSize(self.thumb_size[0], self.thumb_size[1]))
        self.thumbnail_cache = OrderedDict()  # Cache thumbnails
        self.max_cache_size = 50  # Maximum cache size
        self.visible_items = set()  # Current visible item indices set
        self.verticalScrollBar().valueChanged.connect(self.on_scroll)  # Connect scrollbar change signal

    def _split_ints(self, s: str) -> list[int]:
        try:
            if not s.strip():
                raise
            return [int(x.strip()) for x in s.split(',') if x.strip()]
        except Exception:
            return [100, 150]

    def load_initial_thumbnails(self):
        """Load first 20 thumbnails"""
        if not self.enable_thumb:
            return
        count = min(20, self.count())
        for index in range(count):
            self.load_thumbnail(index)

    def addItem(self, text_or_item):
        """Override addItem method, do not load thumbnails during initialization"""
        if isinstance(text_or_item, str):
            item = QListWidgetItem(text_or_item)
        else:
            item = text_or_item

        # Initialize with empty icon
        item.setIcon(QIcon())
        super().addItem(item)

    def on_scroll(self):
        """Respond to scroll events, update visible area and load/unload thumbnails"""
        if not self.enable_thumb:
            return

        if hasattr(self, '_scroll_timer'):
            self._scroll_timer.stop()
        else:
            self._scroll_timer = QTimer()
            self._scroll_timer.setSingleShot(True)
            self._scroll_timer.timeout.connect(self._load_visible_thumbnails)

        self._scroll_timer.start(100)

    def _load_visible_thumbnails(self):
        visible_indices = self.get_visible_indices()
        new_visible_items = set(visible_indices)

        for idx in self.visible_items - new_visible_items:
            self.unload_thumbnail(idx)

        futures = []
        for idx in new_visible_items - self.visible_items:
            item = self.item(idx)
            if item and item.icon().isNull():
                comic_path = os.path.join(self.comics_dir, item.text())
                image_path = self._get_first_image_path(comic_path)
                if image_path:
                    future = self.executor.submit(self._generate_thumbnail, image_path, tuple(self.thumb_size))
                    futures.append((future, image_path, idx))

        for future, image_path, idx in futures:
            future.add_done_callback(lambda f, ip=image_path, i=idx: self.on_thumbnail_loaded(ip, f.result(), i))

        self.visible_items = new_visible_items
    
    def get_visible_indices(self):
        """Calculate item indices within current visible area"""
        # Get indices of top and bottom of current viewport
        top_index = self.indexAt(self.viewport().rect().topLeft()).row()
        bottom_index = self.indexAt(self.viewport().rect().bottomRight()).row()

        # Handle boundary cases
        if top_index == -1:
            top_index = 0
        if bottom_index == -1:
            bottom_index = self.count() - 1

        # Expand visible area range
        buffer = 10  # Buffer size
        top_index = max(0, top_index - buffer)
        bottom_index = min(self.count() - 1, bottom_index + buffer)

        return list(range(top_index, bottom_index + 1))
    
    def load_thumbnail(self, index):
        if not self.enable_thumb:
            return
        
        item = self.item(index)
        if not item or not item.icon().isNull():
            return

        comic_path = os.path.join(self.comics_dir, item.text())
        if os.path.isdir(comic_path):
            image_path = self._get_first_image_path(comic_path)
            if image_path:
                if image_path in self.thumbnail_cache:
                    item.setIcon(self.thumbnail_cache[image_path])
                else:
                    # Submit task to thread pool
                    future = self.executor.submit(self._generate_thumbnail, image_path, (self.thumb_size[0], self.thumb_size[1]))
                    future.add_done_callback(lambda f: self.on_thumbnail_loaded(image_path, f.result(), index))

    def _generate_thumbnail(self, image_path, target_size):
        """Generate thumbnail in thread pool"""
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    target_size[0], target_size[1],
                    Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                x_offset = (scaled_pixmap.width() - target_size[0]) // 2
                y_offset = (scaled_pixmap.height() - target_size[1]) // 2
                cropped_pixmap = scaled_pixmap.copy(x_offset, y_offset, *target_size)
                return QIcon(cropped_pixmap)
        except Exception as e:
            print(f"Failed to generate thumbnail for {image_path}: {e}")
        return QIcon()

    def on_thumbnail_loaded(self, image_path, icon, index):
        """Handle callback after thumbnail loading completes"""
        self.thumbnail_cache[image_path] = icon
        item = self.item(index)
        if item:
            item.setIcon(icon)

        # Control cache size
        if len(self.thumbnail_cache) > self.max_cache_size:
            oldest_key = next(iter(self.thumbnail_cache))
            del self.thumbnail_cache[oldest_key]

    def unload_thumbnail(self, index):
        """Unload thumbnail at specified index"""
        item = self.item(index)
        if item:
            item.setIcon(QIcon())

    def _get_first_image_path(self, folder_path):
        """Get the first valid image in the specified directory"""
        item_text = os.path.basename(folder_path)
        thumb_path = os.path.join(self.thumb_dir, f"{item_text}.webp")

        # First check if corresponding thumbnail already exists in thumbnail directory
        if os.path.exists(thumb_path):
            try:
                pixmap = QPixmap(thumb_path)
                if not pixmap.isNull():
                    return thumb_path
            except Exception as e:
                print(f"Ignoring corrupt thumbnail {thumb_path}: {e}")

        # If no valid thumbnail found, search original directory and generate thumbnail
        supported_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        for file_name in os.listdir(folder_path):
            _, ext = os.path.splitext(file_name)
            if ext.lower() in supported_extensions:
                image_path = os.path.join(folder_path, file_name)
                try:
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        # Scale proportionally to height 300px
                        scaled_pixmap = pixmap.scaledToHeight(300, Qt.SmoothTransformation)
                        scaled_pixmap.save(thumb_path, "WEBP", quality=80)
                        return thumb_path
                except Exception as e:
                    print(f"Ignoring corrupt image {image_path}: {e}")
        
        return None

    def open_context_menu(self, position):
        """Show right-click menu"""
        menu = QMenu(self)
        copy_action = menu.addAction(self.i18n.tr("Copy Name"))
        open_action = menu.addAction(self.i18n.tr("Open Folder"))

        action = menu.exec_(self.mapToGlobal(position))
        if action == copy_action:
            self.copy_item()
        elif action == open_action:
            self.open_item()

    def copy_item(self):
        """Copy current item text"""
        current_item = self.currentItem()
        if current_item:
            pyperclip.copy(current_item.text())

    def open_item(self):
        """Open folder corresponding to current item"""
        current_item = self.currentItem()
        if current_item:
            item_path = os.path.join(self.comics_dir, current_item.text())
            if os.path.exists(item_path):
                os.startfile(item_path)  # Windows