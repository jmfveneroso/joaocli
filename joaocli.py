#!/usr/local/bin/python3

import argparse
import datetime
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

dir_path = os.path.dirname(os.path.realpath(__file__))
def gdrive_authenticate():
  creds = None
  # The file token.pickle stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists(dir_path + '/token.pickle'):
    with open(dir_path + '/token.pickle', 'rb') as token:
      creds = pickle.load(token)

  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      SCOPES = ['https://www.googleapis.com/auth/drive']
      flow = InstalledAppFlow.from_client_secrets_file(
        dir_path + '/credentials.json', SCOPES
      )
      creds = flow.run_local_server(port=0)

    # Save the credentials for the next run
    with open(dir_path + '/token.pickle', 'wb') as token:
      pickle.dump(creds, token)

  return build('drive', 'v3', credentials=creds)

def sync():
  folder_id = '16dRHX58zL2Wh721T5q_8yZ2ulP3hq2Gm'
  try:
    service = gdrive_authenticate()
    service.files().emptyTrash().execute()
    response = service.files().list(q='\'' + folder_id + '\' in parents').execute()
    local_files =  {filename for filename in os.listdir(dir_path + '/files/') if not filename.endswith('.swp') and not filename.startswith('.')}
    remote_files = {item['name']: item['id'] for item in response['files']}

    files = {}
    for filename in local_files:
      local_timestamp = os.stat(dir_path + "/files/" + filename)[8]
      remote_timestamp = 0
      if not filename in remote_files:
        files[filename] = (local_timestamp, 0, 0)
        continue
      
      file_id = remote_files[filename]
      f = service.files().get(fileId=file_id, fields='modifiedTime').execute()
      dt = datetime.datetime.strptime(f['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
      remote_timestamp = int(dt.timestamp()) - 3600 * 3 # 3 hours.
      files[filename] = (local_timestamp, remote_timestamp, file_id)

    for filename in remote_files:
      if filename in local_files:
        continue

      file_id = remote_files[filename]
      f = service.files().get(fileId=file_id, fields='modifiedTime').execute()
      dt = datetime.datetime.strptime(f['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
      remote_timestamp = int(dt.timestamp()) - 3600 * 3 # 3 hours.
      files[filename] = (0, remote_timestamp, file_id)

    keys = [k for k in files]
    keys.sort()

    for filename in keys:
      local_timestamp = files[filename][0]
      remote_timestamp = files[filename][1]
      dt = datetime.datetime.fromtimestamp(local_timestamp) 
      local_time = dt.strftime("%d/%m/%Y %H:%M:%S")
      dt = datetime.datetime.fromtimestamp(files[filename][1]) 
      remote_time = dt.strftime("%d/%m/%Y %H:%M:%S")

      file_id = files[filename][2]
      action = ['Do Nothing', 'Upload', 'Download'][0]
      if local_timestamp == 0:
        print(filename + ' - Remote: ' + remote_time)
        proceed = input('Download file ' + filename + '? (y/n)\n') == 'y'
        if not proceed:
          continue

        request = service.files().export_media(fileId=file_id, mimeType='text/plain')
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while done is False:
          _, done = downloader.next_chunk()

        with open(dir_path + "/files/" + filename, "wb") as f:
          f.write(fh.getbuffer())
        os.utime(dir_path + "/files/" + filename, (remote_timestamp, remote_timestamp))
        print('(DOWNLOADED) ' + filename)
      elif remote_timestamp == 0:
        print(filename + ' - Local: ' + local_time)
        proceed = input('Upload file ' + filename + '? (y/n)\n') == 'y'
        if not proceed:
          continue

        file_metadata = {
          'name': filename,
          'parents': [folder_id]
        }
        media = MediaFileUpload(dir_path + '/files/' + filename, mimetype='text/plain')
        service.files().create(body=file_metadata,
                               media_body=media,
                               fields='id').execute()
        new_timestamp = datetime.datetime.now().timestamp()
        os.utime(dir_path + "/files/" + filename, (new_timestamp, new_timestamp))
        print('(UPLOADED) ' + filename)
      else:
        print(filename + ' - Local: ' + local_time + ' - Remote: ' + remote_time)

        if abs(remote_timestamp - local_timestamp) > 100: # 5 minutes.
          if remote_timestamp > local_timestamp:
            proceed = input('Download file ' + filename + '? (y/n)\n') == 'y'
            if not proceed:
              continue

            request = service.files().export_media(fileId=file_id, mimeType='text/plain')
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while done is False:
              _, done = downloader.next_chunk()

            with open(dir_path + "/files/" + filename, "wb") as f:
              f.write(fh.getbuffer())
            os.utime(dir_path + "/files/" + filename, (remote_timestamp, remote_timestamp))
            print('(DOWNLOADED) ' + filename)
          else:
            proceed = input('Upload file ' + filename + '? (y/n)\n') == 'y'
            if not proceed:
              continue

            new_timestamp = datetime.datetime.now().timestamp()
            service.files().update(
              fileId=file_id,
              media_body=MediaFileUpload(
                dir_path + '/files/' + filename, 
                # 'text/plain', 
                resumable=True
              ),
              modified_time=new_timestamp
            ).execute()
            os.utime(dir_path + "/files/" + filename, (new_timestamp, new_timestamp))
            print('(UPLOADED) ' + filename)
  except errors.HttpError as error:
    print('An error occurred: %s' % error)

config = {}
def load_config():
  global config
  with open(dir_path + '/config.json') as json_file:
    config = json.load(json_file)

def produce_dict_entries(key, entry, knowledge_points):
  knowledge_points[key] = entry
  if 'tags' in entry:
    for q in entry['tags']:
      knowledge_points[q] = entry

  arr = key.split('-')
  knowledge_points[' '.join(arr)] = entry
  knowledge_points[''.join(arr)] = entry

def load_knowledge_points():
  knowledge_points = {}
  with open(dir_path + "/files/knowledge.yml", "r") as f:
    content = f.read()
    entries = yaml.safe_load(content)
    for key in entries:
      e = entries[key]
      produce_dict_entries(key, e, knowledge_points)
  return knowledge_points 

if __name__ == '__main__':
  load_config()

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
      subprocess.run([config['chrome-path'], '--new-tab', q['text']])
    elif 'type' in q and q['type'] == 'img':
      subprocess.run([config['open'], dir_path + '/files/' + q['text']])
    elif 'type' in q and q['type'] == 'file':
      with open(dir_path + '/files/' + q['text'], 'r') as f:
        print(f.read())
    elif 'type' in q and q['type'] == 'bash':
      subprocess.run(q['text'].split())
    else:
      print(q['text'])
  else:
    print('Not found')
    quit()

