import os
import random
import string
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from database import users_col, oauth  # database.py에서 가져옴
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

auth_bp = Blueprint('auth', __name__, template_folder='.')

# ==========================================
# 1. OAuth 설정
# ==========================================
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

# 🔥 [복구 완료 1] 중복 없는 '새싹' 임시 닉네임 생성 로직
def generate_temp_nickname():
    """중복 없는 임시 닉네임 생성 (예: 새싹12345)"""
    while True:
        num = "".join(random.choices(string.digits, k=5))
        temp_nick = f"새싹{num}"
        if not users_col.find_one({'nickname': temp_nick}):
            return temp_nick


# ==========================================
# 2. 일반 회원가입 & 로그인
# ==========================================
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # 🔥 [복구 완료 2] 경고창(Alert) 응답 복구
        if users_col.find_one({'email': email}):
            return "<script>alert('이미 가입된 이메일입니다.'); history.back();</script>"
            
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

        # 바로 로그인 처리
        session.clear()
        session.permanent = True
        session['user_id'] = email
        session['nickname'] = temp_nickname
        session['is_social'] = False
        session['needs_setup'] = True
        
        # ⭐️ 프로필 이미지 세션 연동
        session['profile_img_name'] = 'default.png' 

        return f"<script>alert('{temp_nickname}님, 환영합니다!'); location.href='{url_for('main.index')}';</script>"

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = users_col.find_one({'email': email})

        if user and user.get('PW') and check_password_hash(user['PW'], password):
            session.clear()
            session.permanent = True 
            session['user_id'] = user['email']
            session['nickname'] = user.get('nickname', user['email'].split('@')[0])
            session['is_social'] = user.get('is_social', False)
            
            # ⭐️ 프로필 이미지 세션 연동
            session['profile_img_name'] = user.get('Profile_IMG', 'default.png')

            # 한줄소개가 없고 AND 팝업 닫기 기록(is_setup_done)도 없는 경우에만 팝업 생성
            if not user.get('introduction') and not user.get('is_setup_done'):
                session['needs_setup'] = True
                
            return redirect(url_for('main.index'))
        else:
            return "<script>alert('정보가 일치하지 않습니다.'); history.back();</script>"
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))


# ==========================================
# 3. Google OAuth 
# ==========================================
@auth_bp.route('/login/google')
def google_login():
    redirect_uri = url_for('auth.google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

# 🔥 [복구 완료 3] 구글 로그인 취소 시 에러 방지(Try-Except) 및 authorize 라우트 복구
@auth_bp.route('/login/google/authorize')
def google_authorize():
    try:
        # 사용자가 취소를 누르면 여기서 OAuthError가 발생합니다.
        token = google.authorize_access_token()
    except Exception as e:
        print(f"구글 로그인 취소 또는 오류: {e}")
        return "<script>alert('로그인이 취소되었습니다.'); location.href='/login';</script>"

    resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')
    user_info = resp.json()
    email = user_info['email']

    user = users_col.find_one({'email': email})
    
    if not user:
        temp_nickname = generate_temp_nickname()
        user_document = {
            'email': email,
            'PW': None,
            'nickname': temp_nickname,
            'introduction': '',
            'Bookmark': [],
            'Profile_IMG': user_info.get('picture', 'default.png'),
            'Weight': {'traffic':0, 'convenience':0, 'green':0, 'play':0, 'health':0, 'living':0, 'safety':0},
            'is_social': True
        }
        users_col.insert_one(user_document)
        user = user_document

    session.clear()
    session.permanent = True
    session['user_id'] = user['email']
    session['nickname'] = user.get('nickname', user['email'].split('@')[0])
    session['is_social'] = True
    
    # ⭐️ 프로필 이미지 세션 연동
    session['profile_img_name'] = user.get('Profile_IMG', 'default.png')

    if not user.get('introduction') and not user.get('is_setup_done'):
        session['needs_setup'] = True

    return redirect(url_for('main.index'))


# ==========================================
# 4. Naver OAuth 
# ==========================================
@auth_bp.route('/login/naver')
def naver_login():
    redirect_uri = url_for('auth.naver_callback', _external=True)
    return naver.authorize_redirect(redirect_uri)

@auth_bp.route('/login/naver/callback')
def naver_callback():
    try:
        token = naver.authorize_access_token()
    except Exception as e:
        print(f"네이버 로그인 오류: {e}")
        return "<script>alert('로그인이 취소되었습니다.'); location.href='/login';</script>"

    resp = naver.get('v1/nid/me')
    user_info = resp.json()

    naver_account = user_info.get("response", {})
    email = naver_account.get("email")

    if not email:
        return "<script>alert('이메일 제공에 동의해야 로그인 가능합니다.'); location.href='/login';</script>"

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
            'Profile_IMG': naver_account.get('profile_image', 'default.png'),
            'Weight': {'traffic':0, 'convenience':0, 'green':0, 'play':0, 'health':0, 'living':0, 'safety':0},
            'is_social': True
        }
        users_col.insert_one(user_document)
        user = user_document

    session['user_id'] = user['email']
    session['nickname'] = user.get('nickname', user['email'].split('@')[0])
    session['is_social'] = True
    
    # ⭐️ 프로필 이미지 세션 연동
    session['profile_img_name'] = user.get('Profile_IMG', 'default.png')

    if not user.get('introduction') and not user.get('is_setup_done'):
        session['needs_setup'] = True
        
    return redirect(url_for('main.index'))


# ==========================================
# 5. Kakao OAuth 
# ==========================================
@auth_bp.route('/login/kakao')
def kakao_login():
    redirect_url = url_for('auth.kakao_callback', _external=True)
    return kakao.authorize_redirect(redirect_url)

# 🔥 [복구 완료 4] 카카오 Try-Except 구문 복구
@auth_bp.route('/login/kakao/callback')
def kakao_callback():
    try:
        # 1️⃣ access token 받기
        token = kakao.authorize_access_token()
        if not token:
            return "카카오 로그인 실패", 400

        # 2️⃣ 사용자 정보 요청
        resp = kakao.get('v2/user/me')
        user_info = resp.json()

        # 3️⃣ 이메일 추출
        email = user_info.get('kakao_account', {}).get('email')

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
            
        session['user_id'] = user['email']
        session['nickname'] = user.get('nickname', '카카오회원')
        session['is_social'] = True
        
        # ⭐️ 프로필 이미지 세션 연동
        session['profile_img_name'] = user.get('Profile_IMG', 'default.png')

        if not user.get('introduction') and not user.get('is_setup_done'):
            session['needs_setup'] = True

        return redirect(url_for('main.index'))

    except Exception as e:
        print("카카오 로그인 에러:", e)
        return "카카오 로그인 실패", 400