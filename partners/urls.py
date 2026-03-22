from django.urls import path

from . import views

urlpatterns = [
    path("", views.partner_list, name="partner-list"),
    path("create/", views.partner_create, name="partner-create"),
    path("<int:pk>/", views.partner_detail, name="partner-detail"),
]
