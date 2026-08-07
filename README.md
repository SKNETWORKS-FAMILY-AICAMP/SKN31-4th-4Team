# SKN31-4th-4Team
# 💊 복약메이트 (BokYakMate) — 정신과 복약 관리 챗봇 웹 애플리케이션

<br>

<div align="center">
    <img src="/bokyakmate/image/bokyakmate_banner.png" width="600" height="600"></td>

## 팀 및 팀원 소개

| 이영창 | 김봉남 | 이재일 | 박하린 |
| :---: | :---: | :---: | :---: |
| <a href="https://github.com/<이영창-github-id>"><img src="https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=GitHub&logoColor=white"/></a> | <a href="https://github.com/<김봉남-github-id>"><img src="https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=GitHub&logoColor=white"/></a> | <a href="https://github.com/<이재일-github-id>"><img src="https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=GitHub&logoColor=white"/></a> | <a href="https://github.com/<박하린-github-id>"><img src="https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=GitHub&logoColor=white"/></a> |
| <img src="bokyakmate/image/team_02_이영창.png" width="150" height="170"> | <img src="bokyakmate/image/team_01_김봉남.png" width="150" height="170"> | <img src="bokyakmate/image/team_04_이재일.png" width="150" height="170"> | <img src="bokyakmate/image/team_03_박하린.png" width="150" height="170"> |
| <b>PM(대화엔진/리트리버)</b> | <b>기획/DB설계·구축/대화엔진</b> | <b>Web Beckend/그래프DB</b> | <b>Web F/B · AWS구축</b> |

</div>

## 팀원 소개

| 역할 | 이름 | 담당 업무 (R&R) |
|:---:|:---:|:---|
| **팀장** | **이영창** | • Retriever(검색기) 모델 및 알고리즘 설계• Django 백엔드 - 프론트엔드 연동 |
| **팀원** | **김봉남** | • 시스템 아키텍처 설계 <br>• Neo4j 기반 Graph DB 설계 — 약물 관계(병용금기·부작용) 모델링<br> • 복약/정신건강 상담 챗봇 시나리오 및 대화 엔진 개발 |
| **팀원** | **이재일** | • Django 백엔드 - 프론트엔드 연동 • 그래프 DB 구축 |
| **팀원** | **박하린** | • 환자용(Patient-facing) Django 화면 설계 및 구현 (MVT)<br> Django 백엔드 - 프론트엔드 연동 • AWS EC2/RDS 배포 (Gunicorn + Nginx, MySQL 마이그레이션) |

---

## 프로젝트 소개

### 주제

**복약메이트 — Personal Graph(PGHD)와 Medical Graph를 결합한 설명 가능(Explainable) 정신과 복약 상담 챗봇 웹 서비스**

환자 개인의 복약·증상 이력(Personal Graph)과 약물-질환-부작용-병용금기 지식(Medical Graph)을 Neo4j에서 함께 관리하고, Graph + Vector 하이브리드 검색으로 근거를 제시하는 개인화 RAG 챗봇을 Django 웹 애플리케이션으로 구축했습니다.

### 주제를 선택한 이유

- 정신과 약물은 환자의 나이, 임신 여부, 기저질환에 따라 주의사항이 크게 달라지지만, 병용금기(DUR)나 부작용 정보를 환자·보호자가 직접 확인하기는 쉽지 않습니다.
- 단순 텍스트 검색만으로는 "왜 이 약을 주의해야 하는지"에 대한 관계적 근거(약물-부작용-증상 연결)를 보여주기 어렵다고 판단했습니다.
- Personal Graph와 Medical Graph를 분리해 설계하면, 환자 개인 데이터와 공용 의학 지식을 함께 탐색하면서도 각 답변의 근거를 그래프 경로로 투명하게 제시할 수 있어 Explainable RAG 구조에 적합하다고 판단했습니다.
- 3차 프로젝트에서 구축한 문서 기반 QA 시스템을 실서비스 형태(Django + AWS EC2)로 전환하면서, 병용금기(DUR) 그래프 관계를 추가해 실제 임상 근거에 더 가까운 정보를 제공하고자 했습니다.

### 주요 기능

- 🟢 **개인화 복약 상담**: 환자의 나이·성별·임신 여부·기저질환·복용 약물을 반영한 맞춤 답변
- 🎯 **병용금기(DUR) 및 약물 상호작용 탐색**: `INTERACTS_WITH` 관계 기반 병용 주의 약물 확인
- 🟢 **부작용-증상 연관 분석**: `CAUSES_SIDE_EFFECT` · `PRESENTS_AS` 관계로 특정 증상이 질환 때문인지 약물 부작용 때문인지 구분
- 🟢 **상담 이력 관리**: `ChatSession` · `Message` 노드 및 Django 세션 생명주기 관리를 통해 대화 맥락을 저장하고 이후 상담에 활용
- 🎯 **Graph + Vector 하이브리드 검색**: 구조화된 병용금기/관계 정보는 Neo4j 그래프로, 자유 텍스트 약물 설명은 Qdrant 벡터 검색으로 대응
- 🟢 **Explainable 답변**: 답변 생성 시 참조한 그래프 경로 및 근거 문헌(Paper)을 함께 제시
- 🆕 **Django 웹 서비스화**: 기존 Streamlit 프로토타입을 Django MVT 구조로 전환, 커스텀 에러 페이지·하단 네비게이션 등 UI/UX 정비
- 🆕 **AWS 프로덕션 배포**: EC2(Gunicorn + Nginx) 및 RDS(MySQL) 기반 배포 환경 구축

---

## 🌐 AWS EC2 배포 URL

>[http://52.78.243.234/accounts/login/]

---

## 🏗️ 시스템 아키텍처

```
사용자 (Django 웹 브라우저)
        │
Django MVT (View / Template / URL Routing)
        │
LLM Entity/Relation Extraction (Pydantic Structured Output)
        │
   ┌────┴────┐
Personal Graph   Medical Graph
  (PGHD)        (Drug-Disease-SideEffect-DUR)
   └────┬────┘
Graph Retriever (Graph + Vector Hybrid) → 관련 Subgraph 생성
        │
LangGraph 기반 멀티 에이전트 파이프라인 → LLM
        │
Explainable Personalized Answer → Django Template 렌더링
```

### 배포 아키텍처

```
[ Client ]
    │  HTTPS
    ▼
[ Nginx ] ── 정적 파일 서빙 / 리버스 프록시
    │
[ Gunicorn ] ── WSGI 서버
    │
[ Django Application ]
    │
    ├── MySQL (AWS RDS) ── 서비스 정형 데이터
    ├── Neo4j ── Personal/Medical Graph
    └── Qdrant ── 약물 설명 임베딩 벡터 검색
```

---

## 🛠️ 기술 스택

| 구성 요소 | 기술 |
|---|---|
| Backend / Web Framework | Django (MVT) |
| Agent Workflow | LangGraph |
| LLM | GPT-5.4-mini (기본)|
| Personal Graph / Medical Graph | Neo4j |
| Vector DB | Qdrant |
| Embedding | text-embedding-3-large |
| Entity Extraction | Structured Output (Pydantic) |
| Retriever | Graph + Vector Hybrid |
| RDBMS | MySQL (AWS RDS) |
| 배포 인프라 | AWS EC2, Gunicorn, Nginx |

---

## 🗂️ GraphDB(Neo4j) 설계

Personal Graph와 Medical Graph를 하나의 Neo4j 데이터베이스에서 연결하여 관리합니다. `Patient` 노드를 중심으로 환자의 복약 정보, 증상, 기저질환, 상담 이력을 저장하며, `Drug` 노드는 질환(Disease), 부작용(SideEffect), 다른 약물(병용금기), 의학 논문(Paper)과 연결됩니다.

```text
                    ┌──────────────┐
                    │   Disease    │
                    └──────▲───────┘
                           │ TREATS
                    ┌──────┴───────┐
                    │    Drug      │
                    └───┬─────┬────┘
                        │     │
       CAUSES_SIDE_EFFECT│     │INTERACTS_WITH (병용금기)
                        │     │
                        ▼     ▼
                 ┌──────────┐  Drug
                 │SideEffect│
                 └────▲─────┘
                      │ PRESENTS_AS
                      ▼
                 ┌──────────┐
                 │ Symptom  │
                 └────▲─────┘
                      │ HAS_SYMPTOM
             ┌────────┴────────┐
             │     Patient      │
             └─┬─────┬──────┬───┘
               │     │      │
         TAKES │     │      │HAS_SESSION
               ▼     ▼      ▼
            Drug  Condition ChatSession
                            │
                     HAS_MESSAGE
                            ▼
                        Message
```

### Node 설계

| Node | 역할 | 주요 Property |
|------|------|--------------|
| Patient | 환자의 개인정보 및 건강정보를 저장하는 중심 노드 | patient_id, name, age, gender, pregnancy |
| Drug | 환자가 복용하는 약물 정보 | drug_id, drug_name, ingredient_code, category, dosage |
| Disease | 약물이 치료하는 질환 정보 | disease_name |
| SideEffect | 약물의 부작용 정보 | side_effect_name, frequency |
| Symptom | 환자가 경험하는 증상 | symptom_name, severity |
| Condition | 환자의 기저질환 | condition_name |
| ChatSession | 하나의 상담 세션 관리 | session_id, created_at |
| Message | 상담 중 발생한 대화 저장 | message_id, role, content, timestamp |
| Paper | 의학 논문 및 근거 문헌 | title, year, doi |

### Relationship 설계

| 관계 | From → To | 설명 |
|---|---|---|
| `TAKES` | Patient → Drug | 복용 중인 약물 |
| `TREATS` | Drug → Disease | 약물의 치료 질환 |
| `CAUSES_SIDE_EFFECT` | Drug → SideEffect | 약물의 부작용 |
| `PRESENTS_AS` | SideEffect → Symptom | 부작용의 증상 발현 |
| `HAS_SYMPTOM` | Patient → Symptom | 환자의 현재 증상 |
| `HAS_CONDITION` | Patient → Condition | 환자의 기저질환 |
| `INTERACTS_WITH` | Drug → Drug | **병용금기(DUR) 및 약물 상호작용** *(4차 신규)* |
| `HAS_SESSION` | Patient → ChatSession | 상담 세션 |
| `HAS_MESSAGE` | ChatSession → Message | 세션 내 대화 |
| `REFERENCED_BY` | Drug → Paper | 근거 문헌 |

---

## 🔎 Vector DB(Qdrant) 파이프라인

```
[ Raw Data Source ]
        │  약학정보원 크롤링 데이터 (medicine_new.xlsx)
        ▼
1. Data Parsing & Chunking
   · 엑셀 데이터를 Document 객체로 변환
   · 긴 텍스트는 800자 기준 안전 분할
   · 청크별 메타데이터 부여 (ingredient_code, section)
        ▼
2. Embedding (OpenAI text-embedding-3-large, BATCH_SIZE=100)
        ▼
3. Qdrant (Docker, Port 6333, Collection: medical_docs)
        ▼
4. Retrieval & Filtering (ingredient_code + section 조합 필터 쿼리)
```

### Qdrant 메타데이터 스키마

| 필드명 (Key) | 데이터 타입 | 예시 값 | 설명 |
| --- | --- | --- | --- |
| `ingredient_code` | `String` | `"626402ATR"` | 의약품 식별 고유 코드 |
| `section` | `String` | `"효능효과"`, `"용법용량"`, `"1. 경고"` | 약학 정보의 대분류/소분류 타이틀 |

---

## 📁 데이터 수집 출처

### 1. 정신질환 약물 데이터
약학정보원(https://health.kr/) 크롤링 수집 (Selenium + BeautifulSoup4 하이브리드 동적 크롤링)

| 단계 | 내용 | 출처 |
| --- | --- | --- |
| ① | 건강보험심사평가원_ATC코드 매핑 목록 | [링크](https://www.data.go.kr/data/15118958/fileData.do) |
| ② | 국민건강보험공단_주요 정신신경계 질환 환자 약 처방 현황 | [링크](https://www.data.go.kr/data/15143145/fileData.do) |
| ③ | ① + ② 매핑 → 정신신경계 질환 관련 약물 274종 추출 | - |
| ④ | 약학정보원 크롤링 → 265건 추출 | - |

### 2. 병용금기(DUR) 데이터
**건강보험심사평가원_의약품안전사용서비스(DUR) 의약품 목록** (20260601 기준)

- **출처**: [공공데이터 포털](https://www.data.go.kr/data/15127983/fileData.do)
- **형식**: CSV
- DUR(Drug Utilization Review)은 처방·조제 시 병용금기·연령금기·임부금기·노인주의 등 의약품 안전정보를 실시간으로 제공하는 서비스로, 본 프로젝트에서는 병용금기·연령금기·임부금기·노인주의 항목을 `INTERACTS_WITH` 관계로 Neo4j에 반영했습니다.

---

## 📂 폴더 구조

```
SKN31-4th-4Team/
├── .vscode/
│   └── settings.json
├── bokyakmate/                          # Django 프로젝트 루트
│   ├── Chatbot/                          # LangGraph 기반 챗봇 파이프라인
│   │   ├── builder.py                     # LangGraph 워크플로우(그래프) 빌더
│   │   ├── chat_node.py                   # 대화 노드(에이전트 스텝) 정의
│   │   ├── con_tools.py                   # 챗봇에서 사용하는 도구(Tool) 함수
│   │   ├── db_connect.py                  # Neo4j/DB 연결
│   │   ├── db_loader.py                   # 그래프 DB 데이터 로더
│   │   ├── qdrant_loader.py               # Qdrant 벡터 DB 로더
│   │   ├── session_summary.py             # 상담 세션 요약 생성
│   │   └── state.py                       # LangGraph 상태(State) 스키마
│   │
│   ├── accounts/                         # 로그인/인증 앱
│   │   ├── templates/accounts/
│   │   │   └── login.html
│   │   ├── models.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── config/                           # Django 프로젝트 설정
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   │
│   ├── patients/                         # 환자용(Patient-facing) 화면 — 메인 서비스 앱
│   │   ├── management/commands/
│   │   │   └── seed_demo.py                # 데모 데이터 시딩 커맨드
│   │   ├── migrations/
│   │   ├── static/patients/css/
│   │   │   └── main.css
│   │   ├── templates/patients/
│   │   │   ├── 400.html · 403.html · 403_csrf.html · 404.html · 500.html   # 커스텀 에러 페이지
│   │   │   ├── _bottom_nav.html            # 하단 네비게이션 (inclusion tag)
│   │   │   ├── calendar_day.html / dosing_calendar.html   # 복약 캘린더
│   │   │   ├── chat_history.html / chat_history_detail.html / chatbot.html  # 챗봇 대화
│   │   │   ├── mypage.html                 # 마이페이지
│   │   │   ├── onboarding_*.html           # 온보딩(건강정보 입력·병원 인증 등) 플로우
│   │   │   ├── patient_main.html           # 환자 홈
│   │   │   └── records.html                # 복약/증상 기록
│   │   ├── templatetags/
│   │   │   └── patient_tags.py             # 커스텀 템플릿 태그(하단 네비 등)
│   │   ├── models.py                       # Patient, ChatSession, SymptomLog 등
│   │   ├── urls.py
│   │   └── views.py
│   │
│   ├── services/                         # 도메인 서비스 레이어
│   │   ├── db_connector.py                 # DB 커넥터 공통 모듈
│   │   ├── end_summary.py                  # 상담 종료 시 요약 처리
│   │   └── medical_graph.py                # Medical Graph(Neo4j) 조회/조작 로직
│   │
│   ├── image/                            # README/서비스용 이미지 리소스
│   │   ├── bokyakmate_banner.png
│   │   └── team_0N_이름.png                 # 팀원 프로필 이미지
│   │
│   ├── manage.py
│   ├── langgraph_checkpoint.db            # LangGraph 체크포인트 저장소
│   └── README.md                          # 앱(bokyakmate) 단위 README
│
├── .gitignore
├── README.md                            # 프로젝트 최상위 README
└── requirements.txt
```
## 📁 산출물

| 산출물 | 링크 |
|---|---|
| 요구사항 정의서 | _(링크 입력 예정)_ |
| 화면 설계서 | _(링크 입력 예정)_ |
| 시스템 구성도 | 상단 아키텍처 참고 |
| 테스트 계획서 및 테스트 결과 보고서 | _(링크 입력 예정)_ |

---
