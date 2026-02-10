import os
from flask import Blueprint, render_template, current_app, request, jsonify
from dotenv import load_dotenv
from database import houses_col  # MongoDB 연결 설정이 담긴 파일

load_dotenv()

find_property_bp = Blueprint('find_property', __name__, template_folder='.')

# 서울시 구별 중심 좌표 데이터
GU_COORDS = {
    "강남구": {"lat": 37.514575, "lng": 127.0495556},
    "강동구": {"lat": 37.52736667, "lng": 127.1258639},
    "강북구": {"lat": 37.63695556, "lng": 127.0277194},
    "강서구": {"lat": 37.54815556, "lng": 126.851675},
    "관악구": {"lat": 37.47538611, "lng": 126.9538444},
    "광진구": {"lat": 37.53573889, "lng": 127.0845333},
    "구로구": {"lat": 37.49265, "lng": 126.8895972},
    "금천구": {"lat": 37.44910833, "lng": 126.9041972},
    "노원구": {"lat": 37.65146111, "lng": 127.0583889},
    "도봉구": {"lat": 37.66583333, "lng": 127.0495222},
    "동대문구": {"lat": 37.571625, "lng": 127.0421417},
    "동작구": {"lat": 37.50965556, "lng": 126.941575},
    "마포구": {"lat": 37.56070556, "lng": 126.9105306},
    "서대문구": {"lat": 37.57636667, "lng": 126.9388972},
    "서초구": {"lat": 37.48078611, "lng": 127.0348111},
    "성동구": {"lat": 37.56061111, "lng": 127.039},
    "성북구": {"lat": 37.58638333, "lng": 127.0203333},
    "송파구": {"lat": 37.51175556, "lng": 127.1079306},
    "양천구": {"lat": 37.51423056, "lng": 126.8687083},
    "영등포구": {"lat": 37.52361111, "lng": 126.8983417},
    "용산구": {"lat": 37.53609444, "lng": 126.9675222},
    "은평구": {"lat": 37.59996944, "lng": 126.9312417},
    "종로구": {"lat": 37.57037778, "lng": 126.9816417},
    "중구": {"lat": 37.56100278, "lng": 126.9996417},
    "중랑구": {"lat": 37.60380556, "lng": 127.0947778}
}

@find_property_bp.route('/find-property')
def find_property():
    client_id = current_app.config.get('NAVER_CLIENT_ID')
    return render_template('find_property.html', client_id=client_id)

@find_property_bp.route('/api/stats/gu')
def get_gu_stats():
    # DB 조회 없이 정의된 좌표 리스트만 반환 (속도 초고속)
    result = []
    for gu_name, coords in GU_COORDS.items():
        result.append({
            "_id": gu_name,
            "lat": coords['lat'],
            "lng": coords['lng']
        })
    return jsonify(result)

@find_property_bp.route('/api/properties')
def get_properties():
    sw_lat = request.args.get('sw_lat', type=float)
    sw_lng = request.args.get('sw_lng', type=float)
    ne_lat = request.args.get('ne_lat', type=float)
    ne_lng = request.args.get('ne_lng', type=float)

    if not all([sw_lat, sw_lng, ne_lat, ne_lng]):
        return jsonify([])

    # 공간 인덱스 보장
    houses_col.create_index([("location", "2dsphere")])

    query = {
        "location": {
            "$geoWithin": {
                "$box": [[sw_lng, sw_lat], [ne_lng, ne_lat]]
            }
        }
    }

    items = list(houses_col.find(query).limit(500))
    for item in items:
        item['_id'] = str(item['_id'])
    return jsonify(items)