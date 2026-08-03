# 복약메이트 (bokyakmate)

정신과 복약 관리 챗봇 서비스. 환자용 앱(모바일 웹)과
병원 회원(의사)용 관리 화면(데스크톱 웹)으로 나뉜다 // 환자용 우선 구현

Django MVT 패턴으로 구성했고, 프론트엔드(템플릿+CSS)만 작업함
`views.py`/`models.py`의 실제 DB 연동,비즈니스 로직은 이후 백엔드 작업에서 채워 넣는 것을 전제로 한다.

---

## 1. 폴더 구조와 파일 설명

```
bokyakmate/
├── manage.py                 Django 프로젝트 실행 진입점
├── db.sqlite3                 (실행 시 자동 생성, 개발용 DB)
│
├── config/                    프로젝트 전역 설정
│   ├── settings.py               INSTALLED_APPS, LOGIN_URL 등
│   └── urls.py                   최상위 URL 라우팅 (각 앱 urls.py를 include)
│
├── accounts/                  로그인/로그아웃 (환자·병원 회원 공용)
│   ├── views.py                  로그인 시 역할(환자/병원) 확인 후 분기 리다이렉트
│   ├── urls.py
│   └── templates/accounts/
│       └── login.html            환자/병원 탭 로그인 화면 (인라인 SVG 로고 포함)
│
├── patients/                  환자용 앱
│   ├── models.py                 Hospital, Doctor, Patient, ConditionMaster,
│   │                              AllergyMaster, DiseaseMaster, Drug, HospitalVisit,
│   │                              Prescription, PrescriptionDetail, DosingLog,
│   │                              SideEffectReport, ChatSession
│   ├── views.py                  환자 메인/캘린더/기록/마이페이지 뷰 (일부 자리표시 포함)
│   ├── urls.py
│   ├── static/patients/css/
│   │   └── main.css              환자 앱 전용 스타일 (하늘색/피치/민트 톤)
│   └── templates/patients/
│       ├── onboarding_start.html              온보딩 ① 시작하기
│       ├── onboarding_hospital_select.html    온보딩 ② 병원 선택 + 확인 팝업
│       ├── onboarding_hospital_auth.html      온보딩 ③ 전화번호+병원인증번호
│       ├── onboarding_loading.html            온보딩 ④ 정보 조회 로딩
│       ├── onboarding_info_confirm.html       온보딩 ⑤ 조회 정보 확인
│       ├── onboarding_health_basic.html       온보딩 ⑥ 생활패턴 입력
│       ├── onboarding_health_additional.html  온보딩 ⑦ 기저질환/임신여부
│       ├── patient_main.html                  홈 화면 (오늘의 복약 위젯, 바로가기 4개,
│       │                                        최근 상담 요약, 플로팅 챗봇 버튼)
│       ├── dosing_calendar.html               복약 캘린더 (월별 그리드 + 오늘 체크)
│       ├── records.html                       기록 (처방/병원방문 탭)
│       ├── mypage.html                        마이페이지 (기저질환/알레르기/임신여부 수정)
│       ├── chat_history.html                  상담 히스토리 목록
│       └── chatbot.html                       AI 상담 화면 (최초진입 추천질문 / 대화 진행)
│
└── doctors/                   병원 회원(의사)용 앱
    ├── models.py                  (patients 앱 모델 재사용, 별도 모델 없음)
    ├── views.py                   환자목록/상세/처방/복약체크/부작용기록/약정보 뷰
    ├── urls.py
    ├── static/doctors/css/
    │   └── main.css               병원 앱 전용 스타일 (남색/파랑 톤, 데스크톱 레이아웃)
    └── templates/doctors/
        ├── base.html              공통 상단바(의사명, 병원명, 로그아웃)
        ├── patient_list.html      환자 목록 (검색 + 등록 버튼)
        ├── patient_create.html    환자 등록
        ├── patient_detail.html    환자 상세 (기본정보 + 처방 이력)
        ├── prescription_create.html   새 처방 등록
        ├── prescription_detail.html   처방 상세 (처방약 목록)
        ├── prescription_add_drug.html 처방약 추가
        ├── dosing_check.html      복약 체크 (복용함/놓침/건너뜀)
        ├── side_effect_record.html    부작용 기록 (증상+정도)
        └── drug_info.html         약 정보 조회 (검색 + 관련 질환)
```

### 앱을 3개로 나눈 이유
- **accounts**: 로그인은 환자·병원 공용 기능이라 어느 한쪽 앱에 속하지 않음
- **patients / doctors**: 사용자 역할이 명확히 달라 CSS/템플릿을 분리

---

## 2. 실행 방법

### 준비물
- macOS + VS Code
- Python 3 (터미널에 `python3 --version`으로 확인. 안 뜨면 `brew install python3`)

### 순서

```bash
# 1) VS Code에서 bokyakmate 폴더 열기 (File → Open Folder)
# 2) 터미널 열기 (Ctrl + `)

# 3) 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate        # 활성화 후엔 python만 써도 python3로 동작함

# 4) 필요한 패키지 설치 (이 프로젝트는 Django 하나만 필요)
pip install django

# 5) DB 테이블 생성
python manage.py migrate

# 6) 테스트용 데이터 생성 (병원/의사/환자/처방/복약기록/상담이력까지 한 번에)
python manage.py seed_demo

# 7) (선택) /admin/ 화면에서 데이터 직접 보고 싶을 때
python manage.py createsuperuser

# 8) 개발 서버 실행
python manage.py runserver
```

터미널에 `Starting development server at http://127.0.0.1:8000/`이 뜨면 성공.
브라우저에서 아래 주소로 접속:

```
http://127.0.0.1:8000/accounts/login/
```

**병원 회원**으로 둘러보고 싶으면 병원 탭 → 아이디 `doctor1` / 비밀번호 `test1234!`
**환자**로 둘러보고 싶으면 환자 탭 → "인증하고 시작하기" → 온보딩 화면을 아무 값이나 입력하며
끝까지 진행하면(전화번호·인증번호는 실제 검증을 안 하므로 아무 값이나 입력해도 됨)
자동으로 로그인되어 홈 화면으로 이동합니다.

서버가 켜진 동안 코드를 수정하고 저장하면, 브라우저 새로고침만으로 바로 반영된다.
종료할 땐 터미널에서 `Ctrl + C`.

---

## 3. 이번 라운드에서 새로 연결한 것

요구사항정의서의 온보딩 7화면과 챗봇 화면을 **실제로 클릭해서 끝까지 진행할 수 있게** 최소한으로 연결했다.
단, 병원 인증번호 검증 같은 **진짜 로직은 아직 없다** — 아무 전화번호/인증번호를 입력해도 통과된다.

| 화면 | 연결 방식 |
|---|---|
| 병원 선택 | 실제 DB의 `Hospital` 목록을 보여줌 |
| 병원 인증 | 입력값 검증 없이 그냥 다음 화면으로 진행 (`PatientVerificationCode` 모델 추가 후 채워야 함) |
| 정보 로딩 | 2초 후 자동으로 다음 화면 이동 (JS `setTimeout`) |
| 정보 확인 | 시드 데이터의 고정 환자(`p001`, 박하린) 정보를 보여줌 |
| 생활패턴/추가건강보고 | 입력값을 저장하지 않고 통과만 시킴 |
| 온보딩 완료 시점 | 고정 환자(`p001`)로 실제 로그인 처리 → 홈 화면 이동 |
| 챗봇 | `?state=chat`으로 대화 진행 상태, 기본값은 추천질문 화면 |

### `seed_demo` 명령이 만드는 데이터

```
python manage.py seed_demo
파일 경로 : patients > management > commands > seed_demo.py
```

- 병원 2곳(SKN정신병원, 마음편한의원), 의사 1명(doctor1)
- 환자 1명(p001, 박하린) — 온보딩 데모가 항상 이 환자로 로그인시킴
- 약물 2종, 처방 1건(약 2개 포함)
- 오늘 복약기록 2건(1개 완료·1개 미완료 — 위젯 "일부 완료" 상태 확인용)
- 지난 며칠 복약기록(캘린더 색상 확인용)
- 상담 이력 2건, 부작용 기록 1건
- 여러 번 실행해도 중복 생성되지 않음 (`get_or_create` 사용)

---

## 4. 백엔드 작업 필요

| 항목 | 상태 |
|---|---|
| 병원 인증번호 실제 검증 | `PatientVerificationCode` 모델(전화번호+코드+만료+사용여부) 신규 필요 |
| 온보딩 입력값(생활패턴/기저질환 등) 저장 | 지금은 입력받아도 DB에 안 남음, 뷰에 저장 로직 추가 필요 |
| 온보딩이 항상 고정 환자(p001)로 진행됨 | 실제 인증 완료 후 "그 전화번호의 진짜 환자"로 바뀌어야 함 |
| `chatbot_start` | 데모 메시지만 하드코딩, `pipeline.py` 실제 연동 필요 |
| 병용금기 경고 (처방약 추가 시) | UI/로직 둘 다 미착수 |
| Neo4j Personal Graph 연동 | Django 쪽에 전혀 안 붙어있음 |
| `DEBUG=True`, `SECRET_KEY` 등 | 개발용 설정 그대로, 배포 전 반드시 변경 필요 |
