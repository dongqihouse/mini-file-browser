"""交互式 HTML 预览的独立监听器和源配置。"""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


DEFAULT_APP_BASE_URL = 'http://127.0.0.1:9100'
DEFAULT_PREVIEW_BASE_URL = 'http://127.0.0.1:9101'
DEFAULT_PORT = 9100
DEFAULT_PREVIEW_PORT = 9101


@dataclass(frozen=True)
class PreviewSettings:
    """主应用与只读预览应用的显式 origin 和监听配置。"""

    app_base_url: str
    app_host: str
    app_port: int
    preview_base_url: str
    preview_host: str
    preview_port: int
    preview_bind_host: str


def get_port(value, name, default):
    """读取并验证 TCP 端口。"""
    try:
        port = int(os.environ.get(value, default))
    except ValueError as error:
        raise ValueError(f'Invalid {name}') from error

    if not 1 <= port <= 65535:
        raise ValueError(f'Invalid {name}')

    return port


def normalize_base_url(value, name):
    """验证外部 origin，禁止从请求 Host 推导预览地址。"""
    if not value:
        raise ValueError(f'{name} is required')

    parsed = urlsplit(value.strip())
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError(f'Invalid {name} port') from error

    if (
        parsed.scheme not in ('http', 'https')
        or parsed.username
        or parsed.password
        or parsed.path not in ('', '/')
        or parsed.query
        or parsed.fragment
        or not parsed.hostname
        or port is None
    ):
        raise ValueError(f'Invalid {name}')

    host = parsed.hostname.lower()
    display_host = f'[{host}]' if ':' in host else host
    netloc = f'{display_host}:{port}'
    return urlunsplit((parsed.scheme.lower(), netloc, '', '', '')), host, port


def get_preview_settings():
    """读取并校验主站与独立预览监听器配置。"""
    if 'PREVIEW_HOST' in os.environ:
        raise ValueError(
            'PREVIEW_HOST is no longer supported; use PREVIEW_BIND_HOST and PREVIEW_PORT'
        )

    app_base_url, app_host, app_port = normalize_base_url(
        os.environ.get('APP_BASE_URL', DEFAULT_APP_BASE_URL), 'APP_BASE_URL'
    )
    preview_base_url, preview_host, preview_port = normalize_base_url(
        os.environ.get('PREVIEW_BASE_URL', DEFAULT_PREVIEW_BASE_URL),
        'PREVIEW_BASE_URL'
    )
    main_listener_port = get_port('PORT', 'PORT', DEFAULT_PORT)
    preview_listener_port = get_port(
        'PREVIEW_PORT', 'PREVIEW_PORT', DEFAULT_PREVIEW_PORT
    )

    if app_port != main_listener_port:
        raise ValueError('APP_BASE_URL port must match PORT')
    if preview_port != preview_listener_port:
        raise ValueError('PREVIEW_BASE_URL port must match PREVIEW_PORT')
    if app_base_url == preview_base_url or app_port == preview_port:
        raise ValueError('APP_BASE_URL and PREVIEW_BASE_URL must use different ports')

    return PreviewSettings(
        app_base_url=app_base_url,
        app_host=app_host,
        app_port=app_port,
        preview_base_url=preview_base_url,
        preview_host=preview_host,
        preview_port=preview_port,
        preview_bind_host=os.environ.get('PREVIEW_BIND_HOST', '0.0.0.0')
    )


def get_storage_dir():
    """返回文件存储目录，保持主应用与预览应用一致。"""
    in_docker = Path('/.dockerenv').exists()
    default_storage = '/data' if in_docker else str(Path(__file__).resolve().parent.parent / 'data')
    return Path(os.environ.get('FILE_STORAGE_PATH', default_storage)).resolve()
