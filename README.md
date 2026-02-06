# Mini File Browser

[![中文文档](https://img.shields.io/badge/文档-中文版-blue)](./README_CN.md)

A lightweight file browser for internal networks, built with Python3 + Flask. Supports file upload/download, directory management, and one-click Docker deployment.

## Features

- **File Browsing** - Directory navigation, breadcrumb path, file type icons
- **File Upload** - Multi-file upload, drag & drop, progress bar
- **File Download** - Click to download
- **Directory Management** - Create folders, delete files/folders
- **Security** - Path traversal protection, extension restriction, non-root user
- **Responsive UI** - Desktop and mobile friendly
- **REST API** - JSON file listing endpoint
- **Docker Ready** - Out-of-the-box with Docker Compose

## Quick Start

### Docker Compose (Recommended)

```bash
git clone https://github.com/drayl/mini-file-browser.git
cd mini-file-browser
docker-compose up -d
```

Visit http://localhost:9100

### Local Development

```bash
pip install -r requirements.txt
export FILE_STORAGE_PATH=./data
python src/app.py
```

## Configuration

Configure via environment variables:

| Variable | Description | Default |
|---|---|---|
| `FILE_STORAGE_PATH` | File storage path | `/data` |
| `PORT` | Service port | `9100` |
| `HOST` | Listen address | `0.0.0.0` |
| `MAX_UPLOAD_SIZE` | Max upload size in bytes | `104857600` (100MB) |
| `ALLOWED_EXTENSIONS` | Allowed extensions (comma-separated, empty for all) | empty |
| `SECRET_KEY` | Flask secret key (change in production) | built-in default |
| `DEBUG` | Debug mode | `false` |

## API

```
GET /api/files              # List files in root directory
GET /api/files/<path>       # List files in specified directory
```

Response example:

```json
{
  "items": [
    {
      "name": "example.txt",
      "is_dir": false,
      "size": 1024,
      "modified": 1700000000.0
    }
  ]
}
```

## Project Structure

```
mini-file-browser/
├── src/                    # Source code
│   ├── app.py              # Flask app, routes, config
│   ├── i18n.py             # i18n translations
│   ├── utils.py            # Utility functions
│   └── templates/
│       └── index.html      # HTML/CSS/JS template
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker image config
├── docker-compose.yml      # Docker Compose config
└── data/                   # File storage directory (created at runtime)
```

## Tech Stack

- **Backend** - Python 3.11 / Flask / Gunicorn
- **Frontend** - Vanilla HTML/CSS/JS (Jinja2 templates), zero frontend dependencies
- **Deployment** - Docker / Docker Compose

## License

MIT
