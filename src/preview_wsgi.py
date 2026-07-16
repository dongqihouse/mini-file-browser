"""只读交互预览 WSGI 入口。"""

import os

from werkzeug.serving import run_simple

from preview_app import SETTINGS, app as application


if __name__ == '__main__':
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    run_simple(
        SETTINGS.preview_bind_host,
        SETTINGS.preview_port,
        application,
        use_debugger=debug,
        use_reloader=debug
    )
