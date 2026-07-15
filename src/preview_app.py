"""只读的交互式文件预览应用。"""

from flask import Flask, abort, send_file

from preview_config import get_preview_settings, get_storage_dir
from utils import get_preview_mimetype, is_html_preview_file, is_inline_preview_file


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


def get_preview_csp():
    """返回允许本地交互、禁止网络和危险能力的预览 CSP。"""
    allowed_ancestors = f"{SETTINGS.app_base_url} {SETTINGS.preview_base_url}"
    return (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "media-src 'self' data: blob:; "
        "connect-src 'none'; "
        "worker-src 'none'; "
        "child-src 'self'; "
        "frame-src 'self'; "
        "object-src 'none'; "
        "base-uri 'none'; "
        "form-action 'none'; "
        "manifest-src 'none'; "
        f"frame-ancestors {allowed_ancestors}"
    )


@app.route('/preview/<path:path>')
def preview(path):
    """在隔离预览源下内联提供允许的资源。"""
    file_path = get_preview_file_path(path)
    if (
        file_path is None
        or not file_path.exists()
        or file_path.is_dir()
        or not is_inline_preview_file(file_path.name)
    ):
        abort(404)

    response = send_file(
        file_path,
        as_attachment=False,
        download_name=file_path.name,
        mimetype=get_preview_mimetype(file_path.name)
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'camera=(), geolocation=(), microphone=()'

    if is_html_preview_file(file_path.name):
        response.headers['Content-Security-Policy'] = get_preview_csp()

    return response
