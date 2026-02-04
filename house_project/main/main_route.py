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
        "title": "이사 갈 집 주변에 '꼭' 있어야 하는 시설은? (최대 3개)",
        "multiple": True,
        "max_choice": 3, # 여기에 제한 숫자를 적습니다.
        "options": [
            {"text": "지하철/버스역", "categories": ["traffic"]},
            {"text": "대형마트", "categories": ["convenience"]},
            {"text": "공원/산책로", "categories": ["green"]},
            {"text": "CCTV/파출소", "categories": ["safety"]},
            {"text": "종합병원", "categories": ["health"]},
            {"text": "도서관", "categories": ["living"]}
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