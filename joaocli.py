#!/usr/local/bin/python3

from __future__ import print_function
import argparse
import datetime
import io
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

chrome_location = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' 
# '/opt/google/chrome/chrome'

class Entry:
  def __init__(self, type, text, tags=[]):
    self.type = type
    self.text = text

SCOPES = ['https://www.googleapis.com/auth/drive']
def gdrive_authenticate():
  creds = None
  # The file token.pickle stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
      creds = pickle.load(token)

  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES
      )
      creds = flow.run_local_server(port=0)

    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
      pickle.dump(creds, token)

  return build('drive', 'v3', credentials=creds)

def sync():
  file_id = '1MuaSM4kIRJ4Zz2iIViMOaaz3VG6iH9Q8YLzlXK40mfE'

  try:
    service = gdrive_authenticate()
    download_file = True
    if os.path.isfile('knowledge.yml'):
      f = service.files().get(fileId=file_id, fields='modifiedTime').execute()
      dt = datetime.datetime.strptime(f['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
      remote_timestamp = int(dt.timestamp())
      local_timestamp = os.stat("knowledge.yml")[8] + 3600 * 3 # 3 hours.
      download_file = remote_timestamp > local_timestamp

    if download_file:
      print('Downloading file...')
      request = service.files().export_media(fileId=file_id, mimeType='text/plain')
      fh = io.BytesIO()
      downloader = MediaIoBaseDownload(fh, request)

      done = False
      while done is False:
        _, done = downloader.next_chunk()

      with open("knowledge.yml", "wb") as f:
        f.write(fh.getbuffer())
    else:
      print('Uploading file...')
      updated_file = service.files().update(
        fileId=file_id,
        media_body=MediaFileUpload(
          'knowledge.yml', 'text/plain', resumable=True
        )
      ).execute()
  except errors.HttpError as error:
    print('An error occurred: %s' % error)

def load_knowledge_points():
  knowledge_points = {}
  with open("knowledge.yml", "r") as f:
    content = f.read()
    entries = yaml.safe_load(content)
    for key in entries:
      e = entries[key]
      knowledge_points[key] = e
      if 'tags' in e:
        for q in e['tags']:
          knowledge_points[q] = e
  return knowledge_points 

if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    prog='joaocli', 
    description='Command line interface (CLI) for Joao.'
  )
  parser.add_argument('--version', action='version', version='%(prog)s 0.1')
  parser.add_argument('command', type=str, nargs='+', help='the main command')

  args = parser.parse_args()
  command = ' '.join(args.command)

  if command == 'sync':
    sync()
    quit()

  knowledge_points = load_knowledge_points()
  if command in knowledge_points:
    q = knowledge_points[command]
    if 'type' in q and q['type'] == 'chrome':
      subprocess.run([chrome_location, '--new-tab', q['text']])
    else:
      print(q['text'])
  else:
    print('Not found')
    quit()

