#!/usr/local/bin/python3

import argparse
import datetime
import file_syncer
import jlogger
import glob
import io
import json
import math
import os
import pickle
import re
import shutil
import subprocess
import signal
import sys
import tempfile
import termios
import tty
import yaml
import os.path
from collections import Counter

dir_path = os.path.dirname(os.path.realpath(__file__))
data_path = os.path.join(dir_path, 'files')
orig_settings = termios.tcgetattr(sys.stdin)

def signal_handler(sig, frame):
  global orig_settings
  termios.tcsetattr(sys.stdin, termios.TCSADRAIN, orig_settings)
  sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

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

def get_titles():
  titles = {}
  entries = jlogger.get_logs()
  for e in entries:
    titles[e['title']] = e
  return titles

def get_chronos():
  chronos = {}
  entries = jlogger.get_logs()
  for e in entries:
    if e['chrono_start']:
      chronos[e['chrono_start']] = e
    if e['chrono_end']:
      chronos[e['chrono_end']] = e
  return chronos

def view_titles():
  titles = get_titles()
  for t in titles:
    e = titles[t]
    s = e['date'] + ' ' + e['time'][1:-1]
    dt = datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    print(e['id'], s, t)

def view_chronos():
  chronos = get_chronos()
  for c in chronos:
    print(c)

def view_log(n):
  n = 10 if n is None else n
  n = 1000 if n == 0 else n
  num_entries_to_print = n

  entries = jlogger.get_logs()
  cur_date = None
  for e in entries:
    jlogger.print_log_entry(e, print_date=(cur_date != e['date']))
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

def tknize(s):
  tkns = re.compile("\s+|[:=(),.'?]").split(s)
  return [t for t in tkns if len(t) > 0]

def vocab():
  words = []
  kps = load_knowledge()
  for key in kps:
    words += tknize(key)
    words += tknize(kps[key]['text'])

  for e in jlogger.get_logs():
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

def seconds_since_midnight(date):
  midnight = date.replace(hour=0, minute=0, second=0, microsecond=0)
  seconds = (date - midnight).total_seconds()
  return seconds

def seconds_to_date(seconds):
  d = datetime.datetime(year=2020, month=1, day=1, hour=0, minute=0, second=0)
  d = d + datetime.timedelta(seconds=seconds)
  return d.strftime("%H:%M:%S")

def print_chrono(chrono):
  logs = jlogger.get_logs()
  logs.reverse()

  chrono_events = []
  started = None
  for e in logs:
    if e['chrono_start'] == chrono:
      d = datetime.datetime.strptime(
        "%s %s" % (e['date'], e['time'][1:-1]), '%Y-%m-%d %H:%M:%S'
      )
      chrono_events.append(('S', d))

    if e['chrono_end'] == chrono:
      d = datetime.datetime.strptime(
        "%s %s" % (e['date'], e['time'][1:-1]), '%Y-%m-%d %H:%M:%S'
      )
      chrono_events.append(('E', d))

  lines = []

  avg = { 'S': [], 'E': [], 'D': [] }
  for i in range(len(chrono_events)):
    e = chrono_events[i]
    avg[e[0]].append(seconds_since_midnight(e[1]))

    if i > 0 and e[0] == 'E' and chrono_events[i-1][0] == 'S':
      duration = abs(chrono_events[i][1] - chrono_events[i-1][1])
      avg['D'].append(duration.seconds)
      lines.append("E: %s (%s)" % (
          e[1].strftime("%Y-%m-%d %H:%M:%S"),
          datetime.timedelta(seconds=duration.seconds)
      ))
    else:
      lines.append("%s: %s" % (e[0], e[1].strftime("%Y-%m-%d %H:%M:%S")))

  print('Average start: %s' % seconds_to_date(sum(avg['S']) // len(avg['S'])))
  print('Average end: %s' % seconds_to_date(sum(avg['E']) // len(avg['E'])))

  average_timespan = 0
  if len(avg['D']) > 0:
    average_timespan = sum(avg['D']) // len(avg['D'])
  print('Average time span: %s' % datetime.timedelta(seconds=average_timespan))

  for l in reversed(lines):
    print(l)

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
  for e in jlogger.get_logs():
    if tag in e['tags']:
      jlogger.print_log_entry(e)

def search(q, show_all=False):
  v = load_vocab()
  tkns = tknize(q)

  tags = get_tags()
  if len(tkns) == 1 and tkns[0] in tags:
    return search_tag(tkns[0])

  titles = get_titles()
  if len(tkns) == 1 and tkns[0] in titles:
    return jlogger.print_single_entry(titles[tkns[0]])

  chronos = get_chronos()
  if len(tkns) == 1 and tkns[0] in chronos:
    return print_chrono(tkns[0])

  tkns = [get_closest_word(t, v) for t in tkns]
  tkn_set = { t.lower() for t in tkns }

  scored_entries = []
  for e in jlogger.get_logs():
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
  for i in range(len(scored_entries)):
    e = scored_entries[i][1]
    if e['count'] > 0:
      scored_entries[i][0] += e['count']

  scored_entries = sorted(scored_entries, key=lambda e : e[0], reverse=True)

  if scored_entries == 0:
    print("No results found")
    return

  if show_all:
    for e in scored_entries:
      jlogger.print_log_entry(e[1], e[0])
    return

  global orig_settings

  cursor = 0
  pressed_key = None
  while pressed_key != chr(27):
    subprocess.call('clear')
    print('Query:', bcolors.HEADER + q + bcolors.ENDC + ' ' + ' '.join(tkns))
    print('Showing result %d of %d' % (cursor+1, len(scored_entries)))
    print()

    entry = scored_entries[cursor]
    jlogger.print_log_entry(entry[1], entry[0])

    tty.setcbreak(sys.stdin)
    pressed_key = sys.stdin.read(1)[0]
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, orig_settings)

    if pressed_key == 'j' or pressed_key == 13:
      cursor = cursor + 1 if cursor < len(scored_entries) - 1 else cursor
    elif pressed_key == 'k':
      cursor = cursor - 1 if cursor > 0 else cursor
    elif pressed_key == chr(10):
      jlogger.log_message_increase_count(entry[1]['id'])
      sync(dry_run=False, verbose=True)
      return
    elif pressed_key == 'q':
      return

def get_tags():
  tags = set()
  entries = jlogger.get_logs()
  for e in entries:
    for t in e['tags']:
      tags.add(t)
  return tags

def tags():
  tags = {}
  entries = jlogger.get_logs()
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

  if args.command[0] == 'replace':
    if len(args.command) < 2:
      return
    return jlogger.replace_log_message(args.command[1])

  if query == 'log':
    return jlogger.log_message()

  if query == 'view':
    return view_log(args.n)

  if query == 'titles':
    return view_titles()

  if query == 'chronos':
    return view_chronos()

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
    search(query, bool(args.all))

if __name__ == '__main__':
  load_config()

  parser = argparse.ArgumentParser(
    prog='joaocli',
    description='Command line interface (CLI) for Joao.'
  )
  parser.add_argument('--version', action='version', version='%(prog)s 0.1')
  parser.add_argument('--type', type=str, help="set the KE type")
  parser.add_argument('--text', type=str, help="set the KE text")
  parser.add_argument('-a', '--all', action='store_true')
  parser.add_argument('-d', '--dry-run', action='store_true')
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('-n', type=int, help="number of entries to print")
  parser.add_argument('command', type=str, nargs='+', help='the main command')

  args = parser.parse_args()
  process_query(args)
