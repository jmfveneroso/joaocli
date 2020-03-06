from django.shortcuts import render
from django.http import JsonResponse
import jlogger

def index(request):
  logger = jlogger.Logger()
  log_entries = reversed(logger.log_entries)

  json_entries = []
  for l in log_entries:
    json_entries.append({'title': l.title, 'content': '\n'.join(l.content)})

  response_data = {
    'entries': json_entries
  }

  return JsonResponse(response_data)
