// Example: Using genro-storage-proxy from Go client
//
// This demonstrates how services written in Go (or any language)
// can interact with storage without Python dependencies.

package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
)

const (
	storageProxyURL = "http://localhost:8080"
	authToken       = "your-jwt-token-here"
)

// StorageClient wraps HTTP calls to genro-storage-proxy
type StorageClient struct {
	BaseURL string
	Token   string
	Client  *http.Client
}

// NewStorageClient creates a new client
func NewStorageClient(baseURL, token string) *StorageClient {
	return &StorageClient{
		BaseURL: baseURL,
		Token:   token,
		Client:  &http.Client{},
	}
}

// UploadFile uploads a file to storage
func (c *StorageClient) UploadFile(path string, data []byte) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/files/%s", c.BaseURL, path)

	req, err := http.NewRequest("PUT", url, bytes.NewReader(data))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Authorization", "Bearer "+c.Token)
	req.Header.Set("Content-Type", "application/octet-stream")

	resp, err := c.Client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("upload failed: %s", resp.Status)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return result, nil
}

// DownloadFile downloads a file from storage
func (c *StorageClient) DownloadFile(path string) ([]byte, error) {
	url := fmt.Sprintf("%s/files/%s", c.BaseURL, path)

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("Authorization", "Bearer "+c.Token)

	resp, err := c.Client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("download failed: %s", resp.Status)
	}

	return io.ReadAll(resp.Body)
}

// DeleteFile deletes a file from storage
func (c *StorageClient) DeleteFile(path string) error {
	url := fmt.Sprintf("%s/files/%s", c.BaseURL, path)

	req, err := http.NewRequest("DELETE", url, nil)
	if err != nil {
		return err
	}

	req.Header.Set("Authorization", "Bearer "+c.Token)

	resp, err := c.Client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("delete failed: %s", resp.Status)
	}

	return nil
}

// GetMetadata retrieves file metadata
func (c *StorageClient) GetMetadata(path string) (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/files/%s/metadata", c.BaseURL, path)

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("Authorization", "Bearer "+c.Token)

	resp, err := c.Client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("get metadata failed: %s", resp.Status)
	}

	var metadata map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&metadata); err != nil {
		return nil, err
	}

	return metadata, nil
}

func main() {
	client := NewStorageClient(storageProxyURL, authToken)

	// Upload a file
	fmt.Println("1. Uploading file...")
	data := []byte("Hello from Go!")
	result, err := client.UploadFile("uploads:test/example.txt", data)
	if err != nil {
		fmt.Printf("   Error: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("   Uploaded: %v\n", result)

	// Download the file
	fmt.Println("\n2. Downloading file...")
	content, err := client.DownloadFile("uploads:test/example.txt")
	if err != nil {
		fmt.Printf("   Error: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("   Downloaded %d bytes: %s\n", len(content), string(content))

	// Get metadata
	fmt.Println("\n3. Getting metadata...")
	metadata, err := client.GetMetadata("uploads:test/example.txt")
	if err != nil {
		fmt.Printf("   Error: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("   Metadata: %v\n", metadata)

	// Delete file
	fmt.Println("\n4. Deleting file...")
	if err := client.DeleteFile("uploads:test/example.txt"); err != nil {
		fmt.Printf("   Error: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("   Deleted successfully")
}
