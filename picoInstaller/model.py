import logging
import pathlib
import shutil
import subprocess
from random import randint
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from PyQt5.QtCore import QThread, pyqtSignal
from adbutils import adb, AdbError


def find_apk_obb(folder: pathlib.Path) -> [pathlib.Path, pathlib.Path]:
    obb_folder = None
    apk_file = None

    if any(folder.glob("**/*.obb")):
        obb_folder = next(folder.glob("**/*.obb")).parent
    apk_file = next(folder.glob("*.apk")).resolve()

    return apk_file, obb_folder


class AdbModel:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.device = self.get_device()
        self.cwd = pathlib.Path(".")

    def get_device(self):
        self.device = adb.device()
        return self.device

    def install_apk(self, apk_path):
        self.device.install(str(apk_path), nolaunch=True)

    def install_folder(self, obb_folder: pathlib.Path, apk_file: pathlib.Path):
        self.logger.info(f"Installing {apk_file}")
        self.device.install(str(apk_file), nolaunch=True)

        obb_files = obb_folder.parent.glob('**/*.obb')
        obb_files = [*obb_files]
        self.logger.info(f"Installing obb files")
        for file in obb_files:
            # relative_path = file.relative_to(obb_folder)
            new_dir = f"/sdcard/Android/obb/{file.parent.name}"
            self.device.shell(f"mkdir -p {new_dir}")
            self.device.push(str(file), f"{new_dir}/{file.name}")
            self.logger.info(f"Installed {file}")

    def unpack_zip(self, zip_path: pathlib.Path, target_dir: pathlib.Path):
        self.logger.info(f"Unpacking {zip_path}")
        target_dir.mkdir(exist_ok=True)

        shutil.unpack_archive(zip_path, target_dir)

        self.logger.info(f"Unpacked {zip_path}")

        apk_file, obb_folder = find_apk_obb(target_dir)
        self.logger.info(f"Found obb folder: {obb_folder}")
        self.logger.info(f"Found apk file: {apk_file}")

        return obb_folder, apk_file

    def uninstall_app(self, package_name):
        self.device.uninstall(package_name)

    def list_packages(self):
        return self.device.list_packages()

    def get_package_info(self, package_name):
        return self.device.app_info(package_name)

    def run_command(self, command):
        return self.device.shell(command)


class InstallThread(QThread):
    message = pyqtSignal(str)

    def __init__(self, file_path: pathlib.Path, is_rename_package: bool = False):
        super().__init__()
        self.file_path = file_path
        self.is_rename_package = is_rename_package
        self.temp_dir = pathlib.Path("PicoInstallerTemp")

    def run(self):
        self.log("Installer thread started...")
        model = AdbModel()

        try:
            if self.file_path.suffix == ".apk":
                self._handle_apk(model)

            elif self.file_path.suffix == ".zip":
                self._handle_zip(model)

            elif self.file_path.is_dir():
                self._handle_dir(model)

            else:
                self.log("Unknown file type")
                return

            self._cleanup()

        except AdbError as e:
            self.log(f"Error: {e}")

        except NotImplementedError as e:
            self.log(f"Error: {e}")

    def _handle_apk(self, model):
        self.log("Installing APK...")
        if self.is_rename_package:
            self.log("Renaming package...")
            new_apk = self._rename_package(self.file_path)
            model.install_apk(new_apk)
        else:
            model.install_apk(self.file_path)

    def _handle_zip(self, model):
        self.log("Unpacking ZIP...")
        obb_folder, apk_file = model.unpack_zip(self.file_path, self.temp_dir)

        if not apk_file:
            self.log("Error: No APK file found")
            return

        if self.is_rename_package:
            self.log("Renaming package...")
            new_apk = self._rename_package(apk_file, obb_folder)
            model.install_folder(obb_folder, new_apk)
        else:
            model.install_folder(obb_folder, apk_file)

        self.log("Removing temporary directory...")
        shutil.rmtree(self.temp_dir)

    def _handle_dir(self, model):
        self.log("Installing folder...")
        apk_file, obb_folder = find_apk_obb(self.file_path)

        if not apk_file:
            self.log("Error: No APK file found")
            return

        if self.is_rename_package:
            self.log("Renaming package...")
            new_apk = self._rename_package(apk_file, obb_folder)
            model.install_folder(obb_folder, new_apk)
        else:
            model.install_folder(obb_folder, apk_file)

    def _cleanup(self):
        self.log("Cleaning files")
        pathlib.Path("renamed_app.apk").unlink()
        self.log("Installing complete")

    @staticmethod
    def _rename_package(apk_file, obb_folder=None):
        renamer = Renamer(apk_file, obb_folder)
        _, new_apk = renamer.rename_package()
        return new_apk

    def log(self, message):
        self.message.emit(message)


class Renamer:
    def __init__(self, apk_path: pathlib.Path, obb_folder: pathlib.Path = None):
        self.apk_path = apk_path  # APK file
        self.obb_folder = obb_folder  # Folder with obb files
        self.temp_dir = pathlib.Path("PicoInstallerTempRenamer")  # Temporary directory for renaming APK file
        self.logger = logging.getLogger(__name__)
        assert self.java_is_installed(), "Java is not installed. Please install Java and try again."

    @staticmethod
    def java_is_installed():
        try:
            # Use the 'java -version' command to check if Java is installed
            subprocess.run(['java', '-version'], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def download_apktool(self) -> pathlib.Path:
        url = "https://github.com/iBotPeaches/Apktool/releases/download/v2.7.0/apktool_2.7.0.jar"
        self.temp_dir.mkdir(exist_ok=True)
        path = pathlib.Path(self.temp_dir.parent, "apktool.jar")
        if not path.exists():
            try:
                urllib.request.urlretrieve(url, path)
            except urllib.error.URLError as e:
                self.logger.error(f"Error occurred when downloading apktool: {e}")
        return path

    def download_apksigner(self) -> pathlib.Path:
        url = "https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar"
        self.temp_dir.mkdir(exist_ok=True)
        path = pathlib.Path(self.temp_dir.parent, "apksigner.jar")
        if not path.exists():
            try:
                urllib.request.urlretrieve(url, path)
            except urllib.error.URLError as e:
                self.logger.error(f"Error occurred when downloading apksigner: {e}")
        return path

    @staticmethod
    def replace_package_name(android_manifest_path):
        # Parse the XML file
        tree = ET.parse(android_manifest_path)
        root = tree.getroot()

        # Get 'manifest' element which has 'package' attribute
        manifest = root

        # Replace package name
        old_package_name = manifest.attrib['package']

        random = randint(0, 999999)
        try:
            app = old_package_name.split('.')[-1]
            new_package_name = f"com.r{random}.{app}"
        except IndexError:
            new_package_name = f"com.r{random}"

        with open(android_manifest_path, "r+") as f:
            content = f.read()
            content = content.replace(old_package_name, new_package_name)
            f.seek(0)
            f.write(content)
            f.truncate()

        return new_package_name

    def rename_package(self) -> [str, str]:
        """
        Rename package name in APK and OBB folder
        """
        # Download APKTool
        apktool_path = self.download_apktool()
        # Download APKSigner
        apksigner_path = self.download_apksigner()

        # Extract APK
        subprocess.run(
            ['java', '-jar', str(apktool_path), 'd', '-f', '-o', str(self.temp_dir),
             str(self.apk_path)],
            check=True)

        new_package_name = ""
        for manifest in self.temp_dir.glob('AndroidManifest.xml'):
            new_package_name = self.replace_package_name(manifest)

        # Rebuild APK
        apk_path = pathlib.Path("renamed_app.apk").resolve()
        subprocess.run(['java', '-jar', str(apktool_path), 'b', '-o', str(apk_path), str(self.temp_dir)],
                       check=True)

        # Sign APK
        subprocess.run(['java', '-jar', str(apksigner_path), '-a', str(apk_path), '--overwrite'],
                       check=True)

        # Clean up temporary directory
        shutil.rmtree(self.temp_dir)

        if self.obb_folder:
            # rename obb files
            for file in self.obb_folder.glob('*.obb'):
                old_package_name = self.obb_folder.name
                new_filename = file.name.replace(old_package_name, new_package_name)
                file.rename(file.parent.resolve() / new_filename)
            # rename dir
            self.obb_folder.rename(self.obb_folder.parent.resolve() / new_package_name)
            return self.obb_folder, apk_path
        else:
            return new_package_name, apk_path
