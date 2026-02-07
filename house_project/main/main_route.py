from flask import Blueprint, render_template, session, request, jsonify, redirect, url_for
from database import users_col  # 이전에 만든 database.py에서 가져옴
import random
import string
from datetime import datetime

main_bp = Blueprint('main', __name__, template_folder='.')


@main_bp.route('/')
def index():
    return render_template('main.html')

@main_bp.route('/survey')
def survey():
    if 'user_id' not in session:
        # 스크립트 대신 플라스크 표준 방식으로 리다이렉트 권장
        return "<script>alert('로그인이 필요한 서비스입니다.'); location.href='/login';</script>"

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
\
@main_bp.route('/disable_setup_popup', methods=['POST'])
def disable_setup_popup():
    session.pop('needs_setup', None)  # 세션에서 팝업 트리거 삭제
    return jsonify({"success": True})

@main_bp.route('/survey/save', methods=['POST'])
def save_survey():
    if 'user_id' not in session:
        return jsonify({"status": "fail", "message": "Session expired"}), 401

    data = request.get_json()
    
    # --- 1. 가중치(Category) 계산 로직 ---
    category_log = data.get('category_log', []) 
    counts = {
        'traffic': 0, 'convenience': 0, 'green': 0, 
        'play': 0, 'health': 0, 'living': 0, 'safety': 0
    }

    for cats in category_log:
        for c in cats:
            if c in counts:
                counts[c] += 1

    total_hits = sum(counts.values())
    if total_hits > 0:
        final_weights = {k: round(v / total_hits, 4) for k, v in counts.items()}
    else:
        final_weights = {k: 0.1428 for k in counts.keys()}

    # --- 2. 상세 조건(Details) 및 지역/예산 데이터 정리 ---
    # HTML에서 보낸 'details' 객체를 그대로 가져옵니다.
    details = data.get('details', {})
    location = data.get('location', '')
    budget = data.get('budget', {})
    contract_type = data.get('contract_type', '')

    # --- 3. DB 업데이트 (하나의 필드에 묶어서 저장) ---
    try:
        users_col.update_one(
            {'email': session['user_id']},
            {
                '$set': {
                    'Weight': final_weights,  # 기존 가중치 필드
                    'Survey_Details': {       # 질문하신 건물 유형, 연식 등 상세 데이터
                        'location': location,
                        'contract_type': contract_type,
                        'budget': budget,
                        'building_type': details.get('b_type', []),
                        'building_age': details.get('build_age', []),
                        'room_count': details.get('room_count', []),
                        'special_room': details.get('special_room', ''),
                        'parking': details.get('parking', ''),
                        'updated_at': datetime.now() # 상단에 from datetime import datetime 필요
                    }
                }
            }
        )
        return jsonify({"status": "success", "result": final_weights})
    except Exception as e:
        print(f"DB 저장 오류: {e}")
        return jsonify({"status": "error", "message": "데이터 저장 실패"}), 500