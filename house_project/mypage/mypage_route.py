from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from database import users_col, houses_col, db  
from bson.objectid import ObjectId

# 🔥 [핵심] 이 줄이 있어야 app.py에서 import 할 수 있습니다!
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
    user_email = session.get('user_id')
    if user_email:
        users_col.update_one({'email': user_email}, {'$set': {'is_setup_done': True}})
    
    session.pop('needs_setup', None) 
    return jsonify({"success": True})

# -----------------------------------------------------------
# 2. 마이페이지 메인
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
        if s.get('contract_type') == 'monthly':
            rent_val = s.get('budget', {}).get('max_rent', '0')
            dep_val = s.get('budget', {}).get('max_dep', '0')
            budget_text = f"보증금 {dep_val}만 / 월세 {rent_val}만"
        else:
            budget_text = f"전세 {s.get('budget', {}).get('max_dep', '0')}만원"

        building_age_list = s.get('building_age', [])
        age_info = building_age_list[0] if building_age_list else '연식미상'

        b_type_list = s.get('building_type', [])
        b_type = b_type_list[0] if b_type_list else "유형 미상"

        room_count_list = s.get('room_count', [])
        room_info = f"방 {room_count_list[0]}개" if room_count_list else "정보 없음"
        
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

    # 2. 찜 목록 데이터 가공 (이미지 안 나올 때 DB 재조회하는 안전 로직 포함)
    raw_favorites = user.get('favorites', [])
    processed_favorites = [] 

    for fav in raw_favorites:
        if isinstance(fav, (str, ObjectId)):
            continue
        if not isinstance(fav, dict):
            continue

        fav_id = fav.get('id') or fav.get('_id')
        if not fav_id: continue
        
        fav['_id_str'] = str(fav_id)

        # 가격 표시 가공
        r_type = fav.get('rent_type', '')
        p_val = fav.get('price', 0)
        d_val = fav.get('deposit', 0)

        # 가격이 숫자인지 체크
        try:
            p_val_str = str(p_val).replace(',', '')
            if p_val_str.isdigit() or isinstance(p_val, (int, float)):
                 if r_type == '전세':
                     fav['price'] = f"전세 {p_val}"
                 elif r_type == '월세':
                     fav['price'] = f"월세 {d_val}/{p_val}"
        except:
            pass
        
        # 이미지 처리 (DB user 컬렉션에 저장된 images 배열 사용)
        img_list = fav.get('images', [])
        
        # 🔥 [안전장치] 만약 저장된 이미지가 없다면 DB에서 다시 조회 (Fallback)
        if not img_list:
            try:
                rh = None
                # 숫자 ID로 재조회 (직방)
                if str(fav_id).isdigit():
                     rh = houses_col.find_one({'_id': int(fav_id)})
                # 없으면 문자/ObjectId로 재조회
                if not rh:
                    rh = houses_col.find_one({'_id': fav_id})
                if not rh:
                    rh = houses_col.find_one({'_id': ObjectId(str(fav_id))})
                
                if rh:
                    img_list = rh.get('images', [])
                    # 가격 정보도 최신화
                    if 'price' in rh: fav['price'] = rh['price']
                    if 'deposit' in rh: fav['deposit'] = rh['deposit']
                    if 'rent_type' in rh: fav['rent_type'] = rh['rent_type']
            except:
                pass

        if not isinstance(img_list, list):
            img_list = []
            
        if len(img_list) > 0 and img_list[0]:
            raw_url = str(img_list[0])
            if '?' in raw_url:
                fav['main_image'] = raw_url + '&w=800'
            else:
                fav['main_image'] = raw_url + '?w=800'
        else:
            fav['main_image'] = url_for('static', filename='img/default_room.jpg')
            
        processed_favorites.append(fav)

    return render_template('mypage.html', 
                            user_email=user['email'], 
                            nickname=user.get('nickname', '닉네임 없음'),
                            introduction=user.get('introduction', ''),
                            profile_img=user.get('Profile_IMG', 'default.png'),
                            surveys=surveys,
                            favorites=processed_favorites)

# -----------------------------------------------------------
# 3. 프로필 수정 관련
# -----------------------------------------------------------
@mypage_bp.route('/edit', methods=['GET'])
def edit_profile():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    user = users_col.find_one({'email': session['user_id']})
    if not user: return redirect(url_for('auth.login'))
    return render_template('edit_profile.html', 
                            nickname=user.get('nickname', ''), 
                            introduction=user.get('introduction', ''),
                            profile_img=user.get('Profile_IMG', 'default.png'))

@mypage_bp.route('/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    user = users_col.find_one({'email': session['user_id']})
    new_nickname = request.form.get('nickname', '').strip()
    new_introduction = request.form.get('introduction', '').strip()
    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')
    update_data = {'nickname': new_nickname, 'introduction': new_introduction}
    
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
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "message": "성공적으로 수정되었습니다."})
    return f"<script>alert('성공적으로 수정되었습니다.'); location.href='{url_for('mypage.mypage')}';</script>"

# -----------------------------------------------------------
# 4. 마이페이지 찜하기 토글 (필요 시 사용)
# -----------------------------------------------------------
@mypage_bp.route('/toggle_favorite', methods=['POST'])
def toggle_favorite():
    # 마이페이지에서 찜 해제할 때 사용하는 엔드포인트
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401

    data = request.get_json()
    p_id = data.get('property_id')

    if not p_id:
        return jsonify({"success": False, "message": "매물 정보가 누락되었습니다."}), 400

    user_email = session['user_id']
    user = users_col.find_one({'email': user_email})
    favorites = user.get('favorites', [])

    # 이미 찜했는지 확인하고 삭제 (마이페이지에서는 삭제만 주로 일어남)
    new_favorites = [f for f in favorites if str(f.get('id')) != str(p_id) and str(f.get('_id')) != str(p_id)]
    
    # 길이가 줄었다면 삭제된 것
    if len(new_favorites) < len(favorites):
        users_col.update_one({'email': user_email}, {'$set': {'favorites': new_favorites}})
        return jsonify({"success": True, "status": "removed"})
    
    return jsonify({"success": False, "status": "not_found"})

# -----------------------------------------------------------
# ５. 찜 목록 다중 삭제 (모달용)
# -----------------------------------------------------------
@mypage_bp.route('/delete_favorites', methods=['POST'])
def delete_favorites():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    user_email = session['user_id']
    data = request.get_json()
    fav_ids = data.get('ids', []) # JS에서 보낸 ["47837176", "47712503"] 형태의 리스트

    if not fav_ids:
        return jsonify({'success': False, 'message': '삭제할 항목이 선택되지 않았습니다.'}), 400

    try:
        # DB 구조상 favorites 배열 내부에 객체들이 있고, 각 객체는 'id' 필드를 가짐
        # $pull 연산자와 $in을 사용하여 선택된 모든 ID를 배열에서 한 번에 제거
        result = users_col.update_one(
            {'email': user_email},
            {'$pull': {'favorites': {'id': {'$in': fav_ids}}}}
        )

        if result.modified_count > 0:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': '삭제할 항목을 찾지 못했거나 이미 삭제되었습니다.'})

    except Exception as e:
        print(f"다중 삭제 에러: {e}")
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다.'}), 500

# -----------------------------------------------------------
# ６. 회원 탈퇴
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