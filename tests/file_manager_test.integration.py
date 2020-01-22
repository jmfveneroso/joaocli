#!/usr/local/bin/python3

import json
import os
import unittest
from context import file_syncer
from datetime import datetime
from shutil import copyfile

dir_path = os.path.dirname(os.path.realpath(__file__))
root = os.path.abspath(os.path.join(dir_path, '../'))
tests_folder = os.path.join(root, 'tests')
local_folder = os.path.join(root, 'files_test')

# storage = file_syncer.GdriveWrapper(
#   root + '/credentials.json',
#   root + '/token.pickle'
# )

storage = file_syncer.S3Wrapper('files_test')

class FileSyncerTest(unittest.TestCase):
  def copy_file_to_local(self, filename, new_filename=None):
    if new_filename is None:
      new_filename = filename
    copyfile(
      os.path.join(tests_folder, filename),
      os.path.join(local_folder, new_filename)
    )

  def copy_file_to_remote(self, filename, new_filename=None):
    if new_filename is None:
      new_filename = filename
    storage.upload_file(
      self.remote_folder_id, new_filename,
      os.path.join(tests_folder, filename)
    )

  def setUp(self):
    # Create local folder.
    os.makedirs(local_folder, exist_ok=True)

    # Create remote folder.
    self.remote_folder_id = storage.create_folder('files_test')
    self.file_syncer = file_syncer.FileSyncer(
      storage, local_folder, self.remote_folder_id
    )

  def tearDown(self):
    # Remove local folder.
    for filename in os.listdir(local_folder):
      os.remove(os.path.join(local_folder, filename))
    os.rmdir(local_folder)

    # Remove remote folder.
    storage.delete_folder(self.remote_folder_id)

  def test_ensure_empty_remote_consistency(self):
    self.copy_file_to_remote("test.txt")
    self.file_syncer.ensure_remote_consistency()

    files = storage.list_files_in_folder(self.remote_folder_id)
    self.assertEqual(0, len(files))

    fh = storage.get_file_in_folder('metadata.json', self.remote_folder_id)
    self.assertTrue(fh) # Not None.
    data = fh.getvalue().decode('utf-8').strip()

    actual = json.loads(data)
    expected = { 'id': 0, 'files': [] }
    actual = json.dumps(actual, indent=2)
    expected = json.dumps(expected, indent=2)
    self.assertEqual(expected, actual)

  def test_ensure_remote_consistency(self):
    self.copy_file_to_remote("test.txt")
    self.copy_file_to_remote("test.png")
    self.copy_file_to_remote("bad_metadata.json", "metadata.json")

    files = storage.list_files_in_folder(self.remote_folder_id)
    self.assertEqual(2, len(files))

    self.file_syncer.ensure_remote_consistency()

    # Metadata.json only lists "test.txt". File "test.png" should have been
    # deleted.
    files = storage.list_files_in_folder(self.remote_folder_id)
    self.assertEqual(1, len(files))

    # Metadata.json lists "test.txt" with timestamp "1234".
    self.assertTrue('test.txt' in files)
    self.assertEqual(1545730073, files['test.txt']['timestamp'])

    fh = storage.get_file_in_folder('metadata.json', self.remote_folder_id)
    self.assertTrue(fh) # Not None.
    data = fh.getvalue().decode('utf-8').strip()

    actual = json.loads(data)
    expected = {
      'id': 1, 'files': [{ 'name': 'test.txt', 'modified_at': 1545730073 }]
    }
    actual = json.dumps(actual, indent=2)
    expected = json.dumps(expected, indent=2)
    self.assertEqual(expected, actual)

  def test_none_none_metadata(self):
    self.copy_file_to_local("test.txt")
    self.file_syncer.sync()

    files = self.file_syncer.get_local_files()
    self.assertEqual(1, len(files))

    local_metadata = None
    with open(os.path.join(local_folder, 'metadata.json'), 'r') as f:
      local_metadata = json.loads(f.read())

    # Assert local metadata.json is as expected.
    self.assertEqual(1, local_metadata['id'])
    self.assertEqual('test.txt', local_metadata['files'][0]['name'])

    # Assert remote metadata.json is as expected.
    fh = storage.get_file_in_folder('metadata.json', self.remote_folder_id)
    self.assertTrue(fh) # Not None.

    local_metadata = json.dumps(local_metadata, indent=2)
    remote_metadata = fh.getvalue().decode('utf-8').strip()
    self.assertEqual(local_metadata, remote_metadata)

    # Assert local test.txt is as expected.
    self.assertTrue(os.path.exists(os.path.join(local_folder, 'test.txt')))

    # Assert remote test.txt is as expected.
    fh = storage.get_file_in_folder('test.txt', self.remote_folder_id)
    self.assertTrue(fh) # Not None.

  def test_no_local_metadata(self):
    self.copy_file_to_remote("test.txt")
    self.copy_file_to_remote("test.png")
    self.copy_file_to_remote("metadata.json")
    self.copy_file_to_local("test2.txt")

    files = self.file_syncer.sync()

    # There should be two local files, since test2.txt is untracked.
    files = self.file_syncer.get_local_files()
    self.assertEqual(2, len(files))
    self.assertTrue('test.txt' in files)
    self.assertTrue('test.png' in files)
    self.assertFalse('test2.txt' in files)

    self.assertEqual(1545730073, files['test.txt']['timestamp'])
    self.assertEqual(1545737000, files['test.png']['timestamp'])

    local_metadata = None
    with open(os.path.join(local_folder, 'metadata.json'), 'r') as f:
      local_metadata = json.loads(f.read())

    # Assert local metadata.json is as expected.
    self.assertEqual(1, int(local_metadata['id']))
    self.assertEqual('test.txt', local_metadata['files'][0]['name'])
    self.assertEqual('test.png', local_metadata['files'][1]['name'])
    self.assertEqual(1545730073, local_metadata['files'][0]['modified_at'])
    self.assertEqual(1545737000, local_metadata['files'][1]['modified_at'])

  def test_no_remote_metadata(self):
    self.copy_file_to_local("test.txt")
    self.copy_file_to_local("test.png")
    self.copy_file_to_local("metadata.json")
    self.copy_file_to_remote("test2.txt")

    files = self.file_syncer.sync()

    # File "test2.txt" should have been deleted.
    files = storage.list_files_in_folder(self.remote_folder_id)
    self.assertEqual(2, len(files))

    # Assert both files exist remotely.
    self.assertTrue('test.txt' in files)
    self.assertTrue('test.png' in files)

    # Assert both files have the correct timestamp.
    local_files = self.file_syncer.get_local_files()
    self.assertEqual(local_files['test.txt']['timestamp'],
                     files['test.txt']['timestamp'])
    self.assertEqual(local_files['test.png']['timestamp'],
                     files['test.png']['timestamp'])

    fh = storage.get_file_in_folder('metadata.json', self.remote_folder_id)
    self.assertTrue(fh) # Not None.
    data = fh.getvalue().decode('utf-8').strip()

    actual = json.loads(data)
    expected = ''
    with open(os.path.join(local_folder, 'metadata.json'), 'r') as f:
      expected = json.loads(f.read())

    actual = json.dumps(actual, indent=2)
    expected = json.dumps(expected, indent=2)
    self.assertEqual(expected, actual)

  def test_local_update(self):
    self.copy_file_to_local("test.txt")
    self.copy_file_to_local("test2.txt")
    self.copy_file_to_local("old_metadata.json", "metadata.json")
    self.copy_file_to_remote("test.txt")
    self.copy_file_to_remote("test.png")
    self.copy_file_to_remote("metadata.json")

    self.file_syncer.sync()

    # File "test2.txt" should have been deleted.
    files = self.file_syncer.get_local_files()
    self.assertEqual(2, len(files))

    # Assert both files exist locally.
    self.assertTrue('test.txt' in files)
    self.assertTrue('test.png' in files)
    self.assertFalse('test2.txt' in files)

    local_files = self.file_syncer.get_local_files()
    self.assertEqual(1545730073, files['test.txt']['timestamp'])
    self.assertEqual(1545737000, files['test.png']['timestamp'])

    fh = storage.get_file_in_folder('metadata.json', self.remote_folder_id)
    self.assertTrue(fh) # Not None.
    data = fh.getvalue().decode('utf-8').strip()
    expected = json.loads(data)
    actual = ''
    with open(os.path.join(local_folder, 'metadata.json'), 'r') as f:
      actual = json.loads(f.read())

    actual = json.dumps(actual, indent=2)
    expected = json.dumps(expected, indent=2)
    self.assertEqual(expected, actual)

  def test_local_untracked_changes(self):
    self.copy_file_to_local("test.txt")
    self.copy_file_to_local("test.png")
    self.copy_file_to_local("test2.txt")
    self.copy_file_to_local("metadata.json")
    self.copy_file_to_remote("test.txt")
    self.copy_file_to_remote("test.png")
    self.copy_file_to_remote("metadata.json")

    self.file_syncer.sync()

    files = self.file_syncer.get_local_files()
    self.assertEqual(3, len(files))

    # Assert both files exist locally.
    self.assertTrue('test.txt' in files)
    self.assertTrue('test.png' in files)
    self.assertTrue('test2.txt' in files)

    fh = storage.get_file_in_folder('metadata.json', self.remote_folder_id)
    self.assertTrue(fh) # Not None.
    data = fh.getvalue().decode('utf-8').strip()
    remote_metadata = json.loads(data)

    self.assertEqual(2, int(remote_metadata['id']))
    self.assertEqual(3, len(remote_metadata['files']))

    local_metadata = ''
    with open(os.path.join(local_folder, 'metadata.json'), 'r') as f:
      local_metadata = json.loads(f.read())

    local_metadata = json.dumps(local_metadata, indent=2)
    remote_metadata = json.dumps(remote_metadata, indent=2)
    self.assertEqual(local_metadata, remote_metadata)

if __name__ == '__main__':
  unittest.main()
