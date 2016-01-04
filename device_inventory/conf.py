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
            Settings.__instance = self.load_config()
        
    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)
    
    def load_config(self):
        # https://docs.python.org/3.4/library/configparser.html
        path = os.path.dirname(__file__)
        config_file = os.path.join(path, 'config.ini')
        assert os.path.exists(config_file), config_file

        config = configparser.ConfigParser()
        config.read(config_file)  # donator.cfg merged here
        
        # TODO set fallback values if config is empty
        # https://docs.python.org/3.4/library/configparser.html#fallback-values
        
        return config


settings = Settings()
