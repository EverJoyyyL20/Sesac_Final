from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from database import houses_col, db
from bson.objectid import ObjectId
from datetime import datetime
from collections import Counter
import os
from dotenv import load_dotenv 
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

load_dotenv(override=True)

# ------------------------------------------------------------------
# AI 및 초기 설정
# ------------------------------------------------------------------
api_key = os.getenv("OPENAI_API_KEY")

try:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, openai_api_key=api_key)
    print("✅ GPT 모델 초기화 성공")
except Exception as e:
    print(f"❌ GPT 초기화 실패: {e}")

survey_bp = Blueprint('survey', __name__, template_folder='.')

# DB 카테고리 키와 한글 명칭 매핑 (7개 지표로 통일)
category_map = {
    "traffic": "교통", "convenience": "편의", "green": "녹지",
    "play": "놀이", "health": "건강", "living": "생활", "safety": "안전"
}

TYPE_MAP = {
    frozenset(["traffic", "convenience"]): ("🚇 도심 직장인형", "출퇴근과 생활 편의성을 가장 중요하게 생각하는 타입이에요."),
    frozenset(["traffic", "green"]): ("🌿 도심 힐링형", "이동은 편리하면서도 자연이 가까운 환경을 선호해요."),
    frozenset(["traffic", "play"]): ("🚀 도시 액션형", "이동이 자유롭고 즐길 거리가 많은 동네를 좋아해요."),
    frozenset(["traffic", "health"]): ("🏃 활력 출퇴근형", "바쁜 일상 속에서도 건강한 생활을 중시해요."),
    frozenset(["traffic", "living"]): ("🏙 현실 최적화형", "출퇴근과 일상 동선의 효율을 중요하게 여겨요."),
    frozenset(["traffic", "safety"]): ("🚦 안정 출퇴근형", "빠른 이동과 안전한 주거 환경을 동시에 원해요."),
    frozenset(["convenience", "green"]): ("🍃 쾌적 생활형", "생활은 편리하고 주변 환경은 쾌적하길 바라요."),
    frozenset(["convenience", "play"]): ("🎉 액티브 라이프형", "놀거리와 편의시설이 가까운 곳을 선호해요."),
    frozenset(["convenience", "health"]): ("💪 웰빙 생활형", "편리한 환경 속에서 건강한 삶을 추구해요."),
    frozenset(["convenience", "living"]): ("🧺 생활 밀착형", "일상에 필요한 시설이 가까운 걸 중요하게 생각해요."),
    frozenset(["convenience", "safety"]): ("🛡 안심 생활형", "편리함은 기본, 안전은 필수라고 생각해요."),
    frozenset(["green", "play"]): ("🌳 여유 액티브형", "자연 속에서도 즐길 거리가 있길 원해요."),
    frozenset(["green", "health"]): ("🌿 힐링 라이프형", "조용하고 쾌적한 환경에서 건강한 삶을 원해요."),
    frozenset(["green", "living"]): ("🌱 정주 힐링형", "자연 친화적인 동네에서 오래 살고 싶어요."),
    frozenset(["green", "safety"]): ("🍀 안심 힐링형", "조용하고 안전한 주거 환경을 선호해요."),
    frozenset(["play", "health"]): ("🔥 에너지 충전형", "활동과 건강을 모두 챙기는 라이프스타일이에요."),
    frozenset(["play", "living"]): ("🎈 즐거운 일상형", "일상 속에서도 재미와 활기를 찾고 싶어요."),
    frozenset(["play", "safety"]): ("🎮 세이프 플레이형", "즐길 건 즐기되 안전도 중요해요."),
    frozenset(["health", "living"]): ("🍎 웰니스 정주형", "건강하고 규칙적인 생활을 중요하게 여겨요."),
    frozenset(["health", "safety"]): ("🧘 안심 웰빙형", "몸도 마음도 편안한 환경을 선호해요."),
    frozenset(["living", "safety"]): ("🏡 안정 중시형", "살기 편하고 걱정 없는 동네가 최고예요."),
}

# ------------------------------------------------------------------
# 유틸리티 함수
# ------------------------------------------------------------------

def generate_recommendation_reason(user_weights, house_info):
    # 가중치가 높은 상위 2개 카테고리 추출
    sorted_weights = sorted(user_weights.items(), key=lambda x: x[1], reverse=True)
    top_interests = [f"{category_map.get(k, k)}" for k, v in sorted_weights[:2]]
    
    # 매물의 강점 점수 추출 (category_scores 필드 사용)
    scores = house_info.get('category_scores', {})
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_strengths = [f"{category_map.get(k.lower(), k)}({int(v*100)}점)" for k, v in sorted_scores[:2]]

    template = """
    당신은 전문 부동산 컨설턴트입니다. 사용자의 선호도와 매물 데이터를 분석하여 추천 이유를 작성하세요.
    [사용자 선호] 중요 가치: {top_interests}
    [매물 정보] 주소: {address}, 가격: {price}, 핵심 강점: {top_strengths}
    가이드: 한 문장(80자 이내), "~하기 때문에 딱 맞는 매물입니다" 말투 사용.
    """
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm
    try:
        response = chain.invoke({
            "top_interests": ", ".join(top_interests),
            "address": house_info['address'],
            "price": house_info['price_display'],
            "top_strengths": ", ".join(top_strengths)
        })
        return response.content
    except:
        return "라이프스타일 분석 결과, 고객님께 가장 가치 있는 매물로 선정되었습니다!"

def get_user_normalized_weights(category_log, custom_weights=None):
    if custom_weights:
        # 프론트에서 보낸 {'traffic': 20, 'living': 15 ...} 형태 처리
        w_sum = sum(custom_weights.values())
        if w_sum == 0: return {k: 1/7 for k in category_map.keys()}
        # 합계가 1이 되도록 정규화
        return {k: float(v) / w_sum for k, v in custom_weights.items()}

    # 설문 로그 기반 가중치 계산 (기존 로직)
    total_counts = {'traffic': 6, 'convenience': 10, 'green': 7, 'play': 6, 'health': 6, 'living': 13, 'safety': 10}
    log_counts = Counter(category_log)
    user_weights = {cat: ((log_counts.get(cat, 0) + 1) / total_counts[cat]) for cat in total_counts}
    w_sum = sum(user_weights.values())
    return {k: v / w_sum for k, v in user_weights.items()}

def format_property_data(houses):
    for h in houses:
        h['_id_str'] = str(h['_id'])
        rt, p = h.get('rent_type'), h.get('price', 0)
        # 가격 표시 변환
        h['price_display'] = f"{p}" if rt == "전세" else f"{h.get('deposit',0)}/{p}"
        
        # 이미지 처리
        raw_imgs = h.get('images', [])
        processed_imgs = [img + ('&w=800' if '?' in img else '?w=800') for img in raw_imgs]
        if not processed_imgs:
            processed_imgs = [url_for('static', filename='img/default_room.jpg')]
        h['images'] = processed_imgs
        h['main_image'] = processed_imgs[0]
        
        # 차트용 데이터 (7각형 순서: 교통, 편의, 녹지, 놀이, 건강, 생활, 안전)
        scores = h.get('category_scores', {})
        h['chart_data'] = [round(scores.get(c, 0) * 100, 1) for c in ['traffic', 'convenience', 'green', 'play', 'health', 'living', 'safety']]
    return houses

def build_match_pipeline(match_query, nw, target_coords=None, limit=10, is_random=False):
    pipeline = []
    # 라이프스타일 가중치 계산 식 (7개 지표 합산)
    lifestyle_score_expr = {"$add": [{"$multiply": [{"$ifNull": [f"$category_scores.{c}", 0]}, nw[c]]} for c in nw]}

    if target_coords and 'lng' in target_coords and 'lat' in target_coords and float(target_coords['lat']) != 0:
        pipeline.append({
            "$geoNear": {
                "near": {
                    "type": "Point", 
                    "coordinates": [float(target_coords['lng']), float(target_coords['lat'])]
                },
                "distanceField": "distance_meters",
                "spherical": True,
                "query": match_query
            }
        })
        # 5km 이내 가산점
        dist_score_expr = {"$divide": [{"$max": [0, {"$subtract": [5000, "$distance_meters"]}]}, 50]}
        final_score_expr = {
            "$add": [
                {"$multiply": [lifestyle_score_expr, 100, 0.7]},
                {"$multiply": [dist_score_expr, 0.3]}
            ]
        }
    else:
        pipeline.append({"$match": match_query})
        final_score_expr = {"$multiply": [lifestyle_score_expr, 100]}

    pipeline.append({
        "$addFields": {
            "match_score": {"$round": [final_score_expr, 1]}
        }
    })

    if is_random:
        pipeline.append({"$match": {"match_score": {"$gte": 70.0}}})
        pipeline.append({"$sample": {"size": limit}})
    else:
        pipeline.append({"$sort": {"match_score": -1}})
        pipeline.append({"$limit": limit})
        
    return pipeline

def apply_detail_filters(query, selected_survey):
    # 1. 희망하는 건물 연식
    b_age = selected_survey.get('building_age', [])
    if b_age:
        current_year = datetime.now().year
        age_conditions = []
        for age in b_age:
            if "신축" in age:
                age_conditions.append({"built_year": {"$gte": str(current_year - 5)}})
                age_conditions.append({"year_built": {"$gte": str(current_year - 5)}})
            elif "준신축" in age:
                age_conditions.append({"built_year": {"$gte": str(current_year - 10), "$lt": str(current_year - 5)}})
                age_conditions.append({"year_built": {"$gte": str(current_year - 10), "$lt": str(current_year - 5)}})
            elif "구축" in age:
                age_conditions.append({"built_year": {"$lt": str(current_year - 10), "$gte": "1000"}})
                age_conditions.append({"year_built": {"$lt": str(current_year - 10), "$gte": "1000"}})
        if age_conditions:
            query.setdefault("$and", []).append({"$or": age_conditions})

    # 2. 희망하는 방 개수
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

    # 3. 반지하/옥탑방 제외
    s_room = selected_survey.get('special_room', "")
    if "피하고 싶어요" in s_room:
        query["floor"] = {"$not": {"$regex": "반지하|([0-9]+)\\s*[/중]\\s*\\1(?:[^0-9]|$)"}}

    # 4. 주차장 유무
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
    
    new_survey = {
        "user_id": user_id,
        "location": data.get('location', ""),
        "target_coords": data.get('target_coords'),
        "contract_type": data.get('contract_type', ""),
        "budget": {
            "min_dep": int(budget_raw.get('min_dep', 0) or 0),
            "max_dep": int(budget_raw.get('max_dep', 0) or 2000000000), # 최대값 없을 시 크게 잡음
            "min_rent": int(budget_raw.get('min_rent', 0) or 0),
            "max_rent": int(budget_raw.get('max_rent', 0) or 10000000)
        },
        "building_type": data.get('building_type', []),
        "building_age": data.get('building_age', []),
        "room_count": data.get('room_count', []),
        "special_room": data.get('special_room', ""),
        "parking": data.get('parking', ""),
        "category_log": data.get('category_log', []),
        "created_at": datetime.now()
    }

    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))
    if len(surveys) >= 3:
        db.survey_results.delete_one({"_id": surveys[-1]['_id']})

    db.survey_results.insert_one(new_survey)
    return jsonify({"status": "success", "target_index": 0})

@survey_bp.route('/survey/result/<int:index>')
def survey_result(index):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))
    
    if not surveys or index >= len(surveys):
        return redirect('/mypage')

    selected_survey = surveys[index]
    survey_id = selected_survey['_id']
    
    nw = get_user_normalized_weights(selected_survey.get('category_log', []))
    top2 = sorted(nw.items(), key=lambda x: x[1], reverse=True)[:2]
    user_type, user_type_desc = TYPE_MAP.get(frozenset([top2[0][0], top2[1][0]]), ("기본형", "당신에게 꼭 맞는 매물을 찾고 있어요."))

    # 7각형 차트용 (항목 7개로 확장)
    chart_keys = ['traffic', 'convenience', 'green', 'play', 'health', 'living', 'safety']
    user_chart_labels = ['교통', '편의', '녹지', '놀이', '건강', '생활', '안전']
    user_chart_data = [round(nw.get(k, 0) * 100, 1) for k in chart_keys]

    # 필터 쿼리 구성
    query = {}
    target_coords = selected_survey.get('target_coords')
    loc = selected_survey.get('location')
    if not target_coords or target_coords.get('lat') == 0:
        if loc and loc != "상관없음": query['address'] = {"$regex": loc}
    
    c_type = selected_survey.get('contract_type')
    target_rent_type = {"jeonse": "전세", "monthly": "월세"}.get(c_type, c_type)
    if target_rent_type: query['rent_type'] = target_rent_type
    
    budget = selected_survey.get('budget', {})
    min_dep, max_dep = budget.get('min_dep', 0), budget.get('max_dep', 0)
    min_rent, max_rent = budget.get('min_rent', 0), budget.get('max_rent', 0)

    if target_rent_type == "전세":
        if max_dep > 0: query['price'] = {"$gte": min_dep, "$lte": max_dep}
    elif target_rent_type == "월세":
        if max_dep > 0: query['deposit'] = {"$gte": min_dep, "$lte": max_dep}
        if max_rent > 0: query['price'] = {"$gte": min_rent, "$lte": max_rent}

    query = apply_detail_filters(query, selected_survey)

    total_count = houses_col.count_documents(query)
    pipeline = build_match_pipeline(query, nw, target_coords=target_coords, limit=10)
    matched_properties = format_property_data(list(houses_col.aggregate(pipeline)))

    # AI 코멘트 캐싱 로직
    top_3 = matched_properties[:3]
    others = matched_properties[3:]
    saved_comments = selected_survey.get('ai_comments', {})
    is_updated = False

    for house in top_3:
        h_id = house['_id_str']
        if h_id in saved_comments:
            house['ai_comment'] = saved_comments[h_id]
        else:
            new_comment = generate_recommendation_reason(nw, house)
            house['ai_comment'] = new_comment
            saved_comments[h_id] = new_comment
            is_updated = True

    if is_updated:
        db.survey_results.update_one({"_id": survey_id}, {"$set": {"ai_comments": saved_comments}})
    
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
        index = index
    )

# 🔥 [실시간 시뮬레이션용 API]
@survey_bp.route('/survey/recalculate', methods=['POST'])
def recalculate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400
            
        custom_weights = data.get('weights')
        survey_id_raw = data.get('survey_id')
        
        # 1. 가중치 데이터 형식 검증 및 변환
        keys = ["traffic", "convenience", "green", "play", "health", "living", "safety"]
        nw = {}
        
        # 만약 custom_weights가 리스트([20, 10...])로 왔을 경우
        if isinstance(custom_weights, list):
            for i, key in enumerate(keys):
                nw[key] = custom_weights[i] if i < len(custom_weights) else 0
        # 만약 객체({'traffic': 20...})로 왔을 경우
        elif isinstance(custom_weights, dict):
            nw = {k: custom_weights.get(k, 0) for k in keys}
        else:
            return jsonify({"status": "error", "message": "Invalid weights format"}), 400

        # 2. 사용자 및 설문 데이터 확인
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
            
        surveys = list(db.survey_results.find({"user_id": session['user_id']}).sort("created_at", -1))
        
        selected_survey = None
        # ID가 인덱스(0, 1, 2...)인지 ObjectId인지 판단
        if str(survey_id_raw).isdigit():
            idx = int(survey_id_raw)
            if idx < len(surveys):
                selected_survey = surveys[idx]
        else:
            try:
                selected_survey = db.survey_results.find_one({"_id": ObjectId(survey_id_raw)})
            except:
                # ObjectId 변환 실패 시 최신 설문 사용
                if surveys: selected_survey = surveys[0]

        if not selected_survey:
            return jsonify({"status": "error", "message": "Survey not found"}), 404

        # 3. 필터 및 매칭 로직 실행
        # NW 정규화 (합계를 1로)
        total_w = sum(nw.values())
        if total_w > 0:
            nw_norm = {k: v/total_w for k, v in nw.items()}
        else:
            nw_norm = {k: 1/7 for k in keys}

        # 필터 수집 (JS에서 보낸 filters가 있다면 사용, 없으면 기존 설문 필터 사용)
        client_filters = data.get('filters', {})
        if client_filters:
            # JS에서 보낸 실시간 필터 적용
            query = apply_detail_filters({}, client_filters)
            # 가격 필터 추가
            c_type = client_filters.get('contract_type')
            target_rent_type = {"jeonse": "전세", "monthly": "월세"}.get(c_type, c_type)
            if target_rent_type: query['rent_type'] = target_rent_type
            
            min_dep = int(client_filters.get('min_dep') or 0)
            max_dep = int(client_filters.get('max_dep') or 2000000000)
            if target_rent_type == "전세":
                query['price'] = {"$gte": min_dep, "$lte": max_dep}
            else:
                query['deposit'] = {"$gte": min_dep, "$lte": max_dep}
                query['price'] = {"$gte": int(client_filters.get('min_rent') or 0), "$lte": int(client_filters.get('max_rent') or 10000000)}
        else:
            query = apply_detail_filters({}, selected_survey)

        pipeline = build_match_pipeline(query, nw_norm, target_coords=selected_survey.get('target_coords'), limit=12)
        matched_properties = format_property_data(list(houses_col.aggregate(pipeline)))

        # --- 이 부분을 추가하세요 ---
        # 실시간 조정 시에도 상위 3개 매물에 대해 AI 추천 사유 생성
        for house in matched_properties[:3]:
            # generate_recommendation_reason 함수를 호출하여 코멘트 생성
            house['ai_comment'] = generate_recommendation_reason(nw_norm, house)
        # --------------------------

        # 유저 타입 계산
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
        print(traceback.format_exc()) # 상세 에러 로그 출력
        return jsonify({"status": "error", "message": str(e)}), 500

@survey_bp.route('/survey/short/<int:index>')
def survey_short(index):
    if 'user_id' not in session: return redirect(url_for('login'))
    surveys = list(db.survey_results.find({"user_id": session['user_id']}).sort("created_at", -1))
    if not surveys or index >= len(surveys): return redirect('/mypage')
    
    selected_survey = surveys[index]
    nw = get_user_normalized_weights(selected_survey.get('category_log', []))
    query = apply_detail_filters({}, selected_survey) # 기본 필터 적용

    pipeline = build_match_pipeline(query, nw, target_coords=selected_survey.get('target_coords'), limit=50)
    pipeline.append({"$sample": {"size": 12}})
    
    recommendations = format_property_data(list(houses_col.aggregate(pipeline)))
    session['short_block'] = 0
    session.modified = True

    return render_template('shorts.html', recommendations=recommendations, current_index=index)

@survey_bp.route('/survey/short/<int:index>/more')
def survey_short_more(index):
    if 'user_id' not in session: return jsonify({"status": "error"}), 401
    surveys = list(db.survey_results.find({"user_id": session['user_id']}).sort("created_at", -1))
    if not surveys or index >= len(surveys): return jsonify({"status": "error"}), 400

    selected_survey = surveys[index]
    nw = get_user_normalized_weights(selected_survey.get('category_log', []))
    query = apply_detail_filters({}, selected_survey)

    next_block = session.get('short_block', 0) + 1
    pipeline = build_match_pipeline(query, nw, target_coords=selected_survey.get('target_coords'), limit=100)
    pipeline.extend([{"$skip": next_block * 12}, {"$limit": 12}])
    
    new_items = list(houses_col.aggregate(pipeline))
    if not new_items: return jsonify({"status": "success", "items": [], "has_more": False})

    session['short_block'] = next_block
    session.modified = True
    return jsonify({"status": "success", "items": format_property_data(new_items), "has_more": True})