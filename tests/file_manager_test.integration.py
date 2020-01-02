#!/usr/local/bin/python3

import os
import unittest
from context import knowledge_base
from shutil import copyfile

dir_path = os.path.dirname(os.path.realpath(__file__))
dir_path = os.path.abspath(os.path.join(dir_path, '../'))
local_folder = os.path.join(dir_path, 'files_test')

wrapper = knowledge_base.GdriveWrapper(dir_path + '/credentials.json',
                                       dir_path + '/token.pickle')
file_manager = knowledge_base.FileManager(wrapper)

class UploadLocalOnlyFiles(unittest.TestCase):
  def setUp(self):
    self.remote_folder_id = wrapper.create_folder('files_test')
    os.makedirs(local_folder, exist_ok=True)

    copyfile(
      os.path.join(dir_path, 'tests/test.txt'),
      os.path.join(local_folder, 'test.txt')
    )

    copyfile(
      os.path.join(dir_path, 'tests/test.png'),
      os.path.join(local_folder, 'test.png')
    )

  def tearDown(self):
    os.remove(os.path.join(local_folder, 'test.txt'))
    os.remove(os.path.join(local_folder, 'test.png'))
    os.rmdir(local_folder)
    wrapper.delete_folder(self.remote_folder_id)

  def test_upload_local_files(self):
    # Assert remote folder is empty.
    files = wrapper.list_files_in_folder(self.remote_folder_id)
    self.assertEqual(0, len(files))

    file_manager.sync(local_folder, self.remote_folder_id)

    # Assert remote folder contains both our files.
    files = wrapper.list_files_in_folder(self.remote_folder_id)
    self.assertEqual(2, len(files))

    filenames = [f for f in files]
    filenames.sort()
    self.assertEqual(['test.png', 'test.txt'], filenames)

class DownloadRemoteOnlyFiles(unittest.TestCase):
  def setUp(self):
    self.remote_folder_id = wrapper.create_folder('files_test')
    os.makedirs(local_folder, exist_ok=True)

  def tearDown(self):
    os.remove(os.path.join(local_folder, 'test.txt'))
    os.remove(os.path.join(local_folder, 'test.png'))
    os.rmdir(local_folder)
    wrapper.delete_folder(self.remote_folder_id)

  def test_download_remote_files(self):


if __name__ == '__main__':
  unittest.main()

