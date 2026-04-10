from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("users/sync/", views.sync_user, name="users-sync"),
    path("me/", views.me, name="me"),
    path("diagnoses/", views.diagnoses_list, name="diagnoses-list"),
    path("diagnoses/<int:pk>/", views.diagnoses_detail, name="diagnoses-detail"),
]
