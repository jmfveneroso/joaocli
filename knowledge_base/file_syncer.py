#!/usr/local/bin/python3

import json
import os
import tempfile
from datetime import datetime

class FileSyncer():
  def __init__(self, gdrive_wrapper, dir_path, remote_folder_id):
    self.gdrive = gdrive_wrapper
    self.dir_path = dir_path
    self.remote_folder_id = remote_folder_id

  def get_local_metadata(self):
    if not os.path.isfile(os.path.join(self.dir_path, 'metadata.json')):
      return None

    with open(os.path.join(self.dir_path, 'metadata.json'), 'r') as f:
      return json.loads(f.read())

  def get_remote_metadata(self):
    fh = self.gdrive.get_file_in_folder('metadata.json', self.remote_folder_id)
    if fh is None:
      return None
    data = fh.getvalue().decode('utf-8').strip()
    return json.loads(data)

  def ensure_remote_consistency(self):
    remote_metadata = self.get_remote_metadata()
    files = self.gdrive.list_files_in_folder(self.remote_folder_id)

    metadata_files = {}
    if not remote_metadata is None:
      for f in remote_metadata['files']:
        metadata_files[f['name']] = { 
          'timestamp': f['modified_at']
        }

    update_metadata = False

    # Discard files that are not listed in the metadata.
    unidentified_files = { f for f in files if not f in metadata_files }
    for filename in unidentified_files:
      self.gdrive.delete_file(files[filename]['id'])
      del files[filename]
      update_metadata = True

    valid_files = { f for f in files if f in metadata_files }
    for filename in valid_files:
      # Set file timestamps according to what is in the metadata.
      timestamp = files[filename]['timestamp']
      metadata_timestamp = metadata_files[filename]['timestamp']
      if timestamp != metadata_timestamp:
        self.gdrive.update_file_timestamp(
          files[filename]['id'], metadata_timestamp)

    if not update_metadata:
      return

    files = self.gdrive.list_files_in_folder(self.remote_folder_id)
    remote_metadata_id = 0
    if not remote_metadata is None:
      remote_metadata_id = remote_metadata['id']

    new_metadata = { 'id': int(remote_metadata_id), 'files': [] }
    for filename in files:
      new_metadata['files'].append({
        'name': filename,
        'modified_at': int(files[filename]['timestamp'])
      })

    data = json.dumps(new_metadata, indent=2)
    temp = tempfile.NamedTemporaryFile()
    temp.write(bytes(data, 'utf-8'))
    temp.seek(0)

    file_id = self.gdrive.get_file_id('metadata.json', self.remote_folder_id)
    if file_id is None:
      self.gdrive.upload_file(self.remote_folder_id, 'metadata.json', temp.name)
    else:
      self.gdrive.update_file(file_id, temp.name, 0)
    temp.close()

  def get_local_files(self):
    files = {}
    for filename in os.listdir(self.dir_path):
      if filename.endswith('.swp') or filename.startswith('.') or filename == 'metadata.json':
        continue
      timestamp = os.stat(os.path.join(self.dir_path, filename))[8]
      files[filename] = { 'timestamp': timestamp }
    return files

  def update_local_metadata(self):
    local_metadata = self.get_local_metadata()

    local_metadata_id = 0
    if not local_metadata is None:
      local_metadata_id = local_metadata['id']

    new_metadata = { 'id': int(local_metadata_id), 'files': [] }
    files = self.get_local_files()
    for filename in files:
      new_metadata['files'].append({
        'name': filename,
        'modified_at': int(files[filename]['timestamp'])
      })

    with open(os.path.join(self.dir_path, 'metadata.json'), 'w') as f:
      f.write(json.dumps(new_metadata, indent=2))
    return self.get_local_metadata()

  def sync_local_based_on_remote(self):
    return 0

  def sync_remote_based_on_local(self):
    local_metadata = self.update_local_metadata()
    remote_files = self.gdrive.list_files_in_folder(self.remote_folder_id)

    for f in local_metadata['files']:
      filename = f['name']
      if filename in remote_files:
        if remote_files[filename]['modified_at'] == f['timestamp']:
          continue
        self.gdrive.update_file(
          remote_files[filename]['id'], os.path.join(self.dir_path, filename), 
          f['timestamp']
        )
      else:
        self.gdrive.upload_file(
          self.remote_folder_id, filename, os.path.join(self.dir_path, filename)
        )

    local_files = {f['name'] for f in local_metadata['files']}
    for f in remote_files:
      if remote_files[f]['name'] in local_files:
        continue

      self.gdrive.delete_file(remote_files[f]['id'])

    file_id = self.gdrive.get_file_id('metadata.json', self.remote_folder_id)
    if file_id is None:
      self.gdrive.upload_file(
        self.remote_folder_id, 'metadata.json', 
        os.path.join(self.dir_path, 'metadata.json')
      )
      return 0

    self.gdrive.update_file(
      file_id, os.path.join(self.path_dir, 'metadata.json'), 0
    )
    return 0

  def sync(self):
    self.ensure_remote_consistency()
    local_metadata = self.get_local_metadata()
    remote_metadata = self.get_remote_metadata()

    if local_metadata is None and remote_metadata is None:
      return self.sync_remote_based_on_local()
    return

    if local_metadata is None:
      return self.sync_local_based_on_remote()

    if remote_metadata is None:
      return self.sync_remote_based_on_local()

    local_id = local_metadata['id']
    remote_id = remote_metadata['id']
    if local_id < remote_id:
      return self.sync_local_based_on_remote()

    if local_id > remote_id:
      return self.sync_remote_based_on_local()

    local_metadata = self.update_local_metadata()
    if local_metadata['id'] > local_id:
      self.sync_remote_based_on_local()

    return 0
