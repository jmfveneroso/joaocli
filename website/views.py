from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView
from logger import jlogger
import json
import datetime

@ensure_csrf_cookie
def index(request):
  return render(request, "index.html", {})

# Entry API.
def entry(request, entry_id=None):
  body_unicode = request.body.decode('utf-8')
  body = json.loads(body_unicode)
  logger = jlogger.Logger()

  if request.method == 'GET':
    return JsonResponse(logger.entries_by_id[entry_id].to_json())

  elif request.method == 'POST':
    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    e = logger.create_entry(body['title'], body['parent_id'])
    logger.save()
    return JsonResponse(e.to_json())

  elif request.method == 'PUT':
    entry = logger.entries_by_id[int(body['id'])]
    entry.update(body)
    logger.save()
    return JsonResponse({'status': 'ok'})

  elif request.method == 'DELETE':
    l = logger.delete_entry(entry_id)
    logger.save()
    return JsonResponse({'status': 'ok'})

# Tag API.
def tag(request, tag_id=None):
  body_unicode = request.body.decode('utf-8')
  body = json.loads(body_unicode)
  logger = jlogger.Logger()

  if request.method == 'POST':
    tag = logger.create_tag(body['parent'])
    logger.save()
    return JsonResponse(tag.to_json())

  elif request.method == 'PUT':
    logger.edit_tag(body)
    logger.save()
    return JsonResponse({ 'status': 'ok' })

  elif request.method == 'DELETE':
    logger.delete_tag(body['id'])
    logger.save()
    return JsonResponse({'status': 'ok'})

def all(request):
  logger = jlogger.Logger()
  return JsonResponse({
    'tags': [t.to_json() for t in logger.get_tags()],
    'entries': [e.to_json() for e in logger.get_entries()],
  })

