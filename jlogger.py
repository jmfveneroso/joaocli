import argparse
import datetime
import functools
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


def load_vocab():
  v = {}
  with open(os.path.join(data_path, 'vocab.txt'), 'r') as f:
    for line in f:
      arr = line.split()
      v[arr[0]] = int(arr[1])
  return v


def tokenize(s):
  tkns = re.compile("\s+").split(s)
  good_tkns = []
  for t in tkns:
    # Check if it is a URL.
    if re.match('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', t) is not None:
      good_tkns.append(t)
      continue
    good_tkns += re.compile("\s+|[:=(),.'?]").split(t.lower())
  return [t for t in good_tkns if len(t) > 0]


class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'
  BOLD = '\033[1m'
  UNDERLINE = '\033[4m'


class Tag:
  def __init__(self, name, entries):
    self.name = name
    self.entries = entries

    self.modified_at = datetime.datetime(year=1970, month=1, day=1)
    if self.entries:
      self.modified_at = entries[-1].modified_at

    self.common_words = []
    self.calculate_stats()
    self.children = []
    self.parent = None

  def get_child_tags(self):
    tags = []

    queue = [self]
    while queue:
      current = queue[-1]
      queue.pop()
      tags.append(current)
      queue += current.children

    tags.sort(key=lambda t: t.modified_at, reverse=True)
    return tags

  def get_entries(self):
    entries = []
    for t in self.get_child_tags():
      entries += t.entries
    return entries

  def print_header(self):
    print(bcolors.HEADER + '======================================' + bcolors.ENDC)
    print(bcolors.HEADER + '%s (%d entries)' %
          (self.name, len(self.entries)))
    print(' '.join(['%s (%d %.2f)' % w for w in self.common_words][:5]))
    print(bcolors.HEADER + '======================================' + bcolors.ENDC)

  def print_summary(self):
    self.print_header()

    entries_to_print = 3

    if self.entries:
      self.entries[-1].print_detailed(print_tags=False)

    for e in reversed(self.entries[-entries_to_print:-1]):
      e.print_summarized(print_tags=False)
    print('\n')

  def print_snippet(self):
    dt = 'no entries'
    if self.entries:
      e = self.entries[0]
      dt = datetime.datetime.strftime(e.timestamp, "%Y-%m-%d %H:%M:%S")
    print('%s: %d (%s)' % (self.name, len(self.entries), dt))

  def print_detailed(self):
    tags = self.get_child_tags()

    for t in tags:
      print('============================================')
      t.print_snippet()
      print('============================================')
      for e in t.entries:
        e.print_detailed()

  def calculate_stats(self):
    words = []
    for e in self.entries:
      words += e.get_tokens()

    self.common_words = []
    v = load_vocab()
    counter = Counter([w for w in words])
    for w in counter.most_common():
      if w[0] in v:
        score = w[1] # TF
        score *= math.log2(1 + w[1] / v[w[0]]) # IDF
        self.common_words.append((w[0], w[1], score))

    self.common_words = sorted(self.common_words, key=lambda e : e[2], reverse=True)


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

    self.content = []

    self.parse_header(header)
    self.parse_content(content)

  def parse_header(self, header):
    tags = []
    match = re.search("^\([^)]+\)", header)
    if match is None:
      self.title = header
    else:
      tags = match.group()[1:-1].lower().split(',')
      self.tags = [t.strip() for t in tags]
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
      elif line.startswith('+modified-at '):
        self.modified_at = datetime.datetime.strptime(line[13:], "%Y-%m-%d %H:%M:%S")
      else:
        break
      i += 1

    if self.modified_at is None:
      self.modified_at = self.timestamp

    while i < len(content):
      self.content.append(content[i])
      i += 1

  def set_modified_time(self, modified_at):
    self.modified_at = modified_at

  def print_header(self, print_tags=True):
    date = self.modified_at if self.modified_at else self.timestamp

    if self.modified_at != self.timestamp:
      date = str(date) + bcolors.HEADER + ' (created at: %s)' % self.timestamp + bcolors.ENDC

    print(
      bcolors.UNDERLINE + ('%08d' % self.id) + bcolors.ENDC,
      date,
      bcolors.OKGREEN + self.title + bcolors.ENDC,
    )

    if len(self.tags) > 0 and print_tags:
      print(bcolors.OKBLUE + ' '.join(self.tags) + bcolors.ENDC)
    print('')

  def print_detailed(self, print_tags=True):
    self.print_header(print_tags)
    for l in self.content:
      print(l)

  def print_summarized(self, print_tags=True):
    self.print_header(print_tags)
    for l in self.content[:5]:
      print(l)

  def get_tokens(self):
    tokens = tokenize(self.title)
    for l in self.content:
      tokens += tokenize(l)
    return tokens

  def __str__(self):
    tags = ''
    if len(self.tags) > 0:
      tags = '(' + ' '.join(self.tags) + ')'

    s = (
      "{:08d} ".format(self.id) +
      "[%s] " % self.timestamp.strftime("%H:%M:%S") +
      tags + ' ' + self.title.strip() + "\n"
    )

    if self.modified_at is not None:
      s += '+modified-at %s\n' % self.modified_at.strftime("%Y-%m-%d %H:%M:%S")

    for l in self.content:
      s += l + '\n'

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
    self.main_tag = None
    self.tags = {}

    self.load_log_files()
    self.build_indices()
    self.load_tag_hierarchy()

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

          content.append(lines[i].rstrip())
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
    self.log_entries.sort(key=lambda e: e.modified_at)

  def build_indices(self):
    for e in self.log_entries:
      self.log_entries_by_id[int(e.id)] = e
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
        self.log_files_by_date[str(date)] = log_file
    return self.log_files_by_date[str(date)]

  def create_log_entry(self):
    log_file = self.get_current_log_file()

    current_id = None
    with open(os.path.join(data_path, 'id.txt'), 'r') as f:
      current_id = int(f.read().strip())
    with open(os.path.join(data_path, 'id.txt'), 'w') as f:
      f.write(str(int(current_id) + 1))

    # Try to infer tag.
    tag_name = self.get_tags()[0].name

    with open(log_file.get_path(), 'a') as f:
      n = datetime.datetime.now()
      f.write("\n")
      s = "{:08d} ".format(current_id) + "[%s]" % n.strftime("%H:%M:%S")
      s += " (%s)" % tag_name
      f.write(s)

    subprocess.run(
      ['vim', '+normal G$', log_file.get_path()]
    )

  def edit_log_entry(self, entry):
    now = datetime.datetime.now()
    entry.set_modified_time(now)
    entry.log_file.rewrite()

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

  def print_log_entries(self, n):
    n = 10 if (n is None) else n
    for e in reversed(self.log_entries):
      e.print_summarized()
      n -= 1
      if n == 0:
        break

  def get_tags(self):
    tags = list(self.tags.values())
    tags.sort(key=lambda t: t.modified_at, reverse=True)
    return tags

  def print_tag_hierarchy(self, tag=None, indents=0):
    if tag is None:
      tag = self.main_tag

    print('  ' * indents + tag.name)
    for c in tag.children:
      self.print_tag_hierarchy(c, indents + 1)

  def load_tag_hierarchy(self):
    self.main_tag = Tag('main', [])
    stack = [self.main_tag]

    cur_indents = -1
    with open(os.path.join(data_path, 'tags.txt'), 'r') as f:
      for line in f:
        num_spaces = 0
        for i in range(len(line)):
          if line[i] != ' ':
            break
          num_spaces += 1
        num_indents = num_spaces / 2

        tag_name = line[num_spaces:].strip()
        entries = []
        if tag_name in self.log_entries_by_tag:
          entries = self.log_entries_by_tag[tag_name]
        cur_tag = Tag(tag_name, entries)
        self.tags[tag_name] = cur_tag

        while cur_indents >= num_indents:
          stack.pop()
          cur_indents -= 1

        stack[-1].children.append(cur_tag)
        cur_indents = num_indents
        stack.append(cur_tag)
