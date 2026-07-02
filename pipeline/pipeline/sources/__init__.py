from .arbeitnow import ArbeitnowSource
from .greenhouse import GreenhouseSource
from .hn_hiring import HackerNewsSource
from .remoteok import RemoteOkSource
from .remotive import RemotiveSource
from .wwr import WeWorkRemotelySource

ALL_SOURCES = [
    RemotiveSource(),
    ArbeitnowSource(),
    GreenhouseSource(),
    RemoteOkSource(),
    WeWorkRemotelySource(),
    HackerNewsSource(),
]
