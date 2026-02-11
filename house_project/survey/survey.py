from flask import Blueprint, render_template, request, jsonify, session
from database import houses_col, db  # db 객체와 매물 컬렉션 임포트
from bson.objectid import ObjectId
from datetime import datetime

survey_bp = Blueprint('survey', __name__,template_folder='.')

# 카테고리 영문-한글 매핑 테이블
category_map = {
    "traffic": "교통",
    "convenience": "편의",
    "green": "녹지",
    "play": "놀이",
    "health": "건강",
    "living": "생활",
    "safety": "안전"
}

@survey_bp.route('/survey')
def survey_page():
    # 앞서 정의한 10개의 질문 리스트 (생략, 기존 질문 데이터 그대로 유지)
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
    try:
        data = request.json
        
        # 1. 사용자 가중치 분석 (이미 잘 나오고 있음)
        raw_log = data.get('category_log', [])
        temp_weights = {"traffic": 0, "convenience": 0, "green": 0, "play": 0, "health": 0, "living": 0, "safety": 0}
        
        total_selections = 0
        for cats in raw_log:
            for cat_en in cats:
                if cat_en in temp_weights:
                    temp_weights[cat_en] += 1
                    total_selections += 1

        user_weights_en = {k: (v / total_selections if total_selections > 0 else 0) for k, v in temp_weights.items()}

        # 2. 매물 필터링
        rent_type_ko = "월세" if data.get('contract_type') == 'monthly' else "전세"
        query = {"rent_type": rent_type_ko}
        # (예산 필터가 필요하다면 여기에 추가)

        filtered_houses = list(houses_col.find(query))

        # 3. 스코어링 (DB의 영문 키와 직접 매칭)
        for prop in filtered_houses:
            final_score = 0
            scores = prop.get('category_scores', {})
            
            for cat_en, user_weight in user_weights_en.items():
                if user_weight > 0:
                    item_score = float(scores.get(cat_en, 0))
                    # 가중치를 조금 더 '강력하게' 반영 (예: 제곱근 등을 활용하거나 보정치 부여)
                    final_score += item_score * user_weight

            # [보정 공식] 
            # 단순히 100을 곱하는 대신, 최상단 점수가 90점대에 육박하도록 보정치를 더합니다.
            # 예: (실제 점수 * 80) + 20  -> 최하점을 20점으로 끌어올리고 범위를 조절
            adjusted_score = (final_score * 70) + 30 
            
            # 만약 특정 매물의 점수가 너무 낮다면 최소 50점은 나오게 하고 싶을 때:
            # adjusted_score = max(50, (final_score * 100))

            prop['match_score'] = round(adjusted_score, 1)
            prop['_id'] = str(prop['_id'])

        # 점수 정렬
        filtered_houses.sort(key=lambda x: x['match_score'], reverse=True)
        recommendations = filtered_houses[:20]

        # 4. DB 저장 및 결과 반환
        result_doc = {
            "nickname": session.get('nickname', '익명'),
            "recommendations": recommendations,
            "created_at": datetime.now()
        }
        inserted_result = db.survey_results.insert_one(result_doc)
        
        return jsonify({"status": "success", "result_id": str(inserted_result.inserted_id)})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@survey_bp.route('/survey/result/<result_id>')
def survey_result(result_id):
    # DB에서 해당 ID의 분석 결과를 로드
    try:
        result_data = db.survey_results.find_one({"_id": ObjectId(result_id)})
        
        if not result_data:
            return "결과를 찾을 수 없습니다.", 404
            
        recommendations = result_data.get('recommendations', [])
        
        return render_template('result.html', 
                               top_3=recommendations[:3], 
                               others=recommendations[3:],
                               result_id=result_id)
    except:
        return "잘못된 접근입니다.", 400

@survey_bp.route('/survey/shorts/<result_id>')
def result_shorts(result_id):
    # 쇼츠 페이지도 동일한 ID로 DB에서 데이터 로드
    result_data = db.survey_results.find_one({"_id": ObjectId(result_id)})
    
    if not result_data:
        return "데이터를 찾을 수 없습니다.", 404
        
    return render_template('shorts.html', 
                           recommendations=result_data.get('recommendations', []))