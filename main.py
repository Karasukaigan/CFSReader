import sys
import os
from pathlib import Path
import subprocess
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QListWidget, QLabel, QPushButton, QWidget, QFileDialog, QMessageBox, QSlider, QLineEdit, QTextEdit
from PySide6.QtGui import QPixmap, QIcon, QKeySequence, QShortcut, QMovie
from PySide6.QtCore import Qt
from dotenv import load_dotenv, get_key, set_key
import random
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from src.menu_bar import CustomMenuBar
from src.serial_controller import SerialController
from src.i18n import I18nManager

class ComicReader(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.load_environment()  # Load environment variables
        self.expert_mode = str(get_key(".env", "EXPERT_MODE") or False).lower() in ('true', '1', 'yes', 'on')

        self.i18n = I18nManager()  # i18n

        self.setWindowTitle(f"{self.i18n.tr("CFSReader")} v1.2")
        self.setGeometry(100, 100, 1000, 600)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "img", "logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.load_stylesheet()
        
        self.cfs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cfs")  # Path to the comics directory
        self.comics_dir = self.get_comics_directory()
        self.current_comic_path = None
        self.image_files = []
        self.current_image_index = 0
        self.sort_order = self.get_sort_order()  # Comics sorting method
        self.all_comics = []  # List of comics
        self.is_slider_changing = False

        self.serial_controller = SerialController()  # Serial controller
        self.serial_controller.port = self.serial_controller.get_serial_port_from_env()
        try:
            self.serial_controller.connect()
            # self.serial_controller.send_data("L05000\n")
        except Exception as e:
            pass
        
        self.init_ui()
        self.load_comics_list()
        self.center_window()
    
    def toggle_cfs_editor(self):
        """Toggle the visibility of the CFS editor"""
        is_visible = self.cfs_edit_group.isVisible()
        self.cfs_edit_group.setVisible(not is_visible)
        menu_bar = self.menuBar()
        if hasattr(menu_bar, 'toggle_cfs_action'):
            if is_visible:
                menu_bar.toggle_cfs_action.setText(self.i18n.tr("Show CFS Editor"))
            else:
                menu_bar.toggle_cfs_action.setText(self.i18n.tr("Hide CFS Editor"))

    def center_window(self):
        """Center the window on the screen"""
        sg = self.screen().geometry()
        wg = self.geometry()
        self.move((sg.width() - wg.width()) // 2, (sg.height() - wg.height()) // 2 - 50)
    
    def load_environment(self):
        """Load environment variables"""
        env_path = Path(".env")
        if not env_path.exists():
            env_path.touch()
            set_key(env_path, "COMICS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "comics"))
            set_key(env_path, "SORT_ORDER", "name")
            set_key(env_path, "SERIAL_PORT", "")
        load_dotenv(override=True)
        if not get_key(env_path, 'COMICS_DIR'):
            set_key(env_path, "COMICS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "comics"))
        if not get_key(env_path, 'SORT_ORDER'):
            set_key(env_path, "SORT_ORDER", "name")
        if not get_key(env_path, 'EXPERT_MODE'):
            set_key(env_path, "EXPERT_MODE", "false")

    def get_comics_directory(self):
        """Get the path to the comics directory"""
        return os.getenv("COMICS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "comics"))
    
    def get_sort_order(self):
        """Get the sorting method"""
        return os.getenv("SORT_ORDER", "name")

    def load_stylesheet(self):
        """Load the stylesheet"""
        style_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "styles", "main.qss")
        if os.path.exists(style_file):
            with open(style_file, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
    
    def init_ui(self):
        # Add custom menu bar
        self.setMenuBar(CustomMenuBar(self, self.i18n))

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Left panel for comic list
        left_panel = QVBoxLayout()

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(self.i18n.tr("Search"))
        self.search_box.textChanged.connect(self.filter_comics_list)
        left_panel.addWidget(self.search_box)

        # Comic list
        self.comics_list = QListWidget()
        self.comics_list.itemClicked.connect(self.on_comic_selected)
        left_panel.addWidget(self.comics_list)

        # Right panel for image display and controls
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(3, 0, 3, 0)

        # Image display label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(600, 400)
        right_panel.addWidget(self.image_label)

        # Control buttons
        controls_layout = QHBoxLayout()

        self.prev_button = QPushButton(self.i18n.tr("Previous Page (←)"))
        self.prev_button.clicked.connect(self.previous_image)
        self.prev_button.setEnabled(False)
        controls_layout.addWidget(self.prev_button)

        self.emergency_stop_button = QPushButton(self.i18n.tr("Stop (Space)"))
        self.emergency_stop_button.clicked.connect(self.emergency_stop)
        controls_layout.addWidget(self.emergency_stop_button)
        space_shortcut = QShortcut(QKeySequence("Space"), self)
        space_shortcut.activated.connect(self.emergency_stop)

        self.next_button = QPushButton(self.i18n.tr("Next Page (→)"))
        self.next_button.clicked.connect(self.next_image)
        self.next_button.setEnabled(False)
        controls_layout.addWidget(self.next_button)

        right_panel.addLayout(controls_layout)

        # Page info and slider layout
        info_layout = QHBoxLayout()
        self.page_slider = QSlider(Qt.Horizontal)
        self.page_slider.setMinimum(0)
        self.page_slider.setMaximum(0)
        self.page_slider.setValue(0)
        self.page_slider.setEnabled(False)
        self.page_slider.valueChanged.connect(self.on_slider_value_changed)
        info_layout.addWidget(self.page_slider)
        self.page_info_label = QLabel()
        self.page_info_label.setAlignment(Qt.AlignCenter)
        self.page_info_label.setText("0 / 0")
        self.page_info_label.setObjectName("page_info_label")
        info_layout.addWidget(self.page_info_label)
        right_panel.addLayout(info_layout)

        # CFS parameter editing area
        cfs_edit_layout = QVBoxLayout()
        cfs_edit_group = QWidget()
        cfs_edit_group.setObjectName("cfs_edit_group")
        cfs_edit_layout.setContentsMargins(10, 10, 10, 10)
        cfs_edit_group.setLayout(cfs_edit_layout)

        # CFS data display text box
        self.cfs_display_text = QTextEdit()
        self.cfs_display_text.setMaximumHeight(60)
        self.cfs_display_text.setReadOnly(True)
        cfs_edit_layout.addWidget(self.cfs_display_text)

        # Curve display area
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(120)
        cfs_edit_layout.addWidget(self.canvas)
        self.plot_sawtooth_wave()

        # Max value slider
        max_layout = QVBoxLayout()
        self.max_label_text = self.i18n.tr("Max")
        self.max_label = QLabel(f"{self.max_label_text} 50")
        self.max_label.setAlignment(Qt.AlignCenter)
        self.max_slider = QSlider(Qt.Horizontal)
        self.max_slider.setMinimum(0)
        self.max_slider.setMaximum(100)
        self.max_slider.setValue(50)
        self.max_slider.setSingleStep(1)
        self.max_slider.valueChanged.connect(lambda v: self.max_label.setText(f"{self.max_label_text} {v}"))
        max_layout.addWidget(self.max_label)
        max_layout.addWidget(self.max_slider)
        cfs_edit_layout.addLayout(max_layout)

        # Min value slider
        min_layout = QVBoxLayout()
        self.min_label_text = self.i18n.tr("Min")
        self.min_label = QLabel(f"{self.min_label_text} 50")
        self.min_label.setAlignment(Qt.AlignCenter)
        self.min_slider = QSlider(Qt.Horizontal)
        self.min_slider.setMinimum(0)
        self.min_slider.setMaximum(100)
        self.min_slider.setValue(50)
        self.min_slider.setSingleStep(1)
        self.min_slider.valueChanged.connect(lambda v: self.min_label.setText(f"{self.min_label_text} {v}"))
        min_layout.addWidget(self.min_label)
        min_layout.addWidget(self.min_slider)
        cfs_edit_layout.addLayout(min_layout)

        # Frequency slider
        freq_layout = QVBoxLayout()
        self.freq_label_text = self.i18n.tr("Frequency")
        self.freq_label = QLabel(f"{self.freq_label_text} 1.00")
        self.freq_label.setAlignment(Qt.AlignCenter)
        self.freq_slider = QSlider(Qt.Horizontal)
        self.freq_slider.setMinimum(30)
        self.freq_slider.setMaximum(250)
        self.freq_slider.setValue(100)
        self.freq_slider.setSingleStep(1)
        self.freq_slider.valueChanged.connect(lambda v: self.freq_label.setText(f"{self.freq_label_text} {v/100:.2f}"))
        freq_layout.addWidget(self.freq_label)
        freq_layout.addWidget(self.freq_slider)
        cfs_edit_layout.addLayout(freq_layout)

        # Decline ratio slider
        decline_layout = QVBoxLayout()
        self.decline_ratio_label_text = self.i18n.tr("Decline Ratio")
        self.decline_ratio_label = QLabel(f"{self.decline_ratio_label_text} 0.50")
        self.decline_ratio_label.setAlignment(Qt.AlignCenter)
        self.decline_ratio_slider = QSlider(Qt.Horizontal)
        self.decline_ratio_slider.setMinimum(30)
        self.decline_ratio_slider.setMaximum(70)
        self.decline_ratio_slider.setValue(50)
        self.decline_ratio_slider.setSingleStep(1)
        self.decline_ratio_slider.valueChanged.connect(lambda v: self.decline_ratio_label.setText(f"{self.decline_ratio_label_text} {v/100:.2f}"))
        decline_layout.addWidget(self.decline_ratio_label)
        decline_layout.addWidget(self.decline_ratio_slider)
        cfs_edit_layout.addLayout(decline_layout)

        # Parameter preset buttons
        preset_buttons_layout = QHBoxLayout()
        preset_buttons_layout.setContentsMargins(0, 10, 0, 0)

        slow_btn = QPushButton(self.i18n.tr("S"))
        slow_btn.clicked.connect(lambda: self.set_slider(100, 0, 0.5, 0.35))
        preset_buttons_layout.addWidget(slow_btn)

        medium_btn = QPushButton(self.i18n.tr("M"))
        medium_btn.clicked.connect(lambda: self.set_slider(100, 0, 1.0, 0.45))
        preset_buttons_layout.addWidget(medium_btn)

        fast_btn = QPushButton(self.i18n.tr("F"))
        fast_btn.clicked.connect(lambda: self.set_slider(100, 0, 2.0, 0.5))
        preset_buttons_layout.addWidget(fast_btn)

        top_btn = QPushButton(self.i18n.tr("T"))
        top_btn.clicked.connect(lambda: self.set_slider(100, 45, 1.0, 0.65))
        preset_buttons_layout.addWidget(top_btn)

        bottom_btn = QPushButton(self.i18n.tr("B"))
        bottom_btn.clicked.connect(lambda: self.set_slider(55, 0, 0.8, 0.45))
        preset_buttons_layout.addWidget(bottom_btn)

        cfs_edit_layout.addLayout(preset_buttons_layout)

        # Save button
        self.save_cfs_button = QPushButton(self.i18n.tr("Save (Ctrl+S)"))
        self.save_cfs_button.clicked.connect(self.save_cfs_changes)
        cfs_edit_layout.addWidget(self.save_cfs_button)

        # Delete settings button
        self.delete_cfs_button = QPushButton(self.i18n.tr("Delete (Delete)"))
        self.delete_cfs_button.clicked.connect(self.delete_cfs_setting)
        cfs_edit_layout.addWidget(self.delete_cfs_button)

        cfs_edit_group.setVisible(False)
        self.cfs_edit_group = cfs_edit_group

        # Main layout: left list + right content + CFS editing
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 3)
        main_layout.addWidget(cfs_edit_group)

        # Shortcuts
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_cfs_changes)
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self.delete_cfs_setting)

        self.setFocus()

    def _clamp(self, value, min_val, max_val):
        return max(min_val, min(value, max_val))

    def set_slider(self, max_val=None, min_val=None, freq=None, decline_ratio=None):
        """Set slider value"""
        if max_val is not None:
            self.max_slider.setValue(self._clamp(int(max_val), 0, 100))
        if min_val is not None:
            self.min_slider.setValue(self._clamp(int(min_val), 0, 100))
        if freq is not None:
            self.freq_slider.setValue(self._clamp(int(freq * 100), 10, 250))
        if decline_ratio is not None:
            self.decline_ratio_slider.setValue(self._clamp(int(decline_ratio * 100), 30, 70))

    def filter_comics_list(self, text):
        """Filter the comic list based on the search box content"""
        if len(text) >= 2:
            filtered_items = [comic for comic in self.all_comics if text.lower() in comic.lower()]
            self.comics_list.clear()
            for comic in filtered_items:
                self.comics_list.addItem(comic)
        elif len(text) == 0:
            self.comics_list.clear()
            for comic in self.all_comics:
                self.comics_list.addItem(comic)
    
    def load_comics_list(self):
        """Load the comic list"""
        self.sort_order = self.get_sort_order()
        if not os.path.exists(self.comics_dir):
            self.comics_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comics")
            os.makedirs(self.comics_dir, exist_ok=True)
            return

        self.comics_list.clear()
        self.all_comics = []

        comic_dirs = []
        for item in os.listdir(self.comics_dir):
            item_path = os.path.join(self.comics_dir, item)
            if os.path.isdir(item_path):
                mod_time = os.path.getmtime(item_path)
                comic_dirs.append((item, mod_time))

        if self.sort_order == "time":
            comic_dirs.sort(key=lambda x: x[1], reverse=True)
            sorted_items = [item[0] for item in comic_dirs]
        elif self.sort_order == "random":
            sorted_items = [item[0] for item in comic_dirs]
            random.shuffle(sorted_items)
        else:
            sorted_items = sorted([item[0] for item in comic_dirs])

        self.all_comics = sorted_items
        for item in sorted_items:
            self.comics_list.addItem(item)

    def on_comic_selected(self, item):
        """Comic selection event"""
        comic_name = item.text()

        if self.serial_controller:
            if not os.path.exists(self.cfs_dir):
                self.cfs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cfs")
                os.makedirs(self.cfs_dir, exist_ok=True)
            cfs_path = os.path.join(self.cfs_dir, f"{comic_name}.cfs")
            if not os.path.exists(cfs_path):
                cfs_path = os.path.join(self.comics_dir, f"{comic_name}.cfs")
                if not os.path.exists(cfs_path):
                    cfs_path = os.path.join(self.comics_dir, comic_name, f"{comic_name}.cfs")
            self.serial_controller.load_cfs(cfs_path)

        self.current_comic_path = os.path.join(self.comics_dir, comic_name)
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        self.image_files = []
        for file in sorted(os.listdir(self.current_comic_path)):
            file_ext = Path(file).suffix.lower()
            if file_ext in image_extensions:
                self.image_files.append(os.path.join(self.current_comic_path, file))

        if self.image_files:
            self.current_image_index = 0
            self.show_current_image()
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(len(self.image_files) > 1)
        else:
            self.image_label.clear()
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.page_info_label.setText("0 / 0")
            self.page_slider.setEnabled(False)
            self.page_slider.setValue(0)
            self.page_slider.setMaximum(0)

            self.cfs_display_text.setText('')
            self.max_slider.setValue(50)
            self.min_slider.setValue(50)
            self.freq_slider.setValue(100)
            self.decline_ratio_slider.setValue(50)
            self.plot_sawtooth_wave()
    
    def plot_sawtooth_wave(self, params=None):
        """Plot a sawtooth waveform based on CFS parameters"""
        self.figure.clear()
        self.figure.patch.set_facecolor('#1e1e1e')
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#1e1e1e')
        if params:
            max_val = params['max']
            min_val = params['min']
            freq = params['freq']
            decline_ratio = params['decline_ratio']
            t = np.linspace(0, 3, 1000)  # Generate a time array for 3 seconds
            y = np.zeros_like(t)  # Calculate the sawtooth waveform
            for i, time_point in enumerate(t):
                # Calculate the position within the current cycle
                cycle_time = time_point % (1.0 / freq) if freq != 0 else 0
                cycle_duration = 1.0 / freq if freq != 0 else 1
                
                # Calculate the time points for the decline and rise phases
                decline_duration = cycle_duration * decline_ratio
                rise_duration = cycle_duration - decline_duration
                
                if cycle_time <= decline_duration and decline_duration > 0:
                    # Decline phase
                    progress = cycle_time / decline_duration
                    y[i] = max_val - (max_val - min_val) * progress
                elif rise_duration > 0:
                    # Rise phase
                    progress = (cycle_time - decline_duration) / rise_duration
                    y[i] = min_val + (max_val - min_val) * progress
            ax.plot(t, y, color='#264f78', linewidth=1.5)
        ax.grid(True, linestyle='--', alpha=0.6, color='#3c3c3c')    
        ax.set_xlim(0, 3)
        ax.set_ylim(0, 100)
        ax.spines['bottom'].set_color('#3c3c3c')
        ax.spines['top'].set_color('#3c3c3c')
        ax.spines['left'].set_color('#3c3c3c')
        ax.spines['right'].set_color('#3c3c3c')
        ax.tick_params(colors='#3c3c3c')
        ax.set_xticks([])
        ax.set_yticks([])
        self.figure.tight_layout()
        self.figure.tight_layout(pad=0.1)
        self.canvas.draw()

    def update_cfs_display(self):
        """Update the display of CFS parameters"""
        if self.current_comic_path and self.image_files and self.serial_controller:
            current_image_name = os.path.basename(self.image_files[self.current_image_index])
            cfs_data = self.serial_controller.get_current_cfs()

            if current_image_name in cfs_data:
                current_params = cfs_data[current_image_name]
                cfs_text = f'"{current_image_name}": {current_params}'
                self.cfs_display_text.setText(cfs_text)
                
                self.max_slider.setValue(current_params['max'])
                self.min_slider.setValue(current_params['min'])
                self.freq_slider.setValue(int(current_params['freq'] * 100))
                self.decline_ratio_slider.setValue(int(current_params['decline_ratio'] * 100))

                self.plot_sawtooth_wave(current_params)
            else:
                self.cfs_display_text.setText(f'"{current_image_name}": ' + r'{}')
                self.max_slider.setValue(50)
                self.min_slider.setValue(50)
                self.freq_slider.setValue(100)
                self.decline_ratio_slider.setValue(50)
                self.plot_sawtooth_wave()

    def save_cfs_changes(self):
        """Save changes to CFS parameters"""
        if not self.current_comic_path or not self.image_files or not self.serial_controller:
            return

        current_image_name = os.path.basename(self.image_files[self.current_image_index])
        cfs_data = self.serial_controller.get_current_cfs()

        try:
            updated_params = {
                'max': self.max_slider.value(),
                'min': self.min_slider.value(),
                'freq': self.freq_slider.value() / 100.0,
                'decline_ratio': self.decline_ratio_slider.value() / 100.0
            }
            cfs_data[current_image_name] = updated_params

            self.serial_controller.current_cfs = cfs_data

            comic_name = os.path.basename(self.current_comic_path)
            cfs_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cfs", f"{comic_name}.cfs")
            success = self.serial_controller.save_cfs(cfs_file_path)
            
            if success:
                cfs_text = f'"{current_image_name}": {updated_params}'
                self.cfs_display_text.setText(cfs_text)

                self.plot_sawtooth_wave(updated_params)
                if self.serial_controller:
                    self.serial_controller.new_page(current_image_name)
            else:
                raise Exception(self.i18n.tr("Unable to save CFS parameters to file"))
        except Exception as e:
            QMessageBox.warning(self, self.i18n.tr("Error"), f"{self.i18n.tr('Error occurred while saving CFS file')}: {str(e)}")
        
        self.setFocus()

    def delete_cfs_setting(self):
        """Delete the CFS settings for the current image"""
        if not self.current_comic_path or not self.image_files or not self.serial_controller:
            return

        current_image_name = os.path.basename(self.image_files[self.current_image_index])
        cfs_data = self.serial_controller.get_current_cfs()

        if current_image_name in cfs_data:
            del cfs_data[current_image_name]

            self.serial_controller.current_cfs = cfs_data

            comic_name = os.path.basename(self.current_comic_path)
            cfs_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cfs", f"{comic_name}.cfs")
            success = self.serial_controller.save_cfs(cfs_file_path)
            
            if success:
                self.cfs_display_text.setText(f'"{current_image_name}": ' + r'{}')
                self.max_slider.setValue(50)
                self.min_slider.setValue(50)
                self.freq_slider.setValue(100)
                self.decline_ratio_slider.setValue(50)
                self.plot_sawtooth_wave()
                self.emergency_stop()

        self.setFocus()

    def show_current_image(self):
        """Display the current image"""
        if 0 <= self.current_image_index < len(self.image_files):
            image_path = self.image_files[self.current_image_index]
            image_name = os.path.basename(image_path)
            file_ext = Path(image_path).suffix.lower()

            if file_ext == '.gif':
                pixmap = QPixmap(image_path)
                original_size = pixmap.size()
                movie = QMovie(image_path)
                label_size = self.image_label.size()
                scaled_size = original_size.scaled(
                    label_size.width() - 20,
                    label_size.height() - 20,
                    Qt.KeepAspectRatio
                )
                movie.setScaledSize(scaled_size)
                self.image_label.setMovie(movie)
                movie.start()
            else:
                pixmap = QPixmap(image_path)
                label_size = self.image_label.size()
                scaled_pixmap = pixmap.scaled(
                    label_size.width() - 20,
                    label_size.height() - 20,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)

            if self.serial_controller:
                self.serial_controller.new_page(image_name)

            self.setWindowTitle(f"{self.i18n.tr('CFSReader')} - {os.path.basename(image_path)}")
            self.update_page_info()
            self.update_cfs_display()
    
    def on_slider_value_changed(self, value):
        """Slider value change event"""
        if self.is_slider_changing:
            return
        if 0 <= value < len(self.image_files):
            self._clear_qmovie()
            self.current_image_index = value
            self.show_current_image()
            self.update_buttons_state()

    def update_page_info(self):
        """Update the page information display"""
        if self.image_files:
            current_page = self.current_image_index + 1
            total_pages = len(self.image_files)
            self.page_info_label.setText(f"{current_page} / {total_pages}")

            self.page_slider.setMaximum(len(self.image_files) - 1)
            self.page_slider.setValue(self.current_image_index)
            self.page_slider.setEnabled(True)
        else:
            self.page_info_label.setText("0 / 0")
            self.page_slider.setEnabled(False)
            self.page_slider.setValue(0)
            self.page_slider.setMaximum(0)

    def previous_image(self):
        """Display the previous image"""
        if self.current_image_index > 0:
            self._clear_qmovie()
            self.current_image_index -= 1
            self.is_slider_changing = True
            self.page_slider.setValue(self.current_image_index)
            self.is_slider_changing = False
            self.show_current_image()
            self.update_buttons_state()

    def next_image(self):
        """Display the next image"""
        if self.current_image_index < len(self.image_files) - 1:
            self._clear_qmovie()
            self.current_image_index += 1
            self.is_slider_changing = True
            self.page_slider.setValue(self.current_image_index)
            self.is_slider_changing = False
            self.show_current_image()
            self.update_buttons_state()

    def _clear_qmovie(self):
        if hasattr(self.image_label, 'movie'):
            old_movie = self.image_label.movie()
            if old_movie:
                old_movie.stop()
                self.image_label.setMovie(None)

    def emergency_stop(self):
        """Emergency stop function"""
        if self.serial_controller:
            self.serial_controller.new_page("")
    
    def update_buttons_state(self):
        """Update the state of the buttons"""
        self.prev_button.setEnabled(self.current_image_index > 0)
        self.next_button.setEnabled(self.current_image_index < len(self.image_files) - 1)
        self.update_page_info()
    
    def resizeEvent(self, event):
        """Window resize event"""
        super().resizeEvent(event)
        if self.current_comic_path and self.image_files:
            self.show_current_image()
            self.page_slider.setValue(self.current_image_index)

    def keyPressEvent(self, event):
        """Handle keyboard key press events"""
        key = event.key()
        if key == Qt.Key_Left:
            self.previous_image()
        elif key == Qt.Key_Right:
            self.next_image()
        elif key == Qt.Key_Space:
            self.emergency_stop()
        super().keyPressEvent(event)
    
    def restart_application(self):
        """Restart the application"""
        if self.serial_controller:
            self.serial_controller.disconnect()
        self.close()
        subprocess.Popen([sys.executable, *sys.argv])
        QApplication.quit()

    def export_current_cfs(self):
        """Export the CFS file of the current comic"""
        if not self.current_comic_path or not self.serial_controller:
            return
        comic_name = os.path.basename(self.current_comic_path)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.i18n.tr("Export CFS File"),
            f"{comic_name}.cfs",
            "CFS Files (*.cfs);;All Files (*)"
        )
        if file_path:
            try:
                cfs_data = self.serial_controller.get_current_cfs()
                success = self.serial_controller.export_cfs(cfs_data, file_path)
                if not success:
                    raise Exception(self.i18n.tr("Unable to save CFS file"))
            except Exception as e:
                QMessageBox.warning(self, self.i18n.tr("Error"), f"{self.i18n.tr('Failed to export CFS file')}: {str(e)}")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CFSReader")
    reader = ComicReader()
    reader.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()