import datetime
from logger.util import date_to_str

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

# A document holding text.
class Entry:
  def __init__(self, entry_id, created_at, modified_at, title, category, content, line_num):
    self.id = entry_id
    self.created_at = created_at
    self.modified_at = modified_at
    self.title = title
    self.category = category
    self.content = content
    self.line_num = line_num

  def get_tokens(self):
    tokens = tokenize(self.title)
    for l in self.content:
      tokens += tokenize(l)
    return tokens

  def to_json(self):
    return {
      'id': self.id,
      'title': self.title,
      'content': '\n'.join(self.content),
      'created_at': date_to_str(self.created_at),
      'modified_at': date_to_str(self.modified_at),
      'category': self.category.id,
    }

  def print_header(self, print_tags=True):
    date = self.modified_at if self.modified_at else self.created_at

    if self.modified_at != self.created_at:
      date = str(date) + bcolors.HEADER + ' (created at: %s)' % self.created_at + bcolors.ENDC

    print(
      bcolors.UNDERLINE + ('%08d' % self.id) + bcolors.ENDC,
      date,
      bcolors.OKGREEN + self.title + bcolors.ENDC,
    )

    print(bcolors.OKBLUE + self.category.name + bcolors.ENDC)
    print('')

  def print_detailed(self, print_tags=True):
    self.print_header(print_tags)
    for l in self.content:
      print(l)

  def print_summarized(self, print_tags=True):
    self.print_header(print_tags)
    for l in self.content[:5]:
      print(l)

  def __str__(self):
    s = (
      "K{:08d} ".format(self.id) +
      "[%s|%s] " % (self.created_at.strftime("%Y-%m-%d %H:%M:%S"), 
                    self.modified_at.strftime("%Y-%m-%d %H:%M:%S")) +
      '(' + self.category.name + ') ' + self.title.strip() + "\n"
    )

    s += '\n'
    for l in self.content:
      s += l + '\n'

    if len(self.content) > 0 and len(self.content[-1]):
      s += '\n' 
    return s

