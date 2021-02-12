from decouple import AutoConfig


class WorkbenchConfig:
    config = AutoConfig(search_path='/opt/envs/my-project')
    WB_USER = config('WB_USER', 'user')
    # WB_USER = 'user@dhub.com'
    WB_PASSWORD = config('WB_PASSWORD', '1234')
    WB_HOST = config('WB_HOST', 'localhost:5000')
    WB_DATABASE = config('WB_DATABASE', 'devicehub')
    DEVICEHUB_TEAL_URL = 'https://{user}:{pw}@{host}'.format(
        user=WB_USER,
        pw=WB_PASSWORD,
        host=WB_HOST
    )  # type: str
