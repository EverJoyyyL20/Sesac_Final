from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from database import users_col 

mypage_bp = Blueprint('mypage', __name__, template_folder='.')

UPLOAD_FOLDER = 'static/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -----------------------------------------------------------
# [추가] 팝업 닫기 버튼 클릭 시 세션 제거 API
# -----------------------------------------------------------
@mypage_bp.route('/disable_setup_popup', methods=['POST'])
def disable_setup_popup():
    # 사용자가 '나중에 하기'를 눌렀을 때 호출됨
    session.pop('needs_setup', None) 
    return jsonify({"success": True})

# 1. 마이페이지 메인
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

# 2. 프로필 수정 페이지 이동
@mypage_bp.route('/edit', methods=['GET'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = users_col.find_one({'email': session['user_id']})
    if not user:
        return redirect(url_for('auth.login'))

    return render_template('edit_profile.html', 
                           nickname=user.get('nickname', ''), 
                           bio=user.get('introduction', ''))

# 3. 프로필 정보 업데이트 (닉네임 중복 체크 포함)
@mypage_bp.route('/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": "세션이 만료되었습니다."}), 401
        return redirect(url_for('auth.login'))

    new_nickname = request.form.get('nickname', '').strip()
    new_bio = request.form.get('introduction') or request.form.get('bio') or ""

    if new_nickname:
        existing_user = users_col.find_one({
            'nickname': new_nickname, 
            'email': {'$ne': session['user_id']}
        })
        if existing_user:
            return jsonify({"success": False, "message": "이미 사용 중인 닉네임입니다."})

    update_data = {
        'nickname': new_nickname,
        'introduction': new_bio
    }

    file = request.files.get('profile_img')
    if file and file.filename != '' and allowed_file(file.filename):
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        filename = secure_filename(f"user_{session['user_id']}_{file.filename}")
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        update_data['Profile_IMG'] = filename

    # DB 업데이트
    users_col.update_one({'email': session['user_id']}, {'$set': update_data})
    
    # 세션 갱신 및 팝업 트리거 제거
    session['nickname'] = new_nickname
    session.pop('needs_setup', None) # [중요] 업데이트 성공 시 팝업 세션 제거

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True})
    
    return redirect(url_for('mypage.mypage'))

# 4. 회원 탈퇴 확인 페이지
@mypage_bp.route('/delete_confirm')
def delete_confirm():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('delete_confirm.html')

# 5. 실제 회원 탈퇴 처리
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