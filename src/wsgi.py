"""按 Host 将主文件浏览器和只读预览源分发给不同 WSGI 应用。"""

import os

from werkzeug.serving import run_simple
from werkzeug.wrappers import Response

from app import app as main_app
from preview_app import SETTINGS, app as preview_app
from preview_config import normalize_host


def get_request_host(environ):
    """从 WSGI 环境取得经验证的 Host 名称。"""
    host = environ.get('HTTP_HOST') or environ.get('SERVER_NAME')
    return normalize_host(host)


def application(environ, start_response):
    """预览主机只暴露只读 preview app，其他主机走主应用。"""
    try:
        host = get_request_host(environ)
    except ValueError:
        return Response('Invalid Host header', status=400)(environ, start_response)

    target_app = preview_app if host == SETTINGS.preview_host else main_app
    return target_app(environ, start_response)


if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 9100))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    run_simple(host, port, application, use_debugger=debug, use_reloader=debug)
