#!/usr/bin/env python3
"""
Simple File Browser - 内网文件上传下载服务
基于Python3标准库 + Flask
"""

import errno
import os
import secrets
import shutil
import stat
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, render_template, request, send_file,
    redirect, url_for, flash, jsonify, abort
)
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from i18n import TRANSLATIONS, get_lang, t
from preview_config import get_storage_dir
from utils import (
    get_file_size_str, get_file_icon, get_preview_mimetype,
    is_inline_preview_file, is_previewable_file
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'file-browser-secret-key-change-me')

# 配置
BASE_DIR = get_storage_dir()
PORT = int(os.environ.get('PORT', 9100))
APP_BASE_URL = os.environ.get('APP_BASE_URL', f'http://127.0.0.1:{PORT}')
MAX_UPLOAD_SIZE = int(os.environ.get('MAX_UPLOAD_SIZE', 500 * 1024 * 1024))  # 默认500MB
ALLOWED_EXTENSIONS = os.environ.get('ALLOWED_EXTENSIONS', '')  # 空表示允许所有
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
    SESSION_COOKIE_SECURE=APP_BASE_URL.startswith('https://'),
    SESSION_COOKIE_DOMAIN=None
)

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


def get_upload_target_dir(path_str):
    """解析上传目标目录；无效路径不会回退到存储根目录。"""
    if not path_str:
        return BASE_DIR

    clean_path = Path(path_str).as_posix().lstrip('/')
    target_dir = (BASE_DIR / clean_path).resolve()
    try:
        target_dir.relative_to(BASE_DIR)
    except ValueError:
        return None

    return target_dir


def get_preview_url(path):
    """构造同源可信预览地址。"""
    return url_for('preview', path=path)


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


def get_upload_entries():
    """解析平铺或文件夹上传请求，返回文件与相对路径的配对。"""
    relative_paths = request.form.getlist('relative_paths')
    if not relative_paths:
        return [(file, None) for file in get_request_files()], None

    files = request.files.getlist('files')
    if any(key != 'files' for key in request.files) or len(files) != len(relative_paths):
        return [], {
            'code': 'invalid_folder_upload',
            'message': 'Folder upload files and paths do not match'
        }

    return list(zip(files, relative_paths)), None


def clean_upload_filename(raw_filename):
    """提取安全的上传文件名，并保留 Unicode 名称。"""
    filename = Path(raw_filename.replace('\\', '/')).name.strip()
    if '\x00' in filename or filename in ('', '.', '..'):
        return ''

    return filename


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


def clean_upload_path_parts(relative_path):
    """验证文件夹上传的相对路径，并安全地清理每个组件。"""
    if (
        not relative_path
        or '\x00' in relative_path
        or '\\' in relative_path
        or relative_path.startswith('/')
    ):
        return None

    raw_parts = relative_path.split('/')
    if any(not part or part in ('.', '..') for part in raw_parts):
        return None

    path_parts = []
    for part in raw_parts:
        if len(part) >= 2 and part[0].isalpha() and part[1] == ':':
            return None

        # 文件夹上传的路径来自 webkitRelativePath；保留已验证的 Unicode 名称。
        path_parts.append(part)

    return path_parts


def save_file_to_destination(file, target_dir, path_parts):
    """使用目录文件描述符和原子替换保存文件，避免跟随符号链接。"""
    base_dir = BASE_DIR.resolve()
    target_dir = target_dir.resolve()
    try:
        target_parts = target_dir.relative_to(base_dir).parts
    except ValueError:
        return None, False, 0, 'invalid_path', 'Invalid upload path'

    if not hasattr(os, 'O_DIRECTORY') or not hasattr(os, 'O_NOFOLLOW'):
        return None, False, 0, 'save_failed', 'Secure folder uploads are not supported on this platform'

    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    file_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    parent_fd = None
    temp_dir_fd = None
    temp_dir_name = None
    temp_file_name = 'upload'

    try:
        parent_fd = os.open(base_dir, directory_flags)

        for part in target_parts:
            child_fd = os.open(part, directory_flags, dir_fd=parent_fd)
            previous_fd = parent_fd
            parent_fd = child_fd
            os.close(previous_fd)

        for part in path_parts[:-1]:
            try:
                os.mkdir(part, dir_fd=parent_fd)
            except FileExistsError:
                pass

            child_fd = os.open(part, directory_flags, dir_fd=parent_fd)
            previous_fd = parent_fd
            parent_fd = child_fd
            os.close(previous_fd)

        filename = path_parts[-1]
        try:
            existing = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            overwritten = False
        else:
            if not stat.S_ISREG(existing.st_mode):
                return None, False, 0, 'invalid_path', 'Invalid upload path'
            overwritten = True

        for _ in range(10):
            candidate_dir_name = f'.upload-{secrets.token_hex(16)}'
            try:
                os.mkdir(candidate_dir_name, 0o700, dir_fd=parent_fd)
            except FileExistsError:
                continue

            temp_dir_name = candidate_dir_name
            temp_dir_fd = os.open(temp_dir_name, directory_flags, dir_fd=parent_fd)
            break
        else:
            return None, False, 0, 'save_failed', 'Failed to create upload directory'

        file_fd = os.open(temp_file_name, file_flags, 0o666, dir_fd=temp_dir_fd)
        with os.fdopen(file_fd, 'wb') as destination:
            file.save(destination)
            size = os.fstat(destination.fileno()).st_size

        os.replace(
            temp_file_name,
            filename,
            src_dir_fd=temp_dir_fd,
            dst_dir_fd=parent_fd
        )

        return target_dir.joinpath(*path_parts), overwritten, size, None, None
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            return None, False, 0, 'invalid_path', 'Invalid upload path'
        return None, False, 0, 'save_failed', 'Failed to save file'
    except Exception:
        return None, False, 0, 'save_failed', 'Failed to save file'
    finally:
        if temp_dir_fd is not None:
            try:
                os.unlink(temp_file_name, dir_fd=temp_dir_fd)
            except OSError:
                pass
            os.close(temp_dir_fd)
        if temp_dir_name is not None and parent_fd is not None:
            try:
                os.rmdir(temp_dir_name, dir_fd=parent_fd)
            except OSError:
                pass
        if parent_fd is not None:
            os.close(parent_fd)


def save_uploaded_files(entries, target_dir):
    """保存上传条目，返回成功列表和错误列表。"""
    uploaded = []
    errors = []

    for file, relative_path in entries:
        raw_filename = file.filename or ''
        display_filename = relative_path if relative_path is not None else raw_filename

        if relative_path is None:
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

            path_parts = [filename]
        else:
            path_parts = clean_upload_path_parts(relative_path)
            if not path_parts:
                errors.append({
                    'filename': display_filename,
                    'code': 'invalid_path',
                    'message': 'Invalid upload path'
                })
                continue
            filename = path_parts[-1]

        allowed, ext = is_extension_allowed(filename)
        if not allowed:
            errors.append({
                'filename': display_filename,
                'code': 'extension_not_allowed',
                'message': f'File type {ext} is not allowed',
                'extension': ext
            })
            continue

        file_path, overwritten, size, error_code, error_message = save_file_to_destination(
            file, target_dir, path_parts
        )
        if error_code:
            errors.append({
                'filename': display_filename,
                'code': error_code,
                'message': error_message
            })
            continue

        uploaded.append({
            'name': filename,
            'path': file_path.relative_to(BASE_DIR).as_posix(),
            'size': size,
            'overwritten': overwritten
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
                'is_previewable': not entry.is_dir() and is_previewable_file(entry.name),
                'preview_url': get_preview_url(item_rel_path) if not entry.is_dir() and is_previewable_file(entry.name) else '',
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


@app.route('/preview/<path:path>')
def preview(path):
    """在主应用同源下内联预览可信文件。"""
    file_path = safe_path(path)

    if not file_path.exists() or file_path.is_dir() or not is_inline_preview_file(file_path.name):
        abort(404)

    return send_file(
        file_path,
        as_attachment=False,
        download_name=file_path.name,
        mimetype=get_preview_mimetype(file_path.name)
    )


@app.route('/upload/', methods=['POST'])
@app.route('/upload/<path:path>', methods=['POST'])
def upload(path=''):
    """上传文件"""
    target_dir = get_upload_target_dir(path)

    if target_dir is None or not target_dir.exists() or not target_dir.is_dir():
        flash(t('flash_target_dir_not_exist'), 'error')
        return redirect(url_for('browse', path=path))

    entries, request_error = get_upload_entries()
    if request_error:
        flash(t('flash_folder_upload_metadata_invalid'), 'error')
        return redirect(url_for('browse', path=path))

    if not entries:
        flash(t('flash_no_file_selected'), 'error')
        return redirect(url_for('browse', path=path))

    uploaded, errors = save_uploaded_files(entries, target_dir)

    for error in errors:
        if error['code'] == 'extension_not_allowed':
            flash(t('flash_ext_not_allowed', ext=error['extension']), 'error')
        elif error['code'] in ('empty_filename', 'invalid_filename'):
            flash(t('flash_no_file_selected'), 'error')
        elif error['code'] == 'invalid_path':
            flash(t('flash_invalid_upload_path', name=error.get('filename', '')), 'error')
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
    target_dir = get_upload_target_dir(path)

    if target_dir is None or not target_dir.exists() or not target_dir.is_dir():
        return jsonify({
            'error': 'Target directory does not exist',
            'uploaded': [],
            'errors': []
        }), 404

    entries, request_error = get_upload_entries()
    if request_error:
        return jsonify({
            'error': request_error['message'],
            'code': request_error['code'],
            'uploaded': [],
            'errors': [request_error]
        }), 400

    if not entries:
        return jsonify({
            'error': 'No file selected',
            'uploaded': [],
            'errors': []
        }), 400

    uploaded, errors = save_uploaded_files(entries, target_dir)
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
            'is_previewable': not entry.is_dir() and is_previewable_file(entry.name),
            'size': stat.st_size if not entry.is_dir() else 0,
            'modified': stat.st_mtime
        })

    return jsonify({'items': items})


if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    print("📂 File Browser 主应用启动中...")
    print(f"🌐 主应用: {APP_BASE_URL}")
    print("🪟 HTML 预览: 同源可信模式")
    print(f"📁 存储目录: {BASE_DIR}")

    app.run(host=host, port=PORT, debug=debug)
