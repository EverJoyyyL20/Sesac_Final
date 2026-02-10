import os
from flask import Blueprint, render_template, current_app, request, jsonify # jsonify 추가
from dotenv import load_dotenv
# import requests  # 만약 외부 API 호출이 필요 없다면 이 줄은 삭제해도 됩니다. 
# Flask의 request와 이름이 겹치면 request.args를 쓸 때 에러가 납니다.

from database import houses_col

load_dotenv()

find_property_bp = Blueprint('find_property', __name__, template_folder='.')

@find_property_bp.route('/find-property')
def find_property():
    client_id = current_app.config.get('NAVER_CLIENT_ID')
    return render_template('find_property.html', client_id=client_id)

# find_property_route.py
@find_property_bp.route('/api/properties')
def get_properties():
    sw_lat = request.args.get('sw_lat', type=float)
    sw_lng = request.args.get('sw_lng', type=float)
    ne_lat = request.args.get('ne_lat', type=float)
    ne_lng = request.args.get('ne_lng', type=float)

    if not all([sw_lat, sw_lng, ne_lat, ne_lng]):
        return jsonify([])
    houses_col.create_index([("location", "2dsphere")])

    query = {
        "location": {
            "$geoWithin": {
                "$box": [
                    [sw_lng, sw_lat], 
                    [ne_lng, ne_lat]
                ]
            }
        }
    }
    

    items = list(houses_col.find(query).limit(500))
    print(f"DEBUG: Found {len(items)} items in [[{sw_lng}, {sw_lat}], [{ne_lng}, {ne_lat}]]")

    for item in items:
        item['_id'] = str(item['_id'])
        
    return jsonify(items)