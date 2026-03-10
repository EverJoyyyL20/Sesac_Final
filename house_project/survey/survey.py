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
    # 교통 관련 시설
    # 예: 지하철역, 버스정류장, 도로 접근성 등
    "traffic": "교통", 
    # 편의시설
    # 예: 편의점, 카페, 음식점, 쇼핑몰 등
    "convenience": "편의", 
    # 녹지 공간
    # 예: 공원, 숲, 산책로 등 자연환경
    "green": "녹지",
     # 놀이 시설
    # 예: 놀이터, 키즈카페, 놀이공원 등
    "play": "놀이", 
     # 건강 관련 시설
    # 예: 병원, 약국, 헬스장 등
    "health": "건강",
     # 생활 편의 시설
    # 예: 마트, 세탁소, 은행, 생활 인프라 등 
    "living": "생활", 
    # 안전 관련 시설
    # 예: 경찰서, 소방서, CCTV 등
    "safety": "안전"
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
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "top_interests": ", ".join(top_interests),
            "address": house_info.get('address', '정보 없음'),
            "price": house_info.get('price_display', '정보 없음'),
            "all_scores": ", ".join(all_scores),
            "infra_str": infra_str
        })
        return response.content.replace("```", "").strip()
    except Exception:
        return "고객님의 라이프스타일 지표를 분석한 결과, 가장 추천해 드리는 맞춤형 매물입니다."

def _to_manwon(value):
    """
    DB 금액을 만원 단위로 통일.
    숫자 또는 "전세 24000" 같은 문자열 모두 처리.
    원 단위(≥10,000,000)이면 /10,000.
    """
    import re as _re
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        v = float(value)
        if v <= 0: return 0.0
        if v >= 10_000_000: return v / 10_000
        return v
    s = str(value).replace(',', '').strip()
    m = _re.search(r'[\d.]+', s)
    if not m: return 0.0
    try:
        v = float(m.group())
    except ValueError:
        return 0.0
    if v <= 0: return 0.0
    if v >= 10_000_000: return v / 10_000
    return v


def get_vfm_score_100(house):
    """
    매물 dict → 100점 만점 가성비 점수.

    VFM.py 와 완전히 동일한 계산 방식:
      expense_per_m2 = (3년 총비용) / size_m2

      전세: 3년 총비용 = 전세금 × 0.04 × 3  (기회비용)
            * price 필드 = 전세금(만원), deposit = 0
      월세: 3년 총비용 = 보증금 × 0.04 × 3 + 월세 × 12 × 3

    stats_map 단위: 만원/㎡  (VFM.py 분석 결과 그대로)
    """
    import re as _re

    YEARS = 3
    RATE  = 0.04

    stats_map = {
        '전세_Normal':   {'peak': 99.4,  'mean': 96.2,  'std': 40.0},
        '월세_Normal':   {'peak': 91.9,  'mean': 124.8, 'std': 51.3},
        '월세_Basement': {'peak': 77.7,  'mean': 76.3,  'std': 22.3},
        '전세_Basement': {'peak': 26.4,  'mean': 31.7,  'std': 11.7},
    }

    rent_type   = house.get('rent_type', '')
    floor_str   = str(house.get('floor', ''))
    is_basement = '반지하' in floor_str
    layer       = 'Basement' if is_basement else 'Normal'
    group       = f"{rent_type}_{layer}"

    if group not in stats_map:
        print(f"[VFM] 알 수 없는 그룹: {group!r}")
        return 60.0

    stats = stats_map[group]

    # ── 면적 ──────────────────────────────────────────────────────────
    size = 0.0
    size_key_used = None
    for key in ('size_m2', 'area', 'size', 'supply_area', 'exclusive_area',
                'area_m2', 'private_area', 'net_area', 'living_area', '전용면적', '공급면적'):
        raw = house.get(key)
        if raw is None:
            continue
        try:
            candidate = float(raw)
        except (TypeError, ValueError):
            m = _re.search(r'[\d.]+', str(raw))
            candidate = float(m.group()) if m else 0.0
        if candidate > 0:
            size = candidate
            size_key_used = key
            break

    if size <= 0:
        safe_keys = [k for k in house.keys()
                     if k not in ('_id', 'images', 'category_scores', 'ai_comments_v2')]
        print(f"[VFM] 면적 필드 없음 — rent_type={rent_type!r} 필드: {safe_keys}")
        return 60.0

    # ── 금액 → 만원 단위 ──────────────────────────────────────────────
    deposit = _to_manwon(house.get('deposit', 0))
    price   = _to_manwon(house.get('price',   0))

    # ── 3년 총비용 계산 (VFM.py calculate_total_cost 동일) ───────────
    if rent_type == '전세':
        real_deposit  = deposit if deposit > 0 else price   # deposit=0이면 price가 전세금
        total_expense = real_deposit * RATE * YEARS
    else:
        total_expense = deposit * RATE * YEARS + price * 12 * YEARS

    if total_expense <= 0:
        print(f"[VFM] total_expense=0 — deposit={deposit} price={price}")
        return 60.0

    expense_per_m2 = total_expense / size

    # ── 점수 계산 (VFM.py calculate_vfm_score_pro 동일) ─────────────
    center    = stats['peak'] if stats['mean'] > stats['peak'] * 1.1 else stats['mean']
    z         = (center - expense_per_m2) / stats['std']
    raw_score = 60.0 + (z * 18.0)

    # 가산점: 최우선변제 보증금 5500만원 이하
    if deposit <= 5500:
        raw_score += 5
    if size < 15:
        raw_score -= 5   # 고시원급 감점

    final = round(max(0.0, min(100.0, raw_score)), 1)
    return final


def get_user_normalized_weights(category_log, custom_weights=None):
    if custom_weights:
        w_sum = sum(custom_weights.values())
        if w_sum == 0: return {k: 1/7 for k in category_map.keys()}
        return {k: float(v) / w_sum for k, v in custom_weights.items()}

    total_counts = {'traffic': 6, 'convenience': 10, 'green': 7, 'play': 6, 'health': 6, 'living': 13, 'safety': 10}
    log_counts = Counter(category_log)
    user_weights = {cat: ((log_counts.get(cat, 0) + 1) / total_counts[cat]) for cat in total_counts}
    w_sum = sum(user_weights.values())
    return {k: v / w_sum for k, v in user_weights.items()}

def format_property_data(houses, user_liked_ids=None):
    for h in houses:
        h['_id_str'] = str(h['_id'])
        rt, p = h.get('rent_type'), h.get('price', 0)
        h['price_display'] = f"{p}" if rt == "전세" else f"{h.get('deposit',0)}/{p}"
        
        raw_imgs = h.get('images', [])
        processed_imgs = [img + ('&w=800' if '?' in img else '?w=800') for img in raw_imgs]
        if not processed_imgs:
            processed_imgs = [url_for('static', filename='img/default_room.jpg')]
        h['images'] = processed_imgs
        h['main_image'] = processed_imgs[0]
        
        scores = h.get('category_scores', {})
        h['chart_data'] = [round(float(scores.get(c, 0)) * 100, 1) for c in ['traffic', 'convenience', 'green', 'play', 'health', 'living', 'safety']]
        h['is_liked'] = False
        if user_liked_ids and h['_id_str'] in user_liked_ids:
            h['is_liked'] = True
        # 가성비 점수 계산
        h['vfm_score'] = get_vfm_score_100(h)
    return houses

def build_match_pipeline(match_query, nw, target_coords=None, limit=10, is_random=False, use_vfm=False):
    """
    use_vfm=True: 기존 라이프스타일:거리 = 8:2 비율을 유지하면서
    가성비(Python 후처리)가 30% 추가되는 구조.
    MongoDB 단계는 라이프스타일·거리로만 정렬 → Python에서 VFM 합산 후 재정렬.
    """
    pipeline = []
    lifestyle_score_expr = {"$add": [{"$multiply": [{"$ifNull": [f"$category_scores.{c}", 0]}, nw[c]]} for c in nw]}

    has_coords = target_coords and 'lng' in target_coords and 'lat' in target_coords and float(target_coords.get('lat', 0)) != 0

    if has_coords:
        pipeline.append({
            "$geoNear": {
                "near": {"type": "Point", "coordinates": [float(target_coords['lng']), float(target_coords['lat'])]},
                "distanceField": "distance_meters",
                "spherical": True,
                "query": match_query
            }
        })
        dist_score_expr = {"$divide": [{"$max": [0, {"$subtract": [5000, "$distance_meters"]}]}, 50]}
        if use_vfm:
            # 라이프스타일 56% + 거리 14% (가성비 30%는 Python 후처리)
            base_expr = {"$add": [
                {"$multiply": [lifestyle_score_expr, 100, 0.56]},
                {"$multiply": [dist_score_expr, 0.14]}
            ]}
        else:
            base_expr = {"$add": [
                {"$multiply": [lifestyle_score_expr, 100, 0.7]},
                {"$multiply": [dist_score_expr, 0.3]}
            ]}
    else:
        pipeline.append({"$match": match_query})
        if use_vfm:
            base_expr = {"$multiply": [lifestyle_score_expr, 70]}  # 70% (가성비 30% Python 후처리)
        else:
            base_expr = {"$multiply": [lifestyle_score_expr, 100]}

    pipeline.append({"$addFields": {"match_score": {"$round": [base_expr, 1]}}})

    if is_random:
        pipeline.append({"$match": {"match_score": {"$gte": 35.0}}})
        pipeline.append({"$sample": {"size": limit}})
    else:
        pipeline.append({"$sort": {"match_score": -1}})
        pipeline.append({"$limit": limit})

    return pipeline


def apply_vfm_to_results(houses):
    """가성비 점수(30%)를 match_score에 합산하고 재정렬"""
    for h in houses:
        vfm = h.get('vfm_score', 60.0)
        h['match_score'] = round(h.get('match_score', 0) + vfm * 0.3, 1)
    houses.sort(key=lambda x: x.get('match_score', 0), reverse=True)
    return houses


def apply_detail_filters(query, selected_survey):
    current_year = datetime.now().year

    # --- 건물 연식: 슬라이더 값(정수, 연도 기준) ---
    max_age = selected_survey.get('max_building_age')   # None = 상관없음
    if max_age is not None:
        try:
            max_age = int(max_age)
            oldest_year = str(current_year - max_age)
            query.setdefault("$and", []).append({"$or": [
                {"built_year": {"$gte": oldest_year}},
                {"year_built": {"$gte": oldest_year}}
            ]})
        except (TypeError, ValueError):
            pass
    else:
        # 구형 방식(building_age 리스트) fallback
        b_age = selected_survey.get('building_age', [])
        if b_age:
            age_conditions = []
            for age in b_age:
                if "신축" in age:
                    age_conditions += [{"built_year": {"$gte": str(current_year - 5)}}, {"year_built": {"$gte": str(current_year - 5)}}]
                elif "준신축" in age:
                    age_conditions += [{"built_year": {"$gte": str(current_year - 10), "$lt": str(current_year - 5)}}, {"year_built": {"$gte": str(current_year - 10), "$lt": str(current_year - 5)}}]
                elif "구축" in age:
                    age_conditions += [{"built_year": {"$lt": str(current_year - 10), "$gte": "1000"}}, {"year_built": {"$lt": str(current_year - 10), "$gte": "1000"}}]
            if age_conditions:
                query.setdefault("$and", []).append({"$or": age_conditions})

    # --- 방 개수: 슬라이더 최솟값 ---
    min_rooms = selected_survey.get('min_room_count')   # 1, 2, 3
    if min_rooms is not None:
        try:
            min_rooms = int(min_rooms)
            if min_rooms == 1:
                pass  # 1개 이상 = 모두 허용
            elif min_rooms == 2:
                query.setdefault("$and", []).append({"$or": [
                    {"room_counts": "2개"},
                    {"room_counts": {"$regex": "^[3-9]개|^[1-9][0-9]+개"}}
                ]})
            elif min_rooms >= 3:
                query.setdefault("$and", []).append({"room_counts": {"$regex": "^[3-9]개|^[1-9][0-9]+개"}})
        except (TypeError, ValueError):
            pass
    else:
        # 구형 방식(room_count 리스트) fallback
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

    s_room = selected_survey.get('special_room', "")
    if "피하고 싶어요" in s_room:
        query.setdefault("$and", []).append({"floor": {"$not": {"$regex": "반지하|([0-9]+)\\s*[/중]\\s*\\1(?:[^0-9]|$)"}}})

    park = selected_survey.get('parking', "")
    if "필요해요" in park:
        query["hasParking"] = {"$ne": "주차 불가능"}

    return query

# ------------------------------------------------------------------
# 라우트 핸들러
# ------------------------------------------------------------------

@survey_bp.route('/survey')
def survey_page():
    if 'user_id' not in session:
        return "<script>alert('로그인이 필요한 서비스입니다.'); window.location.href='/login';</script>"
    client_id = current_app.config.get('NAVER_CLIENT_ID')
    questions = [
        {"title": "현재 나의 라이프스타일과 가장 가까운 유형은?", "multiple": False, "options": [{"text": "갓생형 (운동과 자기계발)", "categories": ["health", "living"]}, {"text": "인싸형 (문화생활, 모임)", "categories": ["play", "convenience"]}, {"text": "워라밸형 (휴식, 여유)", "categories": ["green", "living"]}, {"text": "효율형 (이동 효율 중시)", "categories": ["traffic", "living"]}]},
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
    return render_template('survey.html', questions=questions, client_id=client_id)

@survey_bp.route('/survey/save', methods=['POST'])
def save_survey():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "로그인 필요"}), 401

    user_id = session['user_id']
    data = request.get_json() 
    
    budget_raw = data.get('budget', {})
    def parse_budget(val):
        try:
            if val is None or str(val).strip() == "": return None
            # 소수점 문자열 대응 (ex: "100.0")
            return int(float(val))
        except: return None
    
    new_survey = {
        "user_id": user_id,
        "location": data.get('location', ""),
        "target_coords": data.get('target_coords'),
        "contract_type": data.get('contract_type', ""),
        "budget": {
            "min_dep": parse_budget(budget_raw.get('min_dep')),
            "max_dep": parse_budget(budget_raw.get('max_dep')),
            "min_rent": parse_budget(budget_raw.get('min_rent')),
            "max_rent": parse_budget(budget_raw.get('max_rent'))
        },
        "building_type": data.get('building_type', []),
        "building_age": data.get('building_age', []),
        "max_building_age": data.get('max_building_age'),       # 슬라이더: None=상관없음, 숫자=최대 연식(년)
        "room_count": data.get('room_count', []),
        "min_room_count": data.get('min_room_count', 1),        # 슬라이더: 최소 방 개수
        "special_room": data.get('special_room', ""),
        "parking": data.get('parking', ""),
        "prefer_vfm": data.get('prefer_vfm', False),            # 가성비 점수 반영 여부
        "category_log": data.get('category_log', []),
        "created_at": datetime.now()
    }

    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))
    if len(surveys) >= 10:
        db.survey_results.delete_one({"_id": surveys[-1]['_id']})

    result = db.survey_results.insert_one(new_survey)
    survey_id = str(result.inserted_id)
    # AI 생성 없이 즉시 survey_id 반환 → 프론트엔드에서 result 페이지로 이동
    return jsonify({"status": "success", "survey_id": survey_id})

@survey_bp.route('/survey/result/by_id/<survey_id>')
def survey_result_by_id(survey_id):
    """survey_id(ObjectId)로 직접 결과 페이지 접근 — 설문 직후 이동용"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    try:
        selected_survey = db.survey_results.find_one({"_id": ObjectId(survey_id), "user_id": user_id})
    except Exception:
        return redirect('/mypage')

    if not selected_survey:
        return redirect('/mypage')

    # index 찾기
    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))
    index = next((i for i, s in enumerate(surveys) if str(s['_id']) == survey_id), 0)

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

    # [변경] lifestyle_report가 이미 저장되어 있으면 바로 사용, 없으면 None으로 (AI 로딩 UI 표시)
    detailed_analysis = selected_survey.get('lifestyle_report')

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


@survey_bp.route('/survey/ai_generate/<survey_id>', methods=['POST'])
def ai_generate(survey_id):
    """AI 코멘트 & 라이프스타일 분석을 비동기로 생성하고 DB에 저장하는 API.
    프론트엔드에서 결과 페이지 로드 직후 호출한다."""
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    user_id = session['user_id']

    try:
        selected_survey = db.survey_results.find_one({"_id": ObjectId(survey_id)})
    except Exception:
        return jsonify({"status": "error", "message": "Invalid survey_id"}), 400

    if not selected_survey:
        return jsonify({"status": "error", "message": "Survey not found"}), 404

    nw = get_user_normalized_weights(selected_survey.get('category_log', []))
    top2 = sorted(nw.items(), key=lambda x: x[1], reverse=True)[:2]
    top2_keys = [top2[0][0], top2[1][0]]

    updates = {}

    # 매물 쿼리 먼저 준비
    query = {}
    target_coords = selected_survey.get('target_coords')
    loc = selected_survey.get('location')
    if not target_coords or float(target_coords.get('lat', 0)) == 0:
        if loc and loc != "상관없음": query['address'] = {"$regex": loc}

    c_type = selected_survey.get('contract_type')
    target_rent_type = {"jeonse": "전세", "monthly": "월세"}.get(c_type, c_type)
    if target_rent_type: query['rent_type'] = target_rent_type
    query = apply_detail_filters(query, selected_survey)

    use_vfm_gen = bool(selected_survey.get('prefer_vfm', False))
    pipeline = build_match_pipeline(query, nw, target_coords=target_coords, limit=10, use_vfm=use_vfm_gen)
    matched_properties = format_property_data(list(houses_col.aggregate(pipeline)))
    if use_vfm_gen:
        matched_properties = apply_vfm_to_results(matched_properties)
    top_3 = matched_properties[:3]

    saved_comments = selected_survey.get('ai_comments_v2', {})
    needs_lifestyle = not selected_survey.get('lifestyle_report')
    new_comments = dict(saved_comments)

    # 라이프스타일 분석 + 매물 멘트 3개를 모두 동시에 병렬 실행
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # 라이프스타일 분석 (없을 때만)
        lifestyle_future = executor.submit(
            generate_sandbox_lifestyle_analysis, nw, top2_keys
        ) if needs_lifestyle else None

        # 매물 멘트 (없는 것만)
        comment_futures = {}
        for house in top_3:
            h_id = house['_id_str']
            if h_id not in saved_comments:
                comment_futures[h_id] = executor.submit(
                    generate_recommendation_reason, user_id, nw, house
                )

        # 결과 수집 — timeout을 넉넉하게 45초
        if lifestyle_future:
            try:
                detailed_analysis = lifestyle_future.result(timeout=45)
                updates['lifestyle_report'] = detailed_analysis
            except Exception as e:
                print(f"Lifestyle future error: {e}")
                detailed_analysis = selected_survey.get('lifestyle_report', '')
        else:
            detailed_analysis = selected_survey.get('lifestyle_report', '')

        for house in top_3:
            h_id = house['_id_str']
            if h_id in comment_futures:
                try:
                    new_comments[h_id] = comment_futures[h_id].result(timeout=45)
                except Exception as e:
                    print(f"Comment future error [{h_id}]: {e}")
                    new_comments[h_id] = "분석 중 오류가 발생했습니다."

    if new_comments != saved_comments:
        updates['ai_comments_v2'] = new_comments

    if updates:
        db.survey_results.update_one({"_id": ObjectId(survey_id)}, {"$set": updates})

    # top3 하우스에 코멘트 붙여서 반환
    for house in top_3:
        house['ai_comment'] = new_comments.get(house['_id_str'], '')

    return jsonify({
        "status": "success",
        "detailed_analysis": detailed_analysis,
        "ai_comments": {h['_id_str']: h['ai_comment'] for h in top_3}
    })

@survey_bp.route('/survey/recalculate', methods=['POST'])
def recalculate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400
            
        custom_weights = data.get('weights')
        survey_id_raw = data.get('survey_id')
        
        keys = ["traffic", "convenience", "green", "play", "health", "living", "safety"]
        nw = {}
        
        if isinstance(custom_weights, list):
            for i, key in enumerate(keys):
                nw[key] = custom_weights[i] if i < len(custom_weights) else 0
        elif isinstance(custom_weights, dict):
            nw = {k: custom_weights.get(k, 0) for k in keys}
        else:
            return jsonify({"status": "error", "message": "Invalid weights format"}), 400

        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
            
        surveys = list(db.survey_results.find({"user_id": session['user_id']}).sort("created_at", -1))
        
        selected_survey = None
        if str(survey_id_raw).isdigit():
            idx = int(survey_id_raw)
            if idx < len(surveys):
                selected_survey = surveys[idx]
        else:
            try:
                selected_survey = db.survey_results.find_one({"_id": ObjectId(survey_id_raw)})
            except:
                if surveys: selected_survey = surveys[0]

        if not selected_survey:
            return jsonify({"status": "error", "message": "Survey not found"}), 404

        total_w = sum(nw.values())
        nw_norm = {k: v/total_w for k, v in nw.items()} if total_w > 0 else {k: 1/7 for k in keys}

        client_filters = data.get('filters', {})
        query = {}
        if client_filters:
            query = apply_detail_filters({}, client_filters)
            c_type = client_filters.get('contract_type')
            target_rent_type = {"jeonse": "전세", "monthly": "월세"}.get(c_type, c_type)
            if target_rent_type: query['rent_type'] = target_rent_type
            
            def parse_filter_val(val):
                if val is None or str(val).strip() == "": return None
                try: return int(float(val))
                except: return None

            min_dep = parse_filter_val(client_filters.get('min_dep'))
            max_dep = parse_filter_val(client_filters.get('max_dep'))

            if target_rent_type == "전세":
                price_q = {}
                if min_dep is not None: price_q["$gte"] = min_dep
                if max_dep is not None: price_q["$lte"] = max_dep
                if price_q: query['price'] = price_q
            else:
                dep_q = {}
                if min_dep is not None: dep_q["$gte"] = min_dep
                if max_dep is not None: dep_q["$lte"] = max_dep
                if dep_q: query['deposit'] = dep_q
                
                min_rent = parse_filter_val(client_filters.get('min_rent'))
                max_rent = parse_filter_val(client_filters.get('max_rent'))
                rent_q = {}
                if min_rent is not None: rent_q["$gte"] = min_rent
                if max_rent is not None: rent_q["$lte"] = max_rent
                if rent_q: query['price'] = rent_q
        else:
            query = apply_detail_filters({}, selected_survey)

        # 가성비 반영 여부 (클라이언트 필터 우선, 없으면 설문 저장값)
        use_vfm = bool(client_filters.get('prefer_vfm', selected_survey.get('prefer_vfm', False))) if client_filters else bool(selected_survey.get('prefer_vfm', False))

        pipeline = build_match_pipeline(query, nw_norm, target_coords=selected_survey.get('target_coords'), limit=12, use_vfm=use_vfm)
        matched_properties = format_property_data(list(houses_col.aggregate(pipeline)))
        if use_vfm:
            matched_properties = apply_vfm_to_results(matched_properties)

        futures_recalc = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            for house in matched_properties[:3]:
                h_id = house['_id_str']
                futures_recalc[h_id] = executor.submit(generate_recommendation_reason, session['user_id'], nw_norm, house)
            
            for house in matched_properties[:3]:
                h_id = house['_id_str']
                try:
                    house['ai_comment'] = futures_recalc[h_id].result(timeout=10)
                except:
                    house['ai_comment'] = "추천 이유를 생성하지 못했습니다."

        sorted_nw = sorted(nw_norm.items(), key=lambda x: x[1], reverse=True)
        top2_keys = frozenset([sorted_nw[0][0], sorted_nw[1][0]])
        user_type, user_type_desc = TYPE_MAP.get(top2_keys, ("맞춤형 분석가", "라이프스타일에 맞는 매물을 찾는 중입니다."))

        return jsonify({
            "status": "success",
            "items": matched_properties,
            "user_type": user_type,
            "user_type_desc": user_type_desc
        })
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
    # 1. 로그인 여부 확인 (비로그인 시 user_id는 None)
    user_id = session.get('user_id')
    
    # 2. 설문 데이터 가져오기 (비로그인 시 None)
    latest_survey = None
    if user_id:
        latest_survey = db.survey_results.find_one(
            {"user_id": user_id}, 
            sort=[("created_at", -1)]
        )

    # 3. 가중치 및 쿼리 조건 설정
    if not latest_survey:
        # 비로그인 유저: 기본 가중치 및 전체 매물 대상
        nw = {k: 1/7 for k in category_map.keys()}
        query = {}
        target_coords = None
    else:
        # 로그인 유저: 최근 설문 기반 필터 및 가중치 적용
        nw = get_user_normalized_weights(latest_survey.get('category_log', []))
        query = apply_detail_filters({}, latest_survey)
        target_coords = latest_survey.get('target_coords')

    # 4. 페이지네이션(블록) 관리
    # 세션에서 현재 몇 번째 블록인지 가져와서 1 증가시킴
    current_block = session.get('short_block', 0)
    next_block = current_block + 1
    
    # 5. 매칭 파이프라인 구축 (랜덤 샘플링 방식)
    # limit=1000은 전체 후보군을 넓게 잡기 위함입니다.
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
    - 최우선 핵심 가치 2가지: {{top_names}}
    - 7대 지표별 세부 가중치: {{weight_pct}}

    [추천 동네 데이터] — 코드가 계산한 결과입니다. 아래 3개 동네만 사용하고 절대 임의로 동네명을 만들지 마세요.
    {{dong_data}}

    [말투 및 제약 조건]
    - 톤앤매너: 센스 있는 잡지 에디터나 다정한 공간 디렉터처럼 부드럽고 세련된 말투를 사용하세요.
    - 너무 격식을 차린 딱딱한 표현(예: '귀하', '제언합니다') 대신, 대화하듯 친근하면서도 신뢰감이 느껴지는 어조(예: '~인 것 같아요', '~를 추천해 드리고 싶어요', '~를 즐겨보시는 건 어떨까요?')를 사용하세요.
    - 🚨 dong name에는 반드시 [추천 동네 데이터]의 이름만 쓰세요. 절대 임의 생성 금지.
    - 🔥 JSON 외 다른 텍스트(마크다운, 코드블록 ```, 설명문 등)는 절대 출력하지 마세요.

    [출력 형식] 반드시 아래 JSON 구조로만 응답하세요 (키 이름 변경 금지):
    {{{{
      "summary": "고객의 라이프스타일 전체를 2~3문장으로 따뜻하고 감성적으로 요약. 잡지 에디터 스타일로.",
      "insights": [
        {{{{
          "label": "지표명 (7대 지표 중 비중 높은 순서대로 3개)",
          "weight": "00.0%",
          "desc": "이 지표가 이 고객에게 왜 중요한지, 어떤 라이프스타일을 반영하는지 2~3문장으로 감성적으로 설명"
        }}}},
        {{{{"label": "지표명", "weight": "00.0%", "desc": "설명"}}}},
        {{{{"label": "지표명", "weight": "00.0%", "desc": "설명"}}}}
      ],
      "dongs": [
        {{{{
          "name": "동네명 (반드시 위 [추천 동네 데이터]의 이름만 사용)",
          "desc": "이 동네가 이 고객의 라이프스타일과 왜 잘 맞는지 2~3문장으로 감성적으로 설명. 데이터 점수를 근거로.",
          "points": ["구체적 장점 1", "구체적 장점 2", "구체적 장점 3"]
        }}}},
        {{{{"name": "동네명", "desc": "설명", "points": ["장점1", "장점2", "장점3"]}}}},
        {{{{"name": "동네명", "desc": "설명", "points": ["장점1", "장점2", "장점3"]}}}}
      ]
    }}}}
    """

    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm

    try:
        response = chain.invoke({
            "top_names": ", ".join(top_names),
            "weight_pct": str(weight_pct),
            "dong_data": dong_data_str
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
                {"name": dong_data_lines[0].split(":")[0].replace("- ","").strip() if dong_data_lines else "추천 동네", "desc": "고객님의 라이프스타일에 잘 맞는 동네예요.", "points": ["쾌적한 환경", "편리한 교통", "생활 인프라 우수"]},
                {"name": dong_data_lines[1].split(":")[0].replace("- ","").strip() if len(dong_data_lines) > 1 else "추천 동네 2", "desc": "편리하고 활기찬 동네예요.", "points": ["편의시설 풍부", "안전한 주거환경", "다양한 문화시설"]},
                {"name": dong_data_lines[2].split(":")[0].replace("- ","").strip() if len(dong_data_lines) > 2 else "추천 동네 3", "desc": "조용하고 살기 좋은 동네예요.", "points": ["녹지공간 풍부", "안정적인 주거", "좋은 교육환경"]}
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