# 🏠 Sesac Final — 라이프 스타일 맞춤 AI 매물 추천 서비스

> **새싹(SeSAC) 3기 부트캠프 최종 프로젝트**  
> 직방(zigbang) 크롤링 데이터 + GPT-4o 기반으로 사용자의 라이프스타일을 분석해 서울시 매물을 추천하는 Flask 웹 애플리케이션

---

## 📌 프로젝트 개요

직방(zigbang.com)에서 수집한 매물 데이터를 MongoDB Atlas에 적재하고, 사용자가 라이프스타일 설문(10문항)을 완료하면 **교통·편의·녹지·놀이·건강·생활·안전** 7가지 지표를 가중치로 환산하고, MongoDB의 매물 데이터와 매칭하여 맞춤형 추천 결과를 제공합니다. 추천 결과에는 GPT가 작성한 개인화 추천 코멘트가 포함됩니다. 지도 기반 매물 탐색 및 AI 챗봇 자연어 검색도 지원합니다.

---

## 🗂 디렉토리 구조

```
Sesac_Final/
├── app.py                          # Flask 앱 진입점 (블루프린트 등록, OAuth 초기화)
├── house_project/
│   ├── database.py                 # MongoDB 연결, OAuth 객체
│   ├── main/
│   │   ├── main_route.py           # 메인 페이지 라우트 (/)
│   │   └── main.html               # 메인 화면
│   ├── auth/
│   │   ├── auth_route.py           # 회원가입, 로그인, 소셜 OAuth
│   │   ├── login.html
│   │   └── register.html
│   ├── survey/
│   │   ├── survey.py               # 설문 처리, 매물 매칭, AI 추천 코멘트 생성
│   │   ├── survey.html             # 라이프스타일 설문 페이지
│   │   ├── result.html             # 추천 결과 페이지
│   │   └── shorts.html             # 쇼츠형 매물 피드
│   ├── find_property/
│   │   ├── find_property.py        # 지도 기반 매물 탐색, AI 챗봇 검색
│   │   └── find_property.html
│   ├── mypage/
│   │   ├── mypage_route.py         # 마이페이지, 프로필 편집, 찜/설문 관리
│   │   ├── mypage.html
│   │   ├── edit_profile.html
│   │   └── delete_confirm.html
│   └── static/
│       ├── css/                    # 각 페이지별 CSS (common, auth, survey, result, mypage, find_property, shorts)
│       ├── image/                  # 소셜 로그인 아이콘 (Google, Kakao, Naver)
│       ├── img/                    # 메인 배경 이미지
│       └── profile_pics/           # 사용자 프로필 이미지 저장소
├── preprocessing/                  # 데이터 수집·전처리 스크립트
```

---

## 🛠 기술 스택

| 분류 | 기술 |
|------|------|
| **Backend** | Python 3.13, Flask, Blueprint |
| **Database** | MongoDB Atlas (pymongo), GeoJSON 위치 인덱스 |
| **AI / LLM** | LangChain + OpenAI GPT-4o-mini |
| **OAuth** | Authlib (Google / Naver / Kakao) |
| **Frontend** | HTML5, CSS3, Jinja2, Naver Maps API |
| **배포** | dotenv 환경변수 관리 |

---

## ✨ 주요 기능

### 1. 회원 인증 (`auth/`)
- 이메일·비밀번호 일반 가입 (bcrypt 해싱)
- **소셜 로그인**: Google OAuth, Naver OAuth, Kakao OAuth
- 가입 시 자동 임시 닉네임 발급 (`새싹XXXXX`)
- 세션 기반 로그인 유지 (10분 자동 만료)

### 2. 라이프스타일 설문 + AI 매물 추천 (`survey/`)
- **10문항 설문**: 라이프스타일 유형, 필수 시설, 예산, 계약 유형, 건물 조건 등
- 7개 카테고리(교통·편의·녹지·놀이·건강·생활·안전) 가중치 자동 산출
- 21가지 사용자 유형 분류 (예: 🚇 도심 직장인형, 🌿 힐링 라이프형 등)
- MongoDB `$geoNear` 집계 파이프라인으로 위치 기반 매물 매칭
- **GPT-4o-mini**가 상위 3개 매물에 대해 개인화 추천 코멘트 생성 (350~450자)
- **GPT 라이프스타일 분석 리포트**: 사용자 취향을 잡지 에디터 스타일로 분석
- 추천 가중치 실시간 슬라이더 재조정 (`/survey/recalculate`)
- 설문 결과 최대 10건 저장, 마이페이지에서 재열람 가능

### 3. 쇼츠형 매물 피드 (`/survey/short`)
- 비로그인 시 균등 가중치, 로그인 시 최근 설문 기반 개인화 피드
- 무한 스크롤 페이지네이션

### 4. 지도 기반 매물 탐색 (`find_property/`)
- **Naver Maps API** 연동 — 현재 지도 뷰포트 내 매물 핀 표시
- 필터: 계약 유형, 방 개수, 보증금/월세 범위, 면적, 주차 여부, 반지하 제외, 옵션 유무
- 서울 25개 구 중심 좌표 클러스터링
- **AI 챗봇 자연어 검색**: GPT가 대화 맥락을 누적 기억하며 필터 조건을 점진적으로 완성 → 매물 카드 추천

### 5. 마이페이지 (`mypage/`)
- 닉네임·한 줄 소개·프로필 사진 수정 (PNG/JPG/GIF 업로드)
- 비밀번호 변경 (소셜 로그인 계정 불가)
- 찜한 매물 목록 조회·삭제 (최대 10개)
- 내 설문 히스토리 조회·삭제 (단건/다중)
- 회원 탈퇴 (설문·계정 데이터 일괄 삭제)

---

## ⚙️ 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/abcicecream/Sesac_Final.git
cd Sesac_Final
git checkout develop
```

### 2. 의존 패키지 설치

```bash
pip install flask pymongo python-dotenv authlib langchain-openai werkzeug
```

### 3. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 값을 입력합니다.

```env
# Flask
FLASK_SECRET_KEY=your_secret_key

# MongoDB Atlas
MONGO_USER=your_mongo_username
MONGO_PASS=your_mongo_password
MONGO_CLUSTER=your_cluster_address

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Naver Maps API
NAVER_CLIENT_ID=your_naver_maps_client_id

# Naver Login OAuth
NAVER_CLIENT_LID=your_naver_login_client_id
NAVER_CLIENT_LSECRET=your_naver_login_client_secret

# Kakao OAuth
KAKAO_REST_API=your_kakao_rest_api_key
KAKAO_CLIENT_SECRET=your_kakao_client_secret
```

### 4. 서버 실행

```bash
cd house_project
python app.py
```

브라우저에서 `http://127.0.0.1:5000` 접속

---

## 🗄 MongoDB 컬렉션 구조

| 컬렉션 | 설명 |
|--------|------|
| `user` | 사용자 정보 (이메일, 닉네임, 프로필, 가중치, 찜 목록) |
| `properties_test2` | 매물 데이터 (주소, 가격, 면적, 카테고리 점수, GeoJSON 위치) |
| `infra` | 주변 인프라 POI 데이터 (GeoJSON, 카테고리) |
| `survey_results` | 사용자 설문 결과 및 AI 코멘트 캐시 |

---

## 🔑 주요 URL

| URL | 설명 |
|-----|------|
| `/` | 메인 페이지 |
| `/register` `/login` `/logout` | 회원가입 / 로그인 / 로그아웃 |
| `/login/google` `/login/naver` `/login/kakao` | 소셜 로그인 |
| `/survey` | 라이프스타일 설문 |
| `/survey/result/<index>` | 설문 결과 및 AI 추천 |
| `/survey/short` | 쇼츠형 매물 피드 |
| `/find` | 지도 기반 매물 탐색 |
| `/mypage` | 마이페이지 |
| `/edit` | 프로필 편집 |

---

## 📊 데이터

직방(zigbang.com)에서 수집한 서울 원룸·오피스텔 매물 데이터를 MongoDB Atlas에 적재하여 사용합니다.

수집 구: **서울시 전역**

매물 데이터 주요 필드: `address`, `rent_type`, `price`, `deposit`, `size_m2`, `floor`, `room_counts`, `hasParking`, `buildingUse`, `images`, `category_scores` (7개 지표 점수), `location` (GeoJSON Point)

---

## 👥 팀 정보

- **원본 레포지토리**: [SesacDobong3/Sesac_Final](https://github.com/SesacDobong3/Sesac_Final)
- **개발 브랜치**: `develop`
