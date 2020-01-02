#!/usr/local/bin/python3

import json
import os
from datetime import datetime

class FileManager():
  def __init__(self, gdrive_wrapper):
    self.gdrive = gdrive_wrapper

  def get_local_files(self, path):
    files = {}
    for filename in os.listdir(path):
      if filename.endswith('.swp') or filename.startswith('.'):
        continue
      timestamp = os.stat("%s/%s" % (path, filename))[8]
      files[filename] = { 'timestamp': timestamp }
    return files

  def get_local_metadata(self, dir_path):
    if not os.path.isfile('metadata.json'):
      data = { 'id': 0 }
      with open(os.path.join(dir_path, 'metadata.json'), 'w') as f:
        f.write(json.dumps(data, indent=2))

    with open(os.path.join(dir_path, 'metadata.json'), 'r') as f:
      data = json.loads(f.read())
      return data

  def get_remote_metadata(self, remote_folder_id):
    metadata_file_id = '1d-uAQdrScoDjD1KKQrQj_K9_kdjrXQmy'
    fh = self.gdrive.download_file(metadata_file_id)
    data = fh.getvalue().decode('utf-8').strip()
    return json.loads(data)

  def update_local(self, update_local):

  def update_remote(self, update_local):

  def sync(self, local_path, remote_folder_id):
    local_data = self.get_local_metadata(local_path)
    remote_data = self.get_remote_metadata(remote_folder_id)

    # if no metadata locally and no metadata remotely
    #   create metadata locally and upload
    #
    # if no metadata locally and metadata remotely
    #   download from remote
    #
    # if no metadata remote and metadata locally
    #   upload all to remote

    # if local_data['id'] < remote_data['id']:
    #   Update local data, discarding local changes.

    # if local_data['id'] == remote_data['id']:
    #   If any timestamps have changed.
    #     - Update local metadata.
    #     - Increase version.

    # if local_data['id'] > remote_data['id']:
    #   Update remote data, discarding remote changes.

    # When updating.
    #   for each file
    #     if file does not exist in metadata, delete it
    #     if file exists in metadata, download it
    #     if it has smaller timestamp, download file
    #     if it has larger timestamp, correct timestamp (error)

    print(local_id)
    print(remote_id)
    print(local_data)
    print(remote_data)
    return



    remote_files = self.gdrive.list_files_in_folder(remote_folder_id)
    local_files = self.get_local_files(local_path)

    remote_only, local_only, conflicting = [], [], []
    for f in remote_files:
      if f in local_files:
        conflicting.append(f)
      else:
        remote_only.append(f)

    for f in local_files:
      if not f in remote_files:
        local_only.append(f)

    print('Downloading remote only files.')
    for f in remote_only:
      file_id = remote_files[f]
      # self.gdrive.download_file(file_id, local_path)
      # with open(dir_path + "/files/" + filename, "wb") as f:
      #   f.write(file_buffer)
      print('Downloaded %s' % f)

    print('Uploading local only files.')
    for f in local_only:
      self.gdrive.upload_file(
        remote_folder_id,
        f,
        os.path.join(local_path, f),
      )
      ts = datetime.now().timestamp()
      os.utime(os.path.join(local_path, f), (ts, ts))
      print('Uploaded %s' % f)

    print('Resolving conflicts.')
    for f in conflicting:
      local_timestamp = local_files[f]['timestamp']
      remote_timestamp = remote_files[f]['timestamp']

      # Same file.
      if abs(remote_timestamp - local_timestamp) < 100:
        continue

      file_id = remote_files[f]
      msg = 'Download' if remote_timestamp > local_timestamp else 'Upload'
      msg = "%s file '%s'? (y/n)\n" % (msg, f)
      if not input(msg) == 'y':
        continue

      # Download file.
      if remote_timestamp > local_timestamp:
        # self.gdrive.download_file(file_id, local_path)
        print('Downloaded %s' % f)

      # Upload file.
      else:
        # self.gdrive.update_file(file_id, path + '/' + f)
        ts = datetime.now().timestamp()
        os.utime(dir_path + "/files/" + filename, (ts, ts))
        print('Uploaded %s' % f)
