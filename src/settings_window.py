# ./src/settings_window.py
import os
import serial.tools.list_ports
from pathlib import Path
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QFileDialog, QMessageBox, QFormLayout, QDialog, QRadioButton, QButtonGroup, QComboBox
from dotenv import get_key, set_key

class SettingsWindow(QDialog):
    def __init__(self, parent=None, i18n=None):
        super().__init__(parent)
        self.parent = parent
        self.i18n = i18n
        self.setWindowTitle(self.i18n.tr("Preferences"))
        self.setModal(True)
        self.resize(500, 200)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()

        form_layout = QFormLayout()

        # Comics directory setting
        dir_layout = QHBoxLayout()
        self.comics_dir_line_edit = QLineEdit()
        self.comics_dir_line_edit.setReadOnly(True)
        select_dir_btn = QPushButton(self.i18n.tr("Select Directory"))
        select_dir_btn.clicked.connect(self.select_comics_directory)
        dir_layout.addWidget(self.comics_dir_line_edit)
        dir_layout.addWidget(select_dir_btn)
        form_layout.addRow(self.i18n.tr("Comics Directory"), dir_layout)
        
        # Sort order setting
        self.sort_order_group = QVBoxLayout()
        self.name_radio = QRadioButton(self.i18n.tr("Sort by Name"))
        self.time_radio = QRadioButton(self.i18n.tr("Sort from Newest to Oldest"))
        self.random_radio = QRadioButton(self.i18n.tr("Random Sort"))
        self.sort_button_group = QButtonGroup()
        self.sort_button_group.addButton(self.name_radio, 0)
        self.sort_button_group.addButton(self.time_radio, 1)
        self.sort_button_group.addButton(self.random_radio, 2)
        self.sort_order_group.addWidget(self.name_radio)
        self.sort_order_group.addWidget(self.time_radio)
        self.sort_order_group.addWidget(self.random_radio)
        form_layout.addRow(self.i18n.tr("Default Sort Order"), self.sort_order_group)

        # Serial port device setting
        self.serial_port_combo = QComboBox()
        serial_layout = QHBoxLayout()
        serial_layout.addWidget(self.serial_port_combo)
        form_layout.addRow(self.i18n.tr("Serial Port Device"), serial_layout)

        # Default language setting
        self.language_combo = QComboBox()
        self.language_combo.addItems(["en", "zh", "ja"])
        self.language_combo.setCurrentText(self.i18n.default_lang)
        form_layout.addRow(self.i18n.tr("Default Language"), self.language_combo)

        layout.addLayout(form_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton(self.i18n.tr("Save"))
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton(self.i18n.tr("Cancel"))
        cancel_btn.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)

        layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Load current settings
        self.load_settings()
    
    def load_settings(self):
        """Load current settings"""
        # Get current comics directory
        comics_dir = get_key(".env", "COMICS_DIR")
        self.comics_dir_line_edit.setText(comics_dir)
        
        # Load sort order setting
        sort_order = get_key(".env", "SORT_ORDER")
        if sort_order == "time":
            self.time_radio.setChecked(True)
        elif sort_order == "random":
            self.random_radio.setChecked(True)
        else:
            self.name_radio.setChecked(True)

        # Load serial port device setting
        self.refresh_serial_ports()
        self.serial_port_combo.insertItem(0, "", "")  # Add empty option
        selected_port = get_key(".env", "SERIAL_PORT") or ""
        index = self.serial_port_combo.findText(selected_port)
        if index >= 0:
            self.serial_port_combo.setCurrentIndex(index)
    
    def select_comics_directory(self):
        """Select comics directory"""
        current_dir = self.comics_dir_line_edit.text()
        if not os.path.exists(current_dir):
            current_dir = os.getcwd()
        directory = QFileDialog.getExistingDirectory(
            self, 
            self.i18n.tr("Select Comics Directory"), 
            current_dir
        )
        if directory:
            self.comics_dir_line_edit.setText(directory)

    def refresh_serial_ports(self):
        """Refresh serial port list"""
        self.serial_port_combo.clear()
        ports = get_usb_serial_ports()
        for port_info in ports:
            self.serial_port_combo.addItem(port_info['port'], port_info['description'])
    
    def save_settings(self):
        """Save settings"""
        # Get comics directory
        selected_dir = self.comics_dir_line_edit.text()
        if not selected_dir or not os.path.exists(selected_dir):
            return
        
        # Get sort order
        selected_sort_id = self.sort_button_group.checkedId()
        if selected_sort_id == 1:
            sort_order = "time"
        elif selected_sort_id == 2:
            sort_order = "random"
        else:
            sort_order = "name"

        # Get serial port device
        selected_port = self.serial_port_combo.currentText()

        # Get default language
        selected_language = self.language_combo.currentText()
        
        # Update .env
        try:
            env_path = Path(".env")
            if not env_path.exists():
                env_path.touch()
            set_key(env_path, "COMICS_DIR", selected_dir)
            set_key(env_path, "SORT_ORDER", sort_order)
            set_key(env_path, "SERIAL_PORT", selected_port)
            set_key(env_path, "DEF_LANG", selected_language)
            
            # Restart application
            self.parent.restart_application()
        except Exception as e:
            QMessageBox.critical(self, self.i18n.tr("Error"), f"{self.i18n.tr('Failed to save settings')}: {str(e)}")

def get_usb_serial_ports():
    """Get USB serial port list"""
    return [{'port': p.device, 'description': p.description} for p in serial.tools.list_ports.comports()]

if __name__ == "__main__":
    print(get_usb_serial_ports())