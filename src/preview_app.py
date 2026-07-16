"""只读的可信文件预览应用。"""

from flask import Flask, abort, send_file

from preview_config import get_preview_settings, get_storage_dir
from utils import get_preview_mimetype, is_inline_preview_file


app = Flask(__name__)
BASE_DIR = get_storage_dir()
SETTINGS = get_preview_settings()
BASE_DIR.mkdir(parents=True, exist_ok=True)


def get_preview_file_path(path):
    """解析预览资源路径，拒绝存储目录外的文件和符号链接逃逸。"""
    if not path:
        return None

    file_path = (BASE_DIR / path).resolve()
    try:
        file_path.relative_to(BASE_DIR)
    except ValueError:
        return None

    return file_path


@app.route('/preview/<path:path>')
def preview(path):
    """内联提供允许的可信预览资源。"""
    file_path = get_preview_file_path(path)
    if (
        file_path is None
        or not file_path.exists()
        or file_path.is_dir()
        or not is_inline_preview_file(file_path.name)
    ):
        abort(404)

    return send_file(
        file_path,
        as_attachment=False,
        download_name=file_path.name,
        mimetype=get_preview_mimetype(file_path.name)
    )
