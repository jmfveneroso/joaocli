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

# Category node that contains log entries.
class Tag:
  def __init__(self, id, name, entries):
    self.id = id
    self.name = name
    self.entries = entries

    self.created_at = datetime.datetime(year=1970, month=1, day=1)
    self.modified_at = datetime.datetime(year=1970, month=1, day=1)

    self.common_words = []
    self.children = []
    self.parent = None
    self.total_entries = 0

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

    entries.sort(key=lambda e: e.modified_at, reverse=True)
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
      dt = datetime.datetime.strftime(e.created_at, "%Y-%m-%d %H:%M:%S")
    print('%s: %d (%s)' % (self.name, len(self.entries), dt))

  def print_detailed(self):
    tags = self.get_child_tags()

    for t in tags:
      print('============================================')
      t.print_snippet()
      print('============================================')
      for e in t.entries:
        e.print_detailed()

  def add_entry(self, entry):
    self.entries.append(entry)
    if self.created_at < entry.created_at:
      self.created_at = entry.created_at
    if self.modified_at < entry.modified_at:
      self.modified_at = entry.modified_at

# A document holding text.
class Entry:
  def __init__(self, entry_id, created_at, modified_at, title, tags, content):
    self.id = entry_id
    self.created_at = created_at
    self.modified_at = modified_at
    self.title = title
    self.tags = tags
    self.content = content

  def set_modified_time(self, modified_at):
    self.modified_at = modified_at

  def print_header(self, print_tags=True):
    date = self.modified_at if self.modified_at else self.created_at

    if self.modified_at != self.created_at:
      date = str(date) + bcolors.HEADER + ' (created at: %s)' % self.created_at + bcolors.ENDC

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
      tags = '(' + '|'.join(self.tags) + ') '

    s = (
      "K{:08d} ".format(self.id) +
      "[%s|%s] " % (self.created_at.strftime("%Y-%m-%d %H:%M:%S"), self.modified_at.strftime("%Y-%m-%d %H:%M:%S")) +
      tags + self.title.strip() + "\n"
    )

    s += '\n'
    for l in self.content:
      s += l + '\n'

    if len(self.content) > 0 and len(self.content[-1]):
      s += '\n' 
    return s


# A document holding text.
class Logger:
  def __init__(self):
    self.log_files = []
    self.log_entries = []
    self.log_entries_by_id = {}
    self.log_entries_by_title = {}
    self.log_entries_by_tag = {}
    self.main_tag = None
    self.tags = {}

    self.read_entries('jmfveneroso.txt')
    self.build_indices()

  def build_indices(self):
    for e in self.log_entries:
      if e.id in self.log_entries_by_id:
        print(e.id)
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

  def get_current_id(self):
    max_id = 0
    for e in self.log_entries:
      max_id = max(max_id, e.id)
    return max_id + 1

  def create_log_entry(self):
    filename = os.path.join(data_path, 'jmfveneroso.txt')

    entry_id = self.get_current_id()
    date = datetime.datetime.now()
    new_entry = Entry(entry_id, date, date, '', [], [])
    with open(filename, 'a') as f:
      f.write(str(new_entry))

    subprocess.run(['vim', '+normal G$', filename])

  def add_log_entry(self, parent_id, name, date):
    tag = self.get_tag(parent_id)

    entry_id = self.get_current_id()
    new_entry = Entry(entry_id, date, date, name, [], [])
    new_entry.tags.append(tag.name)
    tag.add_entry(new_entry)

    self.log_entries.append(new_entry)
    self.log_entries_by_id[entry_id] = new_entry

    if not tag.name in self.log_entries_by_tag:
      self.log_entries_by_tag[tag.name] = []

    self.log_entries_by_tag[tag.name].append(new_entry)
    return new_entry

  def delete_log_entry(self, entry_id):
    for i, e in enumerate(self.log_entries):
      if int(e.id) == int(entry_id):
        del self.log_entries[i]
        break

  def edit_log_entry(self, entry):
    entry.set_modified_time(datetime.datetime.now())
    self.write_entries()

    filename = os.path.join(data_path, 'jmfveneroso.txt')
    if not os.path.isfile(filename):
      raise ValueError(filename + ' does not exist')

    line_num = 1
    pattern = "^([A-Z])(\d{8}) \[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\|(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]"
    with open(filename, 'r') as f:
      for l in f:
        match = re.search(pattern, l)
        if match:
          entry_id = int(match.group(2))
          if entry_id == entry.id:
            break
        line_num += 1

    subprocess.run(['vim', '+normal %dgg$' % line_num, filename])

  def replace_log_entry(self, entry):
    log_file = entry.log_file
    log_file.remove_entry(entry)
    log_file.rewrite()

    log_file = self.get_current_log_file()
    now = datetime.datetime.now()
    entry.created_at = datetime.datetime.strptime(
            '%s %s' % (log_file.date, now.strftime("%H:%M:%S")),
            "%Y-%m-%d %H:%M:%S")

    current_id = None
    with open(os.path.join(data_path, 'id.txt'), 'r') as f:
      current_id = int(f.read().strip())
    with open(os.path.join(data_path, 'id.txt'), 'w') as f:
      f.write(str(int(current_id) + 1))

    entry.id = current_id
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
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(data_path, 'chrono.txt'), 'a') as f:
      f.write(date + ' ' + chrono_type + ' ' + chrono_name + '\n')

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

    print('  ' * indents + tag.name + ' ' + str(tag.total_entries))
    for c in tag.children:
      self.print_tag_hierarchy(c, indents + 1)

  def fill_tag_stats(self):
    new_tag = Tag(9999, 'other', [])
    self.main_tag.children.append(new_tag)
    for e in self.log_entries:
      if len(e.tags) == 0:
        new_tag.add_entry(e)
    self.tags['other'] = new_tag

    for key, tag in self.tags.items():
      entries = tag.get_entries()
      tag.total_entries = len(entries)

      if len(entries) > 0:
        tag.created_at = entries[0].created_at
        tag.modified_at = entries[0].modified_at

  def get_main_tags(self):
    return self.main_tag.children

  def file_print_tag_hierarchy(self, f, tag=None, indents=0):
    if tag is None:
      tag = self.main_tag
    elif tag.name == 'other':
      return
    else:
      f.write('  ' * indents + tag.name + ' ' + str(tag.id) + '\n')
      # print('  ' * indents + tag.name + ' ' + str(tag.id) + '\n')
      indents += 1

    for c in tag.children:
      self.file_print_tag_hierarchy(f, c, indents)

  def load_tags(self, lines):
    self.main_tag = Tag(0, 'main', [])
    stack = [self.main_tag]
    self.tags['main'] = self.main_tag 

    cur_indents = -1
    for line in lines:
      num_spaces = 0
      for i in range(len(line)):
        if line[i] != ' ':
          break
        num_spaces += 1
      num_indents = num_spaces / 2

      tag_name, tag_id = line[num_spaces:].strip().split(' ')
      tag_id = int(tag_id)
      entries = []
      if tag_name in self.log_entries_by_tag:
        entries = self.log_entries_by_tag[tag_name]

      cur_tag = Tag(tag_id, tag_name, entries)
      self.tags[tag_name] = cur_tag

      while cur_indents >= num_indents:
        stack.pop()
        cur_indents -= 1

      stack[-1].children.append(cur_tag)
      cur_tag.parent = stack[-1]
      cur_indents = num_indents
      stack.append(cur_tag)

  def read_entries(self, filename): 
    self.log_entries = []
    with open(os.path.join(data_path, filename)) as f:
      i, lines = 0, f.readlines()

      tag_lines = []
      while i < len(lines):
        line = lines[i].rstrip()
        if len(line) == 0:
          i += 1
          break
        tag_lines.append(line)
        i += 1
      print(tag_lines)
      self.load_tags(tag_lines)

      pattern = "^([A-Z])(\d{8}) \[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\|(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]"
      while i < len(lines):
        match = re.search(pattern, lines[i])
        if match is None:
          i += 1
          continue

        entry_id = int(match.group(2))
        created_at = match.group(3)
        modified_at = match.group(4)
        header = lines[i][match.span()[1]:].strip()

        created_at = datetime.datetime.strptime('%s' % created_at, "%Y-%m-%d %H:%M:%S")
        modified_at = datetime.datetime.strptime('%s' % modified_at, "%Y-%m-%d %H:%M:%S")

        title = ''
        tags = []
        match = re.search("^\([^)]+\)", header)
        if match is None:
          title = header
        else:
          tags = match.group()[1:-1].lower().split('|')
          tags = [t.strip() for t in tags]
          title = header[match.span()[1]:]

        content = []
        i += 1
        while i < len(lines):
          match = re.search(pattern, lines[i])
          if match is not None:
            break

          content.append(lines[i].rstrip())
          i += 1

        if len(content) > 0 and len(content[0]) == 0:
          content = content[1:]

        if len(content) > 0 and len(content[-1]) == 0:
          content = content[:-1]

        new_entry = Entry(entry_id, created_at, modified_at, title, tags, content)
        for t in tags:
          if t in self.tags:
            self.tags[t].add_entry(new_entry)
        self.log_entries.append(new_entry)
    self.log_entries.sort(key=lambda e: e.modified_at)
    self.fill_tag_stats()

  def write_entries(self):
    with open(os.path.join(data_path, 'jmfveneroso.txt'), 'w') as f:
      self.file_print_tag_hierarchy(f)
      f.write('\n')
    
      for e in self.log_entries:
        f.write(str(e))

  def add_tag(self, parent_id):
    parent = None
    next_tag_id = -1
    for t in self.tags.values():
      if t.name == 'other':
        continue
      next_tag_id = max(next_tag_id, t.id)
      if t.id == parent_id:
        parent = t

    next_tag_id += 1
    name = 'new-%d' % next_tag_id
    new_tag = Tag(next_tag_id, name, [])
    new_tag.parent = parent
    self.tags[name] = new_tag
    parent.children.append(new_tag)
    return new_tag 

  def delete_tag(self, id):
    tag = None
    for t in self.tags.values():
      if t.id == int(id):
        tag = t
        break
 
    for i, c in enumerate(tag.parent.children):
      if int(c.id) == int(id):
        del tag.parent.children[i]
        break

    del self.tags[tag.name]

  def get_tag(self, id):
    for t in self.tags.values():
      if t.id == int(id):
        return t

  def edit_tag(self, id, name, parent_id=None):
    tag = None
    for t in self.tags.values():
      if t.id == int(id):
        tag = t
        break

    for e in self.log_entries:
      for i, t in enumerate(e.tags):
        if t == tag.name:
          e.tags[i] = name
          break

    if parent_id:
      for i, c in enumerate(tag.parent.children):
        if int(c.id) == int(id):
          del tag.parent.children[i]
          break

      for t in self.tags.values():
        if t.id == int(parent_id):
          t.children.append(tag)
          break
 
    del self.tags[tag.name]
    tag.name = name
    self.tags[tag.name] = tag
