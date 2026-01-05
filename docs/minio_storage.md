# MinIO Object Storage

Image and video storage using MinIO on the DB node.

## Overview

```
┌───────────────────────────────────────────────────────────────┐
│                         DB NODE                                │
│                                                                │
│   ┌─────────────────────┐    ┌─────────────────────┐          │
│   │     PostgreSQL      │    │       MinIO         │          │
│   │                     │    │                     │          │
│   │  news_id            │    │  bucket: news-media │          │
│   │  content            │───►│  ├── a3f2b8c9/      │          │
│   │  minio_main_image   │    │  │   ├── main.jpg   │          │
│   │  minio_images[]     │    │  │   ├── img1.jpg   │          │
│   │  ...                │    │  │   └── img2.jpg   │          │
│   └─────────────────────┘    │  ├── b4c5d6e7/      │          │
│                              │  │   └── main.jpg   │          │
│                              └─────────────────────┘          │
└───────────────────────────────────────────────────────────────┘
```

## Configuration

| Setting | Value |
|---------|-------|
| Location | DB node (same machine as PostgreSQL) |
| Storage limit | 100 GB |
| Bucket name | `news-media` |
| Access | Internal only (via VPN) |

## Folder Structure

```
news-media/                    ← Bucket
├── {news_id}/                 ← Folder per news item
│   ├── main.jpg               ← Main image
│   ├── content_0.jpg          ← Content images
│   ├── content_1.jpg
│   └── content_2.png
├── {another_news_id}/
│   └── main.webp
```

## Data Flow

**DB node downloads images directly from original URLs.**

```
1. Crawler gets article + image URLs from news sites
2. Crawler → Orchestrator: sends metadata with image URLs (not bytes)
3. Orchestrator → DB node: forwards metadata
4. DB node:
   a. Generates news_id from URL
   b. Downloads images from original URLs
   c. Saves images to MinIO → gets internal paths
   d. Saves news metadata + MinIO paths to PostgreSQL
5. When VLM needs images:
   a. Orchestrator requests from DB node
   b. DB node reads from MinIO
   c. Returns image bytes to Orchestrator
   d. Orchestrator sends to VLM
```

**Why DB downloads (not Crawler):**
- Less data transfer through network
- DB has persistent storage
- Simpler Crawler code
- Easier retry logic if download fails

## MinIO Path Format

```
minio://news-media/{news_id}/{filename}
```

**Examples:**
- `minio://news-media/a3f2b8c9e1d4f5a6/main.jpg`
- `minio://news-media/a3f2b8c9e1d4f5a6/content_0.jpg`

## Setup (DB Node)

### Install MinIO

```bash
# Download
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/

# Create data directory
sudo mkdir -p /data/minio

# Start MinIO
export MINIO_ROOT_USER=admin
export MINIO_ROOT_PASSWORD=your_secure_password
minio server /data/minio --console-address ":9001"
```

### Create Bucket

```bash
# Install mc (MinIO client)
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# Configure
mc alias set local http://localhost:9000 admin your_secure_password

# Create bucket
mc mb local/news-media

# Set quota (100GB)
mc quota set local/news-media --size 100GB
```

### Systemd Service

```ini
# /etc/systemd/system/minio.service
[Unit]
Description=MinIO
After=network.target

[Service]
User=minio
Environment="MINIO_ROOT_USER=admin"
Environment="MINIO_ROOT_PASSWORD=your_secure_password"
ExecStart=/usr/local/bin/minio server /data/minio --console-address ":9001"
Restart=always

[Install]
WantedBy=multi-user.target
```

## Python Usage

```python
from minio import Minio
import io

client = Minio(
    "10.0.0.3:9000",  # DB node VPN IP
    access_key="admin",
    secret_key="your_secure_password",
    secure=False  # True if using HTTPS
)

# Upload image
def upload_image(news_id: str, filename: str, image_bytes: bytes) -> str:
    path = f"{news_id}/{filename}"
    client.put_object(
        bucket_name="news-media",
        object_name=path,
        data=io.BytesIO(image_bytes),
        length=len(image_bytes)
    )
    return f"minio://news-media/{path}"

# Download image
def download_image(news_id: str, filename: str) -> bytes:
    path = f"{news_id}/{filename}"
    response = client.get_object("news-media", path)
    return response.read()

# Delete news images
def delete_news_images(news_id: str):
    objects = client.list_objects("news-media", prefix=f"{news_id}/")
    for obj in objects:
        client.remove_object("news-media", obj.object_name)
```

## Requirements

Add to DB node's `requirements.txt`:
```
minio>=7.2.0
```

## Ports

| Port | Usage |
|------|-------|
| 9000 | MinIO API |
| 9001 | MinIO Console (web UI) |

**Firewall:** Only allow from VPN (10.0.0.0/24)
