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

"""Backend schemas and capabilities definitions.

This module defines:
- Form schemas for each storage backend
- Capabilities supported by each backend
"""

from typing import Dict, List, Any


# Backend capabilities
CAPABILITIES = {
    "local": {
        "read": True,
        "write": True,
        "delete": True,
        "list": True,
        "mkdir": True,
        "copy": True,
        "move": True,
        "metadata": True,
        "description": "Local filesystem storage with full read/write capabilities"
    },
    "s3": {
        "read": True,
        "write": True,
        "delete": True,
        "list": True,
        "mkdir": False,  # S3 doesn't have true directories
        "copy": True,
        "move": True,
        "metadata": True,
        "description": "Amazon S3 object storage"
    },
    "gcs": {
        "read": True,
        "write": True,
        "delete": True,
        "list": True,
        "mkdir": False,
        "copy": True,
        "move": True,
        "metadata": True,
        "description": "Google Cloud Storage"
    },
    "azure": {
        "read": True,
        "write": True,
        "delete": True,
        "list": True,
        "mkdir": False,
        "copy": True,
        "move": True,
        "metadata": True,
        "description": "Azure Blob Storage"
    },
    "http": {
        "read": True,
        "write": False,
        "delete": False,
        "list": False,
        "mkdir": False,
        "copy": False,
        "move": False,
        "metadata": True,
        "description": "HTTP/HTTPS read-only access"
    },
    "memory": {
        "read": True,
        "write": True,
        "delete": True,
        "list": True,
        "mkdir": True,
        "copy": True,
        "move": True,
        "metadata": True,
        "description": "In-memory storage (volatile)"
    },
    "smb": {
        "read": True,
        "write": True,
        "delete": True,
        "list": True,
        "mkdir": True,
        "copy": True,
        "move": True,
        "metadata": True,
        "description": "SMB/CIFS network share"
    },
    "sftp": {
        "read": True,
        "write": True,
        "delete": True,
        "list": True,
        "mkdir": True,
        "copy": True,
        "move": True,
        "metadata": True,
        "description": "SFTP (SSH File Transfer Protocol)"
    },
    "zip": {
        "read": True,
        "write": False,
        "delete": False,
        "list": True,
        "mkdir": False,
        "copy": False,
        "move": False,
        "metadata": True,
        "description": "ZIP archive read-only access"
    },
    "tar": {
        "read": True,
        "write": False,
        "delete": False,
        "list": True,
        "mkdir": False,
        "copy": False,
        "move": False,
        "metadata": True,
        "description": "TAR archive read-only access"
    },
    "git": {
        "read": True,
        "write": False,
        "delete": False,
        "list": True,
        "mkdir": False,
        "copy": False,
        "move": False,
        "metadata": True,
        "description": "Git repository read-only access"
    },
    "github": {
        "read": True,
        "write": False,
        "delete": False,
        "list": True,
        "mkdir": False,
        "copy": False,
        "move": False,
        "metadata": True,
        "description": "GitHub repository read-only access"
    },
    "webdav": {
        "read": True,
        "write": True,
        "delete": True,
        "list": True,
        "mkdir": True,
        "copy": True,
        "move": True,
        "metadata": True,
        "description": "WebDAV protocol"
    },
    "libarchive": {
        "read": True,
        "write": False,
        "delete": False,
        "list": True,
        "mkdir": False,
        "copy": False,
        "move": False,
        "metadata": True,
        "description": "Various archive formats via libarchive"
    },
    "base64": {
        "read": True,
        "write": True,
        "delete": False,
        "list": False,
        "mkdir": False,
        "copy": False,
        "move": False,
        "metadata": False,
        "description": "Base64 encoded data storage"
    }
}


# Backend form schemas
BACKEND_SCHEMAS = {
    "local": {
        "fields": [
            {
                "name": "path",
                "type": "text",
                "label": "Local Path",
                "required": True,
                "placeholder": "/path/to/directory",
                "help": "Absolute path to local directory"
            }
        ]
    },
    "s3": {
        "fields": [
            {
                "name": "bucket",
                "type": "text",
                "label": "Bucket Name",
                "required": True,
                "placeholder": "my-bucket"
            },
            {
                "name": "region",
                "type": "text",
                "label": "AWS Region",
                "required": True,
                "default": "us-east-1",
                "placeholder": "us-east-1"
            },
            {
                "name": "access_key_id",
                "type": "password",
                "label": "Access Key ID",
                "required": False,
                "help": "Leave empty to use AWS credentials from environment"
            },
            {
                "name": "secret_access_key",
                "type": "password",
                "label": "Secret Access Key",
                "required": False
            },
            {
                "name": "endpoint_url",
                "type": "text",
                "label": "Custom Endpoint URL",
                "required": False,
                "placeholder": "https://s3.example.com",
                "help": "For S3-compatible services (MinIO, DigitalOcean Spaces, etc.)"
            }
        ]
    },
    "gcs": {
        "fields": [
            {
                "name": "bucket",
                "type": "text",
                "label": "Bucket Name",
                "required": True,
                "placeholder": "my-bucket"
            },
            {
                "name": "project",
                "type": "text",
                "label": "Project ID",
                "required": False,
                "placeholder": "my-project-123"
            },
            {
                "name": "credentials_path",
                "type": "text",
                "label": "Credentials JSON Path",
                "required": False,
                "placeholder": "/path/to/credentials.json",
                "help": "Leave empty to use application default credentials"
            }
        ]
    },
    "azure": {
        "fields": [
            {
                "name": "container",
                "type": "text",
                "label": "Container Name",
                "required": True,
                "placeholder": "my-container"
            },
            {
                "name": "account_name",
                "type": "text",
                "label": "Storage Account Name",
                "required": True,
                "placeholder": "mystorageaccount"
            },
            {
                "name": "account_key",
                "type": "password",
                "label": "Account Key",
                "required": False,
                "help": "Leave empty to use connection string or managed identity"
            },
            {
                "name": "connection_string",
                "type": "password",
                "label": "Connection String",
                "required": False
            }
        ]
    },
    "http": {
        "fields": [
            {
                "name": "url",
                "type": "text",
                "label": "Base URL",
                "required": True,
                "placeholder": "https://example.com/files/"
            },
            {
                "name": "username",
                "type": "text",
                "label": "Username",
                "required": False,
                "help": "For HTTP Basic Auth"
            },
            {
                "name": "password",
                "type": "password",
                "label": "Password",
                "required": False
            }
        ]
    },
    "memory": {
        "fields": []
    },
    "smb": {
        "fields": [
            {
                "name": "host",
                "type": "text",
                "label": "Host",
                "required": True,
                "placeholder": "server.example.com or 192.168.1.100"
            },
            {
                "name": "share",
                "type": "text",
                "label": "Share Name",
                "required": True,
                "placeholder": "shared_folder"
            },
            {
                "name": "username",
                "type": "text",
                "label": "Username",
                "required": False
            },
            {
                "name": "password",
                "type": "password",
                "label": "Password",
                "required": False
            },
            {
                "name": "domain",
                "type": "text",
                "label": "Domain",
                "required": False,
                "placeholder": "WORKGROUP"
            }
        ]
    },
    "sftp": {
        "fields": [
            {
                "name": "host",
                "type": "text",
                "label": "Host",
                "required": True,
                "placeholder": "sftp.example.com"
            },
            {
                "name": "port",
                "type": "number",
                "label": "Port",
                "required": False,
                "default": "22"
            },
            {
                "name": "username",
                "type": "text",
                "label": "Username",
                "required": True
            },
            {
                "name": "password",
                "type": "password",
                "label": "Password",
                "required": False,
                "help": "Required if not using key authentication"
            },
            {
                "name": "private_key_path",
                "type": "text",
                "label": "Private Key Path",
                "required": False,
                "placeholder": "/path/to/id_rsa"
            }
        ]
    },
    "zip": {
        "fields": [
            {
                "name": "path",
                "type": "text",
                "label": "ZIP File Path",
                "required": True,
                "placeholder": "/path/to/archive.zip"
            },
            {
                "name": "password",
                "type": "password",
                "label": "Password",
                "required": False,
                "help": "For encrypted ZIP files"
            }
        ]
    },
    "tar": {
        "fields": [
            {
                "name": "path",
                "type": "text",
                "label": "TAR File Path",
                "required": True,
                "placeholder": "/path/to/archive.tar.gz"
            }
        ]
    },
    "git": {
        "fields": [
            {
                "name": "url",
                "type": "text",
                "label": "Repository URL",
                "required": True,
                "placeholder": "https://github.com/user/repo.git"
            },
            {
                "name": "branch",
                "type": "text",
                "label": "Branch",
                "required": False,
                "default": "main",
                "placeholder": "main"
            },
            {
                "name": "username",
                "type": "text",
                "label": "Username",
                "required": False,
                "help": "For private repositories"
            },
            {
                "name": "password",
                "type": "password",
                "label": "Password/Token",
                "required": False
            }
        ]
    },
    "github": {
        "fields": [
            {
                "name": "owner",
                "type": "text",
                "label": "Repository Owner",
                "required": True,
                "placeholder": "username or organization"
            },
            {
                "name": "repo",
                "type": "text",
                "label": "Repository Name",
                "required": True,
                "placeholder": "repository-name"
            },
            {
                "name": "branch",
                "type": "text",
                "label": "Branch",
                "required": False,
                "default": "main",
                "placeholder": "main"
            },
            {
                "name": "token",
                "type": "password",
                "label": "GitHub Token",
                "required": False,
                "help": "Required for private repositories"
            }
        ]
    },
    "webdav": {
        "fields": [
            {
                "name": "url",
                "type": "text",
                "label": "WebDAV URL",
                "required": True,
                "placeholder": "https://webdav.example.com/remote.php/dav/files/user/"
            },
            {
                "name": "username",
                "type": "text",
                "label": "Username",
                "required": True
            },
            {
                "name": "password",
                "type": "password",
                "label": "Password",
                "required": True
            }
        ]
    },
    "libarchive": {
        "fields": [
            {
                "name": "path",
                "type": "text",
                "label": "Archive Path",
                "required": True,
                "placeholder": "/path/to/archive",
                "help": "Supports: tar, tar.gz, tar.bz2, zip, 7z, rar, etc."
            }
        ]
    },
    "base64": {
        "fields": [
            {
                "name": "data",
                "type": "textarea",
                "label": "Base64 Data",
                "required": True,
                "placeholder": "SGVsbG8gV29ybGQh",
                "help": "Base64 encoded content"
            }
        ]
    }
}


def get_backend_info(backend: str) -> Dict[str, Any]:
    """Get complete information for a backend.

    Args:
        backend: Backend name

    Returns:
        Dictionary with schema, capabilities, and description

    Raises:
        ValueError: If backend is not supported
    """
    if backend not in BACKEND_SCHEMAS:
        raise ValueError(f"Unknown backend: {backend}")

    return {
        "backend": backend,
        "schema": BACKEND_SCHEMAS[backend],
        "capabilities": CAPABILITIES[backend]
    }


def get_all_backends() -> List[str]:
    """Get list of all supported backends.

    Returns:
        List of backend names
    """
    return list(BACKEND_SCHEMAS.keys())


def get_backends_summary() -> List[Dict[str, Any]]:
    """Get summary information for all backends.

    Returns:
        List of dicts with name, description, and read-only status
    """
    return [
        {
            "name": name,
            "description": CAPABILITIES[name]["description"],
            "read_only": not CAPABILITIES[name]["write"]
        }
        for name in get_all_backends()
    ]
