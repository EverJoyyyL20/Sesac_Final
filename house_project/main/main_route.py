from flask import Blueprint, render_template, session, request, jsonify

# 'main'이라는 이름의 블루프린트 생성
main_bp = Blueprint('main', __name__, template_folder='.')

@main_bp.route('/')
def index():
    # 중앙에 설문 시작 버튼이 있는 메인 페이지
    return render_template('main.html')

@main_bp.route('/find-property')
def find_property():
    # 매물찾기 로직 (추후 주택임대차 보호법 관련 필터링 추가 가능)
    return render_template('find_property.html')


def calculate_final_scores(selected_categories_list):
    """
    selected_categories_list: [['traffic'], ['convenience', 'living'], ['green', 'health']]
    """
    # 1. 모든 항목 0으로 초기화
    counts = {
        'traffic': 0, 'convenience': 0, 'green': 0, 
        'play': 0, 'health': 0, 'living': 0, 'safety': 0
    }
    
    # 2. 선택된 카테고리 횟수 누적
    for categories in selected_categories_list:
        for cat in categories:
            if cat in counts:
                counts[cat] += 1
    
    # 3. 전체 선택 횟수 합계
    total_count = sum(counts.values())
    
    # 4. 정규화 (합계가 1이 되도록 계산)
    # 만약 아무것도 선택 안 했을 경우 대비(ZeroDivisionError 방지)
    if total_count == 0:
        return {k: 1/len(counts) for k in counts.keys()} # 균등 배분
        
    final_scores = {k: v / total_count for k, v in counts.items()}
    
    return final_scores

@main_bp.route('/survey')
def survey():
    # 1. 로그인 여부 확인
    if 'user_id' not in session:
        # 알림창을 띄우고 로그인 페이지로 이동시키는 스크립트 리턴
        return "<script>alert('로그인이 필요한 서비스입니다.'); location.href='/login';</script>"

    # 2. 로그인되어 있으면 설문 데이터 준비
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

@main_bp.route('/survey/save', methods=['POST'])
def save_survey():
    data = request.get_json()
    category_log = data.get('category_log') # 예: [['traffic'], ['convenience', 'living'], ...]

    # 1. 카테고리별 카운트 초기화
    counts = {
        'traffic': 0, 'convenience': 0, 'green': 0, 
        'play': 0, 'health': 0, 'living': 0, 'safety': 0
    }

    # 2. 횟수 누적
    for cats in category_log:
        for c in cats:
            if c in counts:
                counts[c] += 1

    # 3. 정규화 (전체 합을 1로 만들기)
    total_hits = sum(counts.values())
    if total_hits > 0:
        final_weights = {k: round(v / total_hits, 4) for k, v in counts.items()}
    else:
        final_weights = {k: 0.0 for k in counts.keys()}

    # 4. DB 저장 (예시: current_user.preference 에 저장)
    print("최종 계산된 가중치:", final_weights)
    # user_pref = SurveyPreference.query.filter_by(user_id=session['user_id']).first()
    # ... update 로직 ...

    return jsonify({"status": "success", "result": final_weights})