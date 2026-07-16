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

主应用访问 http://127.0.0.1:9100，HTML 预览使用同源 `/preview/...` 路由。

纯 IP 内网部署时，请将 `docker-compose.yml` 中的 `APP_BASE_URL` 改为客户端实际访问的服务器 IP 或域名（内置示例为 `10.16.10.62`），然后执行：

```bash
docker-compose up -d --build
# 防火墙只需要允许客户端访问 TCP 9100。
```

### 本地开发

启动主应用：

```bash
pip install -r requirements.txt
export FILE_STORAGE_PATH=./data
export APP_BASE_URL=http://127.0.0.1:9100
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
| `APP_BASE_URL` | 客户端可访问的主应用源；端口必须与 `PORT` 一致 | `http://127.0.0.1:9100` |

## 交互式 HTML 预览

交互式预览运行在**可信同源模式**下。点击 HTML 文件会直接进入主应用的 `/preview/...` 页面，让 HTML 占满浏览器内容区，不再包裹预览弹窗、iframe、标题栏或关闭按钮；响应也不添加限制脚本、网络请求或外部资源的 CSP。

同目录相对资源会继续通过预览路由加载，例如 `./app.js`、`./app.jsx`、`./styles.css`、`images/logo.png`、`./child.html`。如果 HTML 使用 Babel standalone 等运行时转换 JSX，确保对应脚本可以由浏览器访问；项目不会再用 CSP 阻止 CDN、内联脚本、XHR/fetch 或 Babel 的运行时转换。

该模式适合可信内网文件。预览 HTML 与文件浏览器同源，可以访问父页面和同源接口；请只预览你信任的 HTML。

手工生产部署时只需要启动主应用：

```bash
.venv/bin/gunicorn --bind 0.0.0.0:9100 --chdir src wsgi:application
```

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

Web 界面提供横向并排的“上传文件”和“上传文件夹”两个按钮，也可以将文件/文件夹拖拽到按钮区域。拖拽文件夹时会自动递归读取目录内容，并保留嵌套路径和拖拽文件夹的根目录名。浏览器只会提供文件条目，因此空文件夹不会被上传。

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
