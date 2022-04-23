from django.http import HttpResponse
from rest_framework import generics
from . import models, serializers


def main(request):
    return HttpResponse("<h1>Hello Django App!</h1>")


class RoomView(generics.ListAPIView):
    queryset = models.Room.objects.all()
    serializer_class = serializers.RoomSerializer