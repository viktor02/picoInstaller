import os
import sys
import logging
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QMessageBox

from model import InstallThread, AdbModel


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        self.install_thread = None
        self.file_path = None
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
        uic.loadUi('main_window.ui', self)

        self.statusBar = self.findChild(QtWidgets.QStatusBar, 'statusbar')
        self.logWidget = self.findChild(QtWidgets.QListWidget, 'listWidget')
        self.button = self.findChild(QtWidgets.QPushButton, 'installButton')
        self.tab_widget = self.findChild(QtWidgets.QTabWidget, 'tabWidget')
        self.list_packages = self.findChild(QtWidgets.QListWidget, 'listPackages')
        self.list_packages_button = self.findChild(QtWidgets.QPushButton, 'deleteButton')
        self.shell_button = self.findChild(QtWidgets.QPushButton, 'SendCommandButton')
        self.shell_input = self.findChild(QtWidgets.QLineEdit, 'ShellInput')
        self.shell_output = self.findChild(QtWidgets.QPlainTextEdit, 'ShellOutput')

        self.button.clicked.connect(self.start_installer_thread)
        self.list_packages_button.clicked.connect(self.on_delete_button)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.shell_button.clicked.connect(self.on_send_command)

        try:
            self.adbmodel = AdbModel()
            device_id = self.adbmodel.get_device()
            self.statusBar.showMessage(f"Connected to {device_id.serial}")
            self.show()
        except RuntimeError as e:
            QMessageBox.warning(self, "Error", str(e))
            sys.exit(1)

    def handle_message(self, message):
        self.labelDrag.setText(message)
        self.logWidget.addItem(message)
        self.statusBar.showMessage(message)

    def open_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Package", "", "APK Files (*.apk);;ZIP Files (*.zip)")
        if file_path:
            self.check_file(file_path)

    def on_tab_changed(self, index):
        if index == 1:
            self.list_packages.clear()
            self.list_packages.addItems(self.adbmodel.list_packages())

    def on_delete_button(self):
        package = self.list_packages.currentItem().text()
        self.adbmodel.uninstall_app(package)
        self.list_packages.clear()
        self.list_packages.addItems(self.adbmodel.list_packages())

    def on_send_command(self):
        self.shell_output.clear()
        command = self.shell_input.text()
        output = self.adbmodel.run_command(command)
        self.shell_output.appendPlainText(output)

    def check_file(self, file_path):
        if file_path.endswith((".apk", ".zip")):
            suffix = "APK file" if file_path.endswith(".apk") else "ZIP archive"
            self.labelDrag.setText(f"Found {suffix}! Click the button below to install")
            self.button.setEnabled(True)
            self.file_path = file_path
        else:
            self.labelDrag.setText("Unknown file type!")
            self.button.setEnabled(False)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        file_path = event.mimeData().urls()[0].toLocalFile()
        self.check_file(file_path)

    def start_installer_thread(self):
        self.install_thread = InstallThread(self.file_path)
        self.install_thread.message.connect(self.handle_message)
        self.button.setEnabled(False)
        self.install_thread.start()


os.system("adb devices") # start adb daemon

app = QtWidgets.QApplication(sys.argv)
window = Ui()
app.exec_()