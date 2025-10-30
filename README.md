# genro-storage-proxy

HTTP microservice that exposes [genro-storage](https://github.com/genropy/genro-storage) capabilities via REST API.

## Overview

**genro-storage-proxy** is a standalone FastAPI service that acts as a **storage aggregator** for microservice architectures. Instead of each microservice integrating storage libraries and managing configuration, services communicate with genro-storage-proxy via HTTP.

## Architecture Pattern

```
┌─────────────────────────────────────────┐
│   genro-storage-proxy                   │
│   - Single storage configuration        │
│   - Mounts: S3, GCS, Azure, local       │
│   - HTTP REST API                       │
│   - Multi-tenant support                │
└─────────────────────────────────────────┘
          ↑          ↑          ↑
     HTTP │     HTTP │     HTTP │
    ┌─────┴───┐ ┌───┴────┐ ┌──┴─────┐
    │ mail-   │ │ image- │ │ video- │
    │ proxy   │ │ proc   │ │ proc   │
    │ (Python)│ │ (Go)   │ │ (Rust) │
    └─────────┘ └────────┘ └────────┘
```

## Benefits

- **Polyglot Architecture**: Any language can use storage via HTTP
- **Centralized Configuration**: Single source of truth for storage mounts
- **Backend Transparency**: Switch S3→GCS without touching microservices
- **Separation of Concerns**: Storage logic isolated in one service
- **Multi-tenant Ready**: Per-tenant storage isolation

## API (Planned)

### File Operations
```
GET    /files/{mount}:{path}           - Download file
PUT    /files/{mount}:{path}           - Upload file
DELETE /files/{mount}:{path}           - Delete file
POST   /files/{mount}:{path}/copy      - Copy file
GET    /files/{mount}:{path}/metadata  - Get metadata
```

### Mount Management (Admin)
```
GET    /mounts                - List mounts
POST   /mounts                - Add mount dynamically
PUT    /mounts/{name}         - Update mount
DELETE /mounts/{name}         - Remove mount
```

## Status

🚧 **Planning Phase** - Not yet implemented

This is a placeholder repository for future development. See `docs/CONCEPT.md` for detailed planning.

## Related Projects

- [genro-storage](https://github.com/genropy/genro-storage) - Core storage library (required dependency)
- [genro-mail-proxy](https://github.com/genropy/genro-mail-proxy) - Potential consumer

## License

MIT
