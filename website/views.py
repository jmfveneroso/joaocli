from django.shortcuts import render
from django.http import JsonResponse
import jlogger
import datetime

def index(request):
  logger = jlogger.Logger()
  log_entries = reversed(logger.log_entries)

  json_entries = []
  for l in log_entries:
    json_entries.append({
        'title': l.title,
        'content': '\n'.join(l.content),
        'created_at': l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        'modified_at': l.modified_at.strftime("%Y-%m-%d %H:%M:%S"),
        'tags': l.tags
    })

  response_data = {
    'entries': json_entries
  }

  return JsonResponse(response_data)
