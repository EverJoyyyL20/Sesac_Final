from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from database import users_col, db  # db 객체 추가 (survey_results 접근용)
from bson.objectid import ObjectId

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
    session.pop('needs_setup', None) 
    return jsonify({"success": True})

# -----------------------------------------------------------
# 2. 마이페이지 메인 (수정본)
# -----------------------------------------------------------
@mypage_bp.route('/mypage')
def mypage():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_email = session['user_id']
    user = users_col.find_one({'email': user_email})
    
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    # 1. 설문 데이터 가져오기 및 가공
    raw_surveys = list(db.survey_results.find({"user_id": user_email}).sort("created_at", -1))
    surveys = []
    
    for s in raw_surveys:
        # [수정] 월세일 경우 보증금이 무조건 앞으로 오도록 설정
        if s.get('contract_type') == 'monthly':
            rent_val = s.get('budget', {}).get('max_rent', '0')
            dep_val = s.get('budget', {}).get('max_dep', '0')
            budget_text = f"보증금 {dep_val}만 / 월세 {rent_val}만"
        else:
            budget_text = f"전세 {s.get('budget', {}).get('max_dep', '0')}만원"

        # 건물/방 정보 요약
        building_age_list = s.get('building_age', [])
        age_info = building_age_list[0] if building_age_list else '연식미상'

        b_type_list = s.get('building_type', [])
        b_type = b_type_list[0] if b_type_list else "유형 미상"

        room_count_list = s.get('room_count', [])
        room_info = f"방 {room_count_list[0]}개" if room_count_list else "정보 없음"
        
        # 특수 조건 태그화
        option_tags = []
        if s.get('special_room') == 'yes': option_tags.append("옥탑/반지하 포함")
        if s.get('parking') == 'yes': option_tags.append("주차 가능")
        if s.get('parking') == 'no': option_tags.append("주차 불가")

        summary = {
            '_id': str(s['_id']),
            'date': s.get('updated_at').strftime('%y.%m.%d') if s.get('updated_at') else '날짜미상',
            'location': s.get('location') if s.get('location') else "전체 지역",
            'main_info': f"{age_info} · {b_type} · {room_info}",
            'budget': budget_text,
            'tags': option_tags
        }
        surveys.append(summary)

    # 2. 찜 목록 데이터 가공
    favorite_properties = user.get('favorites', [])
    for fav in favorite_properties:
        pid = fav.get('id') or fav.get('_id')
        fav['_id_str'] = str(pid)

        # [수정] 찜한 매물 가격 표시도 "보증금/월세" 순으로 재배치
        original_price = fav.get('price', '')
        if '월세' in original_price and '/' in original_price:
            try:
                # "월세 50/500" -> "50/500" 분리 후 [50, 500] -> "500/50"
                price_part = original_price.replace('월세', '').strip()
                p_split = price_part.split('/')
                if len(p_split) == 2:
                    fav['price'] = f"월세 {p_split[1].strip()}/{p_split[0].strip()}"
            except:
                pass

        if 'images' not in fav or not fav['images']:
            fav['images'] = [fav.get('image_url')] if fav.get('image_url') else []

    return render_template('mypage.html', 
                            user_email=user['email'], 
                            nickname=user.get('nickname', '닉네임 없음'),
                            introduction=user.get('introduction', ''), # 한줄 소개 데이터 넘겨줌
                            profile_img=user.get('Profile_IMG', 'default.png'),
                            surveys=surveys,
                            favorites=favorite_properties)

# -----------------------------------------------------------
# 3. 프로필 수정 관련 (기존 유지)
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
    if new_pw:
        if not current_pw or not check_password_hash(user.get('PW', ''), current_pw):
            return "<script>alert('현재 비밀번호가 일치하지 않습니다.'); history.back();</script>"
        if new_pw != confirm_pw:
            return "<script>alert('새 비밀번호 확인이 일치하지 않습니다.'); history.back();</script>"
        update_data['PW'] = generate_password_hash(new_pw)
    if new_nickname:
        existing_user = users_col.find_one({'nickname': new_nickname, 'email': {'$ne': session['user_id']}})
        if existing_user:
            return "<script>alert('이미 사용 중인 닉네임입니다.'); history.back();</script>"
    file = request.files.get('profile_img')
    if file and file.filename != '' and allowed_file(file.filename):
        if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
        user_prefix = session['user_id'].split('@')[0]
        filename = secure_filename(f"user_{user_prefix}_{file.filename}")
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        update_data['Profile_IMG'] = filename
    users_col.update_one({'email': session['user_id']}, {'$set': update_data})
    session['nickname'] = new_nickname
    # url_for를 사용하여 'mypage' 블루프린트의 'mypage' 함수 주소를 동적으로 가져옴.
    target_url = url_for('mypage.mypage') 
    return f"<script>alert('성공적으로 수정되었습니다.'); location.href='{target_url}';</script>"

# -----------------------------------------------------------
# 4. 매물 찜하기 토글 (개수 제한 제거 버전)
# -----------------------------------------------------------
@mypage_bp.route('/toggle_favorite', methods=['POST'])
def toggle_favorite():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

    data = request.get_json()
    p_id = data.get('property_id')
    p_info = data.get('property_info') 

    if not p_id:
        return jsonify({"success": False, "message": "매물 정보가 누락되었습니다."}), 400

    user_email = session['user_id']
    user = users_col.find_one({'email': user_email})
    favorites = user.get('favorites', [])

    is_favorited = any(f.get('id') == p_id for f in favorites)

    if is_favorited:
        users_col.update_one({'email': user_email}, {'$pull': {'favorites': {'id': p_id}}})
        return jsonify({"success": True, "status": "removed"})
    else:
        # [수정] 개수 제한(10개) 로직 삭제
        p_info['id'] = p_id
        if 'images' not in p_info and 'image_url' in p_info:
            p_info['images'] = [p_info['image_url']]
            
        users_col.update_one({'email': user_email}, {'$push': {'favorites': p_info}})
        return jsonify({"success": True, "status": "added"})

# -----------------------------------------------------------
# 5. 회원 탈퇴 (기존 유지)
# -----------------------------------------------------------
@mypage_bp.route('/delete_confirm')
def delete_confirm():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    return render_template('delete_confirm.html')

@mypage_bp.route('/delete_user', methods=['POST'])
def delete_user():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    user_email = session['user_id']
    password = request.form.get('password')
    confirm_check = request.form.get('confirm_check')
    user = users_col.find_one({'email': user_email})
    if confirm_check != 'agreed':
        return "<script>alert('주의사항 동의 체크가 필요합니다.'); history.back();</script>"
    if not user.get('is_social'):
        if not password or not check_password_hash(user.get('PW', ''), password):
            return "<script>alert('비밀번호가 일치하지 않습니다.'); history.back();</script>"
    users_col.delete_one({'email': user_email})
    session.clear()
    return "<script>alert('탈퇴가 완료되었습니다. 이용해주셔서 감사합니다.'); location.href='/';</script>"