# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
