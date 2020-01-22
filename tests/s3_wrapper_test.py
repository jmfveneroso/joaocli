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
folder_id = 'joaocli-test'

class S3WrapperTest(unittest.TestCase):
  def setUp(self):
    self.s3 = file_syncer.S3Wrapper(folder_id)

    # Create local folder.
    os.makedirs(local_folder, exist_ok=True)

    # Create remote folder.
    self.s3.create_folder(folder_id)

  def tearDown(self):
    # Remove local folder.
    for filename in os.listdir(local_folder):
      os.remove(os.path.join(local_folder, filename))
    os.rmdir(local_folder)

    # Remove remote folder.
    self.s3.delete_folder(folder_id)

  def test_upload_download_file(self):
    self.s3.upload_file(
      folder_id, 'test.txt', os.path.join(tests_folder, 'test.txt'))

    self.s3.upload_file(
      folder_id, 'test2.txt', os.path.join(tests_folder, 'test2.txt'))

    files = self.s3.list_files_in_folder(folder_id)
    self.assertEqual(2, len(files))
    self.assertTrue('test.txt' in files)
    self.assertTrue('test2.txt' in files)

    self.s3.download_file(
      folder_id, 'test.txt', os.path.join(local_folder, 'test.txt'))

    with open(os.path.join(tests_folder, 'test.txt'), 'r') as f:
      expected_content = f.read()

    with open(os.path.join(local_folder, 'test.txt'), 'r') as f:
      actual_content = f.read()

    self.assertEqual(expected_content, actual_content)

    self.s3.update_file(
      'test.txt', os.path.join(tests_folder, 'test.txt'), 1579659595)

    f = self.s3.get_file(folder_id, 'test.txt')
    self.assertEqual(1579659595, f['timestamp'])

    self.s3.update_file_timestamp('test.txt', 1579659000)

    f = self.s3.get_file(folder_id, 'test.txt')
    self.assertEqual(1579659000, f['timestamp'])

    fh = self.s3.get_file_in_folder('test.txt', folder_id)
    self.assertTrue(fh) # Not None.
    data = fh.getvalue().decode('utf-8').strip()
    self.assertEqual("This is a test txt file.", data)

    file_id = self.s3.get_file_id('xxx.txt', folder_id)
    self.assertFalse(file_id) # Is None.

    file_id = self.s3.get_file_id('test.txt', folder_id)
    self.assertEqual('test.txt', file_id)

if __name__ == '__main__':
  unittest.main()
