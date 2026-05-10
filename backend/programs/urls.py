from django.urls import path
from . import views

urlpatterns = [
    path("mapper-stats/", views.mapper_stats, name="mapper_stats"),
]
