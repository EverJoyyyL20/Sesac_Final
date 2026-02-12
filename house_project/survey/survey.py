from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import houses_col, db  # db 객체와 매물 컬렉션 임포트
from bson.objectid import ObjectId
from datetime import datetime

# Blueprint 설정
survey_bp = Blueprint('survey', __name__, template_folder='.')

# 카테고리 매핑 테이블
category_map = {
    "traffic": "교통", "convenience": "편의", "green": "녹지",
    "play": "놀이", "health": "건강", "living": "생활", "safety": "안전"
}

@survey_bp.route('/survey')
def survey_page():
    # 질문 데이터 (기존 유지)
    questions = [
        {
            "title": "현재 나의 라이프스타일과 가장 가까운 유형은?",
            "multiple": False,
            "options": [
                {"text": "갓생형 (운동과 자기계발, 규칙적인 생활)", "categories": ["health", "living"]},
                {"text": "인싸형 (문화생활, 모임, 활동적인 생활)", "categories": ["play", "convenience"]},
                {"text": "워라밸형 (휴식, 여유, 조용한 환경)", "categories": ["green", "living"]},
                {"text": "효율형 (출퇴근 시간 및 이동 효율 중시)", "categories": ["traffic", "living"]}
            ]
        },
        {
            "title": "이사 갈 집 주변에 '꼭' 있어야 하는 시설은? (최대 3개)",
            "multiple": True,
            "max_choice": 3,
            "options": [
                {"text": "지하철/버스역", "categories": ["traffic"]},
                {"text": "대형마트", "categories": ["convenience", "living"]},
                {"text": "공원/산책로", "categories": ["green", "health"]},
                {"text": "CCTV/파출소", "categories": ["safety"]}
            ]
        },
        {
            "title": "주말 아침, 집 근처에서 즐기고 싶은 루틴은?",
            "multiple": False,
            "options": [
                {"text": "브런치 카페와 쇼핑", "categories": ["convenience", "play"]},
                {"text": "조깅과 야외 운동", "categories": ["green", "health"]},
                {"text": "조용한 독서와 휴식", "categories": ["living", "green"]}
            ]
        },
        {
            "title": "퇴근 후 귀갓길에 가장 중요하게 생각하는 풍경은?",
            "multiple": False,
            "options": [
                {"text": "집 앞까지 이어지는 밝은 가로등", "categories": ["safety", "living"]},
                {"text": "내일 먹을 장보기가 쉬운 마트", "categories": ["convenience", "living"]},
                {"text": "빠르고 편리한 환승 노선", "categories": ["traffic"]}
            ]
        },
        {
            "title": "동네를 산책할 때 가장 기분 좋은 순간은?",
            "multiple": False,
            "options": [
                {"text": "예쁜 상점과 팝업스토어를 구경할 때", "categories": ["play", "convenience"]},
                {"text": "나무 냄새를 맡으며 흙길을 걸을 때", "categories": ["green", "health"]},
                {"text": "길이 넓고 깨끗하며 위험요소가 없을 때", "categories": ["safety", "living"]}
            ]
        },
        {
            "title": "친구들을 동네로 초대한다면 어디로 데려가고 싶나요?",
            "multiple": False,
            "options": [
                {"text": "유명한 맛집과 핫플레이스", "categories": ["play", "convenience"]},
                {"text": "탁 트인 전망의 대형 공원", "categories": ["green", "play"]},
                {"text": "주차가 편하고 교통이 좋은 곳", "categories": ["traffic", "convenience"]},
                {"text": "조용하고 분위기 좋은 카페/도서관", "categories": ["living", "safety"]}
            ]
        },
        {
            "title": "이사 후 동네를 탐방할 때 가장 먼저 찾아볼 장소는?",
            "multiple": False,
            "options": [
                {"text": "대형 마트 위치", "categories": ["convenience", "living"]},
                {"text": "안심하고 다닐 수 있는 치안센터/경찰서", "categories": ["safety"]},
                {"text": "지하철역까지 가는 지름길", "categories": ["traffic"]}
            ]
        },
        {
            "title": "몸이 조금 아플 때, 나는 보통 어떻게 하나요?",
            "multiple": False,
            "options": [
                {"text": "바로 집 근처 병원·한의원에 가서 진료를 받는다", "categories": ["health", "convenience"]},
                {"text": "집에서 푹 쉬면서 휴식으로 회복하려 한다", "categories": ["safety", "living"]},
                {"text": "가볍게 산책하거나 공원·자연 속에서 몸을 푼다", "categories": ["health", "green"]},
                {"text": "카페·도서관처럼 조용한 공간에서 혼자 시간을 보낸다", "categories": ["living"]}
            ]
        },
        {
            "title": "이런 곳은 정말 피하고 싶어요!",
            "multiple": False,
            "options": [
                {"text": "경찰서/치안센터가 너무 먼 곳", "categories": ["safety"]},
                {"text": "가로등이 없고 지하철역까지 너무 어두운 곳", "categories": ["safety", "traffic"]},
                {"text": "편의점 하나 없는 황량한 곳", "categories": ["convenience", "safety"]}
            ]
        },
        {
            "title": "집 근처 5분 거리에 상점 하나가 새로 들어온다면?",
            "multiple": False,
            "options": [
                {"text": "24시 대형 식자재 마트", "categories": ["convenience", "living"]},
                {"text": "코인 노래방이나 영화관", "categories": ["play"]},
                {"text": "늦게까지 운영하는 종합 검진 센터와 한의원", "categories": ["health", "safety"]}
            ]
        }
    ]
    return render_template('survey.html', questions=questions)

@survey_bp.route('/survey/save', methods=['POST'])
def save_survey():
    if 'user_id' not in session:
        # JSON으로 에러 응답
        return jsonify({"status": "error", "message": "로그인이 필요한 서비스입니다."}), 401

    user_id = session['user_id']
    
    # 폼 데이터가 아닌 JSON 데이터 수집
    data = request.get_json() 
    if not data:
        return jsonify({"status": "error", "message": "전송된 데이터가 없습니다."}), 400

    # 프론트엔드 surveyResults 구조에 맞게 매핑
    new_survey = {
        "user_id": user_id,
        "location": data.get('location'),
        "contract_type": data.get('contract_type'),
        "budget": data.get('budget'), # max_dep, max_rent 포함됨
        "category_log": data.get('category_log'),
        "created_at": datetime.now()
    }

    # 1. 기존 설문 목록 확인 (최신순)
    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))

    # 2. FIFO 로직
    if len(surveys) >= 3:
        oldest_id = surveys[-1]['_id']
        db.survey_results.delete_one({"_id": oldest_id})

    # 3. 새로운 설문 저장
    db.survey_results.insert_one(new_survey)
    
    # 4. JSON으로 성공 응답 전송 (JS가 이걸 받고 redirect를 수행함)
    return jsonify({"status": "success", "target_index": 0})

@survey_bp.route('/survey/result/<int:index>')
def survey_result(index):
    if 'user_id' not in session:
        return "<script>alert('로그인이 필요한 서비스입니다.'); window.location.href='/login';</script>"
    
    user_id = session['user_id']
    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))
    
    if not surveys or index >= len(surveys):
        return f"<script>alert('해당 설문 내역이 없습니다.'); window.location.href='/mypage';</script>"

    selected_survey = surveys[index]
    
    # 설문에서 얻은 카테고리 가중치 (예: ['traffic', 'green', 'safety'])
    user_categories = selected_survey.get('category_log', [])
    
    # 1. 기본적인 필터링 쿼리 (예: 예산, 계약 방식 등 적용 가능)
    query = {}
    if selected_survey.get('location'):
        query['address'] = {"$regex": selected_survey['location']}
    
    # 2. 매물 가져오기
    all_houses = list(houses_col.find(query).limit(20)) # 넉넉히 가져와서 점수 계산
    
    matched_properties = []
    for house in all_houses:
        # --- [중요] 이미지 배열 처리 확인 ---
        # DB에 images 필드가 없거나 비어있을 경우 빈 배열로 세팅
        if 'images' not in house or not house['images']:
            house['images'] = []
            
        # --- 매칭 점수 계산 로직 (간단한 예시) ---
        score = 70.0  # 기본 점수
        # 매물 데이터에 있는 시설 카테고리와 유저 카테고리 비교
        # 예: house['categories'] = ['traffic', 'convenience']
        house_categories = house.get('categories', [])
        match_count = len(set(user_categories) & set(house_categories))
        score += (match_count * 10) # 겹치는 카테고리당 10점 추가
        
        house['match_score'] = min(score, 99.9) # 최대 99.9점
        house['_id_str'] = str(house['_id'])
        matched_properties.append(house)

    # 3. 점수 높은 순 정렬 및 상위 10개 추출
    matched_properties = sorted(matched_properties, key=lambda x: x['match_score'], reverse=True)[:10]

    # 4. 데이터 분리 (TOP 3와 나머지)
    top_3 = matched_properties[:3]
    others = matched_properties[3:]

    return render_template('result.html', 
                           survey=selected_survey, 
                           top_3=top_3, 
                           others=others, 
                           current_index=index,
                           survey_id=str(selected_survey['_id']))

@survey_bp.route('/survey/shorts/<int:index>')
def result_shorts(index):
    if 'user_id' not in session:
        return "<script>alert('로그인이 필요합니다.'); window.location.href='/login';</script>"
    
    user_id = session['user_id']
    surveys = list(db.survey_results.find({"user_id": user_id}).sort("created_at", -1))
    
    if not surveys or index >= len(surveys):
        return "<script>alert('데이터를 찾을 수 없습니다.'); window.location.href='/mypage';</script>"
        
    result_data = surveys[index]
    
    return render_template('shorts.html', 
                           recommendations=result_data.get('recommendations', []),
                           current_index=index)