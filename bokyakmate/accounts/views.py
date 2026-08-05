"""
accounts/views.py

로그인 시 "병원 회원 / 환자 회원" 탭으로 어느 쪽으로 로그인하려는지 받고,
인증 성공 후 실제로 그 역할의 프로필(Patient/Doctor)을 갖고 있는지 확인해서
각각 다른 메인 화면으로 보낸다. 탭 선택과 실제 프로필이 다르면
("환자 계정인데 병원 회원 탭으로 로그인 시도" 같은 경우) 에러 메시지를 보여준다.
"""
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.urls import reverse


from django.contrib.auth import login
from django.shortcuts import render, redirect
from patients.models import Patient


def login_view(request):
    if request.method == "POST":
        role = request.POST.get("role", "patient")

        if role == "patient":
            patient_id = request.POST.get("patient_id", "").strip()
            phone = request.POST.get("phone", "").strip()

            try:
                patient = Patient.objects.select_related("user").get(
                    patient_id=patient_id,
                    phone=phone,
                )

                login(request, patient.user)
                return redirect("patients:home")   # 원하는 페이지

            except Patient.DoesNotExist:
                return render(request, "accounts/login.html", {
                    "error": "환자번호 또는 전화번호가 올바르지 않습니다.",
                    "role": role,
                })

        # 의사 로그인은 기존 방식 유지
        else:
            username = request.POST.get("username", "")
            password = request.POST.get("password", "")

            user = authenticate(
                request,
                username=username,
                password=password,
            )

            if user is None:
                return render(request, "accounts/login.html", {
                    "error": "아이디 또는 비밀번호가 올바르지 않습니다.",
                    "role": role,
                })

            login(request, user)
            return redirect("doctors:home")

    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect(reverse("accounts:login"))