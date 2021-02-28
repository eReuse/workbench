from decouple import AutoConfig

from ereuse_workbench.test import TestDataStorageLength


class WorkbenchConfig:
    # Path where find .env file
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
    WB_BENCHMARK = config('WB_BENCHMARK', True)
    WB_STRESS_TEST = config('WB_STRESS_TEST', 0)
    WB_SMART_TEST = config('WB_SMART_TEST', TestDataStorageLength.Short)

    ## Erase parameters
    WB_ERASE = config('WB_ERASE')
    WB_ERASE_STEPS = config('WB_ERASE_STEPS', 1)
    WB_ERASE_LEADING_ZEROS = config('WB_ERASE_LEADING_ZERO', False)
