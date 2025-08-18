from PyQt5.QtWidgets import (
    QApplication, QWidget, QLineEdit, QTextEdit, QPushButton, QMainWindow, QVBoxLayout, QSizePolicy,
    QHBoxLayout, QComboBox, QLabel, QGridLayout, QDialog, QMessageBox, QStyle, QInputDialog,  QMenu,
    QCheckBox, QSpinBox, QGroupBox, QFileDialog, QTabWidget, QListWidget, QListWidgetItem
)
from PyQt5.QtSerialPort import QSerialPortInfo, QSerialPort
from PyQt5.QtCore import QIODevice, pyqtSignal, Qt
from PyQt5.QtGui import QIcon 
from PyQt5.QtWebEngineWidgets import QWebEngineView 
from MapTabWidget import MapTabWidget
from NmeaSimulator import NmeaSimulator

import sys
import datetime
import os
import stat 
import re 
from DataParserDialog import DataParserDialog

try:
    import pyqtgraph as pg
    import pyqtgraph.exporters
except ImportError:
    print("Warning: pyqtgraph library not found. Graph features will be disabled.")
    pg = None

import paramiko 
import time   
from PyQt5.QtCore import QThread, pyqtSignal, QMutex  
class SSHWorker(QThread):
    # Sinyaller: Ana uygulamaya geri bildirim göndermek için
    output_received = pyqtSignal(str) # Uzak sunucudan gelen çıktıları iletmek için
    connection_established = pyqtSignal(bool, str) # Bağlantı durumu ve mesajı iletmek için
    error_occurred = pyqtSignal(str) # Hata mesajlarını iletmek için

    def __init__(self, host, port, username, password, parent=None):
        super().__init__(parent)
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._running = True # Thread'in çalışıp çalışmadığını kontrol etmek için bayrak
        self.ssh_client = None # Paramiko SSH istemcisi
        self.channel = None    # SSH kanalı (kabuk)
        self.mutex = QMutex()  # Thread güvenliği için mutex

    def run(self):
        """Thread başladığında çalışacak ana metot."""
        try:
            self.ssh_client = paramiko.SSHClient()
            # Güvenilmeyen ana bilgisayar anahtarlarını otomatik ekle.
            # Gerçek uygulamalarda bu politikayı daha dikkatli yönetmek gerekir (örneğin bilinen ana bilgisayar listesi).
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # SSH sunucusuna bağlanma
            self.ssh_client.connect(hostname=self._host, port=self._port,
                                    username=self._username, password=self._password,
                                    timeout=15) # Bağlantı zaman aşımı (saniye)

            self.connection_established.emit(True, "SSH connection established.")

            # Etkileşimli bir kabuk (shell) açma
            self.channel = self.ssh_client.invoke_shell()
            self.channel.settimeout(0.1) # Kanal okuma zaman aşımı (kısa bir bekleme)

            # Veri okuma döngüsü
            while self._running:
                # Kanaldan veri gelip gelmediğini kontrol et
                if self.channel and self.channel.recv_ready():
                    data = self.channel.recv(4096) # 4KB veri oku
                    # Gelen veriyi UTF-8'e dönüştür ve ana uygulamaya gönder
                    self.output_received.emit(data.decode('utf-8', errors='ignore'))
                else:
                    time.sleep(0.01) # CPU kullanımını düşürmek için kısa bekleme

        except paramiko.AuthenticationException:
            self.error_occurred.emit("Authentication failed. Incorrect username or password.")
            self.connection_established.emit(False, "Authentication failed.")
        except paramiko.SSHException as e:
            self.error_occurred.emit(f"SSH error: {e}")
            self.connection_established.emit(False, f"SSH error: {e}")
        except Exception as e:
            self.error_occurred.emit(f"An unexpected error occurred: {e}")
            self.connection_established.emit(False, f"Unexpected error: {e}")
        finally:
            self.disconnect_ssh() # Thread sonlandığında veya hata oluştuğunda bağlantıyı kes

    def send_command(self, command):
        """SSH kanalına komut gönderir."""
        self.mutex.lock() # Yazma işlemi sırasında kilit (thread güvenliği için)
        if self.channel and not self.channel.closed:
            try:
                # Komutu ve yeni satır karakterini (Enter) gönder
                self.channel.send(command + '\n')
            except Exception as e:
                self.error_occurred.emit(f"Failed to send command: {e}")
        self.mutex.unlock()

    def disconnect_ssh(self):
        """SSH bağlantısını ve kanalı kapatır."""
        self.mutex.lock()
        self._running = False # Okuma döngüsünü durdur
        if self.channel:
            try:
                self.channel.close()
            except Exception as e:
                self.error_occurred.emit(f"Error closing SSH channel: {e}") # Hata logu eklendi
            self.channel = None
        if self.ssh_client:
            try:
                self.ssh_client.close()
            except Exception as e:
                self.error_occurred.emit(f"Error closing SSH client: {e}") # Hata logu eklendi
            self.ssh_client = None
        self.output_received.emit("SSH disconnected.") # Bağlantı kesildi mesajı gönder
        self.connection_established.emit(False, "SSH disconnected.") # Bağlantı durumunu bildir
        self.mutex.unlock()

    def stop(self):
        """Thread'in güvenli bir şekilde durmasını sağlar."""
        self._running = False
        self.disconnect_ssh() # Bağlantıyı hemen kes
        self.wait() # Thread'in sonlanmasını bekle

# --- LoginDialog Class ---
class LoginDialog(QDialog):
    loginSuccessful = pyqtSignal(str) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setFixedSize(300, 150)

        self.initUI()

        self.users = {
            "admin": "admin123",
            "user": "user123"
        }

    def initUI(self):
        layout = QVBoxLayout()

        form_layout = QGridLayout()
        
        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        form_layout.addWidget(self.username_label, 0, 0)
        form_layout.addWidget(self.username_input, 0, 1)

        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.password_label, 1, 0)
        form_layout.addWidget(self.password_input, 1, 1)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        self.login_button = QPushButton("Login")
        self.cancel_button = QPushButton("Cancel")
        self.guest_login_button = QPushButton("Login as Guest") # NEW: Guest Login Button
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.guest_login_button) # Add guest button
        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.login_button.clicked.connect(self.check_login)
        self.cancel_button.clicked.connect(self.reject)
        self.guest_login_button.clicked.connect(self.login_as_guest) # NEW: Connect guest login

        self.username_input.returnPressed.connect(self.check_login)
        self.password_input.returnPressed.connect(self.check_login)

    def check_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if username in self.users and self.users[username] == password:
            QMessageBox.information(self, "Login Successful", f"Welcome, {username}!")
            self.loginSuccessful.emit(username)
            self.accept()
        else:
            QMessageBox.warning(self, "Login Failed", "Incorrect username or password.")
            self.username_input.clear()
            self.password_input.clear()
            self.username_input.setFocus()

    def login_as_guest(self): # NEW: Method for guest login
        QMessageBox.information(self, "Login Successful", "Welcome, Guest!")
        self.loginSuccessful.emit("guest")
        self.accept()

# --- SettingsDialog Class ---
class SettingsDialog(QDialog):
    settingsChanged = pyqtSignal(int, int, QSerialPort.Parity, QSerialPort.StopBits)

    def __init__(self, parent=None, initial_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Serial Port Settings")
        self.setMinimumSize(300, 200)
        self.resize(400, 250)
        self.initUI(initial_settings)

    def initUI(self, initial_settings):
        main_layout = QVBoxLayout()
        settings_grid_layout = QGridLayout()

        labels = ["Baud Rate:", "Data Bits:", "Parity:", "Stop Bits:"]
        self.comboBaudRate = QComboBox()
        self.comboBaudRate.addItems(["9600", "19200", "38400", "57600", "115200"])

        self.comboDataBits = QComboBox()
        self.comboDataBits.addItems(["5", "6", "7", "8"])

        self.comboParity = QComboBox()
        self.comboParity.addItems(["No Parity", "Even Parity", "Odd Parity", "Mark Parity", "Space Parity"])

        self.comboStopBits = QComboBox()
        self.comboStopBits.addItems(["1", "1.5", "2"])

        combos = [self.comboBaudRate, self.comboDataBits, self.comboParity, self.comboStopBits]

        for i, label_text in enumerate(labels):
            label = QLabel(label_text)
            settings_grid_layout.addWidget(label, i, 0)
            settings_grid_layout.addWidget(combos[i], i, 1)

        main_layout.addLayout(settings_grid_layout)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Apply")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        self.ok_button.clicked.connect(self.accept_settings)
        self.cancel_button.clicked.connect(self.reject)

        if initial_settings:
            self.comboBaudRate.setCurrentText(str(initial_settings['baud_rate']))
            self.comboDataBits.setCurrentText(str(initial_settings['data_bits']))
            self.comboParity.setCurrentText(self.parity_enum_to_text(initial_settings['parity']))
            self.comboStopBits.setCurrentText(self.stop_bits_enum_to_text(initial_settings['stop_bits']))

    def accept_settings(self):
        baud_rate = int(self.comboBaudRate.currentText())
        data_bits = int(self.comboDataBits.currentText())
        parity = self.parity_text_to_enum(self.comboParity.currentText())
        stop_bits = self.stop_bits_text_to_enum(self.comboStopBits.currentText())
        self.settingsChanged.emit(baud_rate, data_bits, parity, stop_bits)
        self.accept()

    def parity_text_to_enum(self, text):
        return {
            "No Parity": QSerialPort.NoParity,
            "Even Parity": QSerialPort.EvenParity,
            "Odd Parity": QSerialPort.OddParity,
            "Mark Parity": QSerialPort.MarkParity,
            "Space Parity": QSerialPort.SpaceParity,
        }.get(text, QSerialPort.NoParity)

    def parity_enum_to_text(self, enum_val):
        return {
            QSerialPort.NoParity: "No Parity",
            QSerialPort.EvenParity: "Even Parity",
            QSerialPort.OddParity: "Odd Parity",
            QSerialPort.MarkParity: "Mark Parity",
            QSerialPort.SpaceParity: "Space Parity",
        }.get(enum_val, "No Parity")

    def stop_bits_text_to_enum(self, text):
        return {
            "1": QSerialPort.OneStop,
            "1.5": QSerialPort.OneAndHalfStop,
            "2": QSerialPort.TwoStop,
        }.get(text, QSerialPort.OneStop)

    def stop_bits_enum_to_text(self, enum_val):
        return {
            QSerialPort.OneStop: "1",
            QSerialPort.OneAndHalfStop: "1.5",
            QSerialPort.TwoStop: "2",
        }.get(enum_val, "1")

# --- MainWindow Class ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serialPort = QSerialPort()
        self.current_baud_rate = 9600
        self.current_data_bits = 8
        self.current_parity = QSerialPort.NoParity
        self.current_stop_bits = QSerialPort.OneStop
        self.received_buffer = ""
        self.x_data, self.y_data1, self.y_data2 = [], [], []
        self.time_index = 0

        self.recorded_lines = []

        self.terminal_command_history = []
        self.terminal_history_index = -1

        self.data_receiving = True

        self.user_role = "guest"
        self.is_logged_in = False
        
        self.parsing_config = {
            "mode": "simple",
            "delimiter": ",",
            "column1": 1,
            "column2": 2,
            "regex_pattern": r"(-?\d+\.?\d*)\D*(-?\d+\.?\d*)"
        }

        self.ssh_worker = None # SSHWorker nesnesini tutacak değişken
        self.ssh_command_history = [] # SSH terminal komut geçmişi
        self.ssh_history_index = -1 # SSH komut geçmişi indeksi
        self.plot_auto_range = True
        
        self.simulator = NmeaSimulator(self)

        self.initUI() 
        self.show_login_dialog()      

    # --- Login and Access Control Methods ---
    # MainWindow sınıfındaki show_login_dialog metodunu güncelleyin.
    def show_login_dialog(self):
        """Displays the login window when the application starts."""
        login_dialog = LoginDialog(self)
        
        #Login ekranının her zaman koyu tema olmasını sağlar
        self.apply_theme(True) 
        
        login_dialog.loginSuccessful.connect(self.handle_login_success)
        
        result = login_dialog.exec_()
        if result == QDialog.Accepted:
            self.showMaximized()
            # Login başarılı olduktan sonra ana pencerenin temasını checkbox'ın durumuna göre ayarla
            self.toggle_theme(self.theme_switch_checkbox.isChecked())
        else:
            QApplication.quit()
            
    def handle_login_success(self, username):
        """Called when login is successful, sets user role and applies access control."""
        if username == "admin":
            self.user_role = "admin"
            self.append_to_log("Logged in as Admin.", color='green')
        elif username == "user":
            self.user_role = "user"
            self.append_to_log(f"Logged in as User ({username}).", color='blue')
        else: # Guest login
            self.user_role = "guest"
            self.append_to_log("Logged in as Guest.", color='gray')
        
        self.is_logged_in = True
        self.apply_access_control()

    def apply_access_control(self):
        """Sets the visibility and enabled state of UI elements based on user role."""
        is_admin = (self.user_role == "admin")
        is_user = (self.user_role == "user")
        is_guest = (self.user_role == "guest")

        # Settings button only for admins
        self.pushButtonSettings.setVisible(is_admin)

        # Save Data and Export Plot only for admins
        self.pushButtonSaveData.setVisible(is_admin)
        if pg:
            self.pushButtonExportPlot.setVisible(is_admin)
        else:
            self.pushButtonExportPlot.setVisible(False) # pyqtgraph yoksa export butonu gizli

        # Save Terminal Log button only for admins
        self.pushButtonSaveTerminal.setVisible(is_admin)
        
        # Connect/Disconnect buttons (available for admin/user, not guest for initial connection)
        self.pushButtonConnect.setEnabled(is_admin or is_user)
        self.pushButtonDisconnect.setEnabled(self.serialPort.isOpen() and (is_admin or is_user))

        # Stop/Start and Reset buttons only for admins
        self.pushButtonStop.setVisible(is_admin)
        self.pushButtonReset.setVisible(is_admin)
        
        # Terminal tab only for admins
        terminal_index = self.tab_widget.indexOf(self.tab3)
        if terminal_index != -1:
            self.tab_widget.setTabVisible(terminal_index, is_admin)
            # Terminal girişi ve gönderme butonu sadece adminler ve seri port bağlıyken aktif olmalı
            self.terminalLineEdit.setEnabled(is_admin and self.serialPort.isOpen())
            self.terminalSendButton.setEnabled(is_admin and self.serialPort.isOpen())
            self.pushButtonSaveTerminal.setEnabled(is_admin and self.serialPort.isOpen())

        # ... apply_access_control fonksiyonu içinde ...
        ssh_index = self.tab_widget.indexOf(self.tab4)
        if ssh_index != -1:
            # 1. Kullanıcının SSH sekmesini görme yetkisi var mı?
            user_has_ssh_permission = is_admin or is_user
            self.tab_widget.setTabVisible(ssh_index, user_has_ssh_permission)

            # 2. Aktif bir SSH bağlantısı var mı?
            is_ssh_connected = self.ssh_worker and self.ssh_worker.isRunning()

            # 3. Arayüz elemanlarının durumunu yetki ve bağlantı durumuna göre ayarla
            is_ssh_connected = bool(self.ssh_worker and self.ssh_worker.isRunning())

            # Bağlantı başlatma kontrolleri (Giriş alanları ve Bağlan butonu):
            # Yetkisi varsa ve bağlı DEĞİLSE aktif olmalı.
            can_initiate_connection = user_has_ssh_permission and not is_ssh_connected
            self.sshHostInput.setEnabled(can_initiate_connection)
            self.sshPortInput.setEnabled(can_initiate_connection)
            self.sshUserInput.setEnabled(can_initiate_connection)
            self.sshPassInput.setEnabled(can_initiate_connection)
            self.sshConnectButton.setEnabled(can_initiate_connection)

            # Aktif bağlantı kontrolleri (Bağlantıyı Kes butonu ve Terminal):
            # Yetkisi varsa ve ZATEN bağlıysa aktif olmalı.
            can_use_terminal = user_has_ssh_permission and is_ssh_connected
            self.sshDisconnectButton.setEnabled(can_use_terminal)
            self.sshTerminalLineEdit.setEnabled(can_use_terminal)
            self.sshTerminalSendButton.setEnabled(can_use_terminal)

            # SFTP elemanlarının durumunu ayarla
            self.sftpPathLineEdit.setEnabled(can_use_terminal)
            self.sftpListFilesButton.setEnabled(can_use_terminal)
            self.sftpFileListWidget.setEnabled(can_use_terminal)

        map_index = self.tab_widget.indexOf(self.map_tab)
        if map_index != -1:
            user_has_map_permission = is_admin or is_user
            self.tab_widget.setTabVisible(map_index, user_has_map_permission)

        # Eğer o anki sekme erişim kontrolü nedeniyle görünmez hale geldiyse, ilk görünür sekmeye geç
        current_index = self.tab_widget.currentIndex()
        if not self.tab_widget.isTabVisible(current_index):
            found_visible_tab = False
            for i in range(self.tab_widget.count()):
                if self.tab_widget.isTabVisible(i):
                    self.tab_widget.setCurrentIndex(i)
                    found_visible_tab = True
                    break
            if not found_visible_tab:
                self.append_to_log("Warning: No tabs are visible for the current role!", color='red')
        # Grafiğe özel kontroller
        if pg:
            graph_controls_enabled = (is_admin or is_user)
            self.spin_x_from.setEnabled(graph_controls_enabled)
            self.spin_x_to.setEnabled(graph_controls_enabled)
            self.spin_y_from.setEnabled(graph_controls_enabled)
            self.spin_y_to.setEnabled(graph_controls_enabled)
            self.chk_curve1.setEnabled(graph_controls_enabled)
            self.chk_curve2.setEnabled(graph_controls_enabled)
            self.chk_show_legend.setEnabled(graph_controls_enabled)
            self.btn_apply_plot_settings.setEnabled(graph_controls_enabled)
    
    def convert_nmea_to_decimal(self, nmea_val, direction):
        """NMEA formatındaki (DDMM.MMMM) koordinatı ondalık dereceye çevirir."""
        try:
            degrees = int(float(nmea_val) / 100)
            minutes = float(nmea_val) % 100
            decimal_degrees = degrees + (minutes / 60)
            if direction in ['S', 'W']:
                decimal_degrees *= -1
            return decimal_degrees
        except (ValueError, IndexError):
            return None

    def parse_nmea_sentence(self, sentence):
        """Gelen bir NMEA cümlesini ayrıştırır ve haritayı günceller."""
        parts = sentence.split(',')
        
        # Sadece $GPRMC formatındaki, geçerli (A) verileri işle
        if len(parts) > 6 and parts[0] == '$GPRMC' and parts[2] == 'A':
            lat_nmea = parts[3]
            lat_dir = parts[4]
            lon_nmea = parts[5]
            lon_dir = parts[6]

            lat_decimal = self.convert_nmea_to_decimal(lat_nmea, lat_dir)
            lon_decimal = self.convert_nmea_to_decimal(lon_nmea, lon_dir)

            if lat_decimal is not None and lon_decimal is not None:
                # Harita sekmesindeki ilgili fonksiyonları çağır:
                # 1. İşaretçiyi hareket ettir
                self.map_tab.move_marker(lat_decimal, lon_decimal)
                # 2. Canlı rotaya yeni bir nokta ekle
                self.map_tab.add_point_to_live_route(lat_decimal, lon_decimal)

    def sftp_download_file(self):
        """Listeden seçili olan dosyayı indirir."""
        selected_items = self.sftpFileListWidget.selectedItems()
        if not selected_items:
            return # Seçili bir şey yoksa çık

        item_text = selected_items[0].text()
        if not item_text.startswith("[F]"):
            QMessageBox.warning(self, "Download Error", "Please select a file to download, not a directory.")
            return

        filename = item_text[4:] # "[F] " önekini kaldır
        remote_path = os.path.join(self.sftpPathLineEdit.text(), filename).replace("\\", "/")

        # Kullanıcıya nereye kaydedeceğini sor
        local_path, _ = QFileDialog.getSaveFileName(self, "Save File As", filename)
        if not local_path:
            return # Kullanıcı iptal etti

        try:
            sftp = self.ssh_worker.ssh_client.open_sftp()
            # İndirme işlemi
            sftp.get(remote_path, local_path)
            sftp.close()
            self.append_to_log(f"SFTP: File '{filename}' downloaded successfully.", color='green')
            QMessageBox.information(self, "Success", f"File '{filename}' downloaded to\n{local_path}")
        except Exception as e:
            self.append_to_log(f"SFTP Download Error: {e}", color='red')
            QMessageBox.critical(self, "Download Error", f"Could not download file.\nError: {e}")
  

    def show_sftp_context_menu(self, position):
        """SFTP dosya listesi için sağ tık menüsünü oluşturur ve gösterir."""
        menu = QMenu()
        selected_items = self.sftpFileListWidget.selectedItems()

        # Genel eylemler (her zaman görünür ama duruma göre aktif/pasif)
        upload_action = menu.addAction("Upload File Here")
        mkdir_action = menu.addAction("Create New Directory")
        refresh_action = menu.addAction("Refresh List")
        menu.addSeparator()

        if selected_items:
            item_text = selected_items[0].text()
            is_file = item_text.startswith("[F]")

            # Seçime özel eylemler
            download_action = menu.addAction("Download")
            rename_action = menu.addAction("Rename")
            delete_action = menu.addAction("Delete")

            download_action.setEnabled(is_file) # İndirme sadece dosya ise aktif

            # Sinyal bağlantıları
            download_action.triggered.connect(self.sftp_download_file)
            rename_action.triggered.connect(self.sftp_rename_item)
            delete_action.triggered.connect(self.sftp_delete_item)

        upload_action.triggered.connect(self.sftp_upload_file)
        mkdir_action.triggered.connect(self.sftp_create_directory)
        refresh_action.triggered.connect(self.list_sftp_files)

        # Menüyü farenin imlecinin olduğu yerde göster
        menu.exec_(self.sftpFileListWidget.mapToGlobal(position))

    def sftp_upload_file(self):
        """Kullanıcının seçtiği bir dosyayı sunucuya yükler."""
        local_path, _ = QFileDialog.getOpenFileName(self, "Select File to Upload")
        if not local_path:
            return # Kullanıcı iptal etti

        filename = os.path.basename(local_path)
        remote_path = os.path.join(self.sftpPathLineEdit.text(), filename).replace("\\", "/")

        try:
            sftp = self.ssh_worker.ssh_client.open_sftp()
            # Yükleme işlemi
            sftp.put(local_path, remote_path)
            sftp.close()
            self.append_to_log(f"SFTP: File '{filename}' uploaded successfully.", color='green')
            QMessageBox.information(self, "Success", f"File '{filename}' uploaded to\n{self.sftpPathLineEdit.text()}")
            self.list_sftp_files() # Listeyi yenile
        except Exception as e:
            self.append_to_log(f"SFTP Upload Error: {e}", color='red')
            QMessageBox.critical(self, "Upload Error", f"Could not upload file.\nError: {e}")

    def sftp_delete_item(self):
        """Listeden seçili olan dosya veya dizini siler."""
        selected_items = self.sftpFileListWidget.selectedItems()
        if not selected_items:
            return

        item_text = selected_items[0].text()
        is_dir = item_text.startswith("[D]")
        item_name = item_text[4:]
        remote_path = os.path.join(self.sftpPathLineEdit.text(), item_name).replace("\\", "/")

        reply = QMessageBox.question(self, 'Confirm Deletion',
                                    f"Are you sure you want to permanently delete '{item_name}'?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return

        try:
            sftp = self.ssh_worker.ssh_client.open_sftp()
            if is_dir:
                sftp.rmdir(remote_path) # Dizin silme
            else:
                sftp.remove(remote_path) # Dosya silme
            sftp.close()
            self.append_to_log(f"SFTP: Item '{item_name}' deleted successfully.", color='orange')
            self.list_sftp_files() # Listeyi yenile
        except Exception as e:
            # rmdir boş olmayan dizin için hata verir, bu yaygın bir durumdur.
            self.append_to_log(f"SFTP Delete Error: {e}", color='red')
            QMessageBox.critical(self, "Delete Error", f"Could not delete item.\nError: {e}\n\n(Note: Directories must be empty to be deleted).")

    def sftp_create_directory(self):
        """Sunucuda yeni bir dizin oluşturur."""
        dir_name, ok = QInputDialog.getText(self, 'Create New Directory', 'Enter directory name:')
        if not (ok and dir_name):
            return # Kullanıcı iptal etti veya boş isim girdi

        remote_path = os.path.join(self.sftpPathLineEdit.text(), dir_name).replace("\\", "/")

        try:
            sftp = self.ssh_worker.ssh_client.open_sftp()
            sftp.mkdir(remote_path)
            sftp.close()
            self.append_to_log(f"SFTP: Directory '{dir_name}' created.", color='green')
            self.list_sftp_files() # Listeyi yenile
        except Exception as e:
            self.append_to_log(f"SFTP MkDir Error: {e}", color='red')
            QMessageBox.critical(self, "Creation Error", f"Could not create directory.\nError: {e}")

    def sftp_rename_item(self):
        """Seçili dosya veya dizini yeniden adlandırır."""
        selected_items = self.sftpFileListWidget.selectedItems()
        if not selected_items:
            return

        old_name = selected_items[0].text()[4:]
        new_name, ok = QInputDialog.getText(self, 'Rename Item', 'Enter new name:', text=old_name)

        if not (ok and new_name and new_name != old_name):
            return

        old_path = os.path.join(self.sftpPathLineEdit.text(), old_name).replace("\\", "/")
        new_path = os.path.join(self.sftpPathLineEdit.text(), new_name).replace("\\", "/")

        try:
            sftp = self.ssh_worker.ssh_client.open_sftp()
            sftp.rename(old_path, new_path)
            sftp.close()
            self.append_to_log(f"SFTP: Renamed '{old_name}' to '{new_name}'.", color='blue')
            self.list_sftp_files()
        except Exception as e:
            self.append_to_log(f"SFTP Rename Error: {e}", color='red')
            QMessageBox.critical(self, "Rename Error", f"Could not rename item.\nError: {e}")

    def toggle_theme(self, checked):
        """Checkbox'ın durumuna göre temayı değiştiren anahtar fonksiyon."""
        # 'checked' True ise (yani kutu işaretliyse) -> Açık tema (is_dark_mode = False)
        # 'checked' False ise (yani kutu boşsa) -> Koyu tema (is_dark_mode = True)
        is_dark = not checked
        self.apply_theme(is_dark)
        
        # Checkbox'ın yazısını da duruma göre güncelle
        self.theme_switch_checkbox.setText("Koyu Temaya Geç" if checked else "Açık Temaya Geç")

    def apply_theme(self, is_dark_mode):
        """Stil kodlarını içeren ve temayı tüm uygulamaya yükleyen ana fonksiyon."""
        # Dracula Teması (Koyu Mod) için stil kodları
        dark_stylesheet = """
            QWidget {
                background-color: #282a36; color: #f8f8f2; font-family: 'Segoe UI'; font-size: 10pt;
            }
            QGroupBox {
                border: 1px solid #44475a; border-radius: 8px; margin-top: 10px; font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top center; padding: 0 10px;
                background-color: #282a36; color: #bd93f9;
            }
            QTextEdit, QLineEdit, QListWidget, QSpinBox, QComboBox {
                background-color: #44475a; border: 1px solid #6272a4; border-radius: 5px;
                padding: 5px; color: #f8f8f2;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #bd93f9; }
            QPushButton {
                background-color: #bd93f9; color: #f8f8f2; border: none; padding: 8px 15px;
                border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #caa9ff; }
            QPushButton:pressed { background-color: #aa87dd; }
            QPushButton:disabled { background-color: #44475a; color: #6272a4; }
            QPushButton:checked { background-color: #ff79c6; } /* Stop butonu gibi checkable butonlar için */
            QTabBar::tab {
                background: #44475a; border: none; padding: 8px 12px;
                border-top-left-radius: 5px; border-top-right-radius: 5px;
                color: #6272a4; font-weight: bold;
            }
            QTabBar::tab:selected { background: #282a36; color: #ff79c6; border-top: 2px solid #ff79c6; }
            QTabWidget::pane { border: 1px solid #44475a; border-top: none; }
        """        
        # Basit bir Açık Tema (Qt'nin varsayılan stili)
        light_stylesheet = ""

        app = QApplication.instance()
        if is_dark_mode:
            app.setStyleSheet(dark_stylesheet)
        else:
            app.setStyleSheet(light_stylesheet) # "" boş stil vermek varsayılana döndürür

        if pg and hasattr(self, 'plot_widget'):
            if is_dark_mode:
                self.plot_widget.setBackground('#282a36')
                axis_pen = pg.mkPen(color='#f8f8f2')
            else:
                self.plot_widget.setBackground('w')
                axis_pen = pg.mkPen(color='k')
            
            self.plot_widget.getAxis('bottom').setPen(axis_pen)
            self.plot_widget.getAxis('left').setPen(axis_pen)
            self.plot_widget.getAxis('bottom').setTextPen(axis_pen)
            self.plot_widget.getAxis('left').setTextPen(axis_pen)

    def initUI(self):
        """Kullanıcı arayüzünü başlatır. (Yeniden Düzenlenmiş Versiyon)"""
        self.setWindowTitle("Serial Port & SSH Interface")
        self.setGeometry(100, 100, 1200, 800)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # Ana layout sadece sekmeleri içerecek
        main_layout = QVBoxLayout(central_widget)
        style = QApplication.style()

        # Toolbar Odaklı Üst Panel ---
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False) # Toolbar'ın yerinden oynamasını engelle

        # Grup 1: Port Kontrolleri
        toolbar.addWidget(QLabel(" Port: "))
        self.comboSeriPortList = QComboBox()
        self.comboSeriPortList.setMinimumWidth(120)
        toolbar.addWidget(self.comboSeriPortList)
        self.listSerialPorts()

        self.pushButtonConnect = QPushButton("Connect")
        self.pushButtonConnect.setIcon(style.standardIcon(QStyle.SP_DialogApplyButton))
        self.pushButtonDisconnect = QPushButton("Disconnect")
        self.pushButtonDisconnect.setIcon(style.standardIcon(QStyle.SP_DialogCancelButton))
        self.pushButtonDisconnect.setEnabled(False)
        toolbar.addWidget(self.pushButtonConnect)
        toolbar.addWidget(self.pushButtonDisconnect)
        toolbar.addSeparator()

        # Grup 2: Ayarlar
        self.pushButtonSettings = QPushButton("Settings")
        self.pushButtonSettings.setIcon(style.standardIcon(QStyle.SP_FileDialogDetailedView))
        self.pushButtonParserSettings = QPushButton("Data Parser")
        self.pushButtonParserSettings.setIcon(style.standardIcon(QStyle.SP_ComputerIcon))
        toolbar.addWidget(self.pushButtonSettings)
        toolbar.addWidget(self.pushButtonParserSettings)
        toolbar.addSeparator()

        # Grup 3: Veri ve Kontrol
        self.pushButtonSaveData = QPushButton("Save Data")
        self.pushButtonSaveData.setIcon(style.standardIcon(QStyle.SP_DialogSaveButton))
        self.pushButtonSaveData.setEnabled(False)
        
        self.pushButtonExportPlot = QPushButton("Export Plot")
        self.pushButtonExportPlot.setIcon(style.standardIcon(QStyle.SP_FileIcon))
        if not pg: self.pushButtonExportPlot.setEnabled(False)
        
        self.pushButtonStop = QPushButton("Stop")
        self.pushButtonStop.setIcon(style.standardIcon(QStyle.SP_MediaStop)); self.pushButtonStop.setCheckable(True)
        self.pushButtonStop.setEnabled(False)

        self.pushButtonReset = QPushButton("Reset")
        self.pushButtonReset.setIcon(style.standardIcon(QStyle.SP_TrashIcon))

        self.pushButtonSaveTerminal = QPushButton("Save Terminal Log")
        self.pushButtonSaveTerminal.setIcon(style.standardIcon(QStyle.SP_FileIcon))
        self.pushButtonSaveTerminal.setEnabled(False)
        
        toolbar.addWidget(self.pushButtonSaveData)
        toolbar.addWidget(self.pushButtonExportPlot)
        toolbar.addWidget(self.pushButtonStop)
        toolbar.addWidget(self.pushButtonReset)
        toolbar.addWidget(self.pushButtonSaveTerminal)

        # Toolbar'ın sağına yaslanacak elemanlar için boşluk
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
        
        # Grup 4: Arayüz ve Çıkış
        self.theme_switch_checkbox = QCheckBox("Açık Temaya Geç")
        self.theme_switch_checkbox.setChecked(False) # Başlangıçta Koyu Tema (işaretsiz)
        toolbar.addWidget(self.theme_switch_checkbox)
        
        self.pushButtonLogout = QPushButton("Logout")
        self.pushButtonLogout.setIcon(style.standardIcon(QStyle.SP_DialogCloseButton))
        toolbar.addWidget(self.pushButtonLogout)

        # --- Sekmeler (Tab Widget) ---
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget) # Ana layout'a sadece tab widget'ı ekliyoruz

        # Tab-1: Received Data Tab (Raw Data and System Logs)
        self.tab1 = QWidget()
        self.tab_widget.addTab(self.tab1, "Received Data(Log)")
        tab1_layout = QVBoxLayout(self.tab1)
        self.textEditReceiveData = QTextEdit()
        self.textEditReceiveData.setReadOnly(True)
        font_log = self.textEditReceiveData.font()
        font_log.setFamily("Consolas")
        font_log.setPointSize(9)
        self.textEditReceiveData.setFont(font_log)
        tab1_layout.addWidget(self.textEditReceiveData)

        # Tab-2: Graph Tab
        self.tab2 = QWidget()
        self.tab_widget.addTab(self.tab2, "Graph")
        tab2_layout = QGridLayout(self.tab2)

        if pg:
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground('w')
            self.plot_widget.showGrid(x=True, y=True)
            self.plot_widget.setTitle("Real-time Data Plot")
            self.plot_widget.setLabel('bottom', "Time Index")
            self.plot_widget.setLabel('left', "Value")
            
            self.curve1 = self.plot_widget.plot(pen=pg.mkPen('r', width=2), name="Value-1",
                                                    symbol='o', symbolSize=7, symbolBrush=(255, 0, 0, 200), symbolPen='w')
            self.curve2 = self.plot_widget.plot(pen=pg.mkPen('c', width=2), name="Value-2",
                                                    symbol='t', symbolSize=7, symbolBrush=(0, 255, 255, 200), symbolPen='w')

            tab2_layout.addWidget(self.plot_widget, 0, 0, 2, 3)

            # Graph Control Panel
            control_layout = QVBoxLayout()
            control_widget = QWidget()
            control_widget.setLayout(control_layout)
            control_widget.setFixedWidth(200)

            self.chk_curve1 = QCheckBox("Value-1")
            self.chk_curve2 = QCheckBox("Value-2")
            self.chk_curve1.setChecked(True)
            self.chk_curve2.setChecked(True)
            self.chk_curve1.stateChanged.connect(lambda s: self.curve1.setVisible(s == Qt.Checked))
            self.chk_curve2.stateChanged.connect(lambda s: self.curve2.setVisible(s == Qt.Checked))

            group_curve_visibility = QGroupBox("Graph Visibility")
            group_curve_layout = QVBoxLayout()
            group_curve_layout.addWidget(self.chk_curve1)
            group_curve_layout.addWidget(self.chk_curve2)
            group_curve_visibility.setLayout(group_curve_layout)

            control_layout.addWidget(group_curve_visibility)

            self.spin_x_from = QSpinBox()
            self.spin_x_from.setValue(0)
            self.spin_x_to = QSpinBox()
            self.spin_x_to.setValue(100)
            self.spin_y_from = QSpinBox()
            self.spin_y_from.setValue(0)
            self.spin_y_to = QSpinBox()
            self.spin_y_to.setValue(100)
            for spin in [self.spin_x_from, self.spin_x_to, self.spin_y_from, self.spin_y_to]:
                spin.setRange(-1000, 10000) # Daha geniş aralıklar için
            
            control_layout.addWidget(QLabel("X-Axis From:"))
            control_layout.addWidget(self.spin_x_from)
            control_layout.addWidget(QLabel("X-Axis To:"))
            control_layout.addWidget(self.spin_x_to)
            control_layout.addWidget(QLabel("Y-Axis From:"))
            control_layout.addWidget(self.spin_y_from)
            control_layout.addWidget(QLabel("Y-Axis To:"))
            control_layout.addWidget(self.spin_y_to)

            self.chk_show_legend = QCheckBox("Show Legend")
            self.chk_show_legend.setChecked(True)
            self.btn_apply_plot_settings = QPushButton("Apply")
            self.btn_apply_plot_settings.clicked.connect(self.apply_plot_settings)
            control_layout.addWidget(self.chk_show_legend)
            control_layout.addWidget(self.btn_apply_plot_settings)
            control_layout.addStretch()

            tab2_layout.addWidget(control_widget, 0, 3, 2, 1)
        else: # pg yoksa graph sekmesine uyarı 
            no_graph_label = QLabel("PyQtGraph library not found. Graph functionality is disabled.")
            no_graph_label.setAlignment(Qt.AlignCenter)
            tab2_layout.addWidget(no_graph_label, 0, 0, 2, 4)

        # Tab-3: Terminal Tab (Sending Commands and Viewing Responses)
        self.tab3 = QWidget()
        self.tab_widget.addTab(self.tab3, "Terminal")
        tab3_layout = QVBoxLayout(self.tab3)
        
        self.terminalTextEdit = QTextEdit()
        self.terminalTextEdit.setReadOnly(True)
        font_term = self.terminalTextEdit.font()
        font_term.setFamily("Consolas")
        font_term.setPointSize(10)
        self.terminalTextEdit.setFont(font_term)
        tab3_layout.addWidget(self.terminalTextEdit)

        terminal_send_layout = QHBoxLayout()
        self.terminalLineEdit = QLineEdit()
        self.terminalLineEdit.setPlaceholderText("Enter command...")
        self.terminalLineEdit.keyPressEvent = self.terminal_lineEdit_key_press_event
        
        self.terminalSendButton = QPushButton("Send")
        self.terminalSendButton.setEnabled(False) # Başlangıçta devre dışı
        
        terminal_send_layout.addWidget(self.terminalLineEdit)
        terminal_send_layout.addWidget(self.terminalSendButton)
        tab3_layout.addLayout(terminal_send_layout)

        # Tab-4: SSH
        self.tab4 = QWidget()
        self.tab_widget.addTab(self.tab4, "SSH")

        # Map Tab (Harita Sekmesi)
        self.map_tab = MapTabWidget(self) # Ana pencereyi referans olarak veriyoruz
        self.tab_widget.addTab(self.map_tab, "Map")
        
        # SSH sekmesini dikey yerine yatay olarak ikiye böl
        ssh_main_layout = QHBoxLayout(self.tab4)
 
        # SOL TARAF: Bağlantı ve Terminal
        ssh_left_panel = QWidget()
        ssh_left_layout = QVBoxLayout(ssh_left_panel)
        ssh_left_panel.setMaximumWidth(450)

        # SSH Bağlantı Ayarları Grubu
        ssh_settings_group = QGroupBox("SSH Connection")
        ssh_settings_layout = QGridLayout()
        ssh_settings_layout.addWidget(QLabel("Host/IP:"), 0, 0)
        self.sshHostInput = QLineEdit("192.168.1.1")
        ssh_settings_layout.addWidget(self.sshHostInput, 0, 1)
        ssh_settings_layout.addWidget(QLabel("Port:"), 1, 0)
        self.sshPortInput = QSpinBox()
        self.sshPortInput.setRange(1, 65535); self.sshPortInput.setValue(22)
        ssh_settings_layout.addWidget(self.sshPortInput, 1, 1)
        ssh_settings_layout.addWidget(QLabel("Username:"), 2, 0)
        self.sshUserInput = QLineEdit("root")
        ssh_settings_layout.addWidget(self.sshUserInput, 2, 1)
        ssh_settings_layout.addWidget(QLabel("Password:"), 3, 0)
        self.sshPassInput = QLineEdit()
        self.sshPassInput.setEchoMode(QLineEdit.Password)
        ssh_settings_layout.addWidget(self.sshPassInput, 3, 1)
        ssh_settings_group.setLayout(ssh_settings_layout)
        
        # SSH Bağlan/Kes Butonları
        ssh_buttons_layout = QHBoxLayout()
        self.sshConnectButton = QPushButton("Connect")
        self.sshDisconnectButton = QPushButton("Disconnect")
        self.sshDisconnectButton.setEnabled(False)
        ssh_buttons_layout.addWidget(self.sshConnectButton)
        ssh_buttons_layout.addWidget(self.sshDisconnectButton)

        # SSH Terminal Çıktı Alanı
        self.sshTerminalTextEdit = QTextEdit()
        self.sshTerminalTextEdit.setReadOnly(True)
        font_ssh_term = self.sshTerminalTextEdit.font()
        font_ssh_term.setFamily("Consolas")
        font_ssh_term.setPointSize(10)
        self.sshTerminalTextEdit.setFont(font_ssh_term)
        
        # SSH Komut Giriş Alanı
        ssh_send_layout = QHBoxLayout()
        self.sshTerminalLineEdit = QLineEdit()
        self.sshTerminalLineEdit.setPlaceholderText("Enter SSH command...")
        self.sshTerminalLineEdit.keyPressEvent = self.ssh_terminal_lineEdit_key_press_event
        self.sshTerminalSendButton = QPushButton("Send")
        ssh_send_layout.addWidget(self.sshTerminalLineEdit)
        ssh_send_layout.addWidget(self.sshTerminalSendButton)
        
        ssh_left_layout.addWidget(ssh_settings_group)
        ssh_left_layout.addLayout(ssh_buttons_layout)
        ssh_left_layout.addWidget(self.sshTerminalTextEdit)
        ssh_left_layout.addLayout(ssh_send_layout)

        # SAĞ TARAF: SFTP Dosya Tarayıcısı
        sftp_right_panel = QGroupBox("SFTP File Browser")
        sftp_layout = QVBoxLayout(sftp_right_panel)

        sftp_button_layout = QHBoxLayout()
        self.sftpUploadButton = QPushButton("Upload File")
        self.sftpUploadButton.setIcon(style.standardIcon(QStyle.SP_ArrowUp))
        self.sftpMkdirButton = QPushButton("New Folder")
        self.sftpMkdirButton.setIcon(style.standardIcon(QStyle.SP_FileDialogNewFolder))

        sftp_button_layout.addWidget(self.sftpUploadButton)
        sftp_button_layout.addWidget(self.sftpMkdirButton)
        sftp_button_layout.addStretch()

        sftp_path_layout = QHBoxLayout()
        sftp_path_layout.addWidget(QLabel("Path:"))
        self.sftpPathLineEdit = QLineEdit("/")
        self.sftpPathLineEdit.setPlaceholderText("Enter path and press Enter")
        sftp_path_layout.addWidget(self.sftpPathLineEdit)
        
        self.sftpListFilesButton = QPushButton("List Files")
        sftp_path_layout.addWidget(self.sftpListFilesButton)
        
        self.sftpFileListWidget = QListWidget()
        from PyQt5.QtGui import QFont
        self.sftpFileListWidget.setFont(QFont("Consolas", 10))
        
        self.sftpFileListWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        sftp_layout.addLayout(sftp_button_layout)
        sftp_layout.addLayout(sftp_path_layout)
        sftp_layout.addWidget(self.sftpFileListWidget)
        
        ssh_main_layout.addWidget(ssh_left_panel)
        ssh_main_layout.addWidget(sftp_right_panel)

        # --- Sinyal / Slot Bağlantıları ---
        self.pushButtonConnect.clicked.connect(self.portConnect)
        self.pushButtonDisconnect.clicked.connect(self.portDisconnect)
        self.sftpUploadButton.clicked.connect(self.sftp_upload_file)
        self.sftpMkdirButton.clicked.connect(self.sftp_create_directory)
        self.sftpFileListWidget.customContextMenuRequested.connect(self.show_sftp_context_menu)
        self.pushButtonSettings.clicked.connect(self.showSettingsDialog)
        self.pushButtonParserSettings.clicked.connect(self.showDataParserDialog)
        self.pushButtonSaveData.clicked.connect(self.save_data_to_file)
        if pg: self.pushButtonExportPlot.clicked.connect(self.export_plot)
        self.pushButtonStop.clicked.connect(self.toggle_data_receiving)
        self.pushButtonReset.clicked.connect(self.reset_data)
        self.pushButtonSaveTerminal.clicked.connect(self.save_terminal_data_to_file)
        self.theme_switch_checkbox.toggled.connect(self.toggle_theme)
        self.pushButtonLogout.clicked.connect(self.logout_and_show_login)
        self.serialPort.readyRead.connect(self.portDataReceived)
        self.terminalSendButton.clicked.connect(self.portSendData)
        self.terminalLineEdit.returnPressed.connect(self.portSendData)
        self.sshConnectButton.clicked.connect(self.connect_ssh)
        self.sshDisconnectButton.clicked.connect(self.disconnect_ssh)
        self.sshTerminalSendButton.clicked.connect(self.send_ssh_command)
        self.sshTerminalLineEdit.returnPressed.connect(self.send_ssh_command)
        self.sftpListFilesButton.clicked.connect(self.list_sftp_files)
        self.sftpPathLineEdit.returnPressed.connect(self.list_sftp_files)
        self.sftpFileListWidget.itemDoubleClicked.connect(self.handle_sftp_item_double_click)

        self.apply_access_control()
        self.toggle_theme(self.theme_switch_checkbox.isChecked())
    # --- SFTP Metotları ---
    def list_sftp_files(self):
        """SFTP üzerinden belirtilen yoldaki dosyaları ve dizinleri listeler."""
        if not (self.ssh_worker and self.ssh_worker.isRunning() and self.ssh_worker.ssh_client):
            QMessageBox.warning(self, "SFTP Error", "Please establish an SSH connection first.")
            return

        path = self.sftpPathLineEdit.text().strip()
        if not path:
            path = "/"
            self.sftpPathLineEdit.setText(path)

        self.sftpFileListWidget.clear()
        self.sftpFileListWidget.addItem("Loading...") # Kullanıcıya geri bildirim

        try:
            sftp = self.ssh_worker.ssh_client.open_sftp()
            
            files = []
            dirs = []
            for attr in sftp.listdir_attr(path):
                if stat.S_ISDIR(attr.st_mode):
                    dirs.append(attr.filename)
                else:
                    files.append(attr.filename)
            sftp.close()

            self.sftpFileListWidget.clear()

            if path != '/':
                item = QListWidgetItem("..")
                # İkon veya renk eklenebilir
                self.sftpFileListWidget.addItem(item)
            
            # Önce dizinleri sıralı ekle
            for dirname in sorted(dirs):
                item = QListWidgetItem(f"[D] {dirname}")
                self.sftpFileListWidget.addItem(item)
            
            # Sonra dosyaları sıralı ekle
            for filename in sorted(files):
                item = QListWidgetItem(f"[F] {filename}")
                self.sftpFileListWidget.addItem(item)

        except Exception as e:
            self.sftpFileListWidget.clear()
            self.sftpFileListWidget.addItem(f"Error: {e}")
            QMessageBox.critical(self, "SFTP Error", f"Could not list directory '{path}'.\nError: {e}")
    
    def update_plot_data(self, v1, v2):
        if not pg: return
        self.x_data.append(self.time_index)
        self.y_data1.append(v1)
        self.y_data2.append(v2)
        self.time_index += 1
        max_points = 200
        if len(self.x_data) > max_points:
            self.x_data = self.x_data[-max_points:]
            self.y_data1 = self.y_data1[-max_points:]
            self.y_data2 = self.y_data2[-max_points:]

        self.curve1.setVisible(self.chk_curve1.isChecked())
        self.curve2.setVisible(self.chk_curve2.isChecked())

        self.curve1.setData(self.x_data, self.y_data1)
        self.curve2.setData(self.x_data, self.y_data2)

        if self.plot_auto_range:
            # Otomatik kaydırma mantığı
            self.plot_widget.setXRange(max(0, self.time_index - max_points), self.time_index)
 
            if self.y_data1 or self.y_data2:
                 min_y = min(self.y_data1 + self.y_data2)
                 max_y = max(self.y_data1 + self.y_data2)
                 self.plot_widget.setYRange(min_y - 5, max_y + 5) 

    def logout_and_show_login(self):
        """Disconnects all sessions, resets data, and returns to the login dialog."""
        # 1. Aktif bağlantıları güvenli bir şekilde kapat
        if self.serialPort.isOpen():
            self.portDisconnect()
        if self.ssh_worker and self.ssh_worker.isRunning():
            self.disconnect_ssh()
        
        # 2. Tüm verileri ve geçmişi temizle
        self.reset_data()
        
        # 3. Kullanıcı oturum durumunu sıfırla
        self.is_logged_in = False
        self.user_role = "guest"
        
        # 4. Pencere başlığını orijinal haline getir
        self.setWindowTitle("Serial Port & SSH Interface")
        
        # 5. Ana pencereyi gizle
        self.hide()
        
        # 6. Giriş diyalogunu tekrar göster
        self.show_login_dialog()

    def handle_sftp_item_double_click(self, item):
        """SFTP listesindeki bir öğeye çift tıklandığında gezinmeyi sağlar."""
        current_path = self.sftpPathLineEdit.text().strip()
        item_text = item.text()
        
        # Eğer "Loading..." veya "Error" mesajı varsa işlem yapma
        if item_text.startswith("Loading") or item_text.startswith("Error"):
            return
            
        new_path = ""

        if item_text == "..":
            # Bir üst dizine git
            new_path = os.path.dirname(current_path.rstrip('/'))
            if not new_path: new_path = "/"
        elif item_text.startswith("[D]"):
            # Bir alt dizine gir
            dir_name = item_text[4:] # "[D] " önekini kaldır
            if current_path.endswith('/'):
                new_path = current_path + dir_name
            else:
                new_path = current_path + '/' + dir_name
        
        if new_path:
            self.sftpPathLineEdit.setText(new_path)
            self.list_sftp_files() # Yeni yolu listele

    # --- SSH Metotları ---
    def connect_ssh(self):
        """SSHWorker'ı başlatır ve SSH bağlantısını kurmaya çalışır."""
        host = self.sshHostInput.text().strip()
        port = self.sshPortInput.value()
        username = self.sshUserInput.text().strip()
        password = self.sshPassInput.text() 

        if not host:
            QMessageBox.warning(self, "SSH Connection", "Host/IP cannot be empty.")
            self.append_to_log("SSH connection failed: Host/IP is empty.", color='red')
            return
        if not username:
            QMessageBox.warning(self, "SSH Connection", "Username cannot be empty.")
            self.append_to_log("SSH connection failed: Username is empty.", color='red')
            return

        self.sshTerminalTextEdit.clear() # Önceki çıktıları temizle
        self.append_to_ssh_terminal(f"Attempting to connect to {host}:{port} as {username}...", color='gray')
        self.append_to_log(f"Attempting SSH connection to {host}:{port}...", color='gray')

        # Önceki worker varsa durdur ve temizle
        if self.ssh_worker and self.ssh_worker.isRunning():
            self.ssh_worker.stop()
            self.ssh_worker.quit()
            self.ssh_worker.wait() # İş parçacığının bitmesini bekle
            self.ssh_worker = None # Temizleme

        self.ssh_worker = SSHWorker(host, port, username, password)
        # SSHWorker sinyallerini MainWindow metotlarına bağla
        self.ssh_worker.output_received.connect(self.append_to_ssh_terminal)
        self.ssh_worker.connection_established.connect(self.handle_ssh_connection_status)
        self.ssh_worker.error_occurred.connect(lambda msg: self.append_to_ssh_terminal(f"ERROR: {msg}", color='red'))
        self.ssh_worker.error_occurred.connect(lambda msg: self.append_to_log(f"SSH Worker Error: {msg}", color='red'))

        self.ssh_worker.start() # Worker'ı başlat

        # Bağlantı denemesi sırasında UI elemanlarını devre dışı bırak
        self.sshConnectButton.setEnabled(False)
        # Disconnect butonu hemen aktif edilebilir, bağlantı kurulmasa bile iptal etmek için
        self.sshDisconnectButton.setEnabled(True) 
        self.sshHostInput.setEnabled(False)
        self.sshPortInput.setEnabled(False)
        self.sshUserInput.setEnabled(False)
        self.sshPassInput.setEnabled(False)

    def handle_ssh_connection_status(self, success, message):
        """SSH bağlantı durumuna göre UI'yı günceller."""
        if success:
            self.append_to_ssh_terminal(f"SUCCESS: {message}", color='green')
            self.append_to_log(f"SSH connection: {message}", color='green')
            self.sshTerminalLineEdit.setEnabled(True) # Komut girişini etkinleştir
            self.sshTerminalSendButton.setEnabled(True) # Gönder butonunu etkinleştir
            # Bağlantı başarılı olunca kök dizini otomatik listele
            self.sftpPathLineEdit.setText("/")
            self.list_sftp_files()
        else:
            self.append_to_ssh_terminal(f"FAILED: {message}", color='red')
            self.append_to_log(f"SSH connection: {message}", color='red')
            # Bağlantı başarısız olursa, tekrar bağlanmayı etkinleştir
            self.sshConnectButton.setEnabled(True)
            self.sshDisconnectButton.setEnabled(False)
            self.sshHostInput.setEnabled(True)
            self.sshPortInput.setEnabled(True)
            self.sshUserInput.setEnabled(True)
            self.sshPassInput.setEnabled(True)
            self.sshTerminalLineEdit.setEnabled(False)
            self.sshTerminalSendButton.setEnabled(False)
        self.apply_access_control() # Durum değiştiğinde erişim kontrolünü tekrar uygula

    def disconnect_ssh(self):
        """SSH bağlantısını keser."""
        if self.ssh_worker:
            self.ssh_worker.stop() # Worker'a durma komutu gönder
            self.ssh_worker.quit() # Thread'i güvenli bir şekilde kapat
            self.ssh_worker.wait() # Thread'in sonlanmasını bekle
            self.ssh_worker = None # Worker'ı sıfırla
            # YENİ: Bağlantı kesilince SFTP listesini temizle
            self.sftpFileListWidget.clear()
            self.append_to_ssh_terminal("SSH connection terminated.", color='orange')
            self.append_to_log("SSH connection terminated.", color='orange')
        else:
            self.append_to_log("No active SSH connection to terminate.", color='gray')

        # UI'yı başlangıç durumuna döndür (self.apply_access_control() bunu halledebilir)

        self.sshConnectButton.setEnabled(True)
        self.sshDisconnectButton.setEnabled(False)
        self.sshHostInput.setEnabled(True)
        self.sshPortInput.setEnabled(True)
        self.sshUserInput.setEnabled(True)
        self.sshPassInput.setEnabled(True)
        self.sshTerminalLineEdit.setEnabled(False)
        self.sshTerminalSendButton.setEnabled(False)
        self.apply_access_control() # Son durumu uygulayın

    def send_ssh_command(self):
        """SSH terminaline komut gönderir."""
        command = self.sshTerminalLineEdit.text().strip()
        if command:
            # Worker varsa, çalışıyorsa ve SSH kanalı açıksa komutu gönder
            if self.ssh_worker and self.ssh_worker.isRunning() and self.ssh_worker.channel:
                self.append_to_ssh_terminal(f"> {command}", color='lightblue')
                self.ssh_worker.send_command(command)

                # Komut geçmişini güncelle
                if not self.ssh_command_history or self.ssh_command_history[-1] != command:
                    self.ssh_command_history.append(command)
                self.ssh_history_index = len(self.ssh_command_history)

                self.sshTerminalLineEdit.clear() # Giriş kutusunu temizle
            else:
                self.append_to_ssh_terminal("Not connected to SSH server. Command not sent.", color='red')
                self.append_to_log("Error: Not connected to SSH server. SSH command not sent.", color='red')
        else:
            self.append_to_ssh_terminal("Command cannot be empty.", color='red')
            self.append_to_log("Warning: Empty SSH command cannot be sent.", color='orange')

    def append_to_ssh_terminal(self, text, color=None):
        """SSH Terminal tabına metin ekler ve otomatik kaydırır."""
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
        if color:
            self.sshTerminalTextEdit.append(f"<span style=\"color:{color};\">{timestamp}{text}</span>")
        else:
            self.sshTerminalTextEdit.append(f"{timestamp}{text}")
        self.sshTerminalTextEdit.verticalScrollBar().setValue(self.sshTerminalTextEdit.verticalScrollBar().maximum())

    def ssh_terminal_lineEdit_key_press_event(self, event):
        """SSH terminal input box'ta komut geçmişini yukarı/aşağı ok tuşlarıyla gezmeyi sağlar."""
        if event.key() == Qt.Key_Up:
            if self.ssh_command_history and self.ssh_history_index > 0:
                self.ssh_history_index -= 1
                self.sshTerminalLineEdit.setText(self.ssh_command_history[self.ssh_history_index])
            elif self.ssh_command_history and self.ssh_history_index == 0:
                 self.sshTerminalLineEdit.setText(self.ssh_command_history[self.ssh_history_index])
        elif event.key() == Qt.Key_Down:
            if self.ssh_command_history and self.ssh_history_index < len(self.ssh_command_history) - 1:
                self.ssh_history_index += 1
                self.sshTerminalLineEdit.setText(self.ssh_command_history[self.ssh_history_index])
            elif self.ssh_history_index == len(self.ssh_command_history) - 1:
                self.ssh_history_index = len(self.ssh_command_history)
                self.sshTerminalLineEdit.clear()
        else:
            QLineEdit.keyPressEvent(self.sshTerminalLineEdit, event)    

    def listSerialPorts(self):
        """Updates the combo box listing available serial ports."""
        self.comboSeriPortList.clear()
        for port in QSerialPortInfo.availablePorts():
            self.comboSeriPortList.addItem(port.portName())
        if self.comboSeriPortList.count() == 0:
            self.append_to_log("No serial ports found.", color='orange')

    def portConnect(self):
        """Attempts to connect to the selected serial port."""
        name = self.comboSeriPortList.currentText()
        if not name:
            QMessageBox.warning(self, "Serial Port", "No serial port selected.")
            self.append_to_log("Failed to connect: No serial port selected.", color='red')
            return

        self.serialPort.setPortName(name)
        self.serialPort.setBaudRate(self.current_baud_rate)
        self.serialPort.setDataBits(self.data_bits_int_to_enum(self.current_data_bits))
        self.serialPort.setParity(self.current_parity)
        self.serialPort.setStopBits(self.current_stop_bits)
        if self.serialPort.open(QIODevice.ReadWrite):
            self.pushButtonConnect.setEnabled(False)
            self.pushButtonDisconnect.setEnabled(True)
            self.pushButtonSaveData.setEnabled(True)
            self.pushButtonStop.setEnabled(True)
            
            # Terminal ve Save Terminal Log butonlarının durumu erişim kontrolü tarafından yönetilir
            self.apply_access_control() 
            
            self.data_receiving = True
            self.pushButtonStop.setText("Stop")
            self.append_to_log(f"Connected: {name} @ {self.current_baud_rate} baud", color='green')
        else:
            self.append_to_log(f"Failed to connect: {self.serialPort.errorString()}", color='red')
            QMessageBox.critical(self, "Serial Port Error", f"Failed to connect: {self.serialPort.errorString()}")
            self.apply_access_control() # Bağlantı başarısız olursa UI elemanlarını güncelle

    def portDisconnect(self):
        """Disconnects the open serial port connection."""
        if self.serialPort.isOpen():
            self.serialPort.close()
            self.append_to_log("Disconnected.", color='orange')
        else:
            self.append_to_log("No active serial connection to disconnect.", color='gray')
        
        # Disconnect sonrası UI durumunu güncelle
        self.pushButtonConnect.setEnabled(True)
        self.pushButtonDisconnect.setEnabled(False)
        self.pushButtonSaveData.setEnabled(False)
        self.pushButtonStop.setEnabled(False)
        self.apply_access_control() # Erişim kontrolünü tekrar uygula

    def toggle_data_receiving(self):
        """Stops or starts receiving data from the serial port."""
        if self.serialPort.isOpen():
            if self.data_receiving:
                try:
                    self.serialPort.readyRead.disconnect(self.portDataReceived)
                except TypeError: # Zaten bağlantı kesilmişse TypeError verebilir
                    pass
                self.pushButtonStop.setText("Start")
                self.append_to_log("Data reception stopped.", color='black')
                self.data_receiving = False
            else:
                self.serialPort.readyRead.connect(self.portDataReceived)
                self.pushButtonStop.setText("Stop")
                self.append_to_log("Data reception started.", color='black')
                self.data_receiving = True
        else:
            self.append_to_log("Serial port is not open to toggle data reception.", color='orange')
            QMessageBox.warning(self, "Warning", "Serial port is not open.")

    def reset_data(self):
        """Resets all received data, graphs, and terminal history."""
        self.recorded_lines.clear()
        self.x_data.clear()
        self.y_data1.clear()
        self.y_data2.clear()
        self.time_index = 0
        self.textEditReceiveData.clear()
        self.terminalTextEdit.clear()
        self.terminal_command_history.clear()
        self.terminal_history_index = -1

        self.sshTerminalTextEdit.clear()
        self.ssh_command_history.clear()
        self.ssh_history_index = -1

        if pg:
            self.plot_auto_range = True #Reset sonrası otomatik modu tekrar aktifleştir
            self.curve1.setData([], [])
            self.curve2.setData([], [])
            self.plot_widget.setXRange(0, 100)
            self.plot_widget.setYRange(0, 100)
            
        self.append_to_log("All data and graph reset. Plot auto-ranging is ON.", color='black')

    def append_to_log(self, text, color=None):
        """Appends system messages to the QTextEdit in the 'Received Data (Log)' tab and auto-scrolls."""
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
        if color:
            self.textEditReceiveData.append(f"<span style=\"color:{color};\">{timestamp}{text}</span>")
        else:
            self.textEditReceiveData.append(f"{timestamp}{text}")
        self.textEditReceiveData.verticalScrollBar().setValue(self.textEditReceiveData.verticalScrollBar().maximum())

    def append_to_terminal(self, text, color=None):
        """Appends text to the QTextEdit in the 'Terminal' tab and auto-scrolls."""
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
        if color:
            self.terminalTextEdit.append(f"<span style=\"color:{color};\">{timestamp}{text}</span>")
        else:
            self.terminalTextEdit.append(f"{timestamp}{text}")
        self.terminalTextEdit.verticalScrollBar().setValue(self.terminalTextEdit.verticalScrollBar().maximum())

    def portSendData(self):
        """Sends the text from the terminal input to the serial port."""
        text = self.terminalLineEdit.text().strip()
        if text:
            if self.serialPort.isOpen():
                self.serialPort.write((text + '\n').encode('utf-8'))
                self.append_to_terminal(f"> {text}", color='lightblue')
                
                # Komut geçmişini güncelle
                if not self.terminal_command_history or self.terminal_command_history[-1] != text:
                    self.terminal_command_history.append(text)
                self.terminal_history_index = len(self.terminal_command_history)
                
                self.terminalLineEdit.clear()
            else:
                self.append_to_terminal("Serial port not connected. Command not sent.", color='red')
                self.append_to_log("Error: Serial port not connected. Command not sent.", color='red')
                QMessageBox.warning(self, "Serial Port", "Serial port not connected.")
        else:
            self.append_to_terminal("Command cannot be empty.", color='red')
            self.append_to_log("Warning: Empty command cannot be sent to serial port.", color='orange')

    def portDataReceived(self):
        """Seri porttan gelen veriyi okur ve NMEA ayrıştırıcıya gönderir."""
        data = self.serialPort.readAll().data().decode('utf-8', errors='ignore')
        self.received_buffer += data

        while '\n' in self.received_buffer:
            line, self.received_buffer = self.received_buffer.split('\n', 1)
            clean_line = line.strip()

            if not clean_line:
                continue

            self.append_to_log(f"RAW: {clean_line}", color='gray')
            self.recorded_lines.append(clean_line)           
            # Gelen her satırı, hem NMEA hem de diğer veriler için ayrıştırıcıya gönder
            # NMEA ise haritayı güncelleyecek, değilse eski mantıkla devam edecek.
            self.parse_nmea_sentence(clean_line)
            self.parse_other_data(clean_line) # Diğer veriler için yeni bir fonksiyon (opsiyonel)

    def terminal_lineEdit_key_press_event(self, event):
        """Enables navigating command history in the terminal input box using up/down arrow keys."""
        if event.key() == Qt.Key_Up:
            if self.terminal_command_history:
                if self.terminal_history_index == -1: # İlk kez yukarı basıldığında son komuta git
                    self.terminal_history_index = len(self.terminal_command_history) - 1
                elif self.terminal_history_index > 0:
                    self.terminal_history_index -= 1
                self.terminalLineEdit.setText(self.terminal_command_history[self.terminal_history_index])
        elif event.key() == Qt.Key_Down:
            if self.terminal_command_history:
                if self.terminal_history_index < len(self.terminal_command_history) - 1:
                    self.terminal_history_index += 1
                    self.terminalLineEdit.setText(self.terminal_command_history[self.terminal_history_index])
                elif self.terminal_history_index == len(self.terminal_command_history) - 1: # En sondaysa temizle
                    self.terminal_history_index = len(self.terminal_command_history)
                    self.terminalLineEdit.clear()
                else: # Boşsa ve yukarıda hiç komut yoksa
                    self.terminalLineEdit.clear()
        else:
            super(QLineEdit, self.terminalLineEdit).keyPressEvent(event)

    def parse_other_data(self, clean_line):
        """NMEA olmayan diğer metin tabanlı verileri işler."""
        try:
            # Mevcut grafik veri işleme mantığınız
            if self.parsing_config["mode"] == "simple":
                delimiter = self.parsing_config["delimiter"]
                col1_index = self.parsing_config["column1"] - 1
                col2_index = self.parsing_config["column2"] - 1

                parts = clean_line.split(delimiter)
                if len(parts) > max(col1_index, col2_index):
                    value1 = float(parts[col1_index].strip())
                    value2 = float(parts[col2_index].strip())
                    if pg:
                        self.update_plot_data(value1, value2)
                    self.append_to_terminal(f"Graph Data: V1={value1:.2f}, V2={value2:.2f}", color="#FA5EBE")
                    return # Veri işlendi, fonksiyondan çık
            
            elif self.parsing_config["mode"] == "regex":
                pass 

            # Grafik verisi değilse, diğer metin kontrolleri
            if "LED Yandi" in clean_line:
                self.append_to_terminal("STM32: LED Açıldı.", color='green')
            elif "LED Sondu" in clean_line:
                self.append_to_terminal("STM32: LED Kapandı.", color='red')
            elif "STM32 Status:" in clean_line:
                self.append_to_terminal(f"STM32: {clean_line}", color='purple')

        except (ValueError, IndexError):
            # Ayrıştırma başarısız olursa (örn: NMEA cümlesi geldiğinde), görmezden gel
            pass

    def showSettingsDialog(self):
        """Displays the serial port settings dialog."""
        dialog = SettingsDialog(self, {
            'baud_rate': self.current_baud_rate,
            'data_bits': self.current_data_bits,
            'parity': self.current_parity,
            'stop_bits': self.current_stop_bits
        })
        dialog.settingsChanged.connect(self.update_serial_settings)
        dialog.exec_()
    
    def data_bits_int_to_enum(self, val):
        return {
            5: QSerialPort.Data5,
            6: QSerialPort.Data6,
            7: QSerialPort.Data7,
            8: QSerialPort.Data8
        }.get(val, QSerialPort.Data8)

    def update_serial_settings(self, baud, bits, parity, stop):
        """Updates serial port settings."""
        self.current_baud_rate = baud
        self.current_data_bits = bits
        self.current_parity = parity
        self.current_stop_bits = stop
        self.append_to_log(f"Serial settings updated: Baud={baud}, DataBits={bits}, Parity={parity}, StopBits={stop}. You may need to reconnect.", color='gray')

    def apply_plot_settings(self):
        """Applies graph display settings (X/Y ranges, legend, etc.)."""
        if not pg:
            return  # pyqtgraph yoksa çık
        
        self.plot_auto_range = False

        self.plot_widget.setXRange(self.spin_x_from.value(), self.spin_x_to.value())
        self.plot_widget.setYRange(self.spin_y_from.value(), self.spin_y_to.value())
        self.curve1.setVisible(self.chk_curve1.isChecked())
        self.curve2.setVisible(self.chk_curve2.isChecked())

        if self.chk_show_legend.isChecked():
            if self.plot_widget.plotItem.legend is None:
                self.plot_widget.addLegend()
            else:
                self.plot_widget.plotItem.legend.setVisible(True)
        else:
            if self.plot_widget.plotItem.legend is not None:
                self.plot_widget.plotItem.legend.setVisible(False)

        self.append_to_log("Plot settings applied. Auto-ranging is now OFF.", color='black')

    def toggle_dark_mode(self, state):
        """Changes the application's theme to dark or light mode."""
        if state == Qt.Checked:
            self.setStyleSheet("""
                QMainWindow, QDialog { background-color: #2e2e2e; color: #ffffff; }
                QLabel, QCheckBox, QGroupBox, QComboBox, QSpinBox {
                    color: #ffffff;
                    background-color: #3c3c3c;
                    border: 1px solid #5c5c5c;
                    padding: 2px;
                }
                QTabWidget::pane { /* The tab widget frame */
                    border: 1px solid #5c5c5c;
                    background-color: #2e2e2e;
                }
                QTabBar::tab {
                    background: #3c3c3c;
                    color: white;
                    padding: 5px;
                    border: 1px solid #5c5c5c;
                    border-bottom-left-radius: 4px;
                    border-bottom-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #5c5c5c;
                    border-color: #777777;
                    border-bottom-color: #5c5c5c; /* same as pane color */
                }
                QPushButton {
                    background-color: #444444;
                    color: #ffffff;
                    border: 1px solid #666666;
                    padding: 5px 10px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #555555;
                }
                QPushButton:pressed {
                    background-color: #333333;
                }
                QPushButton:disabled {
                    background-color: #383838;
                    color: #888888;
                    border: 1px solid #484848;
                }
            """)
            # QTextEdit ve QLineEdit için özel stil
            self.terminalTextEdit.setStyleSheet("background-color: #1e1e1e; color: #00ff00; border: 1px solid #5c5c5c;")
            self.terminalLineEdit.setStyleSheet("background-color: #2e2e2e; color: #00ff00; border: 1px solid #5c5c5c;")
            self.textEditReceiveData.setStyleSheet("background-color: #1e1e1e; color: #CCCCCC; border: 1px solid #5c5c5c;")
            self.sshTerminalTextEdit.setStyleSheet("background-color: #1e1e1e; color: #00ff00; border: 1px solid #5c5c5c;")
            self.sshTerminalLineEdit.setStyleSheet("background-color: #2e2e2e; color: #00ff00; border: 1px solid #5c5c5c;")

            # Pyqtgraph arka plan ve eksen renkleri
            if pg:
                self.plot_widget.setBackground('#2e2e2e')
                self.plot_widget.getAxis('bottom').setTextPen('w')
                self.plot_widget.getAxis('left').setTextPen('w')
                self.plot_widget.getAxis('bottom').setPen('w')
                self.plot_widget.getAxis('left').setPen('w')
                self.plot_widget.showGrid(x=True, y=True, alpha=0.5)
        else:
            # Varsayılan (açık) tema
            self.setStyleSheet("") # Stili temizle
            self.terminalTextEdit.setStyleSheet("")
            self.terminalLineEdit.setStyleSheet("")
            self.textEditReceiveData.setStyleSheet("")
            self.sshTerminalTextEdit.setStyleSheet("")
            self.sshTerminalLineEdit.setStyleSheet("")
            if pg:
                self.plot_widget.setBackground('w')
                self.plot_widget.getAxis('bottom').setTextPen('k')
                self.plot_widget.getAxis('left').setTextPen('k')
                self.plot_widget.getAxis('bottom').setPen('k')
                self.plot_widget.getAxis('left').setPen('k')
                self.plot_widget.showGrid(x=True, y=True, alpha=1.0)
        self.append_to_log(f"Dark mode toggled to {'on' if state == Qt.Checked else 'off'}.", color='blue')

    def save_data_to_file(self):
        """Saves all recorded data to a CSV or text file."""
        if not self.recorded_lines:
            QMessageBox.warning(self, "Warning", "No data to save.")
            self.append_to_log("Warning: No data to save.", color='orange')
            return

        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_filename = f"data_{now}.csv"

        path, _ = QFileDialog.getSaveFileName(self, "Save Data As", default_filename,
                                              "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)")

        if not path:
            self.append_to_log("Data save canceled.", color='gray')
            return

        try:
            with open(path, 'w', encoding='utf-8') as file:
                for line in self.recorded_lines:
                    file.write(line + "\n")
            QMessageBox.information(self, "Success", f"Data successfully saved:\n{path}")
            self.append_to_log(f"Data successfully saved: {os.path.basename(path)}", color='black')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving file:\n{str(e)}")
            self.append_to_log(f"Error: Error saving data: {str(e)}", color='red')

    def save_terminal_data_to_file(self):
        """Saves the content of the Terminal tab to a text file."""
        terminal_content = self.terminalTextEdit.toPlainText()

        if not terminal_content.strip():
            QMessageBox.warning(self, "Warning", "No terminal data to save.")
            self.append_to_log("Warning: No terminal data to save.", color='orange')
            return

        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_filename = f"terminal_log_{now}.txt"

        path, _ = QFileDialog.getSaveFileName(self, "Save Terminal Log As", default_filename,
                                              "Text Files (*.txt);;All Files (*)")

        if not path:
            self.append_to_log("Terminal log save canceled.", color='gray')
            return

        try:
            with open(path, 'w', encoding='utf-8') as file:
                file.write(terminal_content)
            QMessageBox.information(self, "Success", f"Terminal log successfully saved:\n{path}")
            self.append_to_log(f"Terminal log successfully saved: {os.path.basename(path)}", color='black')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving terminal log:\n{str(e)}")
            self.append_to_log(f"Error: Error saving terminal log: {str(e)}", color='red')

    def export_plot(self):
        """Exports the plot as a PNG or SVG image."""
        if not pg:
            QMessageBox.warning(self, "Warning", "pyqtgraph library not found, cannot export plot.")
            self.append_to_log("Warning: pyqtgraph not found, cannot export plot.", color='orange')
            return
        if not self.x_data:
            QMessageBox.warning(self, "Warning", "No data to export plot.")
            self.append_to_log("Warning: No data to export plot.", color='orange')
            return

        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_filename = f"plot_{now}.png"

        path, filter = QFileDialog.getSaveFileName(self, "Export Plot As", default_filename,
                                                    "PNG Files (*.png);;SVG Files (*.svg)")

        if not path:
            self.append_to_log("Plot export canceled.", color='gray')
            return

        exporter = None
        try:
            # Seçilen filtreye göre dosya uzantısını otomatik ekle
            if filter == "PNG Files (*.png)" and not path.lower().endswith('.png'):
                path += ".png"
            elif filter == "SVG Files (*.svg)" and not path.lower().endswith('.svg'):
                path += ".svg"
            
            if path.lower().endswith('.png'):
                exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
                exporter.parameters()['width'] = self.plot_widget.width() # Mevcut widget boyutunu kullan
                exporter.parameters()['height'] = self.plot_widget.height()
            elif path.lower().endswith('.svg'):
                exporter = pg.exporters.SVGExporter(self.plot_widget.plotItem)
            else: # Varsayılan PNG
                exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
                exporter.parameters()['width'] = self.plot_widget.width()
                exporter.parameters()['height'] = self.plot_widget.height()
                path += ".png" # Eklenti yoksa varsayılanı ekle

            if exporter:
                exporter.export(path)
                QMessageBox.information(self, "Success", f"Plot successfully saved:\n{path}")
                self.append_to_log(f"Plot successfully saved: {os.path.basename(path)}", color='black')
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving plot:\n{str(e)}")
            self.append_to_log(f"Error: Error saving plot: {str(e)}", color='red')
    def showDataParserDialog(self):
        """Veri ayrıştırıcı ayarları penceresini gösterir."""
        # Mevcut ayarların bir kopyasıyla dialog'u oluştur
        dialog = DataParserDialog(self.parsing_config.copy(), self)
        # Dialog'dan gelen 'ayarlar uygulandı' sinyalini, ayarları güncelleyecek metoda bağla
        dialog.settingsApplied.connect(self.update_parsing_config)
        dialog.exec_()

    def update_parsing_config(self, new_config):
        """DataParserDialog'dan gelen yeni ayarları değişkene atar."""
        self.parsing_config = new_config
        self.append_to_log(f"Data parser settings updated. Mode: {self.parsing_config['mode']}", color='blue')

# --- Application Entry Point ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    sys.exit(app.exec_())