import environ
from rororo import BaseSettings


@environ.config(prefix=None, frozen=True)
class Settings(BaseSettings):
    dscensor_app_key: str = environ.var(name="DSCENSOR_APP_KEY", default="digraph")
    input_nodes: str = environ.var(name="DSCENSOR_INPUT_NODES", default="./autocontent")
