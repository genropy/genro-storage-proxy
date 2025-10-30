# genro-storage-proxy - Concept & Architecture

## Vision

A lightweight HTTP microservice that exposes genro-storage functionality via REST API, designed as a **storage aggregator** for polyglot microservice architectures.

## Problem Statement

In a microservices architecture with services written in different languages (Python, Go, Rust, Node.js), each service needs storage access:

**Current approach (without proxy):**
- Each service integrates language-specific storage SDKs
- Each service manages its own storage configuration
- Changing storage backend (S3→GCS) requires updating all services
- No centralized storage policies or access control

**With genro-storage-proxy:**
- Single HTTP endpoint for all storage operations
- Centralized configuration (change once, affects all services)
- Polyglot: any language with HTTP client can use it
- Separation of concerns: storage logic isolated

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  genro-storage-proxy                     │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  FastAPI    │  │  JWT Auth    │  │  Rate Limiter  │  │
│  │  HTTP API   │  │  API Keys    │  │                │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬───────┘  │
│         │                 │                   │          │
│  ┌──────┴─────────────────┴───────────────────┴───────┐  │
│  │         AsyncStorageManager (genro-storage)        │  │
│  │         - Mount management                          │  │
│  │         - File operations                           │  │
│  └─────────────────┬───────────────────────────────────┘  │
│                    │                                      │
└────────────────────┼──────────────────────────────────────┘
                     │
     ┌───────────────┼───────────────┐
     │               │               │
  ┌──▼───┐      ┌───▼────┐     ┌───▼────┐
  │  S3  │      │  GCS   │     │ Local  │
  └──────┘      └────────┘     └────────┘
```

## Use Cases

### 1. Multi-Language Microservices

```python
# genro-mail-proxy (Python)
response = requests.put(
    'http://storage-proxy:8080/files/attachments:email123/file.pdf',
    files={'file': pdf_data},
    headers={'Authorization': f'Bearer {token}'}
)
```

```go
// image-processor (Go)
resp, err := http.Get("http://storage-proxy:8080/files/images:photo.jpg")
defer resp.Body.Close()
data, _ := ioutil.ReadAll(resp.Body)
```

```rust
// video-transcoder (Rust)
let client = reqwest::Client::new();
let res = client.get("http://storage-proxy:8080/files/videos:movie.mp4")
    .header("Authorization", format!("Bearer {}", token))
    .send()
    .await?;
```

### 2. Dynamic Storage Configuration

Admin adds new tenant storage without restarting services:

```bash
curl -X POST http://storage-proxy:8080/admin/mounts \
  -H 'Authorization: Bearer ADMIN_TOKEN' \
  -d '{
    "name": "tenant_acme",
    "type": "s3",
    "bucket": "acme-storage",
    "region": "eu-west-1"
  }'
```

All microservices can immediately use:
```
GET /files/tenant_acme:documents/invoice.pdf
```

### 3. Centralized Access Control

```python
# Storage proxy enforces policies
@app.get("/files/{mount}:{path}")
async def get_file(mount: str, path: str, user: User = Depends(get_current_user)):
    # Check if user has access to this mount/tenant
    if not user.has_access(mount):
        raise HTTPException(403, "Access denied")

    # genro-storage does the actual I/O
    node = storage.node(f'{mount}:{path}')
    return await node.read_bytes()
```

## API Design

### File Operations

#### Upload File
```http
PUT /files/{mount}:{path}
Authorization: Bearer TOKEN
Content-Type: multipart/form-data

Returns:
{
  "path": "uploads:documents/report.pdf",
  "size": 1024,
  "mimetype": "application/pdf",
  "etag": "abc123"
}
```

#### Download File
```http
GET /files/{mount}:{path}
Authorization: Bearer TOKEN

Returns: file bytes
Headers:
  Content-Type: application/pdf
  Content-Length: 1024
  ETag: "abc123"
```

#### Delete File
```http
DELETE /files/{mount}:{path}
Authorization: Bearer TOKEN

Returns:
{
  "deleted": true
}
```

#### Copy File
```http
POST /files/{mount}:{path}/copy
Authorization: Bearer TOKEN
Content-Type: application/json
{
  "destination": "backups:documents/report.pdf"
}

Returns:
{
  "source": "uploads:documents/report.pdf",
  "destination": "backups:documents/report.pdf",
  "size": 1024
}
```

#### List Directory
```http
GET /files/{mount}:{path}?list=true
Authorization: Bearer TOKEN

Returns:
{
  "path": "uploads:documents/",
  "children": [
    {
      "name": "report.pdf",
      "size": 1024,
      "mtime": "2025-10-29T10:00:00Z",
      "is_dir": false
    },
    {
      "name": "images",
      "is_dir": true
    }
  ]
}
```

#### Get Metadata
```http
GET /files/{mount}:{path}/metadata
Authorization: Bearer TOKEN

Returns:
{
  "path": "uploads:documents/report.pdf",
  "size": 1024,
  "mtime": "2025-10-29T10:00:00Z",
  "mimetype": "application/pdf",
  "metadata": {
    "author": "John Doe",
    "custom-field": "value"
  }
}
```

### Mount Management (Admin)

#### List Mounts
```http
GET /admin/mounts
Authorization: Bearer ADMIN_TOKEN

Returns:
{
  "mounts": [
    {
      "name": "uploads",
      "type": "s3",
      "bucket": "company-uploads"
    },
    {
      "name": "backups",
      "type": "local",
      "path": "/data/backups"
    }
  ]
}
```

#### Add Mount
```http
POST /admin/mounts
Authorization: Bearer ADMIN_TOKEN
Content-Type: application/json
{
  "name": "new_tenant",
  "type": "s3",
  "bucket": "tenant-storage",
  "region": "us-east-1"
}

Returns:
{
  "name": "new_tenant",
  "status": "created"
}
```

#### Remove Mount
```http
DELETE /admin/mounts/{name}
Authorization: Bearer ADMIN_TOKEN

Returns:
{
  "name": "old_tenant",
  "status": "deleted"
}
```

### Health & Metrics

```http
GET /health
Returns:
{
  "status": "healthy",
  "mounts": 5,
  "version": "0.1.0"
}

GET /metrics
Returns: Prometheus metrics
```

## Configuration

### INI File (Static Configuration)

```ini
# storage-proxy.ini

[server]
host = 0.0.0.0
port = 8080
workers = 4

[auth]
type = jwt
jwt_secret = ${JWT_SECRET}
jwt_algorithm = HS256

# Or API key auth
# type = apikey
# api_keys = ${API_KEYS}  # comma-separated

[admin]
# Admin API for mount management
enabled = true
admin_token = ${ADMIN_TOKEN}

[rate_limit]
enabled = true
requests_per_minute = 100

# Static mounts
[mount:uploads]
type = s3
bucket = company-uploads
region = eu-west-1

[mount:backups]
type = local
path = /data/backups

[mount:public]
type = s3
bucket = public-assets
anon = true
```

### Environment Variables

```bash
# Required
JWT_SECRET=your-secret-key
ADMIN_TOKEN=admin-secure-token

# Optional
STORAGE_PROXY_HOST=0.0.0.0
STORAGE_PROXY_PORT=8080
LOG_LEVEL=info
```

## Security

### Authentication

**Option 1: JWT Tokens**
- Services get JWT from auth service
- Storage proxy validates token
- Token contains user ID and permissions

**Option 2: API Keys**
- Each service has API key
- Storage proxy validates key
- Simple but less flexible

### Authorization

**Mount-level access control:**
```python
# User can only access certain mounts
user_permissions = {
    "user123": ["uploads", "public"],
    "admin": ["*"]  # All mounts
}
```

**Path-level access control:**
```python
# User can only access their own files
# uploads:users/{user_id}/* → only accessible by user_id
```

### Rate Limiting

```python
# Per-user rate limits
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/files/{mount}:{path}")
@limiter.limit("100/minute")
async def get_file(...):
    ...
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "genro_storage_proxy.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  storage-proxy:
    build: .
    ports:
      - "8080:8080"
    environment:
      JWT_SECRET: ${JWT_SECRET}
      ADMIN_TOKEN: ${ADMIN_TOKEN}
    volumes:
      - ./config/storage.ini:/app/config/storage.ini
      - /data/backups:/data/backups
    restart: unless-stopped

  mail-proxy:
    image: genro-mail-proxy:latest
    environment:
      STORAGE_PROXY_URL: http://storage-proxy:8080
      STORAGE_TOKEN: ${MAIL_PROXY_TOKEN}
    depends_on:
      - storage-proxy
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: storage-proxy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: storage-proxy
  template:
    metadata:
      labels:
        app: storage-proxy
    spec:
      containers:
      - name: storage-proxy
        image: genro-storage-proxy:0.1.0
        ports:
        - containerPort: 8080
        env:
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: storage-proxy-secrets
              key: jwt-secret
        volumeMounts:
        - name: config
          mountPath: /app/config
      volumes:
      - name: config
        configMap:
          name: storage-proxy-config
---
apiVersion: v1
kind: Service
metadata:
  name: storage-proxy
spec:
  selector:
    app: storage-proxy
  ports:
  - port: 8080
    targetPort: 8080
  type: ClusterIP
```

## Implementation Phases

### Phase 1: MVP (Core Functionality)
- [ ] Basic FastAPI structure
- [ ] File CRUD operations (GET, PUT, DELETE)
- [ ] Static INI configuration
- [ ] JWT authentication
- [ ] Basic error handling
- [ ] Docker image
- [ ] Integration with genro-storage async API

**Target: 1-2 weeks**

### Phase 2: Production Ready
- [ ] Dynamic mount management API
- [ ] Rate limiting
- [ ] Comprehensive error handling
- [ ] Logging and metrics
- [ ] Health checks
- [ ] Documentation
- [ ] Unit and integration tests

**Target: 2-3 weeks**

### Phase 3: Enterprise Features
- [ ] Multi-tenant support
- [ ] Path-level authorization
- [ ] Streaming uploads/downloads
- [ ] Webhook notifications
- [ ] Audit logging
- [ ] Prometheus metrics
- [ ] OpenAPI/Swagger docs

**Target: 3-4 weeks**

## Technology Stack

- **Framework**: FastAPI (async, high performance, auto-docs)
- **Storage**: genro-storage with async wrapper (v0.3.0+)
- **Auth**: JWT via python-jose or API keys
- **Rate Limiting**: slowapi
- **Config**: python-dotenv + configparser (INI)
- **Logging**: structlog
- **Metrics**: prometheus-fastapi-instrumentator
- **Testing**: pytest + pytest-asyncio
- **Docker**: Multi-stage builds for minimal image

## Dependencies

```toml
[project]
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "genro-storage[async]>=0.3.0",
    "python-jose[cryptography]>=3.3.0",  # JWT
    "python-multipart>=0.0.6",  # File uploads
    "slowapi>=0.1.9",  # Rate limiting
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",  # FastAPI test client
    "black>=23.0",
    "ruff>=0.1.0",
]
```

## Performance Considerations

### Caching
- ETag support for client-side caching
- Optional Redis cache for frequently accessed files
- CDN integration (Cloudflare, CloudFront)

### Scalability
- Stateless design (horizontal scaling)
- Async I/O (handles many concurrent requests)
- Streaming for large files (no memory buffer)

### Benchmarks (Target)
- **Small files (<1MB)**: 100+ req/sec per worker
- **Large files (10MB+)**: Limited by network, not CPU
- **Latency**: < 50ms overhead vs direct storage access

## Monitoring

```python
from prometheus_fastapi_instrumentator import Instrumentator

# Automatic metrics
Instrumentator().instrument(app).expose(app)

# Custom metrics
from prometheus_client import Counter, Histogram

file_downloads = Counter('storage_downloads_total', 'Total file downloads', ['mount'])
file_size = Histogram('storage_file_size_bytes', 'File sizes', ['mount'])
```

**Metrics to track:**
- Requests per endpoint
- Response times
- File sizes
- Storage backend latency
- Error rates
- Active mounts

## Future Extensions

- **GraphQL API** (alternative to REST)
- **WebSocket** for real-time updates
- **Batch operations** (upload/delete multiple)
- **File versioning** (expose S3 versions)
- **Temporary signed URLs** (direct S3 access for large files)
- **Image transformation** (resize, crop on-the-fly)
- **Virus scanning** integration

## Comparison with Alternatives

### vs. Direct genro-storage Integration
**Direct:**
- Lower latency (no HTTP hop)
- Language-specific (Python only)
- Each service manages config

**Proxy:**
- Polyglot (any language)
- Centralized config
- Easier policy enforcement

### vs. MinIO
**MinIO:**
- S3-compatible API only
- Single backend type (MinIO itself)
- Requires S3 client library

**genro-storage-proxy:**
- Multi-backend (S3, GCS, Azure, local)
- Custom REST API (simpler than S3 API)
- Language-agnostic HTTP

### vs. Cloud Storage Directly
**Direct (S3/GCS SDK):**
- Vendor lock-in
- Requires SDK in each language
- Complex IAM/permissions

**Proxy:**
- Backend-agnostic
- Simple HTTP API
- Centralized access control

## Open Questions

1. **Streaming uploads**: Chunked upload for large files? Multipart?
2. **Transactions**: Atomic multi-file operations?
3. **Quotas**: Per-tenant storage limits?
4. **CDN integration**: Automatic CloudFront/Cloudflare integration?
5. **Encryption**: Server-side encryption for local storage?

## Next Steps

1. Create basic project structure
2. Implement MVP (Phase 1)
3. Test with genro-mail-proxy as first consumer
4. Gather feedback and iterate
5. Stabilize API (v1.0)

## License

MIT (same as genro-storage)
