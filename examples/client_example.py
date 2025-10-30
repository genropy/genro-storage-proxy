"""Example: Using genro-storage-proxy from Python client.

This shows how any microservice (in any language) can interact with
genro-storage-proxy via simple HTTP requests.
"""

import requests
from pathlib import Path

# Configuration
STORAGE_PROXY_URL = "http://localhost:8080"
AUTH_TOKEN = "your-jwt-token-here"

class StorageClient:
    """Simple client for genro-storage-proxy."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {'Authorization': f'Bearer {token}'}

    def upload_file(self, path: str, data: bytes) -> dict:
        """Upload file to storage.

        Args:
            path: Storage path (e.g., "uploads:documents/report.pdf")
            data: File bytes

        Returns:
            Response with file metadata
        """
        url = f"{self.base_url}/files/{path}"
        files = {'file': data}
        response = requests.put(url, files=files, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def download_file(self, path: str) -> bytes:
        """Download file from storage.

        Args:
            path: Storage path (e.g., "uploads:documents/report.pdf")

        Returns:
            File bytes
        """
        url = f"{self.base_url}/files/{path}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.content

    def delete_file(self, path: str) -> dict:
        """Delete file from storage.

        Args:
            path: Storage path

        Returns:
            Response confirming deletion
        """
        url = f"{self.base_url}/files/{path}"
        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def copy_file(self, source: str, destination: str) -> dict:
        """Copy file to another location.

        Args:
            source: Source path (e.g., "uploads:file.pdf")
            destination: Destination path (e.g., "backups:file.pdf")

        Returns:
            Response with copy metadata
        """
        url = f"{self.base_url}/files/{source}/copy"
        data = {'destination': destination}
        response = requests.post(url, json=data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def list_directory(self, path: str) -> dict:
        """List files in directory.

        Args:
            path: Directory path (e.g., "uploads:documents/")

        Returns:
            List of files and subdirectories
        """
        url = f"{self.base_url}/files/{path}"
        params = {'list': 'true'}
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_metadata(self, path: str) -> dict:
        """Get file metadata.

        Args:
            path: File path

        Returns:
            File metadata (size, mtime, mimetype, etc.)
        """
        url = f"{self.base_url}/files/{path}/metadata"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()


# Example usage
if __name__ == '__main__':
    client = StorageClient(STORAGE_PROXY_URL, AUTH_TOKEN)

    # Upload a file
    print("1. Uploading file...")
    with open('example.txt', 'rb') as f:
        result = client.upload_file('uploads:test/example.txt', f.read())
    print(f"   Uploaded: {result}")

    # Download the file
    print("\n2. Downloading file...")
    content = client.download_file('uploads:test/example.txt')
    print(f"   Downloaded {len(content)} bytes")

    # Get metadata
    print("\n3. Getting metadata...")
    metadata = client.get_metadata('uploads:test/example.txt')
    print(f"   Metadata: {metadata}")

    # Copy file
    print("\n4. Copying file...")
    copy_result = client.copy_file(
        'uploads:test/example.txt',
        'backups:test/example.txt'
    )
    print(f"   Copied: {copy_result}")

    # List directory
    print("\n5. Listing directory...")
    files = client.list_directory('uploads:test/')
    print(f"   Files: {files}")

    # Delete file
    print("\n6. Deleting file...")
    delete_result = client.delete_file('uploads:test/example.txt')
    print(f"   Deleted: {delete_result}")
