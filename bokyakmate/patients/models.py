"""
patients/models.py

지난번 정리한 RDB 설계(병원/환자/처방/약정보/복용기록/부작용히스토리 +
병원방문이력, 기저질환마스터)를 Django ORM 모델로 그대로 옮긴 것.
테이블 이름과 관계 구조는 설계 문서와 1:1로 대응된다.

이번 라운드 추가:
  - Patient/Doctor에 Django 기본 User와의 OneToOne 연결 (로그인/인증용)
  - AllergyMaster/PatientAllergy (기저질환과 같은 패턴, 마이페이지 수정에 필요)
"""
from django.conf import settings
from django.db import models


class Hospital(models.Model):
    """1. 병원"""
    hospital_code = models.CharField(max_length=20, primary_key=True)
    hospital_name = models.CharField(max_length=100)
    address = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.hospital_name


class Doctor(models.Model):
    """의사회원 (병원과 분리). user로 로그인 계정과 연결된다."""
    member_id = models.CharField(max_length=30, primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor_profile")
    name = models.CharField(max_length=50)
    license_no = models.CharField(max_length=30, blank=True)
    department = models.CharField(max_length=50, default="정신건강의학과")
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name="doctors")
    joined_at = models.DateField()
    left_at = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.hospital.hospital_name})"


class ConditionMaster(models.Model):
    """기저질환마스터 — patient_intake.py의 multiselect 옵션과 값이 일치해야 함"""
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class AllergyMaster(models.Model):
    """알레르기마스터 — 기저질환과 같은 패턴"""
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Patient(models.Model):
    """2. 환자정보. user로 로그인 계정과 연결된다."""
    GENDER_CHOICES = [("M", "남성"), ("F", "여성"), ("U", "선택 안함")]

    patient_id = models.CharField(max_length=30, primary_key=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_profile")
    name = models.CharField(max_length=50)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default="U")
    birth_date = models.DateField()
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    is_pregnant = models.BooleanField(default=False)
    note = models.TextField(blank=True)

    conditions = models.ManyToManyField(ConditionMaster, through="PatientCondition")
    allergies = models.ManyToManyField(AllergyMaster, through="PatientAllergy")

    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    def __str__(self):
        return self.name


class PatientCondition(models.Model):
    """환자기저질환 (환자 ↔ 기저질환마스터 매핑, 날짜 없는 단순형)"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    condition = models.ForeignKey(ConditionMaster, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("patient", "condition")


class PatientAllergy(models.Model):
    """환자알레르기 (환자 ↔ 알레르기마스터 매핑, 날짜 없는 단순형)"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    allergy = models.ForeignKey(AllergyMaster, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("patient", "allergy")


class DiseaseMaster(models.Model):
    """관련질환마스터 — 약정보 조회 화면의 '관련 질환 목록'용"""
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Drug(models.Model):
    """5. 약정보(정신과) — medicine_new.xlsx / ingredient_drug_class.csv와 연결되는 지점"""
    product_code = models.CharField(max_length=20, primary_key=True)   # 약물ID(제품코드)
    ingredient_code = models.CharField(max_length=20, db_index=True)    # 주성분코드
    drug_name = models.CharField(max_length=100)                       # 약제명
    manufacturer = models.CharField(max_length=100, blank=True)        # 제약사
    drug_class = models.CharField(max_length=100, blank=True)          # 약효분류 (DrugClass)
    treats_diseases = models.ManyToManyField(DiseaseMaster, blank=True, related_name="drugs")

    def __str__(self):
        return self.drug_name


class HospitalVisit(models.Model):
    """신규: 병원방문이력 — 환자가 여러 병원을 다닐 수 있게 하는 핵심 테이블"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="visits")
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True)
    visit_date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-visit_date"]

    def __str__(self):
        return f"{self.patient.name} - {self.hospital.hospital_name} ({self.visit_date})"


class Prescription(models.Model):
    """3. 처방기록.
    hospital/doctor는 환자의 '현재' 소속이 아니라 처방 발생 시점 값을 스냅샷으로 저장한다
    (환자·의사가 나중에 병원을 옮겨도 과거 처방 기록이 안 바뀌게)."""
    prescription_id = models.CharField(max_length=30, primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="prescriptions")
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="prescriptions")
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True)
    visit = models.ForeignKey(HospitalVisit, on_delete=models.SET_NULL, null=True, related_name="prescription")
    prescribed_at = models.DateField()
    diagnosis = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-prescribed_at"]


class PrescriptionDetail(models.Model):
    """4. 처방기록 상세 — 용법용량 컬럼 추가"""
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="details")
    seq = models.PositiveIntegerField()
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT)
    dosage_instruction = models.CharField(max_length=100)   # 예: "1일 2회 1정"
    duration_days = models.PositiveIntegerField(null=True, blank=True)
    start_date = models.DateField()
    expected_end_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("prescription", "seq")


class DosingLog(models.Model):
    """6. 복용기록 — 예정/실제 구분 추가"""
    STATUS_CHOICES = [("done", "복용완료"), ("missed", "미복용"), ("skipped", "건너뜀"), ("pending", "예정")]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="dosing_logs")
    prescription_detail = models.ForeignKey(PrescriptionDetail, on_delete=models.CASCADE)
    scheduled_at = models.DateTimeField()
    taken_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    class Meta:
        ordering = ["-scheduled_at"]


class SideEffectReport(models.Model):
    """7. 부작용 히스토리 — 회원ID를 환자ID로 명확히, 검증상태 추가"""
    SOURCE_CHOICES = [("chatbot", "챗봇 자가보고"), ("doctor", "의료진 확인")]
    VERIFY_CHOICES = [("unverified", "미검증"), ("verified", "검증됨"), ("rejected", "반려")]
    SEVERITY_CHOICES = [("low", "낮음"), ("mid", "중간"), ("high", "높음")]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="side_effects")
    hospital = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, blank=True, related_name="side_effects")
    dosing_log = models.ForeignKey(DosingLog, on_delete=models.SET_NULL, null=True, blank=True)
    reported_at = models.DateTimeField(auto_now_add=True)
    symptom = models.CharField(max_length=100)          # 정규화된 증상명
    severity = models.CharField(max_length=5, choices=SEVERITY_CHOICES, default="low")
    raw_content = models.TextField(blank=True)            # 챗봇 대화 원문 발췌
    llm_summary = models.TextField(blank=True)            # llm이 추출한 요약
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="chatbot")
    verify_status = models.CharField(max_length=10, choices=VERIFY_CHOICES, default="unverified")

    class Meta:
        ordering = ["-reported_at"]


class ChatSession(models.Model):
    """상담 히스토리 요약용 — Neo4j Personal Graph의 ChatSession 노드와 대응.
    hospital: 병원별 대시보드 조회용 스냅샷 (환자의 그 시점 소속 병원, nullable —
    상담이 병원 방문과 무관하게 발생할 수도 있어서)"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="chat_sessions")
    hospital = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_sessions")
    started_at = models.DateTimeField(auto_now_add=True)
    question_summary = models.CharField(max_length=200)   # 메인 화면 카드에 보여줄 한 줄 요약
    intent = models.CharField(max_length=20, blank=True)   # side_effect / interaction / general

    class Meta:
        ordering = ["-started_at"]
