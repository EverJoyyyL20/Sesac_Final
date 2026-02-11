from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from database import users_col 

# 블루프린트 설정
mypage_bp = Blueprint('mypage', __name__, template_folder='.')

# 프로필 사진 저장 경로 및 허용 확장자
UPLOAD_FOLDER = 'static/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """파일 확장자 검사 함수"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -----------------------------------------------------------
# 1. 팝업 및 세션 관리 API
# -----------------------------------------------------------
@mypage_bp.route('/disable_setup_popup', methods=['POST'])
def disable_setup_popup():
    """프로필 설정 유도 팝업을 '나중에 하기' 했을 때 세션 처리"""
    session.pop('needs_setup', None) 
    return jsonify({"success": True})

# -----------------------------------------------------------
# 2. 마이페이지 메인 (찜 목록 포함)
# -----------------------------------------------------------
@mypage_bp.route('/mypage')
def mypage():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = users_col.find_one({'email': session['user_id']})
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    # 유저 정보 및 찜 목록, 설문 데이터 추출
    # properties_col을 따로 조회하지 않고 users_col에 저장된 favorites 객체 배열을 사용함
    favorite_properties = user.get('favorites', [])
    survey_data = user.get('Survey_Details', {})

    return render_template('mypage.html', 
                            user_email=user['email'], 
                            nickname=user.get('nickname', '닉네임 없음'), 
                            bio=user.get('introduction', '소개글이 없습니다.'), 
                            profile_img=user.get('Profile_IMG', 'default.png'),
                            survey=survey_data,
                            favorites=favorite_properties)

# -----------------------------------------------------------
# 3. 프로필 수정 페이지 이동
# -----------------------------------------------------------
@mypage_bp.route('/edit', methods=['GET'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = users_col.find_one({'email': session['user_id']})
    if not user:
        return redirect(url_for('auth.login'))

    return render_template('edit_profile.html', 
                            nickname=user.get('nickname', ''), 
                            bio=user.get('introduction', ''),
                            profile_img=user.get('Profile_IMG', 'default.png'))

# -----------------------------------------------------------
# 4. 프로필 정보 업데이트 (Alert 직접 제어)
# -----------------------------------------------------------
@mypage_bp.route('/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = users_col.find_one({'email': session['user_id']})
    
    new_nickname = request.form.get('nickname', '').strip()
    new_bio = request.form.get('bio', '').strip()
    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')

    update_data = {'nickname': new_nickname, 'introduction': new_bio}

    # 비밀번호 변경 로직
    if new_pw:
        if not current_pw or not check_password_hash(user.get('PW', ''), current_pw):
            return "<script>alert('현재 비밀번호가 일치하지 않습니다.'); history.back();</script>"
        if new_pw != confirm_pw:
            return "<script>alert('새 비밀번호 확인이 일치하지 않습니다.'); history.back();</script>"
        update_data['PW'] = generate_password_hash(new_pw)

    # 닉네임 중복 체크 (본인 제외)
    if new_nickname:
        existing_user = users_col.find_one({
            'nickname': new_nickname, 
            'email': {'$ne': session['user_id']}
        })
        if existing_user:
            return "<script>alert('이미 사용 중인 닉네임입니다.'); history.back();</script>"

    # 사진 파일 업로드 처리
    file = request.files.get('profile_img')
    if file and file.filename != '' and allowed_file(file.filename):
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        user_prefix = session['user_id'].split('@')[0]
        filename = secure_filename(f"user_{user_prefix}_{file.filename}")
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        update_data['Profile_IMG'] = filename

    # DB 업데이트 및 세션 동기화
    users_col.update_one({'email': session['user_id']}, {'$set': update_data})
    session['nickname'] = new_nickname
    session.pop('needs_setup', None) # 설정 완료 시 팝업 세션 제거

    return "<script>alert('성공적으로 수정되었습니다.'); location.href='/mypage/mypage';</script>"

# -----------------------------------------------------------
# 5. 매물 찜하기 토글 (최대 10개 제한)
# -----------------------------------------------------------
@mypage_bp.route('/toggle_favorite', methods=['POST'])
def toggle_favorite():
    """매물 찾기 페이지에서 호출하는 API"""
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

    data = request.get_json()
    p_id = data.get('property_id')
    p_info = data.get('property_info') # 매물 상세 데이터 객체

    if not p_id:
        return jsonify({"success": False, "message": "매물 정보가 누락되었습니다."}), 400

    user_email = session['user_id']
    user = users_col.find_one({'email': user_email})
    favorites = user.get('favorites', [])

    # 이미 찜 목록에 있는지 ID로 확인
    is_favorited = any(f.get('id') == p_id for f in favorites)

    if is_favorited:
        # 이미 있다면 제거 (찜 취소)
        users_col.update_one({'email': user_email}, {'$pull': {'favorites': {'id': p_id}}})
        return jsonify({"success": True, "status": "removed"})
    else:
        # 새로 추가 시 10개 제한 체크
        if len(favorites) >= 10:
            return jsonify({"success": False, "message": "찜은 최대 10개까지만 가능합니다."}), 400
        
        # 찜 추가
        p_info['id'] = p_id # 객체 내에 ID 포함 확인
        users_col.update_one({'email': user_email}, {'$push': {'favorites': p_info}})
        return jsonify({"success": True, "status": "added"})

# -----------------------------------------------------------
# 6. 회원 탈퇴 (비밀번호 확인 포함)
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

    # 소셜 로그인 사용자가 아닐 경우 비밀번호 검증
    if not user.get('is_social'):
        if not password or not check_password_hash(user.get('PW', ''), password):
            return "<script>alert('비밀번호가 일치하지 않습니다.'); history.back();</script>"

    # 탈퇴 처리 (DB 삭제 및 세션 클리어)
    users_col.delete_one({'email': user_email})
    session.clear()

    return "<script>alert('탈퇴가 완료되었습니다. 이용해주셔서 감사합니다.'); location.href='/';</script>"