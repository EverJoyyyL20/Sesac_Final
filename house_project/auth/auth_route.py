import os
import random
import string
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from database import users_col, oauth  # database.py에서 가져옴
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from urllib.parse import urlparse, urljoin, parse_qs # URL 안전성 검사 함수 추가, URL 파라미터 파싱을 위한 parse_qs 추가

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
    token_endpoint_auth_method='client_secret_post',
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

        return redirect(url_for('main.index'))

    return render_template('register.html')

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

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

            # --- auth.py 로그인 성공 로직 내부 ---
            next_url = request.args.get('next')

            if next_url and is_safe_url(next_url):
                # 1. URL 파라미터 파싱
                parsed_url = urlparse(next_url)
                params = parse_qs(parsed_url.query)
                
                # 2. 자동 찜 요청 확인 및 DB 반영
                if params.get('action') == ['wish'] and params.get('wish_id'):
                    wish_id = params.get('wish_id')[0]
                    
                    # 유저 DB의 favorites 리스트에 추가 (형식 주의: {'id': wish_id})
                    users_col.update_one(
                        {'email': session['user_id']},
                        {'$addToSet': {'favorites': {'id': wish_id}}}
                    )
                
                # 3. 찜 처리가 끝난 후 next_url(마이페이지)로 이동
                return redirect(next_url)

            return redirect(url_for('main.index'))
            # --- 자동 찜하기 및 리다이렉트 로직 끝 ---

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
        token = google.authorize_access_token()
    except Exception as e:
        print(f"구글 로그인 취소 또는 오류: {e}")
        return "<script>alert('로그인이 취소되었습니다.'); location.href='/login';</script>"

    resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')
    user_info = resp.json()
    email = user_info['email']
    google_picture = user_info.get('picture', 'default.png')  # ⭐️ 구글 프로필 이미지 URL 추출

    user = users_col.find_one({'email': email})
    
    if not user:
        temp_nickname = generate_temp_nickname()
        user_document = {
            'email': email,
            'PW': None,
            'nickname': temp_nickname,
            'introduction': '',
            'Bookmark': [],
            'Profile_IMG': google_picture,  # ⭐️ 구글 프로필 이미지 URL 저장
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
    
    # ⭐️ 신규 가입이면 구글 이미지, 기존 유저면 저장된 이미지 사용
    session['profile_img_name'] = user.get('Profile_IMG', google_picture)

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

        # 3️⃣ 데이터 추출 (이메일 및 카카오 프로필 이미지)
        kakao_account = user_info.get('kakao_account', {})
        email = kakao_account.get('email')
        profile = kakao_account.get('profile', {})
        # 카카오톡 프로필 이미지 URL 가져오기
        print(f"DEBUG - 카카오 계정 정보: {kakao_account}")
        print(f"DEBUG - 프로필 정보: {profile}")
        kakao_profile_img = profile.get('profile_image_url') or profile.get('thumbnail_image_url') or 'default.png'

        if not email:
            return "이메일 정보를 가져올 수 없습니다.", 400

        session.clear()
        session.permanent = True
        
        # 4️⃣ MongoDB에서 사용자 확인
        user = users_col.find_one({"email": email})

        if not user:
            # 신규 회원가입 시 카카오 프로필 이미지를 저장
            temp_nickname = generate_temp_nickname()
            user_document = {
                'email': email,
                'PW': None,
                'nickname': temp_nickname,
                'introduction': '',
                'Bookmark': [],
                'Profile_IMG': kakao_profile_img if kakao_profile_img else 'default.png',
                'Weight': {'traffic':0, 'convenience':0, 'green':0, 'play':0, 'health':0, 'living':0, 'safety':0},
                'is_social': True
            }
            users_col.insert_one(user_document)
            user = user_document
        else:
            # 기존 회원인데 프로필 이미지가 없는 경우 업데이트 (선택 사항)
            if not user.get('Profile_IMG') or user.get('Profile_IMG') == 'default.png':
                if kakao_profile_img:
                    users_col.update_one({"email": email}, {"$set": {"Profile_IMG": kakao_profile_img}})
                    user['Profile_IMG'] = kakao_profile_img
            
        # 5️⃣ 세션 저장
        session['user_id'] = user['email']
        session['nickname'] = user.get('nickname', '카카오회원')
        session['is_social'] = True
        
        # 프로필 이미지 URL 또는 파일명을 세션에 연동
        session['profile_img_name'] = user.get('Profile_IMG', 'default.png')

        if not user.get('introduction') and not user.get('is_setup_done'):
            session['needs_setup'] = True

        return redirect(url_for('main.index'))

    except Exception as e:
        print("카카오 로그인 에러:", e)
        return "카카오 로그인 실패", 400