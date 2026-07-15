# Mini File Browser

[![English](https://img.shields.io/badge/Docs-English-blue)](./README.md)

基于 Python3 + Flask 的轻量级内网文件浏览器，支持文件上传下载、目录管理和 Docker 一键部署。

## 功能特性

- **文件浏览** - 目录导航、面包屑路径、文件类型图标
- **文件上传** - 多文件/文件夹上传、拖拽上传、上传进度条
- **文件预览/下载** - HTML（含交互式脚本）和文本文件可预览，其他文件可下载
- **目录管理** - 创建文件夹、删除文件与文件夹
- **安全防护** - 路径遍历防护、扩展名限制、非 root 运行
- **响应式界面** - 适配桌面和移动端
- **REST API** - 文件列表 JSON 接口、multipart 文件上传接口
- **Docker 部署** - 开箱即用，支持 Docker Compose

## 快速开始

### Docker Compose（推荐）

```bash
git clone https://github.com/dongqihouse/mini-file-browser.git
cd mini-file-browser
docker-compose up -d
```

访问 http://127.0.0.1:9100

### 本地开发

```bash
pip install -r requirements.txt
export FILE_STORAGE_PATH=./data
python src/wsgi.py
```

## 配置

通过环境变量配置：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `FILE_STORAGE_PATH` | 文件存储路径 | `/data` |
| `PORT` | 服务端口 | `9100` |
| `HOST` | 监听地址 | `0.0.0.0` |
| `MAX_UPLOAD_SIZE` | 最大上传大小（字节） | `524288000` (500MB) |
| `ALLOWED_EXTENSIONS` | 允许的扩展名（逗号分隔，留空允许全部） | 空 |
| `SECRET_KEY` | Flask 密钥（生产环境请修改） | 内置默认值 |
| `DEBUG` | 调试模式 | `false` |
| `APP_BASE_URL` | 允许嵌入预览的文件浏览器源 | `http://127.0.0.1:9100` |
| `PREVIEW_BASE_URL` | 隔离的交互式预览源 | `http://preview.localhost:9100` |
| `PREVIEW_HOST` | 路由到只读预览应用的主机名 | 从 `PREVIEW_BASE_URL` 取得 |

## 交互式 HTML 预览

交互式预览运行在**独立的预览源**上。这样上传 HTML 中的内联脚本、相对 JavaScript、CSS、图片、字体、媒体以及同目录 iframe 可以运行，同时上传代码不会与文件浏览器 UI 或管理 API 同源。

默认本地配置下，请通过 `http://127.0.0.1:9100` 访问文件浏览器。点击 HTML 文件会在沙箱面板中加载 `http://preview.localhost:9100` 的内容；现代浏览器会将 `*.localhost` 解析到本机。不要把 preview hostname 作为主应用地址使用。

预览内容被有意限制：不能访问文件浏览器 API，不能发起 fetch/XHR/WebSocket，不能提交表单、打开弹窗、导航顶层页面、加载第三方资源，也不能访问父页面。`./app.js`、`./styles.css`、`images/logo.png`、`./child.html` 等相对资源仍然支持，但其扩展名必须在预览路由的允许范围内。

生产环境需要配置两个不同的 HTTPS 主机名（例如 `files.example.internal` 与 `preview.example-preview.internal`）并都转发到此服务，同时保留 `Host` 请求头；据此设置 `APP_BASE_URL`、`PREVIEW_BASE_URL` 和 `PREVIEW_HOST`。不要把应用 Cookie 配置为共享的 parent-domain `Domain=` Cookie，也不要让反向代理把 preview host 回退路由到主应用。

## API

```
GET /api/files              # 获取根目录文件列表
GET /api/files/<path>       # 获取指定目录文件列表
POST /api/upload            # 上传文件到根目录
POST /api/upload/<path>     # 上传文件到指定目录
```

响应示例：

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

普通文件上传使用 `multipart/form-data`，文件字段名可使用 `files` 或 `file`。目标目录必须已存在，重名文件会覆盖。

Web 界面支持在实现了 `webkitdirectory` 的现代浏览器中选择文件夹上传（Chromium 系浏览器和 Safari）。文件夹内的文件会保留嵌套路径和所选文件夹的根目录名；普通多文件选择和文件拖拽上传仍可用，暂不支持拖拽文件夹。浏览器只会提供文件条目，因此空文件夹不会被上传。

使用 API 上传文件夹时，必须使用 `files` 字段，并按相同顺序为每个文件发送一个 `relative_paths` 字段。路径必须使用 `/` 分隔，服务端会校验路径以防止目录穿越，并自动创建缺失的嵌套父目录。

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

上传成功响应示例：

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

## 项目结构

```
mini-file-browser/
├── src/                    # 源码目录
│   ├── app.py              # Flask 应用、路由、配置
│   ├── i18n.py             # i18n 翻译
│   ├── utils.py            # 工具函数
│   └── templates/
│       └── index.html      # HTML/CSS/JS 模板
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 镜像配置
├── docker-compose.yml      # Docker Compose 配置
└── data/                   # 文件存储目录（运行时生成）
```

## 技术栈

- **后端** - Python 3.11 / Flask / Gunicorn
- **前端** - 原生 HTML/CSS/JS（Jinja2 模板），零前端依赖
- **部署** - Docker / Docker Compose

## License

MIT
