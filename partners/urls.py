from django.urls import path

from . import views

urlpatterns = [
    path("", views.partner_list, name="partner-list"),
    path("bulk-import/", views.partner_bulk_import, name="partner-bulk-import"),
    path(
        "bulk-import/template/",
        views.partner_bulk_import_template_download,
        name="partner-bulk-import-template",
    ),
    path("create/", views.partner_create, name="partner-create"),
    path("<int:pk>/", views.partner_detail, name="partner-detail"),
    path("<int:pk>/export/pdf/", views.partner_export_pdf, name="partner-export-pdf"),
    path("<int:pk>/update/", views.partner_update, name="partner-update"),
    path("<int:pk>/delete/", views.partner_delete, name="partner-delete"),
    # Needs Repository
    path("<int:partner_pk>/needs/add/", views.need_create, name="need-create"),
    path("needs/<int:pk>/", views.need_detail, name="need-detail"),
    path("needs/<int:pk>/update/", views.need_update, name="need-update"),
    path("needs/<int:pk>/delete/", views.need_delete, name="need-delete"),
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
