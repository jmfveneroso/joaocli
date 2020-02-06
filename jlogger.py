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


class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'
  BOLD = '\033[1m'
  UNDERLINE = '\033[4m'


class Block:
  def __init__(self, parent, content):
    self.parent = parent
    self.type = ''
    self.title = ''
    self.content = []

    self.init_block(content)

  def init_block(self, content):
    if len(content) == 0:
      return

    if content[0].startswith('[ ]'):
      self.type = 'TASK'
      self.title = content[0][3:].strip()
      lines = lines[1:]
      return

    if content[0].startswith('[x]'):
      self.type = 'COMPLETE_TASK'
      self.title = content[0][3:].strip()
      self.content = content[1:]
      return

    self.type = 'TEXT'
    self.content = content


class LogEntry:
  def __init__(self, entry_id, timestamp, header, content):
    # Main attributes.
    self.id = entry_id
    self.timestamp = timestamp
    self.modified_at = None
    self.title = ''
    self.tags = []
    self.commands = []

    # Command attributes.
    self.main = ''
    self.parent = ''
    self.chronos = []

    self.blocks = []

    self.parse_header(header)
    self.parse_content(content)

  def parse_header(self, header):
    tags = []
    match = re.search("^\([^)]+\)", header)
    if match is None:
      self.title = header
    else:
      tags = match.group()[1:-1].lower().split(',')
      self.tags = [header.strip() for t in tags]
      self.title = header[match.span()[1]:]

  def parse_content(self, content):
    i = 0
    while i < len(content):
      line = content[i].strip()

      # commands = {'main', 'parent', 'count', 'modified-at'}
      if line.startswith('+main='):
        self.main = str(line[6:])
      elif line.startswith('+parent='):
        self.parent = str(line[8:])
      elif line.startswith('+count='):
        self.count = int(line[7:])
      elif line.startswith('+modified-at='):
        self.modified_at = line[13:]
      else:
        break
      i += 1

    while i < len(content):
      if len(content[i]) == 0:
        i += 1
        continue

      found_empty_line = False
      block_content = []
      while i < len(content):
        if len(content[i]) == 0:
          if found_empty_line:
            break
          found_empty_line = True
          block_content.append(content[i])
          i += 1
          continue

        if content[i].startswith('[ ]') or content[i].startswith('[x]') :
          break

        block_content.append(content[i])
        self.blocks.append(Block(self, block_content))
        i += 1
      i += 1


class Logger:
  def __init__(self):
    self.log_entries = []

    self.load_log_files()

  def get_log_entries(self, date):
    with open(os.path.join(data_path, "log.%s.txt" % date)) as f:
      pattern = "^(\d{8}) (\[\d{2}:\d{2}:\d{2}\])"
      i, lines = 0, f.readlines()
      while i < len(lines):
        match = re.search(pattern, lines[i])
        if match is None:
          i += 1
          continue

        entry_id = match.group(1)
        time = match.group(2)
        timestamp = datetime.datetime.strptime(
            '%s %s' % (date, time), "%Y-%m-%d [%H:%M:%S]")

        header = lines[i][match.span()[1]:].strip()
        content = []
        i += 1
        while i < len(lines):
          match = re.search(pattern, lines[i])
          if match is not None:
            break

          content.append(lines[i].strip())
          i += 1

        self.log_entries.append(LogEntry(entry_id, timestamp, header, content))

  def load_log_files(self):
    files = glob.glob(os.path.join(data_path, 'log.*.txt'))
    dates = [path.split('/')[-1].split('.')[1] for path in files]
    dates.sort()
    for d in dates:
      entries = self.get_log_entries(d)

  def build_indices(self):
    pass

def _find_log_entry(title_or_id):
  log_entry = None
  for e in jlogger.get_logs():
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

def _create_log_file():
  today = datetime.date.today()
  full_date = str(today)
  week_day = str(today.strftime('%A'))
  filename = os.path.join(data_path, "log.%s.txt" % str(today))
  with open(filename, 'w') as f:
    f.write("%s (%s)\n\n" % (full_date, week_day))

def log_message():
  filename = "log.%s.txt" % str(datetime.date.today())
  if not os.path.isfile(os.path.join(data_path, filename)):
    _create_log_file()

  current_id = None
  with open(os.path.join(data_path, 'id.txt'), 'r') as f:
    current_id = int(f.read().strip())
  with open(os.path.join(data_path, 'id.txt'), 'w') as f:
    f.write(str(int(current_id) + 1))

  with open(os.path.join(data_path, filename), 'a') as f:
    n = datetime.datetime.now()
    f.write("\n")
    f.write("{:08d} ".format(current_id) + "[%s]" % n.strftime("%H:%M:%S"))

  now = datetime.datetime.now()
  current_time = now.strftime("%H:%M:%S")

  subprocess.run(
    ['vim', '+normal G$', os.path.join(data_path, filename)]
  )

  sync(dry_run=False, verbose=True)

def _get_log_entries(timestamp):
  logger = Logger()

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

      chrono_start = ''
      chrono_end = ''
      child = ''
      count = 0
      main = None
      content = []
      i += 1
      while i < len(lines):
        match = re.search(pattern, lines[i])
        if not match is None:
          i -= 1
          break
        content.append(lines[i].strip())

        line = lines[i].strip()
        if line.startswith('+count='):
          count = int(line[7:])

        if line.startswith('+chrono-start='):
          chrono_start = str(line[14:])

        if line.startswith('+chrono-end='):
          chrono_end = str(line[12:])

        if line.startswith('+main='):
          main = str(line[6:])

        if line.startswith('+child='):
          child = str(line[7:])

        i += 1
      entries.append((
          time, title.strip(), content, entry_id, tags, count,
          chrono_start, chrono_end, main, child
      ))
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
    for e in _get_log_entries(d):
      entries.append({
        'date': d,
        'time': e[0],
        'title': e[1],
        'text': e[2],
        'id': e[3],
        'tags': e[4],
        'count': e[5],
        'chrono_start': e[6],
        'chrono_end': e[7],
        'main': e[8],
        'child': e[9],
      })
  return entries

def _get_blocks(e):
  current_block, blocks = [], []
  for l in e['text']:
    if l.startswith('+main'):
      is_main = True
      continue

    if len(l) == 0 or l.startswith('[ ]') or l.startswith('[x]') :
      if len(current_block) > 0:
        blocks.append(Block(current_block, e['title']))

      current_block = []
      if len(l) > 0:
        current_block.append(l)
    else:
      current_block.append(l)

  if len(current_block) > 0:
    blocks.append(Block(current_block, e['title']))

  return blocks

def log_message_increase_count(title_or_id):
  e = _find_log_entry(title_or_id)
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
  e = _find_log_entry(title_or_id)
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
    _create_log_file()

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

  sync(dry_run=False, verbose=True)

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

  for l in e['text']:
    print(l)

def print_single_entry(e):
  cursor = 0
  num_lines = 100
  pressed_key = None
  while pressed_key != chr(27):
    subprocess.call('clear')
    padding = '==================================='
    print(bcolors.HEADER + padding + e['date'] + padding + bcolors.ENDC)

    print(
      bcolors.UNDERLINE + e['id'] + bcolors.ENDC,
      e['time'],
      bcolors.OKGREEN + e['title'] + bcolors.ENDC
    )

    if len(e['tags']) > 0:
      print(bcolors.OKBLUE + ' '.join(e['tags']) + bcolors.ENDC)

    blocks = _get_blocks(e)
    if e['main']:
      print(bcolors.FAIL + 'MAIN ' + e['main'] + bcolors.ENDC)
      print('')

      for c in jlogger.get_logs():
        if c['child'] == e['main']:
          blocks = blocks + _get_blocks(c)

    complete, total, num_tasks, complete_tasks = 0, 0, 0, 0
    for b in blocks:
      if b.type == 'TASK':
        total += b.score
        num_tasks += 1
      elif b.type == 'COMPLETE_TASK':
        complete += b.score
        total += b.score
        complete_tasks += 1
        num_tasks += 1

    if total > 0:
      print(bcolors.HEADER + 'Score: %d / %d (%.2f) in %d of %d tasks' % (
            complete, total, complete / total, complete_tasks, num_tasks) +
            bcolors.ENDC)
      print('')

    task_blocks = [b for b in blocks if b.type == 'TASK']
    main_tasks = [b for b in task_blocks if b.parent_title == e['title']]
    child_tasks = [b for b in task_blocks if b.parent_title != e['title']]

    by_parent_title = {}
    for b in child_tasks:
      if not by_parent_title[b.parent_title]:
        by_parent_title[b.parent_title] = []
      by_parent_title[b.parent_title].append(b)

    num_lines = 0
    # Print tasks.
    for b in main_tasks:
      line = (bcolors.WARNING + '[ ] ' + str(b.title) + ' - ' + str(b.score) +
              bcolors.ENDC)

      if num_lines == cursor:
        print(bcolors.UNDERLINE + line + bcolors.ENDC)
      else:
        print(line)

      print('\n'.join(b.text), end='')
      print('')
      num_lines += 1

    for t in by_parent_title:
      print(bcolors.BOLD + t + bcolors.ENDC)
      for b in by_parent_title[t]:
        line = (bcolors.WARNING + '[ ] ' + str(b.title) +
              ' - ' + bcolors.OKBLUE + str(b.score) +
                ' - ' + b.parent_title)

        if num_lines == cursor:
          print(bcolors.UNDERLINE + line + bcolors.ENDC)
        else:
          print(line)

        print('\n'.join(b.text), end='')
        print('')
        num_lines += 1

    # Print texts.
    for b in blocks:
      if b.type != 'TEXT':
        continue

      print('\n'.join(b.text))
      print('')

    # Complete tasks.
    for b in blocks:
      if b.type != 'COMPLETE_TASK':
        continue

      print(bcolors.HEADER + '[x] ' + str(b.title) + bcolors.ENDC +
            ' - ' + bcolors.OKBLUE + str(b.score) + bcolors.ENDC +
            ' - ' + b.parent_title)
      print('\n'.join(b.text), end='')
      print('')

    tty.setcbreak(sys.stdin)
    pressed_key = sys.stdin.read(1)[0]
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, orig_settings)

    if pressed_key == 'j' or pressed_key == 13:
      cursor = cursor + 1 if cursor < num_lines - 1 else cursor
    elif pressed_key == 'k':
      cursor = cursor - 1 if cursor > 0 else cursor
    elif pressed_key == chr(10):
      return
    elif pressed_key == 'q':
      return


