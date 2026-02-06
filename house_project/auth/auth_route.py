import random
import string
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from database import users_col
from werkzeug.security import generate_password_hash, check_password_hash


auth_bp = Blueprint('auth', __name__, template_folder='.')

def generate_temp_nickname():
    """중복 없는 임시 닉네임 생성 (예: 새싹12345)"""
    while True:
        num = "".join(random.choices(string.digits, k=5))
        temp_nick = f"새싹{num}"
        if not users_col.find_one({'nickname': temp_nick}):
            return temp_nick

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # 이메일 중복 체크
        if users_col.find_one({'email': email}):
            return "<script>alert('이미 가입된 이메일입니다.'); history.back();</script>"

        # 1. 임시 닉네임 생성
        temp_nickname = generate_temp_nickname()
        
        # 2. 유저 데이터 생성
        user_document = {
            'email': email,
            'PW': generate_password_hash(password),
            'nickname': temp_nickname,
            'introduction': '', # 소개글은 비워둠
            'Bookmark': [],
            'Profile_IMG': 'default.png',
            'Weight': {'traffic':0, 'convenience':0, 'green':0, 'play':0, 'health':0, 'living':0, 'safety':0}
        }
        users_col.insert_one(user_document)

        # 3. ★ 자동 로그인 처리 ★
        session.clear() # 기존 세션 초기화
        session['user_id'] = email
        session['nickname'] = temp_nickname
        session['needs_setup'] = True  # 메인 화면 팝업 트리거
        
        return f"<script>alert('{temp_nickname}님, 환영합니다!'); location.href='{url_for('main.index')}';</script>"
        
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = users_col.find_one({'email': email})
        
        if user and check_password_hash(user['PW'], password):
            session.clear()
            session['user_id'] = user['email']
            session['nickname'] = user['nickname']
            # 기존에 소개글이 없었다면 다시 띄워줄 수도 있습니다 (선택 사항)
            if not user.get('introduction'):
                session['needs_setup'] = True
            return redirect(url_for('main.index'))
        else:
            return "<script>alert('정보가 일치하지 않습니다.'); history.back();</script>"
    return render_template('login.html')

@auth_bp.route('/update_profile_fast', methods=['POST'])
def update_profile_fast():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "로그인 세션 만료"}), 401
    
    new_nick = request.form.get('nickname', '').strip()
    intro = request.form.get('introduction', '').strip()

    # 본인 제외 닉네임 중복 체크
    if users_col.find_one({'nickname': new_nick, 'email': {'$ne': session['user_id']}}):
        return jsonify({"success": False, "message": "이미 사용 중인 닉네임입니다."})

    users_col.update_one(
        {'email': session['user_id']},
        {'$set': {'nickname': new_nick, 'introduction': intro}}
    )
    
    session['nickname'] = new_nick
    session.pop('needs_setup', None)
    return jsonify({"success": True})

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))