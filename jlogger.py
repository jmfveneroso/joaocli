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


def tokenize(s):
  tkns = re.compile("\s+|[:=(),.'?]").split(s)
  return [t.lower() for t in tkns if len(t) > 0]


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

  def get_tokens(self):
    tokens = []
    for l in self.content:
      tokens += tokenize(l)
    return tokens

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

  def get_tokens(self):
    tokens = tokenize(self.title)
    for b in self.blocks:
      tokens += b.get_tokens()
    return tokens

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

  def add_chrono(self, go, chrono_name):
    chrono_type = '>' if (go == 'go') else '<'
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(data_path, 'chrono.txt'), 'a') as f:
      f.write(timestamp + ' ' + chrono_type + ' ' + chrono_name + '\n')

  def print_log_entries(self, n=10):
    for e in reversed(self.log_entries):
      e.print_summarized()
      n -= 1
      if n == 0:
        break
