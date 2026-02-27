import os
import random
import string
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from database import users_col, oauth  # database.py에서 가져옴
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

auth_bp = Blueprint('auth', __name__, template_folder='.')

# 1. OAuth 설정 (Google)
# app.py가 아닌 여기서 register를 수행하여 블루프린트 내에서 google 객체를 바로 사용합니다.
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=None,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

naver = oauth.register(
    name='naver',
    client_id=os.getenv("NAVER_CLIENT_LID"),
    client_secret=os.getenv("NAVER_CLIENT_LSECRET"),
    access_token_url='https://nid.naver.com/oauth2.0/token',
    authorize_url='https://nid.naver.com/oauth2.0/authorize',
    api_base_url='https://openapi.naver.com/',
    client_kwargs={'scope': 'email profile'},
)

kakao = oauth.register(
    name='kakao',
    client_id=os.getenv("KAKAO_REST_API"),
    client_secret=os.getenv("KAKAO_CLIENT_SECRET"),
    access_token_url='https://kauth.kakao.com/oauth/token',
    authorize_url='https://kauth.kakao.com/oauth/authorize',
    api_base_url='https://kapi.kakao.com/',
    client_kwargs={'scope': 'profile_nickname account_email'},
)

def generate_temp_nickname(length=8):
    """랜덤 영문/숫자 조합 닉네임 생성"""
    characters = string.ascii_letters + string.digits
    return "user_" + "".join(random.choice(characters) for _ in range(length))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if users_col.find_one({'email': email}):
            return "이미 존재하는 이메일입니다.", 400
            
        hashed_pw = generate_password_hash(password)
        temp_nickname = generate_temp_nickname()
        
        user_document = {
            'email': email,
            'PW': hashed_pw,
            'nickname': temp_nickname,
            'introduction': '',
            'Bookmark': [],
            'Profile_IMG': 'default.png',
            'Weight': {'traffic':0, 'convenience':0, 'green':0, 'play':0, 'health':0, 'living':0, 'safety':0},
            'is_social': False,
            'created_at': datetime.datetime.now()
        }
        users_col.insert_one(user_document)
        
        # 바로 로그인 처리 & 초기 설정 플래그
        session.clear()
        session.permanent = True
        session['user_id'] = email
        session['nickname'] = temp_nickname
        session['is_social'] = False
        session['needs_setup'] = True
        session['profile_img_name'] = 'default.png' # 🔥 프로필 이미지 세션 저장 추가
        
        return redirect(url_for('main.index'))
        
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = users_col.find_one({'email': email})
        
        if user and check_password_hash(user['PW'], password):
            session.clear()
            session.permanent = True
            session['user_id'] = user['email']
            session['nickname'] = user.get('nickname', user['email'].split('@')[0])
            session['is_social'] = user.get('is_social', False)
            session['profile_img_name'] = user.get('Profile_IMG', 'default.png') # 🔥 프로필 이미지 세션 저장 추가
            
            return redirect(url_for('main.index'))
        else:
            return "<script>alert('정보가 일치하지 않습니다.'); history.back();</script>"
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

# ==========================================
# Google OAuth 
# ==========================================
@auth_bp.route('/login/google')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@auth_bp.route('/login/google/callback')
def google_callback():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    
    email = user_info.get('email')
    
    session.clear()
    session.permanent = True
    user = users_col.find_one({"email": email})
    
    if not user:
        temp_nickname = generate_temp_nickname()
        user_document = {
            'email': email,
            'PW': None,
            'nickname': temp_nickname,
            'introduction': '',
            'Bookmark': [],
            'Profile_IMG': 'default.png',
            'Weight': {'traffic':0, 'convenience':0, 'green':0, 'play':0, 'health':0, 'living':0, 'safety':0},
            'is_social': True
        }
        users_col.insert_one(user_document)
        user = user_document
        session['needs_setup'] = True
        
    session['user_id'] = user['email']
    session['nickname'] = user.get('nickname', user['email'].split('@')[0])
    session['is_social'] = True
    session['profile_img_name'] = user.get('Profile_IMG', 'default.png') # 🔥 프로필 이미지 세션 저장 추가
    
    return redirect(url_for('main.index'))

# ==========================================
# Naver OAuth 
# ==========================================
@auth_bp.route('/login/naver')
def naver_login():
    redirect_uri = url_for('auth.naver_callback', _external=True)
    return naver.authorize_redirect(redirect_uri)

@auth_bp.route('/login/naver/callback')
def naver_callback():
    token = naver.authorize_access_token()
    resp = naver.get('v1/nid/me')
    user_info = resp.json().get('response')
    
    email = user_info.get('email')
    
    session.clear()
    session.permanent = True
    user = users_col.find_one({"email": email})
    
    if not user:
        temp_nickname = generate_temp_nickname()
        user_document = {
            'email': email,
            'PW': None,
            'nickname': temp_nickname,
            'introduction': '',
            'Bookmark': [],
            'Profile_IMG': 'default.png',
            'Weight': {'traffic':0, 'convenience':0, 'green':0, 'play':0, 'health':0, 'living':0, 'safety':0},
            'is_social': True
        }
        users_col.insert_one(user_document)
        user = user_document
        session['needs_setup'] = True
        
    session['user_id'] = user['email']
    session['nickname'] = user.get('nickname', user['email'].split('@')[0])
    session['is_social'] = True
    session['profile_img_name'] = user.get('Profile_IMG', 'default.png') # 🔥 프로필 이미지 세션 저장 추가
    
    return redirect(url_for('main.index'))

# ==========================================
# Kakao OAuth 
# ==========================================
@auth_bp.route('/login/kakao')
def kakao_login():
    redirect_uri = url_for('auth.kakao_callback', _external=True)
    return kakao.authorize_redirect(redirect_uri)

@auth_bp.route('/login/kakao/callback')
def kakao_callback():
    # 1️⃣ 토큰 받기
    token = kakao.authorize_access_token()
    if not token:
        return "카카오 로그인 실패", 400

    # 2️⃣ 사용자 정보 요청
    resp = kakao.get('v2/user/me')
    user_info = resp.json()

    # 3️⃣ 이메일 추출
    email = user_info.get('kakao_account', {}).get('email')
    print("🔥 user_info 전체:", user_info)

    if not email:
        return "이메일 정보를 가져올 수 없습니다.", 400

    session.clear()
    session.permanent = True
    # 4️⃣ MongoDB에서 사용자 확인
    user = users_col.find_one({"email": email})

    if not user:
        temp_nickname = generate_temp_nickname()
        user_document = {
            'email': email,
            'PW': None,
            'nickname': temp_nickname,
            'introduction': '',
            'Bookmark': [],
            'Profile_IMG': 'default.png',
            'Weight': {'traffic':0, 'convenience':0, 'green':0, 'play':0, 'health':0, 'living':0, 'safety':0},
            'is_social': True
        }
        users_col.insert_one(user_document)
        user = user_document
        session['needs_setup'] = True
    else:
        print("기존 회원 로그인")

    # ✅ 세션 저장 
    session['user_id'] = user['email']
    session['nickname'] = user.get('nickname', '카카오회원')
    session['is_social'] = True
    session['profile_img_name'] = user.get('Profile_IMG', 'default.png') # 🔥 프로필 이미지 세션 저장 추가

    return redirect(url_for('main.index'))