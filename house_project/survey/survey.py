from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from database import houses_col, db
from bson.objectid import ObjectId
from datetime import datetime
from collections import Counter
import os
from dotenv import load_dotenv 
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
import concurrent.futures

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
# DB 실제 데이터를 활용한 완벽한 프라이빗 브리핑 생성
# ------------------------------------------------------------------
def generate_recommendation_reason(user_id, nw, house_info):
    user_doc = db.user.find_one({"email": user_id})
    actual_weight = user_doc.get("Weight", nw) if user_doc else nw
    
    sorted_weights = sorted(actual_weight.items(), key=lambda x: x[1], reverse=True)
    top_interests = [f"{category_map.get(k, k)}({int(float(v)*100)}%)" for k, v in sorted_weights[:2]]
    
    scores = house_info.get('category_scores', {})
    all_scores = [f"{category_map.get(k.lower(), k)} {int(float(v)*100)}점" for k, v in scores.items() if float(v) > 0]
    
    lng, lat = None, None
    if 'location' in house_info and 'coordinates' in house_info['location']:
        coords = house_info['location']['coordinates']
        if len(coords) == 2:
            lng, lat = coords[0], coords[1]
    
    nearby_infra_names = []
    if lat is not None and lng is not None:
        try:
            infra_cursor = db.infra.aggregate([
                {
                    "$geoNear": {
                        "near": { "type": "Point", "coordinates": [float(lng), float(lat)] },
                        "distanceField": "dist",
                        "maxDistance": 1000, 
                        "spherical": True
                    }
                },
                { "$limit": 6 } 
            ])
            for doc in infra_cursor:
                name = doc.get('name')
                cat = doc.get('category', '')
                cat_kr = category_map.get(cat, cat)
                if name: nearby_infra_names.append(f"{name}({cat_kr})")
        except Exception as e:
            pass

    infra_str = ", ".join(list(set(nearby_infra_names))) if nearby_infra_names else "훌륭한 지역 상권 및 인프라"

    template = """
    당신은 상위 1% VIP를 전담하는 수석 부동산 큐레이터입니다.
    고객의 최우선 가중치, 매물의 실제 지표 점수, 그리고 매물 1km 이내의 실제 인프라 시설을 종합하여 이 매물을 강력히 추천하는 '심층 브리핑'을 작성해주세요.

    [고객 분석 데이터] 최우선 선호 지표: {top_interests}
    [추천 매물 데이터] 주소: {address}, 가격: {price}
    [매물 평가 점수] {all_scores}
    [매물 주변 실제 인프라] {infra_str}

    [작성 가이드]
    1. 분량: 반드시 3~4개의 문단으로 구성된 긴 호흡의 글 (약 350~450자 분량)을 작성하세요. 절대 짧게 쓰지 마세요.
    2. 내용 구성:
       - 첫 문단: 고객의 '{top_interests}' 성향을 언급하며 이 매물이 왜 완벽한 맞춤형 공간인지 총평하세요.
       - 두 번째 문단: [매물 평가 점수]에 명시된 구체적인 '점수 숫자'를 1~2개 언급하며 객관적인 강점을 논리적으로 어필하세요.
       - 세 번째 문단: [매물 주변 실제 인프라]에 나열된 장소 이름들(예: 특정 공원, 식당, 병원명 등)을 직접 언급하며, 이곳에 살면 어떤 프리미엄 일상을 누릴 수 있는지 시각적으로 묘사하세요.
    3. 톤앤매너: 5성급 호텔 컨시어지나 프라이빗 뱅커(PB)처럼 극도로 정중하고, 세련되며, 확신에 찬 어조를 사용하세요. (~입니다, ~누리실 수 있습니다)
    4. 제약사항: 문장 첫머리나 끝에 마크다운(```)이나 HTML 태그를 절대 넣지 마세요. 자연스러운 엔터(줄바꿈)만 사용하여 문단을 구분하세요.
    """
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "top_interests": ", ".join(top_interests),
            "address": house_info['address'],
            "price": house_info['price_display'],
            "all_scores": ", ".join(all_scores),
            "infra_str": infra_str
        })
        return response.content.replace("```", "").strip()
    except Exception as e:
        return "고객님의 라이프스타일 지표와 주변 인프라를 종합적으로 분석한 결과, 가장 추천해 드리는 맞춤형 매물입니다."

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

def format_property_data(houses):
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
        h['chart_data'] = [round(scores.get(c, 0) * 100, 1) for c in ['traffic', 'convenience', 'green', 'play', 'health', 'living', 'safety']]
    return houses

def build_match_pipeline(match_query, nw, target_coords=None, limit=10, is_random=False):
    pipeline = []
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
        # 팀원 수정사항: 거리별 점수 산정 로직 개선
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
        # 팀원 수정사항: 랜덤 추출 기준 점수 하향(50.0)
        pipeline.append({"$match": {"match_score": {"$gte": 50.0}}})
        pipeline.append({"$sample": {"size": limit}})
    else:
        pipeline.append({"$sort": {"match_score": -1}})
        pipeline.append({"$limit": limit})
        
    return pipeline

def apply_detail_filters(query, selected_survey):
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
        query["floor"] = {"$not": {"$regex": "반지하|([0-9]+)\\s*[/중]\\s*\\1(?:[^0-9]|$)"}}

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
    
    # 질문자님 핵심 로직: 빈칸인 경우 강제로 0을 넣지 않음
    budget_raw = data.get('budget', {})
    def parse_budget(val):
        try:
            if val is None or str(val).strip() == "": return None
            return int(val)
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
        "room_count": data.get('room_count', []),
        "special_room": data.get('special_room', ""),
        "parking": data.get('parking', ""),
        "category_log": data.get('category_log', []),
        "created_at": datetime.now()
    }

    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))
    if len(surveys) >= 10:
        db.survey_results.delete_one({"_id": surveys[-1]['_id']})

    db.survey_results.insert_one(new_survey)
    return jsonify({"status": "success", "target_index": 0})

@survey_bp.route('/survey/result/<int:index>')
def survey_result(index):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))
    
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

    is_updated = False
    detailed_analysis = selected_survey.get('lifestyle_report')
    if not detailed_analysis:
        detailed_analysis = generate_sandbox_lifestyle_analysis(nw, top2_keys)
        db.survey_results.update_one({"_id": survey_id}, {"$set": {"lifestyle_report": detailed_analysis}})
        is_updated = True

    query = {}
    target_coords = selected_survey.get('target_coords')
    loc = selected_survey.get('location')
    if not target_coords or target_coords.get('lat') == 0:
        if loc and loc != "상관없음": query['address'] = {"$regex": loc}
    
    c_type = selected_survey.get('contract_type')
    target_rent_type = {"jeonse": "전세", "monthly": "월세"}.get(c_type, c_type)
    if target_rent_type: query['rent_type'] = target_rent_type
    
    budget = selected_survey.get('budget', {})
    min_dep, max_dep = budget.get('min_dep'), budget.get('max_dep')
    min_rent, max_rent = budget.get('min_rent'), budget.get('max_rent')

    if max_dep == 2000000000: max_dep = None
    if max_rent == 10000000: max_rent = None

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

    total_count = houses_col.count_documents(query)
    pipeline = build_match_pipeline(query, nw, target_coords=target_coords, limit=10)
    matched_properties = format_property_data(list(houses_col.aggregate(pipeline)))

    top_3 = matched_properties[:3]
    others = matched_properties[3:]
    saved_comments = selected_survey.get('ai_comments_v2', {})

    futures = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        for house in top_3:
            h_id = house['_id_str']
            if h_id in saved_comments:
                house['ai_comment'] = saved_comments[h_id]
            else:
                futures[h_id] = executor.submit(generate_recommendation_reason, user_id, nw, house)
        
        for house in top_3:
            h_id = house['_id_str']
            if h_id in futures:
                new_comment = futures[h_id].result()
                house['ai_comment'] = new_comment
                saved_comments[h_id] = new_comment
                is_updated = True

    if is_updated:
        db.survey_results.update_one({"_id": survey_id}, {"$set": {"ai_comments_v2": saved_comments}})
    
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
        index = index
    )

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
        if total_w > 0:
            nw_norm = {k: v/total_w for k, v in nw.items()}
        else:
            nw_norm = {k: 1/7 for k in keys}

        client_filters = data.get('filters', {})
        if client_filters:
            query = apply_detail_filters({}, client_filters)
            c_type = client_filters.get('contract_type')
            target_rent_type = {"jeonse": "전세", "monthly": "월세"}.get(c_type, c_type)
            if target_rent_type: query['rent_type'] = target_rent_type
            
            def parse_filter_val(val):
                if val is None or str(val).strip() == "": return None
                try: return int(val)
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

        pipeline = build_match_pipeline(query, nw_norm, target_coords=selected_survey.get('target_coords'), limit=12)
        matched_properties = format_property_data(list(houses_col.aggregate(pipeline)))

        futures_recalc = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            for house in matched_properties[:3]:
                h_id = house['_id_str']
                futures_recalc[h_id] = executor.submit(generate_recommendation_reason, session['user_id'], nw_norm, house)
            
            for house in matched_properties[:3]:
                h_id = house['_id_str']
                house['ai_comment'] = futures_recalc[h_id].result()

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

@survey_bp.route('/survey/short/<int:index>')
def survey_short(index):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    surveys = list(db.survey_results.find({"user_id": session['user_id']}).sort("created_at", -1))
    if not surveys or index >= len(surveys): return redirect('/mypage')
    
    selected_survey = surveys[index]
    nw = get_user_normalized_weights(selected_survey.get('category_log', []))
    query = apply_detail_filters({}, selected_survey) 

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
    
    # 팀원 수정사항 적용: 무한 스크롤 limit 버그 수정
    pipeline = build_match_pipeline(
        query, 
        nw, 
        target_coords=selected_survey.get('target_coords'), 
        limit=1000, # 전체 후보군을 넉넉히 확보
        is_random=True
    )
    
    # 🔥 [중요] skip과 limit의 순서가 맞아야 페이징이 작동합니다.
    pipeline.extend([
        {"$skip": next_block * 12}, 
        {"$limit": 12}
    ])
    
    new_items = list(houses_col.aggregate(pipeline))
    
    # 데이터가 없으면 종료 응답
    if not new_items: 
        return jsonify({"status": "success", "items": [], "has_more": False})

    session['short_block'] = next_block
    session.modified = True
    
    return jsonify({
        "status": "success", 
        "items": format_property_data(new_items), 
        "has_more": True
    })

def generate_sandbox_lifestyle_analysis(nw_weights, top2_keys):
    weight_pct = {category_map[k]: f"{v*100:.1f}%" for k, v in nw_weights.items()}
    top_names = [category_map[k] for k in top2_keys]

    template = """
    당신은 상위 1% VIP를 전담하는 프리미엄 공간 큐레이터이자 수석 라이프스타일 애널리스트입니다.
    고객의 설문조사 결과(가중치)를 바탕으로, 기계적인 보고서가 아닌 '프라이빗 매거진' 스타일의 1:1 맞춤형 공간 큐레이션 브리핑을 작성해주세요.

    [고객 데이터]
    - 최우선 핵심 가치 2가지: {top_names}
    - 7대 지표별 세부 가중치: {weight_pct}

    [작성 가이드 및 HTML 구조]
    반드시 아래 제공된 HTML 태그 구조를 그대로 사용하여 내용만 채워주세요. (CSS 클래스가 미리 세팅되어 있습니다.)

    <div class="report-header">
        <h2 class="title">고객님의 라이프스타일 페르소나</h2>
        <p class="summary">
            </p>
    </div>

    <div class="report-body">
        <h3 class="section-title"><i class="fa-solid fa-magnifying-glass-chart"></i> 데이터로 읽어낸 3대 핵심 니즈</h3>
        
        <div class="insight-card">
            <div class="insight-header">
                <span class="badge">1순위 지표명 (예: 교통)</span>
                <span class="weight-text">00.0%</span>
            </div>
            <p class="insight-desc">
                </p>
        </div>
    </div>

    <div class="report-footer">
        <h3 class="section-title"><i class="fa-solid fa-location-dot"></i> 수석 큐레이터의 핀포인트 추천 지역</h3>
        <div class="curation-box">
            <h4 class="dong-name"></h4>
            <p class="dong-desc">
                </p>
            <ul class="dong-points">
                <li>장점 1</li>
                <li>장점 2</li>
                <li>장점 3</li>
            </ul>
        </div>
    </div>

    [말투 및 제약 조건]
    - 톤앤매너: 5성급 호텔 컨시어지나 프라이빗 뱅커(PB)처럼 극도로 정중하고, 세련되며, 신뢰감 있는 전문가의 말투를 사용하세요. (~입니다, ~하시군요)
    - 🔥 치명적 제약: 당신의 응답은 웹페이지의 HTML 안에 바로 삽입됩니다. 따라서 답변의 맨 처음과 맨 끝에 ```html, ``` 같은 마크다운 코드블럭 기호나 부연 설명을 절대 붙이지 마세요. 오직 순수한 HTML 텍스트만 출력해야 합니다.
    """
    
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "top_names": ", ".join(top_names),
            "weight_pct": str(weight_pct)
        })
        clean_html = response.content.replace("```html", "").replace("```", "").strip()
        return clean_html
    except Exception as e:
        print(f"Sandbox LLM Analysis Error: {e}")
        return "<p>라이프스타일 분석을 불러오는 중 오류가 발생했습니다.</p>"

@survey_bp.route('/survey/prompt_test/<int:index>')
def survey_prompt_sandbox(index):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    user_id = session['user_id']
    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))
    if not surveys or index >= len(surveys): return "설문 결과가 없습니다.", 404
    selected_survey = surveys[index]
    nw = get_user_normalized_weights(selected_survey.get('category_log', []))
    sorted_nw = sorted(nw.items(), key=lambda x: x[1], reverse=True)
    top2_keys = [sorted_nw[0][0], sorted_nw[1][0]]
    user_type, user_type_desc = TYPE_MAP.get(frozenset(top2_keys), ("✨ 맞춤형 라이프", "당신만의 특별한 매물을 찾고 있어요."))
    chart_keys = ['traffic', 'convenience', 'green', 'play', 'health', 'living', 'safety']
    user_chart_labels = ['교통', '편의', '녹지', '놀이', '건강', '생활', '안전']
    user_chart_data = [round(nw.get(k, 0) * 100, 1) for k in chart_keys]
    detailed_analysis = generate_sandbox_lifestyle_analysis(nw, top2_keys)
    return render_template('prompt_test.html', user_type=user_type, user_type_desc=user_type_desc, detailed_analysis=detailed_analysis, user_chart_labels=user_chart_labels, user_chart_data=user_chart_data)