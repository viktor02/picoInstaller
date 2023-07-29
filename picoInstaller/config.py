import pathlib
import configparser
import random


class MyConfigParser:
    def __init__(self, config_file="config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()

        if not pathlib.Path(self.config_file).exists():
            self.create_default_config()

        self.config.read(self.config_file)

    def create_default_config(self):
        # Set default values

        unique = random.randint(0, 99999)

        self.config['keytool'] = {
            'CN': f'user{unique}',
            'password': 'ab944ac',
            'file': 'android.keystore',
            'alias': 'mykey',
        }

        self.config['picoInstaller'] = {
            'prefix': f'r{unique}'  # Init the random prefix for package name
        }

        # Write config file
        with open(self.config_file, 'w') as f:
            self.config.write(f)

    def get(self, category, option):
        return self.config.get(category, option)
