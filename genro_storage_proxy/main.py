"""Main entry point for genro-storage-proxy server."""

import argparse
import asyncio
import configparser
from pathlib import Path

import uvicorn
from nicegui import ui

from genro_storage_proxy.api import create_app
from genro_storage_proxy.config_loader import load_volumes_from_config
from genro_storage_proxy.logger import get_logger

logger = get_logger("Main")


def load_server_config(config_path: str) -> dict:
    """Load server configuration from config.ini.

    Args:
        config_path: Path to config.ini file

    Returns:
        Dictionary with server configuration
    """
    config = configparser.ConfigParser()
    config.read(config_path)

    server_config = {}

    # Server section
    if config.has_section("server"):
        server_config["host"] = config.get("server", "host", fallback="0.0.0.0")
        server_config["port"] = config.getint("server", "port", fallback=8080)
        server_config["api_token"] = config.get("server", "api_token", fallback=None)

    # Storage section
    if config.has_section("storage"):
        server_config["db_path"] = config.get("storage", "db_path", fallback="/tmp/storage_proxy.db")

    return server_config


async def initialize_app(config_path: str):
    """Initialize the application and load volumes from config.

    Args:
        config_path: Path to config.ini file

    Returns:
        Configured FastAPI application
    """
    # Load server configuration
    server_config = load_server_config(config_path)

    # Create FastAPI app
    app = create_app(
        db_path=server_config.get("db_path", "/tmp/storage_proxy.db"),
        api_token=server_config.get("api_token"),
        config_path=config_path
    )

    # Initialize database
    await app.state.persistence.init_db()

    # NOTE: Volumes are NOT loaded automatically from config.ini on startup
    # Users must create volumes via the admin UI or API
    # To enable auto-loading, uncomment the code below:
    # try:
    #     count = await load_volumes_from_config(
    #         config_path,
    #         app.state.persistence,
    #         overwrite=False
    #     )
    #     logger.info(f"Loaded {count} volumes from config file")
    # except Exception as e:
    #     logger.warning(f"Could not load volumes from config: {e}")

    return app, server_config


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Genro Storage Proxy Server")
    parser.add_argument(
        "--config",
        "-c",
        default="config.ini",
        help="Path to config.ini file (default: config.ini)"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind to (overrides config file)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to (overrides config file)"
    )
    args = parser.parse_args()

    # Check if config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        logger.info("Create a config.ini file based on config.ini.example")
        return 1

    # Initialize app and load config
    app, server_config = asyncio.run(initialize_app(str(config_path)))

    # Override with command line arguments
    host = args.host or server_config.get("host", "0.0.0.0")
    port = args.port or server_config.get("port", 8080)

    logger.info(f"Starting server on {host}:{port}")

    # Initialize NiceGUI with FastAPI
    ui.run_with(
        app,
        storage_secret="change-this-secret-in-production"
    )

    # Start uvicorn server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

    return 0


if __name__ == "__main__":
    exit(main())
