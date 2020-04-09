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
from logger.entry import Entry
from logger.tag import Tag
from logger.util import str_to_date, strip_lines

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
DATA_PATH = os.path.realpath(os.path.join(ROOT_PATH, '../files'))
FILENAME = 'jmfveneroso.txt'
ENTRY_PATTERN = ("^([A-Z])(\d{8}) \[(\d{4}-\d{2}-\d{2} "
                 "\d{2}:\d{2}:\d{2})\|(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")

# Logger class to map entries into a data file.
class Logger:
  def __init__(self):
    self.load()

  def clear(self):
    self.entries_by_id = {}
    self.main_tag = None
    self.tags_by_name = {}
    self.tags_by_id = {}

  def load(self):
    self.clear()
    with open(os.path.join(DATA_PATH, FILENAME)) as f:
      i, lines = 0, f.readlines()
      i = self.load_tags(lines, i)
      i = self.load_entries(lines, i)

  def load_tags(self, lines, i):
    self.main_tag = Tag(0, 'main', [])
    self.tags_by_name['main'] = self.main_tag 
    self.tags_by_id[0] = self.main_tag 

    other_tag = Tag(1, 'other', [])
    self.tags_by_name['other'] = other_tag
    self.tags_by_id[1] = other_tag 
    self.main_tag.add_child(other_tag)

    cur_indents = -1
    stack = [self.main_tag]
    while i < len(lines):
      line = lines[i].rstrip()
      if len(line) == 0:
        break

      num_spaces = 0
      for j in range(len(line)):
        if line[j] != ' ':
          break
        num_spaces += 1
      num_indents = num_spaces / 2

      tag_name, tag_id = line[num_spaces:].strip().split(' ')
      tag_id = int(tag_id)

      if tag_name in self.tags_by_name:
        raise Exception('Duplicate tag %s' % tag_name)

      tag = Tag(tag_id, tag_name, [])
      self.tags_by_name[tag_name] = tag
      self.tags_by_id[tag_id] = tag

      while cur_indents >= num_indents:
        stack.pop()
        cur_indents -= 1

      parent = stack[-1]
      parent.children.append(tag)
      tag.parent = parent
      cur_indents = num_indents
      stack.append(tag)
      i += 1
    return i + 1

  def load_entries(self, lines, i): 
    while i < len(lines):
      match = re.search(ENTRY_PATTERN, lines[i])
      if match is None:
        i += 1
        continue

      entry_id = int(match.group(2))
      created_at = str_to_date(match.group(3))
      modified_at = str_to_date(match.group(4))
      header = lines[i][match.span()[1]:].strip()

      title = ''
      entry_tags = []
      match = re.search("^\([^)]+\)", header)
      if match is None:
        title = header
      else:
        entry_tags = [t.strip() for t in match.group()[1:-1].lower().split('|')]
        title = header[match.span()[1]:]

      i += 1
      line_num = i
      content = []
      while i < len(lines):
        match = re.search(ENTRY_PATTERN, lines[i])
        if match is not None:
          break
        content.append(lines[i].rstrip())
        i += 1
      content = strip_lines(content)

      category = self.tags_by_name['other']
      if len(entry_tags) and entry_tags[0] in self.tags_by_name:
        category = self.tags_by_name[entry_tags[0]]

      entry = Entry(entry_id, created_at, modified_at, title, 
                    category, content, line_num)
      self.entries_by_id[int(entry.id)] = entry
      category.add_entry(entry)
    return i

  def write_tag_hierarchy(self, f, tag=None, indents=0):
    if tag is None:
      tag = self.main_tag
    elif tag.name == 'other':
      return
    else:
      f.write('  ' * indents + tag.name + ' ' + str(tag.id) + '\n')
      indents += 1

    for c in tag.children:
      self.write_tag_hierarchy(f, c, indents)

  def get_next_entry_id(self):
    return max(self.entries_by_id.keys()) + 1

  def get_next_tag_id(self):
    return max(self.tags_by_id.keys()) + 1


  # ==========================
  # Public.
  # ==========================

  def save(self):
    with open(os.path.join(DATA_PATH, FILENAME), 'w') as f:
      self.write_tag_hierarchy(f)
      f.write('\n')
    
      for e in self.get_entries():
        f.write(str(e))


  # ------- Entries --------
  def get_entry_by_id(self, id):
    if id in self.entries_by_id:
      return self.entries_by_id[id]
    raise Exception('Entry with id %d does not exist' % id)

  def get_entries(self):
    entries = list(self.entries_by_id.values())
    entries.sort(key=lambda e: e.modified_at)
    return entries

  def create_entry(self, name, tag_id):
    tag = self.get_tag_by_id(tag_id)
    id = self.get_next_entry_id()
    date = datetime.datetime.now()
    new_entry = Entry(id, date, date, name, tag, [], -1)
    tag.add_entry(new_entry)
    self.entries_by_id[id] = new_entry
    return new_entry

  def delete_entry(self, id):
    entry = self.entries_by_id[id]
    if int(id) in self.entries_by_id:
      del self.entries_by_id[id]
    return entry

  def edit_entry(self, attributes):
    entry = self.get_entry_by_id(int(attributes['id']))
    for attr in attributes:
      if attr == 'tag':
        tag = self.get_tag_by_name(attributes['tag'])
        tag.add_entry(entry)
        
      elif hasattr(entry, attr):
        if not callable(getattr(entry, attr)) and not attr.startswith("__"):
          if attr == 'content':
            entry.content = attributes[attr].split('\n')
          else:
            setattr(entry, attr, attributes[attr])
    self.modified_at = datetime.datetime.now()
    return entry


  # ------- Tags --------
  def get_tag_by_id(self, id):
    if id in self.tags_by_id:
      return self.tags_by_id[id]
    raise Exception('Tag with id %d does not exist' % id)

  def get_tag_by_name(self, name):
    if name in self.tags_by_name:
      return self.tags_by_name[name]
    raise Exception('Tag with name %s does not exist' % name)

  def get_tags(self):
    tags = list(self.tags_by_id.values())
    tags.sort(key=lambda t: t.modified_at, reverse=True)
    return tags

  def create_tag(self, parent_id):
    parent = self.get_tag_by_id(parent_id)
    tag_id = self.get_next_tag_id()
    name = 'new-%d' % tag_id
    tag = Tag(tag_id, name, [])
    tag.parent = parent
    self.tags_by_name[name] = tag
    self.tags_by_id[tag_id] = tag
    parent.children.append(tag)
    return tag 

  def delete_tag(self, id):
    tag = self.get_tag_by_id(id)
    tag.parent.delete_child(id)
    for c in tag.get_child_tags():
      for e in c.entries:
        del self.entries_by_id[e.id]
      del self.tags_by_id[c.id]
      del self.tags_by_name[c.name]
    return tag

  def edit_tag(self, attributes):
    tag = self.get_tag_by_id(int(attributes['id']))
    tag.name = attributes['name'] if 'name' in attributes else tag.name
 
    if 'parent' in attributes and attributes['parent'] and attributes['parent'] != tag.parent.id:
      tag.parent.delete_child(int(attributes['id']))
      new_parent = self.get_tag_by_id(attributes['parent'])
      new_parent.add_child(tag)
    return tag
