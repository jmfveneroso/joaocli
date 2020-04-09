from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView
from rest_framework import routers, serializers, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView

from logger import jlogger
import json
import datetime

@ensure_csrf_cookie
def index(request):
  return render(request, "index.html", {})


class EntrySerializer(serializers.Serializer):
  id = serializers.IntegerField(read_only=True)
  title = serializers.CharField(max_length=256)
  created_at = serializers.CharField(max_length=256)
  modified_at = serializers.CharField(max_length=256)
  category = serializers.IntegerField(read_only=True)
  content = serializers.CharField(max_length=999999)

class EntryViewSet(APIView):
  serializer_class = EntrySerializer

  def list(self, request):
    logger = jlogger.Logger()
    entries = [e.to_json() for e in logger.get_entries()]
    serializer = EntrySerializer(
      instance=entries, many=True)
    return Response(serializer.data)

  def post(self, request):
    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    logger = jlogger.Logger()
    e = logger.create_entry(body['title'], body['parent_id'])
    logger.save()
    serializer = EntrySerializer(instance=e.to_json())
    return Response(serializer.data)

  def patch(self, request):
    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    logger = jlogger.Logger()
    e = logger.edit_entry(body)
    logger.save()
    serializer = EntrySerializer(instance=e.to_json())
    return Response(serializer.data)

  def delete(self, request, pk=None):
    logger = jlogger.Logger()
    e = logger.delete_entry(int(pk))
    logger.save()
    serializer = EntrySerializer(instance=e.to_json())
    return Response(serializer.data)


class TagSerializer(serializers.Serializer):
  id = serializers.IntegerField(read_only=True)
  name = serializers.CharField(max_length=256)
  modified_at = serializers.CharField(max_length=256)
  children = serializers.ListField(
    child=serializers.IntegerField(min_value=0, max_value=999999)
  )
  total_entries = serializers.IntegerField(read_only=True)

class TagViewSet(APIView):
  serializer_class = TagSerializer

  def list(self, request):
    logger = jlogger.Logger()
    tags = [t.to_json() for t in logger.get_tags()]
    serializer = TagSerializer(
      instance=tags, many=True)
    return Response(serializer.data)

  def post(self, request):
    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    logger = jlogger.Logger()
    tag = logger.create_tag(body['parent'])
    logger.save()
    serializer = TagSerializer(instance=tag.to_json())
    return Response(serializer.data)

  def patch(self, request):
    body_unicode = request.body.decode('utf-8')
    body = json.loads(body_unicode)
    logger = jlogger.Logger()
    tag = logger.edit_tag(body)
    logger.save()
    serializer = TagSerializer(instance=tag.to_json())
    return Response(serializer.data)

  def delete(self, request, pk=None):
    logger = jlogger.Logger()
    tag = logger.delete_tag(int(pk))
    logger.save()
    serializer = TagSerializer(instance=tag.to_json())
    return Response(serializer.data)


def all(request):
  logger = jlogger.Logger()
  return JsonResponse({
    'tags': [t.to_json() for t in logger.get_tags()],
    'entries': [e.to_json() for e in logger.get_entries()],
  })

