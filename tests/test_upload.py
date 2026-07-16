import importlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

from werkzeug.datastructures import MultiDict


class FailingUpload:
    filename = 'existing.txt'

    def save(self, destination):
        destination.write(b'partial')
        raise OSError('simulated upload failure')


class UploadTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.temp_dir.name) / 'storage'
        self.old_storage_path = os.environ.get('FILE_STORAGE_PATH')
        self.old_allowed_extensions = os.environ.get('ALLOWED_EXTENSIONS')
        self.preview_environment = {
            key: os.environ.get(key)
            for key in ('APP_BASE_URL', 'PREVIEW_BASE_URL', 'PREVIEW_HOST', 'PORT', 'PREVIEW_PORT')
        }
        os.environ['FILE_STORAGE_PATH'] = str(self.storage_dir)
        os.environ['APP_BASE_URL'] = 'http://127.0.0.1:9100'
        os.environ['PREVIEW_BASE_URL'] = 'http://127.0.0.1:9101'
        os.environ['PORT'] = '9100'
        os.environ['PREVIEW_PORT'] = '9101'
        os.environ.pop('PREVIEW_HOST', None)
        os.environ.pop('ALLOWED_EXTENSIONS', None)

        if 'app' in sys.modules:
            self.app_module = importlib.reload(sys.modules['app'])
        else:
            self.app_module = importlib.import_module('app')

        self.app_module.app.config['TESTING'] = True
        self.client = self.app_module.app.test_client()

    def tearDown(self):
        if self.old_storage_path is None:
            os.environ.pop('FILE_STORAGE_PATH', None)
        else:
            os.environ['FILE_STORAGE_PATH'] = self.old_storage_path

        if self.old_allowed_extensions is None:
            os.environ.pop('ALLOWED_EXTENSIONS', None)
        else:
            os.environ['ALLOWED_EXTENSIONS'] = self.old_allowed_extensions

        for key, value in self.preview_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        self.temp_dir.cleanup()

    def post_folder_upload(self, entries, path=''):
        data = MultiDict()
        for content, relative_path in entries:
            data.add('files', (io.BytesIO(content), 'upload.bin'))
            data.add('relative_paths', relative_path)

        url = '/api/upload' if not path else f'/api/upload/{path}'
        return self.client.post(url, data=data, content_type='multipart/form-data')

    def test_flat_upload_remains_compatible(self):
        data = MultiDict([
            ('file', (io.BytesIO(b'first'), 'first.txt')),
            ('files', (io.BytesIO(b'second'), 'second.txt')),
        ])

        response = self.client.post('/api/upload', data=data, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['count'], 2)
        self.assertEqual((self.storage_dir / 'first.txt').read_bytes(), b'first')
        self.assertEqual((self.storage_dir / 'second.txt').read_bytes(), b'second')

    def test_flat_upload_preserves_unicode_html_name_and_preview(self):
        data = MultiDict([
            ('files', (io.BytesIO(b'<h1>preview</h1>'), '预览.html')),
        ])

        response = self.client.post('/api/upload', data=data, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['uploaded'][0]['path'], '预览.html')
        self.assertEqual((self.storage_dir / '预览.html').read_bytes(), b'<h1>preview</h1>')

        preview_response = self.client.get('/preview/预览.html')
        self.addCleanup(preview_response.close)
        self.assertEqual(preview_response.status_code, 200)
        self.assertEqual(preview_response.mimetype, 'text/html')
        self.assertEqual(preview_response.data, b'<h1>preview</h1>')

    def test_folder_upload_creates_nested_directories(self):
        response = self.post_folder_upload([
            (b'# Project', 'Project/docs/readme.md'),
            (b'print("hello")', 'Project/src/app.py'),
        ])

        payload = response.get_json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload['count'], 2)
        self.assertEqual(
            {item['path'] for item in payload['uploaded']},
            {'Project/docs/readme.md', 'Project/src/app.py'}
        )
        self.assertEqual((self.storage_dir / 'Project/docs/readme.md').read_bytes(), b'# Project')
        self.assertEqual((self.storage_dir / 'Project/src/app.py').read_bytes(), b'print("hello")')

    def test_folder_upload_preserves_unicode_top_level_name_and_paths(self):
        entries = [
            (b'homepage', '赛事中心07101857/首页/预览.html'),
            (b'event-center', '赛事中心07101857/赛事中心/07101857_赛事中心_.html'),
            (b'search', '赛事中心07101857/搜索/07101857_搜索_.html'),
            (b'event-search', '赛事中心07101857/event-search/07101857_event-search_.html'),
        ]

        response = self.post_folder_upload(entries)

        expected_paths = {relative_path for _, relative_path in entries}
        payload = response.get_json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload['count'], len(entries))
        self.assertEqual({item['path'] for item in payload['uploaded']}, expected_paths)
        for content, relative_path in entries:
            self.assertEqual((self.storage_dir / relative_path).read_bytes(), content)

    def test_folder_upload_uses_current_target_directory(self):
        target_dir = self.storage_dir / 'existing-target'
        target_dir.mkdir(parents=True)

        response = self.post_folder_upload(
            [(b'notes', 'Project/notes/todo.txt')],
            path='existing-target'
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            (target_dir / 'Project/notes/todo.txt').read_bytes(),
            b'notes'
        )
        self.assertFalse((self.storage_dir / 'Project').exists())

    def test_folder_upload_rejects_mismatched_metadata_without_writing(self):
        data = MultiDict([
            ('files', (io.BytesIO(b'one'), 'one.txt')),
            ('relative_paths', 'Project/one.txt'),
            ('files', (io.BytesIO(b'two'), 'two.txt')),
        ])

        response = self.client.post('/api/upload', data=data, content_type='multipart/form-data')

        payload = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(payload['code'], 'invalid_folder_upload')
        self.assertFalse((self.storage_dir / 'Project').exists())

    def test_folder_upload_rejects_unsafe_paths(self):
        unsafe_paths = [
            '../outside.txt',
            'Project/../../outside.txt',
            '/absolute.txt',
            r'Project\outside.txt',
            'Project//outside.txt',
            'C:/outside.txt',
        ]

        for relative_path in unsafe_paths:
            with self.subTest(relative_path=relative_path):
                response = self.post_folder_upload([(b'blocked', relative_path)])
                payload = response.get_json()

                self.assertEqual(response.status_code, 400)
                self.assertEqual(payload['errors'][0]['code'], 'invalid_path')
                self.assertFalse((self.storage_dir / 'outside.txt').exists())

    def test_folder_upload_allows_partial_success(self):
        response = self.post_folder_upload([
            (b'valid', 'Project/keep.txt'),
            (b'blocked', '../outside.txt'),
        ])

        payload = response.get_json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload['count'], 1)
        self.assertEqual(payload['errors'][0]['code'], 'invalid_path')
        self.assertEqual((self.storage_dir / 'Project/keep.txt').read_bytes(), b'valid')
        self.assertFalse((self.storage_dir / 'outside.txt').exists())

    def test_folder_upload_enforces_extension_restrictions(self):
        self.app_module.ALLOWED_EXTENSIONS = '.txt'

        response = self.post_folder_upload([
            (b'allowed', 'Project/allowed.txt'),
            (b'blocked', 'Project/blocked.exe'),
        ])

        payload = response.get_json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(payload['count'], 1)
        self.assertEqual(payload['errors'][0]['code'], 'extension_not_allowed')
        self.assertEqual((self.storage_dir / 'Project/allowed.txt').read_bytes(), b'allowed')
        self.assertFalse((self.storage_dir / 'Project/blocked.exe').exists())

    def test_folder_upload_rejects_escaped_target_directory(self):
        outside_dir = Path(self.temp_dir.name) / 'outside'
        outside_dir.mkdir()
        target_link = self.storage_dir / 'linked-target'
        target_link.symlink_to(outside_dir, target_is_directory=True)

        response = self.post_folder_upload(
            [(b'blocked', 'Project/file.txt')],
            path='linked-target'
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse((outside_dir / 'Project/file.txt').exists())

    def test_folder_upload_rejects_symlink_paths(self):
        outside_dir = Path(self.temp_dir.name) / 'outside'
        outside_dir.mkdir()
        directory_link = self.storage_dir / 'linked'
        directory_link.symlink_to(outside_dir, target_is_directory=True)

        response = self.post_folder_upload([(b'blocked', 'linked/escape.txt')])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['errors'][0]['code'], 'invalid_path')
        self.assertFalse((outside_dir / 'escape.txt').exists())

        outside_file = outside_dir / 'original.txt'
        outside_file.write_bytes(b'original')
        file_link = self.storage_dir / 'linked-file.txt'
        file_link.symlink_to(outside_file)

        response = self.post_folder_upload([(b'blocked', 'linked-file.txt')])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['errors'][0]['code'], 'invalid_path')
        self.assertEqual(outside_file.read_bytes(), b'original')

    def test_folder_upload_replaces_hard_link_without_modifying_target(self):
        outside_dir = Path(self.temp_dir.name) / 'outside'
        outside_dir.mkdir()
        outside_file = outside_dir / 'original.txt'
        outside_file.write_bytes(b'original')
        hard_link = self.storage_dir / 'hard-linked.txt'
        os.link(outside_file, hard_link)

        response = self.post_folder_upload([(b'uploaded', 'hard-linked.txt')])

        self.assertEqual(response.status_code, 201)
        self.assertEqual(hard_link.read_bytes(), b'uploaded')
        self.assertEqual(outside_file.read_bytes(), b'original')

    def test_failed_overwrite_keeps_existing_file(self):
        existing_file = self.storage_dir / 'existing.txt'
        existing_file.write_bytes(b'original')

        uploaded, errors = self.app_module.save_uploaded_files(
            [(FailingUpload(), None)], self.storage_dir
        )

        self.assertEqual(uploaded, [])
        self.assertEqual(errors[0]['code'], 'save_failed')
        self.assertEqual(existing_file.read_bytes(), b'original')
        self.assertEqual(list(self.storage_dir.glob('.upload-*')), [])

    def test_upload_page_uses_one_entry_with_automatic_folder_drop_support(self):
        response = self.client.get('/')
        page = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(page.count('class="upload-label"'), 1)
        self.assertIn('id="fileInput"', page)
        self.assertNotIn('id="folderInput"', page)
        self.assertNotIn('webkitdirectory', page)
        self.assertNotIn('upload_folder_hint', page)
        self.assertIn('webkitGetAsEntry', page)
        self.assertIn('relative_paths', page)

    def test_html_folder_upload_redirects_after_saving(self):
        data = MultiDict([
            ('files', (io.BytesIO(b'content'), 'file.txt')),
            ('relative_paths', 'Project/file.txt'),
        ])

        response = self.client.post('/upload/', data=data, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 302)
        self.assertEqual((self.storage_dir / 'Project/file.txt').read_bytes(), b'content')


if __name__ == '__main__':
    unittest.main()
