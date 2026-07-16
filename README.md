# Mini File Browser

[![中文文档](https://img.shields.io/badge/文档-中文版-blue)](./README_CN.md)

A lightweight file browser for internal networks, built with Python3 + Flask. Supports file upload/download, directory management, and one-click Docker deployment.

## Features

- **File Browsing** - Directory navigation, breadcrumb path, file type icons
- **File Upload** - Multi-file and folder uploads, drag & drop, progress bar
- **File Preview/Download** - Preview interactive HTML and text files, download other files
- **Directory Management** - Create folders, delete files/folders
- **Security** - Path traversal protection, extension restriction, non-root user
- **Responsive UI** - Desktop and mobile friendly
- **REST API** - JSON file listing endpoint and multipart file upload endpoint
- **Docker Ready** - Out-of-the-box with Docker Compose

## Quick Start

### Docker Compose (Recommended)

```bash
git clone https://github.com/dongqihouse/mini-file-browser.git
cd mini-file-browser
docker-compose up -d
```

Visit the main application at http://127.0.0.1:9100. HTML previews use the same-origin `/preview/...` route.

For an IP-only intranet deployment, change `APP_BASE_URL` in `docker-compose.yml` to the server IP or hostname that clients use (the included example uses `10.16.10.62`). Then run:

```bash
docker-compose up -d --build
# Allow client access to TCP port 9100.
```

### Local Development

Start the main application:

```bash
pip install -r requirements.txt
export FILE_STORAGE_PATH=./data
export APP_BASE_URL=http://127.0.0.1:9100
python src/wsgi.py
```

## Configuration

Configure via environment variables:

| Variable | Description | Default |
|---|---|---|
| `FILE_STORAGE_PATH` | File storage path | `/data` |
| `PORT` | Service port | `9100` |
| `HOST` | Listen address | `0.0.0.0` |
| `MAX_UPLOAD_SIZE` | Max upload size in bytes | `524288000` (500MB) |
| `ALLOWED_EXTENSIONS` | Allowed extensions (comma-separated, empty for all) | empty |
| `SECRET_KEY` | Flask secret key (change in production) | built-in default |
| `DEBUG` | Debug mode | `false` |
| `APP_BASE_URL` | Externally reachable main-application origin; its port must equal `PORT` | `http://127.0.0.1:9100` |

## Interactive HTML previews

Interactive previews run in **trusted same-origin mode**. Clicking an HTML file opens the main application's `/preview/...` page directly so the HTML fills the browser content area, without a preview modal, iframe, title bar, or close button. Responses do not add a CSP that blocks scripts, network requests, or external resources.

Relative resources in the same folder continue to load through the preview route, including `./app.js`, `./app.jsx`, `./styles.css`, `images/logo.png`, and `./child.html`. If an HTML file uses Babel standalone or a similar runtime JSX transformer, make sure the runtime script is reachable by the browser; this app no longer blocks CDN scripts, inline scripts, XHR/fetch, or Babel's runtime transform.

This mode is intended for trusted intranet files. Previewed HTML is same-origin with the file browser and can access the parent page and same-origin APIs; only preview HTML you trust.

For a manual production deployment, run the main application:

```bash
.venv/bin/gunicorn --bind 0.0.0.0:9100 --chdir src wsgi:application
```

## API

```
GET /api/files              # List files in root directory
GET /api/files/<path>       # List files in specified directory
POST /api/upload            # Upload files to root directory
POST /api/upload/<path>     # Upload files to specified directory
```

Response example:

```json
{
  "items": [
    {
      "name": "example.txt",
      "is_dir": false,
      "is_previewable": true,
      "size": 1024,
      "modified": 1700000000.0
    }
  ]
}
```

Flat upload requests use `multipart/form-data`; the file field name can be `files` or `file`.
The target directory must already exist, and existing files with the same name are overwritten.

The web UI shows two side-by-side buttons for uploading files and uploading a folder, and files/folders can also be dropped onto the button area. Dropped folders are read recursively and retain nested paths, including the dropped root folder. Empty directories cannot be uploaded because browsers only provide file entries.

For API folder uploads, use the `files` field and send one `relative_paths` field for every file in the same order. Paths must use `/` separators, are validated to prevent traversal, and missing nested parent directories are created automatically.

```bash
curl -F "files=@example.txt" http://localhost:9100/api/upload
curl -F "files=@a.txt" -F "files=@b.jpg" http://localhost:9100/api/upload/docs
curl \
  -F "files=@Project/docs/readme.txt" \
  -F "relative_paths=Project/docs/readme.txt" \
  -F "files=@Project/src/app.py" \
  -F "relative_paths=Project/src/app.py" \
  http://localhost:9100/api/upload
```

Successful upload response example:

```json
{
  "count": 1,
  "uploaded": [
    {
      "name": "example.txt",
      "path": "example.txt",
      "size": 1024,
      "overwritten": false
    }
  ],
  "errors": []
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
