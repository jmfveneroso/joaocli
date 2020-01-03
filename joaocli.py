#!/usr/local/bin/python3

import argparse
import datetime
import file_syncer
import io
import json
import os
import pickle
import subprocess
import yaml
import os.path

dir_path = os.path.dirname(os.path.realpath(__file__))

config = {}
def load_config():
  global config
  with open(dir_path + '/config.json') as json_file:
    config = json.load(json_file)

def sync():
  gdrive = file_syncer.GdriveWrapper(
    dir_path + '/credentials.json',
    dir_path + '/token.pickle',
  )
  fsyncer = file_syncer.FileSyncer(
    gdrive,
    os.path.join(dir_path, 'files'),
    '16dRHX58zL2Wh721T5q_8yZ2ulP3hq2Gm',
  )
  fsyncer.sync()

def produce_dict_entries(key, entry, knowledge_points):
  knowledge_points[key] = entry
  if 'tags' in entry:
    for q in entry['tags']:
      knowledge_points[q] = entry

  arr = key.split('-')
  knowledge_points[' '.join(arr)] = entry
  knowledge_points[''.join(arr)] = entry

def load_knowledge():
  knowledge_points = {}
  with open(dir_path + "/files/knowledge.yml", "r") as f:
    content = f.read()
    entries = yaml.safe_load(content)
    for key in entries:
      e = entries[key]
      produce_dict_entries(key, e, knowledge_points)
  return knowledge_points

def process_knowlege_piece(q):
  knowledge_pieces = load_knowledge()
  if not q in knowledge_pieces:
    print('Not found')
    return

  kp = knowledge_pieces[q]
  kp_type = kp['type'] if 'type' in kp else 'text'

  if kp_type == 'chrome':
    subprocess.run([config['chrome-path'], '--new-tab', q['text']])
    return

  if kp_type == 'img':
    subprocess.run([config['open'], dir_path + '/files/' + q['text']])
    return

  if kp_type == 'file':
    with open(dir_path + '/files/' + q['text'], 'r') as f:
      print(f.read())
    return

  if kp_type == 'bash':
    subprocess.run(q['text'].split())
    return

  print(q['text'])

def process_query(query):
  if query == 'sync':
    return sync()

  if query == 'add':
    # Create a knowledge piece.
    # j add
    # query: newline-vim (check if it is valid)
    # type: text (check if is valid)
    # text:
    # "%s/,/\r/g" replaces "," with NL
    return

  if query == 'log':
    # Log a message in the current open log file.
    return

  if query == 'lint':
    # Lint knowledge files.
    return

  if query == 'diff':
    # Show differences between data folders.
    return

  process_knowledge_piece(query)

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
  process_query(command)

