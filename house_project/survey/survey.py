from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import houses_col, db
from bson.objectid import ObjectId
from datetime import datetime
from collections import Counter
import os
from dotenv import load_dotenv 
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

load_dotenv(override=True)

api_key = os.getenv("OPENAI_API_KEY")

if api_key:
    api_key = api_key.strip()
    print(f"🔑 [최종 로드된 키] 끝자리 확인: ...{api_key[-4:]}") 
else:
    print("❌ .env 파일을 찾을 수 없거나 비어있습니다!")

try:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, openai_api_key=api_key)
    print("✅ GPT 모델 초기화 성공")
except Exception as e:
    print(f"❌ GPT 초기화 실패: {e}")

# ------------------------------------------------------------------
# AI 추천 사유 생성 함수
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
    당신은 전문 부동산 컨설턴트입니다. 
    사용자의 선호도와 매물의 데이터를 분석하여, 이 집을 추천하는 이유를 **한 문장으로** 매력 있게 작성해주세요.
    
    [사용자 선호]
    - 중요 가치: {top_interests}
    
    [매물 정보]
    - 주소: {address}
    - 가격: {price}
    - 핵심 강점: {top_strengths}
    
    [작성 가이드]
    - "~하기 때문에 고객님께 딱 맞는 매물입니다" 또는 "~한 점이 매력적입니다" 같은 말투를 사용하세요.
    - 공백 포함 80자 이내로 짧게 요약하세요.
    - 너무 기계적인 말투는 피하세요.
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
    except Exception as e:
        print(f"GPT 호출 에러: {e}")
        return "데이터를 기반으로 딱 맞는 집을 찾았습니다!"

survey_bp = Blueprint('survey', __name__, template_folder='.')

category_map = {
    "traffic": "교통", "convenience": "편의", "green": "녹지",
    "play": "놀이", "health": "건강", "living": "생활", "safety": "안전"
}

@survey_bp.route('/survey')
def survey_page():
    if 'user_id' not in session:
        return "<script>alert('로그인이 필요한 서비스입니다.'); window.location.href='/login';</script>"
    
    questions = [
        {"title": "현재 나의 라이프스타일과 가장 가까운 유형은?", "multiple": False, "options": [{"text": "갓생형 (운동과 자기계발, 규칙적인 생활)", "categories": ["health", "living"]}, {"text": "인싸형 (문화생활, 모임, 활동적인 생활)", "categories": ["play", "convenience"]}, {"text": "워라밸형 (휴식, 여유, 조용한 환경)", "categories": ["green", "living"]}, {"text": "효율형 (출퇴근 시간 및 이동 효율 중시)", "categories": ["traffic", "living"]}]},
        {"title": "이사 갈 집 주변에 '꼭' 있어야 하는 시설은? (최대 3개)", "multiple": True, "max_choice": 3, "options": [{"text": "지하철/버스역", "categories": ["traffic"]}, {"text": "대형마트", "categories": ["convenience", "living"]}, {"text": "공원/산책로", "categories": ["green", "health"]}, {"text": "CCTV/파출소", "categories": ["safety"]}]},
        {"title": "주말 아침, 집 근처에서 즐기고 싶은 루틴은?", "multiple": False, "options": [{"text": "브런치 카페와 쇼핑", "categories": ["convenience", "play"]}, {"text": "조깅과 야외 운동", "categories": ["green", "health"]}, {"text": "조용한 독서와 휴식", "categories": ["living", "green"]}]},
        {"title": "퇴근 후 귀갓길에 가장 중요하게 생각하는 풍경은?", "multiple": False, "options": [{"text": "집 앞까지 이어지는 밝은 가로등", "categories": ["safety", "living"]}, {"text": "내일 먹을 장보기가 쉬운 마트", "categories": ["convenience", "living"]}, {"text": "빠르고 편리한 환승 노선", "categories": ["traffic"]}]},
        {"title": "동네를 산책할 때 가장 기분 좋은 순간은?", "multiple": False, "options": [{"text": "예쁜 상점과 팝업스토어를 구경할 때", "categories": ["play", "convenience"]}, {"text": "나무 냄새를 맡으며 흙길을 걸을 때", "categories": ["green", "health"]}, {"text": "길이 넓고 깨끗하며 위험요소가 없을 때", "categories": ["safety", "living"]}]},
        {"title": "친구들을 동네로 초대한다면 어디로 데려가고 싶나요?", "multiple": False, "options": [{"text": "유명한 맛집과 핫플레이스", "categories": ["play", "convenience"]}, {"text": "탁 트인 전망의 대형 공원", "categories": ["green", "play"]}, {"text": "주차가 편하고 교통이 좋은 곳", "categories": ["traffic", "convenience"]}, {"text": "조용하고 분위기 좋은 카페/도서관", "categories": ["living", "safety"]}]},
        {"title": "이사 후 동네를 탐방할 때 가장 먼저 찾아볼 장소는?", "multiple": False, "options": [{"text": "대형 마트 위치", "categories": ["convenience", "living"]}, {"text": "안심하고 다닐 수 있는 치안센터/경찰서", "categories": ["safety"]}, {"text": "지하철역까지 가는 지름길", "categories": ["traffic"]}]},
        {"title": "몸이 조금 아플 때, 나는 보통 어떻게 하나요?", "multiple": False, "options": [{"text": "바로 집 근처 병원·한의원에 가서 진료를 받는다", "categories": ["health", "convenience"]}, {"text": "집에서 푹 쉬면서 휴식으로 회복하려 한다", "categories": ["safety", "living"]}, {"text": "가볍게 산책하거나공원·자연 속에서 몸을 푼다", "categories": ["health", "green"]}, {"text": "카페·도서관처럼 조용한 공간에서 혼자 시간을 보낸다", "categories": ["living"]}]},
        {"title": "이런 곳은 정말 피하고 싶어요!", "multiple": False, "options": [{"text": "경찰서/치안센터가 너무 먼 곳", "categories": ["safety"]}, {"text": "가로등이 없고 지하철역까지 너무 어두운 곳", "categories": ["safety", "traffic"]}, {"text": "편의점 하나 없는 황량한 곳", "categories": ["convenience", "safety"]}]},
        {"title": "집 근처 5분 거리에 상점 하나가 새로 들어온다면?", "multiple": False, "options": [{"text": "24시 대형 식자재 마트", "categories": ["convenience", "living"]}, {"text": "코인 노래방이나 영화관", "categories": ["play"]}, {"text": "늦게까지 운영하는 종합 검진 센터와 한의원", "categories": ["health", "safety"]}]}
    ]
    return render_template('survey.html', questions=questions)

@survey_bp.route('/survey/save', methods=['POST'])
def save_survey():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "로그인이 필요한 서비스입니다."}), 401

    user_id = session['user_id']
    data = request.get_json() 
    if not data:
        return jsonify({"status": "error", "message": "전송된 데이터가 없습니다."}), 400

    budget_raw = data.get('budget', {})
    
    # 🔥 [수정] 프론트에서 받은 상세 조건(연식, 방개수 등) 5가지를 DB에 저장
    new_survey = {
        "user_id": user_id,
        "location": data.get('location', ""),
        "contract_type": data.get('contract_type', ""),
        "budget": {
            "min_dep": int(budget_raw.get('min_dep', 0)),
            "max_dep": int(budget_raw.get('max_dep', 0)),
            "min_rent": int(budget_raw.get('min_rent', 0)),
            "max_rent": int(budget_raw.get('max_rent', 0))
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

@survey_bp.route('/survey/result/<int:index>')
def survey_result(index):
    if 'user_id' not in session:
        return "<script>alert('로그인이 필요한 서비스입니다.'); window.location.href='/login';</script>"
    
    user_id = session['user_id']
    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))
    
    if not surveys or index >= len(surveys):
        return f"<script>alert('해당 설문 내역이 없습니다.'); window.location.href='/mypage';</script>"

    selected_survey = surveys[index]
    
    total_counts = {
        'traffic': 6, 'convenience': 10, 'green': 7, 
        'play': 6, 'health': 6, 'living': 13, 'safety': 10
    }
    
    user_log = selected_survey.get('category_log', [])
    log_counts = Counter(user_log)
    
    raw_weights = {}
    for cat, total in total_counts.items():
        raw_weights[cat] = (log_counts.get(cat, 0) + 1) / total

    sum_raw_weights = sum(raw_weights.values())
    user_weights = {k: v / sum_raw_weights for k, v in raw_weights.items()}

    top2 = sorted(user_weights.items(), key=lambda x: x[1], reverse=True)[:2]
    top2_keys = frozenset([top2[0][0], top2[1][0]])

    user_type_data = TYPE_MAP.get(top2_keys, ("기본형", "라이프스타일을 분석 중입니다."))
    user_type = user_type_data[0]
    user_type_desc = user_type_data[1]

    query = {}
    loc = selected_survey.get('location')
    if loc and loc.strip():
        query['address'] = {"$regex": loc}
    
    c_type = selected_survey.get('contract_type')
    mapping = {"jeonse": "전세", "monthly": "월세"}
    if c_type:
        query['rent_type'] = mapping.get(c_type, c_type)
    
    budget_data = selected_survey.get('budget', {})
    min_dep = budget_data.get('min_dep', 0)
    max_dep = budget_data.get('max_dep', 0)
    min_rent = budget_data.get('min_rent', 0)
    max_rent = budget_data.get('max_rent', 0)
    
    target_rent_type = mapping.get(c_type, c_type) 

    if target_rent_type == "전세":
        price_q = {}
        if min_dep > 0: price_q["$gte"] = min_dep
        if max_dep > 0: price_q["$lte"] = max_dep
        if price_q:
            query['price'] = price_q

    else:
        dep_q = {}
        if min_dep > 0: dep_q["$gte"] = min_dep
        if max_dep > 0: dep_q["$lte"] = max_dep
        if dep_q:
            query['deposit'] = dep_q

        rent_q = {}
        if min_rent > 0: rent_q["$gte"] = min_rent
        if max_rent > 0: rent_q["$lte"] = max_rent
        if rent_q:
            query['price'] = rent_q

    filtered_houses = list(houses_col.find(query).limit(500))

    ##### [AI 검증 로그 추가] #####
    print("\n" + "="*60)
    print(f"📂 [STEP 1] DB 조회 쿼리: {query}")
    
    total_count = len(filtered_houses)
    print(f"📊 [STEP 2] 1차 검색 결과: {total_count}개")
    
    suggested_count = 0
    if total_count == 0:
        # 가격 필터만 40% 높여서 다시 카운트하는 로직 확인
        relaxed_query = query.copy()
        if target_rent_type == "전세":
            if max_dep > 0:
                relaxed_query['price'] = {"$gte": min_dep, "$lte": int(max_dep * 1.4)}
        else:
            # 월세는 보증금 20% 완화와 월세 40% 완화하여 검색 범위를 넓힘
            if max_dep > 0:
                relaxed_query['deposit'] = {"$gte": min_dep, "$lte": int(max_dep * 1.2)}
            if max_rent > 0:
                relaxed_query['price'] = {"$gte": min_rent, "$lte": int(max_rent * 1.4)}

        print(f"💸 [STEP 3] 예산 40% 완화 쿼리: {relaxed_query}")
        suggested_count = houses_col.count_documents(relaxed_query)
        print(f"📊 [STEP 4] 완화 시 예상 결과: {suggested_count}개")
    
    # 만약 결과가 0인데 STEP 4도 0이라면, 예산 문제가 아니라 지역/방개수/건물유형 중 하나가 때문.
    print("="*60 + "\n")
    ##### [AI 검증 로그 끝] #####

    ##### [AI 수정] 결과 개수 및 예산 완화 카운팅 로직 추가 #####

    # 결과가 너무 적을 때 기존에 있던 위치 기반 완화 검색 로직 (유지)
    if len(filtered_houses) < 5:
        relaxed_query_base = {}
        if loc and loc.strip(): relaxed_query_base['address'] = {"$regex": loc}
        if c_type: relaxed_query_base['rent_type'] = mapping.get(c_type, c_type)
        filtered_houses = list(houses_col.find(relaxed_query_base).limit(100))

    matched_properties = []
    for house in filtered_houses:
        infra_scores = house.get('category_scores', {})
        final_score_raw = sum(infra_scores.get(cat, 0) * user_weights.get(cat, 0) for cat in total_counts.keys())
        
        house['match_score'] = round(final_score_raw * 100, 1)
        house['_id_str'] = str(house['_id'])
        
        rent_type = house.get('rent_type')
        main_price = house.get('price', 0) 
        
        if rent_type == '전세':
            house['price_display'] = f"{main_price}"
        else:
            dep_amount = house.get('deposit', 0)
            house['price_display'] = f"{dep_amount}/{main_price}"
        
        house['sort_key'] = main_price

        img_list = house.get('images', [])
        if not isinstance(img_list, list):
            img_list = []
            
        if len(img_list) > 0 and img_list[0]:
            raw_url = img_list[0]
            if '?' in raw_url:
                house['main_image'] = raw_url + '&w=800'
            else:
                house['main_image'] = raw_url + '?w=800'
        else:
            house['main_image'] = url_for('static', filename='img/default_room.jpg')

        matched_properties.append(house)

    matched_properties = sorted(
        matched_properties, 
        key=lambda x: (-x['match_score'], x['sort_key'])
    )[:10]

    top_3 = matched_properties[:3]
    others = matched_properties[3:]
    
    print("🤖 GPT-4o-mini 분석 시작...")
    
    for house in top_3:
        try:
            house_info = {
                "address": house['address'],
                "price_display": house['price_display'],
                "scores": house.get('category_scores', {}) 
            }
            ai_comment = generate_recommendation_reason(user_weights, house_info)
            house['ai_comment'] = ai_comment
            
        except Exception as e:
            print(f"❌ 매물 ID {house.get('_id')} AI 분석 실패: {e}")
            house['ai_comment'] = "고객님의 라이프스타일에 최적화된 추천 매물입니다."

    print("✅ 분석 완료")
    
    
    return render_template(
        'result.html', 
        survey=selected_survey, 
        top_3=top_3, 
        others=others, 
        current_index=index, 
        survey_id=str(selected_survey['_id']),
        user_type=user_type,
        user_type_desc=user_type_desc,
        ##### [AI 수정] 템플릿에 데이터 추가 #####
        total_count=total_count,
        suggested_count=suggested_count
        ##### [AI 수정 끝] #####
    )

# 다른 조건은 동일, 지역만 전체 지역으로 바꿈
@survey_bp.route('/survey/result/<string:survey_id>/expand')
def expand_region(survey_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    # 1. 전달받은 survey_id를 사용해 즉시 지역 정보만 비움
    # index 변수를 거치지 않고 직접 DB의 해당 문서를 수정합니다.
    db.survey_results.update_one(
        {"_id": ObjectId(survey_id)},
        {"$set": {"location": ""}}
    )
    
    # 2. 업데이트가 완료되면 이 데이터가 해당 사용자의 가장 최신 설문이 됩니다.
    # 따라서 결과 페이지의 0번 인덱스(최신순 정렬 결과)로 리다이렉트합니다.
    return redirect(url_for('survey.survey_result', index=0))