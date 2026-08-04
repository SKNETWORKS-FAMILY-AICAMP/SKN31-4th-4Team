"""
patients/views.py

목업 HTML에서 하드코딩했던 값(하린님/로나센정4mg/34세 등)을
전부 실제 DB 조회로 바꾼다. quick_cards의 url은 여기서 reverse()로
미리 계산해서 넘긴다 (템플릿 안에서 URL 이름을 문자열로 조합하는 건
불안정한 패턴이라 피한다).
"""
import calendar
from datetime import date

from django.contrib.auth import login  # [추가] 온보딩 완료/재로그인 분기에서 로그인 처리에 사용
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone

from .models import (
    Patient, ChatSession, Prescription, PrescriptionDetail,
    DosingLog,SymptomLog, Hospital
)


def _check_owner(request, patient_id):
    """로그인한 사용자가 이 환자 본인인지 확인 (다른 환자 URL을 직접 쳐서 못 들어가게)."""
    # [수정] Patient.user의 related_name은 "patient_profile"이 아니라 "patient"다.
    patient_profile = getattr(request.user, "patient", None)
    return request.user.is_authenticated and patient_profile \
        and patient_profile.patient_id == patient_id


@login_required
def patient_main(request, patient_id):
    patient = get_object_or_404(Patient, patient_id=patient_id)

    latest_prescription = (
        Prescription.objects.filter(patient=patient)
        .prefetch_related("details__drug")
        .first()
    )
    current_drug = None
    if latest_prescription and latest_prescription.details.exists():
        current_drug = latest_prescription.details.first().drug

    recent_chats = ChatSession.objects.filter(patient=patient)[:3]

    # 오늘의 복약 위젯
    today = timezone.localdate()
    todays_logs = DosingLog.objects.filter(patient=patient, scheduled_at__date=today) \
        .select_related("prescription_detail__drug")
    today_doses = [
        {
            "id": log.id,
            "drug_name": log.prescription_detail.drug.drug_name,
            "checked": log.status == "done",
            "missed": log.status == "missed",
        }
        for log in todays_logs
    ]
    all_doses_done = bool(today_doses) and all(d["checked"] for d in today_doses)

    quick_cards = [
        {"icon": "📅", "label": "복약 캘린더", "desc": "오늘 복용 체크하기", "color": "mint",
         "url": reverse("patients:dosing_calendar", args=[patient_id])},
        {"icon": "🏥", "label": "병원 방문 기록", "desc": "지난 진료 확인", "color": "peach",
         "url": reverse("patients:records", args=[patient_id]) + "?tab=visits"},
        {"icon": "📋", "label": "처방받은 약", "desc": "현재 복용 약 목록", "color": "butter",
         "url": reverse("patients:records", args=[patient_id]) + "?tab=prescriptions"},
        {"icon": "💬", "label": "상담 히스토리", "desc": "지난 상담 요약 보기", "color": "lavender",
         "url": reverse("patients:chat_history", args=[patient_id])},
    ]

    context = {
        "patient": patient,
        "current_drug": current_drug,
        "recent_chats": recent_chats,
        "quick_cards": quick_cards,
        "today_doses": today_doses,
        "all_doses_done": all_doses_done,
        "calendar_url": reverse("patients:dosing_calendar", args=[patient_id]),
        "records_url": reverse("patients:records", args=[patient_id]),
        "mypage_url": reverse("patients:mypage", args=[patient_id]),
        "chatbot_url": reverse("patients:chatbot_start", args=[patient_id]),
    }
    return render(request, "patients/patient_main.html", context)


@login_required
def dosing_calendar(request, patient_id):
    """복약 캘린더 — 이번 달 그리드 + 날짜별 복용상태 표시 + 오늘 복용 체크 액션."""
    patient = get_object_or_404(Patient, patient_id=patient_id)

    today = timezone.localdate()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    logs = DosingLog.objects.filter(
        patient=patient, scheduled_at__year=year, scheduled_at__month=month
    ).select_related("prescription_detail__drug")

    # 날짜별로 그 날의 복용상태를 모은다 (하루에 여러 건이면 '모두 완료'일 때만 done)
    status_by_day = {}
    for log in logs:
        day = log.scheduled_at.day
        status_by_day.setdefault(day, []).append(log.status)

    def day_status(statuses):
        if all(s == "done" for s in statuses):
            return "done"
        if any(s == "missed" for s in statuses):
            return "missed"
        return "pending"

    cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
    weeks = []
    for week in cal.monthdayscalendar(year, month):
        week_cells = []
        for day in week:
            if day == 0:
                week_cells.append(None)
            else:
                statuses = status_by_day.get(day)
                week_cells.append({
                    "day": day,
                    "status": day_status(statuses) if statuses else "none",
                    "is_today": date(year, month, day) == today,
                })
        weeks.append(week_cells)

    todays_logs = DosingLog.objects.filter(patient=patient, scheduled_at__date=today) \
        .select_related("prescription_detail__drug")

    prev_month = (date(year, month, 1) - timezone.timedelta(days=1))
    next_month_date = date(year, month, 28) + timezone.timedelta(days=7)
    next_month_date = next_month_date.replace(day=1)

    context = {
        "patient": patient,
        "weeks": weeks,
        "year": year,
        "month": month,
        "todays_logs": todays_logs,
        "prev_url": f"?year={prev_month.year}&month={prev_month.month}",
        "next_url": f"?year={next_month_date.year}&month={next_month_date.month}",
        "main_url": reverse("patients:main", args=[patient_id]),
    }
    return render(request, "patients/dosing_calendar.html", context)


@login_required
def mark_dose_taken(request, patient_id, log_id):
    """복약 체크 액션 (POST) — 오늘의 복약 리스트에서 '복용했어요' 버튼.
    ?next=main 이면 홈으로, 없으면 기존처럼 캘린더로 돌아간다."""
    if request.method == "POST":
        log = get_object_or_404(DosingLog, id=log_id, patient__patient_id=patient_id)
        log.status = "done"
        log.taken_at = timezone.now()
        log.save()
    if request.GET.get("next") == "main":
        return redirect("patients:main", patient_id=patient_id)
    return redirect("patients:dosing_calendar", patient_id=patient_id)


@login_required
def records(request, patient_id):
    """기록 — 처방 기록/병원 방문 기록을 탭으로 묶어서 보여준다."""
    patient = get_object_or_404(Patient, patient_id=patient_id)
    active_tab = request.GET.get("tab", "prescriptions")

    prescriptions = (
        Prescription.objects.filter(patient=patient)
        .prefetch_related("details__drug")
    )

    context = {
        "patient": patient,
        "active_tab": active_tab,
        "prescriptions": prescriptions,
        "main_url": reverse("patients:main", args=[patient_id]),
    }
    return render(request, "patients/records.html", context)


@login_required
def mypage(request, patient_id):
    """마이페이지 - 기저질환/알레르기 등을 note에 저장"""

    patient = get_object_or_404(Patient, patient_id=patient_id)

    if request.method == "POST":
        patient.is_pregnant = request.POST.get("is_pregnant") == "on"

        conditions = request.POST.getlist("conditions")
        allergies = request.POST.getlist("allergies")
        etc = request.POST.get("etc", "").strip()

        notes = []

        if conditions:
            notes.append(f"기저질환: {', '.join(conditions)}")

        if allergies:
            notes.append(f"알레르기: {', '.join(allergies)}")

        if etc:
            notes.append(f"기타: {etc}")

        patient.note = "\n".join(notes)
        patient.save()

        return redirect("patients:mypage", patient_id=patient_id)

    context = {
        "patient": patient,
        "main_url": reverse("patients:main", args=[patient_id]),
    }

    return render(request, "patients/mypage.html", context)


@login_required
def chat_history(request, patient_id):
    patient = get_object_or_404(Patient, patient_id=patient_id)
    chats = ChatSession.objects.filter(patient=patient)
    return render(request, "patients/chat_history.html", {
        "patient": patient, "chats": chats,
        "main_url": reverse("patients:main", args=[patient_id]),
    })


@login_required
def chatbot_start(request, patient_id):
    """실제 챗봇 파이프라인(pipeline.py) 연동은 다음 라운드.
    지금은 화면 확인용으로 두 상태를 보여준다:
      ?state=chat  -> 대화가 진행된 상태(데모 메시지+근거)
      기본값        -> 최초진입 상태(추천 질문 카드)
    """
    patient = get_object_or_404(Patient, patient_id=patient_id)

    messages = []
    if request.GET.get("state") == "chat":
        messages = [
            {"role": "patient", "content": "콘서타 먹고 나서 머리가 좀 아파요"},
            {
                "role": "assistant",
                "content": "말씀하신 약(콘서타)의 이상반응에 두통이 보고되어 있어요(0.6%). "
                           "증상이 심하거나 계속되면 의료진과 상담해주세요.",
                "citations": [
                    {"source_label": "사용상의주의사항 · 4. 이상반응",
                     "snippet": "위약 투여한 환자 중 두통 및 불면증 사례가 보고됨(0.6%)"},
                ],
            },
        ]

    return render(request, "patients/chatbot.html", {
        "patient": patient,
        "messages": messages,
        "main_url": reverse("patients:main", args=[patient_id]),  # 상단 뒤로가기용, 하단바와 별개
    })


# ------------------------------------------------------------------
# 온보딩 (최초진입) — 명세서의 "최초진입" 구간 7화면
#
# [변경] 이제 실제로 전화번호+환자 고유코드로 Patient를 조회해서 인증한다 (더미 통과 아님).
# [추가] 인증 성공 직후, DB에 저장된 건강정보(키/몸무게)가 이미 있는지로 분기한다.
#   - 이미 있음(재로그인/기존 환자)  -> 건강정보 입력 화면들을 건너뛰고 바로 로그인 후 메인으로
#   - 아직 없음(최초 로그인/신규 환자) -> 기존 순서(로딩→확인→건강정보 기본→추가)대로 입력받음
#
# "건강정보가 있다"의 판단 기준은 별도 완료 플래그 컬럼을 추가하는 대신,
# 실제 저장되는 값인 Patient.height_cm / weight_kg가 채워져 있는지로 본다
# (아래 _has_health_info 참고). 이 두 값은 onboarding_health_basic에서 저장된다.
# ------------------------------------------------------------------


def _has_health_info(patient):
    """[추가] DB 기준으로 이 환자가 건강정보(키/몸무게)를 이미 입력했는지 판단.
    별도 '완료 여부' 컬럼을 두지 않고, 건강정보 입력 화면(health_basic)에서
    실제로 저장하는 키/몸무게가 둘 다 채워져 있는지로 판단한다."""
    return patient.height_cm is not None and patient.weight_kg is not None


def _get_onboarding_patient_id(request):
    """온보딩 인증 단계(onboarding_hospital_auth)에서 세션에 저장해둔
    인증된 환자 id를 꺼낸다."""
    return request.session.get("patient_id")


def onboarding_start(request):
    return render(request, "patients/onboarding_start.html")


def onboarding_hospital_select(request):
    from .models import Hospital
    hospitals = Hospital.objects.all()

    if request.method == "POST":
        hospital_code = request.POST.get("hospital_code")
        request.session["onboarding_hospital_code"] = hospital_code
        return redirect("patients:onboarding_hospital_auth")

    return render(request, "patients/onboarding_hospital_select.html", {"hospitals": hospitals})


def onboarding_hospital_auth(request):
    from .models import Hospital

    hospital_code = request.session.get("onboarding_hospital_code")
    selected_hospital = Hospital.objects.filter(
        hospital_code=hospital_code
    ).first()

    if request.method == "POST":
        phone = request.POST.get("phone","").strip()
        patient_code = request.POST.get("patient_code","").strip()

        patient = Patient.objects.filter(
            phone=phone,
            patient_id=patient_code,
            hospital=selected_hospital
        ).first()

        if not patient:
            return render(
                request,
                "patients/onboarding_hospital_auth.html",
                {
                    "selected_hospital": selected_hospital,
                    "error": "전화번호 또는 환자코드가 일치하지 않습니다."
                }
            )

        # Session 저장
        request.session["patient_id"] = patient.patient_id

        # ========== [추가] 여기가 핵심 분기 지점 ==========
        # DB에 건강정보(키/몸무게)가 이미 있는 환자면 건강정보 입력 화면들을
        # 전부 건너뛰고 바로 로그인 처리 후 메인 화면으로 이동시킨다.
        if _has_health_info(patient):
            login(request, patient.user)
            request.session.pop("onboarding_hospital_code", None)
            request.session.pop("patient_id", None)
            return redirect("patients:main", patient_id=patient.patient_id)
        # ========== [추가] 분기 끝 ==========

        # 건강정보가 아직 없는 환자(최초 로그인) -> 기존 온보딩 순서 그대로 진행
        return redirect("patients:onboarding_loading")

    return render(
        request,
        "patients/onboarding_hospital_auth.html",
        {
            "selected_hospital": selected_hospital,
        }
    )


def onboarding_loading(request):
    from .models import Hospital

    hospital_code = request.session.get("onboarding_hospital_code")
    patient_id = _get_onboarding_patient_id(request)

    selected_hospital = Hospital.objects.filter(
        hospital_code=hospital_code
    ).first()

    patient = Patient.objects.filter(
        patient_id=patient_id
    ).first()

    return render(request, "patients/onboarding_loading.html", {
        "selected_hospital": selected_hospital,
        "patient_name": patient.name if patient else "",
        "step": 3,
    })

def onboarding_info_confirm(request):
    from .models import Hospital

    hospital_code = request.session.get("onboarding_hospital_code")
    patient_id = _get_onboarding_patient_id(request)

    selected_hospital = Hospital.objects.filter(
        hospital_code=hospital_code
    ).first()

    patient = get_object_or_404(
        Patient,
        patient_id=patient_id
    )

    if request.method == "POST":
        return redirect("patients:onboarding_health_basic")

    return render(request, "patients/onboarding_info_confirm.html", {
        "patient": patient,
        "selected_hospital": selected_hospital,
    })


def onboarding_health_basic(request):
    # [변경] 세션에 저장된 인증 환자를 조회해서 실제로 키/몸무게를 저장하도록 구현
    # (기존엔 TODO만 있고 저장을 안 해서, 값을 입력해도 DB에는 안 남아 매번 다시
    #  건강정보 입력 화면으로 오게 되는 문제가 있었다)
    patient = get_object_or_404(Patient, patient_id=_get_onboarding_patient_id(request))

    if request.method == "POST":
        # ========== [추가] 키/몸무게를 실제 Patient에 저장 ==========
        height_cm = request.POST.get("height_cm")
        weight_kg = request.POST.get("weight_kg")
        if height_cm:
            patient.height_cm = height_cm
        if weight_kg:
            patient.weight_kg = weight_kg
        patient.save()
        # ========== [추가] 끝 ==========
        return redirect("patients:onboarding_health_additional")
    return render(request, "patients/onboarding_health_basic.html")


def onboarding_health_additional(request):
    # [변경] 정의되지 않은 _DEMO_PATIENT_ID를 참조하던 버그 수정.
    # 세션에 저장해둔 실제 인증 환자 id를 사용한다.
    patient = get_object_or_404(Patient, patient_id=_get_onboarding_patient_id(request))

    if request.method == "POST":
        # ========== [추가] 임신 여부 저장 (여성 환자에게만 폼에 노출됨) ==========
        if patient.gender == "F":
            patient.is_pregnant = request.POST.get("is_pregnant") == "on"
            patient.save()
        # 기저질환(conditions)은 코드가 아니라 한글명이 그대로 넘어오고 있어
        # 별도 정리가 필요함 -> 기존 TODO 그대로 유지 (이번 작업 범위 밖)

        login(request, patient.user)  # 온보딩(=건강정보 입력) 완료 -> 로그인 처리
        request.session.pop("onboarding_hospital_code", None)
        request.session.pop("patient_id", None)  # [추가] 온보딩용 임시 세션 값 정리
        return redirect("patients:main", patient_id=patient.patient_id)

    return render(request, "patients/onboarding_health_additional.html", {"patient": patient})