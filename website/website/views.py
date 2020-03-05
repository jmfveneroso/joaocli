from django.shortcuts import render
from django.http import JsonResponse
import jlogger

def index(request):
  logs = jlogger.get_logs()

  response_data = {
    'entries': [
        l.content for l in logs
    ]
  }

  return JsonResponse(response_data)
