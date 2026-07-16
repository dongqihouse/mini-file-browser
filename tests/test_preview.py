import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

from werkzeug.test import Client
from werkzeug.wrappers import Response


class PreviewTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.temp_dir.name) / 'storage'
        self.environment = {
            key: os.environ.get(key)
            for key in (
                'FILE_STORAGE_PATH', 'APP_BASE_URL', 'PREVIEW_BASE_URL',
                'PREVIEW_HOST', 'PORT', 'PREVIEW_PORT', 'PREVIEW_BIND_HOST'
            )
        }
        os.environ['FILE_STORAGE_PATH'] = str(self.storage_dir)
        os.environ['APP_BASE_URL'] = 'http://10.16.10.62:9100'
        os.environ['PREVIEW_BASE_URL'] = 'http://10.16.10.62:9101'
        os.environ['PORT'] = '9100'
        os.environ['PREVIEW_PORT'] = '9101'
        os.environ['PREVIEW_BIND_HOST'] = '127.0.0.1'
        os.environ.pop('PREVIEW_HOST', None)

        self.app_module = self.reload_module('app')
        self.preview_module = self.reload_module('preview_app')
        self.wsgi_module = self.reload_module('wsgi')
        self.preview_wsgi_module = self.reload_module('preview_wsgi')
        self.app_module.app.config['TESTING'] = True
        self.preview_module.app.config['TESTING'] = True
        self.main_client = self.app_module.app.test_client()
        self.preview_client = self.preview_module.app.test_client()
        self.main_wsgi_client = Client(self.wsgi_module.application, Response)
        self.preview_wsgi_client = Client(self.preview_wsgi_module.application, Response)

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

    def test_ip_and_port_configuration_is_accepted(self):
        settings = self.preview_module.SETTINGS

        self.assertEqual(settings.app_base_url, 'http://10.16.10.62:9100')
        self.assertEqual(settings.preview_base_url, 'http://10.16.10.62:9101')
        self.assertEqual(settings.app_port, 9100)
        self.assertEqual(settings.preview_port, 9101)
        self.assertEqual(settings.preview_bind_host, '127.0.0.1')

    def test_preview_configuration_rejects_invalid_listener_origins(self):
        get_settings = self.reload_module('preview_config').get_preview_settings
        cases = (
            ({
                'PREVIEW_BASE_URL': 'http://10.16.10.62:9100',
                'PREVIEW_PORT': '9100'
            }, 'APP_BASE_URL and PREVIEW_BASE_URL must use different ports'),
            ({'APP_BASE_URL': 'http://10.16.10.62:9200'},
             'APP_BASE_URL port must match PORT'),
            ({'PREVIEW_BASE_URL': 'http://10.16.10.62:9200'},
             'PREVIEW_BASE_URL port must match PREVIEW_PORT'),
            ({'PREVIEW_BASE_URL': 'http://10.16.10.62'},
             'Invalid PREVIEW_BASE_URL'),
            ({'PREVIEW_HOST': 'preview.localhost'},
             'PREVIEW_HOST is no longer supported'),
        )

        for updates, message in cases:
            with self.subTest(updates=updates):
                original = {key: os.environ.get(key) for key in updates}
                os.environ.update(updates)
                try:
                    with self.assertRaisesRegex(ValueError, message):
                        get_settings()
                finally:
                    for key, value in original.items():
                        if value is None:
                            os.environ.pop(key, None)
                        else:
                            os.environ[key] = value

    def test_main_preview_route_serves_trusted_html_inline(self):
        self.write_file('项目/预览.html', b'<h1>preview</h1>')

        response = self.main_client.get('/preview/项目/预览.html')
        self.addCleanup(response.close)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/html')
        self.assertEqual(response.data, b'<h1>preview</h1>')
        self.assertNotIn('Location', response.headers)
        self.assertNotIn('Content-Security-Policy', response.headers)

    def test_preview_serves_html_and_relative_assets_without_sandbox_headers(self):
        self.write_file(
            'Site/index.html',
            b'<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>'
            b'<script type="text/babel" src="./app.jsx"></script>'
            b'<script src="./app.js"></script><iframe src="./child.html"></iframe>'
        )
        self.write_file('Site/app.js', b'document.body.dataset.ready = "true";')
        self.write_file('Site/app.jsx', b'const App = () => <h1>ready</h1>;')
        self.write_file('Site/styles.css', b'body { color: green; }')
        self.write_file('Site/child.html', b'<h1>child</h1>')

        response = self.preview_client.get('/preview/Site/index.html')
        self.addCleanup(response.close)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/html')
        self.assertIn(b'./app.js', response.data)
        self.assertIn(b'./app.jsx', response.data)
        self.assertIn(b'https://unpkg.com/@babel/standalone/babel.min.js', response.data)
        self.assertNotIn('Content-Security-Policy', response.headers)
        self.assertNotIn('X-Content-Type-Options', response.headers)
        self.assertNotIn('Referrer-Policy', response.headers)
        self.assertNotIn('Permissions-Policy', response.headers)
        self.assertNotIn('Set-Cookie', response.headers)

        javascript = self.preview_client.get('/preview/Site/app.js')
        jsx = self.preview_client.get('/preview/Site/app.jsx')
        stylesheet = self.preview_client.get('/preview/Site/styles.css')
        child = self.preview_client.get('/preview/Site/child.html')
        for asset_response in (javascript, jsx, stylesheet, child):
            self.addCleanup(asset_response.close)

        self.assertEqual(javascript.status_code, 200)
        self.assertEqual(javascript.mimetype, 'application/javascript')
        self.assertEqual(jsx.status_code, 200)
        self.assertEqual(jsx.mimetype, 'text/jsx')
        self.assertEqual(stylesheet.status_code, 200)
        self.assertEqual(stylesheet.mimetype, 'text/css')
        self.assertEqual(child.status_code, 200)
        self.assertNotIn('Content-Security-Policy', child.headers)

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

    def test_preview_wsgi_exposes_no_browser_or_management_routes(self):
        self.assertEqual(self.preview_wsgi_client.get('/').status_code, 404)
        self.assertEqual(self.preview_wsgi_client.get('/api/files').status_code, 404)
        self.assertEqual(self.preview_wsgi_client.post('/api/upload').status_code, 404)
        self.assertEqual(self.preview_wsgi_client.post('/delete/example.txt').status_code, 404)

    def test_wsgi_listeners_are_not_selected_by_request_host(self):
        self.write_file('Site/index.html', b'<h1>preview</h1>')

        main_response = self.main_wsgi_client.get(
            '/', headers={'Host': 'preview.localhost:9100'}
        )
        main_preview = self.main_wsgi_client.get(
            '/preview/Site/index.html', headers={'Host': 'preview.localhost:9100'}
        )
        preview_response = self.preview_wsgi_client.get('/preview/Site/index.html')
        for response in (main_response, main_preview, preview_response):
            self.addCleanup(response.close)

        self.assertEqual(main_response.status_code, 200)
        self.assertEqual(main_preview.status_code, 200)
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(preview_response.mimetype, 'text/html')

    def test_template_links_directly_to_trusted_preview_without_preview_ui(self):
        self.write_file("quote'\"<tag>.html", b'<h1>preview</h1>')

        response = self.main_client.get('/')
        page = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/preview/', page)
        self.assertNotIn('previewModal', page)
        self.assertNotIn('previewFrame', page)
        self.assertNotIn('preview-trigger', page)
        self.assertNotIn('data-preview-url=', page)
        self.assertNotIn('openPreview', page)
        self.assertNotIn('closePreview', page)
        self.assertNotIn('sandbox=', page)
        self.assertNotIn('referrerpolicy=', page)
        self.assertIn('data-delete-name=', page)
        self.assertNotIn('previewOpenNew', page)
        self.assertNotIn('preview_open_new', page)
        self.assertNotIn('onclick="confirmDelete(', page)
        self.assertNotIn('target="_blank"', page)


if __name__ == '__main__':
    unittest.main()
