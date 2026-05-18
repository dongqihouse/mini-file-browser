# File Browser 项目

基于 Python3 + Flask 的内网文件浏览器，支持文件上传下载和 Docker 部署。

## 项目结构

```
file-browser/
├── src/                    # 源码目录
│   ├── app.py              # Flask app、配置、路由、入口
│   ├── i18n.py             # i18n 翻译字典 + get_lang() + t()
│   ├── utils.py            # get_file_size_str() + get_file_icon()
│   └── templates/
│       └── index.html      # HTML/CSS/JS 模板
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 镜像配置
├── docker-compose.yml      # Docker Compose 配置
├── data/                   # 文件存储目录
```

## 运行方式

### Docker Compose（推荐）
```bash
docker-compose up -d
```

### 本地开发
```bash
pip install -r requirements.txt
export FILE_STORAGE_PATH=./data
python src/app.py
```

访问: http://localhost:9100

## 环境变量

- `FILE_STORAGE_PATH`: 文件存储路径，默认 `/data`
- `PORT`: 端口，默认 `9100`
- `MAX_UPLOAD_SIZE`: 最大上传大小，默认 100MB
- `ALLOWED_EXTENSIONS`: 允许的扩展名（逗号分隔），空为全部允许
