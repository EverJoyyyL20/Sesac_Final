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

@find_bp.route('/api/property/<prop_id>')
def get_property_by_id(prop_id):
    try:
        search_query = [{'_id': prop_id}]
        try: search_query.append({'_id': int(prop_id)})
        except ValueError: pass

        item = houses_col.find_one({"$or": search_query})
        
        if item:
            is_fav = False
            if 'user_id' in session:
                user = users_col.find_one({"email": session['user_id']})
                if user:
                    favorites = user.get('favorites', [])
                    for f in favorites:
                        if isinstance(f, dict):
                            if str(f.get('id')) == str(item['_id']):
                                is_fav = True
                                break
                        elif str(f) == str(item['_id']):
                            is_fav = True
                            break

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

            processed = {
                "_id": str(item['_id']),
                "price": item.get('price'),
                "deposit": item.get('deposit'),
                "rent_type": item.get('rent_type', item.get('type')),
                "address": item.get('address'),
                "floor": floor_display,
                "location": item.get('location'),
                "parking":item.get("hasParking"),
                "buildtype":item.get("buildingUse"),
                "area": item.get('size_m2'),
                "images": item.get('images') if isinstance(item.get('images'), list) else [],
                "is_favorite": is_fav,
                "score": dict(item.get('category_scores', {})),
                "options": item.get('options', [])
            }
            return jsonify(processed)
        return jsonify({"error": "매물을 찾을 수 없습니다."}), 404
    except Exception as e:
        print(f"❌ 매물 상세조회 에러: {e}")
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
                    "images": real_house.get('images', []), 
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                

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
        radius_in_radians = radius_m / 6378100
        query["location"] = {
            "$geoWithin": {
                "$centerSphere": [[center_lng, center_lat], radius_in_radians]
            }
        }

    rent_type = request.args.get('type')
    if rent_type: query["rent_type"] = rent_type

    # 다중 방 개수 필터 로직 (room_counts 필드 기준 검색으로 수정됨)
    rooms_param = request.args.get('rooms')
    if rooms_param:
        room_list = rooms_param.split(',')
        room_conditions = []
        for r in room_list:
            # 💡 핵심 수정 1: URL 통신 중 '+' 기호가 공백(' ')으로 치환되는 현상 방지
            r = r.strip()
            
            if r == '원룸':
                room_conditions.append({"room_counts": "1개"})
            elif r == '투룸':
                room_conditions.append({"room_counts": "2개"})
            elif r in ['쓰리룸+', '쓰리룸']:
                # 💡 핵심 수정 2: '3', '3개', '4개' 등 3 이상의 숫자가 포함된 모든 데이터를 확실하게 잡아내는 유연한 정규식
                room_conditions.append({"room_counts": {"$regex": "[3-9]|[1-9][0-9]"}})
        
        if room_conditions:
            query.setdefault("$and", []).append({"$or": room_conditions})

    # 🔥 [수정된 부분] 전세/월세에 따른 가격/보증금 필터 동적 할당
    min_dep = request.args.get('min_deposit', type=int)
    max_dep = request.args.get('max_deposit', type=int)
    min_pri = request.args.get('min_price', type=int)
    max_pri = request.args.get('max_price', type=int)

    if rent_type == '전세':
        # 전세일 경우: UI의 '보증금' 입력값을 DB의 'price'(전세금) 필드로 조회
        if min_dep is not None or max_dep is not None:
            query["price"] = {}
            if min_dep is not None: query["price"]["$gte"] = min_dep
            if max_dep is not None: query["price"]["$lte"] = max_dep
    else:
        # 월세(또는 전체)일 경우: 보증금은 deposit, 월세는 price 로 각각 조회
        if min_dep is not None or max_dep is not None:
            query["deposit"] = {}
            if min_dep is not None: query["deposit"]["$gte"] = min_dep
            if max_dep is not None: query["deposit"]["$lte"] = max_dep

        if min_pri is not None or max_pri is not None:
            query["price"] = {}
            if min_pri is not None: query["price"]["$gte"] = min_pri
            if max_pri is not None: query["price"]["$lte"] = max_pri

    # 🔥 [추가된 부분] 면적 필터 로직 (기존에 누락되어 있어 추가했습니다)
    min_size = request.args.get('min_size', type=float)
    max_size = request.args.get('max_size', type=float)
    if min_size is not None or max_size is not None:
        query["size_m2"] = {}
        if min_size is not None: query["size_m2"]["$gte"] = min_size
        if max_size is not None: query["size_m2"]["$lte"] = max_size

    exclude_under = request.args.get('exclude_under')
    if exclude_under == 'true':
        query["floor"] = {"$not": {"$regex": "반지하"}}

    parking = request.args.get('parking')
    if parking == '주차 가능':
        query["hasParking"] = "주차 가능"

    # 🔥 [추가된 부분] 옵션 여부 필터 (배열 데이터 유무 확인)
    option_status = request.args.get('option_status')
    if option_status == '있음':
        # options 필드가 존재하고, 배열의 크기가 0이 아닌 경우 (데이터가 들어있음)
        query['options'] = {"$exists": True, "$not": {"$size": 0}}
    elif option_status == '없음':
        # options 필드가 아예 없거나, 빈 배열([])인 경우
        query['$or'] = [
            {'options': {"$exists": False}},
            {'options': {"$size": 0}}
        ]

    items = list(houses_col.find(query).limit(300))
    return jsonify([{**item, "_id": str(item['_id'])} for item in items])