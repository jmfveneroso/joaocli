#!/usr/local/bin/python3

import json
import logging
import logging.config
import os
import sys
import tempfile
from datetime import datetime
from dateutil.tz import *

logging.config.fileConfig(os.path.abspath(os.path.join(os.path.dirname(__file__), '../logging.conf')))
logger = logging.getLogger('joaocli_default')

def pretty_date(timestamp):
  d = datetime.fromtimestamp(timestamp)
  return d.strftime('%Y-%m-%d %H:%M:%S')

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

  def ensure_remote_consistency(self, dry_run=False):
    logger.info('Ensuring remote metadata.json consistency')
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
      logger.info(
        'Deleted file %s from remote. Reason: '
        'not listed in metadata.json' % filename)

    valid_files = { f for f in files if f in metadata_files }
    for filename in valid_files:
      # Set file timestamps according to what is in the metadata.
      timestamp = files[filename]['timestamp']
      metadata_timestamp = metadata_files[filename]['timestamp']
      if timestamp != metadata_timestamp:
        self.storage.update_file_timestamp(
          files[filename]['id'], metadata_timestamp)
        logger.info(
          'Changed file %s timestamp. Reason:'
          'inconsistent with metadata.json.'
          'Previous timestamp: %s, New timestamp: %s' % (
              filename, pretty_date(timestamp), pretty_date(metadata_timestamp)
          ))

    if not update_metadata:
      logger.info('Remote metadata.json is already consistent')
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
    logger.info('Remote metadata.json is inconsistent.\n'
                'Writing metadata.json:\n%s' % data)
    temp.close()

  def update_local_metadata(self, dry_run=False):
    local_metadata = self.get_local_metadata()

    local_metadata_id = 0
    if not local_metadata is None:
      local_metadata_id = local_metadata['id']

    metadata_files = None
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

        for filename in metadata_files:
          if not filename in files:
            update_metadata = True
            break

    if update_metadata:
      logger.info('There are untracked changes on the local folder')
      new_metadata = { 'id': int(local_metadata_id), 'files': [] }
      files = self.get_local_files()
      for filename in files:
        timestamp = int(files[filename]['timestamp'])
        new_metadata['files'].append({
          'name': filename,
          'modified_at': timestamp
        })

        if (local_metadata is None or not filename in metadata_files):
          logger.info('Adding %s %s' % (filename, pretty_date(timestamp)))
        elif timestamp != metadata_files[filename]:
          logger.info('Changing %s from %s to %s' % (
            filename, pretty_date(metadata_files[filename]),
            pretty_date(timestamp)))

      for filename in metadata_files:
        if not filename in files:
          logger.info('Deleting %s %s' % (
            filename, pretty_date(metadata_files[filename])))

      new_metadata['id'] += 1

      if not dry_run:
        with open(os.path.join(self.dir_path, 'metadata.json'), 'w') as f:
          f.write(json.dumps(new_metadata, indent=2))
    else:
      logger.info('Local metadata.json is up to date')

    return self.get_local_metadata()

  def sync_local_based_on_remote(self, dry_run=False):
    logger.info('Syncing local based on remote')
    remote_metadata = self.get_remote_metadata()
    if remote_metadata is None:
      return # Error

    local_files = {}
    local_metadata = self.get_local_metadata()
    if not local_metadata is None:
      local_files = {f['name']: f['modified_at'] for f in local_metadata['files']}

    for f in remote_metadata['files']:
      filename = f['name']
      timestamp = f['modified_at']

      download_file = False
      if local_metadata is None:
        download_file = True
        logger.info('Remote file %s does not exist locally' % filename)
      elif not f['name'] in local_files:
        download_file = True
        logger.info('Remote file %s does not exist locally' % filename)
      else:
        local_timestamp = local_files[filename]
        if local_timestamp != f['modified_at']:
          download_file = True
        logger.info('File %s has local timestamp %s and remote timestamp %s' % (
          filename,
          pretty_date(local_timestamp),
          pretty_date(f['modified_at'])))

      if download_file:
        fh = self.storage.get_file_in_folder(f['name'], self.remote_folder_id)
        if fh is None:
          return None # Error

        if not dry_run:
          with open(os.path.join(self.dir_path, filename), "wb") as f:
            f.write(fh.getbuffer())
          os.utime(os.path.join(self.dir_path, filename), (timestamp, timestamp))
          logger.info('Downloading file %s %s' % (
            filename, pretty_date(timestamp)))

    remote_files = {f['name'] for f in remote_metadata['files']}
    local_files = self.get_local_files()
    for f in local_files:
      if not f in remote_files:
        if not dry_run:
          os.remove(os.path.join(self.dir_path, f))
        logger.info(
          'Deleting file %s. Local file does not exist on remote' % f)

    if not dry_run:
      fh = self.storage.get_file_in_folder('metadata.json', self.remote_folder_id)
      with open(os.path.join(self.dir_path, 'metadata.json'), "wb") as f:
        f.write(fh.getbuffer())
    logger.info('Updating local metadata.json')

  def sync_remote_based_on_local(self, dry_run=False):
    logger.info('Syncing remote based on local')
    local_metadata = self.update_local_metadata(dry_run)
    remote_files = self.storage.list_files_in_folder(self.remote_folder_id)

    for f in local_metadata['files']:
      filename = f['name']
      if filename in remote_files:
        if remote_files[filename]['timestamp'] == f['modified_at']:
          continue
        if not dry_run:
          self.storage.update_file(
            remote_files[filename]['id'], os.path.join(self.dir_path, filename),
            f['modified_at']
          )
          logger.info('Updated file %s. From %s to %s' % (
          filename, pretty_date(remote_files[filename]['timestamp']),
          pretty_date(f['modified_at'])))
      else:
        if not dry_run:
          self.storage.upload_file(
            self.remote_folder_id, filename,
            os.path.join(self.dir_path, filename), f['modified_at']
          )
        logger.info('Uploaded to remote: %s %s' % (
          filename, pretty_date(f['modified_at'])))

    local_files = {f['name'] for f in local_metadata['files']}
    for f in remote_files:
      if f in local_files:
        continue
      if not dry_run:
        self.storage.delete_file(remote_files[f]['id'])
      logger.info('Deleted file from remote: %s' % f)

    file_id = self.storage.get_file_id('metadata.json', self.remote_folder_id)
    if file_id is None:
      if not dry_run:
        self.storage.upload_file(
          self.remote_folder_id, 'metadata.json',
          os.path.join(self.dir_path, 'metadata.json')
        )
      logger.info('Uploaded remote metadata.json.')
    else:
      if not dry_run:
        self.storage.update_file(
          file_id, os.path.join(self.dir_path, 'metadata.json'), 0
        )
      logger.info('Updated remote metadata.json.')

  def sync(self, dry_run=True, verbose=False):
    global logger
    # verbose = verbose or dry_run
    verbose = True
    if verbose or dry_run:
      logger = logging.getLogger('joaocli_verbose')

    logger.info(
      'Syncing local %s and remote %s' %
      (self.dir_path, self.remote_folder_id))

    if dry_run:
      logger.info('Dry run')

    # self.ensure_remote_consistency(dry_run)
    local_metadata = self.get_local_metadata()
    remote_metadata = self.get_remote_metadata()

    if local_metadata is None and remote_metadata is None:
      logger.info('Local and remote folders are empty')
      return self.sync_remote_based_on_local(dry_run)

    if local_metadata is None:
      logger.info('Missing local metadata.json. Removing untracked local files')

      # Remove all local untracked files.
      for filename in os.listdir(self.dir_path):
        os.remove(os.path.join(self.dir_path, filename))
        logger.info('Removed local file %s' % filename)
      return self.sync_local_based_on_remote(dry_run)

    # Remote is empty but local has a metadata file.
    if remote_metadata is None:
      logger.info('Missing remote metadata.json')
      return self.sync_remote_based_on_local(dry_run)

    local_id = int(local_metadata['id'])
    remote_id = int(remote_metadata['id'])

    # Update remote.
    if local_id > remote_id:
      logger.info(
        'Local metadata id (%d) is more recent than remote id (%d)' % (
        local_id, remote_id))
      return self.sync_remote_based_on_local(dry_run)

    # Update local.
    if local_id < remote_id:
      logger.info(
        'Remote metadata id (%d) is more recent than local id (%d)' % (
        remote_id, local_id))
      return self.sync_local_based_on_remote(dry_run)

    local_metadata = self.update_local_metadata(dry_run)
    if int(local_metadata['id']) > local_id:
      logger.info('Pushing untracked changes to remote')
      self.sync_remote_based_on_local(dry_run)
