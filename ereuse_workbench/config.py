from decouple import AutoConfig


class WorkbenchConfig:
    config = AutoConfig(search_path='/home/user/envs/')
    DH_USER = config('DH_USER', 'user@dhub.com')
    DH_PASSWORD = config('DH_PASSWORD', '1234')
    DH_HOST = config('DH_HOST', 'api.testing.usody.com')
    DH_DATABASE = config('DH_DATABASE', 'usodybeta')
    DEVICEHUB_TEAL_URL = 'https://{user}:{pw}@{host}'.format(
        user=DH_USER,
        pw=DH_PASSWORD,
        host=DH_HOST
    )  # type: str
