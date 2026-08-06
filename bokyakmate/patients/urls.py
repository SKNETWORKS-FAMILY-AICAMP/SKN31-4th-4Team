from django.urls import path
from . import views

app_name = "patients"

urlpatterns = [
    # 온보딩(최초진입)은 <str:patient_id>/ 패턴과 겹치지 않도록 반드시 그 위에 둔다.
    path("onboarding/start/", views.onboarding_start, name="onboarding_start"),
    path("onboarding/hospital/", views.onboarding_hospital_select, name="onboarding_hospital_select"),
    path("onboarding/auth/", views.onboarding_hospital_auth, name="onboarding_hospital_auth"),
    path("onboarding/loading/", views.onboarding_loading, name="onboarding_loading"),
    path("onboarding/confirm/", views.onboarding_info_confirm, name="onboarding_info_confirm"),
    path("onboarding/health-basic/", views.onboarding_health_basic, name="onboarding_health_basic"),
    path("onboarding/health-additional/", views.onboarding_health_additional, name="onboarding_health_additional"),

    path("<str:patient_id>/", views.patient_main, name="main"),
    path("<str:patient_id>/calendar/", views.dosing_calendar, name="dosing_calendar"),
    path("<str:patient_id>/calendar/<int:log_id>/take/", views.mark_dose_taken, name="mark_dose_taken"),
    path("<str:patient_id>/records/", views.records, name="records"),
    path("<str:patient_id>/chats/", views.chat_history, name="chat_history"),
    path("<str:patient_id>/mypage/", views.mypage, name="mypage"),
    path("<str:patient_id>/chatbot/", views.chatbot_start, name="chatbot_start"),
    path("<str:patient_id>/chatbot/end", views.chatbot_end, name="chatbot_end"),
]
