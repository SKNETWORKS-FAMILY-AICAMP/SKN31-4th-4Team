"""
patients/templatetags/patient_tags.py

하단 네비게이션(홈/캘린더/기록/마이) "함수"

사용법 (필요한 템플릿 맨 위에):
    {% load patient_tags %}

바 넣을 위치에:
    {% bottom_nav "home" %}       
    {% bottom_nav "calendar" %}
    {% bottom_nav "records" %}
    {% bottom_nav "mypage" %}
    {% bottom_nav "chat" %}       
"""
from django import template
from django.urls import reverse

register = template.Library()

@register.inclusion_tag("patients/_bottom_nav.html", takes_context=True)
def bottom_nav(context, active_tab=""):
    request = context["request"]
    patient = getattr(request.user, "Patient", None)
    if patient is None:
        return {
            "main_url": "", "calendar_url": "", "records_url": "",
            "mypage_url": "", "active_tab": active_tab,
        }
    patient_id = patient.patient_id

    return {
        "main_url": reverse("patients:main", args=[patient_id]),
        "calendar_url": reverse("patients:dosing_calendar", args=[patient_id]),
        "records_url": reverse("patients:records", args=[patient_id]),
        "mypage_url": reverse("patients:mypage", args=[patient_id]),
        "active_tab": active_tab,
    }