from django.urls import path

from . import views


urlpatterns = [
    path("data-tables", views.managed_table_list),
    path("data-tables/<str:table_name>/schema", views.managed_table_schema),
    path("data-tables/<str:table_name>/relations/<str:column_name>/options", views.managed_table_relation_options),
    path("data-tables/<str:table_name>/rows", views.managed_table_rows),
    path("data-tables/<str:table_name>/rows/create", views.managed_table_row_create),
    path("data-tables/<str:table_name>/rows/batch-delete", views.managed_table_batch_delete),
    path("data-tables/<str:table_name>/template/download", views.managed_table_template),
    path("data-tables/<str:table_name>/import", views.managed_table_import),
    path("data-tables/<str:table_name>/rows/<str:row_id>", views.managed_table_row_detail),
    path("companies", views.company_list),
    path("companies/create", views.company_create),
    path("companies/batch-delete", views.company_batch_delete),
    path("companies/template/download", views.company_template_download),
    path("companies/import", views.company_import),
    path("companies/<str:identifier>", views.company_detail),
]
