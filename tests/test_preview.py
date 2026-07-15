import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from werkzeug.test import Client
from werkzeug.wrappers import Response


class PreviewTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.temp_dir.name) / 'storage'
        self.environment = {
            key: os.environ.get(key)
            for key in (
                'FILE_STORAGE_PATH', 'APP_BASE_URL',
                'PREVIEW_BASE_URL', 'PREVIEW_HOST'
            )
        }
        os.environ['FILE_STORAGE_PATH'] = str(self.storage_dir)
        os.environ['APP_BASE_URL'] = 'http://127.0.0.1:9100'
        os.environ['PREVIEW_BASE_URL'] = 'http://preview.localhost:9100'
        os.environ['PREVIEW_HOST'] = 'preview.localhost'

        self.app_module = self.reload_module('app')
        self.preview_module = self.reload_module('preview_app')
        self.wsgi_module = self.reload_module('wsgi')
        self.app_module.app.config['TESTING'] = True
        self.preview_module.app.config['TESTING'] = True
        self.main_client = self.app_module.app.test_client()
        self.preview_client = self.preview_module.app.test_client()
        self.dispatch_client = Client(self.wsgi_module.application, Response)

    def tearDown(self):
        for key, value in self.environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    @staticmethod
    def reload_module(name):
        if name in sys.modules:
            return importlib.reload(sys.modules[name])
        return importlib.import_module(name)

    def write_file(self, relative_path, content):
        file_path = self.storage_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return file_path

    def test_main_preview_route_redirects_to_isolated_origin(self):
        self.write_file('项目/预览.html', b'<h1>preview</h1>')

        response = self.main_client.get('/preview/项目/预览.html')

        self.assertEqual(response.status_code, 302)
        location = response.headers['Location']
        parsed = urlsplit(location)
        self.assertEqual(parsed.scheme, 'http')
        self.assertEqual(parsed.netloc, 'preview.localhost:9100')
        self.assertEqual(parsed.path, '/preview/%E9%A1%B9%E7%9B%AE/%E9%A2%84%E8%A7%88.html')

    def test_preview_serves_html_and_relative_assets_with_security_headers(self):
        self.write_file(
            'Site/index.html',
            b'<script src="./app.js"></script><iframe src="./child.html"></iframe>'
        )
        self.write_file('Site/app.js', b'document.body.dataset.ready = "true";')
        self.write_file('Site/styles.css', b'body { color: green; }')
        self.write_file('Site/child.html', b'<h1>child</h1>')

        response = self.preview_client.get('/preview/Site/index.html')
        self.addCleanup(response.close)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/html')
        self.assertIn(b'./app.js', response.data)
        csp = response.headers['Content-Security-Policy']
        self.assertIn("script-src 'self' 'unsafe-inline'", csp)
        self.assertIn("connect-src 'none'", csp)
        self.assertIn("form-action 'none'", csp)
        self.assertIn("frame-src 'self'", csp)
        self.assertIn('frame-ancestors http://127.0.0.1:9100 http://preview.localhost:9100', csp)
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['Referrer-Policy'], 'no-referrer')
        self.assertEqual(
            response.headers['Permissions-Policy'],
            'camera=(), geolocation=(), microphone=()'
        )

        javascript = self.preview_client.get('/preview/Site/app.js')
        stylesheet = self.preview_client.get('/preview/Site/styles.css')
        child = self.preview_client.get('/preview/Site/child.html')
        for asset_response in (javascript, stylesheet, child):
            self.addCleanup(asset_response.close)

        self.assertEqual(javascript.status_code, 200)
        self.assertEqual(javascript.mimetype, 'application/javascript')
        self.assertEqual(javascript.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(stylesheet.status_code, 200)
        self.assertEqual(stylesheet.mimetype, 'text/css')
        self.assertEqual(child.status_code, 200)
        self.assertIn("script-src 'self' 'unsafe-inline'", child.headers['Content-Security-Policy'])

    def test_preview_rejects_directories_unsupported_extensions_and_escaped_paths(self):
        self.write_file('Site/index.html', b'<h1>preview</h1>')
        self.write_file('Site/program.exe', b'not previewable')
        outside_file = Path(self.temp_dir.name) / 'outside.html'
        outside_file.write_bytes(b'outside')
        (self.storage_dir / 'escaped.html').symlink_to(outside_file)

        self.assertEqual(self.preview_client.get('/preview/Site').status_code, 404)
        self.assertEqual(self.preview_client.get('/preview/Site/program.exe').status_code, 404)
        self.assertEqual(self.preview_client.get('/preview/escaped.html').status_code, 404)
        self.assertEqual(self.preview_client.get('/preview/../outside.html').status_code, 404)

    def test_preview_app_exposes_no_browser_or_management_routes(self):
        self.assertEqual(self.preview_client.get('/').status_code, 404)
        self.assertEqual(self.preview_client.get('/api/files').status_code, 404)
        self.assertEqual(self.preview_client.post('/api/upload').status_code, 404)
        self.assertEqual(self.preview_client.post('/delete/example.txt').status_code, 404)

    def test_wsgi_dispatches_preview_host_to_preview_only_application(self):
        self.write_file('Site/index.html', b'<h1>preview</h1>')

        main_response = self.dispatch_client.get('/', headers={'Host': '127.0.0.1:9100'})
        preview_response = self.dispatch_client.get(
            '/preview/Site/index.html',
            headers={'Host': 'preview.localhost:9100'}
        )
        preview_root = self.dispatch_client.get('/', headers={'Host': 'preview.localhost:9100'})
        preview_api = self.dispatch_client.get(
            '/api/files', headers={'Host': 'preview.localhost:9100'}
        )
        main_preview = self.dispatch_client.get(
            '/preview/Site/index.html', headers={'Host': '127.0.0.1:9100'}
        )
        for response in (
            main_response, preview_response, preview_root, preview_api, main_preview
        ):
            self.addCleanup(response.close)

        self.assertEqual(main_response.status_code, 200)
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(preview_response.mimetype, 'text/html')
        self.assertEqual(preview_root.status_code, 404)
        self.assertEqual(preview_api.status_code, 404)
        self.assertEqual(main_preview.status_code, 302)


if __name__ == '__main__':
    unittest.main()
