import os
from flask import Blueprint, render_template, current_app, request, jsonify, session
from datetime import datetime
from database import houses_col, db, users_col
from bson.objectid import ObjectId

# 블루프린트 설정
find_bp = Blueprint('find', __name__, template_folder='.')

# 서울 각 구별 중심 좌표 (클러스터링용)
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

@find_bp.route('/find')
def find():
    client_id = current_app.config.get('NAVER_CLIENT_ID')
    return render_template('find_property.html', client_id=client_id)

@find_bp.route('/api/stats/gu')
def get_gu_stats():
    result = [{"_id": k, "lat": v['lat'], "lng": v['lng']} for k, v in GU_COORDS.items()]
    return jsonify(result)

# -------------------------------------------------------------------------
# 🔥 [수정] 상세 정보 조회 로직 (500 에러 해결)
# -------------------------------------------------------------------------
@find_bp.route('/api/property/<prop_id>')
def get_property_by_id(prop_id):
    try:
        # ID 타입 대응 (문자열/숫자 모두 검색)
        search_query = [{'_id': prop_id}]
        try: search_query.append({'_id': int(prop_id)})
        except ValueError: pass

        item = houses_col.find_one({"$or": search_query})
        
        if item:
            is_fav = False
            # 세션 확인 및 찜 여부 체크
            if 'user_id' in session:
                # db.users 대신 이미 정의된 users_col 사용
                user = users_col.find_one({"email": session['user_id']})
                if user:
                    favorites = user.get('favorites', [])
                    for f in favorites:
                        # 딕셔너리와 문자열 데이터 모두 대응하는 안전한 비교
                        if isinstance(f, dict):
                            if str(f.get('id')) == str(item['_id']):
                                is_fav = True
                                break
                        elif str(f) == str(item['_id']):
                            is_fav = True
                            break

            # 층수 정보 가공
            raw_floor = item.get('floor', '정보없음')
            floor_display = raw_floor
            if '/' in raw_floor:
                parts = raw_floor.split('/')
                if len(parts) == 2:
                    current_f = parts[0].strip()
                    total_f = parts[1].strip()
                    mapping = {"고": "고층", "중": "중층", "저": "저층", "옥탑": "옥탑방", "반지": "반지하"}
                    current_f = mapping.get(current_f, f"{current_f}층")
                    floor_display = f"전체 {total_f} 중 {current_f}"

            # 최종 데이터 구성
            processed = {
                "_id": str(item['_id']),
                "price": item.get('price'),
                "deposit": item.get('deposit'),
                "rent_type": item.get('rent_type', item.get('type')),
                "address": item.get('address'),
                "floor": floor_display,
                "location": item.get('location'),
                "parking":item.get("hasparking"),
                "buildtype":item.get("buildingUse"),
                "area": item.get('size_m2'),                     # 면적
                "images": item.get('images') if isinstance(item.get('images'), list) else [],
                "is_favorite": is_fav,
                "score": dict(item.get('category_scores', {}))
            }
            return jsonify(processed)
        return jsonify({"error": "매물을 찾을 수 없습니다."}), 404
    except Exception as e:
        print(f"❌ 매물 상세조회 에러: {e}") # 디버깅을 위해 터미널에 에러 출력
        return jsonify({"error": str(e)}), 500

@find_bp.route('/api/favorite', methods=['POST'])
def add_favorite():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "로그인이 필요합니다."}), 401
    
    data = request.get_json()
    user_email = session['user_id']
    prop_id = str(data.get('property_id'))
    
    user = users_col.find_one({'email': user_email})
    if not user:
        return jsonify({"status": "error", "message": "사용자를 찾을 수 없습니다."}), 404

    favorites = user.get('favorites', [])
    is_exists = False
    for f in favorites:
        if isinstance(f, dict) and str(f.get('id')) == prop_id:
            is_exists = True
            break
        elif str(f) == prop_id:
            is_exists = True
            break

    if is_exists:
        users_col.update_one(
            {'email': user_email},
            {'$pull': {'favorites': {'id': prop_id}}}
        )
        return jsonify({"status": "success", "message": "찜 목록에서 삭제되었습니다.", "action": "removed"})
    
    else:
        try:
            real_house = None
            if prop_id.isdigit():
                real_house = houses_col.find_one({'_id': int(prop_id)})
            
            if not real_house:
                real_house = houses_col.find_one({'_id': prop_id})

            if not real_house:
                try: real_house = houses_col.find_one({'_id': ObjectId(prop_id)})
                except: pass
            
            if real_house:
                price_info = ""
                if real_house.get('rent_type') == '월세':
                    price_info = f"월세 {real_house.get('deposit')}/{real_house.get('price')}"
                else:
                    price_info = f"{real_house.get('rent_type')} {real_house.get('price')}"

                new_favorite = {
                    "id": str(real_house['_id']),
                    "address": real_house.get('address'),
                    "price": price_info,
                    "rent_type": real_house.get('rent_type'),
                    "deposit": real_house.get('deposit'),
                    "images": real_house.get('images', []), # DB 이미지 배열 저장
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                if len(favorites) >= 10:
                    return jsonify({"status": "error", "message": "찜은 최대 10개까지만 가능합니다."}), 400

                users_col.update_one(
                    {'email': user_email},
                    {'$push': {'favorites': new_favorite}}
                )
                return jsonify({"status": "success", "message": "찜 목록에 추가되었습니다!", "action": "added"})
            
            return jsonify({"status": "error", "message": "매물 정보를 찾을 수 없습니다."}), 404
            
        except Exception as e:
            print(f"찜하기 에러: {e}")
            return jsonify({"status": "error", "message": "서버 오류가 발생했습니다."}), 500

@find_bp.route('/api/properties')
def get_properties():
    sw_lat = request.args.get('sw_lat', type=float)
    sw_lng = request.args.get('sw_lng', type=float)
    ne_lat = request.args.get('ne_lat', type=float)
    ne_lng = request.args.get('ne_lng', type=float)

    center_lat = request.args.get('center_lat', type=float)
    center_lng = request.args.get('center_lng', type=float)
    radius_m = request.args.get('radius', default=1000, type=int)

    if not all([sw_lat, sw_lng, ne_lat, ne_lng]): 
        return jsonify([])

    query = {
        "location": {
            "$geoWithin": {
                "$box": [[sw_lng, sw_lat], [ne_lng, ne_lat]]
            }
        }
    }

    if center_lat is not None and center_lng is not None:
        # $centerSphere는 [경도, 위도] 순서이며, 거리는 '라디안' 단위로 계산합니다.
        # 라디안 = 미터 / (지구 반지름 약 6,378,100m)
        radius_in_radians = radius_m / 6378100
        query["location"] = {
            "$geoWithin": {
                "$centerSphere": [[center_lng, center_lat], radius_in_radians]
            }
        }

    rent_type = request.args.get('type')
    if rent_type: query["rent_type"] = rent_type

    min_dep = request.args.get('min_deposit', type=int)
    max_dep = request.args.get('max_deposit', type=int)
    if min_dep is not None or max_dep is not None:
        query["deposit"] = {}
        if min_dep is not None: query["deposit"]["$gte"] = min_dep
        if max_dep is not None: query["deposit"]["$lte"] = max_dep

    min_pri = request.args.get('min_price', type=int)
    max_pri = request.args.get('max_price', type=int)
    if min_pri is not None or max_pri is not None:
        query["price"] = {}
        if min_pri is not None: query["price"]["$gte"] = min_pri
        if max_pri is not None: query["price"]["$lte"] = max_pri

    items = list(houses_col.find(query).limit(300))
    return jsonify([{**item, "_id": str(item['_id'])} for item in items])