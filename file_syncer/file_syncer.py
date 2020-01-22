#!/usr/local/bin/python3

import json
import os
import tempfile
from datetime import datetime

class FileSyncer():
  def __init__(self, storage, dir_path, remote_folder_id):
    self.storage = storage
    self.dir_path = dir_path
    self.remote_folder_id = remote_folder_id

  def get_local_files(self):
    files = {}
    for filename in os.listdir(self.dir_path):
      if filename.endswith('.swp') or filename.startswith('.') or filename == 'metadata.json':
        continue
      timestamp = os.stat(os.path.join(self.dir_path, filename))[8]
      files[filename] = { 'timestamp': timestamp }
    return files

  def get_local_metadata(self):
    if not os.path.isfile(os.path.join(self.dir_path, 'metadata.json')):
      return None

    with open(os.path.join(self.dir_path, 'metadata.json'), 'r') as f:
      return json.loads(f.read())

  def get_remote_metadata(self):
    fh = self.storage.get_file_in_folder('metadata.json', self.remote_folder_id)
    if fh is None:
      return None
    data = fh.getvalue().decode('utf-8').strip()
    return json.loads(data)

  def ensure_remote_consistency(self):
    remote_metadata = self.get_remote_metadata()
    files = self.storage.list_files_in_folder(self.remote_folder_id)

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
      self.storage.delete_file(files[filename]['id'])
      del files[filename]
      update_metadata = True

    valid_files = { f for f in files if f in metadata_files }
    for filename in valid_files:
      # Set file timestamps according to what is in the metadata.
      timestamp = files[filename]['timestamp']
      metadata_timestamp = metadata_files[filename]['timestamp']
      if timestamp != metadata_timestamp:
        self.storage.update_file_timestamp(
          files[filename]['id'], metadata_timestamp)

    if not update_metadata:
      return

    files = self.storage.list_files_in_folder(self.remote_folder_id)
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

    file_id = self.storage.get_file_id('metadata.json', self.remote_folder_id)
    if file_id is None:
      self.storage.upload_file(self.remote_folder_id, 'metadata.json', temp.name)
    else:
      self.storage.update_file(file_id, temp.name, 0)
    temp.close()

  def update_local_metadata(self):
    local_metadata = self.get_local_metadata()

    local_metadata_id = 0
    if not local_metadata is None:
      local_metadata_id = local_metadata['id']

    update_metadata = False
    files = self.get_local_files()
    if local_metadata is None:
      update_metadata = True
    else:
      metadata_files = { f['name']: f['modified_at'] for f in local_metadata['files'] }
      if len(metadata_files) != len(files):
        update_metadata = True
      else:
        for filename in files:
          timestamp = int(files[filename]['timestamp'])
          if not filename in metadata_files:
            update_metadata = True
            break

          if metadata_files[filename] != timestamp:
            update_metadata = True
            break

    if update_metadata:
      new_metadata = { 'id': int(local_metadata_id), 'files': [] }
      files = self.get_local_files()
      for filename in files:
        timestamp = int(files[filename]['timestamp'])
        new_metadata['files'].append({
          'name': filename,
          'modified_at': timestamp
        })

      new_metadata['id'] += 1
      with open(os.path.join(self.dir_path, 'metadata.json'), 'w') as f:
        f.write(json.dumps(new_metadata, indent=2))

    return self.get_local_metadata()

  def sync_local_based_on_remote(self):
    remote_metadata = self.get_remote_metadata()
    if remote_metadata is None:
      return # Error

    update_metadata = False
    local_metadata = self.get_local_metadata()
    for f in remote_metadata['files']:
      filename = f['name']
      timestamp = f['modified_at']

      download_file = False
      if local_metadata is None:
        download_file = True
      elif not f['name'] in local_metadata['files']:
        download_file = True
      else:
        local_file = local_metadata['files'][filename]
        if local_file['modified_at'] != f['modified_at']:
          download_file = True

      if download_file:
        update_metadata = True
        fh = self.storage.get_file_in_folder(f['name'], self.remote_folder_id)
        if fh is None:
          return None # Error

        with open(os.path.join(self.dir_path, filename), "wb") as f:
          f.write(fh.getbuffer())
        os.utime(os.path.join(self.dir_path, filename), (timestamp, timestamp))

    remote_files = {f['name'] for f in remote_metadata['files']}
    local_files = self.get_local_files()
    for f in local_files:
      if not f in remote_files:
        os.remove(os.path.join(self.dir_path, f))

    fh = self.storage.get_file_in_folder('metadata.json', self.remote_folder_id)
    with open(os.path.join(self.dir_path, 'metadata.json'), "wb") as f:
      f.write(fh.getbuffer())

  def sync_remote_based_on_local(self):
    local_metadata = self.update_local_metadata()
    remote_files = self.storage.list_files_in_folder(self.remote_folder_id)

    for f in local_metadata['files']:
      filename = f['name']
      if filename in remote_files:
        if remote_files[filename]['timestamp'] == f['modified_at']:
          continue
        self.storage.update_file(
          remote_files[filename]['id'], os.path.join(self.dir_path, filename),
          f['modified_at']
        )
      else:
        self.storage.upload_file(
          self.remote_folder_id, filename,
          os.path.join(self.dir_path, filename), f['modified_at']
        )

    local_files = {f['name'] for f in local_metadata['files']}
    for f in remote_files:
      if f in local_files:
        continue
      self.storage.delete_file(remote_files[f]['id'])

    file_id = self.storage.get_file_id('metadata.json', self.remote_folder_id)
    if file_id is None:
      self.storage.upload_file(
        self.remote_folder_id, 'metadata.json',
        os.path.join(self.dir_path, 'metadata.json')
      )
    else:
      self.storage.update_file(
        file_id, os.path.join(self.dir_path, 'metadata.json'), 0
      )

  def sync(self):
    self.ensure_remote_consistency()
    local_metadata = self.get_local_metadata()
    remote_metadata = self.get_remote_metadata()

    if local_metadata is None and remote_metadata is None:
      return self.sync_remote_based_on_local()

    if local_metadata is None:
      # Remove all local untracked files.
      for filename in os.listdir(self.dir_path):
        os.remove(os.path.join(self.dir_path, filename))
      return self.sync_local_based_on_remote()

    if remote_metadata is None:
      return self.sync_remote_based_on_local()

    local_id = int(local_metadata['id'])
    remote_id = int(remote_metadata['id'])

    # Update remote.
    if local_id > remote_id:
      return self.sync_remote_based_on_local()

    # Update local.
    if local_id < remote_id:
      return self.sync_local_based_on_remote()

    local_metadata = self.update_local_metadata()
    if local_metadata['id'] > local_id:
      self.sync_remote_based_on_local()
