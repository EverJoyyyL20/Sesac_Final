import os
from flask import Blueprint, render_template, current_app, request, jsonify, session
from datetime import datetime
from database import houses_col, db 

find_property_bp = Blueprint('find_property', __name__, template_folder='.')

# 서울 각 구별 중심 좌표 (클러스터링 대용)
GU_COORDS = {
    "강남구": {"lat": 37.514575, "lng": 127.0495556}, "강동구": {"lat": 37.52736667, "lng": 127.1258639},
    "강북구": {"lat": 37.63695556, "lng": 127.0277194}, "강서구": {"lat": 37.54815556, "lng": 126.851675},
    "관악구": {"lat": 37.47538611, "lng": 126.9538444}, "광진구": {"lat": 37.53573889, "lng": 127.0845333},
    "구로구": {"lat": 37.49265, "lng": 126.8895972}, "금천구": {"lat": 37.44910833, "lng": 126.9041972},
    "노원구": {"lat": 37.65146111, "lng": 127.0583889}, "도봉구": {"lat": 37.66583333, "lng": 127.0495222},
    "동대문구": {"lat": 37.571625, "lng": 127.0421417}, "동작구": {"lat": 37.50965556, "lng": 126.941575},
    "마포구": {"lat": 37.56070556, "lng": 126.9105306}, "서대문구": {"lat": 37.57636667, "lng": 126.9388972},
    "서초구": {"lat": 37.48078611, "lng": 127.0348111}, "성동구": {"lat": 37.56061111, "lng": 127.039},
    "성북구": {"lat": 37.58638333, "lng": 127.0203333}, "송파구": {"lat": 37.51175556, "lng": 127.1079306},
    "양천구": {"lat": 37.51423056, "lng": 126.8687083}, "영등포구": {"lat": 37.52361111, "lng": 126.8983417},
    "용산구": {"lat": 37.53609444, "lng": 126.9675222}, "은평구": {"lat": 37.59996944, "lng": 126.9312417},
    "종로구": {"lat": 37.57037778, "lng": 126.9816417}, "중구": {"lat": 37.56100278, "lng": 126.9996417},
    "중랑구": {"lat": 37.60380556, "lng": 127.0947778}
}

@find_property_bp.route('/find_property')
def find_property():
    client_id = current_app.config.get('NAVER_CLIENT_ID')
    return render_template('find_property.html', client_id=client_id)

@find_property_bp.route('/api/stats/gu')
def get_gu_stats():
    result = [{"_id": k, "lat": v['lat'], "lng": v['lng']} for k, v in GU_COORDS.items()]
    return jsonify(result)

# find_property.py 내의 get_property_by_id 부분 수정
@find_property_bp.route('/api/property/<prop_id>')
def get_property_by_id(prop_id):
    try:
        search_query = [{'_id': prop_id}]
        try: search_query.append({'_id': int(prop_id)})
        except ValueError: pass

        item = houses_col.find_one({"$or": search_query})
        if item:
            is_fav = False
            if 'user_id' in session:
                if db.favorites.find_one({"user_id": session['user_id'], "property_id": str(item['_id'])}):
                    is_fav = True

            # --- 층수 정보 가공 로직 시작 ---
            raw_floor = item.get('floor', '정보없음')
            floor_display = raw_floor # 기본값
            
            if '/' in raw_floor:
                parts = raw_floor.split('/') # '고/15층' -> ['고', '15층']
                if len(parts) == 2:
                    current_f = parts[0].strip()
                    total_f = parts[1].strip()
                    
                    # '고층', '저층' 등으로 변환 (선택 사항)
                    mapping = {"고": "고층", "중": "중층", "저": "저층", "옥탑": "옥탑방", "반지": "반지하"}
                    current_f = mapping.get(current_f, f"{current_f}층")
                    
                    floor_display = f"전체 {total_f} 중 {current_f}"
            # --- 층수 정보 가공 로직 끝 ---

            processed = {
                "_id": str(item['_id']),
                "price": item.get('price'),
                "deposit": item.get('deposit'),
                "rent_type": item.get('rent_type', item.get('type')),
                "address": item.get('address'),
                "floor": floor_display, # 가공된 텍스트 전달
                "location": item.get('location'),
                "is_favorite": is_fav
            }
            return jsonify(processed)
        return jsonify({"error": "없음"}), 404
    except:
        return jsonify({"error": "에러"}), 500

@find_property_bp.route('/api/favorite', methods=['POST'])
def add_favorite():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "로그인이 필요합니다."}), 401
    
    data = request.get_json()
    user_id = session['user_id']
    prop_id = str(data.get('property_id'))
    
    exists = db.favorites.find_one({"user_id": user_id, "property_id": prop_id})
    if exists:
        db.favorites.delete_one({"_id": exists['_id']})
        return jsonify({"status": "success", "message": "찜 목록에서 삭제되었습니다.", "action": "removed"})
    
    db.favorites.insert_one({
        "user_id": user_id,
        "property_id": prop_id,
        "address": data.get('address'),
        "price_info": data.get('price_info'),
        "created_at": datetime.now()
    })
    return jsonify({"status": "success", "message": "찜 목록에 추가되었습니다!", "action": "added"})

@find_property_bp.route('/api/properties')
def get_properties():
    sw_lat = request.args.get('sw_lat', type=float)
    sw_lng = request.args.get('sw_lng', type=float)
    ne_lat = request.args.get('ne_lat', type=float)
    ne_lng = request.args.get('ne_lng', type=float)

    if not all([sw_lat, sw_lng, ne_lat, ne_lng]): return jsonify([])

    query = {"location": {"$geoWithin": {"$box": [[sw_lng, sw_lat], [ne_lng, ne_lat]]}}}
    try:
        items = list(houses_col.find(query).limit(300))
        return jsonify([{**item, "_id": str(item['_id'])} for item in items])
    except:
        return jsonify([]), 500