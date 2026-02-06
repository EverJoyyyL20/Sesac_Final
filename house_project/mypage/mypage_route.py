from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from database import users_col 

mypage_bp = Blueprint('mypage', __name__, template_folder='.')

# 프로필 사진 저장 경로 설정
UPLOAD_FOLDER = 'static/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -----------------------------------------------------------
# 1. 팝업 관련 API
# -----------------------------------------------------------
@mypage_bp.route('/disable_setup_popup', methods=['POST'])
def disable_setup_popup():
    """사용자가 프로필 설정 팝업에서 '나중에 하기'를 눌렀을 때 세션 제거"""
    session.pop('needs_setup', None) 
    return jsonify({"success": True})

# -----------------------------------------------------------
# 2. 마이페이지 메인 화면
# -----------------------------------------------------------
@mypage_bp.route('/mypage')
def mypage():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = users_col.find_one({'email': session['user_id']})
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    return render_template('mypage.html', 
                           user_email=user['email'], 
                           nickname=user.get('nickname', '닉네임 없음'), 
                           bio=user.get('introduction', '소개글이 없습니다.'), 
                           profile_img=user.get('Profile_IMG', 'default.png'))

# -----------------------------------------------------------
# 3. 프로필 수정 페이지 이동 (누락되었던 함수)
# -----------------------------------------------------------
@mypage_bp.route('/edit', methods=['GET'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = users_col.find_one({'email': session['user_id']})
    if not user:
        return redirect(url_for('auth.login'))

    # 수정 페이지 렌더링
    return render_template('edit_profile.html', 
                           nickname=user.get('nickname', ''), 
                           bio=user.get('introduction', ''),
                           profile_img=user.get('Profile_IMG', 'default.png'))

# -----------------------------------------------------------
# 4. 프로필 정보 업데이트 (팝업 및 수정 페이지 공용)
# -----------------------------------------------------------
@mypage_bp.route('/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": "세션이 만료되었습니다."}), 401
        return redirect(url_for('auth.login'))

    # HTML의 name="nickname"과 name="bio" 값을 가져옴
    new_nickname = request.form.get('nickname', '').strip()
    new_bio = request.form.get('bio', '').strip()

    # 닉네임 중복 체크 (본인 제외)
    if new_nickname:
        existing_user = users_col.find_one({
            'nickname': new_nickname, 
            'email': {'$ne': session['user_id']}
        })
        if existing_user:
            # 비동기 요청일 경우 JSON 응답
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "message": "이미 사용 중인 닉네임입니다."})
            # 일반 폼 전송일 경우 알림창 후 뒤로가기
            return "<script>alert('이미 사용 중인 닉네임입니다.'); history.back();</script>"

    update_data = {
        'nickname': new_nickname,
        'introduction': new_bio
    }

    # 파일 업로드 처리
    file = request.files.get('profile_img')
    if file and file.filename != '' and allowed_file(file.filename):
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        # 파일명 안전하게 생성 (이메일 앞부분 포함)
        user_prefix = session['user_id'].split('@')[0]
        filename = secure_filename(f"user_{user_prefix}_{file.filename}")
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        update_data['Profile_IMG'] = filename

    # MongoDB 업데이트
    users_col.update_one({'email': session['user_id']}, {'$set': update_data})
    
    # 세션 정보 갱신 및 팝업 플래그 제거
    session['nickname'] = new_nickname
    session.pop('needs_setup', None) 

    # ★ 비동기(fetch) 요청인 경우 JSON 응답 (팝업창 해결용)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({"success": True})
    
    # 일반 폼 전송일 경우(edit_profile.html) 마이페이지로 이동
    return redirect(url_for('mypage.mypage'))

# -----------------------------------------------------------
# 5. 회원 탈퇴 관련
# -----------------------------------------------------------
@mypage_bp.route('/delete_confirm')
def delete_confirm():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('delete_confirm.html')

@mypage_bp.route('/delete_user', methods=['POST'])
def delete_user():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_email = session['user_id']
    password = request.form.get('password')
    confirm_check = request.form.get('confirm_check')

    user = users_col.find_one({'email': user_email})

    if confirm_check != 'agreed':
        return "<script>alert('주의사항 동의 체크가 필요합니다.'); history.back();</script>"

    if not user.get('is_social'):
        if not password or not check_password_hash(user['PW'], password):
            return "<script>alert('비밀번호가 일치하지 않습니다.'); history.back();</script>"

    users_col.delete_one({'email': user_email})
    session.clear()

    return "<script>alert('탈퇴가 완료되었습니다. 이용해주셔서 감사합니다.'); location.href='/';</script>"