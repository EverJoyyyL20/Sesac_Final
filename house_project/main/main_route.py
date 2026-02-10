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
@main_bp.route('/survey/save', methods=['POST'])
def save_survey():
    if 'user_id' not in session:
        return jsonify({"status": "fail", "message": "Session expired"}), 401

    data = request.get_json()
    
    # --- 1. 가중치(Category) 계산 로직 수정됨 ---
    
    # (1) 설문지 내 각 카테고리의 총 등장 횟수 (사전 정의된 값)
    category_frequency = {
        'traffic': 6,      # 교통
        'convenience': 10, # 편의
        'green': 7,        # 녹지
        'play': 6,         # 놀이
        'health': 6,       # 건강
        'living': 13,      # 생활
        'safety': 10       # 안전
    }

    # (2) 유저 선택 횟수 카운트 (초기화)
    user_selections = {key: 0 for key in category_frequency.keys()}
    
    category_log = data.get('category_log', []) 
    for cats in category_log:
        for c in cats:
            if c in user_selections:
                user_selections[c] += 1

    # (3) 빈도 보정 및 점수 계산 (Laplace Smoothing: 기본값 +1)
    # 공식: (유저 선택 횟수 + 1) / 총 등장 횟수
    # 이렇게 하면 한 번도 선택 안 된 항목도 0이 아닌 최소한의 점수를 가짐
    raw_scores = {}
    for cat, total_appearance in category_frequency.items():
        # 기본값 1을 더해줌
        adjusted_count = user_selections[cat] + 1
        # 등장 빈도로 나누어 밸런싱
        raw_scores[cat] = adjusted_count / total_appearance

    # (4) 정규화 (합계가 1이 되도록 변환)
    total_score_sum = sum(raw_scores.values())
    
    # 합계가 0일 수는 없지만(기본값 1 때문에), 안전하게 처리
    if total_score_sum > 0:
        final_weights = {k: round(v / total_score_sum, 4) for k, v in raw_scores.items()}
    else:
        # 이론상 도달할 수 없으나 예외 처리
        final_weights = {k: 0.1428 for k in category_frequency.keys()}

    # --- 2. 상세 조건(Details) 및 지역/예산 데이터 정리 ---
    details = data.get('details', {})
    location = data.get('location', '')
    budget = data.get('budget', {})
    contract_type = data.get('contract_type', '')

    # --- 3. DB 업데이트 ---
    try:
        users_col.update_one(
            {'email': session['user_id']},
            {
                '$set': {
                    'Weight': final_weights,  # 계산된 최종 가중치
                    'Survey_Details': {       
                        'location': location,
                        'contract_type': contract_type,
                        'budget': budget,
                        'building_type': details.get('b_type', []),
                        'building_age': details.get('build_age', []),
                        'room_count': details.get('room_count', []),
                        'special_room': details.get('special_room', ''),
                        'parking': details.get('parking', ''),
                        'updated_at': datetime.now()
                    }
                }
            }
        )
        return jsonify({"status": "success", "result": final_weights})
    except Exception as e:
        print(f"DB 저장 오류: {e}")
        return jsonify({"status": "error", "message": "데이터 저장 실패"}), 500