# Flask 웹 프레임워크에서 필요한 기능들을 가져옴
# Blueprint: 기능별로 라우트를 묶는 모듈 단위
# render_template: HTML 파일을 사용자에게 보여줄 때 사용
# request: 사용자가 보낸 데이터(폼, JSON 등)를 읽을 때 사용
# jsonify: Python 데이터를 JSON 형태로 변환해서 응답할 때 사용
# session: 사용자별로 데이터를 잠깐 저장할 때 사용 (로그인 정보 등)
# redirect: 다른 URL로 이동시킬 때 사용
# url_for: URL을 자동으로 생성
# current_app: 현재 Flask 앱의 설정이나 상태에 접근할 때 사용
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
# database.py 파일에서 MongoDB 관련 객체를 가져옴
# houses_col : 집 데이터가 저장된 MongoDB 컬렉션
# db : MongoDB 데이터베이스 객체
from database import houses_col, db
# MongoDB에서 사용하는 고유 ID(ObjectId)를 다루기 위해 import
# 예: "65fae1b1a12d3c4f5a..." 같은 MongoDB 문서 ID
from bson.objectid import ObjectId
# 날짜와 시간을 다루기 위한 라이브러리
# 예: 현재 시간 기록 (로그 저장 등)
from datetime import datetime
# 리스트 안의 데이터 개수를 쉽게 세기 위한 도구
# 예: ["서울","서울","부산"] → 서울 2, 부산 1
from collections import Counter
# 운영체제(OS) 기능을 사용하기 위한 모듈
# 주로 환경 변수 읽기 등에 사용
import os
# .env 파일에 저장된 환경변수(API 키 등)를 불러오기 위한 라이브러리
from dotenv import load_dotenv
# LangChain에서 OpenAI GPT 모델을 사용하기 위한 클래스
# ChatOpenAI를 이용하면 GPT 모델에게 질문을 보내고 답변을 받을 수 있음
from langchain_openai import ChatOpenAI
# 프롬프트 템플릿을 만들기 위한 클래스
# AI에게 보낼 질문의 틀을 만들 때 사용
# 예: "다음 질문에 답해주세요: {question}"
from langchain_core.prompts import PromptTemplate
# 여러 작업을 동시에 실행할 수 있게 해주는 라이브러리
# 예: 추천 계산 + 데이터 조회 등을 동시에 처리해서 속도를 빠르게 함
import concurrent.futures
# 프로젝트 내부 constants 파일에서 TYPE_MAP을 가져옴
# TYPE_MAP은 집 유형 코드 → 실제 이름으로 변환할 때 사용하는 딕셔너리일 가능성이 높음
# 예: {"APT":"아파트", "OFF":"오피스텔"}
from src.core.constants import TYPE_MAP

# .env 파일에 있는 환경 변수를 프로그램에서 사용할 수 있게 로드
# override=True : 이미 존재하는 환경 변수도 덮어쓰기 허용
load_dotenv(override=True)

# ------------------------------------------------------------------
# AI 및 초기 설정
# ------------------------------------------------------------------

# 환경 변수에서 OpenAI API 키를 가져옴
# .env 파일 예시
# OPENAI_API_KEY=sk-xxxxxxx
api_key = os.getenv("OPENAI_API_KEY")


# GPT 모델 초기화 시도
# 오류가 발생할 수 있으므로 try-except 사용
try:
    # ChatOpenAI 객체 생성 (GPT 모델 사용 준비)
    
    # model="gpt-4o-mini"
    # → 사용할 OpenAI 모델 이름
    
    # temperature=0.5
    # → 답변의 창의성 정도
    # 0에 가까울수록 더 정확하고 동일한 답변
    # 1에 가까울수록 더 창의적인 답변
    
    # openai_api_key=api_key
    # → 위에서 가져온 OpenAI API 키 사용
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, openai_api_key=api_key)
     # GPT 모델이 정상적으로 초기화되면 콘솔에 메시지 출력
    print("✅ GPT 모델 초기화 성공")
except Exception as e:
     # GPT 초기화 중 오류가 발생하면 에러 메시지 출력
    print(f"❌ GPT 초기화 실패: {e}")

# Flask Blueprint 생성
# 'survey'라는 이름의 블루프린트를 만들어서
# 설문 관련 라우트(API, 페이지 등)를 이 모듈에서 관리함
#
# __name__ : 현재 파일 이름을 Flask가 인식하도록 전달
# template_folder='.' : HTML 템플릿 파일 위치 (현재 폴더)
survey_bp = Blueprint('survey', __name__, template_folder='.')

# ------------------------------------------------------------------
# 쇼츠(Shorts) 페이지 라우트 생성
# ------------------------------------------------------------------

# Flask Blueprint(survey_bp)에 '/shorts'라는 URL 경로를 연결
# 사용자가 웹 브라우저에서  /shorts  주소로 접속하면
# 바로 아래에 있는 shorts_page() 함수가 실행됨
@survey_bp.route('/shorts')
def shorts_page():
    # render_template는 HTML 파일을 브라우저에 보여주는 Flask 함수
    # templates 폴더에 있는 'shorts.html' 파일을 사용자에게 화면으로 반환함
    # 즉, /shorts 주소로 접속하면 shorts.html 페이지가 열림
    return render_template('shorts.html')

# ------------------------------------------------------------------
# 카테고리 영어 → 한국어 변환 딕셔너리
# ------------------------------------------------------------------

# category_map은 카테고리 코드를 한국어 이름으로 변환하기 위한 딕셔너리
# 예를 들어 DB에는 "traffic" 같은 영어 코드로 저장되어 있을 수 있는데
# 화면에서는 "교통"처럼 사용자에게 이해하기 쉽게 보여주기 위해 사용됨
category_map = {
    "traffic": "교통", "convenience": "편의", "green": "녹지",
    "play": "놀이", "health": "건강", "living": "생활", "safety": "안전"
}


# ------------------------------------------------------------
# 추천 매물에 대한 "추천 이유 설명"을 생성하는 함수
# ------------------------------------------------------------
# user_id   : 사용자 이메일 (DB에서 사용자 취향을 가져오기 위해 사용)
# nw        : 새로 계산된 사용자 가중치 (fallback용)
# house_info: 추천할 매물 정보 (주소, 가격, 카테고리 점수, 위치 등)
# ------------------------------------------------------------
def generate_recommendation_reason(user_id, nw, house_info):
    # MongoDB에서 해당 사용자 정보를 찾음
    # user 컬렉션에서 email이 user_id인 문서를 가져옴
    user_doc = db.user.find_one({"email": user_id})
    # 사용자의 취향 가중치 가져오기
    # DB에 Weight가 있으면 그것을 사용
    # 없으면 함수 인자로 받은 nw 사용
    actual_weight = user_doc.get("Weight", nw) if user_doc else nw
    
    # ------------------------------------------------------------
    # 사용자 취향 가중치 분석 (TOP 3 관심 카테고리 추출)
    # ------------------------------------------------------------

    # 가중치를 높은 순서로 정렬
    # actual_weight 예시
    # {"traffic":0.4,"green":0.2,"health":0.1}
    sorted_weights = sorted(actual_weight.items(), key=lambda x: x[1], reverse=True)
    # 상위 관심 카테고리 추출
    # - 의미 없는 작은 값(스무딩 값) 제거
    # - 최대 3개까지만 선택
    top_interests = [
        # category_map을 이용해서 영어 카테고리를 한국어로 변환
        # 예: traffic -> 교통
        # 가중치는 퍼센트로 변환
        f"{category_map.get(k, k)}({int(float(v)*100)}%)" 
         # sorted_weights를 반복하면서
          # 너무 작은 값은 제외 (추천 설명에 의미 없는 값 제거)
        for k, v in sorted_weights if float(v) > 0.015  
    ][:3] # 상위 3개만 사용
    
    # ------------------------------------------------------------
    # 매물의 카테고리 점수 정보 가져오기
    # ------------------------------------------------------------

    # house_info 안에 있는 category_scores 가져오기
    # 없으면 빈 딕셔너리
    scores = house_info.get('category_scores', {})

    # 점수를 문자열 리스트로 변환
    # 예: "교통 85점"
    all_scores = [f"{category_map.get(k.lower(), k)} {int(float(v)*100)}점" for k, v in scores.items() if float(v) > 0]
    
    # ------------------------------------------------------------
    # 매물 위치 좌표 추출 (위도, 경도)
    # ------------------------------------------------------------
    lng, lat = None, None
    # house_info 안에 location과 coordinates가 있는지 확인
    if 'location' in house_info and 'coordinates' in house_info['location']:
        coords = house_info['location']['coordinates']
        # 좌표가 [경도, 위도] 두 개로 구성되어 있는지 확인
        if len(coords) == 2:
            lng, lat = coords[0], coords[1]
    
    # ------------------------------------------------------------
    # 매물 주변 인프라(시설) 검색
    # ------------------------------------------------------------
    nearby_infra_names = []
     # 좌표가 존재할 때만 검색 수행
    if lat is not None and lng is not None:
        try:
             # MongoDB의 geoNear를 사용하여
            # 해당 위치 주변 인프라 검색
            infra_cursor = db.infra.aggregate([
                {
                    "$geoNear": {
                        # 기준 위치 (매물 위치)
                        "near": { "type": "Point", "coordinates": [float(lng), float(lat)] },
                         # 거리 필드 생성
                        "distanceField": "dist",
                         # 최대 거리 1000m (1km)
                        "maxDistance": 1000, 
                        # 지구 곡률 고려 거리 계산
                        "spherical": True
                    }
                },
                 # 최대 6개 시설만 가져오기
                { "$limit": 6 } 
            ])
              # 검색된 인프라 반복
            for doc in infra_cursor:
                # 시설 이름
                name = doc.get('name')
                # 시설 카테고리
                cat = doc.get('category', '')
                 # 영어 카테고리를 한국어로 변환
                cat_kr = category_map.get(cat, cat)
                # 이름이 있으면 리스트에 저장
                # 예: "서울숲(녹지)"
                if name: nearby_infra_names.append(f"{name}({cat_kr})")
        except Exception:
             # geo 검색 중 오류 발생 시 그냥 무시
            pass
    # ------------------------------------------------------------
    # 인프라 리스트를 문자열로 변환
    # ------------------------------------------------------------

    # 중복 제거 후 문자열로 합침
    # 주변 인프라 정보가 없으면 기본 문장 사용
    infra_str = ", ".join(list(set(nearby_infra_names))) if nearby_infra_names else "훌륭한 지역 상권 및 인프라"

     # ------------------------------------------------------------
    # GPT에게 보낼 프롬프트 템플릿
    # ------------------------------------------------------------
   
    template = """
    당신은 상위 1% VIP를 전담하는 수석 부동산 큐레이터입니다.
    제공된 [고객 분석 데이터]는 고객이 직접 선택한 '우선순위 가중치'입니다.

    [고객 분석 데이터] 최우선 선호 지표: {top_interests}
    [추천 매물 데이터] 주소: {address}, 가격: {price}
    [매물 평가 점수] {all_scores}
    [매물 주변 실제 인프라] {infra_str}

    [작성 가이드]
    1. 분량: 반드시 3~4개의 문단으로 구성된 긴 호흡의 글 (약 350~450자 분량)을 작성하세요. 절대 짧게 쓰지 마세요.
    2. 내용 구성:
       - 첫 문단: 반드시 고객님이 가장 중요하게 생각하시는 '{top_interests}' 항목들을 직접 언급하며 시작하세요. (예: "{top_interests}을 최우선으로 생각하시는 고객님을 위한 이 매물은...")
       - 두 번째 문단: [매물 평가 점수]에 명시된 구체적인 '점수 숫자'를 1~2개 언급하며 객관적인 강점을 논리적으로 어필하세요.
       - 세 번째 문단: [매물 주변 실제 인프라]에 나열된 장소 이름들(예: 특정 공원, 식당, 병원명 등)을 직접 언급하며, 이곳에 살면 어떤 프리미엄 일상을 누릴 수 있는지 시각적으로 묘사하세요.
    3. 톤앤매너: 5성급 호텔 컨시어지나 프라이빗 뱅커(PB)처럼 극도로 정중하고, 세련되며, 확신에 찬 어조를 사용하세요. (~입니다, ~누리실 수 있습니다)
    4. 제약사항: 0%이거나 데이터에 없는 내용은 절대 언급하지 말고, 문장 첫머리나 끝에 마크다운(```)이나 HTML 태그를 절대 넣지 마세요. 자연스러운 엔터(줄바꿈)만 사용하여 문단을 구분하세요.
    """
    # PromptTemplate 객체 생성
    prompt = PromptTemplate.from_template(template)
    # LangChain 체인 생성
    # prompt -> llm(GPT)
    chain = prompt | llm
    
    # ------------------------------------------------------------
    # GPT 실행
    # ------------------------------------------------------------
    try:
        response = chain.invoke({
            # 사용자 관심 카테고리
            "top_interests": ", ".join(top_interests),
            # 매물 주소
            "address": house_info.get('address', '정보 없음'),
            # 매물 가격
            "price": house_info.get('price_display', '정보 없음'),
            # 매물 점수
            "all_scores": ", ".join(all_scores),
            # 주변 인프라
            "infra_str": infra_str
        })
         # GPT 응답 반환
        # ``` 같은 코드블록 제거
        return response.content.replace("```", "").strip()
     # 오류 발생 시 기본 추천 문장 반환
    except Exception:
        return "고객님의 라이프스타일 지표를 분석한 결과, 가장 추천해 드리는 맞춤형 매물입니다."

def _parse_lifestyle_report(raw):
    """DB에 저장된 JSON 문자열을 Python 객체로 파싱."""
    import json as _json
    if not raw:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return _json.loads(raw)
    except Exception:
        # 파싱 실패 → None 반환해서 재생성 유도
        return None

def _to_manwon(value):
    """
    DB 금액을 만원 단위로 통일.
    숫자 또는 "전세 24000" 같은 문자열 모두 처리.
    원 단위(≥10,000,000)이면 /10,000.
    """
    # 정규표현식 라이브러리 import
    # 문자열에서 숫자만 추출하기 위해 사용
    import re as _re
    # ---------------------------------------------------
    # 1️⃣ 값이 아예 없는 경우
    # ---------------------------------------------------
    # None이면 금액 정보가 없는 것이므로 0 반환
    if value is None:
        return 0.0
    # ---------------------------------------------------
    # 2️⃣ 입력 값이 숫자인 경우 (int 또는 float)
    # ---------------------------------------------------
    if isinstance(value, (int, float)):
         # 숫자를 float 타입으로 변환
        # (정수든 실수든 동일하게 처리하기 위함)
        v = float(value)
        # 금액이 0 이하이면 의미 없는 값이므로 0 반환
        if v <= 0: return 0.0
        # 금액이 천만원 이상이면
        # → 원 단위로 저장된 것으로 판단
        # 예) 200000000원 → 20000만원
        if v >= 10_000_000: return v / 10_000
        # 이미 만원 단위로 저장된 경우
        # 그대로 반환
        return v
    
    # ---------------------------------------------------
    # 3️⃣ 입력 값이 문자열인 경우 처리
    # ---------------------------------------------------

    # 문자열로 변환
    # 예: "전세 24,000"
    # 금액에 포함된 콤마 제거
    # "24,000" → "24000"
    # 문자열 앞뒤 공백 제거
    s = str(value).replace(',', '').strip()

    # ---------------------------------------------------
    # 문자열 안에서 숫자만 추출
    # ---------------------------------------------------
    # 예:
    # "전세 24000" → 24000
    # "월세 1000" → 1000
    m = _re.search(r'[\d.]+', s)

    # 숫자가 전혀 없으면 금액 데이터가 아니므로 0 반환
    if not m: return 0.0

    # ---------------------------------------------------
    # 추출된 숫자를 float으로 변환
    # ---------------------------------------------------
    try:
        # m.group() → 정규식으로 찾은 숫자 문자열
        # 예: "24000"
        v = float(m.group())
    # 숫자로 변환 실패 시 (예외 처리)
    except ValueError:
        return 0.0
    
    # ---------------------------------------------------
    # 4️⃣ 숫자 값 검증
    # ---------------------------------------------------

    # 금액이 0 이하이면 의미 없는 값
    if v <= 0: return 0.0
    # 금액이 천만원 이상이면
    # → 원 단위로 저장된 금액으로 판단
    # 예: 200000000원
    # → 20000만원
    if v >= 10_000_000: return v / 10_000
     # 이미 만원 단위라면 그대로 반환
    return v


def get_vfm_score_100(house):
    # 문자열에서 숫자를 추출할 때 사용할 정규식 라이브러리
    import re as _re

    # 가성비 계산 기준
    YEARS = 3  # 3년 동안 거주한다고 가정
    RATE  = 0.04 # 연 이자율 4% (전세금/보증금의 기회비용 계산용)

    # 매물 유형별 통계 데이터
    # peak : 가장 많이 나타나는 값
    # mean : 평균 값
    # std  : 표준편차 (데이터 분산 정도)
    # 이 값들은 "㎡당 비용"을 비교할 때 기준으로 사용됨
    stats_map = {
        '전세_Normal':   {'peak': 99.4,  'mean': 96.2,  'std': 40.0},
        '월세_Normal':   {'peak': 91.9,  'mean': 124.8, 'std': 51.3},
        '월세_Basement': {'peak': 77.7,  'mean': 76.3,  'std': 22.3},
        '전세_Basement': {'peak': 26.4,  'mean': 31.7,  'std': 11.7},
    }

    # 매물의 거래 유형 (전세 / 월세)
    rent_type   = house.get('rent_type', '')
    # 층 정보 가져오기
    floor_str   = str(house.get('floor', ''))
    # 층 문자열에 '반지하'가 포함되어 있는지 확인
    is_basement = '반지하' in floor_str
    # 반지하이면 Basement, 아니면 Normal
    layer       = 'Basement' if is_basement else 'Normal'
    # 전세_Normal / 월세_Basement 같은 그룹 이름 생성
    group       = f"{rent_type}_{layer}"

    # 해당 그룹의 통계 데이터가 없으면 기본 점수 반환
    if group not in stats_map:
        print(f"[VFM] 알 수 없는 그룹: {group!r}")
        return 60.0

    # 해당 그룹의 통계 데이터 가져오기
    stats = stats_map[group]

    # ---------------------------------------------------
    # 면적 찾기
    # ---------------------------------------------------
    size = 0.0
    size_key_used = None
    # DB마다 면적 필드 이름이 다를 수 있기 때문에
    # 여러 키를 순서대로 확인
    for key in ('size_m2', 'area', 'size', 'supply_area', 'exclusive_area',
                'area_m2', 'private_area', 'net_area', 'living_area', '전용면적', '공급면적'):
        # 해당 키의 값 가져오기
        raw = house.get(key)

        # 값이 없으면 다음 키로 넘어감
        if raw is None:
            continue
        try:
            # 숫자라면 바로 float 변환
            candidate = float(raw)
        except (TypeError, ValueError):
            # 문자열일 경우 (예: "30㎡")
            # 문자열에서 숫자 부분만 추출
            m = _re.search(r'[\d.]+', str(raw))
            # 숫자가 있으면 float 변환
            candidate = float(m.group()) if m else 0.0
        # 유효한 면적이면 사용
        if candidate > 0:
            size = candidate
            size_key_used = key
            break
    # 면적을 찾지 못하면 기본 점수 반환
    if size <= 0:
        safe_keys = [k for k in house.keys()
                     if k not in ('_id', 'images', 'category_scores', 'ai_comments_v2')]
        print(f"[VFM] 면적 필드 없음 — rent_type={rent_type!r} 필드: {safe_keys}")
        return 60.0

    # ---------------------------------------------------
    # 금액을 "만원 단위"로 변환
    # ---------------------------------------------------
    # deposit : 보증금
    # price   : 월세 또는 전세금
    deposit = _to_manwon(house.get('deposit', 0))
    price   = _to_manwon(house.get('price',   0))

    # ---------------------------------------------------
    # 3년 동안 드는 총 비용 계산
    # ---------------------------------------------------
    if rent_type == '전세':
        # 전세의 경우 deposit이 없고 price에 전세금이 들어있는 경우가 있음
        real_deposit  = deposit if deposit > 0 else price
        # 전세는 실제로 월세를 내지 않지만
        # 전세금을 은행에 넣었다면 받을 수 있는 이자(기회비용)를 계산  
        total_expense = real_deposit * RATE * YEARS
    else:
        # 월세의 경우
        # 보증금 기회비용 + 월세 3년 비용
        total_expense = deposit * RATE * YEARS + price * 12 * YEARS

    # 총 비용이 이상하면 기본 점수 반환
    if total_expense <= 0:
        print(f"[VFM] total_expense=0 — deposit={deposit} price={price}")
        return 60.0

    # ---------------------------------------------------
    # ㎡당 비용 계산
    # ---------------------------------------------------
    # 집 크기로 나눠서
    # 면적 대비 비용을 계산
    expense_per_m2 = total_expense / size

    # ---------------------------------------------------
    # 가성비 점수 계산
    # ---------------------------------------------------

    # 평균값과 peak값 중 더 적절한 기준 선택
    center    = stats['peak'] if stats['mean'] > stats['peak'] * 1.1 else stats['mean']
    # 평균 대비 얼마나 싼지/비싼지 계산 (z-score)
    z         = (center - expense_per_m2) / stats['std']
    # 기본 점수 계산
    raw_score = 60.0 + (z * 18.0)

    # ---------------------------------------------------
    # 추가 점수 / 감점
    # ---------------------------------------------------

    # 보증금이 5500만원 이하이면 가산점
    # (최우선변제 보호 범위 고려)
    if deposit <= 5500:
        raw_score += 5
    # 면적이 너무 작은 경우 감점 (고시원급)
    if size < 15:
        raw_score -= 5   # 고시원급 감점

    # ---------------------------------------------------
    # 최종 점수 정리
    # ---------------------------------------------------

    # 점수를 0~100 사이로 제한
    # 소수점 한 자리까지 반올림
    final = round(max(0.0, min(100.0, raw_score)), 1)

     # 최종 가성비 점수 반환
    return final


def get_user_normalized_weights(category_log, custom_weights=None):
    # ------------------------------------------------------------
    # 사용자 관심 카테고리 가중치를 계산하는 함수
    # ------------------------------------------------------------
    # category_log  : 사용자가 조회하거나 클릭한 카테고리 기록
    #                  예) ["traffic", "traffic", "green", "safety"]
    #
    # custom_weights: 사용자가 직접 설정한 카테고리 중요도
    #                  예) {"traffic":3, "green":1, "safety":2}
    #
    # 이 함수의 목적
    # → 사용자 관심도를 기반으로 카테고리 가중치를 계산하고
    # → 모든 가중치의 합이 1이 되도록 정규화해서 반환
    # ------------------------------------------------------------


    # ------------------------------------------------------------
    # 1️⃣ 사용자가 직접 가중치를 설정한 경우
    # ------------------------------------------------------------
    if custom_weights:
        # custom_weights 딕셔너리에 있는 값들의 총합 계산
        # 예: {"traffic":3, "green":1, "safety":2}
        # → 3 + 1 + 2 = 6
        w_sum = sum(custom_weights.values())

        # 만약 사용자가 모든 값을 0으로 설정했다면
        # → 정규화 계산이 불가능하기 때문에
        # → 모든 카테고리에 동일한 가중치를 부여
        # category_map에는 전체 카테고리 목록이 들어 있음
        # (traffic, convenience, green, play, health, living, safety)
        if w_sum == 0: return {k: 1/7 for k in category_map.keys()}

        # 가중치를 정규화 (Normalization)
        # 목적: 모든 가중치의 합이 1이 되도록 만들기
        #
        # 예:
        # traffic = 3
        # green   = 1
        # safety  = 2
        #
        # 총합 = 6
        #
        # 정규화
        # traffic = 3/6 = 0.5
        # green   = 1/6 = 0.16
        # safety  = 2/6 = 0.33
        #
        # 이렇게 하면 추천 점수 계산에 바로 사용할 수 있음
        return {k: float(v) / w_sum for k, v in custom_weights.items()}

      # ------------------------------------------------------------
    # 2️⃣ 사용자가 가중치를 직접 설정하지 않은 경우
    # ------------------------------------------------------------
    # → 사용자 행동 로그(category_log)를 기반으로
    # → 관심 카테고리 가중치를 계산
    # ------------------------------------------------------------


    # 카테고리별 전체 시설 개수
    # (데이터 분석으로 미리 계산해 둔 값)
    #
    # 예
    # traffic      : 교통 시설 개수
    # convenience  : 편의 시설 개수
    # green        : 공원 / 녹지 시설
    # play         : 놀이 시설
    # health       : 병원 / 헬스
    # living       : 생활 시설
    # safety       : 안전 시설
    #
    # 이 값은 "빈도 보정"에 사용됨
    total_counts = {'traffic': 6, 'convenience': 10, 'green': 7, 'play': 6, 'health': 6, 'living': 13, 'safety': 10}

    # ------------------------------------------------------------
    # 사용자 행동 로그 분석
    # ------------------------------------------------------------
    # Counter를 사용하면 리스트 안의 값 개수를 자동으로 세줌
    #
    # 예
    # category_log = ["traffic","traffic","green","safety"]
    #
    # 결과
    # {
    #   "traffic":2,
    #   "green":1,
    #   "safety":1
    # }
    log_counts = Counter(category_log)

    # ------------------------------------------------------------
    # 사용자 관심도 가중치 계산
    # ------------------------------------------------------------
    # 공식
    #
    # (사용자가 본 횟수 + 1) / 전체 시설 개수
    #
    # +1을 하는 이유
    # → Laplace smoothing (라플라스 스무딩)
    # → 사용자가 안 본 카테고리도 최소 관심도를 부여
    #
    # 전체 시설 개수로 나누는 이유
    # → 카테고리 규모 차이 보정
    #
    # 예
    #
    # traffic 시설 = 6개
    # living 시설 = 13개
    #
    # 사용자 로그
    #
    # traffic = 2
    # living = 2
    #
    # 그냥 사용하면
    # traffic = 2
    # living = 2
    #
    # 하지만 보정하면
    #
    # traffic = (2+1) / 6  = 0.5
    # living  = (2+1) / 13 = 0.23
    #
    # → 교통에 더 관심 있는 것으로 판단
    user_weights = {cat: ((log_counts.get(cat, 0) + 1) / total_counts[cat]) for cat in total_counts}
    # ------------------------------------------------------------
    # 가중치 총합 계산
    # ------------------------------------------------------------
    # 정규화를 위해 모든 가중치를 더함
    w_sum = sum(user_weights.values())

    # ------------------------------------------------------------
    # 가중치 정규화
    # ------------------------------------------------------------
    # 모든 가중치 합을 1로 맞춤
    #
    # 예
    #
    # traffic = 0.5
    # green   = 0.28
    # safety  = 0.2
    #
    # 총합 = 0.98
    #
    # 정규화 후
    #
    # traffic = 0.5 / 0.98
    # green   = 0.28 / 0.98
    # safety  = 0.2 / 0.98
    #
    # 이렇게 하면 추천 점수 계산 시
    # 각 카테고리 영향도를 정확히 반영할 수 있음
    return {k: v / w_sum for k, v in user_weights.items()}

def format_property_data(houses, user_liked_ids=None):
    """
    DB에서 가져온 매물 데이터를 프론트엔드(웹페이지)에서 사용하기 좋게 가공하는 함수

    houses : MongoDB에서 조회한 매물 리스트
    user_liked_ids : 사용자가 '좋아요'를 누른 매물 ID 리스트 (선택값)

    반환값 : 화면에서 바로 사용할 수 있도록 가공된 매물 리스트
    """
     # houses 리스트 안에 있는 매물들을 하나씩 처리
    for h in houses:
        # ---------------------------------------------------
        # 1️⃣ MongoDB ObjectId → 문자열로 변환
        # ---------------------------------------------------
        # MongoDB의 _id는 ObjectId 타입이라
        # JS나 HTML에서 비교하거나 사용하기 불편함
        # 그래서 문자열 형태로 변환해서 따로 저장
        h['_id_str'] = str(h['_id'])

        # ---------------------------------------------------
        # 2️⃣ 거래 유형과 가격 가져오기
        # ---------------------------------------------------
        # rent_type : 거래 유형 (전세 / 월세)
        # price : 월세 또는 전세금
        rt, p = h.get('rent_type'), h.get('price', 0)

        # ---------------------------------------------------
        # 3️⃣ 화면에 보여줄 가격 문자열 생성
        # ---------------------------------------------------
        # 전세 → "20000"
        # 월세 → "1000/50" (보증금/월세)
        h['price_display'] = f"{p}" if rt == "전세" else f"{h.get('deposit',0)}/{p}"
        
        # ---------------------------------------------------
        # 4️⃣ 이미지 리스트 가져오기
        # ---------------------------------------------------
        # DB에 저장된 이미지 URL 리스트
        raw_imgs = h.get('images', [])

         # ---------------------------------------------------
        # 5️⃣ 이미지 사이즈 파라미터 추가
        # ---------------------------------------------------
        # 이미지 URL 뒤에 width=800 옵션을 추가
        # 이미 ?가 있는 경우 → &w=800
        # 없는 경우 → ?w=800
        # 목적 : 이미지 크기 통일 및 로딩 최적화
        processed_imgs = [img + ('&w=800' if '?' in img else '?w=800') for img in raw_imgs]

        # ---------------------------------------------------
        # 6️⃣ 이미지가 없는 경우 기본 이미지 사용
        # ---------------------------------------------------
        # 매물에 이미지가 하나도 없으면
        # 기본 방 이미지를 사용
        if not processed_imgs:
            processed_imgs = [url_for('static', filename='img/default_room.jpg')]

        # ---------------------------------------------------
        # 7️⃣ 가공된 이미지 리스트 저장
        # ---------------------------------------------------
        h['images'] = processed_imgs

        # ---------------------------------------------------
        # 8️⃣ 대표 이미지 설정
        # ---------------------------------------------------
        # 첫 번째 이미지를 대표 이미지로 사용
        # (리스트의 첫 번째 요소)
        h['main_image'] = processed_imgs[0]
        

        # ---------------------------------------------------
        # 9️⃣ 카테고리 점수 가져오기
        # ---------------------------------------------------
        # 매물 주변 환경 점수
        # 예
        # {
        #   traffic:0.8,
        #   convenience:0.7,
        #   green:0.6
        # }
        scores = h.get('category_scores', {})

        # ---------------------------------------------------
        # 🔟 차트 데이터 생성
        # ---------------------------------------------------
        # 프론트에서 레이더 차트를 그리기 위해
        # 점수를 0~100 점수로 변환
        #
        # 예
        # traffic:0.83 → 83.0
        h['chart_data'] = [round(float(scores.get(c, 0)) * 100, 1) for c in ['traffic', 'convenience', 'green', 'play', 'health', 'living', 'safety']]
        # ---------------------------------------------------
        # 1️⃣1️⃣ 좋아요 여부 초기값
        # ---------------------------------------------------
        # 기본값은 False (좋아요 안 누름)
        h['is_liked'] = False

        # ---------------------------------------------------
        # 1️⃣2️⃣ 사용자가 좋아요 누른 매물인지 확인
        # ---------------------------------------------------
        # user_liked_ids에 현재 매물 id가 있으면
        # 좋아요 상태 True
        if user_liked_ids and h['_id_str'] in user_liked_ids:
            h['is_liked'] = True
        # 가성비 점수 계산

        # ---------------------------------------------------
        # 1️⃣3️⃣ 가성비 점수 계산
        # ---------------------------------------------------
        # 매물 가격 / 면적 등을 기반으로
        # 가성비 점수를 계산하는 함수 호출
        #
        # 결과 : 0~100 점수
        h['vfm_score'] = get_vfm_score_100(h)
    # ---------------------------------------------------
    # 모든 매물 데이터 가공 완료 후 반환
    # ---------------------------------------------------
    return houses

def build_match_pipeline(match_query, nw, target_coords=None, limit=10, is_random=False, use_vfm=False):
    """
    MongoDB Aggregation Pipeline을 생성하는 함수.
    사용자 취향 가중치와 위치 정보를 기반으로 매물 추천 점수(match_score)를 계산한다.

    match_query : MongoDB 매물 필터 조건 (가격, 전세/월세, 방 개수 등)
    nw          : 사용자 라이프스타일 가중치 (예: 교통 0.4, 녹지 0.2 ...)
    target_coords : 사용자 기준 위치 (위도, 경도)
    limit       : 가져올 매물 개수
    is_random   : 랜덤 추천 여부
    use_vfm     : 가성비 점수(VFM)를 사용할지 여부

    추천 점수 구조
    -------------------------
    기본 구조
        라이프스타일 점수 + 거리 점수

    use_vfm=True일 때
        라이프스타일 56%
        거리 14%
        가성비 30% (Python 후처리)
    """
     # MongoDB aggregation pipeline을 저장할 리스트
    pipeline = []

    # -----------------------------------------------------------
    # 1️⃣ 라이프스타일 점수 계산식 생성
    # -----------------------------------------------------------
    # category_scores는 매물 주변 환경 점수
    # 예:
    # category_scores = {
    #   traffic: 0.8,
    #   convenience: 0.7,
    #   green: 0.5
    # }
    #
    # nw는 사용자 취향 가중치
    # 예:
    # nw = {
    #   traffic: 0.4,
    #   convenience: 0.2,
    #   green: 0.4
    # }
    #
    # 최종 계산식
    # (traffic 점수 × 사용자 가중치)
    # + (convenience 점수 × 사용자 가중치)
    # + ...
    #
    # $ifNull은 해당 점수가 없는 경우 0으로 처리
    lifestyle_score_expr = {"$add": [{"$multiply": [{"$ifNull": [f"$category_scores.{c}", 0]}, nw[c]]} for c in nw]}

    # -----------------------------------------------------------
    # 2️⃣ 사용자 위치가 있는지 확인
    # -----------------------------------------------------------
    # 거리 기반 추천을 할 수 있는지 체크
    has_coords = target_coords and 'lng' in target_coords and 'lat' in target_coords and float(target_coords.get('lat', 0)) != 0

    # -----------------------------------------------------------
    # 3️⃣ 위치 기반 검색 (geoNear)
    # -----------------------------------------------------------
    if has_coords:
        # geoNear는 MongoDB의 위치 기반 검색 기능
        # 특정 좌표 기준으로 가까운 매물을 찾는다.
        pipeline.append({
            "$geoNear": {
                # 기준 위치
                "near": {"type": "Point", "coordinates": [float(target_coords['lng']), float(target_coords['lat'])]},
                # 거리 계산 결과를 저장할 필드
                "distanceField": "distance_meters",
                # 지구 곡률을 고려한 거리 계산
                "spherical": True,
                # 추가 필터 조건 (가격, 전세/월세 등)
                "query": match_query
            }
        })
        # -----------------------------------------------------------
        # 4️⃣ 거리 점수 계산
        # -----------------------------------------------------------
        # 거리 계산 방식
        #
        # 5000m 기준
        # 가까울수록 점수가 높다.
        #
        # 예
        # 거리 100m → 높은 점수
        # 거리 4km → 낮은 점수
        #
        # 계산식
        # (5000 - 거리) / 50
        dist_score_expr = {"$divide": [{"$max": [0, {"$subtract": [5000, "$distance_meters"]}]}, 50]}

        # -----------------------------------------------------------
        # 5️⃣ 최종 추천 점수 계산
        # -----------------------------------------------------------
        if use_vfm:
            # 가성비 사용
            # 라이프스타일 56%
            # 거리 14%
            # 가성비 30% (Python에서 나중에 계산)
            base_expr = {"$add": [
                {"$multiply": [lifestyle_score_expr, 100, 0.56]},
                {"$multiply": [dist_score_expr, 0.14]}
            ]}
        else:
            # 가성비 사용 안할 때
            # 라이프스타일 70%
            # 거리 30%
            base_expr = {"$add": [
                {"$multiply": [lifestyle_score_expr, 100, 0.7]},
                {"$multiply": [dist_score_expr, 0.3]}
            ]}
    # -----------------------------------------------------------
    # 6️⃣ 위치 정보가 없는 경우
    # -----------------------------------------------------------
    else:
        # 단순 필터 검색
        pipeline.append({"$match": match_query})
        # 거리 점수가 없으므로 라이프스타일 점수만 사용
        if use_vfm:
            # 라이프스타일 70%
            # 가성비 30% (Python 후처리)
            base_expr = {"$multiply": [lifestyle_score_expr, 70]}  # 70% (가성비 30% Python 후처리)
        else:
            # 라이프스타일만 100%
            base_expr = {"$multiply": [lifestyle_score_expr, 100]}

    # -----------------------------------------------------------
    # 7️⃣ match_score 필드 생성
    # -----------------------------------------------------------
    # 매물 추천 점수 계산
    # 소수점 1자리까지 반올림
    pipeline.append({"$addFields": {"match_score": {"$round": [base_expr, 1]}}})


    # -----------------------------------------------------------
    # 8️⃣ 랜덤 추천 모드
    # -----------------------------------------------------------

    if is_random:
        # 점수 너무 낮은 매물 제거
        pipeline.append({"$match": {"match_score": {"$gte": 35.0}}})
         # 랜덤 샘플링
        pipeline.append({"$sample": {"size": limit}})

    # -----------------------------------------------------------
    # 9️⃣ 일반 추천 모드
    # -----------------------------------------------------------
    else:
        # 추천 점수 높은 순 정렬
        pipeline.append({"$sort": {"match_score": -1}})
         # 상위 limit 개수만 가져오기
        pipeline.append({"$limit": limit})
     # -----------------------------------------------------------
    # 🔟 최종 pipeline 반환
    # -----------------------------------------------------------
    return pipeline


def apply_vfm_to_results(houses):
    # houses 리스트 안에 있는 각 주택 데이터를 하나씩 꺼내어 반복 처리합니다.
    for h in houses:
        # 1. 'vfm_score'(가성비 점수)를 가져옵니다. 
        #    만약 데이터에 해당 키가 없으면 기본값으로 60.0을 사용합니다.
        vfm = h.get('vfm_score', 60.0)
        # 2. 새로운 매칭 점수를 계산하여 업데이트합니다.
        #    기존 매칭 점수에 '가성비 점수의 30%(0.3)'를 더한 뒤, 
        #    소수점 첫째 자리까지 반올림(round)합니다.
        h['match_score'] = round(h.get('match_score', 0) + vfm * 0.3, 1)
    # 3. 모든 계산이 끝난 후, houses 리스트를 'match_score' 기준으로 정렬합니다.
    #    reverse=True를 사용하여 점수가 높은 순서(내림차순)로 배치합니다.
    houses.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    # 4. 점수 계산과 정렬이 완료된 최종 리스트를 반환합니다.
    return houses


def apply_detail_filters(query, selected_survey):
    # ---------------------------------------------------------
    # 사용자가 설문에서 선택한 조건을 기반으로
    # MongoDB 검색 query에 "세부 필터"를 추가하는 함수
    #
    # query : MongoDB 기본 검색 조건 (dict 형태)
    # selected_survey : 사용자가 설문에서 선택한 값들
    #
    # 예)
    # selected_survey = {
    #   "max_building_age": 10,
    #   "min_room_count": 2,
    #   "parking": "필요해요"
    # }
    # ---------------------------------------------------------

    # 현재 연도를 가져옴 (건물 나이 계산에 사용)
    
    current_year = datetime.now().year

    # ---------------------------------------------------------
    # 1️⃣ 건물 나이 필터
    # ---------------------------------------------------------

    # 설문에서 선택한 "최대 건물 나이"
    # 예: 10년 이하
    max_age = selected_survey.get('max_building_age')  
    # max_age 값이 존재하는 경우 (새로운 설문 방식)
    if max_age is not None:
        try:
            # 문자열일 수도 있으므로 숫자로 변환
            max_age = int(max_age)
            # 허용 가능한 가장 오래된 건물 연도 계산
            # 예: 현재 2026년이고 max_age = 10이면
            # 2026 - 10 = 2016
            oldest_year = str(current_year - max_age)
            # MongoDB query에 건물 연도 조건 추가
            # built_year 또는 year_built 둘 중 하나라도 조건을 만족하면 허용
            query.setdefault("$and", []).append({"$or": [
                {"built_year": {"$gte": oldest_year}},
                {"year_built": {"$gte": oldest_year}}
            ]})
         # 숫자로 변환 실패 시 오류 무시
        except (TypeError, ValueError):
            pass
    else:
        # ---------------------------------------------------------
        # 구형 설문 방식 (fallback)
        # 예: "신축", "준신축", "구축"
        # ---------------------------------------------------------
        b_age = selected_survey.get('building_age', [])
        if b_age:
            age_conditions = []
             # 선택된 건물 나이 조건들을 순회
            for age in b_age:
                # 신축: 5년 이하
                if "신축" in age:
                    age_conditions += [{"built_year": {"$gte": str(current_year - 5)}}, {"year_built": {"$gte": str(current_year - 5)}}]
                # 준신축: 5~10년
                elif "준신축" in age:
                    age_conditions += [{"built_year": {"$gte": str(current_year - 10), "$lt": str(current_year - 5)}}, {"year_built": {"$gte": str(current_year - 10), "$lt": str(current_year - 5)}}]
                 # 구축: 10년 이상
                elif "구축" in age:
                    age_conditions += [{"built_year": {"$lt": str(current_year - 10), "$gte": "1000"}}, {"year_built": {"$lt": str(current_year - 10), "$gte": "1000"}}]
             # 조건이 존재하면 query에 추가
            if age_conditions:
                query.setdefault("$and", []).append({"$or": age_conditions})

    # ---------------------------------------------------------
    # 2️⃣ 방 개수 필터
    # ---------------------------------------------------------

    # 슬라이더로 선택한 최소 방 개수
    # 예: 1, 2, 3
    min_rooms = selected_survey.get('min_room_count')   # 1, 2, 3
    if min_rooms is not None:
        try:
            # 숫자로 변환
            min_rooms = int(min_rooms)
            # 1개 이상 → 모든 집 허용
            if min_rooms == 1:
                pass  
            # 2개 이상
            elif min_rooms == 2:
                query.setdefault("$and", []).append({"$or": [
                    {"room_counts": "2개"},
                    {"room_counts": {"$regex": "^[3-9]개|^[1-9][0-9]+개"}}
                ]})
             # 3개 이상
            elif min_rooms >= 3:
                query.setdefault("$and", []).append({"room_counts": {"$regex": "^[3-9]개|^[1-9][0-9]+개"}})
         # 숫자 변환 오류 방지
        except (TypeError, ValueError):
            pass
    else:
        # ---------------------------------------------------------
        # 구형 설문 방식 (room_count 리스트)
        # ---------------------------------------------------------
        r_count = selected_survey.get('room_count', [])
        if r_count:
            room_conditions = []
            for rc in r_count:
                if rc == "1개": room_conditions.append({"room_counts": "1개"})
                elif rc == "2개": room_conditions.append({"room_counts": "2개"})
                elif rc == "3개 이상":
                    room_conditions.append({"room_counts": {"$regex": "^[3-9]개|^[1-9][0-9]+개"}})
            if room_conditions:
                query.setdefault("$and", []).append({"$or": room_conditions})
    # ---------------------------------------------------------
    # 3️⃣ 반지하 회피 필터
    # ---------------------------------------------------------
    # 특수 방 조건
    s_room = selected_survey.get('special_room', "")

    # 사용자가 "반지하 피하고 싶어요" 선택 시
    if "피하고 싶어요" in s_room:
        query.setdefault("$and", []).append({"floor": {"$not": {"$regex": "반지하|([0-9]+)\\s*[/중]\\s*\\1(?:[^0-9]|$)"}}})

    # 의미
    # 반지하 또는 특정 지하 형태를 제외

    # ---------------------------------------------------------
    # 4️⃣ 주차 가능 여부 필터
    # ---------------------------------------------------------
    park = selected_survey.get('parking', "")
    # 사용자가 주차 필요 선택 시
    if "필요해요" in park:
        # "주차 불가능" 매물 제외
        query["hasParking"] = {"$ne": "주차 불가능"}

    # ---------------------------------------------------------
    # 최종 필터가 적용된 MongoDB query 반환
    # ---------------------------------------------------------
    return query


# /survey 주소로 접속하면 실행되는 Flask 라우트
@survey_bp.route('/survey')
def survey_page():
    # ---------------------------------------------------------
    # 1️⃣ 로그인 여부 확인
    # ---------------------------------------------------------
    # session 안에 'user_id'가 없으면 로그인하지 않은 상태
    if 'user_id' not in session:
        # JavaScript로 알림창을 띄우고 로그인 페이지로 이동
        return "<script>alert('로그인이 필요한 서비스입니다.'); window.location.href='/login';</script>"
    # ---------------------------------------------------------
    # 2️⃣ 네이버 API Client ID 가져오기
    # ---------------------------------------------------------
    # Flask 설정(config)에 저장된 NAVER_CLIENT_ID 값을 가져옴
    # 지도 API 등에서 사용할 수 있음
    client_id = current_app.config.get('NAVER_CLIENT_ID')

    # ---------------------------------------------------------
    # 3️⃣ 설문 질문 데이터 정의
    # ---------------------------------------------------------
    # 설문 전체 질문을 리스트 형태로 정의
    # 각 질문은 dictionary 구조
    # survey.html 템플릿에서 이 데이터를 사용해 질문을 화면에 출력함
    questions = [
        # ---------------------------------------------------------
        # 질문 1
        # ---------------------------------------------------------
        {"title": "현재 나의 라이프스타일과 가장 가까운 유형은?", 
        "multiple": False, # multiple = False → 하나만 선택 가능
        # 선택지 리스트
        
        # ---------------------------------------------------------
        # 질문 2
        # ---------------------------------------------------------
        "options": [{"text": "갓생형 (운동과 자기계발)", 
                     "categories": ["health", "living"]}, {"text": "인싸형 (문화생활, 모임)", "categories": ["play", "convenience"]}, {"text": "워라밸형 (휴식, 여유)", "categories": ["green", "living"]}, {"text": "효율형 (이동 효율 중시)", "categories": ["traffic", "living"]}]},
        {"title": "이사 갈 집 주변에 '꼭' 있어야 하는 시설은? (최대 3개)", "multiple": True, "max_choice": 3, "options": [{"text": "지하철/버스역", "categories": ["traffic"]}, {"text": "대형마트", "categories": ["convenience", "living"]}, {"text": "공원/산책로", "categories": ["green", "health"]}, {"text": "CCTV/파출소", "categories": ["safety"]}]},
        {"title": "주말 아침, 집 근처에서 즐기고 싶은 루틴은?", "multiple": False, "options": [{"text": "브런치 카페와 쇼핑", "categories": ["convenience", "play"]}, {"text": "조깅과 야외 운동", "categories": ["green", "health"]}, {"text": "조용한 독서와 휴식", "categories": ["living", "green"]}]},
        {"title": "퇴근 후 귀갓길에 가장 중요하게 생각하는 풍경은?", "multiple": False, "options": [{"text": "집 앞까지 이어지는 밝은 가로등", "categories": ["safety", "living"]}, {"text": "장보기가 쉬운 마트", "categories": ["convenience", "living"]}, {"text": "빠른 환승 노선", "categories": ["traffic"]}]},
        {"title": "동네를 산책할 때 가장 기분 좋은 순간은?", "multiple": False, "options": [{"text": "예쁜 상점 구경", "categories": ["play", "convenience"]}, {"text": "나무 냄새와 흙길", "categories": ["green", "health"]}, {"text": "깨끗하고 안전한 길", "categories": ["safety", "living"]}]},
        {"title": "친구들을 동네로 초대한다면 어디로?", "multiple": False, "options": [{"text": "핫플레이스 맛집", "categories": ["play", "convenience"]}, {"text": "탁 트인 대형 공원", "categories": ["green", "play"]}, {"text": "교통이 편리한 곳", "categories": ["traffic", "convenience"]}, {"text": "조용한 카페/도서관", "categories": ["living", "safety"]}]},
        {"title": "이사 후 동네 탐방 시 가장 먼저 찾을 곳은?", "multiple": False, "options": [{"text": "마트 위치", "categories": ["convenience", "living"]}, {"text": "치안센터/경찰서", "categories": ["safety"]}, {"text": "지하철역 지름길", "categories": ["traffic"]}]},
        {"title": "몸이 조금 아플 때, 나는 보통?", "multiple": False, "options": [{"text": "근처 병원 방문", "categories": ["health", "convenience"]}, {"text": "집에서 휴식", "categories": ["safety", "living"]}, {"text": "가벼운 산책", "categories": ["health", "green"]}]},
        {"title": "이런 곳은 정말 피하고 싶어요!", "multiple": False, "options": [{"text": "치안 시설이 먼 곳", "categories": ["safety"]}, {"text": "밤길이 너무 어두운 곳", "categories": ["safety", "traffic"]}, {"text": "편의시설이 없는 곳", "categories": ["convenience", "safety"]}]},
        {"title": "집 근처 5분 거리에 상점이 들어온다면?", "multiple": False, "options": [{"text": "24시 대형 마트", "categories": ["convenience", "living"]}, {"text": "코인 노래방/영화관", "categories": ["play"]}, {"text": "종합 검진 센터", "categories": ["health", "safety"]}]}
    ]
    # ---------------------------------------------------------
    # 4️⃣ survey.html 페이지 렌더링
    # ---------------------------------------------------------
    # questions 데이터를 HTML로 전달
    # survey.html에서 질문과 선택지를 화면에 출력
    return render_template('survey.html', questions=questions, client_id=client_id)


# ---------------------------------------------------------
# /survey/save 주소로 POST 요청이 오면 실행되는 API
# 설문 결과를 받아 MongoDB에 저장하는 역할
# ---------------------------------------------------------
@survey_bp.route('/survey/save', methods=['POST'])
def save_survey():
     # ---------------------------------------------------------
    # 1️⃣ 로그인 여부 확인
    # ---------------------------------------------------------
    # session에 user_id가 없으면 로그인하지 않은 상태
    if 'user_id' not in session:
        # JSON 형태로 오류 메시지 반환
        # 401은 "Unauthorized(인증 필요)" 상태 코드
        return jsonify({"status": "error", "message": "로그인 필요"}), 401

    # ---------------------------------------------------------
    # 2️⃣ 로그인한 사용자 ID 가져오기
    # ---------------------------------------------------------
    user_id = session['user_id']
    # ---------------------------------------------------------
    # 3️⃣ 프론트엔드에서 보낸 설문 데이터(JSON) 받기
    # ---------------------------------------------------------
    # 예: fetch("/survey/save", { method:"POST", body: JSON })
    data = request.get_json() 
    
    # ---------------------------------------------------------
    # 4️⃣ 예산(budget) 데이터 가져오기
    # ---------------------------------------------------------
    # budget 구조 예시
    # {
    #   min_dep: 1000,
    #   max_dep: 3000,
    #   min_rent: 40,
    #   max_rent: 70
    # }
    budget_raw = data.get('budget', {})

     # ---------------------------------------------------------
    # 5️⃣ 예산 값을 숫자로 변환하는 함수
    # ---------------------------------------------------------
    def parse_budget(val):
        try:
            # 값이 없거나 빈 문자열이면 None 반환
            if val is None or str(val).strip() == "": return None
              # 문자열 "100.0" 같은 값도 처리하기 위해
            # float → int 순서로 변환
            # 예: "100.0" → 100
            return int(float(val))
         # 숫자로 변환 실패 시 None 반환
        except: return None
    # ---------------------------------------------------------
    # 6️⃣ MongoDB에 저장할 설문 데이터 생성
    # ---------------------------------------------------------
    new_survey = {
         # 어떤 사용자의 설문인지 저장
        "user_id": user_id,
        # 사용자가 선택한 지역
        "location": data.get('location', ""),
        # 지도 좌표 (위도, 경도)
        # 예: {lat: 37.55, lng: 126.97}
        "target_coords": data.get('target_coords'),
        # 계약 형태 (월세 / 전세)
        "contract_type": data.get('contract_type', ""),

        # ---------------------------------------------------------
        # 예산 정보
        # ---------------------------------------------------------
        "budget": {
             # 최소 보증금
            "min_dep": parse_budget(budget_raw.get('min_dep')),
             # 최대 보증금
            "max_dep": parse_budget(budget_raw.get('max_dep')),
            # 최소 월세
            "min_rent": parse_budget(budget_raw.get('min_rent')),
             # 최대 월세
            "max_rent": parse_budget(budget_raw.get('max_rent'))
        },
        # 건물 유형
        # 예: ["아파트", "오피스텔"]
        "building_type": data.get('building_type', []),
        # 건물 연식 선택 (구형 방식)
        # 예: ["신축", "준신축"]
        "building_age": data.get('building_age', []),
        # 슬라이더 방식 최대 건물 연식
        # None = 상관없음
        # 숫자 = 최대 건물 나이
        "max_building_age": data.get('max_building_age'), 
        # 방 개수 (구형 방식)
        # 예: ["1개", "2개"]      
        "room_count": data.get('room_count', []),
        # 슬라이더 최소 방 개수
        # 기본값 1
        "min_room_count": data.get('min_room_count', 1),
        # 특수 조건
        # 예: "반지하 피하고 싶어요"        
        "special_room": data.get('special_room', ""),
          # 주차 필요 여부
        "parking": data.get('parking', ""),
         # 가성비 점수(VFM)를 추천에 반영할지 여부
        "prefer_vfm": data.get('prefer_vfm', False),
        # 설문에서 선택한 라이프스타일 카테고리 로그
        # 예: ["green", "traffic", "convenience"]            
        "category_log": data.get('category_log', []),
         # 설문 생성 시간
        "created_at": datetime.now()
    }

    # ---------------------------------------------------------
    # 7️⃣ 사용자의 기존 설문 목록 조회
    # ---------------------------------------------------------
    # 최신순으로 정렬
    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))

    # ---------------------------------------------------------
    # 8️⃣ 설문 저장 개수 제한 (최대 10개)
    # ---------------------------------------------------------
    if len(surveys) >= 10:
        # 가장 오래된 설문 삭제
        # surveys[-1] → 마지막 요소 = 가장 오래된 설문
        db.survey_results.delete_one({"_id": surveys[-1]['_id']})

    # ---------------------------------------------------------
    # 9️⃣ 새로운 설문 MongoDB에 저장
    # ---------------------------------------------------------
    result = db.survey_results.insert_one(new_survey)

     # ---------------------------------------------------------
    # 🔟 MongoDB에서 생성된 ID 가져오기
    # ---------------------------------------------------------
    survey_id = str(result.inserted_id)
    # AI 생성 없이 즉시 survey_id 반환 → 프론트엔드에서 result 페이지로 이동
    return jsonify({"status": "success", "survey_id": survey_id})

# 설문 결과를 survey_id로 직접 조회하는 라우트
# 예: /survey/result/by_id/65f2a8c19a2c2f0e8c3b2c11
@survey_bp.route('/survey/result/by_id/<survey_id>')
def survey_result_by_id(survey_id):
    """
    survey_id(ObjectId)를 이용해 특정 설문 결과 페이지로 직접 접근하는 함수
    
    사용 목적
    - 설문을 완료한 직후
    - 방금 생성된 설문 결과 페이지로 바로 이동하기 위해 사용
    
    기존 결과 페이지는 index 기반으로 동작하기 때문에
    survey_id → index 로 변환하는 과정이 필요하다.
    """

    # ---------------------------------------------------------
    # 1️⃣ 로그인 여부 확인
    # ---------------------------------------------------------
    # session에 user_id가 없으면 로그인하지 않은 상태
    # 설문 결과는 사용자 개인 데이터이므로 로그인 필수
    if 'user_id' not in session:
         # 로그인 페이지로 이동
        return redirect(url_for('auth.login'))

    # ---------------------------------------------------------
    # 2️⃣ 현재 로그인한 사용자 ID 가져오기
    # ---------------------------------------------------------
    # session에 저장된 user_id를 변수에 저장
    user_id = session['user_id']


    # ---------------------------------------------------------
    # 3️⃣ MongoDB에서 해당 설문 결과 조회
    # ---------------------------------------------------------
    # survey_id는 문자열이기 때문에
    # MongoDB의 ObjectId 타입으로 변환해야 조회 가능
    try:
        selected_survey = db.survey_results.find_one({"_id": ObjectId(survey_id), # 설문 결과의 고유 ID
    
                                          "user_id": user_id})  # 현재 로그인한 사용자
     # ObjectId 변환 실패 등의 예외 처리
    except Exception:
        # 잘못된 ID이거나 접근 오류가 발생한 경우
        # 안전하게 마이페이지로 이동
        return redirect('/mypage')

    # ---------------------------------------------------------
    # 4️⃣ 설문 결과 존재 여부 확인
    # ---------------------------------------------------------
    # DB에 해당 설문 결과가 없는 경우
    if not selected_survey:
        # 마이페이지로 이동
        return redirect('/mypage')

    # ---------------------------------------------------------
    # 5️⃣ 현재 사용자의 모든 설문 결과 목록 가져오기
    # ---------------------------------------------------------
    # 이유:
    # 기존 결과 페이지는 index 기반으로 설문을 보여주기 때문
    # 따라서 survey_id → index 변환 필요

    # 해당 사용자의 설문만 조회
    # 최신 설문이 위로 오도록 정렬
    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))

    # ---------------------------------------------------------
    # 6️⃣ 현재 설문의 index 찾기
    # ---------------------------------------------------------
    # surveys 리스트에서 survey_id와 동일한 설문 위치를 찾는다
    #
    # enumerate(surveys)
    # → 리스트를 (index, 데이터) 형태로 반환
    #
    # 예:
    # (0, surveyA)
    # (1, surveyB)
    # (2, surveyC)
    index = next((i # 찾은 index 값
                  for i, s in enumerate(surveys) if str(s['_id']) == survey_id), 0)
    # 리스트 순회
    # 현재 설문 ID와 비교
    # 찾지 못한 경우 기본값 0


    # ---------------------------------------------------------
    # 7️⃣ 기존 결과 페이지 함수 실행
    # ---------------------------------------------------------
    # survey_result()는 index 기반으로 설문 결과를 보여주는 함수
    #
    # 예:
    # survey_result(0) → 가장 최근 설문
    # survey_result(1) → 두 번째 설문
    #
    # 따라서 위에서 계산한 index를 전달
    return survey_result(index)


@survey_bp.route('/survey/result/<int:index>')
def survey_result(index):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))

    user_likes = db.likes.find({"user_id": user_id})
    user_liked_ids = [str(like['house_id']) for like in user_likes]
    
    if not surveys or index >= len(surveys):
        return redirect('/mypage')

    selected_survey = surveys[index]
    survey_id = selected_survey['_id']
    
    nw = get_user_normalized_weights(selected_survey.get('category_log', []))
    top2 = sorted(nw.items(), key=lambda x: x[1], reverse=True)[:2]
    top2_keys = [top2[0][0], top2[1][0]]
    user_type, user_type_desc = TYPE_MAP.get(frozenset(top2_keys), ("기본형", "당신에게 꼭 맞는 매물을 찾고 있어요."))

    chart_keys = ['traffic', 'convenience', 'green', 'play', 'health', 'living', 'safety']
    user_chart_labels = ['교통', '편의', '녹지', '놀이', '건강', '생활', '안전']
    user_chart_data = [round(nw.get(k, 0) * 100, 1) for k in chart_keys]

    detailed_analysis = _parse_lifestyle_report(selected_survey.get('lifestyle_report'))

    query = {}
    target_coords = selected_survey.get('target_coords')
    loc = selected_survey.get('location')
    if not target_coords or float(target_coords.get('lat', 0)) == 0:
        if loc and loc != "상관없음": query['address'] = {"$regex": loc}
    
    c_type = selected_survey.get('contract_type')
    target_rent_type = {"jeonse": "전세", "monthly": "월세"}.get(c_type, c_type)
    if target_rent_type: query['rent_type'] = target_rent_type
    
    budget = selected_survey.get('budget', {})
    min_dep, max_dep = budget.get('min_dep'), budget.get('max_dep')
    min_rent, max_rent = budget.get('min_rent'), budget.get('max_rent')

    if max_dep == 0: max_dep = None
    if max_rent == 0: max_rent = None

    if target_rent_type == "전세":
        price_q = {}
        if min_dep is not None: price_q["$gte"] = min_dep
        if max_dep is not None: price_q["$lte"] = max_dep
        if price_q: query['price'] = price_q
    elif target_rent_type == "월세":
        dep_q = {}
        if min_dep is not None: dep_q["$gte"] = min_dep
        if max_dep is not None: dep_q["$lte"] = max_dep
        if dep_q: query['deposit'] = dep_q
        
        rent_q = {}
        if min_rent is not None: rent_q["$gte"] = min_rent
        if max_rent is not None: rent_q["$lte"] = max_rent
        if rent_q: query['price'] = rent_q

    query = apply_detail_filters(query, selected_survey)

    use_vfm = bool(selected_survey.get('prefer_vfm', False))
    total_count = houses_col.count_documents(query)
    pipeline = build_match_pipeline(query, nw, target_coords=target_coords, limit=10, use_vfm=use_vfm)
    matched_properties = format_property_data(list(houses_col.aggregate(pipeline)), user_liked_ids)
    if use_vfm:
        matched_properties = apply_vfm_to_results(matched_properties)

    top_3 = matched_properties[:3]
    others = matched_properties[3:]

    saved_comments = selected_survey.get('ai_comments_v2', {})
    for house in top_3:
        house['ai_comment'] = saved_comments.get(house['_id_str'])
    
    return render_template(
        'result.html', 
        survey=selected_survey, 
        top_3=top_3, 
        others=others, 
        current_index=index, 
        survey_id=str(survey_id),
        user_type=user_type, 
        user_type_desc=user_type_desc,
        total_count=total_count,
        user_chart_labels=user_chart_labels,
        user_chart_data=user_chart_data,
        chart_keys=chart_keys,
        detailed_analysis=detailed_analysis,
        prefer_vfm=use_vfm,
        index=index
    )

# ---------------------------------------------------------
# AI 분석 생성 API
# URL 예시: /survey/ai_generate/<survey_id>
# 설문 결과를 기반으로
# 1) 사용자 라이프스타일 분석
# 2) 추천 매물 설명(멘트)
# 을 AI로 생성하는 API
# ---------------------------------------------------------
@survey_bp.route('/survey/ai_generate/<survey_id>', methods=['POST'])
def ai_generate(survey_id):
    # ---------------------------------------------------------
    # 1️⃣ 로그인 여부 확인
    # ---------------------------------------------------------
    # 설문 결과와 추천 매물은 사용자 개인 데이터이므로
    # 로그인하지 않은 경우 접근을 막는다.
    if 'user_id' not in session:
          # 로그인 안 된 상태 → JSON 에러 반환
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    # 현재 로그인한 사용자 ID 가져오기
    user_id = session['user_id']

    # ---------------------------------------------------------
    # 2️⃣ survey_id로 설문 결과 조회
    # ---------------------------------------------------------
    # URL로 받은 survey_id를 ObjectId로 변환해서
    # MongoDB survey_results 컬렉션에서 설문 데이터 조회
    try:
        selected_survey = db.survey_results.find_one({"_id": ObjectId(survey_id)})
    except Exception:
          # survey_id 형식이 잘못된 경우
        return jsonify({"status": "error", "message": "Invalid survey_id"}), 400

    # 설문이 존재하지 않을 경우
    if not selected_survey:
        return jsonify({"status": "error", "message": "Survey not found"}), 404

    # ---------------------------------------------------------
    # 3️⃣ 사용자 관심 카테고리 가중치 계산
    # ---------------------------------------------------------
    # 설문에서 기록된 category_log를 기반으로
    # 사용자 관심 카테고리 가중치를 계산
    # 예: 교통 0.35, 편의 0.28 ...
    nw = get_user_normalized_weights(selected_survey.get('category_log', []))
    # 가중치 기준으로 정렬 후 상위 2개 선택
    top2 = sorted(nw.items(), key=lambda x: x[1], reverse=True)[:2]
     # 카테고리 이름만 추출
    top2_keys = [top2[0][0], top2[1][0]]


    # DB 업데이트용 딕셔너리

    updates = {}

    # ---------------------------------------------------------
    # 4️⃣ 추천 매물 검색을 위한 MongoDB 쿼리 생성
    # ---------------------------------------------------------
    query = {}
    # 설문에서 선택한 목표 위치 좌표
    target_coords = selected_survey.get('target_coords')
    # 사용자가 선택한 지역 이름
    loc = selected_survey.get('location')
     # 좌표가 없는 경우 주소 문자열 검색
    if not target_coords or float(target_coords.get('lat', 0)) == 0:
        if loc and loc != "상관없음": query['address'] = {"$regex": loc}

    # ---------------------------------------------------------
    # 5️⃣ 계약 유형 필터
    # ---------------------------------------------------------
    # 설문에서 선택한 계약 유형
    c_type = selected_survey.get('contract_type')
     # 내부 코드값 → DB 값으로 변환
    target_rent_type = {"jeonse": "전세", "monthly": "월세"}.get(c_type, c_type)

    # MongoDB 쿼리에 계약 유형 추가
    if target_rent_type: query['rent_type'] = target_rent_type

    # ---------------------------------------------------------
    # 6️⃣ 추가 상세 조건 필터 적용
    # ---------------------------------------------------------
    # 예: 엘리베이터, 주차, 반려동물 가능 여부 등
    query = apply_detail_filters(query, selected_survey)



    # ---------------------------------------------------------
    # 7️⃣ 추천 매물 검색 실행
    # ---------------------------------------------------------
    # 가성비 모드 사용 여부
    use_vfm_gen = bool(selected_survey.get('prefer_vfm', False))

     # 추천 매물 검색 파이프라인 생성
    pipeline = build_match_pipeline(query, nw, target_coords=target_coords, limit=10, use_vfm=use_vfm_gen)
    # MongoDB aggregate 실행 후
    # 매물 데이터를 화면에 맞게 포맷 변환
    matched_properties = format_property_data(list(houses_col.aggregate(pipeline)))

     # 가성비 모드일 경우 점수 재정렬
    if use_vfm_gen:
        matched_properties = apply_vfm_to_results(matched_properties)
      # 상위 3개 매물만 선택
    top_3 = matched_properties[:3]


     # ---------------------------------------------------------
    # 8️⃣ 기존 AI 코멘트 가져오기
    # ---------------------------------------------------------
    saved_comments = selected_survey.get('ai_comments_v2', {})
    # lifestyle_report가 없는 경우만 새로 생성
    needs_lifestyle = not selected_survey.get('lifestyle_report')
    # 새 코멘트 저장용 딕셔너리
    new_comments = dict(saved_comments)

      # ---------------------------------------------------------
    # 9️⃣ AI 작업 병렬 실행 (속도 개선)
    # ---------------------------------------------------------
    # 라이프스타일 분석 + 매물 설명을 동시에 실행
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # ---------------------------------------------------------
        # 라이프스타일 분석 생성 (없는 경우만)
        # ---------------------------------------------------------
        lifestyle_future = executor.submit(
            generate_sandbox_lifestyle_analysis, nw, top2_keys
        ) if needs_lifestyle else None

        # ---------------------------------------------------------
        # 추천 매물 설명 생성
        # ---------------------------------------------------------
        # 이미 생성된 코멘트는 다시 생성하지 않음
        comment_futures = {}
        for house in top_3:
            h_id = house['_id_str']
            if h_id not in saved_comments:
                comment_futures[h_id] = executor.submit(
                    generate_recommendation_reason, user_id, nw, house
                )

        # ---------------------------------------------------------
        # 10️⃣ 라이프스타일 분석 결과 수집
        # ---------------------------------------------------------
        # 최대 45초 대기
        if lifestyle_future:
            try:
                detailed_analysis = lifestyle_future.result(timeout=45)
                  # DB 업데이트용 데이터에 추가
                updates['lifestyle_report'] = detailed_analysis
                detailed_analysis = _parse_lifestyle_report(detailed_analysis)
            except Exception as e:
                print(f"Lifestyle future error: {e}")

                  # 기존 값 유지
                detailed_analysis = selected_survey.get('lifestyle_report', '')
                detailed_analysis = _parse_lifestyle_report(selected_survey.get('lifestyle_report', ''))

        else:
            detailed_analysis = _parse_lifestyle_report(selected_survey.get('lifestyle_report', ''))

        # ---------------------------------------------------------
        # 11️⃣ 매물 설명 결과 수집
        # ---------------------------------------------------------
        for house in top_3:
            h_id = house['_id_str']
            if h_id in comment_futures:
                try:
                    new_comments[h_id] = comment_futures[h_id].result(timeout=45)
                except Exception as e:
                    print(f"Comment future error [{h_id}]: {e}")
                    new_comments[h_id] = "분석 중 오류가 발생했습니다."

    # ---------------------------------------------------------
    # 12️⃣ 새로운 코멘트가 생성된 경우 DB 업데이트
    # ---------------------------------------------------------
    if new_comments != saved_comments:
        updates['ai_comments_v2'] = new_comments

    if updates:
        db.survey_results.update_one({"_id": ObjectId(survey_id)}, {"$set": updates})

     # ---------------------------------------------------------
    # 13️⃣ 반환할 매물 데이터에 AI 코멘트 추가
    # ---------------------------------------------------------
    for house in top_3:
        house['ai_comment'] = new_comments.get(house['_id_str'], '')


    # ---------------------------------------------------------
    # 14️⃣ 프론트엔드로 결과 반환
    # ---------------------------------------------------------
    return jsonify({

        # 실행 결과 상태
        "status": "success",
         # AI 라이프스타일 분석 결과
        "detailed_analysis": detailed_analysis,
         # TOP3 매물 AI 설명
        "ai_comments": {h['_id_str']: h['ai_comment'] for h in top_3}
    })

@survey_bp.route('/survey/recalculate', methods=['POST'])
def recalculate():
    try:
        # ---------------------------------------------------------
        # 1️⃣ 클라이언트에서 보낸 JSON 데이터 가져오기
        # ---------------------------------------------------------
        # 프론트엔드에서 추천 조건(가중치, 필터 등)을 변경하면
        # JSON 형태로 서버에 전달된다.
        data = request.get_json()
        # 데이터가 없는 경우 오류 반환
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400
        
        # ---------------------------------------------------------
        # 2️⃣ 사용자 가중치와 설문 ID 가져오기
        # ---------------------------------------------------------
        # weights : 사용자가 조정한 카테고리 중요도
        # survey_id : 현재 보고 있는 설문 결과
        custom_weights = data.get('weights')
        survey_id_raw = data.get('survey_id')
        
         # ---------------------------------------------------------
        # 3️⃣ 추천 시스템에서 사용하는 카테고리 목록
        # ---------------------------------------------------------
        # 총 7개 생활 카테고리
        keys = ["traffic", "convenience", "green", "play", "health", "living", "safety"]
        # 사용자 가중치를 저장할 딕셔너리
        nw = {}
        

        # ---------------------------------------------------------
        # 4️⃣ 가중치 데이터 형식 처리
        # ---------------------------------------------------------
        # 프론트에서 가중치가 리스트 형태로 올 수도 있음
        if isinstance(custom_weights, list):
             # 예: [30,20,10,5,10,15,10]
            for i, key in enumerate(keys):
                 # 리스트 길이보다 인덱스가 크면 0 처리
                nw[key] = custom_weights[i] if i < len(custom_weights) else 0
        # 가중치가 딕셔너리 형태일 경우
        elif isinstance(custom_weights, dict):
            # 예: {"traffic":30,"green":10}
            # 없는 값은 0으로 채움
            nw = {k: custom_weights.get(k, 0) for k in keys}
        else:
            # 잘못된 형식이면 오류 반환
            return jsonify({"status": "error", "message": "Invalid weights format"}), 400

        # ---------------------------------------------------------
        # 5️⃣ 로그인 여부 확인
        # ---------------------------------------------------------
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
         # ---------------------------------------------------------
        # 6️⃣ 현재 사용자의 설문 목록 가져오기
        # ---------------------------------------------------------
        # 최신 설문이 위로 오도록 정렬
        surveys = list(db.survey_results.find({"user_id": session['user_id']}).sort("created_at", -1))
        
         # 선택된 설문 저장 변수
        selected_survey = None


        # ---------------------------------------------------------
        # 7️⃣ survey_id 처리
        # ---------------------------------------------------------
        # survey_id가 숫자라면 → index 방식
        if str(survey_id_raw).isdigit():
            # index 범위 확인
            idx = int(survey_id_raw)
            if idx < len(surveys):
                selected_survey = surveys[idx]
        # survey_id가 MongoDB ObjectId인 경우
        else:
            try:
                selected_survey = db.survey_results.find_one({"_id": ObjectId(survey_id_raw)})
            # ObjectId 변환 실패 시
            except:
                  # 설문이 존재하면 가장 최근 설문 사용
                if surveys: selected_survey = surveys[0]

        if not selected_survey:
            return jsonify({"status": "error", "message": "Survey not found"}), 404

        # ---------------------------------------------------------
        # 8️⃣ 가중치 정규화
        # ---------------------------------------------------------
        # 가중치 합계 계산
        total_w = sum(nw.values())
        # 모든 가중치를 합이 1이 되도록 정규화
        nw_norm = {k: v/total_w for k, v in nw.items()} if total_w > 0 else {k: 1/7 for k in keys}


         # ---------------------------------------------------------
        # 9️⃣ 클라이언트 필터 가져오기
        # ---------------------------------------------------------
        client_filters = data.get('filters', {})

        # MongoDB 검색 조건
        query = {}
        if client_filters:
              # ---------------------------------------------------------
            # 10️⃣ 상세 필터 적용
            # ---------------------------------------------------------
            # 예: 엘리베이터, 주차, 반려동물 등
            query = apply_detail_filters({}, client_filters)
             # 계약 유형
            c_type = client_filters.get('contract_type')
            # 내부 코드 → DB 값 변환
            target_rent_type = {"jeonse": "전세", "monthly": "월세"}.get(c_type, c_type)
            if target_rent_type: query['rent_type'] = target_rent_type
            

            # ---------------------------------------------------------
            # 11️⃣ 필터 값 숫자 변환 함수
            # ---------------------------------------------------------
            def parse_filter_val(val):
                if val is None or str(val).strip() == "": return None
                try: return int(float(val))
                except: return None


            # ---------------------------------------------------------
            # 12️⃣ 보증금 필터
            # ---------------------------------------------------------
            min_dep = parse_filter_val(client_filters.get('min_dep'))
            max_dep = parse_filter_val(client_filters.get('max_dep'))

            if target_rent_type == "전세":
                price_q = {}
                if min_dep is not None: price_q["$gte"] = min_dep
                if max_dep is not None: price_q["$lte"] = max_dep
                if price_q: query['price'] = price_q
             # ---------------------------------------------------------
            # 13️⃣ 월세 조건
            # ---------------------------------------------------------
            else:
                dep_q = {}
                if min_dep is not None: dep_q["$gte"] = min_dep
                if max_dep is not None: dep_q["$lte"] = max_dep
                if dep_q: query['deposit'] = dep_q
                
                # 월세 범위
                min_rent = parse_filter_val(client_filters.get('min_rent'))
                max_rent = parse_filter_val(client_filters.get('max_rent'))
                rent_q = {}
                if min_rent is not None: rent_q["$gte"] = min_rent
                if max_rent is not None: rent_q["$lte"] = max_rent
                if rent_q: query['price'] = rent_q
         # 필터가 없는 경우
        else:
            query = apply_detail_filters({}, selected_survey)

         # ---------------------------------------------------------
        # 14️⃣ 가성비(VFM) 적용 여부
        # ---------------------------------------------------------
        # 클라이언트 필터 우선
        use_vfm = bool(client_filters.get('prefer_vfm', selected_survey.get('prefer_vfm', False))) if client_filters else bool(selected_survey.get('prefer_vfm', False))


        # ---------------------------------------------------------
        # 15️⃣ 추천 매물 검색 파이프라인 생성
        # ---------------------------------------------------------
        pipeline = build_match_pipeline(query, nw_norm, target_coords=selected_survey.get('target_coords'), limit=12, use_vfm=use_vfm)
         # MongoDB aggregate 실행
        matched_properties = format_property_data(list(houses_col.aggregate(pipeline)))
          # 가성비 점수 적용
        if use_vfm:
            matched_properties = apply_vfm_to_results(matched_properties)

          # ---------------------------------------------------------
        # 16️⃣ TOP3 매물 AI 추천 이유 생성
        # ---------------------------------------------------------
        futures_recalc = {}

         # 병렬 실행 (속도 개선)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
              # AI 작업 시작
            for house in matched_properties[:3]:
                h_id = house['_id_str']
                futures_recalc[h_id] = executor.submit(generate_recommendation_reason, session['user_id'], nw_norm, house)
            # 결과 수집
            for house in matched_properties[:3]:
                h_id = house['_id_str']
                try:
                    house['ai_comment'] = futures_recalc[h_id].result(timeout=10)
                except:
                    house['ai_comment'] = "추천 이유를 생성하지 못했습니다."

        # ---------------------------------------------------------
        # 17️⃣ 사용자 유형 계산
        # ---------------------------------------------------------
        sorted_nw = sorted(nw_norm.items(), key=lambda x: x[1], reverse=True)
        top2_keys = frozenset([sorted_nw[0][0], sorted_nw[1][0]])
        user_type, user_type_desc = TYPE_MAP.get(top2_keys, ("맞춤형 분석가", "라이프스타일에 맞는 매물을 찾는 중입니다."))

        # ---------------------------------------------------------
        # 18️⃣ 최종 결과 반환
        # ---------------------------------------------------------
        return jsonify({
            "status": "success",
            # 추천 매물 목록
            "items": matched_properties,

              # 사용자 유형
            "user_type": user_type,
            "user_type_desc": user_type_desc
        })
     # ---------------------------------------------------------
    # 19️⃣ 에러 처리
    # ---------------------------------------------------------
    except Exception as e:
        import traceback
        print(f"❌ Recalculate Error: {str(e)}")
        print(traceback.format_exc()) 
        return jsonify({"status": "error", "message": str(e)}), 500

@survey_bp.route('/survey/short')
def survey_short():
    # 1. 로그인 여부 확인 (에러 대신 None 처리)
    user_id = session.get('user_id')
    
    latest_survey = None
    if user_id:
        latest_survey = db.survey_results.find_one(
            {"user_id": user_id}, 
            sort=[("created_at", -1)]
        )
    
    # 2. 가중치 및 쿼리 설정 (비로그인 시 기본값)
    if not latest_survey:
        # 비로그인 유저를 위한 균등 가중치 (또는 운영진 추천 가중치)
        nw = {k: 1/7 for k in category_map.keys()}
        query = {}  # 특정 필터 없이 전체 매물 대상
        target_coords = None
        is_latest = False
    else:
        nw = get_user_normalized_weights(latest_survey.get('category_log', []))
        query = apply_detail_filters({}, latest_survey)
        target_coords = latest_survey.get('target_coords')
        is_latest = True

    # 3. 매칭 파이프라인 (추천 점수 상위 50개 중 랜덤 12개)
    pipeline = build_match_pipeline(query, nw, target_coords=target_coords, limit=50)
    pipeline.append({"$sample": {"size": 12}})
    
    recommendations = format_property_data(list(houses_col.aggregate(pipeline)))
    
    session['short_block'] = 0
    return render_template('shorts.html', 
                           recommendations=recommendations, 
                           is_latest=is_latest)

@survey_bp.route('/survey/short/more')
def survey_short_more():
    # ---------------------------------------------------------
    # 1️⃣ 로그인 여부 확인
    # ---------------------------------------------------------
    # session에서 user_id를 가져온다.
    # 로그인하지 않은 경우 None이 반환된다.
    user_id = session.get('user_id')
    
     # 최신 설문 데이터를 저장할 변수
    latest_survey = None
      # ---------------------------------------------------------
    # 2️⃣ 로그인된 경우 가장 최근 설문 가져오기
    # ---------------------------------------------------------
    if user_id:
         # survey_results 컬렉션에서
        # 해당 user_id의 설문 중
        # created_at 기준으로 가장 최근 설문 1개 조회
        latest_survey = db.survey_results.find_one(
            {"user_id": user_id}, 
            sort=[("created_at", -1)]
        )

    # ---------------------------------------------------------
    # 3️⃣ 추천 계산을 위한 가중치 및 검색 조건 설정
    # ---------------------------------------------------------

      # 설문이 없는 경우 (비로그인 사용자 또는 설문 미작성 사용자)
    if not latest_survey:
        # 모든 카테고리를 동일한 중요도로 설정
        # 예: 교통=1/7, 편의=1/7, 녹지=1/7 ...
        # 즉 특정 취향 없이 균등 추천
        nw = {k: 1/7 for k in category_map.keys()}

        # MongoDB 검색 필터 없음
        # → 전체 매물을 대상으로 추천
        query = {}
        # 특정 위치 기준 없음
        target_coords = None
    # ---------------------------------------------------------
    # 4️⃣ 설문이 존재하는 경우
    # ---------------------------------------------------------
    else:
        # 설문 결과(category_log)를 기반으로
        # 사용자 관심 카테고리 가중치 계산
        # 예: 교통 0.32, 편의 0.25, 녹지 0.12 ...
        nw = get_user_normalized_weights(latest_survey.get('category_log', []))
        # 설문에서 선택한 조건들을 MongoDB 필터로 변환
        # 예: 계약유형, 주차 여부, 반려동물 가능 여부 등
        query = apply_detail_filters({}, latest_survey)
        # 설문에서 선택한 목표 위치 좌표
        # 추천 점수 계산 시 거리 반영에 사용
        target_coords = latest_survey.get('target_coords')

    # 4. 페이지네이션(블록) 관리
    # 세션에서 현재 몇 번째 블록인지 가져와서 1 증가시킴
    current_block = session.get('short_block', 0)
    next_block = current_block + 1
    
    # ---------------------------------------------------------
    # 5️⃣ 추천 매물 검색 파이프라인 생성
    # ---------------------------------------------------------
    # build_match_pipeline 함수는
    # MongoDB aggregation pipeline을 생성한다.
    #
    # 내부에서는
    # - 필터(query)
    # - 사용자 가중치(nw)
    # - 위치(target_coords)
    # 등을 기반으로 추천 점수를 계산한다.
    #
    # limit=50
    # → 추천 점수가 높은 매물 50개 후보를 먼저 가져온다.
    pipeline = build_match_pipeline(
        query, 
        nw, 
        target_coords=target_coords, 
        limit=1000, 
        is_random=True
    )
    
    # 6. 건너뛰기($skip)와 가져오기($limit) 추가
    # 한 번에 12개씩 가져온다고 가정
    items_per_page = 12
    pipeline.extend([
        {"$skip": next_block * items_per_page}, 
        {"$limit": items_per_page}
    ])
    
    # 7. DB 실행 및 데이터 포맷팅
    new_items = list(houses_col.aggregate(pipeline))
    
    if not new_items: 
        return jsonify({"status": "success", "items": [], "has_more": False})

    # 8. 세션 갱신 (다음 스크롤을 위해 현재 블록 번호 저장)
    session['short_block'] = next_block
    session.modified = True # 세션 변경사항 강제 저장
    
    # 9. JSON 데이터 반환 (클라이언트 JS에서 받아서 화면에 추가)
    return jsonify({
        "status": "success", 
        "items": format_property_data(new_items), 
        "has_more": True
    })


def get_top_dong_recommendations(nw, top_n=3):
    """유저 가중치 기반으로 최적 동네를 수학적으로 계산 (LLM 아님)"""
    dong_profiles = list(db.dong_profiles.find())
    
    scored_dongs = []
    for dong in dong_profiles:
        score = sum(
            nw.get(cat, 0) * (dong.get(f"avg_{cat}") or 0)
            for cat in ['traffic', 'convenience', 'green', 'play', 'health', 'living', 'safety']
        )
        scored_dongs.append({
            "name": dong["_id"],
            "score": score,
            "scores": {cat: dong.get(f"avg_{cat}") or 0 for cat in ['traffic', 'convenience', 'green', 'play', 'health', 'living', 'safety']}
        })
    
    return sorted(scored_dongs, key=lambda x: x["score"], reverse=True)[:top_n]


def generate_sandbox_lifestyle_analysis(nw_weights, top2_keys):
    import json as _json
    weight_pct = {category_map[k]: f"{v*100:.1f}%" for k, v in nw_weights.items()}
    top_names = [category_map[k] for k in top2_keys]

    top_dongs = get_top_dong_recommendations(nw_weights)
    
    # 🔥 [수정 1] _id 필드에 들어있는 순수한 '동 이름'만 따로 추출합니다.
    exact_dong_names = [d['name'] for d in top_dongs]
    
    dong_data_lines = []
    for d in top_dongs:
        sorted_scores = sorted(d["scores"].items(), key=lambda x: x[1], reverse=True)[:3]
        score_str = ", ".join([f"{category_map[k]} {int(v*100)}점" for k, v in sorted_scores])
        dong_data_lines.append(f"- {d['name']}: {score_str}")
    dong_data_str = "\n".join(dong_data_lines)

    template = """
    당신은 고객의 취향과 일상을 섬세하게 읽어내는 라이프스타일 큐레이터이자 공간 에디터입니다.
    고객의 설문조사 결과(가중치)를 바탕으로, 딱딱한 보고서가 아닌 따뜻한 감성이 담긴 '퍼스널 매거진' 스타일의 1:1 맞춤형 공간 브리핑을 JSON으로 작성해주세요.

    [고객 데이터]
    - 최우선 핵심 가치 2가지: {top_names}
    - 7대 지표별 세부 가중치: {weight_pct}

    [추천 동네 데이터] — 코드가 계산한 결과입니다. 
    {dong_data}

    [🔥 허용된 동네 이름 목록]
    반드시 이 이름들 중 하나만 사용해야 합니다: {exact_dong_names}

    [말투 및 제약 조건]
    - 톤앤매너: 센스 있는 잡지 에디터나 다정한 공간 디렉터처럼 부드럽고 세련된 말투를 사용하세요.
    - 너무 격식을 차린 딱딱한 표현 대신, 대화하듯 친근하면서도 신뢰감이 느껴지는 어조를 사용하세요.
    - 🚨 insights의 label에는 절대 새로운 단어(예: 자아실현, 사회적 관계 등)를 지어내지 마세요. 반드시 '교통', '편의', '녹지', '놀이', '건강', '생활', '안전' 7가지 중에서만 정확히 똑같은 글자로 선택하세요.
    - 🚨 dongs의 name에는 반드시 [허용된 동네 이름 목록]에 있는 문자열을 토씨 하나 틀리지 않고 그대로 입력하세요. (예: '연남동', '역삼1동'). 절대 '연남동 일대'처럼 설명을 덧붙이거나 새로운 동네를 지어내면 안 됩니다.
    - 🔥 JSON 외 다른 텍스트(마크다운, 코드블록 ```, 설명문 등)는 절대 출력하지 마세요.

    [출력 형식] 반드시 아래 JSON 구조로만 응답하세요 (키 이름 변경 금지):
    {{
      "summary": "고객의 라이프스타일 전체를 2~3문장으로 따뜻하고 감성적으로 요약. 잡지 에디터 스타일로.",
      "insights": [
        {{
          "label": "지표명 (반드시 교통, 편의, 녹지, 놀이, 건강, 생활, 안전 중 하나)",
          "weight": "00.0%",
          "desc": "이 지표가 이 고객에게 왜 중요한지, 어떤 라이프스타일을 반영하는지 2~3문장으로 감성적으로 설명"
        }},
        {{"label": "지표명 (반드시 7대 지표 중 하나)", "weight": "00.0%", "desc": "설명"}},
        {{"label": "지표명 (반드시 7대 지표 중 하나)", "weight": "00.0%", "desc": "설명"}}
      ],
      "dongs": [
        {{
          "name": "허용된 동네 이름 목록에 있는 문자열 그대로 (예: 삼성동)",
          "desc": "이 동네가 이 고객의 라이프스타일과 왜 잘 맞는지 2~3문장으로 감성적으로 설명. 데이터 점수를 근거로.",
          "points": ["구체적 장점 1", "구체적 장점 2", "구체적 장점 3"]
        }},
        {{"name": "허용된 동네 이름 그대로", "desc": "설명", "points": ["장점1", "장점2", "장점3"]}},
        {{"name": "허용된 동네 이름 그대로", "desc": "설명", "points": ["장점1", "장점2", "장점3"]}}
      ]
    }}
    """

    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm

    try:
        # 🔥 [수정 2] exact_dong_names 변수를 프롬프트에 전달합니다.
        response = chain.invoke({
            "top_names": ", ".join(top_names),
            "weight_pct": str(weight_pct),
            "dong_data": dong_data_str,
            "exact_dong_names": ", ".join(exact_dong_names)
        })
        raw = response.content.replace("```json", "").replace("```", "").strip()
        parsed = _json.loads(raw)
        return _json.dumps(parsed, ensure_ascii=False)
    except Exception as e:
        print(f"Lifestyle Analysis Error: {e}")
        fallback = {
            "summary": "설문 결과를 바탕으로 고객님께 꼭 맞는 매물을 찾고 있어요.",
            "insights": [
                {"label": top_names[0] if top_names else "생활", "weight": weight_pct.get(top_names[0], "–") if top_names else "–", "desc": "고객님이 가장 중요하게 생각하시는 가치예요."},
                {"label": top_names[1] if len(top_names) > 1 else "교통", "weight": weight_pct.get(top_names[1], "–") if len(top_names) > 1 else "–", "desc": "두 번째로 중요하게 생각하시는 가치예요."},
                {"label": "안전", "weight": weight_pct.get("안전", "–"), "desc": "편안하고 안심되는 환경을 선호하시는 것 같아요."}
            ],
            "dongs": [
                {"name": exact_dong_names[0] if exact_dong_names else "추천 동네", "desc": "고객님의 라이프스타일에 잘 맞는 동네예요.", "points": ["쾌적한 환경", "편리한 교통", "생활 인프라 우수"]},
                {"name": exact_dong_names[1] if len(exact_dong_names) > 1 else "추천 동네 2", "desc": "편리하고 활기찬 동네예요.", "points": ["편의시설 풍부", "안전한 주거환경", "다양한 문화시설"]},
                {"name": exact_dong_names[2] if len(exact_dong_names) > 2 else "추천 동네 3", "desc": "조용하고 살기 좋은 동네예요.", "points": ["녹지공간 풍부", "안정적인 주거", "좋은 교육환경"]}
            ]
        }
        return _json.dumps(fallback, ensure_ascii=False)

@survey_bp.route('/survey/prompt_test/<int:index>')
def survey_prompt_sandbox(index):
    if 'user_id' not in session: 
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))
    
    if not surveys or index >= len(surveys): 
        return "설문 결과가 없습니다.", 404
    
    selected_survey = surveys[index]
    survey_id = selected_survey['_id']
    
    nw = get_user_normalized_weights(selected_survey.get('category_log', []))
    sorted_nw = sorted(nw.items(), key=lambda x: x[1], reverse=True)
    top2_keys = [sorted_nw[0][0], sorted_nw[1][0]]
    
    user_type, user_type_desc = TYPE_MAP.get(frozenset(top2_keys), ("✨ 맞춤형 라이프", "당신만의 특별한 매물을 찾고 있어요."))
    
    chart_keys = ['traffic', 'convenience', 'green', 'play', 'health', 'living', 'safety']
    user_chart_labels = ['교통', '편의', '녹지', '놀이', '건강', '생활', '안전']
    user_chart_data = [round(nw.get(k, 0) * 100, 1) for k in chart_keys]

    detailed_analysis = selected_survey.get('lifestyle_report')
    if not detailed_analysis:
        detailed_analysis = generate_sandbox_lifestyle_analysis(nw, top2_keys)
        db.survey_results.update_one({"_id": survey_id}, {"$set": {"lifestyle_report": detailed_analysis}})

    return render_template(
        'prompt_test.html', 
        user_type=user_type, 
        user_type_desc=user_type_desc, 
        detailed_analysis=detailed_analysis, 
        user_chart_labels=user_chart_labels, 
        user_chart_data=user_chart_data,
        chart_keys=chart_keys,
        index=index,
        survey_id=str(survey_id)
    )