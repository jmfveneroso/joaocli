#!/usr/local/bin/python3

import argparse
import datetime
import knowledge_base
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
    wrapper = knowledge_base.GdriveWrapper(
      dir_path + '/credentials.json',
      dir_path + '/token.pickle',
    )
    file_manager = knowledge_base.FileSyncer(
      wrapper,
      os.path.join(dir_path, 'files'),
      '16dRHX58zL2Wh721T5q_8yZ2ulP3hq2Gm',
    )
    file_manager.sync()
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

