import importlib
import io
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


class DownloadTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.temp_dir.name) / 'storage'
        self.environment = {
            key: os.environ.get(key)
            for key in ('FILE_STORAGE_PATH', 'APP_BASE_URL', 'PREVIEW_BASE_URL', 'PREVIEW_HOST', 'PORT', 'PREVIEW_PORT')
        }
        os.environ['FILE_STORAGE_PATH'] = str(self.storage_dir)
        os.environ['APP_BASE_URL'] = 'http://127.0.0.1:9100'
        os.environ['PREVIEW_BASE_URL'] = 'http://127.0.0.1:9101'
        os.environ['PORT'] = '9100'
        os.environ['PREVIEW_PORT'] = '9101'
        os.environ.pop('PREVIEW_HOST', None)

        if 'app' in sys.modules:
            self.app_module = importlib.reload(sys.modules['app'])
        else:
            self.app_module = importlib.import_module('app')

        self.app_module.app.config['TESTING'] = True
        self.client = self.app_module.app.test_client()

    def tearDown(self):
        for key, value in self.environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp_dir.cleanup()

    def write_file(self, relative_path, content):
        file_path = self.storage_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return file_path

    def test_downloads_folder_as_zip_with_nested_and_empty_directories(self):
        self.write_file('Project/docs/readme.txt', b'documentation')
        self.write_file('Project/app.py', b'print("hello")')
        (self.storage_dir / 'Project/empty').mkdir()

        response = self.client.get('/download/Project')
        self.addCleanup(response.close)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/zip')
        self.assertIn('attachment; filename=Project.zip', response.headers['Content-Disposition'])

        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {'Project/', 'Project/docs/', 'Project/docs/readme.txt', 'Project/app.py', 'Project/empty/'}
            )
            self.assertEqual(archive.read('Project/docs/readme.txt'), b'documentation')
            self.assertEqual(archive.read('Project/app.py'), b'print("hello")')

    def test_downloads_regular_file_as_an_attachment(self):
        self.write_file('notes.txt', b'keep existing file downloads')

        response = self.client.get('/download/notes.txt')
        self.addCleanup(response.close)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b'keep existing file downloads')
        self.assertIn('attachment; filename=notes.txt', response.headers['Content-Disposition'])

    def test_folder_archive_excludes_symbolic_links_and_escaped_directories(self):
        self.write_file('Project/inside.txt', b'inside')
        outside_dir = Path(self.temp_dir.name) / 'outside'
        outside_dir.mkdir()
        (outside_dir / 'secret.txt').write_bytes(b'secret')
        (self.storage_dir / 'Project/outside-file.txt').symlink_to(outside_dir / 'secret.txt')
        (self.storage_dir / 'Project/outside-folder').symlink_to(outside_dir, target_is_directory=True)
        (self.storage_dir / 'escaped').symlink_to(outside_dir, target_is_directory=True)

        response = self.client.get('/download/Project')
        self.addCleanup(response.close)

        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            self.assertEqual(set(archive.namelist()), {'Project/', 'Project/inside.txt'})

        self.assertEqual(self.client.get('/download/escaped').status_code, 404)

    def test_download_page_shows_a_zip_button_for_folders(self):
        (self.storage_dir / 'Project').mkdir()

        response = self.client.get('/')
        page = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/download/Project"', page)
        self.assertIn('Download ZIP', page)


if __name__ == '__main__':
    unittest.main()
