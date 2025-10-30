# Design Notes & Decisions

## Project Creation - 2025-10-29

### Why This Project?

**Problem**: In microservice architectures with polyglot services (Python, Go, Rust, Node.js), each service needs storage access. Current options:

1. **Each service integrates storage SDKs** → Duplication, different configs
2. **Direct cloud storage API** → Vendor lock-in, complex IAM
3. **MinIO** → S3-only, not multi-backend

**Solution**: genro-storage-proxy acts as a **storage aggregator** - one HTTP service that all microservices can use regardless of language.

### Key Design Decisions

#### 1. Language: Python with FastAPI

**Why Python?**
- Reuses genro-storage library (no reimplementation)
- FastAPI: async, fast, auto-docs, modern
- Storage is I/O-bound (Rust overhead not justified)

**Why not Rust/Go?**
- Would need to reimplement all backend logic
- Maintenance duplication
- Storage bottleneck is I/O, not CPU

#### 2. Architecture: Stateless HTTP Proxy

```
Microservices → HTTP → genro-storage-proxy → genro-storage → S3/GCS/Azure
```

**Benefits**:
- Horizontal scaling (stateless)
- Language-agnostic clients
- Centralized storage config
- Easy policy enforcement

#### 3. Authentication: JWT Primary, API Keys Secondary

**JWT** (Phase 1):
- Standard, widely supported
- Contains user claims
- Stateless validation

**API Keys** (Phase 2):
- Simpler for service-to-service
- Good for internal microservices

#### 4. Configuration: INI + Environment Variables

**INI file** for static mounts:
- Human-readable
- Standard format
- Easy to version control

**Dynamic API** for runtime mounts:
- Add/remove mounts without restart
- Multi-tenant use case
- Stored in memory (or optional DB)

#### 5. API Design: REST with Mount:Path Format

```
GET /files/uploads:documents/report.pdf
```

**Why mount:path?**
- Consistent with genro-storage syntax
- Clear separation of "where" and "what"
- Easy to understand

**Alternative considered**: `/files/{mount}/{path}`
- More REST-ful but loses genro-storage consistency

### Comparison with Alternatives

#### vs. Direct genro-storage Integration
**Direct**: Lower latency, Python-only
**Proxy**: Polyglot, centralized config

**Decision**: Both are valid - proxy for microservices, direct for Python apps

#### vs. MinIO
**MinIO**: S3-compatible, single backend
**Proxy**: Multi-backend, custom API

**Decision**: Different use cases - MinIO for S3 replacement, proxy for abstraction

#### vs. Cloud Storage APIs
**Direct APIs**: Feature-complete, vendor-specific
**Proxy**: Vendor-agnostic, simpler API

**Decision**: Proxy abstracts backends, easier to switch

### Use Cases Prioritized

1. **genro-mail-proxy** (first consumer)
   - Stores email attachments
   - Python service but validates polyglot pattern
   - Needs: upload, download, delete, list

2. **Multi-tenant platforms**
   - Each tenant gets own mount (S3 bucket)
   - Dynamic mount addition
   - Access control per tenant

3. **Image/video processing pipelines**
   - Go/Rust services process media
   - No Python dependencies needed
   - High throughput requirements

### Implementation Phases

**Phase 1 (MVP)**: Core file operations + JWT auth
- Validates concept
- Usable by genro-mail-proxy
- ~1-2 weeks

**Phase 2**: Production hardening + dynamic mounts
- Rate limiting, metrics, logging
- Ready for real deployments
- ~2-3 weeks

**Phase 3**: Enterprise features
- Multi-tenant, webhooks, audit logs
- Optional, based on demand
- ~3-4 weeks

### Open Questions & TODOs

1. **Streaming vs Buffering**
   - Large files (>100MB): stream or presigned URL?
   - Decision pending performance tests

2. **Mount Persistence**
   - Dynamic mounts stored where? Memory? SQLite? Redis?
   - Decision: Start with memory, add persistence later

3. **Error Handling Verbosity**
   - Detailed errors expose internals?
   - Decision: Configurable (verbose in dev, minimal in prod)

4. **Rate Limiting Strategy**
   - Per-user? Per-IP? Per-mount?
   - Decision: Per-user, configurable

5. **Admin API Security**
   - Separate admin token? Scope in JWT?
   - Decision: Separate token for simplicity

### Technical Constraints

- Requires genro-storage v0.3.0+ (async support)
- Python 3.9+ (type hints, async)
- Stateless (no local state except config)
- Docker-first deployment

### Performance Expectations

**Not a performance-critical service** (storage I/O is bottleneck):
- Target: <50ms overhead vs direct storage
- Throughput: 100+ req/sec per worker (FastAPI can handle this)
- Scalability: Horizontal (add workers/replicas)

**If performance becomes critical**:
- Add CDN in front
- Use presigned URLs for large files
- Implement Redis cache

### Security Considerations

**Threat Model**:
- Unauthorized access to files → JWT validation
- Path traversal attacks → Input validation
- DoS via large uploads → Rate limiting + size limits
- Credential exposure → Environment variables, never in responses

**Not in Scope** (delegate to infrastructure):
- DDoS protection → Cloudflare/WAF
- Network encryption → TLS termination at load balancer
- Secrets management → Kubernetes secrets / Vault

### Deployment Model

**Primary**: Kubernetes
- StatefulSet not needed (stateless)
- Horizontal scaling
- Health checks for liveness/readiness

**Also supports**: Docker Compose, bare metal
- Single server deployment
- Development/testing

### Testing Strategy

**Unit tests**: Core logic (auth, config, path parsing)
**Integration tests**: genro-storage operations
**API tests**: FastAPI TestClient
**Performance tests**: locust for load testing

**No need for**: Browser testing (API only)

### Documentation Priority

1. **README** - Quick start, architecture overview
2. **API reference** - Auto-generated from FastAPI
3. **Configuration guide** - INI format, env vars
4. **Integration examples** - Python, Go, JavaScript
5. **Deployment guide** - Docker, K8s

### Success Metrics

**Phase 1 (MVP)**:
- [ ] genro-mail-proxy can use it successfully
- [ ] API is intuitive (low learning curve)
- [ ] Deployment is straightforward (Docker Compose works)

**Phase 2 (Production)**:
- [ ] Handles 1000+ req/sec across cluster
- [ ] <50ms overhead vs direct storage
- [ ] Zero downtime for mount additions

**Phase 3 (Enterprise)**:
- [ ] Multiple tenants in production
- [ ] Community interest (GitHub stars, issues)
- [ ] Other projects adopt it

### Future Extensions (Maybe)

- GraphQL API alternative
- WebSocket notifications
- Image transformation on-the-fly
- Video transcoding integration
- File virus scanning
- Deduplication
- Compression

**Decision**: Only if demand emerges, keep MVP simple

### Lessons from genro-storage

**Keep**:
- Mount:path syntax (familiar)
- Multi-backend abstraction
- Comprehensive docs

**Avoid**:
- Feature creep (keep proxy simple)
- Premature optimization
- Complex configuration

### Team Notes

**Contributors**: Start with single maintainer
**License**: MIT (same as genro-storage)
**Versioning**: SemVer (0.1.0-dev → 0.1.0 → 1.0.0)
**Release cycle**: Rapid iteration until 1.0, then stable

### Questions for Future

1. Should we support GraphQL?
2. WebSocket for real-time file updates?
3. Built-in image transformation?
4. Integration with message queues (RabbitMQ)?
5. S3-compatible API for drop-in MinIO replacement?

**Answer**: Wait for user feedback, don't overengineer

---

## Next Steps

1. Create OpenAPI spec (API contract)
2. Set up FastAPI project structure
3. Implement Phase 1 MVP
4. Test with genro-mail-proxy
5. Iterate based on feedback
