#!/usr/local/bin/python3

import argparse
from datetime import datetime
import io
import json
import os
import pickle
import subprocess
import yaml
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient import errors
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

class GdriveWrapper():
  def __init__(self, credentials_file, token_file):
    self.authenticate(credentials_file, token_file)

  def authenticate(self, credentials_file, token_file):
    """
    Authenticate to Google drive using the credentials stored in
    credentials_file and store the authentication tokens in token_file.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, it is
    # created automatically when the authorization flow completes.
    if os.path.exists(token_file):
      with open(token_file, 'rb') as token:
        creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
      if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
      else:
        scopes = ['https://www.googleapis.com/auth/drive']
        flow = InstalledAppFlow.from_client_secrets_file(
          credentials_file, scopes
        )
        creds = flow.run_local_server(port=0)

      # Save the credentials for the next run.
      with open(token_file, 'wb') as token:
        pickle.dump(creds, token)

    self.service = build('drive', 'v3', credentials=creds)

  def create_folder(self, folder_name):
    file_metadata = {
      'name': folder_name,
      'mimeType': 'application/vnd.google-apps.folder'
    }
    response = self.service.files().create(body=file_metadata, 
                                        fields='id').execute()
    return response['id']

  def delete_folder(self, folder_id):
    self.service.files().delete(fileId=folder_id).execute()
    self.service.files().emptyTrash().execute()

  def get_file_timestamp(self, file_id):
    f = self.service.files().get(
        fileId=file_id, fields='modifiedTime').execute()
    dt = datetime.strptime(f['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
    return int(dt.timestamp()) - 3600 * 3 # 3 hours.

  def list_files_in_folder(self, folder_id):
    self.service.files().emptyTrash().execute()
    q = "'%s' in parents" % folder_id
    response = self.service.files().list(
        q=q,
        fields='files(id, name, modifiedTime)',
        orderBy='name'
    ).execute()

    files = {}
    for f in response['files']:
      dt = datetime.strptime(f['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
      # Correct time zone (-3 hours in BRZ local time).
      timestamp = int(dt.timestamp()) - 3600 * 3
      files[f['name']] = { 'id': f['id'], 'timestamp': timestamp }
    return files

  def get_file_in_folder(self, filename, folder_id):
    self.service.files().emptyTrash().execute()
    q = "name = '%s' and '%s' in parents" % (filename, folder_id)
    response = self.service.files().list(
        q=q,
        fields='files(id, name, modifiedTime)',
        orderBy='name'
    ).execute()

    if len(response['files']) == 0:
      return None

    file_id = response['files'][0]['id']
    return self.download_file(file_id)

  def download_file(self, file_id):
    # request = self.service.files().export_media(
    request = self.service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while done is False:
      _, done = downloader.next_chunk()

    # return fh.getbuffer()
    return fh

  def upload_file(self, folder_id, filename, path):
    file_metadata = {
      'name': filename,
      'parents': [folder_id]
    }
    media = MediaFileUpload(path, mimetype='text/plain')
    self.service.files().create(body=file_metadata, media_body=media).execute()

  def update_file(self, file_id, path):
    service.files().update(
      fileId=file_id,
      media_body=MediaFileUpload(
        dir_path + '/files/' + filename,
        resumable=True
      ),
      modified_time=datetime.now().timestamp()
    ).execute()
