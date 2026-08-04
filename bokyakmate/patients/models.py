from django.conf import settings
from django.db import models


# =========================
# Hospital
# =========================

class Hospital(models.Model):
    hospital_code = models.CharField(max_length=20, primary_key=True)
    hospital_name = models.CharField(max_length=100)
    address = models.CharField(max_length=200, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "hospital"

    def __str__(self):
        return self.hospital_name


# =========================
# Doctor
# =========================

class Doctor(models.Model):
    member_id = models.CharField(max_length=30, primary_key=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor"
    )

    name = models.CharField(max_length=50)
    license_no = models.CharField(max_length=30, blank=True)

    department = models.CharField(
        max_length=50,
        default="정신건강의학과"
    )

    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.PROTECT,
        db_column="hospital_code"
    )

    joined_at = models.DateField()
    left_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "doctor"

    def __str__(self):
        return self.name


# =========================
# Drug
# =========================

class Drug(models.Model):
    drug_product_code = models.CharField(max_length=20, primary_key=True)
    drug_name = models.CharField(max_length=200)
    ingredient_code = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "drug"

    def __str__(self):
        return self.drug_name


# =========================
# Patient
# =========================

class Patient(models.Model):
    patient_id = models.CharField(max_length=30, primary_key=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient"
    )
    
    phone = models.CharField(
    "전화번호",
    max_length=13,   # 010-1234-5678
    blank=True,
    default="",
    )
    
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.PROTECT,
        db_column="hospital_code"
    )

    name = models.CharField(max_length=50)

    gender = models.CharField(
        max_length=1,
        choices=[
            ("M", "남"),
            ("F", "여"),
            ("U", "미상"),
        ],
        default="U",
    )

    birth_date = models.DateField()

    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    is_pregnant = models.BooleanField(default=False)
    average_sleep_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="평균 취침시간"
    )
    average_wake_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name="평균 기상시간"
    )

    meal_pattern = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[
            ("regular", "규칙적"),
            ("irregular", "불규칙적"),
            ("less_than_2", "하루 2끼 이하"),
            ("skip", "식사를 자주 거름"),
        ],
        verbose_name="식사 습관"
    )
        
    note = models.TextField(blank=True)
    is_smoker = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="흡연 여부"
    )

    class Meta:
        db_table = "patient"

    def __str__(self):
        return self.name


# =========================
# Prescription
# =========================

class Prescription(models.Model):
    prescription_id = models.CharField(max_length=30, primary_key=True)

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE
    )

    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.PROTECT,
        db_column="hospital_code"
    )

    prescribed_at = models.DateField()

    diagnosis = models.CharField(max_length=100, blank=True)

    note = models.TextField(blank=True)

    class Meta:
        db_table = "prescription"


# =========================
# Prescription Detail
# =========================

class PrescriptionDetail(models.Model):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE
    )

    seq = models.IntegerField()

    drug = models.ForeignKey(
        Drug,
        on_delete=models.PROTECT,
        db_column="drug_product_code"
    )

    dosage_instruction = models.CharField(max_length=100)

    duration_days = models.IntegerField(null=True, blank=True)

    start_date = models.DateField()

    expected_end_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "prescription_detail"

        constraints = [
            models.UniqueConstraint(
                fields=["prescription", "seq"],
                name="uq_prescription_seq"
            )
        ]


# =========================
# Dosing Log
# =========================

class DosingLog(models.Model):

    STATUS = [
        ("done", "복용"),
        ("missed", "놓침"),
        ("skipped", "건너뜀"),
        ("pending", "대기"),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE
    )

    prescription_detail = models.ForeignKey(
        PrescriptionDetail,
        on_delete=models.CASCADE
    )

    scheduled_at = models.DateTimeField()

    taken_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS,
        default="pending"
    )

    class Meta:
        db_table = "dosing_log"


# =========================
# Chat Session
# =========================

class ChatSession(models.Model):

    INTENT = [
        ("부작용", "부작용"),
        ("복약", "복약"),
        ("일반질문", "일반질문"),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE
    )

    intent = models.CharField(max_length=10, choices=INTENT)

    started_at = models.DateTimeField()

    ended_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = "chat_session"


# =========================
# Symptom Log
# =========================

class SymptomLog(models.Model):

    LOG_TYPE = [
        ("free_text", "자유문진"),
        ("scale", "척도"),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE
    )

    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    chat_session = models.ForeignKey(
        ChatSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    log_type = models.CharField(max_length=20, choices=LOG_TYPE)

    chief_complaint = models.TextField()

    onset = models.CharField(max_length=200, blank=True)

    symptom_pattern = models.TextField(blank=True)

    severity = models.CharField(max_length=50, blank=True)

    aggravating_factor = models.TextField(blank=True)

    scale_name = models.CharField(max_length=50, blank=True)

    scale_score = models.IntegerField(null=True, blank=True)

    keyword = models.CharField(max_length=255, blank=True)

    summary = models.TextField(blank=True)

    suspected_drugs = models.JSONField(null=True, blank=True)

    reported_at = models.DateTimeField()

    class Meta:
        db_table = "symptom_log"
        indexes = [
            models.Index(
                fields=["patient", "-reported_at"],
                name="idx_patient_time",
            )
        ]