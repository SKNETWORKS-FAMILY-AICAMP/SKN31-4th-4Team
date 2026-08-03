"""
doctors/views.py

명세서의 6개 화면(환자목록/환자상세/처방상세/복약체크/부작용기록/약정보조회)을
전부 구현한다. 로그인은 accounts 앱의 공용 로그인을 그대로 재사용한다
(환자/병원 탭 로그인 시 이미 만들어둔 것).

병원 스코프 원칙: Patient 자체엔 병원ID가 없다 (환자가 여러 병원을 다닐 수
있다는 지난 논의에 따라 이벤트 테이블로 옮겼음). 그래서 "이 병원이 관리하는
환자"는 HospitalVisit을 통해 조인해서 구한다.
"""
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db import IntegrityError

from patients.models import (
    Doctor, Patient, HospitalVisit, Prescription, PrescriptionDetail,
    Drug, DosingLog, SideEffectReport,
)


@login_required
def patient_list(request, member_id):
    doctor = get_object_or_404(Doctor, member_id=member_id, user=request.user)

    query = request.GET.get("q", "").strip()
    patients = Patient.objects.filter(visits__hospital=doctor.hospital).distinct()
    if query:
        patients = patients.filter(name__icontains=query)

    return render(request, "doctors/patient_list.html", {
        "doctor": doctor, "patients": patients, "query": query,
    })


@login_required
def patient_create(request, member_id):
    doctor = get_object_or_404(Doctor, member_id=member_id, user=request.user)

    if request.method == "POST":
        patient_id = request.POST.get("patient_id", "").strip()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        name = request.POST.get("name", "").strip()
        gender = request.POST.get("gender", "U")
        birth_date = request.POST.get("birth_date")

        if not all([patient_id, username, password, name, birth_date]):
            messages.error(request, "필수 항목을 모두 입력해주세요.")
            return render(request, "doctors/patient_create.html", {"doctor": doctor})

        try:
            user = User.objects.create_user(username=username, password=password)
            patient = Patient.objects.create(
                patient_id=patient_id, user=user, name=name,
                gender=gender, birth_date=birth_date,
            )
            HospitalVisit.objects.create(
                patient=patient, hospital=doctor.hospital, doctor=doctor,
                visit_date=timezone.localdate(), reason="신규 환자 등록",
            )
        except IntegrityError:
            messages.error(request, "이미 존재하는 환자ID 또는 아이디입니다.")
            return render(request, "doctors/patient_create.html", {"doctor": doctor})

        return redirect("doctors:patient_detail", member_id=member_id, patient_id=patient.patient_id)

    return render(request, "doctors/patient_create.html", {"doctor": doctor})


@login_required
def patient_detail(request, member_id, patient_id):
    doctor = get_object_or_404(Doctor, member_id=member_id, user=request.user)
    patient = get_object_or_404(Patient, patient_id=patient_id, visits__hospital=doctor.hospital)

    prescriptions = Prescription.objects.filter(patient=patient, hospital=doctor.hospital) \
        .prefetch_related("details__drug")

    return render(request, "doctors/patient_detail.html", {
        "doctor": doctor, "patient": patient, "prescriptions": prescriptions,
    })


@login_required
def prescription_create(request, member_id, patient_id):
    doctor = get_object_or_404(Doctor, member_id=member_id, user=request.user)
    patient = get_object_or_404(Patient, patient_id=patient_id, visits__hospital=doctor.hospital)

    if request.method == "POST":
        prescription_id = request.POST.get("prescription_id", "").strip()
        diagnosis = request.POST.get("diagnosis", "").strip()
        prescribed_at = request.POST.get("prescribed_at") or timezone.localdate()

        prescription = Prescription.objects.create(
            prescription_id=prescription_id, patient=patient, hospital=doctor.hospital,
            doctor=doctor, diagnosis=diagnosis, prescribed_at=prescribed_at,
        )
        return redirect("doctors:prescription_detail", member_id=member_id, prescription_id=prescription.prescription_id)

    return render(request, "doctors/prescription_create.html", {"doctor": doctor, "patient": patient})


@login_required
def prescription_detail(request, member_id, prescription_id):
    doctor = get_object_or_404(Doctor, member_id=member_id, user=request.user)
    prescription = get_object_or_404(Prescription, prescription_id=prescription_id, hospital=doctor.hospital)
    details = prescription.details.select_related("drug")

    return render(request, "doctors/prescription_detail.html", {
        "doctor": doctor, "prescription": prescription, "details": details,
    })


@login_required
def prescription_add_drug(request, member_id, prescription_id):
    doctor = get_object_or_404(Doctor, member_id=member_id, user=request.user)
    prescription = get_object_or_404(Prescription, prescription_id=prescription_id, hospital=doctor.hospital)

    if request.method == "POST":
        product_code = request.POST.get("drug")
        dosage_instruction = request.POST.get("dosage_instruction", "").strip()
        start_date = request.POST.get("start_date") or timezone.localdate()

        next_seq = (prescription.details.count() or 0) + 1
        PrescriptionDetail.objects.create(
            prescription=prescription, seq=next_seq,
            drug_id=product_code, dosage_instruction=dosage_instruction, start_date=start_date,
        )
        return redirect("doctors:prescription_detail", member_id=member_id, prescription_id=prescription_id)

    return render(request, "doctors/prescription_add_drug.html", {
        "doctor": doctor, "prescription": prescription, "drugs": Drug.objects.all(),
    })


@login_required
def dosing_check(request, member_id, detail_id):
    doctor = get_object_or_404(Doctor, member_id=member_id, user=request.user)
    detail = get_object_or_404(PrescriptionDetail, id=detail_id, prescription__hospital=doctor.hospital)

    if request.method == "POST":
        status = request.POST.get("status")
        DosingLog.objects.create(
            patient=detail.prescription.patient, prescription_detail=detail,
            scheduled_at=timezone.now(),
            taken_at=timezone.now() if status == "done" else None,
            status=status,
        )
        return redirect("doctors:dosing_check", member_id=member_id, detail_id=detail_id)

    logs = DosingLog.objects.filter(prescription_detail=detail)
    return render(request, "doctors/dosing_check.html", {
        "doctor": doctor, "detail": detail, "logs": logs,
    })


@login_required
def side_effect_record(request, member_id, detail_id):
    doctor = get_object_or_404(Doctor, member_id=member_id, user=request.user)
    detail = get_object_or_404(PrescriptionDetail, id=detail_id, prescription__hospital=doctor.hospital)

    if request.method == "POST":
        symptom = request.POST.get("symptom", "").strip()
        severity = request.POST.get("severity", "low")

        SideEffectReport.objects.create(
            patient=detail.prescription.patient, hospital=doctor.hospital,
            symptom=symptom, severity=severity, source="doctor", verify_status="verified",
        )
        return redirect("doctors:patient_detail", member_id=member_id, patient_id=detail.prescription.patient.patient_id)

    return render(request, "doctors/side_effect_record.html", {"doctor": doctor, "detail": detail})


@login_required
def drug_info(request, member_id, product_code=None):
    doctor = get_object_or_404(Doctor, member_id=member_id, user=request.user)
    query = request.GET.get("q", "").strip()

    drug = None
    if product_code:
        drug = get_object_or_404(Drug, product_code=product_code)

    results = Drug.objects.filter(drug_name__icontains=query) if query else Drug.objects.none()

    return render(request, "doctors/drug_info.html", {
        "doctor": doctor, "drug": drug, "query": query, "results": results,
    })
