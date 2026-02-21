from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from database import houses_col, db
from bson.objectid import ObjectId
from datetime import datetime
from collections import Counter
import os
import random
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

category_map = {
    "traffic": "교통", "convenience": "편의", "green": "녹지",
    "play": "놀이", "health": "건강", "living": "생활", "safety": "안전"
}

# 라이프스타일 타입 맵핑 상수 (기존과 동일)
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
# AI 및 유틸리티 함수 (기존 로직 유지)
# ------------------------------------------------------------------
def generate_recommendation_reason(user_weights, house_info):
    sorted_weights = sorted(user_weights.items(), key=lambda x: x[1], reverse=True)
    top_interests = [f"{category_map.get(k, k)}" for k, v in sorted_weights[:2]]
    
    scores = house_info.get('scores', {})
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_strengths = []
    for k, v in sorted_scores[:2]:
        k_kor = category_map.get(k.lower(), k)
        top_strengths.append(f"{k_kor}({int(v*100)}점)")

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

def get_user_normalized_weights(category_log):
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
        h['chart_data'] = [round(scores.get(c, 0) * 100, 1) for c in ['traffic', 'convenience', 'green', 'play', 'health', 'safety']]
    return houses

def build_match_pipeline(match_query, nw, target_coords=None, limit=10, skip=0, is_random=False):
    pipeline = []

    # 1. 위치 기반 시작 (좌표가 있을 때만 $geoNear 사용)
    if target_coords and 'lng' in target_coords and 'lat' in target_coords:
        pipeline.append({
            "$geoNear": {
                "near": {
                    "type": "Point", 
                    "coordinates": [float(target_coords['lng']), float(target_coords['lat'])]
                },
                "distanceField": "distance_meters",
                "spherical": True,
                "query": match_query  # 기본 필터링(예산 등)을 geoNear 안에서 수행
            }
        })
        # 5km 이내 가산점 계산 (최대 100점)
        dist_score_expr = {
            "$divide": [
                {"$max": [0, {"$subtract": [5000, "$distance_meters"]}]}, 
                50 
            ]
        }
        # 거리가 있을 때는 라이프 70% + 거리 30% 반영
        final_score_expr = {
            "$add": [
                {"$multiply": [
                    {"$add": [{"$multiply": [{"$ifNull": [f"$category_scores.{c}", 0]}, nw[c]]} for c in nw]}, 
                    100, 0.7
                ]},
                {"$multiply": [dist_score_expr, 0.3]}
            ]
        }
    else:
        # 2. 좌표가 없을 때 (일반 매칭)
        pipeline.append({"$match": match_query})
        # 거리가 없으므로 라이프스타일 점수만 100% 반영 (이래야 80~90점이 나옵니다)
        final_score_expr = {
            "$multiply": [
                {"$add": [{"$multiply": [{"$ifNull": [f"$category_scores.{c}", 0]}, nw[c]]} for c in nw]}, 
                100
            ]
        }

    # 3. 최종 match_score 계산 및 필드 추가
    pipeline.append({
        "$addFields": {
            "match_score": {
                "$round": [final_score_expr, 1]
            }
        }
    })

    # 4. 정렬 및 샘플링 로직
    if is_random:
        # 최소 점수 70점 이상인 '괜찮은 매물'들만 제비뽑기 상자에 넣기
        pipeline.append({"$match": {"match_score": {"$gte": 70.0}}})
        
        # 상자에서 무작위로 limit(예: 12개)만큼 꺼내기
        pipeline.append({"$sample": {"size": limit}})
    else:
        pipeline.append({"$sort": {"match_score": -1}})
        pipeline.append({"$limit": limit})
        
    return pipeline

# ------------------------------------------------------------------
# 라우트 핸들러
# ------------------------------------------------------------------

@survey_bp.route('/survey')
def survey_page():
    if 'user_id' not in session:
        return "<script>alert('로그인이 필요한 서비스입니다.'); window.location.href='/login';</script>"
    client_id = current_app.config.get('NAVER_CLIENT_ID')
    # 질문 리스트 (기존과 동일)
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
    
    # 🌟 변경 포인트: 상세 희망 조건 필드들은 JS에서 빈 값으로 오거나 
    # 제외되더라도 기본값을 유지하여 DB 구조 유연성을 유지합니다.
    new_survey = {
        "user_id": user_id,
        "location": data.get('location', ""),
        "target_coords": data.get('target_coords'),
        "contract_type": data.get('contract_type', ""),
        "budget": {
            "min_dep": int(budget_raw.get('min_dep', 0) or 0),
            "max_dep": int(budget_raw.get('max_dep', 0) or 0),
            "min_rent": int(budget_raw.get('min_rent', 0) or 0),
            "max_rent": int(budget_raw.get('max_rent', 0) or 0)
        },
        # 상세 조건 생략을 위해 필드는 유지하되 검색에는 반영하지 않음
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
    nw = get_user_normalized_weights(selected_survey.get('category_log', []))
    target_coords = selected_survey.get('target_coords')

    # 사용자 유형 결정 (상단 가중치 기반)
    top2 = sorted(nw.items(), key=lambda x: x[1], reverse=True)[:2]
    top2_keys = frozenset([top2[0][0], top2[1][0]])
    user_type, user_type_desc = TYPE_MAP.get(top2_keys, ("기본형", "분석 중입니다."))

    # 🌟 변경 포인트: 상세 필터링 로직 제거 (매칭 실패 방지)
    query = {}
    
    # 1. 위치 필터 (좌표 정보가 없을 때만 주소 텍스트 기반 검색)
    if not target_coords:
        loc = selected_survey.get('location')
        if loc and loc.strip() and loc != "상관없음":
            query['address'] = {"$regex": loc}
    
    # 2. 계약 형태 및 예산 필터 (입력된 경우에만 적용)
    c_type = selected_survey.get('contract_type')
    target_rent_type = {"jeonse": "전세", "monthly": "월세"}.get(c_type, c_type)
    if target_rent_type: query['rent_type'] = target_rent_type
    
    budget = selected_survey.get('budget', {})
    if target_rent_type == "전세":
        if budget.get('max_dep', 0) > 0: 
            query['price'] = {"$gte": budget.get('min_dep', 0), "$lte": budget.get('max_dep', 0)}
    elif target_rent_type == "월세":
        if budget.get('max_dep', 0) > 0: 
            query['deposit'] = {"$gte": budget.get('min_dep', 0), "$lte": budget.get('max_dep', 0)}
        if budget.get('max_rent', 0) > 0: 
            query['price'] = {"$gte": budget.get('min_rent', 0), "$lte": budget.get('max_rent', 0)}

    # 파이프라인 빌드 및 실행 (상세 필터 제외로 결과값이 더 많이 나옴)
    pipeline = build_match_pipeline(query, nw, target_coords=target_coords, limit=50)
    matched_properties = list(houses_col.aggregate(pipeline))
    matched_properties = format_property_data(matched_properties)
    
    top_3 = matched_properties[:3]
    others = matched_properties[3:10]
    
    for house in top_3:
        house_info = {"address": house['address'], "price_display": house['price_display'], "scores": house.get('category_scores', {})}
        house['ai_comment'] = generate_recommendation_reason(nw, house_info)
    
    return render_template('result.html', survey=selected_survey, top_3=top_3, others=others, 
                           current_index=index, user_type=user_type, user_type_desc=user_type_desc,
                           total_count=len(matched_properties))

@survey_bp.route('/survey/short/<int:index>/more')
def survey_short_more(index):
    if 'user_id' not in session: return jsonify({"status": "error"}), 401
    
    # 🌟 세션에서 이미 본 매물 ID 리스트 가져오기
    seen_ids = session.get('seen_ids', [])
    
    selected_survey = db.survey_results.find_one({"user_id": session['user_id']}, sort=[("created_at", -1)])
    nw = get_user_normalized_weights(selected_survey.get('category_log', []))
    target_coords = selected_survey.get('target_coords')
    
    # 기본 쿼리에 '이미 본 매물 제외' 조건 추가
    query = {}
    if seen_ids:
        query['_id'] = {"$nin": [ObjectId(i) for i in seen_ids]}
    
    # 제비뽑기 파이프라인 실행 (limit은 10개씩)
    pipeline = build_match_pipeline(query, nw, target_coords=target_coords, limit=10, is_random=True)
    new_items = list(houses_col.aggregate(pipeline))
    
    # 🌟 새로 뽑은 ID들을 세션에 업데이트
    new_ids = [str(item['_id']) for item in new_items]
    session['seen_ids'] = seen_ids + new_ids
    session.modified = True # 세션 변경사항 강제 저장
    
    new_items = format_property_data(new_items)
    return jsonify({"status": "success", "items": new_items, "has_more": len(new_items) > 0})
@survey_bp.route('/survey/short/<int:index>')
def survey_short(index):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    selected_survey = db.survey_results.find_one({"user_id": session['user_id']}, sort=[("created_at", -1)])
    if not selected_survey: return redirect('/mypage')
    
    nw = get_user_normalized_weights(selected_survey.get('category_log', []))
    target_coords = selected_survey.get('target_coords')
    
    # 🌟 일단 주소 필터를 제거하고 테스트해 보세요 (데이터가 나오는지 확인용)
    query = {} 
    
    # 만약 좌표 변환이 필요하다면 여기서 한번 더 처리
    if target_coords:
        target_coords = {"lng": float(target_coords['lng']), "lat": float(target_coords['lat'])}

    pipeline = build_match_pipeline(query, nw, target_coords=target_coords, limit=12, is_random=True)
    recommendations = list(houses_col.aggregate(pipeline))
    
    # 🌟 첫 로드 시에도 본 매물 ID를 세션에 저장!
    session['seen_ids'] = [str(item['_id']) for item in recommendations]
    session.modified = True
    
    recommendations = format_property_data(recommendations)
    return render_template('shorts.html', recommendations=recommendations, current_index=index)