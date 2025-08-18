from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QRadioButton, QFormLayout, 
    QLineEdit, QDialogButtonBox, QLabel, QMessageBox
)
from PyQt5.QtCore import pyqtSignal

class DataParserDialog(QDialog):
    settingsApplied = pyqtSignal(dict)

    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Data Parser Settings")
        self.config = current_config.copy()
        self.initUI()
        self.load_settings()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        mode_group = QGroupBox("Parsing Method")
        mode_layout = QVBoxLayout()
        self.radio_simple = QRadioButton("Simple (Delimiter and Columns)")
        self.radio_regex = QRadioButton("Advanced (Regular Expression)")
        self.radio_binary = QRadioButton("Binary GPS Struct")
        self.radio_packet = QRadioButton("Packeted GPS with CRC")
        
        mode_layout.addWidget(self.radio_simple)
        mode_layout.addWidget(self.radio_regex)
        mode_layout.addWidget(self.radio_binary)
        mode_layout.addWidget(self.radio_packet)
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)

        self.simple_group = QGroupBox("Simple Mode Settings")
        simple_layout = QFormLayout()
        self.line_delimiter = QLineEdit()
        self.line_columns = QLineEdit()
        simple_layout.addRow("Delimiter:", self.line_delimiter)
        simple_layout.addRow("Columns (comma-separated):", self.line_columns)
        simple_layout.addRow(QLabel("Enter up to 8 column numbers, e.g., 1,2,3,4,5,6,7,8"))
        self.simple_group.setLayout(simple_layout)
        main_layout.addWidget(self.simple_group)

        self.regex_group = QGroupBox("Advanced Mode Settings")
        regex_layout = QFormLayout()
        self.line_regex = QLineEdit()
        regex_layout.addRow("Regex Pattern:", self.line_regex)
        regex_layout.addRow(QLabel("Use (...) to capture up to 8 numbers.\nEx: V1:(\\d+.*) V2:(\\d+.*) ..."))
        self.regex_group.setLayout(regex_layout)
        main_layout.addWidget(self.regex_group)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.apply_and_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self.radio_simple.toggled.connect(self.update_ui_state)
        self.radio_regex.toggled.connect(self.update_ui_state)
        self.radio_binary.toggled.connect(self.update_ui_state)
        self.radio_packet.toggled.connect(self.update_ui_state)

    def update_ui_state(self):
        is_simple_mode = self.radio_simple.isChecked()
        is_regex_mode = self.radio_regex.isChecked()
        self.simple_group.setEnabled(is_simple_mode)
        self.regex_group.setEnabled(is_regex_mode)

    def load_settings(self):
        mode = self.config.get("mode", "simple")
        
        if mode == "regex":
            self.radio_regex.setChecked(True)
        elif mode == "binary":
            self.radio_binary.setChecked(True)
        elif mode == "packet":
            self.radio_packet.setChecked(True)
        else: # "simple" veya tanımsızsa
            self.radio_simple.setChecked(True)
            
        self.line_delimiter.setText(self.config.get("delimiter", ","))
        columns = self.config.get("columns", list(range(1, 9)))
        self.line_columns.setText(", ".join(map(str, columns)))
        self.line_regex.setText(self.config.get("regex_pattern", ""))
        self.update_ui_state()

    def apply_and_accept(self):
        new_config = {}
        if self.radio_simple.isChecked():
            new_config["mode"] = "simple"
            new_config["delimiter"] = self.line_delimiter.text()
            try:
                columns_str = self.line_columns.text().strip()
                parts = [p.strip() for p in columns_str.split(',') if p.strip()]
                if not parts or len(parts) > 8:
                    raise ValueError("Please enter between 1 and 8 column numbers.")
                new_config["columns"] = [int(p) for p in parts]
            except ValueError as e:
                QMessageBox.warning(self, "Input Error", f"Invalid column format: {e}\nPlease use numbers separated by commas.")
                return

        elif self.radio_regex.isChecked():
            new_config["mode"] = "regex"
            new_config["regex_pattern"] = self.line_regex.text()
            if not new_config["regex_pattern"]:
                QMessageBox.warning(self, "Input Error", "Regex pattern cannot be empty.")
                return

        elif self.radio_binary.isChecked():
            new_config["mode"] = "binary"

        elif self.radio_packet.isChecked():
            new_config["mode"] = "packet"
        
        # Sinyali yeni ve temiz konfigürasyon ile gönder
        self.settingsApplied.emit(new_config)
        self.accept()