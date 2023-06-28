import logging
import pathlib
import tempfile

from PyQt5.QtCore import QThread, pyqtSignal
from adbutils import adb, AdbError
import shutil


class InstallThread(QThread):
    message = pyqtSignal(str)

    def __init__(self, installer_args):
        super().__init__()
        self.file_path = installer_args

        self.adb = AdbModel()

    def log(self, message):
        self.message.emit(message)

    def run(self):
        self.log("Installer thread started...")

        try:
            if self.file_path.endswith(".apk"):
                self.adb.install_apk(self.file_path)
            elif self.file_path.endswith(".zip"):
                self.adb.install_zip(self.file_path)
            else:
                self.log("Unknown file type")
            self.log("Installation complete.")
        except AdbError as e:
            self.log(f"Error: {e}")
        except NotImplementedError as e:
            self.log(f"Error: {e}")


class AdbModel:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.device = self.get_device()
        self.cwd = pathlib.Path("/")

    def get_device(self):
        self.device = adb.device()
        return self.device

    def install_apk(self, apk_path):
        self.device.install(apk_path, nolaunch=True)

    def install_zip(self, zip_path):
        with tempfile.TemporaryDirectory("picoInstaller") as temp_folder:
            temp_folder = pathlib.Path(temp_folder)

            self.logger.info("Unpacking archive to temp folder")
            shutil.unpack_archive(zip_path, temp_folder)
            apk_file = next(temp_folder.glob("*.apk")).resolve()

            self.logger.info(f"Installing {apk_file}")
            self.device.install(str(apk_file), nolaunch=True)

            obb_files = temp_folder.glob('**/*.obb')
            self.logger.info(f"Installing obb files")
            for file in obb_files:
                relative_path = file.relative_to(temp_folder)
                new_dir = f"/sdcard/Android/obb/{relative_path.parent}"
                self.device.shell(f"mkdir -p {new_dir}")
                self.device.push(str(file), f"{new_dir}/{file.name}")
                self.logger.info(f"Installed {file}")

    def uninstall_app(self, package_name):
        self.device.uninstall(package_name)

    def list_packages(self):
        return self.device.list_packages()

    def get_package_info(self, package_name):
        return self.device.app_info(package_name)

    def run_command(self, command):
        return self.device.shell(command)
