# genro-storage-proxy - Administrative API

**Version:** 1.0
**Date:** 2025-10-30
**Status:** Draft

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Schema](#database-schema)
4. [Authentication Model](#authentication-model)
5. [Configuration](#configuration)
6. [Volume Management API](#volume-management-api)
7. [User Management API](#user-management-api)
8. [Permission Management API](#permission-management-api)
9. [Security Considerations](#security-considerations)

---

## Overview

genro-storage-proxy provides a REST API for managing storage volumes and users in a multi-tenant environment. The administrative API handles:

- **Volume Management**: Create, configure, and delete storage backends
- **User Management**: Manage users and sub-users with token-based authentication
- **Permission Management**: Control access to volumes with granular permissions

### Three-Tier Authentication Model

- **Owner**: Administrative access (configured in `config.ini`)
- **User**: Can manage own volumes and create sub-users
- **Sub-user**: Read-only access to assigned volumes

All administrative operations require token-based authentication via the `Authorization: Bearer <token>` header.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  genro-storage-proxy (FastAPI)              │
│                                                              │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │ Admin API      │  │ File API     │  │ Auth Middleware │ │
│  │ /admin/*       │  │ /files/*     │  │ Token validation│ │
│  └────────┬───────┘  └──────────────┘  └────────┬────────┘ │
│           │                                      │          │
│  ┌────────┴──────────────────────────────────────┴───────┐ │
│  │            SQLite Database                            │ │
│  │  - volumes                                            │ │
│  │  - users                                              │ │
│  │  - user_volumes (permissions)                         │ │
│  └─────────────────────────┬─────────────────────────────┘ │
│                            │                                │
│  ┌─────────────────────────▼─────────────────────────────┐ │
│  │      AsyncStorageManager (genro-storage)              │ │
│  │      - Dynamic volume mounting                        │ │
│  │      - Multi-backend support                          │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Table: `volumes`

Stores storage volume configurations.

```sql
CREATE TABLE volumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,           -- Volume name (e.g., "uploads", "s3-bucket")
    backend TEXT NOT NULL,                -- Backend type (s3, gcs, local, http, etc.)
    config JSON NOT NULL,                 -- Backend-specific configuration
    owner_id INTEGER,                     -- User who owns this volume (NULL = owner-created)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**Fields**:
- `name`: Unique volume identifier used in `mount:path` format
- `backend`: Type of storage backend (s3, gcs, azure, local, http, webdav, sftp, zip, tar, etc.)
- `config`: JSON object with backend-specific configuration (bucket, credentials, paths, etc.)
- `owner_id`: NULL for owner-created volumes (global), user_id for user-created volumes

**Example rows**:
```json
{
  "id": 1,
  "name": "shared-uploads",
  "backend": "s3",
  "config": {"bucket": "company-uploads", "region": "us-east-1"},
  "owner_id": null
}
{
  "id": 2,
  "name": "user-alice-data",
  "backend": "local",
  "config": {"path": "/data/users/alice"},
  "owner_id": 5
}
```

---

### Table: `users`

Stores user accounts and authentication tokens.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,       -- Username for identification
    token TEXT UNIQUE NOT NULL,          -- Authentication token
    role TEXT NOT NULL CHECK(role IN ('owner', 'user', 'subuser')),
    parent_user_id INTEGER,              -- For sub-users, references parent user
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**Roles**:
- `owner`: Administrative account (configured in config.ini, single instance)
- `user`: Can manage own volumes and create sub-users
- `subuser`: Read-only access to assigned volumes only

**Hierarchy**:
```
owner (root)
├─ user1
│  ├─ subuser1a
│  └─ subuser1b
└─ user2
   └─ subuser2a
```

**Example rows**:
```json
{
  "id": 1,
  "username": "admin",
  "token": "owner_token_from_config",
  "role": "owner",
  "parent_user_id": null
}
{
  "id": 5,
  "username": "alice",
  "token": "alice_secure_token_123",
  "role": "user",
  "parent_user_id": null
}
{
  "id": 12,
  "username": "alice_readonly",
  "token": "subuser_token_456",
  "role": "subuser",
  "parent_user_id": 5
}
```

---

### Table: `user_volumes`

Maps users to volumes they can access with permission levels.

```sql
CREATE TABLE user_volumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    volume_id INTEGER NOT NULL,
    permissions TEXT NOT NULL CHECK(permissions IN ('readonly', 'readwrite', 'delete')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (volume_id) REFERENCES volumes(id) ON DELETE CASCADE,
    UNIQUE(user_id, volume_id)
);
```

**Permission levels**:
- `readonly`: Can read files only (GET operations)
- `readwrite`: Can read, write, create files (GET, PUT operations)
- `delete`: Full access including delete operations (GET, PUT, DELETE operations)

**Implicit permissions**:
- Owner: Full access to all volumes (no entries needed in this table)
- User: Full access to volumes where `volumes.owner_id = user.id`

**Example rows**:
```json
{
  "id": 1,
  "user_id": 5,
  "volume_id": 1,
  "permissions": "readwrite"
}
{
  "id": 2,
  "user_id": 12,
  "volume_id": 1,
  "permissions": "readonly"
}
```

---

## Authentication Model

### Token-Based Authentication

All requests to `/admin/*` and `/files/*` require:
```
Authorization: Bearer <token>
```

### Token Validation Flow

```
1. Extract token from Authorization header
2. Query: SELECT * FROM users WHERE token = ?
3. If not found → 401 Unauthorized
4. If found → Set current_user context
5. Check operation permission based on role and resource ownership
6. Execute request or return 403 Forbidden
```

### Role Permissions Matrix

| Operation | Owner | User (own resource) | User (others) | Sub-user |
|-----------|-------|---------------------|---------------|----------|
| Create volume | ✅ | ✅ | ❌ | ❌ |
| Delete volume | ✅ (all) | ✅ (own) | ❌ | ❌ |
| View volume | ✅ (all) | ✅ (own + shared) | ❌ | ❌ |
| Create user | ✅ | ✅ (sub-user only) | ❌ | ❌ |
| Delete user | ✅ (all) | ✅ (own sub-users) | ❌ | ❌ |
| Grant permissions | ✅ | ✅ (own volumes) | ❌ | ❌ |
| Read file | ✅ (all) | ✅ (with permission) | ❌ | ✅ (with permission) |
| Write file | ✅ (all) | ✅ (readwrite+) | ❌ | ❌ |
| Delete file | ✅ (all) | ✅ (delete perm) | ❌ | ❌ |

---

## Configuration

### config.ini

```ini
[server]
host = 0.0.0.0
port = 8080
workers = 4

[database]
path = /var/lib/genro-storage-proxy/proxy.db

[auth]
# Owner (admin) token for administrative operations
owner_token = ${OWNER_TOKEN}

[logging]
level = info
format = json
```

### Environment Variables

```bash
# Required
OWNER_TOKEN=your-secure-admin-token-here

# Optional
STORAGE_PROXY_HOST=0.0.0.0
STORAGE_PROXY_PORT=8080
STORAGE_PROXY_DB=/var/lib/genro-storage-proxy/proxy.db
LOG_LEVEL=info
```

### Owner User Initialization

On first startup, the owner user is automatically created:

```python
# Pseudocode
if not db.query(User).filter(role='owner').first():
    owner = User(
        username='admin',
        token=config.auth.owner_token,
        role='owner'
    )
    db.add(owner)
    db.commit()
```

---

## Volume Management API

### Create Volume

**Endpoint**: `POST /admin/volumes`

**Authorization**: Owner or User

**Request Body**:
```json
{
  "name": "my-storage",
  "backend": "s3",
  "config": {
    "bucket": "my-bucket",
    "region": "us-east-1",
    "access_key": "AKIAIOSFODNN7EXAMPLE",
    "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
  }
}
```

**Response** (201 Created):
```json
{
  "id": 15,
  "name": "my-storage",
  "backend": "s3",
  "config": {
    "bucket": "my-bucket",
    "region": "us-east-1"
  },
  "owner_id": 5,
  "created_at": "2025-10-30T10:00:00Z"
}
```

**Notes**:
- If caller is User: `owner_id` set to their `user_id`
- If caller is Owner: `owner_id` is NULL (global/shared volume)
- Volume `name` must be unique globally
- Credentials in `config` are not returned in responses (security)

**Supported backends**:
- `s3`: Amazon S3 and compatible
- `gcs`: Google Cloud Storage
- `azure`: Azure Blob Storage
- `local`: Local filesystem
- `http`: HTTP/HTTPS (read-only)
- `webdav`: WebDAV (Nextcloud, ownCloud, SharePoint)
- `sftp`: SFTP/SSH
- `smb`: SMB/CIFS shares
- `zip`: ZIP archive mount
- `tar`: TAR archive mount
- `memory`: In-memory storage (testing)
- `base64`: Inline base64 data

---

### List Volumes

**Endpoint**: `GET /admin/volumes`

**Authorization**: Owner (all volumes) or User (own volumes + shared)

**Query Parameters**:
- `owner_id` (optional): Filter by owner (Owner only)

**Response** (200 OK):
```json
{
  "volumes": [
    {
      "id": 1,
      "name": "shared-uploads",
      "backend": "s3",
      "config": {"bucket": "company-uploads"},
      "owner_id": null,
      "created_at": "2025-10-29T10:00:00Z"
    },
    {
      "id": 15,
      "name": "my-storage",
      "backend": "s3",
      "config": {"bucket": "my-bucket"},
      "owner_id": 5,
      "created_at": "2025-10-30T10:00:00Z"
    }
  ]
}
```

**Filtering logic**:
- Owner sees: all volumes
- User sees: volumes where `owner_id = user.id` OR `owner_id IS NULL` OR has entry in `user_volumes`

---

### Get Volume

**Endpoint**: `GET /admin/volumes/{volume_id}`

**Authorization**: Owner or User (if owns or has access)

**Response** (200 OK):
```json
{
  "id": 15,
  "name": "my-storage",
  "backend": "s3",
  "config": {
    "bucket": "my-bucket",
    "region": "us-east-1"
  },
  "owner_id": 5,
  "created_at": "2025-10-30T10:00:00Z",
  "updated_at": "2025-10-30T10:00:00Z",
  "permissions": [
    {
      "user_id": 5,
      "username": "alice",
      "permissions": "delete"
    },
    {
      "user_id": 12,
      "username": "alice_readonly",
      "permissions": "readonly"
    }
  ]
}
```

**Notes**:
- `permissions` array shows all users with explicit access
- Owner's implicit full access not listed

---

### Update Volume

**Endpoint**: `PUT /admin/volumes/{volume_id}`

**Authorization**: Owner or User (if owns)

**Request Body**:
```json
{
  "config": {
    "bucket": "my-new-bucket",
    "region": "eu-west-1"
  }
}
```

**Response** (200 OK):
```json
{
  "id": 15,
  "name": "my-storage",
  "backend": "s3",
  "config": {
    "bucket": "my-new-bucket",
    "region": "eu-west-1"
  },
  "owner_id": 5,
  "updated_at": "2025-10-30T11:00:00Z"
}
```

**Notes**:
- Cannot change `name` or `backend` (delete and recreate instead)
- Volume is unmounted and remounted automatically with new config
- Active file operations may fail during remount

---

### Delete Volume

**Endpoint**: `DELETE /admin/volumes/{volume_id}`

**Authorization**: Owner or User (if owns)

**Response** (200 OK):
```json
{
  "deleted": true,
  "volume_id": 15,
  "name": "my-storage"
}
```

**Notes**:
- Cascades: removes all `user_volumes` entries
- Does NOT delete actual files in storage backend
- Volume unmounted from AsyncStorageManager

---

### Mount Volume from Archive

**Endpoint**: `POST /admin/volumes/from-archive`

**Authorization**: Owner or User

**Request Body**:
```json
{
  "name": "archive-vol",
  "type": "zip",
  "file": "shared-uploads:backups/data.zip",
  "mode": "r"
}
```

**Response** (201 Created):
```json
{
  "id": 20,
  "name": "archive-vol",
  "backend": "zip",
  "config": {
    "file": "shared-uploads:backups/data.zip",
    "mode": "r"
  },
  "owner_id": 5,
  "created_at": "2025-10-30T12:00:00Z"
}
```

**Supported archive types**:
- `zip`: ZIP archives
- `tar`: TAR archives (including .tar.gz, .tar.bz2, .tar.xz)

**Mode options**:
- `r`: Read-only (mount existing archive)
- `w`: Write mode (creates new archive)

**Notes**:
- `file` path references another mounted volume (e.g., `volume:path`)
- Caller must have read access to source volume containing archive

---

## User Management API

### Create User

**Endpoint**: `POST /admin/users`

**Authorization**: Owner (any user) or User (sub-users only)

**Request Body**:
```json
{
  "username": "bob",
  "role": "user",
  "token": "bob_secure_token_789"
}
```

**Response** (201 Created):
```json
{
  "id": 20,
  "username": "bob",
  "role": "user",
  "token": "bob_secure_token_789",
  "parent_user_id": null,
  "created_at": "2025-10-30T13:00:00Z"
}
```

**Validation rules**:
- If caller is User and `role=subuser`: `parent_user_id` set automatically to caller's `id`
- If caller is User and `role=user`: 403 Forbidden (only Owner can create users)
- If caller is Owner: can create any role, `parent_user_id` always NULL
- `username` must be unique globally
- `token` must be unique globally and at least 32 characters

**Token in response**:
- Only returned on creation
- Never returned in GET/LIST operations

---

### List Users

**Endpoint**: `GET /admin/users`

**Authorization**: Owner (all users) or User (self + own sub-users)

**Response** (200 OK):
```json
{
  "users": [
    {
      "id": 5,
      "username": "alice",
      "role": "user",
      "parent_user_id": null,
      "created_at": "2025-10-20T10:00:00Z"
    },
    {
      "id": 12,
      "username": "alice_readonly",
      "role": "subuser",
      "parent_user_id": 5,
      "created_at": "2025-10-25T14:00:00Z"
    }
  ]
}
```

**Filtering logic**:
- Owner sees: all users
- User sees: self + users where `parent_user_id = user.id`
- Sub-user: 403 Forbidden

**Notes**:
- Token is never returned in list operations
- Use for user discovery and management UI

---

### Get User

**Endpoint**: `GET /admin/users/{user_id}`

**Authorization**: Owner or User (if self or descendant)

**Response** (200 OK):
```json
{
  "id": 12,
  "username": "alice_readonly",
  "role": "subuser",
  "parent_user_id": 5,
  "created_at": "2025-10-25T14:00:00Z",
  "updated_at": "2025-10-25T14:00:00Z",
  "volumes": [
    {
      "volume_id": 1,
      "volume_name": "shared-uploads",
      "permissions": "readonly"
    }
  ]
}
```

**Notes**:
- `volumes` array shows all volumes this user can access
- Useful for auditing user permissions

---

### Update User Token

**Endpoint**: `PUT /admin/users/{user_id}/token`

**Authorization**: Owner or User (if owns user)

**Request Body**:
```json
{
  "token": "new_secure_token_abc"
}
```

**Response** (200 OK):
```json
{
  "id": 12,
  "username": "alice_readonly",
  "token": "new_secure_token_abc",
  "updated_at": "2025-10-30T15:00:00Z"
}
```

**Notes**:
- Token must be unique globally
- Old token immediately invalidated
- Active sessions with old token will fail on next request
- Token rotation recommended every 90 days

---

### Delete User

**Endpoint**: `DELETE /admin/users/{user_id}`

**Authorization**: Owner or User (if owns user)

**Response** (200 OK):
```json
{
  "deleted": true,
  "user_id": 12,
  "username": "alice_readonly"
}
```

**Cascade behavior**:
- Removes all `user_volumes` entries for this user
- If deleting User (not sub-user):
  - Deletes all their sub-users recursively
  - Deletes all volumes where `owner_id = user.id`
  - All files in deleted volumes remain in backend storage

**Protection**:
- Cannot delete Owner user
- Cannot delete self (prevent lockout)

---

## Permission Management API

### Grant Volume Access

**Endpoint**: `POST /admin/users/{user_id}/volumes`

**Authorization**: Owner or User (if owns both user and volume)

**Request Body**:
```json
{
  "volume_id": 1,
  "permissions": "readonly"
}
```

**Response** (201 Created):
```json
{
  "id": 50,
  "user_id": 12,
  "volume_id": 1,
  "volume_name": "shared-uploads",
  "permissions": "readonly",
  "created_at": "2025-10-30T16:00:00Z"
}
```

**Permission levels**:
- `readonly`: GET operations only (read files, list directories, get metadata)
- `readwrite`: GET + PUT operations (read + write/create files/directories)
- `delete`: Full access (GET + PUT + DELETE operations)

**Validation**:
- User can only grant access to volumes they own
- Owner can grant access to any volume
- Cannot grant permissions to Owner (implicit full access)

---

### List User's Volume Access

**Endpoint**: `GET /admin/users/{user_id}/volumes`

**Authorization**: Owner or User (if owns user)

**Response** (200 OK):
```json
{
  "volumes": [
    {
      "volume_id": 1,
      "volume_name": "shared-uploads",
      "permissions": "readonly",
      "granted_at": "2025-10-30T16:00:00Z"
    },
    {
      "volume_id": 15,
      "volume_name": "my-storage",
      "permissions": "readwrite",
      "granted_at": "2025-10-29T10:00:00Z"
    }
  ]
}
```

---

### Update Volume Permissions

**Endpoint**: `PUT /admin/users/{user_id}/volumes/{volume_id}`

**Authorization**: Owner or User (if owns both)

**Request Body**:
```json
{
  "permissions": "readwrite"
}
```

**Response** (200 OK):
```json
{
  "user_id": 12,
  "volume_id": 1,
  "permissions": "readwrite",
  "updated_at": "2025-10-30T17:00:00Z"
}
```

**Notes**:
- Changes take effect immediately
- Active file operations with old permissions continue until completion

---

### Revoke Volume Access

**Endpoint**: `DELETE /admin/users/{user_id}/volumes/{volume_id}`

**Authorization**: Owner or User (if owns both)

**Response** (200 OK):
```json
{
  "deleted": true,
  "user_id": 12,
  "volume_id": 1
}
```

**Notes**:
- Removes entry from `user_volumes` table
- User loses access immediately
- Active file operations may fail

---

## Security Considerations

### Token Management

**Generation**:
```python
import secrets
token = secrets.token_urlsafe(32)  # 256 bits, URL-safe
```

**Storage**:
- Tokens stored in plain text (API tokens, not passwords)
- Consider adding `last_used_at` field for auditing
- Implement token rotation policy (90 days recommended)

**Transmission**:
- Always use HTTPS in production
- Tokens via `Authorization: Bearer <token>` header only
- Never log tokens in application logs
- Redact tokens in error messages

### Permission Validation Pattern

```python
# Pseudocode for permission check
def check_file_permission(user, volume, operation):
    # Owner has full access
    if user.role == 'owner':
        return True

    # Check volume ownership
    if volume.owner_id == user.id:
        return True  # Full access to own volumes

    # Check explicit permission
    permission = db.query(UserVolumes).filter(
        user_id=user.id,
        volume_id=volume.id
    ).first()

    if not permission:
        return False  # No access

    # Check permission level
    if operation == 'read':
        return permission.permissions in ['readonly', 'readwrite', 'delete']
    elif operation == 'write':
        return permission.permissions in ['readwrite', 'delete']
    elif operation == 'delete':
        return permission.permissions == 'delete'

    return False
```

### Audit Logging

Recommended audit log entries:

```python
# Log format (JSON)
{
  "timestamp": "2025-10-30T10:00:00Z",
  "event": "volume_created",
  "user_id": 5,
  "username": "alice",
  "resource_type": "volume",
  "resource_id": 15,
  "resource_name": "my-storage",
  "details": {"backend": "s3", "bucket": "my-bucket"}
}

{
  "timestamp": "2025-10-30T16:00:00Z",
  "event": "permission_granted",
  "user_id": 5,
  "username": "alice",
  "target_user_id": 12,
  "target_username": "alice_readonly",
  "volume_id": 1,
  "permissions": "readonly"
}

{
  "timestamp": "2025-10-30T18:00:00Z",
  "event": "user_deleted",
  "user_id": 1,
  "username": "admin",
  "target_user_id": 12,
  "target_username": "alice_readonly",
  "cascade": {"volumes": 0, "subusers": 0}
}
```

### Rate Limiting

Recommended limits per user:

```python
from slowapi import Limiter

limiter = Limiter(key_func=lambda: request.state.user_id)

# Administrative endpoints
@app.post("/admin/volumes")
@limiter.limit("100/minute")
async def create_volume(...):
    ...

@app.delete("/admin/users/{user_id}")
@limiter.limit("10/minute")
async def delete_user(...):
    ...
```

**Limits**:
- `/admin/volumes` (POST/PUT/DELETE): 100/minute
- `/admin/users` (POST/PUT/DELETE): 10/minute
- `/admin/users/*/volumes` (POST/PUT/DELETE): 100/minute

### Input Validation

**Volume names**:
```python
import re

def validate_volume_name(name: str):
    # Alphanumeric, hyphens, underscores only
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise ValueError("Invalid volume name")

    # Reserved names
    if name in ['admin', 'system', 'root']:
        raise ValueError("Reserved volume name")

    return True
```

**Tokens**:
```python
def validate_token(token: str):
    if len(token) < 32:
        raise ValueError("Token too short (min 32 chars)")

    # Check uniqueness
    if db.query(User).filter(token=token).first():
        raise ValueError("Token already exists")

    return True
```

---

## Error Responses

### Standard Format

```json
{
  "error": "Forbidden",
  "detail": "You do not own this volume",
  "code": "VOLUME_ACCESS_DENIED"
}
```

### HTTP Status Codes

| Status | Meaning |
|--------|---------|
| 200 | OK - Successful operation |
| 201 | Created - Resource created successfully |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing or invalid token |
| 403 | Forbidden - Valid token, insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Duplicate name/token |
| 500 | Internal Server Error |

### Common Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `AUTH_MISSING_TOKEN` | 401 | Authorization header missing |
| `AUTH_INVALID_TOKEN` | 401 | Token not found in database |
| `AUTH_INSUFFICIENT_PERMISSION` | 403 | Operation not allowed for role |
| `VOLUME_NOT_FOUND` | 404 | Volume ID doesn't exist |
| `VOLUME_DUPLICATE_NAME` | 409 | Volume name already exists |
| `VOLUME_ACCESS_DENIED` | 403 | User cannot access this volume |
| `USER_NOT_FOUND` | 404 | User ID doesn't exist |
| `USER_DUPLICATE_USERNAME` | 409 | Username already exists |
| `USER_DUPLICATE_TOKEN` | 409 | Token already exists |
| `USER_CANNOT_DELETE_SELF` | 403 | Cannot delete own user account |
| `USER_CANNOT_DELETE_OWNER` | 403 | Cannot delete owner account |
| `PERMISSION_ALREADY_EXISTS` | 409 | User already has access to volume |

---

## Appendix: Complete Endpoint List

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| **Volume Management** |
| POST | `/admin/volumes` | Owner/User | Create volume |
| GET | `/admin/volumes` | Owner/User | List volumes |
| GET | `/admin/volumes/{id}` | Owner/User | Get volume details |
| PUT | `/admin/volumes/{id}` | Owner/User | Update volume config |
| DELETE | `/admin/volumes/{id}` | Owner/User | Delete volume |
| POST | `/admin/volumes/from-archive` | Owner/User | Mount archive as volume |
| **User Management** |
| POST | `/admin/users` | Owner/User | Create user/sub-user |
| GET | `/admin/users` | Owner/User | List users |
| GET | `/admin/users/{id}` | Owner/User | Get user details |
| PUT | `/admin/users/{id}/token` | Owner/User | Update user token |
| DELETE | `/admin/users/{id}` | Owner/User | Delete user |
| **Permission Management** |
| POST | `/admin/users/{id}/volumes` | Owner/User | Grant volume access |
| GET | `/admin/users/{id}/volumes` | Owner/User | List user's volumes |
| PUT | `/admin/users/{id}/volumes/{vid}` | Owner/User | Update permissions |
| DELETE | `/admin/users/{id}/volumes/{vid}` | Owner/User | Revoke volume access |

---

**End of Document**
