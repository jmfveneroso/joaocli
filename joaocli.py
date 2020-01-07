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

def create_log_file():
  today = datetime.date.today()
  full_date = str(today)
  week_day = str(today.strftime('%A'))
  filename = os.path.join('files', "log.%s.txt" % str(today))
  with open(filename, 'w') as f:
    f.write("%s (%s)\n\n" % (full_date, week_day))

def log_message():
  filename = "log.%s.txt" % str(datetime.date.today())
  if not os.path.isfile(os.path.join('files', filename)):
    create_log_file()

  with open(os.path.join('files', filename), 'a') as f:
    n = datetime.datetime.now()
    f.write("\n")
    f.write("[%s]" % n.strftime("%H:%M:%S"))

  subprocess.run(
    ['vim', '+normal G$', os.path.join('files', filename)]
  )

def view_log():
  pass

def process_knowledge_piece(q):
  knowledge_pieces = load_knowledge()
  if not q in knowledge_pieces:
    print('Not found')
    return

  kp = knowledge_pieces[q]
  kp_type = kp['type'] if 'type' in kp else 'text'

  if kp_type == 'chrome':
    subprocess.run([config['chrome-path'], '--new-tab', kp['text']])
    return

  if kp_type == 'img':
    subprocess.run([config['open'], dir_path + '/files/' + kp['text']])
    return

  if kp_type == 'file':
    with open(dir_path + '/files/' + kp['text'], 'r') as f:
      print(f.read())
    return

  if kp_type == 'bash':
    subprocess.run(q['text'].split())
    return

  print(kp['text'])

def create_knowledge_piece():
  # text: "%s/,/\r/g" replaces "," with NL
  knowledge_pieces = load_knowledge()

  kp_q, kp_type, kp_text = None, None, None

  valid_query = False
  while not valid_query:
    kp_q = input('Key: ')
    if len(kp_q) == 0:
      print("Query cannot be null.")
    elif kp_q in knowledge_pieces:
      print("Query '%s' already exists. Choose another keyphrase." % kp_q)
    else:
      valid_query = True

  valid_type = False
  while not valid_type:
    kp_type = input('Type (default: text): ')
    kp_type = 'text' if len(kp_type) == 0 else kp_type
    if kp_type in ['text', 'chrome', 'bash', 'file']:
      valid_type = True
    else:
      print('Invalid type. Valid types are: text, chrome, bash, or file.')

  valid_text = False
  while not valid_text:
    kp_text = input('Text: ')
    if len(kp_text):
      valid_text = True
    else:
      print('Invalid text.')

  data = None
  with open(os.path.join(dir_path, "files/knowledge.yml"), "r") as f:
    content = f.read()
    data = yaml.safe_load(content)
    data[kp_q] = {
      'type': kp_type,
      'text': kp_text
    }

  with open(os.path.join(dir_path, "files/knowledge.yml"), "w") as f:
    yaml.dump(data, f)

def process_query(args):
  query = ' '.join(args.command)

  if query == 'sync':
    return sync()

  # Create a knowledge piece.
  if query == 'add' or query == 'create':
    # add_text = args.text
    # add_type = args.type
    return create_knowledge_piece()

  if query == 'log':
    # Log a message in the current open log file.
    return log_message()

  if query == 'view':
    return view_log()

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
  parser.add_argument('--type', type=str, help="set the KE type")
  parser.add_argument('--text', type=str, help="set the KE text")
  parser.add_argument('command', type=str, nargs='+', help='the main command')

  args = parser.parse_args()
  process_query(args)

