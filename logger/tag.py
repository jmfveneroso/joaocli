import datetime
from logger.util import date_to_str

# Category node that contains log entries.
class Tag:
  def __init__(self, id, name, entries):
    self.id = id
    self.name = name
    self.modified_at = datetime.datetime(year=1970, month=1, day=1)
    self.entries = entries
    self.children = []
    self.parent = None
    self.total_entries = 0

  def add_child(self, child):
    self.children.append(child)

  def add_entry(self, entry):
    self.entries.append(entry)
    parent = self
    while parent is not None:
      parent.total_entries += 1
      if parent.modified_at < entry.modified_at:
        parent.modified_at = entry.modified_at
      parent = parent.parent

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

  def delete_child(self, child_id):
    for i, c in enumerate(self.children):
      if int(c.id) == int(child_id):
        del self.children[i]
        return
    raise Exception('Child with id %d for tag %s does not exist' % 
                    (child_id, self.name))

  def to_json(self):
    return {
      'id': self.id,
      'name': self.name,
      'children': [t.id for t in self.children],
      'entries': [e.id for e in self.get_entries()],
      'total_entries': self.total_entries,
      'modified_at': date_to_str(self.modified_at),
    }

  def print_header(self):
    print('======================================')
    print('%s (%d entries)' %
          (self.name, len(self.entries)))
    print('======================================')

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

