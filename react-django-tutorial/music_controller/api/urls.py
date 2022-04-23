from django.urls import path
from . import views

urlpatterns = [
    path('', views.main),
    path('rooms/', views.RoomView.as_view()),
]
