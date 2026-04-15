from django.urls import path

from . import views

urlpatterns = [
    path("", views.partner_list, name="partner-list"),
    path("create/", views.partner_create, name="partner-create"),
    path("<int:pk>/", views.partner_detail, name="partner-detail"),
    path("<int:pk>/export/pdf/", views.partner_export_pdf, name="partner-export-pdf"),
    path("<int:pk>/update/", views.partner_update, name="partner-update"),
    path("<int:pk>/delete/", views.partner_delete, name="partner-delete"),
    # Programs
    path("<int:partner_pk>/programs/add/", views.program_create, name="program-create"),
    path("programs/<int:pk>/", views.program_detail, name="program-detail"),
    path("programs/<int:pk>/update/", views.program_update, name="program-update"),
    path("programs/<int:pk>/delete/", views.program_delete, name="program-delete"),
    # Past Interventions
    path(
        "<int:partner_pk>/interventions/add/",
        views.intervention_create,
        name="intervention-create",
    ),
    path(
        "interventions/<int:pk>/", views.intervention_detail, name="intervention-detail"
    ),
    path(
        "interventions/<int:pk>/update/",
        views.intervention_update,
        name="intervention-update",
    ),
    path(
        "interventions/<int:pk>/delete/",
        views.intervention_delete,
        name="intervention-delete",
    ),
]
