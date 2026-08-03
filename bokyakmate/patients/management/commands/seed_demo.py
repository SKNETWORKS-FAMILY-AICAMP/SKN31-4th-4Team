"""
patients/management/commands/seed_demo.py

모든 화면을 실제 데이터로 확인할 수 있게 테스트용 데이터를 만든다.
몇 번을 실행해도 중복 생성되지 않도록 전부 get_or_create를 쓴다.

실행:
    python manage.py seed_demo
"""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from patients.models import (
    Hospital, Doctor, Patient, ConditionMaster, AllergyMaster, DiseaseMaster,
    Drug, HospitalVisit, Prescription, PrescriptionDetail, DosingLog,
    SideEffectReport, ChatSession, PatientCondition, PatientAllergy,
)


class Command(BaseCommand):
    help = "모든 화면을 확인할 수 있는 테스트용 데이터를 생성합니다."

    def handle(self, *args, **options):
        hospital, _ = Hospital.objects.get_or_create(
            hospital_code="01",
            defaults={"hospital_name": "SKN정신병원", "address": "서울 금천구", "phone": "02-1234-5678"},
        )
        hospital2, _ = Hospital.objects.get_or_create(
            hospital_code="02",
            defaults={"hospital_name": "마음편한의원", "address": "서울 강남구", "phone": "02-9876-5432"},
        )

        doctor_user, created = User.objects.get_or_create(username="doctor1")
        if created:
            doctor_user.set_password("test1234!")
            doctor_user.save()
        doctor, _ = Doctor.objects.get_or_create(
            member_id="doc001",
            defaults={"user": doctor_user, "name": "김봉남", "hospital": hospital,
                      "joined_at": date(2026, 1, 1)},
        )

        patient_user, created = User.objects.get_or_create(username="patient1")
        if created:
            patient_user.set_password("test1234!")
            patient_user.save()
        patient, _ = Patient.objects.get_or_create(
            patient_id="p001",
            defaults={"user": patient_user, "name": "박서연", "gender": "F",
                      "birth_date": date(1992, 3, 14), "weight_kg": 60, "height_cm": 163},
        )

        # 기저질환 / 알레르기 마스터 (마이페이지·온보딩 체크박스용)
        conditions = ["고혈압", "당뇨", "간질환", "신장질환", "심혈관질환"]
        for i, name in enumerate(conditions, start=1):
            ConditionMaster.objects.get_or_create(code=f"COND{i:03d}", defaults={"name": name})

        allergies = ["페니실린", "달걀", "갑각류"]
        for i, name in enumerate(allergies, start=1):
            AllergyMaster.objects.get_or_create(code=f"ALG{i:03d}", defaults={"name": name})

        cond_hbp = ConditionMaster.objects.get(code="COND001")
        PatientCondition.objects.get_or_create(patient=patient, condition=cond_hbp)

        # 약물 + 관련 질환
        disease, _ = DiseaseMaster.objects.get_or_create(code="D001", defaults={"name": "조현병"})
        drug1, _ = Drug.objects.get_or_create(
            product_code="738600ATB",
            defaults={"ingredient_code": "511302ATB", "drug_name": "로나센정4mg", "manufacturer": "일동제약"},
        )
        drug1.treats_diseases.add(disease)

        drug2, _ = Drug.objects.get_or_create(
            product_code="193209ATR",
            defaults={"ingredient_code": "193209ATR", "drug_name": "콘서타OROS서방정54mg", "manufacturer": "한국얀센"},
        )

        # 병원 방문 + 처방
        visit, _ = HospitalVisit.objects.get_or_create(
            patient=patient, hospital=hospital, doctor=doctor, visit_date=date(2026, 7, 29),
            defaults={"reason": "정기 진료"},
        )
        prescription, _ = Prescription.objects.get_or_create(
            prescription_id="RX001",
            defaults={"patient": patient, "hospital": hospital, "doctor": doctor, "visit": visit,
                      "prescribed_at": date(2026, 7, 29), "diagnosis": "조현병"},
        )
        detail1, _ = PrescriptionDetail.objects.get_or_create(
            prescription=prescription, seq=1,
            defaults={"drug": drug1, "dosage_instruction": "1일 2회 1정", "start_date": date(2026, 7, 29)},
        )
        detail2, _ = PrescriptionDetail.objects.get_or_create(
            prescription=prescription, seq=2,
            defaults={"drug": drug2, "dosage_instruction": "1일 1회 1정", "start_date": date(2026, 7, 29)},
        )

        # 오늘의 복약 위젯이 "일부만 완료" 상태로 보이도록: 하나는 완료, 하나는 미완료
        now = timezone.now()
        DosingLog.objects.get_or_create(
            patient=patient, prescription_detail=detail1, scheduled_at=now.replace(hour=8, minute=0, second=0, microsecond=0),
            defaults={"status": "done", "taken_at": now.replace(hour=8, minute=5)},
        )
        DosingLog.objects.get_or_create(
            patient=patient, prescription_detail=detail2, scheduled_at=now.replace(hour=8, minute=0, second=0, microsecond=0),
            defaults={"status": "pending"},
        )

        # 캘린더가 비어 보이지 않도록 이번 달 지난 날짜 몇 개 추가
        for days_ago in [2, 3, 5, 6]:
            d = now - timedelta(days=days_ago)
            status = "done" if days_ago in (2, 5) else "missed"
            DosingLog.objects.get_or_create(
                patient=patient, prescription_detail=detail1,
                scheduled_at=d.replace(hour=8, minute=0, second=0, microsecond=0),
                defaults={"status": status, "taken_at": d if status == "done" else None},
            )

        # 상담 히스토리
        ChatSession.objects.get_or_create(
            patient=patient, hospital=hospital, question_summary="두통 관련 부작용 문의",
            defaults={"intent": "side_effect"},
        )
        ChatSession.objects.get_or_create(
            patient=patient, hospital=hospital, question_summary="케토코나졸 병용 가능 여부 문의",
            defaults={"intent": "interaction"},
        )

        # 부작용 기록
        SideEffectReport.objects.get_or_create(
            patient=patient, hospital=hospital, symptom="두통",
            defaults={"severity": "mid", "source": "chatbot", "verify_status": "unverified"},
        )

        self.stdout.write(self.style.SUCCESS("시드 데이터 생성 완료"))
        self.stdout.write("  병원 회원 로그인: doctor1 / test1234!")
        self.stdout.write("  환자 계정(온보딩 데모용으로 자동 로그인됨): patient1 / test1234!")
        self.stdout.write(f"  환자ID: {patient.patient_id} / 의사ID: {doctor.member_id}")
