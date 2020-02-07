import argparse
import datetime
import file_syncer
import functools
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
      self.content = content[1:]
      return

    if content[0].startswith('[x]'):
      self.type = 'COMPLETE_TASK'
      self.title = content[0][3:].strip()
      self.content = content[1:]
      return

    if content[0].startswith('+'):
      self.type = 'COMMAND'
      self.title = content[0][1:].strip()
      self.content = content[1:]
      return

    self.type = 'TEXT'
    self.content = content

  def print_detailed(self):
    if self.type == 'TASK':
      print('[ ] %s' % self.title)

    if self.type == 'COMPLETE_TASK':
      print('[x] %s' % self.title)

    if self.type == 'COMMAND':
      print('%s' % self.title)

    print('\n'.join(self.content))

  def print_summarized(self):
    if self.type == 'TEXT':
      print('\n'.join(self.content))

  def __str__(self):
    s = ''
    if self.type == 'TASK':
      s += '[ ] %s' % self.title + '\n'

    if self.type == 'COMPLETE_TASK':
      s += '[x] %s' % self.title + '\n'

    if self.type == 'COMMAND':
      s += '+%s' % self.title + '\n'

    s += '\n'.join(self.content)
    return s


class LogEntry:
  def __init__(self, log_file, entry_id, timestamp, header, content):
    # Main attributes.
    self.log_file = log_file
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
    self.sort_blocks()

  def parse_header(self, header):
    tags = []
    match = re.search("^\([^)]+\)", header)
    if match is None:
      self.title = header
    else:
      tags = match.group()[1:-1].lower().split(',')
      self.tags = [t.strip() for t in tags]
      self.title = header[match.span()[1]:]

  def is_block_start(self, s):
    prefixes = ['[ ]', '[x]', '+']
    return any([s.startswith(p) for p in prefixes])

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
      block_content = [content[i]]
      i += 1
      while i < len(content):
        line = content[i]
        if len(line) == 0:
          if found_empty_line:
            break

          found_empty_line = True
          block_content.append(line)
          i += 1
          continue
        elif self.is_block_start(line):
          break

        found_empty_line = False
        block_content.append(line)
        i += 1
      self.blocks.append(Block(self, block_content))

  def sort_blocks(self):
    def compare_fn(b1, b2):
      precedence = { 'TASK': 0, 'COMMAND': 1, 'TEXT': 1, 'COMPLETE_TASK': 2 }
      return precedence[b1.type] - precedence[b2.type]
    self.blocks = sorted(self.blocks, key=functools.cmp_to_key(compare_fn))

  def print_header(self):
    print(
      bcolors.UNDERLINE + ('%08d' % self.id) + bcolors.ENDC,
      self.timestamp,
      bcolors.OKGREEN + self.title + bcolors.ENDC,
    )

    if len(self.tags) > 0:
      print(bcolors.OKBLUE + ' '.join(self.tags) + bcolors.ENDC)
    print('')

  def print_detailed(self):
    self.print_header()
    for b in self.blocks:
      b.print_detailed()

  def print_summarized(self):
    self.print_header()
    for b in self.blocks:
      b.print_summarized()

  def __str__(self):
    s = (
      "{:08d} ".format(self.id) +
      "[%s] " % self.timestamp.strftime("%H:%M:%S") +
      self.title + "\n\n"
    )

    for b in self.blocks:
      s += str(b) + '\n'

    return s


class LogFile:
  def __init__(self, date):
    self.date = date
    self.log_entries = []

  def rewrite(self):
    filename = "log.%s.txt" % str(self.date)
    path = os.path.join(data_path, filename)

    if not os.path.isfile(path):
      raise ValueError(path + ' does not exist')

    with open(path, 'w') as f:
      dt = datetime.datetime.strptime(self.date, '%Y-%m-%d')
      week_day = str(dt.strftime('%A'))
      f.write("%s (%s)\n\n\n" % (self.date, week_day))

      for e in self.log_entries:
        f.write(str(e))

  def get_path(self):
    filename = "log.%s.txt" % str(self.date)
    return os.path.join(data_path, filename)

  def add_entry(self, entry):
    self.log_entries.append(entry)
    entry.log_file = self

  def remove_entry(self, entry):
    for i in range(len(self.log_entries)):
      if self.log_entries[i].id == entry.id:
        del self.log_entries[i]
        break
    entry.log_file = None

class Logger:
  def __init__(self):
    self.log_files = []
    self.log_entries = []
    self.log_entries_by_id = {}
    self.log_entries_by_title = {}
    self.log_entries_by_tag = {}
    self.log_files_by_date = {}

    self.load_log_files()
    self.build_indices()

  def get_log_entries(self, date):
    with open(os.path.join(data_path, "log.%s.txt" % date)) as f:
      log_file = LogFile(date)

      pattern = "^(\d{8}) (\[\d{2}:\d{2}:\d{2}\])"
      i, lines = 0, f.readlines()
      while i < len(lines):
        match = re.search(pattern, lines[i])
        if match is None:
          i += 1
          continue

        entry_id = int(match.group(1))
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

        new_entry = LogEntry(log_file, entry_id, timestamp, header, content)
        self.log_entries.append(new_entry)
        log_file.log_entries.append(new_entry)
      self.log_files.append(log_file)
      self.log_files_by_date[date] = log_file

  def load_log_files(self):
    files = glob.glob(os.path.join(data_path, 'log.*.txt'))
    dates = [path.split('/')[-1].split('.')[1] for path in files]
    dates.sort()
    for d in dates:
      self.get_log_entries(d)

  def build_indices(self):
    for e in self.log_entries:
      self.log_entries_by_id[e.id] = e
      self.log_entries_by_title[e.title.lower()] = e

      for t in e.tags:
        if t not in self.log_entries_by_tag:
          self.log_entries_by_tag[t] = []
        self.log_entries_by_tag[t].append(e)

  def get_log_entry_by_id(self, entry_id):
    if entry_id not in self.log_entries_by_id:
      return None
    return self.log_entries_by_id[entry_id]

  def get_log_entry_by_title(self, title):
    if title not in self.log_entries_by_title:
      return None
    return self.log_entries_by_title[title]

  def get_log_entries_by_tag(self, tag):
    if tag not in self.log_entries_by_tag:
      return None
    return self.log_entries_by_tag[tag]

  def get_current_log_file(self):
    date = datetime.date.today()
    filename = "log.%s.txt" % str(date)
    path = os.path.join(data_path, filename)
    if not os.path.isfile(path):
      with open(path, 'w') as f:
        full_date = str(date)
        week_day = str(date.strftime('%A'))
        f.write("%s (%s)\n\n" % (full_date, week_day))

        log_file = LogFile(date)
        self.log_files.append(log_file)
        self.log_files_by_date[date] = log_file
    return self.log_files_by_date[str(date)]

  def create_log_entry(self):
    log_file = self.get_current_log_file()

    current_id = None
    with open(os.path.join(data_path, 'id.txt'), 'r') as f:
      current_id = int(f.read().strip())
    with open(os.path.join(data_path, 'id.txt'), 'w') as f:
      f.write(str(int(current_id) + 1))

    with open(log_file.get_path(), 'a') as f:
      n = datetime.datetime.now()
      f.write("\n")
      f.write("{:08d} ".format(current_id) + "[%s]" % n.strftime("%H:%M:%S"))

    subprocess.run(
      ['vim', '+normal G$', log_file.get_path()]
    )

  def edit_log_entry(self, entry):
    print(str(entry))
    return
    filename = "log.%s.txt" % str(entry.log_file.date)
    path = os.path.join(data_path, filename)

    line_num = 1
    if not os.path.isfile(path):
      raise ValueError(path + ' does not exist')

    pattern = "^(\d{8}) (\[\d{2}:\d{2}:\d{2}\])"
    with open(path, 'r') as f:
      for l in f:
        match = re.search(pattern, l)
        if match:
          entry_id = int(match.group(1))
          if entry_id == entry.id:
            break

        line_num += 1

    subprocess.run(
      ['vim', '+normal %dgg$' % line_num, os.path.join(data_path, filename)]
    )

  def replace_log_entry(self, entry):
    log_file = entry.log_file
    log_file.remove_entry(entry)
    log_file.rewrite()

    log_file = self.get_current_log_file()
    now = datetime.datetime.now()
    entry.timestamp = datetime.datetime.strptime(
            '%s %s' % (log_file.date, now.strftime("%H:%M:%S")),
            "%Y-%m-%d %H:%M:%S")

    log_file.add_entry(entry)
    log_file.rewrite()

    subprocess.run(
      ['vim', '+normal G$', log_file.get_path()]
    )

  def autoformat(self, date):
    if date not in self.log_files_by_date:
      raise ValueError('Date is invalid')

    self.log_files_by_date[date].rewrite()


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

def _get_log_entries(timestamp):
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

  # print('\n'.join(e['text']))
  for b in blocks:
    if b.type == 'TEXT':
      print('\n'.join(e['content']))

  #
  # for b in blocks:
  #   print(b.content)
  #   # if b.type == 'TASK':
  #   #   total += b.score
  #   #   num_tasks += 1
  #   # elif b.type == 'COMPLETE_TASK':
  #   #   complete += b.score
  #   #   total += b.score
  #   #   complete_tasks += 1
  #   #   num_tasks += 1

  #   #   for c in jlogger.get_logs():
  #   #     if c['child'] == e['main']:
  #   #       blocks = blocks + _get_blocks(c)

  #   # blocks = _get_blocks(e)
  #   # if e['main']:
  #   #   print(bcolors.FAIL + 'MAIN ' + e['main'] + bcolors.ENDC)
  #   #   print('')

  #   #   for c in jlogger.get_logs():
  #   #     if c['child'] == e['main']:
  #   #       blocks = blocks + _get_blocks(c)

  #   # complete, total, num_tasks, complete_tasks = 0, 0, 0, 0
  #   # for b in blocks:
  #   #   if b.type == 'TASK':
  #   #     total += b.score
  #   #     num_tasks += 1
  #   #   elif b.type == 'COMPLETE_TASK':
  #   #     complete += b.score
  #   #     total += b.score
  #   #     complete_tasks += 1
  #   #     num_tasks += 1

  #   # if total > 0:
  #   #   print(bcolors.HEADER + 'Score: %d / %d (%.2f) in %d of %d tasks' % (
  #   #         complete, total, complete / total, complete_tasks, num_tasks) +
  #   #         bcolors.ENDC)
  #   #   print('')

  #   # task_blocks = [b for b in blocks if b.type == 'TASK']
  #   # main_tasks = [b for b in task_blocks if b.parent_title == e['title']]
  #   # child_tasks = [b for b in task_blocks if b.parent_title != e['title']]

  #   # by_parent_title = {}
  #   # for b in child_tasks:
  #   #   if not by_parent_title[b.parent_title]:
  #   #     by_parent_title[b.parent_title] = []
  #   #   by_parent_title[b.parent_title].append(b)

  #   # # Print tasks.
  #   # num_lines = 0
  #   # for b in main_tasks:
  #   #   line = (bcolors.WARNING + '[ ] ' + str(b.title) + ' - ' + str(b.score) +
  #   #           bcolors.ENDC)

  #   #   if num_lines == cursor:
  #   #     print(bcolors.UNDERLINE + line + bcolors.ENDC)
  #   #   else:
  #   #     print(line)

  #   #   print('\n'.join(b.text), end='')
  #   #   print('')
  #   #   num_lines += 1

  #   # for t in by_parent_title:
  #   #   print(bcolors.BOLD + t + bcolors.ENDC)
  #   #   for b in by_parent_title[t]:
  #   #     line = (bcolors.WARNING + '[ ] ' + str(b.title) +
  #   #           ' - ' + bcolors.OKBLUE + str(b.score) +
  #   #             ' - ' + b.parent_title)

  #   #     if num_lines == cursor:
  #   #       print(bcolors.UNDERLINE + line + bcolors.ENDC)
  #   #     else:
  #   #       print(line)

  #   #     print('\n'.join(b.content), end='')
  #   #     print('')
  #   #     num_lines += 1

  #   # # Print texts.
  #   # for b in blocks:
  #   #   if b.type != 'TEXT':
  #   #     continue

  #   #   print('\n'.join(b.content))
  #   #   print('')

  #   # # Complete tasks.
  #   # for b in blocks:
  #   #   if b.type != 'COMPLETE_TASK':
  #   #     continue

  #   #   print(bcolors.HEADER + '[x] ' + str(b.title) + bcolors.ENDC +
  #   #         ' - ' + bcolors.OKBLUE + str(b.score) + bcolors.ENDC +
  #   #         ' - ' + b.parent_title)
  #   #   print('\n'.join(b.content), end='')
  #   #   print('')

  #   # tty.setcbreak(sys.stdin)
  #   # pressed_key = sys.stdin.read(1)[0]
  #   # termios.tcsetattr(sys.stdin, termios.TCSADRAIN, orig_settings)

  #   # if pressed_key == 'j' or pressed_key == 13:
  #   #   cursor = cursor + 1 if cursor < num_lines - 1 else cursor
  #   # elif pressed_key == 'k':
  #   #   cursor = cursor - 1 if cursor > 0 else cursor
  #   # elif pressed_key == chr(10):
  #   #   return
  #   # elif pressed_key == 'q':
  #   #   return
