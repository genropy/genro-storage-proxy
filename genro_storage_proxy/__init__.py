"""genro-storage-proxy - HTTP microservice for genro-storage.

Exposes genro-storage capabilities via REST API for polyglot microservice
architectures.
"""

from genro_storage_proxy.api import create_app
from genro_storage_proxy.persistence import Persistence
from genro_storage_proxy.config_loader import VolumeConfigLoader, load_volumes_from_config

__version__ = '0.1.0-dev'

__all__ = [
    '__version__',
    'create_app',
    'Persistence',
    'VolumeConfigLoader',
    'load_volumes_from_config',
]
