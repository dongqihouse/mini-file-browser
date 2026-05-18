#!/usr/bin/env python3
"""
Simple File Browser - 内网文件上传下载服务
基于Python3标准库 + Flask
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, render_template, request, send_file,
    redirect, url_for, flash, jsonify, abort
)
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from i18n import TRANSLATIONS, get_lang, t
from utils import get_file_size_str, get_file_icon

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'file-browser-secret-key-change-me')

# 配置
_in_docker = Path('/.dockerenv').exists()
_default_storage = '/data' if _in_docker else str(Path(__file__).resolve().parent.parent / 'data')
BASE_DIR = Path(os.environ.get('FILE_STORAGE_PATH', _default_storage)).resolve()
MAX_UPLOAD_SIZE = int(os.environ.get('MAX_UPLOAD_SIZE', 500 * 1024 * 1024))  # 默认500MB
ALLOWED_EXTENSIONS = os.environ.get('ALLOWED_EXTENSIONS', '')  # 空表示允许所有
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE

# 确保存储目录存在
BASE_DIR.mkdir(parents=True, exist_ok=True)


def safe_path(path_str):
    """确保路径安全，不能逃逸出BASE_DIR"""
    if not path_str:
        return BASE_DIR

    # 清理路径
    clean_path = Path(path_str).as_posix()
    clean_path = clean_path.lstrip('/')

    # 构建完整路径并解析
    full_path = (BASE_DIR / clean_path).resolve()

    # 确保路径在BASE_DIR内
    try:
        full_path.relative_to(BASE_DIR)
    except ValueError:
        return BASE_DIR

    return full_path


def get_breadcrumbs(rel_path):
    """生成面包屑导航"""
    if not rel_path or rel_path == '.':
        return [(t('root_dir'), '')]

    parts = Path(rel_path).parts
    breadcrumbs = [(t('root_dir'), '')]

    current = ''
    for part in parts:
        current = f"{current}/{part}" if current else part
        breadcrumbs.append((part, current))

    return breadcrumbs


def get_request_files():
    """获取请求中的所有上传文件，兼容 files/file/自定义字段名"""
    files = []
    for key in request.files:
        files.extend(request.files.getlist(key))
    return files


def clean_upload_filename(raw_filename):
    """清理上传文件名，避免客户端传入路径片段"""
    filename = secure_filename(raw_filename)
    if filename:
        return filename

    basename = Path(raw_filename.replace('\\', '/')).name.strip()
    if basename in ('', '.', '..'):
        return ''

    return basename


def is_extension_allowed(filename):
    """检查文件扩展名是否允许"""
    if not ALLOWED_EXTENSIONS:
        return True, ''

    allowed = [ext.strip().lower() for ext in ALLOWED_EXTENSIONS.split(',') if ext.strip()]
    if not allowed:
        return True, ''

    ext = Path(filename).suffix.lower()
    if ext and ext not in allowed and ext.lstrip('.') not in allowed:
        return False, ext

    return True, ext


def save_uploaded_files(files, target_dir):
    """保存上传文件，返回成功列表和错误列表"""
    uploaded = []
    errors = []
    target_dir = target_dir.resolve()

    for file in files:
        raw_filename = file.filename or ''
        if not raw_filename:
            errors.append({
                'filename': raw_filename,
                'code': 'empty_filename',
                'message': 'No filename provided'
            })
            continue

        filename = clean_upload_filename(raw_filename)
        if not filename:
            errors.append({
                'filename': raw_filename,
                'code': 'invalid_filename',
                'message': 'Invalid filename'
            })
            continue

        allowed, ext = is_extension_allowed(filename)
        if not allowed:
            errors.append({
                'filename': filename,
                'code': 'extension_not_allowed',
                'message': f'File type {ext} is not allowed',
                'extension': ext
            })
            continue

        file_path = (target_dir / filename).resolve()
        try:
            file_path.relative_to(target_dir)
            file_path.relative_to(BASE_DIR)
        except ValueError:
            errors.append({
                'filename': filename,
                'code': 'invalid_path',
                'message': 'Invalid upload path'
            })
            continue

        try:
            overwritten = file_path.exists()
            file.save(file_path)
            uploaded.append({
                'name': filename,
                'path': file_path.relative_to(BASE_DIR).as_posix(),
                'size': file_path.stat().st_size,
                'overwritten': overwritten
            })
        except Exception as e:
            errors.append({
                'filename': filename,
                'code': 'save_failed',
                'message': str(e)
            })

    return uploaded, errors


@app.errorhandler(RequestEntityTooLarge)
def handle_upload_too_large(error):
    """上传超过大小限制时返回更友好的响应"""
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'File is too large',
            'max_upload_size': MAX_UPLOAD_SIZE
        }), 413

    return t('flash_upload_too_large', max_size=get_file_size_str(MAX_UPLOAD_SIZE)), 413


@app.route('/')
@app.route('/browse/')
@app.route('/browse/<path:path>')
def browse(path=''):
    """浏览目录"""
    current_dir = safe_path(path)

    if not current_dir.exists():
        flash(t('flash_dir_not_exist'), 'error')
        return redirect(url_for('browse'))

    if not current_dir.is_dir():
        return redirect(url_for('download', path=path))

    # 获取相对路径
    try:
        rel_path = current_dir.relative_to(BASE_DIR).as_posix()
        if rel_path == '.':
            rel_path = ''
    except ValueError:
        rel_path = ''

    # 获取父目录路径
    parent_path = None
    if rel_path:
        parent = Path(rel_path).parent.as_posix()
        parent_path = '' if parent == '.' else parent

    # 获取目录内容
    items = []
    try:
        for entry in sorted(current_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            stat = entry.stat()
            item_rel_path = (Path(rel_path) / entry.name).as_posix() if rel_path else entry.name

            items.append({
                'name': entry.name,
                'path': item_rel_path,
                'is_dir': entry.is_dir(),
                'size': get_file_size_str(stat.st_size) if not entry.is_dir() else '',
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                'icon': get_file_icon(entry.name, entry.is_dir())
            })
    except PermissionError:
        flash(t('flash_no_permission'), 'error')

    return render_template(
        'index.html',
        items=items,
        current_path=rel_path,
        parent_path=parent_path,
        breadcrumbs=get_breadcrumbs(rel_path),
        i18n=TRANSLATIONS[get_lang()],
        lang=get_lang()
    )


@app.route('/download/<path:path>')
def download(path):
    """下载文件"""
    file_path = safe_path(path)

    if not file_path.exists():
        abort(404)

    if file_path.is_dir():
        return redirect(url_for('browse', path=path))

    return send_file(
        file_path,
        as_attachment=True,
        download_name=file_path.name
    )


@app.route('/upload/', methods=['POST'])
@app.route('/upload/<path:path>', methods=['POST'])
def upload(path=''):
    """上传文件"""
    target_dir = safe_path(path)

    if not target_dir.exists() or not target_dir.is_dir():
        flash(t('flash_target_dir_not_exist'), 'error')
        return redirect(url_for('browse', path=path))

    files = get_request_files()
    if not files:
        flash(t('flash_no_file_selected'), 'error')
        return redirect(url_for('browse', path=path))

    uploaded, errors = save_uploaded_files(files, target_dir)

    for error in errors:
        if error['code'] == 'extension_not_allowed':
            flash(t('flash_ext_not_allowed', ext=error['extension']), 'error')
        elif error['code'] in ('empty_filename', 'invalid_filename'):
            flash(t('flash_no_file_selected'), 'error')
        else:
            flash(t('flash_upload_file_failed', name=error.get('filename', ''), error=error['message']), 'error')

    if uploaded:
        flash(t('flash_upload_success', count=len(uploaded)), 'success')

    return redirect(url_for('browse', path=path))


@app.route('/new_folder/', methods=['POST'])
@app.route('/new_folder/<path:path>', methods=['POST'])
def new_folder(path=''):
    """创建新文件夹"""
    parent_dir = safe_path(path)
    folder_name = request.form.get('folder_name', '').strip()

    if not folder_name:
        flash(t('flash_folder_name_empty'), 'error')
        return redirect(url_for('browse', path=path))

    # 清理文件夹名称
    folder_name = secure_filename(folder_name)
    if not folder_name:
        folder_name = request.form.get('folder_name', '').strip()

    new_dir = parent_dir / folder_name

    if new_dir.exists():
        flash(t('flash_folder_exists'), 'error')
    else:
        try:
            new_dir.mkdir(parents=True)
            flash(t('flash_folder_created', name=folder_name), 'success')
        except Exception as e:
            flash(t('flash_folder_create_failed', error=str(e)), 'error')

    return redirect(url_for('browse', path=path))


@app.route('/delete/<path:path>', methods=['POST'])
def delete(path):
    """删除文件或文件夹"""
    target = safe_path(path)

    if not target.exists():
        flash(t('flash_not_exist'), 'error')
        return redirect(url_for('browse'))

    # 不允许删除根目录
    if target == BASE_DIR:
        flash(t('flash_cannot_delete_root'), 'error')
        return redirect(url_for('browse'))

    # 获取父目录路径用于重定向
    try:
        rel_path = target.relative_to(BASE_DIR)
        parent_path = rel_path.parent.as_posix()
        if parent_path == '.':
            parent_path = ''
    except ValueError:
        parent_path = ''

    try:
        name = target.name
        if target.is_dir():
            shutil.rmtree(target)
            flash(t('flash_delete_folder_success', name=name), 'success')
        else:
            target.unlink()
            flash(t('flash_delete_file_success', name=name), 'success')
    except Exception as e:
        flash(t('flash_delete_failed', error=str(e)), 'error')

    return redirect(url_for('browse', path=parent_path))


@app.route('/api/upload', methods=['POST'])
@app.route('/api/upload/', methods=['POST'])
@app.route('/api/upload/<path:path>', methods=['POST'])
def api_upload(path=''):
    """API: 上传文件"""
    target_dir = safe_path(path)

    if not target_dir.exists() or not target_dir.is_dir():
        return jsonify({
            'error': 'Target directory does not exist',
            'uploaded': [],
            'errors': []
        }), 404

    files = get_request_files()
    if not files:
        return jsonify({
            'error': 'No file selected',
            'uploaded': [],
            'errors': []
        }), 400

    uploaded, errors = save_uploaded_files(files, target_dir)
    status_code = 201 if uploaded else 400

    response = {
        'count': len(uploaded),
        'uploaded': uploaded,
        'errors': errors
    }
    if not uploaded:
        response['error'] = 'No file uploaded'

    return jsonify(response), status_code


@app.route('/api/files')
@app.route('/api/files/<path:path>')
def api_files(path=''):
    """API: 获取文件列表"""
    current_dir = safe_path(path)

    if not current_dir.exists() or not current_dir.is_dir():
        return jsonify({'error': '目录不存在'}), 404

    items = []
    for entry in current_dir.iterdir():
        stat = entry.stat()
        items.append({
            'name': entry.name,
            'is_dir': entry.is_dir(),
            'size': stat.st_size if not entry.is_dir() else 0,
            'modified': stat.st_mtime
        })

    return jsonify({'items': items})


if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 9100))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    print(f"📂 File Browser 启动中...")
    print(f"🌐 访问地址: http://{host}:{port}")
    print(f"📁 存储目录: {BASE_DIR}")

    app.run(host=host, port=port, debug=debug)
