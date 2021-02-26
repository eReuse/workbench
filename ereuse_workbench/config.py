from decouple import AutoConfig


class WorkbenchConfig:
    config = AutoConfig(search_path='/home/user/')
    DH_TOKEN = config('DH_TOKEN', 'Yzc5YzI5MTItOWJhNi00NjU4LTg1MTAtNWNlOWYyZTBmNzk2Og==')
    DH_HOST = config('DH_HOST', 'api.testing.usody.com')
    DH_DATABASE = config('DH_DATABASE', 'usodybeta')
    DEVICEHUB_URL = 'https://{host}/{db}/'.format(
        host=DH_HOST,
        db=DH_DATABASE
    )  # type: str
