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

"""FastAPI application for genro-storage-proxy.

Provides administrative endpoints for managing storage volumes.
"""

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import APIKeyHeader
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from genro_storage_proxy.persistence import Persistence
from genro_storage_proxy.config_loader import load_volumes_from_config
from genro_storage_proxy.logger import get_logger
from genro_storage_proxy.backend_schemas import (
    get_backend_info,
    get_all_backends,
    get_backends_summary
)
from genro_storage import StorageManager

logger = get_logger("API")

# Application state
app = FastAPI(
    title="Genro Storage Proxy",
    description="HTTP microservice that exposes genro-storage capabilities via REST API",
    version="0.1.0"
)
app.state.persistence = None
app.state.api_token = None
app.state.config_path = None
app.state.storage_manager = None

# API Token authentication
API_TOKEN_HEADER_NAME = "X-API-Token"
api_key_scheme = APIKeyHeader(name=API_TOKEN_HEADER_NAME, auto_error=False)


async def require_token(api_token: str | None = Depends(api_key_scheme)) -> None:
    """Validate the API token carried in the ``X-API-Token`` header.

    If a token has been configured and a request provides either a missing
    or different value, a ``401`` error is raised.
    When no token is configured the dependency is effectively bypassed.
    """
    expected = getattr(app.state, "api_token", None)
    if expected is None:
        return
    if not api_token or api_token != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API token")


auth_dependency = Depends(require_token)


# Pydantic models

class VolumePayload(BaseModel):
    """Volume definition for create/update operations."""
    name: str = Field(..., description="Unique volume name (e.g., 'uploads', 's3-data')")
    backend: str = Field(..., description="Backend type (s3, gcs, local, http, etc.)")
    config: Dict[str, Any] = Field(..., description="Backend-specific configuration as JSON object")


class VolumeResponse(BaseModel):
    """Volume information returned by API."""
    id: int
    name: str
    backend: str
    config: Dict[str, Any]
    created_at: str
    updated_at: str


class StatusResponse(BaseModel):
    """Base response for status operations."""
    ok: bool
    message: Optional[str] = None
    error: Optional[str] = None


class ReloadConfigResponse(StatusResponse):
    """Response for config reload operation."""
    volumes_loaded: Optional[int] = None


# Admin API endpoints

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with service information."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Genro Storage Proxy</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                border-radius: 10px;
                padding: 40px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                margin-top: 0;
            }
            .version {
                color: #666;
                font-size: 14px;
                margin-bottom: 30px;
            }
            .links {
                display: flex;
                gap: 15px;
                flex-direction: column;
            }
            .link-card {
                background: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                padding: 20px;
                text-decoration: none;
                color: inherit;
                transition: all 0.2s;
            }
            .link-card:hover {
                border-color: #007bff;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            .link-title {
                font-size: 18px;
                font-weight: 600;
                color: #007bff;
                margin-bottom: 5px;
            }
            .link-desc {
                font-size: 14px;
                color: #666;
            }
            .status {
                display: inline-block;
                padding: 4px 12px;
                background: #d4edda;
                color: #155724;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🗄️ Genro Storage Proxy</h1>
            <div class="version">
                Version 0.1.0 &nbsp;•&nbsp; <span class="status">● Running</span>
            </div>

            <div class="links">
                <a href="/admin/ui" class="link-card">
                    <div class="link-title">Admin Interface</div>
                    <div class="link-desc">Manage storage volumes and browse files</div>
                </a>

                <a href="/docs" class="link-card">
                    <div class="link-title">API Documentation</div>
                    <div class="link-desc">Interactive API documentation (Swagger UI)</div>
                </a>

                <a href="/health" class="link-card">
                    <div class="link-title">Health Check</div>
                    <div class="link-desc">Check service health status</div>
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/admin/volumes", response_model=List[VolumeResponse], dependencies=[auth_dependency])
async def list_volumes():
    """List all configured storage volumes.

    Requires authentication via X-API-Token header.
    """
    persistence: Persistence = app.state.persistence
    if not persistence:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Persistence not initialized")

    volumes = await persistence.list_volumes()
    return volumes


@app.get("/admin/volumes/{volume_name}", response_model=VolumeResponse, dependencies=[auth_dependency])
async def get_volume(volume_name: str):
    """Get details of a specific volume.

    Requires authentication via X-API-Token header.
    """
    persistence: Persistence = app.state.persistence
    if not persistence:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Persistence not initialized")

    volume = await persistence.get_volume(volume_name)
    if not volume:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Volume '{volume_name}' not found")

    return volume


@app.post("/admin/volumes", response_model=StatusResponse, dependencies=[auth_dependency])
async def create_volume(payload: VolumePayload):
    """Create or update a storage volume.

    Requires authentication via X-API-Token header.

    Example:
    ```json
    {
        "name": "s3-uploads",
        "backend": "s3",
        "config": {
            "bucket": "my-uploads",
            "region": "us-east-1"
        }
    }
    ```
    """
    persistence: Persistence = app.state.persistence
    if not persistence:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Persistence not initialized")

    try:
        await persistence.add_volume({
            "name": payload.name,
            "backend": payload.backend,
            "config": payload.config
        })
        return StatusResponse(ok=True, message=f"Volume '{payload.name}' created/updated successfully")
    except Exception as e:
        logger.error(f"Failed to create volume: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to create volume: {str(e)}")


@app.put("/admin/volumes/{volume_name}", response_model=StatusResponse, dependencies=[auth_dependency])
async def update_volume(volume_name: str, payload: VolumePayload):
    """Update an existing storage volume.

    Requires authentication via X-API-Token header.
    The volume name in the URL must match the name in the payload.
    """
    persistence: Persistence = app.state.persistence
    if not persistence:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Persistence not initialized")

    if volume_name != payload.name:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Volume name mismatch: URL has '{volume_name}' but payload has '{payload.name}'"
        )

    # Check if volume exists
    existing = await persistence.get_volume(volume_name)
    if not existing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Volume '{volume_name}' not found")

    try:
        await persistence.update_volume(volume_name, payload.backend, payload.config)
        return StatusResponse(ok=True, message=f"Volume '{volume_name}' updated successfully")
    except Exception as e:
        logger.error(f"Failed to update volume: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to update volume: {str(e)}")


@app.delete("/admin/volumes/{volume_name}", response_model=StatusResponse, dependencies=[auth_dependency])
async def delete_volume(volume_name: str):
    """Delete a storage volume.

    Requires authentication via X-API-Token header.
    """
    persistence: Persistence = app.state.persistence
    if not persistence:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Persistence not initialized")

    deleted = await persistence.delete_volume(volume_name)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Volume '{volume_name}' not found")

    return StatusResponse(ok=True, message=f"Volume '{volume_name}' deleted successfully")


@app.get("/admin/volumes/{volume_name}/browse")
async def browse_volume(volume_name: str, path: str = ""):
    """Browse files in a storage volume.

    Returns a list of files and directories for tree view.
    """
    storage_manager: StorageManager = app.state.storage_manager
    if not storage_manager:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Storage manager not initialized")

    try:
        # Check if volume exists
        if not storage_manager.has_mount(volume_name):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Volume '{volume_name}' not found")

        # Get storage node for the volume with path
        full_path = path or ""
        node = storage_manager.node(f"{volume_name}:{full_path}")

        items = []

        try:
            # List directory contents
            if node.isdir:  # isdir is a property, not a method
                for child_node in node.children():  # children() returns list of StorageNode objects
                    item = {
                        "id": child_node.path,  # Use node's path property
                        "label": child_node.basename,  # Use node's basename property
                        "icon": "folder" if child_node.isdir else "description",
                    }
                    # For directories, add children count
                    if child_node.isdir:
                        try:
                            children_list = list(child_node.children())
                            item["children_count"] = len(children_list)
                        except Exception:
                            item["children_count"] = 0
                    items.append(item)
        except Exception as e:
            logger.error(f"Error listing path '{full_path}' in volume '{volume_name}': {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error listing directory: {str(e)}")

        return items

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing volume '{volume_name}': {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error accessing volume: {str(e)}")


@app.post("/admin/reload-config", response_model=ReloadConfigResponse, dependencies=[auth_dependency])
async def reload_config(overwrite: bool = False):
    """Reload volumes from config.ini file.

    By default, only loads volumes that don't already exist in the database.
    Set overwrite=true to replace existing volumes with config file values.

    Requires authentication via X-API-Token header.
    """
    persistence: Persistence = app.state.persistence
    config_path: str = app.state.config_path

    if not persistence:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Persistence not initialized")

    if not config_path:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Config path not configured")

    try:
        count = await load_volumes_from_config(config_path, persistence, overwrite=overwrite)
        return ReloadConfigResponse(
            ok=True,
            message=f"Loaded {count} volumes from config",
            volumes_loaded=count
        )
    except FileNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except Exception as e:
        logger.error(f"Failed to reload config: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to reload config: {str(e)}")


# Application lifecycle

@app.on_event("startup")
async def startup_event():
    """Initialize persistence and storage manager on startup."""
    persistence = app.state.persistence
    storage_manager = app.state.storage_manager

    if persistence:
        await persistence.init_db()

        # Load volumes into storage manager
        if storage_manager:
            volumes = await persistence.list_volumes()
            for vol in volumes:
                try:
                    # Use configure() with proper format
                    storage_manager.configure([{
                        "name": vol["name"],
                        "type": vol["backend"],
                        **vol["config"]
                    }])
                    logger.info(f"Registered volume '{vol['name']}' ({vol['backend']})")
                except Exception as e:
                    logger.error(f"Failed to register volume '{vol['name']}': {e}")

        logger.info("Storage proxy started successfully")


def create_app(
    db_path: str = "/tmp/storage_proxy.db",
    api_token: Optional[str] = None,
    config_path: Optional[str] = None
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        db_path: Path to SQLite database
        api_token: Optional API token for authentication
        config_path: Optional path to config.ini file

    Returns:
        Configured FastAPI application
    """
    app.state.persistence = Persistence(db_path)
    app.state.api_token = api_token
    app.state.config_path = config_path
    app.state.storage_manager = StorageManager()

    # Initialize NiceGUI web interface
    from genro_storage_proxy.web_ui import init_ui
    init_ui(app.state.persistence, app.state.storage_manager)

    return app
