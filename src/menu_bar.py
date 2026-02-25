# ./src/menu_bar.py
from PySide6.QtWidgets import QMenuBar, QMenu, QFileDialog, QMessageBox, QLabel
from PySide6.QtGui import QAction, QKeySequence, QDesktopServices
from PySide6.QtCore import QUrl, Qt
import os

from src.settings_window import SettingsWindow

class CustomMenuBar(QMenuBar):
    def __init__(self, parent=None, i18n=None):
        super().__init__(parent)
        self.parent = parent
        self.i18n = i18n
        self.is_fullscreen = False
        self.comics_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comics")
        self.toggle_cfs_action = None
        self.init_menu()
    
    def init_menu(self):
        # File menu
        file_menu = QMenu(self.i18n.tr("File"), self)

        refresh_action = QAction(self.i18n.tr("Refresh Comics List"), self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_comics_list)
        file_menu.addAction(refresh_action)

        select_folder_action = QAction(self.i18n.tr("Select Comics Directory"), self)
        select_folder_action.triggered.connect(self.select_comics_directory)
        file_menu.addAction(select_folder_action)

        open_comics_folder_action = QAction(self.i18n.tr("Open Comics Directory"), self)
        open_comics_folder_action.triggered.connect(self.open_comics_directory)
        file_menu.addAction(open_comics_folder_action)

        open_cfs_folder_action = QAction(self.i18n.tr("Open CFS Directory"), self)
        open_cfs_folder_action.triggered.connect(self.open_cfs_directory)
        file_menu.addAction(open_cfs_folder_action)

        export_cfs_action = QAction(self.i18n.tr("Export CFS File"), self)
        export_cfs_action.setShortcut("Ctrl+E")
        export_cfs_action.triggered.connect(self.export_cfs_file)
        file_menu.addAction(export_cfs_action)

        export_heatmap_action = QAction(self.i18n.tr("Export Heatmap"), self)
        export_heatmap_action.triggered.connect(self.export_heatmap)
        file_menu.addAction(export_heatmap_action)

        open_thumbnails_action = QAction(self.i18n.tr("Open Thumbnails Directory"), self)
        open_thumbnails_action.triggered.connect(self.open_thumbnails_directory)
        file_menu.addAction(open_thumbnails_action)

        preferences_action = QAction(self.i18n.tr("Preferences"), self)
        preferences_action.triggered.connect(self.open_preferences)
        file_menu.addAction(preferences_action)

        file_menu.addSeparator()

        exit_action = QAction(self.i18n.tr("Exit"), self)
        exit_action.setShortcut("Esc")
        exit_action.triggered.connect(self.parent.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = QMenu(self.i18n.tr("View"), self)
        view_menu.setObjectName("view_menu_action")

        self.toggle_cfs_action = QAction(self.i18n.tr("Show CFS Editor"), self)
        self.toggle_cfs_action.setShortcut("F10")
        self.toggle_cfs_action.triggered.connect(self.toggle_cfs_editor)
        view_menu.addAction(self.toggle_cfs_action)
        self.toggle_cfs_action.setData("toggle_cfs_editor")

        fullscreen_action = QAction(self.i18n.tr("Fullscreen"), self)
        fullscreen_action.setShortcut(QKeySequence.StandardKey.FullScreen)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        # Help menu
        help_menu = QMenu(self.i18n.tr("Help"), self)

        donation_action = QAction(self.i18n.tr("Support This Project"), self)
        donation_action.triggered.connect(self.show_donation_dialog)
        help_menu.addAction(donation_action)

        open_github_action = QAction(self.i18n.tr("Open GitHub"), self)
        open_github_action.triggered.connect(self.open_github)
        help_menu.addAction(open_github_action)

        self.addMenu(file_menu)
        self.addMenu(view_menu)
        self.addMenu(help_menu)

    def select_comics_directory(self):
        """Select comics directory"""
        directory = QFileDialog.getExistingDirectory(self, self.i18n.tr("Select Comics Directory"), self.comics_dir)
        if directory:
            self.comics_dir = directory
            if hasattr(self.parent, 'load_comics_list'):
                self.parent.comics_dir = directory
                self.parent.load_comics_list()

    def open_comics_directory(self):
        """Open comics directory"""
        directory = getattr(self.parent, 'comics_dir', self.comics_dir)
        QDesktopServices.openUrl(QUrl.fromLocalFile(directory))

    def open_cfs_directory(self):
        """Open CFS directory"""
        cfs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cfs")
        if not os.path.exists(cfs_path):
            os.makedirs(cfs_path, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(cfs_path)))

    def open_thumbnails_directory(self):
        """Open thumbnails directory"""
        thumbnails_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "thumbnails")
        if not os.path.exists(thumbnails_path):
            os.makedirs(thumbnails_path, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(thumbnails_path)))
    
    def toggle_cfs_editor(self):
        """Show/hide CFS editor"""
        if hasattr(self.parent, 'toggle_cfs_editor'):
            self.parent.toggle_cfs_editor()

    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if not self.is_fullscreen:
            self.parent.showFullScreen()
            self.is_fullscreen = True
        else:
            self.parent.showNormal()
            self.is_fullscreen = False

    def open_preferences(self):
        """Open preferences window"""
        settings_window = SettingsWindow(self.parent, self.i18n)
        settings_window.exec()

    def refresh_comics_list(self):
        """Refresh comics list"""
        if hasattr(self.parent, 'load_comics_list'):
            self.parent.load_comics_list()

    def export_cfs_file(self):
        """Export the current comic's CFS file"""
        if hasattr(self.parent, 'export_current_cfs'):
            self.parent.export_current_cfs()

    def export_heatmap(self):
        """Export heatmap"""
        if hasattr(self.parent, 'export_heatmap'):
            self.parent.export_heatmap()

    def show_donation_dialog(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(self.i18n.tr("Support This Project"))
        msg_box.setIcon(QMessageBox.NoIcon)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.button(QMessageBox.StandardButton.Ok).setText(self.i18n.tr("OK"))
        label = QLabel()
        donation_text = (
            f"<h3>{self.i18n.tr('Support Development')}</h3>"
            f"<p>{self.i18n.tr('This project is free and open source, developed and maintained in my spare time by me (github.com/Karasukaigan). If you find it helpful or inspiring, please consider supporting its continued development.')}</p>"
            f"<p>{self.i18n.tr('Your donation helps cover development time, feature improvements, and maintenance costs.')}</p>"
            f"<p><b>{self.i18n.tr('Ethereum (ETH)')}:</b><br>"
            f"<b style='color: yellow;'>0x3E709387db900c47C6726e4CFa40A5a51bC9Fb97</b></p>"
            f"<p><b>{self.i18n.tr('Bitcoin (BTC)')}:</b><br>"
            f"<b style='color: yellow;'>bc1qguk59xapemd3k0a8hen229av3vs5aywq9gzk6e</b></p>"
            f"<p>{self.i18n.tr('Every contribution, no matter the amount, is greatly appreciated. Thank you for supporting open-source!')}</p>"
        )
        label.setText(donation_text)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)  # 启用文本选择
        label.setWordWrap(True)
        label.setStyleSheet("QLabel { margin-right: 20px; }")
        msg_box.layout().addWidget(label, 0, 1)
        msg_box.exec()

    def open_github(self):
        """Open GitHub page"""
        QDesktopServices.openUrl(QUrl("https://github.com/Karasukaigan/CFSReader"))