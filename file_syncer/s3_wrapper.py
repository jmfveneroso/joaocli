#!/usr/local/bin/python3

import argparse
import boto3
from datetime import datetime, timezone
import io
import json
import os
import pickle
import subprocess
import tempfile
import yaml
import os.path
from dateutil.tz import *

class S3Wrapper():
  def __init__(self, folder_id):
    self.s3 = boto3.resource('s3')
    self.folder_id = folder_id

  def create_folder(self, folder_name):
    f = tempfile.NamedTemporaryFile()
    self.s3.meta.client.upload_file(f.name, 'jmfveneroso', folder_name)
    return folder_name

  def list_files_in_folder(self, folder_id):
    response = self.s3.meta.client.list_objects_v2(
      Bucket='jmfveneroso', Prefix=folder_id)

    files = {}
    if response['KeyCount'] == 0:
      return files

    for f in response['Contents']:
      if f['Key'] == folder_id:
        continue

      name = f['Key'].split('/')[1]
      if name == 'metadata.json' or len(name) == 0:
        continue

      obj = self.get_file(folder_id, name)
      files[name] = { 'id': obj['name'], 'timestamp': obj['timestamp'] }
    return files

  def upload_file(self, folder_id, filename, path, timestamp=0):
    self.s3.meta.client.upload_file(
      path, 'jmfveneroso', '%s/%s' % (folder_id, filename),
      ExtraArgs={'Metadata': {'timestamp': str(timestamp) }}
    )

  def download_file(self, folder_id, file_id, path):
    self.s3.meta.client.download_file(
      'jmfveneroso', '%s/%s' % (folder_id, file_id), path)

  def delete_folder(self, folder_id):
    files = self.list_files_in_folder(folder_id)
    for f in files:
      self.s3.meta.client.delete_object(
        Bucket='jmfveneroso', Key='%s/%s' % (folder_id, f))

    if not self.get_file_id('metadata.json', folder_id) is None:
      self.s3.meta.client.delete_object(
        Bucket='jmfveneroso', Key="%s/metadata.json" % folder_id)

    self.s3.meta.client.delete_object(
      Bucket='jmfveneroso', Key="%s/" % folder_id)

  def delete_file(self, file_id):
    self.s3.meta.client.delete_object(
      Bucket='jmfveneroso', Key="%s/%s" % (self.folder_id, file_id))

  def update_file(self, filename, path, timestamp):
    self.upload_file(self.folder_id, filename, path, timestamp)

  def get_file(self, folder_id, file_id):
    name = '%s/%s' % (folder_id, file_id)
    obj = self.s3.meta.client.get_object(
      Bucket='jmfveneroso', Key=name)

    timestamp = obj['Metadata']['timestamp']
    return { 'name': file_id, 'timestamp': int(timestamp) }

  def get_file_timestamp(self, folder_id, file_id):
    return get_file(folder_id, file_id)['timestamp']

  def get_file_id(self, filename, folder_id):
    prefix = '%s/%s' % (folder_id, filename)
    response = self.s3.meta.client.list_objects_v2(
      Bucket='jmfveneroso', Prefix=prefix)

    if response['KeyCount'] == 0:
      return None

    return filename

  def get_file_in_folder(self, file_id, folder_id):
    if self.get_file_id(file_id, folder_id) is None:
      return None

    fh = io.BytesIO()
    self.s3.meta.client.download_fileobj(
      'jmfveneroso', '%s/%s' % (folder_id, file_id), fh)
    return fh

  def update_file_timestamp(self, file_id, timestamp):
    self.s3.meta.client.copy_object(
      Bucket='jmfveneroso', Key='%s/%s' % (self.folder_id, file_id), 
      CopySource={
        'Bucket': 'jmfveneroso', 'Key': '%s/%s' % (self.folder_id, file_id)},
      Metadata={ 'timestamp': str(timestamp) },
      MetadataDirective='REPLACE')
