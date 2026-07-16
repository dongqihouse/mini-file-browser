"""主文件浏览器 WSGI 入口。"""

import os

from werkzeug.serving import run_simple

from app import app as application


if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 9100))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    run_simple(host, port, application, use_debugger=debug, use_reloader=debug)
