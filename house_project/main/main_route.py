from flask import Blueprint, render_template

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

@main_bp.route('/survey')
def survey():
    # 설문 시작 페이지
    return render_template('survey.html')
