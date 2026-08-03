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


def login_view(request):
    if request.method == "POST":
        role = request.POST.get("role", "patient")   # "patient" 또는 "doctor"
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if user is None:
            return render(request, "accounts/login.html", {
                "error": "아이디 또는 비밀번호가 올바르지 않습니다.",
                "role": role,
            })

        if role == "patient":
            if not hasattr(user, "patient_profile"):
                return render(request, "accounts/login.html", {
                    "error": "환자 회원 계정이 아닙니다.",
                    "role": role,
                })
            login(request, user)
            return redirect(reverse("patients:main", args=[user.patient_profile.patient_id]))

        else:  # doctor
            if not hasattr(user, "doctor_profile"):
                return render(request, "accounts/login.html", {
                    "error": "병원 회원 계정이 아닙니다.",
                    "role": role,
                })
            login(request, user)
            return redirect(reverse("doctors:patient_list", args=[user.doctor_profile.member_id]))

    return render(request, "accounts/login.html", {"role": "patient"})


def logout_view(request):
    logout(request)
    return redirect(reverse("accounts:login"))
