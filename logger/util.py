import datetime

DATE_PATTERN = "%Y-%m-%d %H:%M:%S"

def date_to_str(date):
  return date.strftime(DATE_PATTERN)

def str_to_date(s):
  return datetime.datetime.strptime(s, DATE_PATTERN)

def strip_lines(lines):
  if len(lines) > 0 and len(lines[0]) == 0:
    lines = lines[1:]
  if len(lines) > 0 and len(lines[-1]) == 0:
    lines = lines[:-1]
  return lines
