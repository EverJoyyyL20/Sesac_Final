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
    client_secret=None,
    access_token_url='https://kauth.kakao.com/oauth/token',
    authorize_url='https://kauth.kakao.com/oauth/authorize',
    api_base_url='https://kapi.kakao.com/',
    client_kwargs={
        'scope': 'account_email'
    }
)

def generate_temp_nickname():
    """중복 없는 임시 닉네임 생성 (예: 새싹12345)"""
    while True:
        num = "".join(random.choices(string.digits, k=5))
        temp_nick = f"새싹{num}"
        if not users_col.find_one({'nickname': temp_nick}):
            return temp_nick

# --- [일반 회원가입] ---
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if users_col.find_one({'email': email}):
            return "<script>alert('이미 가입된 이메일입니다.'); history.back();</script>"

        temp_nickname = generate_temp_nickname()
        
        user_document = {
            'email': email,
            'PW': generate_password_hash(password),
            'nickname': temp_nickname,
            'introduction': '', 
            'Bookmark': [],
            'Profile_IMG': 'default.png',
            'Weight': {'traffic':0, 'convenience':0, 'green':0, 'play':0, 'health':0, 'living':0, 'safety':0},
            'is_social': False
        }
        users_col.insert_one(user_document)

        session.clear()
        session['user_id'] = email
        session['nickname'] = temp_nickname
        session['needs_setup'] = True  
        
        return f"<script>alert('{temp_nickname}님, 환영합니다!'); location.href='{url_for('main.index')}';</script>"
        
    return render_template('register.html')

# --- [일반 로그인] ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = users_col.find_one({'email': email})
        
        if user and user.get('PW') and check_password_hash(user['PW'], password):
            session.clear()
            session['user_id'] = user['email']
            session['nickname'] = user['nickname']
            
            # [수정된 조건문] 
            # 한줄소개가 없고 AND 팝업 닫기 기록(is_setup_done)도 없는 경우에만 팝업 생성
            if not user.get('introduction') and not user.get('is_setup_done'):
                session['needs_setup'] = True
                
            return redirect(url_for('main.index'))
        else:
            return "<script>alert('정보가 일치하지 않습니다.'); history.back();</script>"
    return render_template('login.html')

# --- [구글 로그인 시작] ---
@auth_bp.route('/login/google')
def google_login():
    # 이 redirect_uri가 구글 콘솔에 등록된 주소와 반드시 일치해야 합니다.
    # 결과: http://127.0.0.1:5000/login/google/authorize
    redirect_uri = url_for('auth.google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

# --- [구글 콜백: 구글이 인증 후 정보를 보내는 곳] ---
@auth_bp.route('/login/google/authorize')
def google_authorize():
    try:
        # 사용자가 취소를 누르면 여기서 OAuthError가 발생합니다.
        token = google.authorize_access_token()
    except Exception as e:
        # 사용자가 로그인을 취소했거나 설정 오류가 있을 경우 메인으로 돌려보냄
        print(f"구글 로그인 취소 또는 오류: {e}")
        # 오류 메시지와 함께 로그인 페이지로 리다이렉트
        return "<script>alert('로그인이 취소되었습니다.'); location.href='/login';</script>"

    # 토큰이 정상적으로 발행된 경우 (기존 로직 수행)
    # resp = google.get('userinfo')
    # resp = google.get('userinfo_endpoint')
    # 'userinfo'라는 별칭 대신 전체 URL을 직접 넣어줍니다.
    resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')
    user_info = resp.json()
    email = user_info['email']

    user = users_col.find_one({'email': email})

    if not user:
        # 신규 유저일 때만 'needs_setup' 세션을 생성합니다.
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
        session['needs_setup'] = True  # 최초 1회 팝업 트리거

    session.clear()
    session['user_id'] = user['email']
    session['nickname'] = user['nickname']
    # 기존 유저라도 소개글이 없으면 띄우고 싶다면 아래 주석 해제
    # if not user.get('introduction'): session['needs_setup'] = True
    
    # [수정된 부분] 기존 유저 로그인 시에도 체크
    # 한줄소개가 없고 AND 팝업 닫기 기록도 없는 '진짜' 초기 상태일 때만 세션 생성
    if not user.get('introduction') and not user.get('is_setup_done'):
        session['needs_setup'] = True
    
    return redirect(url_for('main.index'))

# --- 네이버 로그인 콜백함수----
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

    user = users_col.find_one({'email': email})

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
        session['needs_setup'] = True

    session.clear()
    session['user_id'] = user['email']
    session['nickname'] = user['nickname']

    if not user.get('introduction') and not user.get('is_setup_done'):
        session['needs_setup'] = True

    return redirect(url_for('main.index'))

# --- 네이버 로그인----

@auth_bp.route('/login/naver')
def naver_login():
    redirect_uri = url_for('auth.naver_callback', _external=True)
    return naver.authorize_redirect(redirect_uri)



#---- 카카오 로그인
@auth_bp.route('/login/kakao')
def kakao_login():
    redirect_url=url_for('auth.kakao_callback',_external=True)
    print("🔥 redirect_url:", url_for('auth.kakao_callback', _external=True))
    return kakao.authorize_redirect(redirect_url)


#--- 카카오 콜백 함수
@auth_bp.route('/kakao/callback')
def kakao_callback():
    try:
        # 1️⃣ access token 받기
        token = kakao.authorize_access_token()

        # 2️⃣ 사용자 정보 요청
        resp = kakao.get('v2/user/me')
        user_info = resp.json()

        # 3️⃣ 이메일 추출
        email = user_info.get('kakao_account', {}).get('email')
        print("🔥 user_info 전체:", user_info)

        if not email:
            return "이메일 정보를 가져올 수 없습니다.", 400

        session.clear()
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

        # ✅ 여기만 수정
    
        session['user_id'] = user['email']
        session['nickname'] = user.get('nickname', '카카오회원')

        return redirect(url_for('main.index'))

    except Exception as e:
        print("카카오 로그인 에러:", e)
        return "카카오 로그인 실패", 400
    
# --- [로그아웃] ---
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))