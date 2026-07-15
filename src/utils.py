"""工具函数模块"""

import mimetypes
from pathlib import Path

HTML_PREVIEW_EXTENSIONS = {'.html', '.htm'}

TEXT_PREVIEW_EXTENSIONS = {
    '.txt', '.md', '.markdown', '.log', '.csv',
    '.json', '.xml', '.yaml', '.yml',
    '.css', '.js', '.mjs', '.ts', '.tsx',
    '.py', '.sh', '.bat', '.ini', '.conf', '.env',
}

INLINE_PREVIEW_ASSET_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.ico',
    '.svg', '.mp3', '.wav', '.ogg', '.mp4', '.webm',
    '.woff', '.woff2', '.ttf', '.otf',
}

PREVIEW_EXTENSIONS = HTML_PREVIEW_EXTENSIONS | TEXT_PREVIEW_EXTENSIONS
INLINE_PREVIEW_EXTENSIONS = PREVIEW_EXTENSIONS | INLINE_PREVIEW_ASSET_EXTENSIONS


def get_file_size_str(size_bytes):
    """将字节数转换为人类可读的格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def get_file_icon(filename, is_dir=False):
    """根据文件类型返回图标"""
    if is_dir:
        return '📁'

    ext = Path(filename).suffix.lower()
    icons = {
        '.txt': '📄', '.md': '📝', '.log': '📋',
        '.py': '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨',
        '.json': '📊', '.xml': '📰', '.yaml': '⚙️', '.yml': '⚙️',
        '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️', '.svg': '🖼️',
        '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵',
        '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬', '.mov': '🎬',
        '.zip': '📦', '.tar': '📦', '.gz': '📦', '.rar': '📦', '.7z': '📦',
        '.pdf': '📕', '.doc': '📘', '.docx': '📘', '.xls': '📗', '.xlsx': '📗',
        '.exe': '⚡', '.sh': '🔧', '.bat': '🔧',
    }
    return icons.get(ext, '📄')


def is_previewable_file(filename):
    """判断文件是否支持浏览器内预览"""
    return Path(filename).suffix.lower() in PREVIEW_EXTENSIONS


def is_html_preview_file(filename):
    """判断文件是否是 HTML 预览"""
    return Path(filename).suffix.lower() in HTML_PREVIEW_EXTENSIONS


def is_inline_preview_file(filename):
    """判断文件是否允许通过预览路由内联展示或作为 HTML 资源加载"""
    return Path(filename).suffix.lower() in INLINE_PREVIEW_EXTENSIONS


def get_preview_mimetype(filename):
    """返回预览响应使用的 MIME 类型"""
    ext = Path(filename).suffix.lower()
    if ext in HTML_PREVIEW_EXTENSIONS:
        return 'text/html'
    if ext == '.css':
        return 'text/css'
    if ext in {'.js', '.mjs'}:
        return 'application/javascript'
    if ext == '.json':
        return 'application/json'
    if ext == '.xml':
        return 'application/xml'

    guessed_type, _ = mimetypes.guess_type(filename)
    if guessed_type:
        return guessed_type

    return 'text/plain'
