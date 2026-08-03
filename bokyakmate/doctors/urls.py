from django.urls import path
from . import views

app_name = "doctors"

urlpatterns = [
    path("<str:member_id>/patients/", views.patient_list, name="patient_list"),
    path("<str:member_id>/patients/new/", views.patient_create, name="patient_create"),
    path("<str:member_id>/patients/<str:patient_id>/", views.patient_detail, name="patient_detail"),
    path("<str:member_id>/patients/<str:patient_id>/prescriptions/new/",
         views.prescription_create, name="prescription_create"),

    path("<str:member_id>/prescriptions/<str:prescription_id>/",
         views.prescription_detail, name="prescription_detail"),
    path("<str:member_id>/prescriptions/<str:prescription_id>/drugs/new/",
         views.prescription_add_drug, name="prescription_add_drug"),

    path("<str:member_id>/details/<int:detail_id>/dosing/", views.dosing_check, name="dosing_check"),
    path("<str:member_id>/details/<int:detail_id>/side-effect/new/",
         views.side_effect_record, name="side_effect_record"),

    path("<str:member_id>/drugs/", views.drug_info, name="drug_search"),
    path("<str:member_id>/drugs/<str:product_code>/", views.drug_info, name="drug_info"),
]
