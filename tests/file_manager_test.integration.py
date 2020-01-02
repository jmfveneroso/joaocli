#!/usr/local/bin/python3

import os
import unittest
from context import knowledge_base
from shutil import copyfile

remote_folder_id = '1fHGO82QmZAEsKIO5kMnFXYGmOi8fyIFI'
dir_path = os.path.dirname(os.path.realpath(__file__))
dir_path = os.path.abspath(os.path.join(dir_path, '../'))

wrapper = knowledge_base.GdriveWrapper(dir_path + '/credentials.json',
                                       dir_path + '/token.pickle')
file_manager = knowledge_base.FileManager(wrapper)

class AdvancedTestSuite(unittest.TestCase):
  def setUp(self):
    # Create files_test folder.
    local_folder = os.path.join(dir_path, 'files_test')
    os.makedirs(local_folder, exist_ok=True)

  def tearDown(self):
    local_folder = os.path.join(dir_path, 'files_test')
    os.rmdir(local_folder)

  def test_upload_local_files(self):
    # Assert remote folder is empty.
    files = wrapper.list_files_in_folder(remote_folder_id)
    self.assertEqual(0, len(files))


    # Copy our test files.
    copyfile(
      os.path.join(dir_path, 'tests/test.txt'),
      os.path.join(local_folder, 'test.txt')
    )

    copyfile(
      os.path.join(dir_path, 'tests/test.png'),
      os.path.join(local_folder, 'test.png')
    )

    file_manager.sync(local_folder, remote_folder_id)

    files = wrapper.list_files_in_folder(remote_folder_id)
    self.assertEqual(2, len(files))

if __name__ == '__main__':
  unittest.main()

