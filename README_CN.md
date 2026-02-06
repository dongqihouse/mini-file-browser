# Mini File Browser

[![English](https://img.shields.io/badge/Docs-English-blue)](./README.md)

基于 Python3 + Flask 的轻量级内网文件浏览器，支持文件上传下载、目录管理和 Docker 一键部署。

## 功能特性

- **文件浏览** - 目录导航、面包屑路径、文件类型图标
- **文件上传** - 多文件上传、拖拽上传、上传进度条
- **文件下载** - 点击直接下载
- **目录管理** - 创建文件夹、删除文件与文件夹
- **安全防护** - 路径遍历防护、扩展名限制、非 root 运行
- **响应式界面** - 适配桌面和移动端
- **REST API** - 文件列表 JSON 接口
- **Docker 部署** - 开箱即用，支持 Docker Compose

## 快速开始

### Docker Compose（推荐）

```bash
git clone https://github.com/dongqihouse/mini-file-browser.git
cd mini-file-browser
docker-compose up -d
```

访问 http://localhost:9100

### 本地开发

```bash
pip install -r requirements.txt
export FILE_STORAGE_PATH=./data
python src/app.py
```

## 配置

通过环境变量配置：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `FILE_STORAGE_PATH` | 文件存储路径 | `/data` |
| `PORT` | 服务端口 | `9100` |
| `HOST` | 监听地址 | `0.0.0.0` |
| `MAX_UPLOAD_SIZE` | 最大上传大小（字节） | `104857600` (100MB) |
| `ALLOWED_EXTENSIONS` | 允许的扩展名（逗号分隔，留空允许全部） | 空 |
| `SECRET_KEY` | Flask 密钥（生产环境请修改） | 内置默认值 |
| `DEBUG` | 调试模式 | `false` |

## API

```
GET /api/files              # 获取根目录文件列表
GET /api/files/<path>       # 获取指定目录文件列表
```

响应示例：

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
