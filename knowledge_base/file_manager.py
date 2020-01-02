#!/usr/local/bin/python3

import json
import os
from datetime import datetime

class FileManager():
  def __init__(self, gdrive_wrapper):
    self.gdrive = gdrive_wrapper

  def get_local_metadata(self, dir_path):
    if not os.path.isfile(os.path.join(dir_path, 'metadata.json')):
      return None

    with open(os.path.join(dir_path, 'metadata.json'), 'r') as f:
      return json.loads(f.read())

  def get_remote_metadata(self, remote_folder_id):
    fh = self.gdrive.get_file_in_folder('metadata.json', remote_folder_id)
    data = fh.getvalue().decode('utf-8').strip()
    return json.loads(data)

  def sync_local_based_on_remote(self):
    pass

  def sync_remote_based_on_local(self):
    pass

  def sync(self, local_path, remote_folder_id):
    local_metadata = self.get_local_metadata(local_path)
    remote_metadata = self.get_remote_metadata(remote_folder_id)
    print(local_data)
    print(remote_data)

    if local_metadata is None and remote_metadata is None:
      pass
      # Create metadata locally and upload everything.

    if local_metadata is None:
      pass
      # Sync local based on remote.

    if remote_metadata is None:
      pass
      # Sync remote based on local.

    if local_metadata['id'] < remote_metadata['id']:
      pass
      # Sync local based on remote.

    if local_metadata['id'] > remote_metadata['id']:
      pass
      # Sync remote based on local.

    if local_metadata['id'] == remote_metadata['id']:
      pass
      # Update local metadata. 
      # If version changed. Sync remote based on local.

    # When updating.
    #   for each file
    #     if file does not exist in metadata, delete it
    #     if file exists in metadata, download it
    #     if it has smaller timestamp, download file
    #     if it has larger timestamp, correct timestamp (error)

    return

    print(local_id)
    print(remote_id)
    print(local_data)
    print(remote_data)
    return

    # data = { 'id': 0 }
    # with open(os.path.join(dir_path, 'metadata.json'), 'w') as f:
    #   f.write(json.dumps(data, indent=2))


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

  def get_local_files(self, path):
    files = {}
    for filename in os.listdir(path):
      if filename.endswith('.swp') or filename.startswith('.'):
        continue
      timestamp = os.stat("%s/%s" % (path, filename))[8]
      files[filename] = { 'timestamp': timestamp }
    return files
