try:
    import ConfigParser as configparser  # Python2
except ImportError:
    import configparser
import os


class Settings(object):
    """
    Settings in a singleton way to only load configuration once and
    allow overriding settings using args.

    """
    __instance = None

    def __init__(self):
        if Settings.__instance is None:
            Settings.__instance = configparser.ConfigParser()
            self.load_config()

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)

    def load_config(self, config_file=None):
        if config_file is None:
            path = os.path.dirname(__file__)
            config_file = os.path.join(path, 'config.ini')

        if not os.path.exists(config_file):
            raise IOError('No such file or directory: {}'.format(config_file))

        self.__instance.read(config_file)


settings = Settings()
