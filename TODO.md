# genro-storage-proxy - TODO & Ideas

## Planning Phase (Current)

- [x] Create project structure
- [x] Document concept and architecture
- [ ] Define API contracts (OpenAPI spec)
- [ ] Design configuration schema
- [ ] Choose auth strategy (JWT vs API keys)
- [ ] Plan testing strategy

## Phase 1: MVP (Not Started)

### Core Features
- [ ] FastAPI project setup
- [ ] Configuration loading (INI + env vars)
- [ ] Storage manager initialization
- [ ] Basic endpoints:
  - [ ] GET /files/{mount}:{path}
  - [ ] PUT /files/{mount}:{path}
  - [ ] DELETE /files/{mount}:{path}
- [ ] JWT authentication
- [ ] Error handling
- [ ] Docker image

### Testing
- [ ] Unit tests for core logic
- [ ] Integration tests with genro-storage
- [ ] API tests with FastAPI TestClient

### Documentation
- [ ] API documentation (auto-generated from FastAPI)
- [ ] Setup guide
- [ ] Configuration reference

## Phase 2: Production Ready (Future)

- [ ] Dynamic mount management API
- [ ] Rate limiting
- [ ] Structured logging
- [ ] Health checks
- [ ] Prometheus metrics
- [ ] Comprehensive error responses
- [ ] File streaming for large files

## Phase 3: Enterprise (Future)

- [ ] Multi-tenant support
- [ ] Path-level authorization
- [ ] Webhook notifications
- [ ] Audit logging
- [ ] Admin dashboard UI

## Open Decisions

### Authentication
- **Option A**: JWT tokens (more flexible, standard)
- **Option B**: API keys (simpler, good for service-to-service)
- **Decision**: Start with JWT, add API keys later?

### Configuration Persistence
- **Option A**: Static INI file only
- **Option B**: INI + dynamic mounts in SQLite
- **Option C**: INI + dynamic mounts in Redis
- **Decision**: Start with INI only, add persistence later?

### Large File Handling
- **Option A**: Buffer in memory (simple, limited size)
- **Option B**: Stream through proxy (more complex, no size limit)
- **Option C**: Generate presigned URL (most efficient, less control)
- **Decision**: Start with streaming, add presigned URL option?

### Error Handling
- **Option A**: Generic error messages
- **Option B**: Detailed errors (might expose internals)
- **Decision**: Detailed for development, configurable for production?

## Ideas for Future

- [ ] GraphQL API as alternative to REST
- [ ] WebSocket support for real-time notifications
- [ ] Batch operations (upload/delete multiple files)
- [ ] Image transformation (resize, crop)
- [ ] Video thumbnail generation
- [ ] File virus scanning integration
- [ ] Temporary presigned URLs for direct S3 access
- [ ] CDN integration (Cloudflare, CloudFront)
- [ ] File deduplication
- [ ] Compression on-the-fly

## Questions to Answer

1. Should mount names be validated (regex)?
2. Max file size limit (configurable)?
3. Should we support multipart uploads?
4. How to handle mount conflicts (same name)?
5. Should we expose S3 versioning through API?
6. Rate limiting: per-user or per-IP or both?
7. Should we support file locking?
8. How to handle storage backend failures?

## Related Projects to Study

- [MinIO](https://min.io/) - S3-compatible storage
- [SeaweedFS](https://github.com/seaweedfs/seaweedfs) - Distributed file system
- [Minio/console](https://github.com/minio/console) - Object storage UI
- [Nextcloud](https://nextcloud.com/) - Self-hosted file sync

## Performance Targets

- **Latency**: < 50ms overhead vs direct storage
- **Throughput**: 100+ req/sec per worker for small files
- **Concurrency**: 1000+ concurrent connections
- **Memory**: < 512MB base + streaming (no buffering)

## Testing Strategy

### Unit Tests
- Configuration parsing
- Auth validation
- Path normalization
- Error handling

### Integration Tests
- genro-storage backend operations
- Mount management
- File operations end-to-end

### Performance Tests
- Load testing with locust
- Stress testing with ab/wrk
- Memory profiling with py-spy

### Security Tests
- Auth bypass attempts
- Path traversal attempts
- Rate limit verification

## Deployment Considerations

- [ ] Health checks for K8s liveness/readiness
- [ ] Graceful shutdown handling
- [ ] Signal handling (SIGTERM)
- [ ] Connection pooling for storage backends
- [ ] Resource limits (CPU, memory)

## Documentation Needed

- [ ] README with quick start
- [ ] Architecture diagram
- [ ] API reference (OpenAPI)
- [ ] Configuration guide
- [ ] Deployment guide (Docker, K8s)
- [ ] Security best practices
- [ ] Integration examples (Python, Go, Rust, JS)
- [ ] Troubleshooting guide

## Notes

- Wait for genro-storage v0.3.0 to be stable
- Consider genro-mail-proxy as first integration target
- Keep API simple and RESTful
- Prioritize developer experience
- Document everything
