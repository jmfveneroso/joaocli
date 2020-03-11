from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView
import jlogger
import json
import datetime

@ensure_csrf_cookie
def index(request):
  c = {}
  # context = RequestContext(request)
  return render(request, "index.html", c)

def logs(request):
  logger = jlogger.Logger()
  log_entries = reversed(logger.log_entries)

  json_entries = []
  for l in log_entries:
    json_entries.append({
        'id': l.id,
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

def entry(request, entry_id):
  if request.method == 'POST':
    # Parse request parameters.
    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    entry_id = body['id']
    content = body['content']

    # Update log entry.
    logger = jlogger.Logger()
    l = logger.log_entries_by_id[int(entry_id)]
    now = datetime.datetime.now()
    l.set_modified_time(now)
    l.content = content.split('\n')
    l.log_file.rewrite()

    return JsonResponse({'status': 'ok'})

  else:
    logger = jlogger.Logger()
    l = logger.log_entries_by_id[entry_id]

    json_data = {
      'id': l.id,
      'title': l.title,
      'content': '\n'.join(l.content),
      'created_at': l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
      'modified_at': l.modified_at.strftime("%Y-%m-%d %H:%M:%S"),
      'tags': l.tags
    }

    response_data = {
      'entry': json_data
    }

    return JsonResponse(response_data)
