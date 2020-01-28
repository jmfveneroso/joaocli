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
    self.bucket = 'joaodata121442-amplify'
    # self.bucket = 'jmfveneroso'

  def create_folder(self, folder_name):
    f = tempfile.NamedTemporaryFile()
    self.s3.meta.client.upload_file(f.name, self.bucket, folder_name)
    return folder_name

  def list_files_in_folder(self, folder_id):
    response = self.s3.meta.client.list_objects_v2(
      Bucket=self.bucket, Prefix=folder_id)

    files = {}
    if response['KeyCount'] == 0:
      return files

    for f in response['Contents']:
      if f['Key'] == folder_id:
        continue

      name = f['Key'].split('/')[1]
      if name == 'metadata.json' or len(name) == 0:
        continue

      file_id = name
      split_name = name.split('.')
      name = '.'.join(split_name[:-1])
      timestamp = int(split_name[-1])
      # obj = self.get_file(folder_id, name)

      files[name] = { 'id': file_id, 'timestamp': timestamp }
    return files

  def upload_file(self, folder_id, filename, path, timestamp=0):
    if not filename == 'metadata.json':
      filename = '%s.%s' % (filename, str(timestamp))

    self.s3.meta.client.upload_file(
      path, self.bucket, '%s/%s' % (folder_id, filename),
      # ExtraArgs={'Metadata': {'timestamp': str(timestamp) }}
    )

  def download_file(self, folder_id, file_id, path):
    self.s3.meta.client.download_file(
      self.bucket, '%s/%s' % (folder_id, file_id), path)

  def delete_folder(self, folder_id):
    files = self.list_files_in_folder(folder_id)
    for f in files:
      self.s3.meta.client.delete_object(
        Bucket=self.bucket, Key='%s/%s' % (folder_id, f))

    if not self.get_file_id('metadata.json', folder_id) is None:
      self.s3.meta.client.delete_object(
        Bucket=self.bucket, Key="%s/metadata.json" % folder_id)

    self.s3.meta.client.delete_object(
      Bucket=self.bucket, Key="%s/" % folder_id)

  def delete_file(self, file_id):
    self.s3.meta.client.delete_object(
      Bucket=self.bucket, Key="%s/%s" % (self.folder_id, file_id))

  def update_file(self, file_id, path, timestamp):
    filename = file_id
    if filename != 'metadata.json':
      filename = '.'.join(file_id.split('.')[:-1])

    self.delete_file(file_id)
    self.upload_file(self.folder_id, filename, path, timestamp)

  def get_file_timestamp(self, folder_id, file_id):
    split_name = file_id.split('.')
    name = '.'.join(split_name[:-1])
    timestamp = split_name[-1]
    return timestamp

  def get_file_id(self, filename, folder_id):
    prefix = '%s/%s' % (folder_id, filename)
    response = self.s3.meta.client.list_objects_v2(
      Bucket=self.bucket, Prefix=prefix)

    if response['KeyCount'] == 0:
      return None

    # return filename
    return response['Contents'][0]['Key'].split('/')[-1]

  def get_file_in_folder(self, filename, folder_id):
    file_id = self.get_file_id(filename, folder_id)
    if file_id is None:
      return None

    fh = io.BytesIO()
    self.s3.meta.client.download_fileobj(
      self.bucket, '%s/%s' % (folder_id, file_id), fh)
    return fh

  def update_file_timestamp(self, file_id, timestamp):
    split_name = file_id.split('.')
    name = '.'.join(split_name[:-1])
    timestamp= split_name[-1]
    new_file_id = name + '.' + str(timestamp)

    self.s3.meta.client.copy_object(
      Bucket=self.bucket, Key='%s/%s' % (self.folder_id, new_file_id), 
      CopySource={
        'Bucket': self.bucket, 'Key': '%s/%s' % (self.folder_id, file_id)},
      # Metadata={ 'timestamp': str(timestamp) },
      MetadataDirective='REPLACE')
