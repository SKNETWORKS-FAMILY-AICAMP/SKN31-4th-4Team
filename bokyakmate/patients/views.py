"""
patients/views.py

목업 HTML에서 하드코딩했던 값(하린님/로나센정4mg/34세 등)을
전부 실제 DB 조회로 바꾼다. quick_cards의 url은 여기서 reverse()로
미리 계산해서 넘긴다 (템플릿 안에서 URL 이름을 문자열로 조합하는 건
불안정한 패턴이라 피한다).
"""
import calendar
from datetime import datetime, date
import re

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist


from .models import (
    Patient, ChatSession, Prescription, PrescriptionDetail,
    DosingLog,SymptomLog, Hospital
)

# 챗봇 쪽 
from django.http import JsonResponse, HttpResponse
from langchain_core.messages import HumanMessage
from asgiref.sync import async_to_sync
import sqlite3
import json
from Chatbot.builder import build_graph, build_initial_state
from services.end_summary import process_chat_summary

def _check_owner(request, patient_id):
    """로그인한 사용자가 이 환자 본인인지 확인 (다른 환자 URL을 직접 쳐서 못 들어가게)."""
    return request.user.is_authenticated and getattr(request.user, "patient_profile", None) \
        and request.user.Patient.patient_id == patient_id


@login_required
def patient_main(request, patient_id):
    patient = get_object_or_404(Patient, patient_id=patient_id)

    latest_prescription = (
        Prescription.objects.filter(patient=patient)
        .prefetch_related("details__drug")
        .first()
    )
    current_drug = None
    if latest_prescription:
        for detail in latest_prescription.details.all():
            try:
                current_drug = detail.drug
                break
            except ObjectDoesNotExist:
                continue  # 깨진 FK는 건너뜀

    recent_chats = ChatSession.objects.filter(patient=patient)[:3]

    today = timezone.localdate()
    todays_logs = DosingLog.objects.filter(patient=patient, scheduled_at__date=today) \
        .select_related("prescription_detail__drug")

    today_doses = []
    for log in todays_logs:
        try:
            drug_name = log.prescription_detail.drug.drug_name
        except ObjectDoesNotExist:
            drug_name = "알 수 없는 약"
        today_doses.append({
            "id": log.id,
            "drug_name": drug_name,
            "checked": log.status == "done",
            "missed": log.status == "missed",
        })

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
    selected_date = request.GET.get("date")

    if selected_date:
        selected_date = datetime.strptime(
            selected_date,
            "%Y-%m-%d"
        ).date()
    else:
        selected_date = today

    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    # 수정 select_related() 삭제
    logs = list(
        DosingLog.objects.filter(
            patient=patient,
            scheduled_at__year=year,
            scheduled_at__month=month
        )
    )

    # 자동 미복용 처리
    now = timezone.now()

    for log in logs:
        if (
            log.status == "pending"
            and log.scheduled_at < now
        ):
            log.status = "missed"
            log.save(update_fields=["status"])

    # 월간 통계
    done_logs = sum(1 for log in logs if log.status == "done")
    missed_logs = sum(1 for log in logs if log.status == "missed")
    pending_logs = sum(1 for log in logs if log.status == "pending")

    total_logs = len(logs)

    if total_logs > 0:
        monthly_progress = int(done_logs * 100 / total_logs)
    else:
        monthly_progress = 0

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
                    "date": date(year, month, day),                    
                    "status": day_status(statuses) if statuses else "none",
                    "is_today": date(year, month, day) == today,
                })
        weeks.append(week_cells)

    todays_logs = DosingLog.objects.filter(
        patient=patient,
        scheduled_at__date=selected_date
    ).select_related("prescription_detail__drug")

    for log in todays_logs:
        if (
            log.status == "pending"
            and log.scheduled_at < timezone.now()
        ):
            log.status = "missed"
            log.save(update_fields=["status"])

    total_count = todays_logs.count()
    done_count = todays_logs.filter(status="done").count()

    if total_count > 0:
        progress = int(done_count * 100 / total_count)
    else:
        progress = 0

    prev_month = (datetime(year, month, 1) - timezone.timedelta(days=1))
    next_month_date = datetime(year, month, 28) + timezone.timedelta(days=7)
    next_month_date = next_month_date.replace(day=1)

    context = {
        "patient": patient,
        "weeks": weeks,
        "year": year,
        "month": month,
        "selected_date": selected_date,
        "todays_logs": todays_logs,
        "done_count": done_count,
        "total_count": total_count,
        "progress": progress,
        "monthly_progress": monthly_progress,
        "done_logs": done_logs,
        "missed_logs": missed_logs,
        "pending_logs": pending_logs,
        "prev_url": f"?year={prev_month.year}&month={prev_month.month}&date={selected_date}",
        "next_url": f"?year={next_month_date.year}&month={next_month_date.month}&date={selected_date}",
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

    selected_date = request.GET.get("date")

    if selected_date:
        return redirect(
            f"{reverse('patients:dosing_calendar', args=[patient_id])}"
            f"?date={selected_date}"
        )

    return redirect("patients:dosing_calendar", patient_id=patient_id)


@login_required
def records(request, patient_id):
    """기록 — 처방 기록/병원 방문 기록을 탭으로 묶어서 보여준다."""
    patient = get_object_or_404(Patient, patient_id=patient_id)
    active_tab = request.GET.get("tab", "prescriptions")

    prescriptions = (
        Prescription.objects.filter(patient=patient)
        .select_related("hospital", "doctor")           
        .prefetch_related("details__drug")
        .order_by("-prescribed_at")
    )

    context = {
        "patient": patient,
        "active_tab": active_tab,
        "prescriptions": prescriptions,
        "main_url": reverse("patients:main", args=[patient_id]),
    }
    return render(request, "patients/records.html", context)

# @login_required
# def mypage(request, patient_id):
#     patient = get_object_or_404(Patient, patient_id=patient_id)
#     all_conditions = Condition.objects.all()

#     if request.method == "POST":
#         patient.is_pregnant = request.POST.get("is_pregnant") == "on"
#         etc = request.POST.get("etc", "").strip()
#         patient.note = etc  # note는 이제 순수 '기타' 텍스트만
#         patient.save()

#         selected_codes = request.POST.getlist("conditions")
#         PatientCondition.objects.filter(patient=patient).delete()
#         PatientCondition.objects.bulk_create([
#             PatientCondition(patient=patient, condition_id=code) for code in selected_codes
#         ])

#         return redirect("patients:mypage", patient_id=patient_id)

#     my_condition_codes = list(
#         PatientCondition.objects.filter(patient=patient).values_list("condition_id", flat=True)
#     )

#     context = {
#         "patient": patient,
#         "main_url": reverse("patients:main", args=[patient_id]),
#         "all_conditions": all_conditions,
#         "my_condition_codes": my_condition_codes,
#         "etc_value": patient.note,
#     }
#     return render(request, "patients/mypage.html", context)

@login_required
def mypage(request, patient_id):
    """마이페이지 - 기저질환/알레르기/수면시간 등을 저장"""

    patient = get_object_or_404(Patient, patient_id=patient_id)

    if request.method == "POST":
        patient.is_pregnant = request.POST.get("is_pregnant") == "on"

        # ===== 기저질환/기타: 폼에 해당 필드가 실제로 존재할 때만 note 갱신 =====
        if "conditions" in request.POST or "etc" in request.POST:
            conditions = request.POST.getlist("conditions")
            etc = request.POST.get("etc", "").strip()

            notes = []
            if conditions:
                notes.append(", ".join(conditions))
            if etc:
                notes.append(f"기타: {etc}")

            patient.note = "\n".join(notes)

        # ===== 취침/기상 시간 =====
        sleep_time = request.POST.get("sleep_time", "").strip()
        wake_time = request.POST.get("wake_time", "").strip()

        if sleep_time:
            patient.average_sleep_time = datetime.strptime(sleep_time, "%H:%M").time()
        if wake_time:
            patient.average_wake_time = datetime.strptime(wake_time, "%H:%M").time()

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
    patient = get_object_or_404(Patient, patient_id=patient_id)
    graph = build_graph()
    
    chat_session = ChatSession.objects.filter(
        patient=patient,
        status="active"
    ).first()
        
    if chat_session is None:
        chat_session = ChatSession.objects.create(
            patient=patient,
            status="active"
        )
        
    thread_id = str(chat_session.session_id)
    
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }


    if request.method == "POST":
        try:
            data = json.loads(request.body)
            current_state = graph.get_state(config)
            user_message = data.get("user_input", "")
            
            if not current_state.values:
                conn = sqlite3.connect("langgraph_checkpoint.db", check_same_thread=False)
                input_data = build_initial_state(conn, str(patient_id))
                
                # ★ 딕셔너리를 버리고, 랭그래프 전용 HumanMessage 객체로 포장합니다!
                input_data["messages"] = [HumanMessage(content=user_message)]
                input_data["patient_id"] = str(patient_id) 
            else:
                input_data = {
                    # ★ 여기도 마찬가지로 객체로 포장!
                    "messages": [HumanMessage(content=user_message)],
                    "patient_id": str(patient_id) 
                }

            result = graph.invoke(input_data, config=config)
            
            # (아까 수정한 아래 코드는 그대로 두시면 됩니다!)
            last_message = result["messages"][-1]
            if isinstance(last_message, dict):
                ai_reply = last_message.get("content", "")
            else:
                ai_reply = last_message.content
                
            return JsonResponse({"reply": ai_reply})
        except Exception as e:
            return JsonResponse({"error": f"모델 처리 중 오류가 발생했습니다: {str(e)}"}, status=500)

    # GET 요청: 여기서 current_state를 안전하게 부를 수 있습니다.
    messages = []
    current_state = graph.get_state(config)
    if current_state.values and "messages" in current_state.values:
        for msg in current_state.values["messages"]:
            # ★ 수정할 부분: 과거 메시지가 딕셔너리일 때와 객체일 때 모두 안전하게 꺼내기
            if isinstance(msg, dict):
                msg_type = msg.get("type", "")
                msg_content = msg.get("content", "")
            else:
                msg_type = msg.type
                msg_content = msg.content

            role = "patient" if msg_type == "human" else "assistant"
            messages.append({
                "role": role,
                "content": msg_content
            })

    return render(request, "patients/chatbot.html", {
        "patient": patient,
        "messages": messages,
        "main_url": reverse("patients:main", args=[patient_id]),
    })
    
@login_required
def chatbot_end(request, patient_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    patient = get_object_or_404(Patient, patient_id=patient_id)

    chat_session = ChatSession.objects.filter(
        patient=patient,
        status="active"
    ).first()

    # 원인 1: 찾을 수 없어서 조용히 success=True만 반환하고 끝나는 경우
    if chat_session is None:
        print(f"⚠️ [chatbot_end] {patient_id} 환자의 active 상태인 ChatSession을 찾을 수 없습니다.")
        return JsonResponse({"error": "No active session"}, status=404)

    try:
        chat_session.status = "closed"
        chat_session.ended_at = timezone.now()
        
        # 원인 2: 요약 처리 함수에서 에러가 발생하는 경우
        title, detail = process_chat_summary(chat_session.session_id)
        chat_session.intent = title
        chat_session.summary = detail

        chat_session.save()
        print("✅ 데이터베이스 저장 완료!")
        return JsonResponse({"success": True})
        
    except Exception as e:
        print(f"❌ [chatbot_end] 에러 발생: {e}")
        return JsonResponse({"error": str(e)}, status=500)

# ------------------------------------------------------------------
# 온보딩 (최초진입) — 명세서의 "최초진입" -- 7단계
# ------------------------------------------------------------------

# _DEMO_PATIENT_ID = "P-2009"


def onboarding_start(request):
    return render(request, "patients/onboarding_start.html")


def onboarding_hospital_select(request):
    from .models import Hospital, Patient
    hospitals = Hospital.objects.all()

    if request.method == "POST":
        hospital_code = request.POST.get("hospital_code")
        request.session["onboarding_hospital_code"] = hospital_code
        return redirect("patients:onboarding_hospital_auth")

    return render(request, "patients/onboarding_hospital_select.html", {"hospitals": hospitals})


from .models import Patient

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
        # (이 두 값은 onboarding_health_basic에서 저장된다)
        if patient.height_cm is not None and patient.weight_kg is not None:
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
    from .models import Hospital, Patient

    hospital_code = request.session.get("onboarding_hospital_code")
    patient_id = request.session.get("patient_id")

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
    from .models import Hospital, Patient

    hospital_code = request.session.get("onboarding_hospital_code")
    patient_id = request.session.get("patient_id")

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
    patient_id = request.session.get("patient_id")
    if not patient_id:
        return redirect("patients:onboarding_start")
    patient = get_object_or_404(Patient, patient_id=patient_id)
    if request.method == "POST":
        height = request.POST.get("height_cm")
        weight = request.POST.get("weight_kg")
        sleep_time = request.POST.get("sleep_time")
        wake_time = request.POST.get("wake_time")
        eating_habit = request.POST.get("eating_habit")

        if height:
            patient.height_cm = Decimal(height)
        if weight:
            patient.weight_kg = Decimal(weight)
        if sleep_time:
            patient.average_sleep_time = datetime.strptime(sleep_time, "%H:%M").time()
        if wake_time:
            patient.average_wake_time = datetime.strptime(wake_time, "%H:%M").time()
        if eating_habit:
            patient.meal_pattern = eating_habit
        patient.is_smoker = request.POST.get("is_smoking") == "on"
        patient.save()
        return redirect("patients:onboarding_health_additional")
    
    return render(request, "patients/onboarding_health_basic.html")


from django.contrib.auth import login
from django.shortcuts import get_object_or_404, redirect, render

# def onboarding_health_additional(request):
#     patient_id = request.session.get("patient_id")

#     if not patient_id:
#         return redirect("patients:onboarding_start")

#     patient = get_object_or_404(
#         Patient,
#         patient_id=patient_id
#     )

#     if request.method == "POST":
#         # TODO: 기저질환/알레르기/임신 여부 저장

#         login(request, patient.user)

#         request.session.pop("onboarding_hospital_code", None)
#         request.session.pop("patient_id", None)

#         return redirect("patients:main", patient_id=patient.patient_id)

#     return render(
#         request,
#         "patients/onboarding_health_additional.html",
#         {
#             "patient": patient
#         }
#     )

def onboarding_health_additional(request):
    """추가 건강 정보(기저질환, 임신 여부) 입력 및 온보딩 완료 뷰"""
    patient_id = request.session.get("patient_id")

    if not patient_id:
        return redirect("patients:onboarding_start")

    patient = get_object_or_404(Patient, patient_id=patient_id)

    if request.method == "POST":
        # 임신 체크 시 1, 미체크 시 0
        patient.is_pregnant = 1 if request.POST.get("is_pregnant") == "on" else 0

        # 기저질환 처리
        conditions = request.POST.getlist("conditions")
        condition_etc = request.POST.get("condition_etc", "").strip()

        # '기타' 선택 시 직접 입력한 텍스트로 대체
        if "기타" in conditions:
            conditions.remove("기타")
            if condition_etc:
                conditions.append(condition_etc)

        # 수집된 기저질환 정보를 Patient.note 텍스트 필드에 기록
        if conditions:
            formatted_conditions = f"기저질환: {', '.join(conditions)}"
            if patient.note:
                patient.note = f"{patient.note}\n{formatted_conditions}"
            else:
                patient.note = formatted_conditions

        # MySQL DB 저장
        patient.save()

        # 회원 인증 및 세션 로그인 처리
        login(request, patient.user)

        # 온보딩 세션 임시 데이터 정리
        request.session.pop("onboarding_hospital_code", None)
        request.session.pop("patient_id", None)

        return redirect("patients:main", patient_id=patient.patient_id)

    return render(
        request,
        "patients/onboarding_health_additional.html",
        {
            "patient": patient,
        },
    )

def calendar_day(request, patient_id, selected_date):

    patient = get_object_or_404(
        Patient,
        patient_id=patient_id
    )

    target_date = datetime.strptime(
        selected_date,
        "%Y-%m-%d"
    ).date()

    logs = DosingLog.objects.filter(
        patient=patient,
        scheduled_at__date=target_date
    ).select_related(
        "prescription_detail__drug"
    ).order_by("scheduled_at")

    context = {
        "patient": patient,
        "target_date": target_date,
        "logs": logs,
    }

    return render(
        request,
        "patients/calendar_day.html",
        context
    )