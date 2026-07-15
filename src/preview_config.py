"""交互式 HTML 预览的独立源配置。"""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


DEFAULT_APP_BASE_URL = 'http://127.0.0.1:9100'
DEFAULT_PREVIEW_BASE_URL = 'http://preview.localhost:9100'


@dataclass(frozen=True)
class PreviewSettings:
    """主应用与只读预览应用的显式源配置。"""

    app_base_url: str
    app_host: str
    preview_base_url: str
    preview_host: str


def normalize_host(value):
    """验证 Host 值并返回小写主机名，不含端口。"""
    if not value:
        raise ValueError('Host is required')

    parsed = urlsplit(f'//{value.strip()}')
    if (
        parsed.username
        or parsed.password
        or parsed.path not in ('', '/')
        or parsed.query
        or parsed.fragment
        or not parsed.hostname
    ):
        raise ValueError('Invalid host')

    try:
        parsed.port
    except ValueError as error:
        raise ValueError('Invalid host port') from error

    return parsed.hostname.lower()


def normalize_base_url(value, name):
    """验证外部基地址，避免从请求 Host 推导预览源。"""
    if not value:
        raise ValueError(f'{name} is required')

    parsed = urlsplit(value.strip())
    if (
        parsed.scheme not in ('http', 'https')
        or parsed.username
        or parsed.password
        or parsed.path not in ('', '/')
        or parsed.query
        or parsed.fragment
        or not parsed.hostname
    ):
        raise ValueError(f'Invalid {name}')

    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError(f'Invalid {name} port') from error

    host = parsed.hostname.lower()
    display_host = f'[{host}]' if ':' in host else host
    netloc = display_host if port is None else f'{display_host}:{port}'
    return urlunsplit((parsed.scheme.lower(), netloc, '', '', '')), host


def get_preview_settings():
    """读取并校验隔离预览源的配置。"""
    app_base_url, app_host = normalize_base_url(
        os.environ.get('APP_BASE_URL', DEFAULT_APP_BASE_URL), 'APP_BASE_URL'
    )
    preview_base_url, preview_url_host = normalize_base_url(
        os.environ.get('PREVIEW_BASE_URL', DEFAULT_PREVIEW_BASE_URL),
        'PREVIEW_BASE_URL'
    )
    preview_host = normalize_host(
        os.environ.get('PREVIEW_HOST', preview_url_host)
    )

    if preview_host != preview_url_host:
        raise ValueError('PREVIEW_HOST must match PREVIEW_BASE_URL')
    if app_host == preview_host:
        raise ValueError('APP_BASE_URL and PREVIEW_BASE_URL must use different hosts')

    return PreviewSettings(
        app_base_url=app_base_url,
        app_host=app_host,
        preview_base_url=preview_base_url,
        preview_host=preview_host
    )


def get_storage_dir():
    """返回文件存储目录，保持主应用与预览应用一致。"""
    in_docker = Path('/.dockerenv').exists()
    default_storage = '/data' if in_docker else str(Path(__file__).resolve().parent.parent / 'data')
    return Path(os.environ.get('FILE_STORAGE_PATH', default_storage)).resolve()
