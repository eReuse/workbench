from decouple import AutoConfig

from ereuse_workbench.test import TestDataStorageLength


class WorkbenchConfig:
    # Path where find settings.ini file
    config = AutoConfig(search_path='/home/user/')

    # Env variables for DH parameters
    DH_TOKEN = config('DH_TOKEN')
    DH_HOST = config('DH_HOST')
    DH_DATABASE = config('DH_DATABASE')
    DEVICEHUB_URL = 'https://{host}/{db}/'.format(
        host=DH_HOST,
        db=DH_DATABASE
    )  # type: str

    ## Env variables for WB parameters
    WB_BENCHMARK = config('WB_BENCHMARK', default=True, cast=bool)
    WB_STRESS_TEST = config('WB_STRESS_TEST', default=0, cast=int)
    WB_SMART_TEST = config('WB_SMART_TEST', default='')

    ## Erase parameters
    WB_ERASE = config('WB_ERASE')
    WB_ERASE_STEPS = config('WB_ERASE_STEPS', default=1, cast=int)
    WB_ERASE_LEADING_ZEROS = config('WB_ERASE_LEADING_ZERO', default=False, cast=bool)

    WB_DEBUG = config('WB_DEBUG', default=True, cast=bool)
