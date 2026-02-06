"""工具函数模块"""

from pathlib import Path


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
