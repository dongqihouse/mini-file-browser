"""i18n 翻译模块"""

from flask import request

TRANSLATIONS = {
    'en': {
        'title': 'File Browser',
        'root_dir': 'Root',
        'new_folder_btn': 'New Folder',
        'upload_hint': 'Click to upload files, or drag files/folders here',
        'folder_upload_unsupported': 'Folder upload is not supported by this browser',
        'parent_dir': 'Go to parent directory',
        'download': 'Download',
        'preview_title': 'Preview: {name}',
        'preview_close': 'Close preview',
        'delete': 'Delete',
        'empty_state': 'Folder is empty, upload some files!',
        'new_folder_title': 'New Folder',
        'folder_name_placeholder': 'Folder name',
        'cancel': 'Cancel',
        'create': 'Create',
        'confirm_delete_title': 'Confirm Delete',
        'confirm_delete_file': 'Are you sure to delete file "{name}"?',
        'confirm_delete_folder': 'Are you sure to delete folder "{name}"? All contents will be deleted!',
        'upload_failed': 'Upload failed: ',
        'upload_error': 'Upload error',
        'flash_dir_not_exist': 'Directory does not exist',
        'flash_no_permission': 'No permission to access this directory',
        'flash_target_dir_not_exist': 'Target directory does not exist',
        'flash_no_file_selected': 'No file selected',
        'flash_ext_not_allowed': 'File type {ext} is not allowed',
        'flash_upload_file_failed': 'Failed to upload "{name}": {error}',
        'flash_upload_too_large': 'Upload exceeds maximum size: {max_size}',
        'flash_upload_success': 'Successfully uploaded {count} file(s)',
        'flash_folder_upload_metadata_invalid': 'Folder upload files and paths do not match',
        'flash_invalid_upload_path': 'Invalid folder upload path: {name}',
        'flash_folder_name_empty': 'Folder name cannot be empty',
        'flash_folder_exists': 'Folder already exists',
        'flash_folder_created': 'Successfully created folder "{name}"',
        'flash_folder_create_failed': 'Failed to create folder: {error}',
        'flash_not_exist': 'File or folder does not exist',
        'flash_cannot_delete_root': 'Cannot delete root directory',
        'flash_delete_folder_success': 'Successfully deleted folder "{name}"',
        'flash_delete_file_success': 'Successfully deleted file "{name}"',
        'flash_delete_failed': 'Delete failed: {error}',
    },
    'zh': {
        'title': '文件浏览器',
        'root_dir': '根目录',
        'new_folder_btn': '新建文件夹',
        'upload_hint': '点击上传文件，或拖拽文件/文件夹到此处',
        'folder_upload_unsupported': '当前浏览器不支持文件夹上传',
        'parent_dir': '返回上级目录',
        'download': '下载',
        'preview_title': '预览：{name}',
        'preview_close': '关闭预览',
        'delete': '删除',
        'empty_state': '文件夹为空，上传一些文件吧！',
        'new_folder_title': '新建文件夹',
        'folder_name_placeholder': '文件夹名称',
        'cancel': '取消',
        'create': '创建',
        'confirm_delete_title': '确认删除',
        'confirm_delete_file': '确定要删除文件 "{name}" 吗？',
        'confirm_delete_folder': '确定要删除文件夹 "{name}" 吗？这将删除文件夹内的所有内容！',
        'upload_failed': '上传失败：',
        'upload_error': '上传出错',
        'flash_dir_not_exist': '目录不存在',
        'flash_no_permission': '没有权限访问此目录',
        'flash_target_dir_not_exist': '目标目录不存在',
        'flash_no_file_selected': '没有选择文件',
        'flash_ext_not_allowed': '不允许上传 {ext} 类型的文件',
        'flash_upload_file_failed': '上传 "{name}" 失败：{error}',
        'flash_upload_too_large': '上传超过最大限制：{max_size}',
        'flash_upload_success': '成功上传 {count} 个文件',
        'flash_folder_upload_metadata_invalid': '文件夹上传的文件与路径信息不匹配',
        'flash_invalid_upload_path': '无效的文件夹上传路径：{name}',
        'flash_folder_name_empty': '文件夹名称不能为空',
        'flash_folder_exists': '文件夹已存在',
        'flash_folder_created': '成功创建文件夹 "{name}"',
        'flash_folder_create_failed': '创建文件夹失败: {error}',
        'flash_not_exist': '文件或文件夹不存在',
        'flash_cannot_delete_root': '不能删除根目录',
        'flash_delete_folder_success': '成功删除文件夹 "{name}"',
        'flash_delete_file_success': '成功删除文件 "{name}"',
        'flash_delete_failed': '删除失败: {error}',
    }
}


def get_lang():
    """从 cookie 读取语言偏好，默认 en"""
    return request.cookies.get('lang', 'en') if request else 'en'


def t(key, **kwargs):
    """获取翻译文本"""
    lang = get_lang()
    text = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
