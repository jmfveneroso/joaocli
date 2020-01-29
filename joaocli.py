#!/usr/local/bin/python3

import argparse
import datetime
import file_syncer
import glob
import io
import json
import math
import os
import pickle
import re
import shutil
import subprocess
import sys
import tempfile
import termios
import tty
import yaml
import os.path
from collections import Counter

dir_path = os.path.dirname(os.path.realpath(__file__))
data_path = os.path.join(dir_path, 'files')

class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'
  BOLD = '\033[1m'
  UNDERLINE = '\033[4m'

config = {}
def load_config():
  global config
  with open(dir_path + '/config.json') as json_file:
    config = json.load(json_file)

def sync(dry_run, verbose):
  # storage = file_syncer.GdriveWrapper(
  #   dir_path + '/credentials.json',
  #   dir_path + '/token.pickle',
  # )
  storage = file_syncer.S3Wrapper('public')
  fsyncer = file_syncer.FileSyncer(
    storage,
    os.path.join(dir_path, 'files')
  )
  fsyncer.sync(dry_run=dry_run, verbose=verbose)

def produce_dict_entries(key, entry, knowledge_points):
  knowledge_points[key] = entry
  if 'tags' in entry:
    for q in entry['tags']:
      knowledge_points[q] = entry

  arr = key.split('-')
  knowledge_points[' '.join(arr)] = entry

def load_knowledge():
  knowledge_points = {}
  with open(os.path.join(data_path, "knowledge.yml"), "r") as f:
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
  filename = os.path.join(data_path, "log.%s.txt" % str(today))
  with open(filename, 'w') as f:
    f.write("%s (%s)\n\n" % (full_date, week_day))

def log_message():
  filename = "log.%s.txt" % str(datetime.date.today())
  if not os.path.isfile(os.path.join(data_path, filename)):
    create_log_file()

  current_id = None
  with open(os.path.join(data_path, 'id.txt'), 'r') as f:
    current_id = int(f.read().strip())
  with open(os.path.join(data_path, 'id.txt'), 'w') as f:
    f.write(str(int(current_id) + 1))

  with open(os.path.join(data_path, filename), 'a') as f:
    n = datetime.datetime.now()
    f.write("\n")
    f.write("{:08d} ".format(current_id) + "[%s]" % n.strftime("%H:%M:%S"))

  subprocess.run(
    ['vim', '+normal G$', os.path.join(data_path, filename)]
  )

def get_log_entries(timestamp):
  pattern = "^(\d{8}) (\[\d{2}:\d{2}:\d{2}\])"
  entries = []
  current_time = None
  with open(os.path.join(data_path, "log.%s.txt" % timestamp)) as f:
    i, lines = 0, f.readlines()
    while i < len(lines):
      match = re.search(pattern, lines[i])
      if match is None:
        i += 1
        continue

      entry_id = match.group(1)
      time = match.group(2)

      s = lines[i][match.span()[1]:].strip()

      tags = []
      match = re.search("^\([^)]+\)", s)
      if not match is None:
        tags = match.group()[1:-1].lower().split(',')
        tags = [t.strip() for t in tags]
        title = s[match.span()[1]:]
      else:
        title = s

      content = []
      i += 1
      while i < len(lines):
        match = re.search(pattern, lines[i])
        if not match is None:
          i -= 1
          break
        content.append(lines[i].strip())
        i += 1
      entries.append((time, title.strip(), content, entry_id, tags))
  return reversed(entries)

def get_logs():
  match_str = os.path.join(data_path, 'log.*.txt')
  files = glob.glob(match_str)
  timestamps = []
  for path in files:
    filename = path.split('/')[-1]
    timestamps.append(filename.split('.')[1])

  dates = [datetime.datetime.strptime(ts, "%Y-%m-%d") for ts in timestamps]
  dates.sort(reverse=True)
  dates = [datetime.datetime.strftime(ts, "%Y-%m-%d") for ts in dates]

  entries = []
  for d in dates:
    for e in get_log_entries(d):
      entries.append({
        'date': d,
        'time': e[0],
        'title': e[1],
        'text': e[2],
        'id': e[3],
        'tags': e[4],
      })
  return entries

def get_titles():
  titles = {}
  entries = get_logs()
  for e in entries:
    titles[e['title']] = e
  return titles

def view_titles():
  titles = get_titles()
  for t in titles:
    e = titles[t]
    s = e['date'] + ' ' + e['time'][1:-1]
    dt = datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    print(e['id'], s, t)

def view_log(n):
  n = 10 if n is None else n
  n = 1000 if n == 0 else n
  num_entries_to_print = n

  entries = get_logs()
  cur_date = None
  for e in entries:
    print_log_entry(e, print_date=(cur_date != e['date']))
    cur_date = e['date']

    num_entries_to_print -= 1
    if num_entries_to_print == 0:
      break

def process_knowledge_piece(q):
  knowledge_pieces = load_knowledge()
  if not q in knowledge_pieces:
    return False

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
    subprocess.run(kp['text'].split())
    return

  print(kp['text'])
  return True

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
  with open(os.path.join(data_path, "knowledge.yml"), "r") as f:
    content = f.read()
    data = yaml.safe_load(content)
    data[kp_q] = {
      'type': kp_type,
      'text': kp_text
    }

  with open(os.path.join(data_path, "knowledge.yml"), "w") as f:
    yaml.dump(data, f)

def tknize(s):
  tkns = re.compile("\s+|[:=(),.'?]").split(s)
  return [t for t in tkns if len(t) > 0]

def vocab():
  words = []
  kps = load_knowledge()
  for key in kps:
    words += tknize(key)
    words += tknize(kps[key]['text'])

  for e in get_logs():
    words += tknize(e['title'])
    for l in e['text']:
      words += tknize(l)
  words = [w.lower() for w in words]

  with open(os.path.join(data_path, 'vocab.txt'), 'w') as f:
    counter = Counter(words)
    for w in counter.most_common():
      f.write(w[0] + ' ' + str(w[1]) + '\n')

def load_vocab():
  v = {}
  with open(os.path.join(data_path, 'vocab.txt'), 'r') as f:
    for line in f:
      arr = line.split()
      v[arr[0]] = int(arr[1])
  return v

def print_log_entry(e, score=0.0, print_date=True):
  padding = '==================================='
  if score > 0:
    print(bcolors.OKBLUE + str(score) + bcolors.ENDC)

  if print_date:
    print(bcolors.HEADER + padding + e['date'] + padding + bcolors.ENDC)

  print(
    bcolors.UNDERLINE + e['id'] + bcolors.ENDC,
    e['time'],
    bcolors.OKGREEN + e['title'] + bcolors.ENDC
  )

  if len(e['tags']) > 0:
    print(bcolors.OKBLUE + ' '.join(e['tags']) + bcolors.ENDC)

  is_empty = False
  for l in e['text']:
    print(l)
    is_empty = len(l) == 0
  if not is_empty:
    print('')

def get_levenshtein_distance(w1, w2):
  memo = [i for i in range(len(w1) + 1)]
  memo2 = [0 for _ in range(len(w1) + 1)]

  for j in range(len(w2)):
    memo2[0] = j
    for i in range(len(w1)):
      min_val = memo[i] + (0 if w1[i] == w2[j] else 1)
      min_val = min(min_val, memo[i+1] + 1)
      min_val = min(min_val, memo2[i] + 1)
      memo2[i+1] = min_val
    memo = memo2.copy()
  return memo[len(w1)]

def get_closest_word(w, vocab):
  if w in vocab:
    return w

  min_word = None
  min_distance = 100
  for w2 in vocab:
    if abs(len(w2) - len(w)) > min_distance:
      continue

    dis = get_levenshtein_distance(w, w2)
    if dis < min_distance:
      min_distance = dis
      min_word = w2

  return min_word

def search_tag(tag):
  entries = []
  for e in get_logs():
    if tag in e['tags']:
      print_log_entry(e)

def search(q):
  v = load_vocab()
  tkns = tknize(q)

  tags = get_tags()
  if len(tkns) == 1 and tkns[0] in tags:
    return search_tag(tkns[0])

  titles = get_titles()
  if len(tkns) == 1 and tkns[0] in titles:
    return print_log_entry(titles[tkns[0]], 0.0)

  tkns = [get_closest_word(t, v) for t in tkns]
  tkn_set = { t.lower() for t in tkns }

  scored_entries = []
  for e in get_logs():
    words = tknize(e['title'])
    for l in e['text']:
      words += tknize(l)
    words = [w.lower() for w in words]

    score = 0
    norm = 0
    for w in words:
      if w in v:
        if w in tkn_set:
          score += (1.0 / v[w]) ** 2
        norm += (1.0 / v[w]) ** 2
    if norm > 0.0:
      score /= math.sqrt(norm)
    scored_entries.append([score, e])

  scored_entries = [e for e in scored_entries if e[0] > 0.0]
  scored_entries = sorted(scored_entries, key=lambda e : e[0], reverse=True)

  cursor = 0
  orig_settings = termios.tcgetattr(sys.stdin)

  pressed_key = None
  while pressed_key != chr(27):
    subprocess.call('clear')
    print('Query:', bcolors.HEADER + q + bcolors.ENDC + ' ' + ' '.join(tkns))
    print('Showing result %d of %d' % (cursor+1, len(scored_entries)))
    print()

    entry = scored_entries[cursor]
    print_log_entry(entry[1], entry[0])

    tty.setcbreak(sys.stdin)
    pressed_key = sys.stdin.read(1)[0]
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, orig_settings)

    if pressed_key == 'j' or pressed_key == 13:
      cursor = cursor + 1 if cursor < len(scored_entries) - 1 else cursor
    elif pressed_key == 'k':
      cursor = cursor - 1 if cursor > 0 else cursor
    elif pressed_key == chr(10):
      log_message_increase_count(entry[1]['id'])
      return

  # TODO: show all if flag --all
  # for e in scored_entries:
  #   print_log_entry(e[1], e[0])

def find_log_entry(title_or_id):
  log_entry = None
  for e in get_logs():
    try:
      if int(e['id']) == int(title_or_id):
        log_entry = e
        break
    except ValueError:
      pass

    if e['title'] == title_or_id:
      log_entry = e
      break
  return log_entry

def log_message_increase_count(title_or_id):
  e = find_log_entry(title_or_id)
  if e is None:
    print('Couldn\'t find this entry')
    return

  w_lines = []
  with open(os.path.join(data_path, "log.%s.txt" % e['date']), 'r') as f:
    pattern = "^(\d{8}) (\[\d{2}:\d{2}:\d{2}\])"
    while True:
      l = f.readline()
      if not l:
        break

      match = re.search(pattern, l)
      if match:
        w_lines.append(l)
        entry_id = match.group(1)
        if entry_id == e['id']:
          found = False
          log_lines = []
          while True:
            l2 = f.readline()
            if not l2:
              break

            if l2.startswith('+count='):
              found = True
              count = int(l2[7:])
              log_lines.append("+count=%d\n" % (count+1))
              break

            log_lines.append(l2)
            match = re.search(pattern, l2)
            if match:
              break

          if not found:
            log_lines = ['+count=1\n'] + log_lines

          for l2 in log_lines:
            w_lines.append(l2)
      else:
        w_lines.append(l)

  with open(os.path.join(data_path, "log.%s.txt" % e['date']), 'w') as f:
    for l in w_lines:
      f.write(l)

def replace_log_message(title_or_id):
  e = find_log_entry(title_or_id)
  log_entry = e
  if e is None:
    print('Couldn\'t find this entry')
    return

  with open(os.path.join(data_path, "log.%s.txt" % e['date']), 'r') as f:
    lines = [l for l in f]

  # Delete entry.
  with open(os.path.join(data_path, "log.%s.txt" % e['date']), 'w') as f:
    write = True
    pattern = "^(\d{8}) (\[\d{2}:\d{2}:\d{2}\])"
    for l in lines:
      match = re.search(pattern, l)
      if match:
        if not write:
          write = True

        entry_id = match.group(1)
        if entry_id == log_entry['id']:
          write = False
      if write:
        f.write(l)

  # Create new entry.
  filename = "log.%s.txt" % str(datetime.date.today())
  if not os.path.isfile(os.path.join(data_path, filename)):
    create_log_file()

  current_id = None
  with open(os.path.join(data_path, 'id.txt'), 'r') as f:
    current_id = int(f.read().strip())
  with open(os.path.join(data_path, 'id.txt'), 'w') as f:
    f.write(str(int(current_id) + 1))

  with open(os.path.join(data_path, filename), 'a') as f:
    n = datetime.datetime.now()
    f.write("\n")
    f.write(
      "{:08d} ".format(current_id) + "[%s] " % n.strftime("%H:%M:%S") +
      log_entry['title'] + "\n"
    )

    f.write("+change: %s %s\n" % (log_entry['date'], log_entry['time']))
    for l in log_entry['text']:
      f.write("%s\n" % l)

  subprocess.run(
    ['vim', '+normal G$', os.path.join(data_path, filename)]
  )

def get_tags():
  tags = set()
  entries = get_logs()
  for e in entries:
    for t in e['tags']:
      tags.add(t)
  return tags

def tags():
  tags = {}
  entries = get_logs()
  for e in entries:
    for t in e['tags']:
      dt = datetime.datetime.strptime(
        "%s %s" % (e['date'], e['time'][1:-1]), '%Y-%m-%d %H:%M:%S'
      )

      if not t in tags:
        tags[t] = (dt, 0)
      elif dt > tags[t][0]:
        tags[t] = (dt, tags[t][1])
      tags[t] = (tags[t][0], tags[t][1] + 1)

  tags = [(t, tags[t][0], tags[t][1]) for t in tags]
  sorted_tags = sorted(tags, key=lambda e : e[1], reverse=True)
  for t in sorted_tags:
    dt = datetime.datetime.strftime(t[1], "%Y-%m-%d %H:%M:%S")
    print("%s (%d): %s" % (t[0], t[2], dt))

def backup():
  print("Starting backup")
  source_dir = os.path.join(dir_path, "files")
  dest_dir = os.path.join(dir_path, "files_bak")

  if os.path.isdir(dest_dir):
    print("Directory %s already exists. Deleting files" % dest_dir)
    for filename in os.listdir(dest_dir):
      path = os.path.join(dest_dir, filename)
      os.remove(path)
      print("Deleted file at path %s" % path)
  else:
    os.mkdir(dest_dir)

  for filename in os.listdir(source_dir):
    source_file = os.path.join(source_dir, filename)
    dest_file = os.path.join(dest_dir, filename)
    shutil.copyfile(source_file, dest_file)

    timestamp = os.stat(source_file)[8]
    os.utime(dest_file, (timestamp, timestamp))

    source_suffix = '/'.join(source_file.split('/')[-2:])
    dest_suffix = '/'.join(dest_file.split('/')[-2:])
    print("Copied from %s to %s" % (source_suffix, dest_suffix))
  print("Finished backup")

def process_query(args):
  query = ' '.join(args.command)

  if query == 'sync':
    return sync(dry_run=bool(args.dry_run), verbose=bool(args.verbose))

  # Create a knowledge piece.
  if query == 'add' or query == 'create':
    # add_text = args.text
    # add_type = args.type
    return create_knowledge_piece()

  if args.command[0] == 'replace':
    if len(args.command) < 2:
      return
    return replace_log_message(args.command[1])

  if query == 'log':
    # Log a message in the current open log file.
    return log_message()

  if query == 'view':
    return view_log(args.n)

  if query == 'titles':
    return view_titles()

  if query == 'lint':
    # Lint knowledge files.
    return

  if query == 'diff':
    # Show differences between data folders.
    return

  if query == 'vocab':
    return vocab()

  if query == 'tags':
    return tags()

  if query == 'bak':
    return backup()

  if query == 'checkpoint':
    titles = get_titles()
    if 'Checkpoint' in titles:
      entry = titles['Checkpoint']
      text = ' ' .join(entry['text']).strip()
      checkpoint_date = datetime.datetime.strptime(text, '%Y-%m-%d')
      days_to_checkpoint = abs(checkpoint_date - datetime.datetime.now()).days
      print('%d days remaining to the next checkpoint' % days_to_checkpoint)
    return

  if not process_knowledge_piece(query):
    search(query)

if __name__ == '__main__':
  load_config()

  parser = argparse.ArgumentParser(
    prog='joaocli',
    description='Command line interface (CLI) for Joao.'
  )
  parser.add_argument('--version', action='version', version='%(prog)s 0.1')
  parser.add_argument('--type', type=str, help="set the KE type")
  parser.add_argument('--text', type=str, help="set the KE text")
  parser.add_argument('-d', '--dry-run', action='store_true')
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('-n', type=int, help="number of entries to print")
  parser.add_argument('command', type=str, nargs='+', help='the main command')

  args = parser.parse_args()
  process_query(args)
