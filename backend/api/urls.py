from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("users/sync/", views.sync_user, name="users-sync"),
    path("me/", views.me, name="me"),
    path("diagnoses/", views.diagnoses_list, name="diagnoses-list"),
    path("diagnoses/<int:pk>/", views.diagnoses_detail, name="diagnoses-detail"),
    path(
        "admin/catalog/plants/",
        views.admin_catalog_plants,
        name="admin-catalog-plants",
    ),
    path(
        "admin/catalog/plants/<int:plant_id>/diseases/",
        views.admin_catalog_plant_diseases,
        name="admin-catalog-plant-diseases",
    ),
    path(
        "admin/catalog/plants/<int:plant_id>/",
        views.admin_catalog_plant_detail,
        name="admin-catalog-plant-detail",
    ),
    path(
        "admin/catalog/diseases/<int:disease_id>/",
        views.admin_catalog_disease_detail,
        name="admin-catalog-disease-detail",
    ),
    path("debug/vision-test/", views.vision_test_page, name="vision-test-page"),
]
