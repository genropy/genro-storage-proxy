# genro-storage-proxy - Quick Start Guide

This guide will help you get genro-storage-proxy up and running quickly.

## Installation

### Development Installation

```bash
# Clone the repository (if not already done)
git clone https://github.com/genropy/genro-storage-proxy.git
cd genro-storage-proxy

# Install in development mode
pip install -e ".[dev]"
```

### Production Installation

```bash
pip install genro-storage-proxy
```

## Configuration

1. **Create a configuration file** by copying the example:

```bash
cp config.ini.example config.ini
```

2. **Edit config.ini** with your settings:

```ini
[server]
host = 0.0.0.0
port = 8080
api_token = your-secret-token-here  # Change this!

[storage]
db_path = /tmp/storage_proxy.db  # Change to persistent location in production

[volumes]
# Define your storage volumes
volume.local_uploads.backend = local
volume.local_uploads.config = {"path": "/data/uploads"}

volume.s3_documents.backend = s3
volume.s3_documents.config = {"bucket": "my-documents", "region": "us-east-1"}
```

⚠️ **Important**: Change the `api_token` to a secure random string!

## Running the Server

### Using the command-line tool

```bash
genro-storage-proxy --config config.ini
```

Or with command-line overrides:

```bash
genro-storage-proxy --config config.ini --host 127.0.0.1 --port 8000
```

### Using Python directly

```bash
python -m genro_storage_proxy.main --config config.ini
```

### Running in development mode

```bash
# From the project directory
python genro_storage_proxy/main.py --config config.ini
```

## Testing the API

### Health Check

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{"status": "healthy"}
```

### List Volumes

```bash
curl -H "X-API-Token: your-secret-token-here" \
  http://localhost:8080/admin/volumes
```

Expected response:
```json
[
  {
    "id": 1,
    "name": "local_uploads",
    "backend": "local",
    "config": {"path": "/data/uploads"},
    "created_at": "2025-10-30 12:00:00",
    "updated_at": "2025-10-30 12:00:00"
  },
  {
    "id": 2,
    "name": "s3_documents",
    "backend": "s3",
    "config": {"bucket": "my-documents", "region": "us-east-1"},
    "created_at": "2025-10-30 12:00:00",
    "updated_at": "2025-10-30 12:00:00"
  }
]
```

### Get Volume Details

```bash
curl -H "X-API-Token: your-secret-token-here" \
  http://localhost:8080/admin/volumes/local_uploads
```

### Create a New Volume

```bash
curl -X POST \
  -H "X-API-Token: your-secret-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "gcs_backups",
    "backend": "gcs",
    "config": {"bucket": "my-backups", "project": "my-project"}
  }' \
  http://localhost:8080/admin/volumes
```

Expected response:
```json
{
  "ok": true,
  "message": "Volume 'gcs_backups' created/updated successfully"
}
```

### Update an Existing Volume

```bash
curl -X PUT \
  -H "X-API-Token: your-secret-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "local_uploads",
    "backend": "local",
    "config": {"path": "/new/data/path"}
  }' \
  http://localhost:8080/admin/volumes/local_uploads
```

### Delete a Volume

```bash
curl -X DELETE \
  -H "X-API-Token: your-secret-token-here" \
  http://localhost:8080/admin/volumes/gcs_backups
```

### Reload Configuration from File

```bash
curl -X POST \
  -H "X-API-Token: your-secret-token-here" \
  http://localhost:8080/admin/reload-config
```

To force overwrite of existing volumes:

```bash
curl -X POST \
  -H "X-API-Token: your-secret-token-here" \
  "http://localhost:8080/admin/reload-config?overwrite=true"
```

## API Documentation

Once the server is running, you can access the interactive API documentation:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## Next Steps

1. **Configure your storage volumes** in `config.ini`
2. **Set a secure API token**
3. **Test the admin endpoints** using the examples above
4. **Integrate with genro-storage** to enable file operations (coming soon)

## Troubleshooting

### Cannot connect to server

- Check that the server is running: `ps aux | grep genro-storage-proxy`
- Verify the host and port in config.ini
- Check firewall rules

### 401 Unauthorized

- Ensure you're sending the correct `X-API-Token` header
- Verify the token matches the one in `config.ini`

### Volumes not loading from config

- Check the config.ini syntax (JSON must be valid)
- Look for errors in the server logs
- Use `/admin/reload-config` endpoint to reload manually

## Production Deployment

For production:

1. **Use a persistent database path** (not /tmp)
2. **Generate a strong API token** (use `openssl rand -hex 32`)
3. **Use a reverse proxy** (nginx, traefik) with HTTPS
4. **Set appropriate file permissions** on config.ini (600)
5. **Consider using environment variables** for sensitive data
6. **Run as a systemd service** or in Docker

Example systemd service:

```ini
[Unit]
Description=Genro Storage Proxy
After=network.target

[Service]
Type=simple
User=genro
WorkingDirectory=/opt/genro-storage-proxy
ExecStart=/usr/local/bin/genro-storage-proxy --config /etc/genro-storage-proxy/config.ini
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Support

- **Documentation**: https://github.com/genropy/genro-storage-proxy
- **Issues**: https://github.com/genropy/genro-storage-proxy/issues
