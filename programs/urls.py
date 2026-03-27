from django.urls import path

from . import views


urlpatterns = [
    path("", views.area_engagement_list, name="area-engagement-list"),
    path("create/", views.area_engagement_create, name="area-engagement-create"),
    path(
        "engagements/<int:pk>/",
        views.area_engagement_detail,
        name="area-engagement-detail",
    ),
]
