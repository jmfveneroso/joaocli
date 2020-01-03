#!/usr/local/bin/python3

import json
import os
import unittest
from context import knowledge_base
from datetime import datetime
from shutil import copyfile

dir_path = os.path.dirname(os.path.realpath(__file__))
root = os.path.abspath(os.path.join(dir_path, '../'))
tests_folder = os.path.join(root, 'tests')
local_folder = os.path.join(root, 'files_test')

gdrive = knowledge_base.GdriveWrapper(root + '/credentials.json', 
                                           root + '/token.pickle')
class FileSyncerTest(unittest.TestCase):
  def copy_file_to_local(self, filename):
    copyfile(
      os.path.join(tests_folder, filename),
      os.path.join(local_folder, filename)
    )

  def copy_file_to_remote(self, filename):
    os.path.join(tests_folder, filename),
    gdrive.upload_file(
      self.remote_folder_id, filename, 
      os.path.join(tests_folder, filename)
    )

  def setUp(self):
    # Create local folder.
    os.makedirs(local_folder, exist_ok=True)

    # Create remote folder.
    self.remote_folder_id = gdrive.create_folder('files_test')
    self.file_syncer = knowledge_base.FileSyncer(
      gdrive, local_folder, self.remote_folder_id
    )

  def tearDown(self):
    # Remove local folder.
    for filename in os.listdir(local_folder):
      os.remove(os.path.join(local_folder, filename))
    os.rmdir(local_folder)

    # Remove remote folder.
    gdrive.delete_folder(self.remote_folder_id)

  def test_ensure_remote_consistency(self):
    self.copy_file_to_remote("test.txt")
    self.copy_file_to_remote("test.png")
    self.copy_file_to_remote("metadata.json")
    
    files = gdrive.list_files_in_folder(self.remote_folder_id)
    self.assertEqual(2, len(files))

    self.file_syncer.ensure_remote_consistency()

    # Metadata.json only lists "test.txt". File "test.png" should have been
    # deleted.
    files = gdrive.list_files_in_folder(self.remote_folder_id)
    self.assertEqual(1, len(files))

    # Metadata.json lists "test.txt" with timestamp "1234".
    self.assertTrue('test.txt' in files) 
    diff = int(files['test.txt']['timestamp'])
    self.assertEqual(1545730073, files['test.txt']['timestamp']) 
 
    fh = gdrive.get_file_in_folder('metadata.json', self.remote_folder_id)
    self.assertTrue(fh) # Not None.
    data = fh.getvalue().decode('utf-8').strip()

    actual = json.loads(data)
    expected = { 
      'id': 1, 'files': [{ 'name': 'test.txt', 'modified_at': 1545730073 }]
    }
    actual = json.dumps(actual, indent=2)
    expected = json.dumps(expected, indent=2)
    self.assertEqual(expected, actual) 

  def test_null_null_metadata(self):
    self.copy_file_to_local("test.txt")
    self.file_syncer.sync()

    files = self.file_syncer.get_local_files()
    self.assertEqual(1, len(files))

    local_metadata = None
    with open(os.path.join(local_folder, 'metadata.json'), 'r') as f:
      local_metadata = json.loads(f.read())

    # Assert local metadata.json is as expected.
    self.assertEqual(0, local_metadata['id'])
    self.assertEqual('test.txt', local_metadata['files'][0]['name'])

    # Assert remote metadata.json is as expected.
    fh = gdrive.get_file_in_folder('metadata.json', self.remote_folder_id)
    self.assertTrue(fh) # Not None.

    local_metadata = json.dumps(local_metadata, indent=2)
    remote_metadata = fh.getvalue().decode('utf-8').strip()
    self.assertEqual(local_metadata, remote_metadata)

    # Assert local test.txt is as expected.
    self.assertTrue(os.path.exists(os.path.join(local_folder, 'test.txt')))

    # Assert remote test.txt is as expected.
    fh = gdrive.get_file_in_folder('test.txt', self.remote_folder_id)
    self.assertTrue(fh) # Not None.

if __name__ == '__main__':
  # local_folder = os.path.join(dir_path, 'files')
  # file_manager.generate_metadata(local_folder)
  unittest.main()

