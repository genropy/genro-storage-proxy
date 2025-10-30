# genro-storage-proxy - File Operations API

**Version:** 1.0
**Date:** 2025-10-30
**Status:** Draft

---

## Table of Contents

1. [Overview](#overview)
2. [Path Format](#path-format)
3. [Authentication & Authorization](#authentication--authorization)
4. [Basic File Operations](#basic-file-operations)
5. [Directory Operations](#directory-operations)
6. [Advanced Operations](#advanced-operations)
7. [Error Handling](#error-handling)
8. [Examples](#examples)

---

## Overview

The File Operations API provides HTTP endpoints for managing files and directories across multiple storage backends. All operations use the unified `mount:path` format from genro-storage, allowing transparent access to S3, GCS, local filesystem, and other backends.

**Base path**: `/files/`

**Authentication**: All operations require `Authorization: Bearer <token>` header

**Supported operations**:
- Read files (binary and text modes)
- Write files (binary and text modes)
- Delete files and directories
- List directory contents
- Get file/directory metadata
- Create directories
- Copy files/directories (cross-backend)
- Move files/directories
- Create ZIP archives

---

## Path Format

All file paths use the genro-storage `mount:path` format:

```
/files/{mount}:{path}
```

**Components**:
- `{mount}`: Volume name configured in admin API
- `{path}`: Relative path within the volume

**Examples**:
```
/files/uploads:documents/report.pdf
/files/s3-bucket:images/photo.jpg
/files/local-storage:data/users/alice/profile.json
/files/cdn:assets/logo.png
```

**Path rules**:
- Forward slashes (`/`) separate path components
- No leading slash after colon
- Multiple consecutive slashes collapsed to one
- Parent directory references (`..`) not supported (security)
- URL encoding required for special characters

**Valid paths**:
```
✓ uploads:file.txt
✓ uploads:dir/subdir/file.txt
✓ uploads:with%20spaces.txt (URL encoded)
```

**Invalid paths**:
```
✗ uploads:/file.txt (leading slash)
✗ uploads:../file.txt (parent reference)
✗ uploads://dir//file.txt (multiple slashes, but auto-collapsed)
```

---

## Authentication & Authorization

### Token-Based Authentication

All requests require:
```
Authorization: Bearer <token>
```

### Permission Levels

File operations require specific permission levels on the volume:

| Operation | Required Permission |
|-----------|---------------------|
| GET (read file) | `readonly`, `readwrite`, or `delete` |
| GET (list directory) | `readonly`, `readwrite`, or `delete` |
| GET (stat/metadata) | `readonly`, `readwrite`, or `delete` |
| PUT (write file) | `readwrite` or `delete` |
| POST (mkdir) | `readwrite` or `delete` |
| DELETE | `delete` only |
| POST (copy/move/zip) | Source readable, destination writable |

### Access Check Flow

```
1. Extract token from Authorization header
2. Identify user from token
3. Extract mount name from path
4. Check user has permission for mount:
   - Owner: Always allowed
   - User: Check ownership or user_volumes entry
   - Sub-user: Check user_volumes entry (read-only)
5. Verify permission level matches operation
6. Execute or return 403 Forbidden
```

---

## Basic File Operations

### Read File

**Endpoint**: `GET /files/{mount}:{path}`

**Query Parameters**:
- `mode` (optional): `rb` (binary, default) or `r` (text)
- `encoding` (optional): Text encoding for mode=r (default: `utf-8`)

**Response** (200 OK):
- **Headers**:
  - `Content-Type`: Detected MIME type
  - `Content-Length`: File size in bytes
  - `ETag`: MD5 hash (if available from backend)
  - `Last-Modified`: File modification time
- **Body**: File bytes

**Examples**:

```bash
# Binary mode (default)
GET /files/uploads:documents/report.pdf
Authorization: Bearer token123

Response:
Content-Type: application/pdf
Content-Length: 524288
ETag: "d41d8cd98f00b204e9800998ecf8427e"
Last-Modified: Wed, 29 Oct 2025 10:00:00 GMT

<PDF binary data>
```

```bash
# Text mode
GET /files/uploads:config.json?mode=r&encoding=utf-8
Authorization: Bearer token123

Response:
Content-Type: application/json; charset=utf-8
Content-Length: 156

{"key": "value", "number": 42}
```

**Errors**:
- 401: Missing or invalid token
- 403: No read permission on volume
- 404: File not found
- 404: Volume not found

---

### Write File

**Endpoint**: `PUT /files/{mount}:{path}`

**Query Parameters**:
- `mode` (optional): `wb` (binary, default) or `w` (text)
- `encoding` (optional): Text encoding for mode=w (default: `utf-8`)

**Request**:
- **Headers**:
  - `Content-Type`: File MIME type (optional but recommended)
  - `Content-Length`: File size in bytes
- **Body**: File bytes

**Response** (201 Created or 200 OK):
```json
{
  "path": "uploads:documents/report.pdf",
  "size": 524288,
  "created": true
}
```

**Fields**:
- `created`: `true` if new file, `false` if overwritten existing file

**Examples**:

```bash
# Binary mode (default)
PUT /files/uploads:images/photo.jpg?mode=wb
Authorization: Bearer token123
Content-Type: image/jpeg

<JPEG binary data>

Response:
{
  "path": "uploads:images/photo.jpg",
  "size": 245678,
  "created": true
}
```

```bash
# Text mode
PUT /files/uploads:config.json?mode=w
Authorization: Bearer token123
Content-Type: application/json

{"key": "value"}

Response:
{
  "path": "uploads:config.json",
  "size": 17,
  "created": false
}
```

**Errors**:
- 401: Missing or invalid token
- 403: No write permission on volume
- 404: Volume not found
- 413: File too large (if size limit configured)

---

### Delete File or Directory

**Endpoint**: `DELETE /files/{mount}:{path}`

**Response** (200 OK):
```json
{
  "deleted": true,
  "path": "uploads:documents/report.pdf",
  "type": "file"
}
```

**Behavior**:
- If path is **file**: Delete file
- If path is **directory**: Recursive delete (like `rm -rf`)
- If path doesn't exist: Return success (idempotent)

**Examples**:

```bash
# Delete file
DELETE /files/uploads:documents/report.pdf
Authorization: Bearer token123

Response:
{
  "deleted": true,
  "path": "uploads:documents/report.pdf",
  "type": "file"
}
```

```bash
# Delete directory recursively
DELETE /files/uploads:documents/archive
Authorization: Bearer token123

Response:
{
  "deleted": true,
  "path": "uploads:documents/archive",
  "type": "directory",
  "files_deleted": 42
}
```

**Errors**:
- 401: Missing or invalid token
- 403: No delete permission on volume
- 404: Volume not found

---

## Directory Operations

### List Directory

**Endpoint**: `GET /files/{mount}:{path}?list=true`

**Query Parameters**:
- `list=true` (required): Indicates directory listing operation
- `recursive` (optional): `true` for recursive listing

**Response** (200 OK):
```json
{
  "path": "uploads:documents",
  "type": "directory",
  "children": [
    {
      "name": "report.pdf",
      "type": "file",
      "size": 524288,
      "mtime": "2025-10-29T10:00:00Z",
      "mimetype": "application/pdf"
    },
    {
      "name": "images",
      "type": "directory",
      "mtime": "2025-10-28T15:30:00Z"
    }
  ]
}
```

**Child entry fields**:
- `name`: Filename or directory name (basename)
- `type`: `"file"` or `"directory"`
- `size`: File size in bytes (files only)
- `mtime`: Last modification time (ISO 8601)
- `mimetype`: Detected MIME type (files only)

**Examples**:

```bash
# List directory
GET /files/uploads:documents?list=true
Authorization: Bearer token123

Response:
{
  "path": "uploads:documents",
  "type": "directory",
  "children": [
    {"name": "file1.txt", "type": "file", "size": 100},
    {"name": "subdir", "type": "directory"}
  ]
}
```

```bash
# Recursive listing
GET /files/uploads:documents?list=true&recursive=true
Authorization: Bearer token123

Response:
{
  "path": "uploads:documents",
  "type": "directory",
  "children": [
    {"name": "file1.txt", "type": "file"},
    {
      "name": "subdir",
      "type": "directory",
      "children": [
        {"name": "file2.txt", "type": "file"}
      ]
    }
  ]
}
```

**Errors**:
- 401: Missing or invalid token
- 403: No read permission on volume
- 404: Directory not found
- 404: Path is a file (not a directory)

---

### Get File/Directory Metadata

**Endpoint**: `GET /files/{mount}:{path}/stat`

**Response** (200 OK):

**For files**:
```json
{
  "path": "uploads:documents/report.pdf",
  "exists": true,
  "type": "file",
  "size": 524288,
  "mtime": "2025-10-29T10:00:00Z",
  "mimetype": "application/pdf",
  "md5hash": "d41d8cd98f00b204e9800998ecf8427e"
}
```

**For directories**:
```json
{
  "path": "uploads:documents",
  "exists": true,
  "type": "directory",
  "mtime": "2025-10-29T10:00:00Z"
}
```

**Fields**:
- `exists`: Boolean indicating if path exists
- `type`: `"file"` or `"directory"`
- `size`: File size in bytes (files only)
- `mtime`: Last modification time (ISO 8601)
- `mimetype`: Detected MIME type (files only)
- `md5hash`: MD5 hash of content (files only, if available from backend)

**Examples**:

```bash
GET /files/uploads:documents/report.pdf/stat
Authorization: Bearer token123

Response:
{
  "path": "uploads:documents/report.pdf",
  "exists": true,
  "type": "file",
  "size": 524288,
  "mtime": "2025-10-29T10:00:00Z",
  "mimetype": "application/pdf",
  "md5hash": "d41d8cd98f00b204e9800998ecf8427e"
}
```

**Errors**:
- 401: Missing or invalid token
- 403: No read permission on volume
- 404: Volume not found
- Note: Returns `exists: false` if path doesn't exist (not 404 error)

---

### Create Directory

**Endpoint**: `POST /files/{mount}:{path}?mkdir=true`

**Query Parameters**:
- `mkdir=true` (required): Indicates directory creation
- `parents` (optional, default: `false`): Create parent directories if needed
- `exist_ok` (optional, default: `false`): Don't error if directory already exists

**Response** (201 Created):
```json
{
  "created": true,
  "path": "uploads:documents/2025"
}
```

**Examples**:

```bash
# Simple mkdir
POST /files/uploads:documents/newdir?mkdir=true
Authorization: Bearer token123

Response:
{
  "created": true,
  "path": "uploads:documents/newdir"
}
```

```bash
# Create with parents
POST /files/uploads:a/b/c/d?mkdir=true&parents=true
Authorization: Bearer token123

Response:
{
  "created": true,
  "path": "uploads:a/b/c/d",
  "parents_created": ["uploads:a", "uploads:a/b", "uploads:a/b/c"]
}
```

```bash
# Idempotent creation
POST /files/uploads:documents/existing?mkdir=true&exist_ok=true
Authorization: Bearer token123

Response:
{
  "created": false,
  "path": "uploads:documents/existing",
  "already_exists": true
}
```

**Errors**:
- 401: Missing or invalid token
- 403: No write permission on volume
- 404: Volume not found
- 409: Directory already exists (if `exist_ok=false`)
- 404: Parent directory doesn't exist (if `parents=false`)

---

## Advanced Operations

### Create ZIP Archive

**Endpoint**: `POST /files/{mount}:{path}/zip`

**Request Body** (optional):
```json
{
  "dest": "backups:archives/data.zip"
}
```

**Response**:

**If `dest` specified** (200 OK):
```json
{
  "archive_path": "backups:archives/data.zip",
  "size": 1048576,
  "files_count": 42,
  "compression": "deflate"
}
```

**If `dest` omitted** (200 OK):
- **Headers**:
  - `Content-Type`: `application/zip`
  - `Content-Disposition`: `attachment; filename="<basename>.zip"`
- **Body**: ZIP binary data

**Behavior based on source type**:
- **File**: ZIP contains single file
- **Directory**: ZIP contains all files recursively
- **Compression**: ZIP_DEFLATED (level 9)

**Examples**:

```bash
# ZIP file to destination
POST /files/uploads:documents/report.pdf/zip
Authorization: Bearer token123
Content-Type: application/json

{
  "dest": "backups:archives/report.zip"
}

Response:
{
  "archive_path": "backups:archives/report.zip",
  "size": 450000,
  "files_count": 1
}
```

```bash
# ZIP directory to destination
POST /files/uploads:documents/zip
Authorization: Bearer token123
Content-Type: application/json

{
  "dest": "backups:archives/documents_2025.zip"
}

Response:
{
  "archive_path": "backups:archives/documents_2025.zip",
  "size": 5242880,
  "files_count": 42
}
```

```bash
# ZIP and download directly
POST /files/uploads:documents/zip
Authorization: Bearer token123

Response:
Content-Type: application/zip
Content-Disposition: attachment; filename="documents.zip"

<ZIP binary data>
```

**Errors**:
- 401: Missing or invalid token
- 403: Source not readable or destination not writable
- 404: Source path not found
- 400: Source is neither file nor directory

---

### Copy File or Directory

**Endpoint**: `POST /files/{mount}:{path}/copy`

**Request Body**:
```json
{
  "dest": "backups:documents/report_backup.pdf",
  "skip": "hash"
}
```

**Fields**:
- `dest` (required): Destination path (format: `mount:path`)
- `skip` (optional): Skip strategy (see below)

**Skip strategies**:
- `null` (default): Always copy, overwrite if exists
- `"exists"`: Skip if destination exists
- `"size"`: Skip if destination exists and has same size
- `"hash"`: Skip if destination exists and has same MD5 hash (content-based)

**Response** (200 OK):
```json
{
  "source": "uploads:documents/report.pdf",
  "dest": "backups:documents/report_backup.pdf",
  "size": 524288,
  "copied": true,
  "skipped": false
}
```

**For directories**:
```json
{
  "source": "uploads:documents",
  "dest": "backups:documents_backup",
  "files_copied": 42,
  "files_skipped": 8,
  "total_size": 5242880,
  "copied": true
}
```

**Behavior**:
- Works across different storage backends (S3 → local, etc.)
- If source is file: Copy single file
- If source is directory: Recursive copy
- If dest exists and is directory: Create file/directory inside with same basename

**Examples**:

```bash
# Simple copy
POST /files/uploads:file.txt/copy
Authorization: Bearer token123
Content-Type: application/json

{
  "dest": "backups:file.txt"
}

Response:
{
  "source": "uploads:file.txt",
  "dest": "backups:file.txt",
  "size": 1024,
  "copied": true
}
```

```bash
# Copy with skip strategy
POST /files/uploads:documents/copy
Authorization: Bearer token123
Content-Type: application/json

{
  "dest": "backups:documents",
  "skip": "hash"
}

Response:
{
  "source": "uploads:documents",
  "dest": "backups:documents",
  "files_copied": 12,
  "files_skipped": 30,
  "total_size": 2500000,
  "copied": true
}
```

**Errors**:
- 401: Missing or invalid token
- 403: Source not readable or destination not writable
- 404: Source not found
- 400: Invalid destination path

---

### Move File or Directory

**Endpoint**: `POST /files/{mount}:{path}/move`

**Request Body**:
```json
{
  "dest": "archive:old-documents/report.pdf"
}
```

**Response** (200 OK):
```json
{
  "source": "uploads:documents/report.pdf",
  "dest": "archive:old-documents/report.pdf",
  "moved": true
}
```

**Behavior**:
- **Same backend**: Efficient rename operation (no data transfer)
- **Different backends**: Copy to destination + delete source
- If source is directory: Recursive move

**Examples**:

```bash
# Move within same volume (efficient)
POST /files/uploads:temp/file.txt/move
Authorization: Bearer token123
Content-Type: application/json

{
  "dest": "uploads:archive/file.txt"
}

Response:
{
  "source": "uploads:temp/file.txt",
  "dest": "uploads:archive/file.txt",
  "moved": true,
  "rename": true
}
```

```bash
# Move across volumes (copy + delete)
POST /files/uploads:documents/report.pdf/move
Authorization: Bearer token123
Content-Type: application/json

{
  "dest": "archive:2025/report.pdf"
}

Response:
{
  "source": "uploads:documents/report.pdf",
  "dest": "archive:2025/report.pdf",
  "moved": true,
  "size": 524288,
  "cross_backend": true
}
```

**Errors**:
- 401: Missing or invalid token
- 403: Source not deletable or destination not writable
- 404: Source not found
- 400: Invalid destination path

---

## Error Handling

### Standard Error Response

```json
{
  "error": "File not found",
  "detail": "The file uploads:documents/report.pdf does not exist",
  "code": "FILE_NOT_FOUND",
  "path": "uploads:documents/report.pdf"
}
```

### HTTP Status Codes

| Status | Meaning | Common Causes |
|--------|---------|---------------|
| 200 | OK | Successful GET, POST, DELETE |
| 201 | Created | Successful PUT (new file), POST (mkdir) |
| 400 | Bad Request | Invalid path format, missing parameters |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | Insufficient permission for operation |
| 404 | Not Found | File, directory, or volume not found |
| 409 | Conflict | Directory already exists (mkdir) |
| 413 | Payload Too Large | File exceeds size limit |
| 500 | Internal Server Error | Backend storage error |

### Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `FILE_NOT_FOUND` | 404 | File or directory doesn't exist |
| `FILE_PERMISSION_DENIED` | 403 | Insufficient permission for operation |
| `FILE_INVALID_PATH` | 400 | Path format invalid or parent reference |
| `FILE_ALREADY_EXISTS` | 409 | File/directory already exists |
| `FILE_IS_DIRECTORY` | 400 | Operation requires file, got directory |
| `FILE_IS_FILE` | 400 | Operation requires directory, got file |
| `FILE_TOO_LARGE` | 413 | File exceeds configured size limit |
| `VOLUME_NOT_FOUND` | 404 | Volume mount name doesn't exist |
| `VOLUME_ACCESS_DENIED` | 403 | User cannot access this volume |
| `STORAGE_BACKEND_ERROR` | 500 | Backend (S3, etc.) returned error |

### Backend-Specific Errors

**S3 errors**:
```json
{
  "error": "Storage backend error",
  "detail": "S3 AccessDenied: Access Denied",
  "code": "STORAGE_BACKEND_ERROR",
  "backend": "s3",
  "backend_error": "AccessDenied"
}
```

**Network errors**:
```json
{
  "error": "Storage backend error",
  "detail": "Connection timeout to storage backend",
  "code": "STORAGE_BACKEND_ERROR",
  "backend": "http"
}
```

---

## Examples

### Complete Workflow: Upload, Process, Archive

```bash
# 1. Upload file
PUT /files/uploads:temp/data.csv
Authorization: Bearer token123
Content-Type: text/csv

id,name,value
1,Alice,100
2,Bob,200

# 2. Read and verify
GET /files/uploads:temp/data.csv/stat
Authorization: Bearer token123

Response:
{
  "exists": true,
  "type": "file",
  "size": 45,
  "md5hash": "abc123..."
}

# 3. Copy to processed directory
POST /files/uploads:temp/data.csv/copy
Authorization: Bearer token123

{
  "dest": "uploads:processed/data_2025.csv"
}

# 4. Create backup archive
POST /files/uploads:processed/zip
Authorization: Bearer token123

{
  "dest": "backups:archives/processed_2025.zip"
}

# 5. Delete temp file
DELETE /files/uploads:temp/data.csv
Authorization: Bearer token123
```

### Cross-Backend Synchronization

```bash
# Copy from S3 to local with skip strategy
POST /files/s3-bucket:documents/copy
Authorization: Bearer token123

{
  "dest": "local-storage:backup/documents",
  "skip": "hash"
}

Response:
{
  "source": "s3-bucket:documents",
  "dest": "local-storage:backup/documents",
  "files_copied": 15,
  "files_skipped": 85,
  "total_size": 25000000,
  "copied": true
}
```

### Batch Operations with Directory Listing

```bash
# 1. List all files in directory
GET /files/uploads:documents?list=true&recursive=true
Authorization: Bearer token123

Response:
{
  "path": "uploads:documents",
  "children": [
    {"name": "file1.pdf", "type": "file"},
    {"name": "file2.pdf", "type": "file"},
    {"name": "subdir/file3.pdf", "type": "file"}
  ]
}

# 2. Process each file (client-side loop)
# GET /files/uploads:documents/file1.pdf
# ... process ...
# PUT /files/processed:file1_processed.pdf

# 3. Archive original directory
POST /files/uploads:documents/zip
Authorization: Bearer token123

{
  "dest": "archives:documents_backup.zip"
}

# 4. Delete original
DELETE /files/uploads:documents
Authorization: Bearer token123
```

---

## Performance Considerations

### Streaming Large Files

For files >10MB, the API streams data without buffering in memory:

```bash
# Upload 1GB file - streams directly to backend
PUT /files/uploads:large-file.bin
Authorization: Bearer token123
Content-Length: 1073741824

<streaming binary data>
```

### Concurrent Operations

Multiple file operations can run concurrently:

```bash
# Client can parallelize reads
GET /files/uploads:file1.txt  # Request 1
GET /files/uploads:file2.txt  # Request 2
GET /files/uploads:file3.txt  # Request 3
# All execute concurrently
```

### ETag Caching

Clients can use ETags for conditional requests:

```bash
# First request
GET /files/uploads:file.txt
Response:
ETag: "abc123..."

# Subsequent request with If-None-Match
GET /files/uploads:file.txt
If-None-Match: "abc123..."

Response: 304 Not Modified (if unchanged)
```

---

## Appendix: Complete Endpoint List

| Method | Endpoint | Operation | Auth Permission |
|--------|----------|-----------|-----------------|
| GET | `/files/{mount}:{path}` | Read file | readonly+ |
| GET | `/files/{mount}:{path}?list=true` | List directory | readonly+ |
| GET | `/files/{mount}:{path}/stat` | Get metadata | readonly+ |
| PUT | `/files/{mount}:{path}` | Write file | readwrite+ |
| DELETE | `/files/{mount}:{path}` | Delete file/dir | delete |
| POST | `/files/{mount}:{path}?mkdir=true` | Create directory | readwrite+ |
| POST | `/files/{mount}:{path}/zip` | Create ZIP | readonly+ (dest: readwrite+) |
| POST | `/files/{mount}:{path}/copy` | Copy file/dir | src: readonly+, dest: readwrite+ |
| POST | `/files/{mount}:{path}/move` | Move file/dir | src: delete, dest: readwrite+ |

---

**End of Document**
