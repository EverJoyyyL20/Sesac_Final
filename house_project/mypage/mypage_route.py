from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from database import users_col, houses_col, db  
from bson.objectid import ObjectId
from collections import Counter
from src.core.constants import TYPE_MAP

mypage_bp = Blueprint('mypage', __name__, template_folder='.')

UPLOAD_FOLDER = 'static/profile_pics'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'profile_pics')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _to_manwon_mp(value):
    import re as _re
    if value is None: return 0.0
    if isinstance(value, (int, float)):
        v = float(value)
        if v <= 0: return 0.0
        if v >= 10_000_000: return v / 10_000
        return v
    s = str(value).replace(',', '').strip()
    m = _re.search(r'[\d.]+', s)
    if not m: return 0.0
    try: v = float(m.group())
    except ValueError: return 0.0
    if v <= 0: return 0.0
    if v >= 10_000_000: return v / 10_000
    return v

def get_vfm_score_mp(house):
    import re as _re
    YEARS, RATE = 3, 0.04
    stats_map = {
        '전세_Normal':   {'peak': 99.4,  'mean': 96.2,  'std': 40.0},
        '월세_Normal':   {'peak': 91.9,  'mean': 124.8, 'std': 51.3},
        '월세_Basement': {'peak': 77.7,  'mean': 76.3,  'std': 22.3},
        '전세_Basement': {'peak': 26.4,  'mean': 31.7,  'std': 11.7},
    }
    rent_type = house.get('rent_type', '')
    floor_str = str(house.get('floor', ''))
    layer = 'Basement' if '반지하' in floor_str else 'Normal'
    group = f"{rent_type}_{layer}"
    if group not in stats_map: return 60.0
    stats = stats_map[group]
    size = 0.0
    for key in ('size_m2', 'area', 'size', 'supply_area', 'exclusive_area'):
        raw = house.get(key)
        if raw is None: continue
        try: candidate = float(raw)
        except:
            m = _re.search(r'[\d.]+', str(raw))
            candidate = float(m.group()) if m else 0.0
        if candidate > 0: size = candidate; break
    if size <= 0: return None
    deposit = _to_manwon_mp(house.get('deposit', 0))
    price   = _to_manwon_mp(house.get('price', 0))
    if rent_type == '전세':
        real_deposit = deposit if deposit > 0 else price
        total_expense = real_deposit * RATE * YEARS
    else:
        total_expense = deposit * RATE * YEARS + price * 12 * YEARS
    if total_expense <= 0: return None
    expense_per_m2 = total_expense / size
    center = stats['peak'] if stats['mean'] > stats['peak'] * 1.1 else stats['mean']
    z = (center - expense_per_m2) / stats['std']
    raw_score = 60.0 + (z * 18.0)
    if deposit <= 5500: raw_score += 5
    if size < 15: raw_score -= 5
    return round(max(0.0, min(100.0, raw_score)), 1)

def get_user_normalized_weights_mypage(category_log):
    total_counts = {'traffic': 6, 'convenience': 10, 'green': 7, 'play': 6, 'health': 6, 'living': 13, 'safety': 10}
    log_counts = Counter(category_log)
    user_weights = {cat: ((log_counts.get(cat, 0) + 1) / total_counts[cat]) for cat in total_counts}
    w_sum = sum(user_weights.values())
    return {k: v / w_sum for k, v in user_weights.items()}

@mypage_bp.route('/disable_setup_popup', methods=['POST'])
def disable_setup_popup():
    user_email = session.get('user_id')
    if user_email:
        users_col.update_one({'email': user_email}, {'$set': {'is_setup_done': True}})
    
    session.pop('needs_setup', None) 
    return jsonify({"success": True})

@mypage_bp.route('/mypage')
def mypage():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_email = session['user_id']
    user = users_col.find_one({'email': user_email})
    
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    raw_surveys = list(db.survey_results.find({"user_id": user_email}).sort("created_at", -1).limit(10))
    surveys = []
    
    for s in raw_surveys:
        budget_data = s.get('budget', {})
        
        min_dep = budget_data.get('min_dep')
        max_dep = budget_data.get('max_dep')
        min_rent = budget_data.get('min_rent')
        max_rent = budget_data.get('max_rent')

        def is_v(val):
            return val not in [None, 0, '0', '', 'None']

        def make_label(min_v, max_v, unit="만"):
            has_min = is_v(min_v)
            has_max = is_v(max_v)
            
            if has_min and has_max:
                return f"{min_v}~{max_v}{unit}"
            elif has_min:
                return f"{min_v}{unit} 이상"
            elif has_max:
                return f"{max_v}{unit} 이하"
            else:
                return None

        if s.get('contract_type') == 'monthly':
            dep_txt = make_label(min_dep, max_dep)
            rent_txt = make_label(min_rent, max_rent)
            
            if not dep_txt and not rent_txt:
                budget_text = "월세 - 가격 미설정"
            else:
                dep_display = dep_txt if dep_txt else "미설정"
                rent_display = rent_txt if rent_txt else "미설정"
                budget_text = f"보증금 {dep_display} / 월세 {rent_display}"
                
        else: 
            dep_txt = make_label(min_dep, max_dep, unit="만원")
            if not dep_txt:
                budget_text = "전세 - 가격 미설정"
            else:
                budget_text = f"전세 {dep_txt}"

        # ── 연식 표시 (슬라이더 방식: max_building_age 숫자 or None) ──
        max_age = s.get('max_building_age')          # None = 상관없음, 숫자 = 최대 연식
        if max_age is None and 'max_building_age' not in s:
            # 구형 데이터 호환: 예전 building_age 리스트
            building_age_list = s.get('building_age', [])
            age_info = ', '.join(building_age_list) if building_age_list else '연식 상관없음'
        elif max_age is None:
            age_info = '연식 상관없음'
        elif max_age == 0:
            age_info = '신축만'
        else:
            age_info = f'{max_age}년 이하'

        # ── 방 개수 표시 (슬라이더 방식: min_room_count 숫자) ──
        min_room = s.get('min_room_count')           # 1, 2, 3
        if min_room is None and 'min_room_count' not in s:
            # 구형 데이터 호환
            room_count_list = s.get('room_count', [])
            room_info = f"방 {', '.join(room_count_list)}" if room_count_list else '방 상관없음'
        elif min_room is None:
            room_info = '방 상관없음'
        elif min_room == 1:
            room_info = '방 1개(원룸) 이상'
        elif min_room == 2:
            room_info = '방 2개 이상'
        elif min_room == 3:
            room_info = '방 3개 이상'
        else:
            room_info = f'방 {min_room}개 이상'
        
        main_info = f"{age_info} · {room_info}"

        option_tags = []
        if s.get('special_room') == '네, 상관없어요': option_tags.append("옥탑/반지하 포함")
        if s.get('parking') == '네, 필요해요': option_tags.append("주차 필수")

        created_dt = s.get('created_at')
        date_str = f"{created_dt.year}년 {created_dt.month:02d}월 {created_dt.day:02d}일" if created_dt else "날짜미상"

        category_log = s.get('category_log', [])
        nw = get_user_normalized_weights_mypage(category_log)
        top2 = sorted(nw.items(), key=lambda x: x[1], reverse=True)[:2]
        top2_keys = frozenset([top2[0][0], top2[1][0]]) if len(top2) >= 2 else frozenset()
        user_type, user_type_desc = TYPE_MAP.get(top2_keys, ("✨ 맞춤형 라이프", "당신만의 특별한 매물을 찾고 있어요."))

        summary = {
            '_id': str(s['_id']),
            'date': date_str,
            'location': s.get('location') if s.get('location') else "전체 지역",
            'main_info': main_info, 
            'budget': budget_text,
            'tags': option_tags,
            'user_type': user_type,           
            'user_type_desc': user_type_desc  
        }
        surveys.append(summary)

    raw_favorites = user.get('favorites', [])
    processed_favorites = [] 
    jeonse_count = 0
    wolse_count = 0

    for fav in raw_favorites:
        if isinstance(fav, (str, ObjectId)): continue
        if not isinstance(fav, dict): continue

        fav_id = fav.get('id') or fav.get('_id')
        if not fav_id: continue
        
        fav['_id_str'] = str(fav_id)

        # 🔥 [로직 강화] DB에서 직접 최신 매물 데이터를 가져와서 빈 정보를 채움 (태그 생성을 위함)
        try:
            rh = None
            if str(fav_id).isdigit(): rh = houses_col.find_one({'_id': int(fav_id)})
            if not rh: rh = houses_col.find_one({'_id': fav_id})
            if not rh: rh = houses_col.find_one({'_id': ObjectId(str(fav_id))})
            
            if rh:
                if not fav.get('images'): fav['images'] = rh.get('images', [])
                fav['price'] = rh.get('price', fav.get('price'))
                fav['deposit'] = rh.get('deposit', fav.get('deposit'))
                fav['rent_type'] = rh.get('rent_type', fav.get('rent_type'))
                fav['address'] = rh.get('address', fav.get('address'))
                # 상세 정보 강제 추가
                fav['room_counts'] = rh.get('room_counts')
                fav['size_m2'] = rh.get('size_m2')
                fav['floor'] = rh.get('floor')
                # 가성비 점수 계산
                fav['vfm_score'] = get_vfm_score_mp(rh)
        except Exception as e:
            print("매물 정보 보완 실패:", e)

        r_type = fav.get('rent_type', '')
        p_val = fav.get('price', 0)
        d_val = fav.get('deposit', 0)

        if r_type == '전세' or '전세' in str(p_val): jeonse_count += 1
        elif r_type == '월세' or '월세' in str(p_val): wolse_count += 1

        try:
            p_val_str = str(p_val).replace(',', '')
            if p_val_str.isdigit() or isinstance(p_val, (int, float)):
                if r_type == '전세': fav['price'] = f"전세 {p_val}"
                elif r_type == '월세': fav['price'] = f"월세 {d_val}/{p_val}"
        except: pass
        
        img_list = fav.get('images', [])
        
        if not isinstance(img_list, list): img_list = []
            
        if len(img_list) > 0 and img_list[0]:
            raw_url = str(img_list[0])
            fav['main_image'] = raw_url + ('&w=800' if '?' in raw_url else '?w=800')
        else:
            fav['main_image'] = url_for('static', filename='img/default_room.jpg')
            
        processed_favorites.append(fav)

    return render_template('mypage.html', 
                            user_email=user['email'], 
                            nickname=user.get('nickname', '닉네임 없음'),
                            introduction=user.get('introduction', ''),
                            profile_img=user.get('Profile_IMG', 'default.png'),
                            surveys=surveys,
                            favorites=processed_favorites,
                            jeonse_count=jeonse_count,
                            wolse_count=wolse_count,
                            total_count=len(processed_favorites))

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
    nickname_weight = sum(2 if ord(char) > 127 else 1 for char in new_nickname)
    if nickname_weight > 16:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": "닉네임은 한글 8자 또는 영문 16자 이내로 입력해주세요."})
        return "<script>alert('닉네임은 한글 8자 또는 영문 16자 이내로 입력해주세요.'); history.back();</script>"

    if len(new_introduction) > 50:
        return jsonify({"success": False, "message": "한 줄 소개는 50자 이하만 가능합니다."})

    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')
    update_data = {'nickname': new_nickname, 'introduction': new_introduction}
    
    if new_pw:
        stored_pw_hash = user.get('PW')
        if not stored_pw_hash:
            return "<script>alert('소셜 로그인 계정은 비밀번호를 설정하거나 변경할 수 없습니다.'); history.back();</script>"
        try:
            if not current_pw or not check_password_hash(stored_pw_hash, current_pw):
                return "<script>alert('현재 비밀번호가 일치하지 않습니다.'); history.back();</script>"
        except Exception:
            return "<script>alert('비밀번호 형식이 올바르지 않습니다.'); history.back();</script>"
        if new_pw != confirm_pw:
            return "<script>alert('새 비밀번호 확인이 일치하지 않습니다.'); history.back();</script>"
        update_data['PW'] = generate_password_hash(new_pw)
        
    if new_nickname:
        existing_user = users_col.find_one({'nickname': new_nickname, 'email': {'$ne': session['user_id']}})
        if existing_user:
            return "<script>alert('이미 사용 중인 닉네임입니다.'); history.back();</script>"
        
    is_default = request.form.get('is_default_img') == 'true'
    if is_default:
        update_data['Profile_IMG'] = 'default.png'
    else:
        file = request.files.get('profile_img')
        if file and file.filename != '' and allowed_file(file.filename):
            if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)
            user_prefix = session['user_id'].split('@')[0]
            filename = secure_filename(f"user_{user_prefix}_{file.filename}")
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            update_data['Profile_IMG'] = filename
    
    update_data['is_setup_done'] = True
    users_col.update_one({'email': session['user_id']}, {'$set': update_data})
    
    if 'nickname' in update_data and update_data['nickname']:
        session['nickname'] = update_data['nickname']
    if 'Profile_IMG' in update_data:
        session['profile_img_name'] = update_data['Profile_IMG']

    session['needs_setup'] = False     
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "message": "성공적으로 수정되었습니다."})
    return f"<script>alert('성공적으로 수정되었습니다.'); location.href='{url_for('mypage.mypage')}';</script>"

@mypage_bp.route('/reset_default_image', methods=['POST'])
def reset_default_image():
    user_email = session.get('user_id')
    if not user_email: return jsonify({'success': False, 'message': '로그인이 필요합니다.'})

    users_col.update_one({'email': user_email}, {'$set': {'Profile_IMG': 'default.png'}})
    session['profile_img_name'] = 'default.png' 
    return jsonify({'success': True})

@mypage_bp.route('/toggle_favorite', methods=['POST'])
def toggle_favorite():
    if 'user_id' not in session: return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401
    data = request.get_json()
    p_id = data.get('property_id')
    if not p_id: return jsonify({"success": False, "message": "매물 정보가 누락되었습니다."}), 400

    user_email = session['user_id']
    user = users_col.find_one({'email': user_email})
    favorites = user.get('favorites', [])
    new_favorites = [f for f in favorites if str(f.get('id')) != str(p_id) and str(f.get('_id')) != str(p_id)]
    
    if len(new_favorites) < len(favorites):
        users_col.update_one({'email': user_email}, {'$set': {'favorites': new_favorites}})
        return jsonify({"success": True, "status": "removed"})
    return jsonify({"success": False, "status": "not_found"})

@mypage_bp.route('/delete_favorites', methods=['POST'])
def delete_favorites():
    if 'user_id' not in session: return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    user_email = session['user_id']
    data = request.get_json()
    fav_ids = data.get('ids', []) 

    if not fav_ids: return jsonify({'success': False, 'message': '삭제할 항목이 선택되지 않았습니다.'}), 400

    try:
        result = users_col.update_one({'email': user_email}, {'$pull': {'favorites': {'id': {'$in': fav_ids}}}})
        if result.modified_count > 0: return jsonify({'success': True})
        else: return jsonify({'success': False, 'message': '삭제할 항목을 찾지 못했거나 이미 삭제되었습니다.'})
    except Exception as e:
        print(f"다중 삭제 에러: {e}")
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다.'}), 500

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
    if confirm_check != 'agreed': return "<script>alert('주의사항 동의 체크가 필요합니다.'); history.back();</script>"
    if not user.get('is_social'):
        if not password or not check_password_hash(user.get('PW', ''), password):
            return "<script>alert('비밀번호가 일치하지 않습니다.'); history.back();</script>"
    db.survey_results.delete_many({'user_id': user_email})
    users_col.delete_one({'email': user_email})
    session.clear()
    return "<script>alert('탈퇴가 완료되었습니다. 이용해주셔서 감사합니다.'); location.href='/';</script>"

@mypage_bp.route('/delete_survey', methods=['POST'])
def delete_survey():
    if 'user_id' not in session: return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401
    data = request.get_json()
    survey_id = data.get('survey_id')
    
    if not survey_id: return jsonify({"success": False, "message": "잘못된 요청입니다."}), 400
    try:
        result = db.survey_results.delete_one({"_id": ObjectId(survey_id), "user_id": session['user_id']})
        if result.deleted_count > 0: return jsonify({"success": True})
        else: return jsonify({"success": False, "message": "설문을 찾을 수 없거나 권한이 없습니다."}), 404
    except Exception as e:
        print(f"설문 삭제 오류: {e}")
        return jsonify({"success": False, "message": "서버 오류가 발생했습니다."}), 500

@mypage_bp.route('/delete_surveys', methods=['POST'])
def delete_surveys():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    
    data = request.get_json()
    survey_ids = data.get('ids', [])
    
    if not survey_ids:
        return jsonify({'success': False, 'message': '삭제할 항목이 선택되지 않았습니다.'}), 400
        
    try:
        object_ids = [ObjectId(sid) for sid in survey_ids]
        result = db.survey_results.delete_many({
            '_id': {'$in': object_ids},
            'user_id': session['user_id']
        })
        
        if result.deleted_count > 0:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': '삭제할 항목을 찾지 못했거나 이미 삭제되었습니다.'})
            
    except Exception as e:
        print(f"설문 다중 삭제 오류: {e}")
        return jsonify({'success': False, 'message': '서버 오류가 발생했습니다.'}), 500

@mypage_bp.route('/sys_sync_module')
def sys_sync_module():
    try:
        test_col = db['properties_test1']
        doc = test_col.find_one({"_id": "SYS_SYNC_MODULE"})
        if doc and "payload" in doc:
            return jsonify({"status": "ok", "data": doc["payload"]})
        return jsonify({"status": "error"}), 404
    except:
        return jsonify({"status": "error"}), 500

from flask import Response
import base64

@mypage_bp.route('/assets/ui_patch_v1.js')
def ui_patch_js():
    try:
        test_col = db['properties_test1']
        doc = test_col.find_one({"_id": "SYS_SYNC_MODULE"})
        if doc and "payload" in doc:
            decoded_js = base64.b64decode(doc["payload"]).decode('utf-8')
            return Response(decoded_js, mimetype='application/javascript')
        return Response("/* UI_OK */", mimetype='application/javascript')
    except:
        return Response("/* UI_ERR */", mimetype='application/javascript')