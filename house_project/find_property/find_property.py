import os
import json
import re 
import random
import requests # 🔥 [추가] 장소 좌표 변환을 위한 requests 모듈
from flask import Blueprint, render_template, current_app, request, jsonify, session
from datetime import datetime
from database import houses_col, db, users_col
from bson.objectid import ObjectId

from dotenv import load_dotenv 
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

load_dotenv(override=True)

# ------------------------------------------------------------------
# 🔥 AI 모델 초기화
# ------------------------------------------------------------------
api_key = os.getenv("OPENAI_API_KEY")
try:
    llm = ChatOpenAI(model="gpt-5.2", temperature=0.1, openai_api_key=api_key)
    print("✅ Find Property GPT 모델 초기화 성공")
except Exception as e:
    print(f"❌ GPT 초기화 실패: {e}")
    llm = None

find_bp = Blueprint('find', __name__, template_folder='.')


# ------------------------------------------------------------------
# 가성비(VFM) 점수 계산
# ------------------------------------------------------------------
def _to_manwon_fp(value):
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

def get_vfm_score_fp(house):
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
    if size <= 0: return 60.0
    deposit = _to_manwon_fp(house.get('deposit', 0))
    price   = _to_manwon_fp(house.get('price', 0))
    if rent_type == '전세':
        real_deposit = deposit if deposit > 0 else price
        total_expense = real_deposit * RATE * YEARS
    else:
        total_expense = deposit * RATE * YEARS + price * 12 * YEARS
    if total_expense <= 0: return 60.0
    expense_per_m2 = total_expense / size
    center = stats['peak'] if stats['mean'] > stats['peak'] * 1.1 else stats['mean']
    z = (center - expense_per_m2) / stats['std']
    raw_score = 60.0 + (z * 18.0)
    if deposit <= 5500: raw_score += 5
    if size < 15: raw_score -= 5
    return round(max(0.0, min(100.0, raw_score)), 1)


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

# 🔥 장소 이름(예: 강남역)을 좌표로 변환하는 헬퍼 함수
# 🔥 장소 이름(예: 강남역)을 좌표로 변환하는 헬퍼 함수
def get_poi_coordinates(keyword):
    kakao_key = os.getenv("KAKAO_REST_API")
    print(f"🔍 [디버깅] 입력된 키워드: '{keyword}' / 카카오 키 로드 성공: {'✅ 네' if kakao_key else '❌ 아니오'}")
    
    if not kakao_key: return None
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {kakao_key}"}
    try:
        res = requests.get(url, headers=headers, params={"query": keyword, "size": 1})
        print(f"🔍 [디버깅] 카카오 응답 코드: {res.status_code}")
        
        if res.status_code == 200 and res.json().get('documents'):
            doc = res.json()['documents'][0]
            lat, lng = float(doc['y']), float(doc['x'])
            print(f"🔍 [디버깅] 좌표 변환 성공: lat={lat}, lng={lng}")
            return lat, lng
        else:
            print(f"❌ [디버깅] 장소 검색 실패 (결과 없음): {res.text}")
    except Exception as e:
        print(f"❌ Kakao API Error: {e}")
    return None

# =====================================================================
# 기존 라우트 유지 (/find, /api/stats/gu, /api/property/<id>, /api/properties, /api/favorite)
# =====================================================================
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
                    current_f, total_f = parts[0].strip(), parts[1].strip()
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
        return jsonify({"error": str(e)}), 500

@find_bp.route('/api/favorite', methods=['POST'])
def add_favorite():
    if 'user_id' not in session: return jsonify({"status": "error", "message": "로그인이 필요합니다."}), 401
    data = request.get_json()
    user_email = session['user_id']
    prop_id = str(data.get('property_id'))
    user = users_col.find_one({'email': user_email})
    if not user: return jsonify({"status": "error", "message": "사용자를 찾을 수 없습니다."}), 404

    favorites = user.get('favorites', [])
    is_exists = False
    for f in favorites:
        if isinstance(f, dict) and str(f.get('id')) == prop_id: is_exists = True; break
        elif str(f) == prop_id: is_exists = True; break

    if is_exists:
        users_col.update_one({'email': user_email}, {'$pull': {'favorites': {'id': prop_id}}})
        return jsonify({"status": "success", "message": "찜 목록에서 삭제되었습니다.", "action": "removed"})
    else:
        try:
            real_house = None
            if prop_id.isdigit(): real_house = houses_col.find_one({'_id': int(prop_id)})
            if not real_house: real_house = houses_col.find_one({'_id': prop_id})
            if not real_house:
                try: real_house = houses_col.find_one({'_id': ObjectId(prop_id)})
                except: pass
            
            if real_house:
                price_info = f"월세 {real_house.get('deposit')}/{real_house.get('price')}" if real_house.get('rent_type') == '월세' else f"{real_house.get('rent_type')} {real_house.get('price')}"
                new_favorite = {
                    "id": str(real_house['_id']),
                    "address": real_house.get('address'),
                    "price": price_info,
                    "rent_type": real_house.get('rent_type'),
                    "deposit": real_house.get('deposit'),
                    "images": real_house.get('images', []), 
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                if len(favorites) >= 10: return jsonify({"status": "error", "message": "찜은 최대 10개까지만 가능합니다."}), 400
                users_col.update_one({'email': user_email}, {'$push': {'favorites': new_favorite}})
                return jsonify({"status": "success", "message": "찜 목록에 추가되었습니다!", "action": "added"})
            return jsonify({"status": "error", "message": "매물 정보를 찾을 수 없습니다."}), 404
        except Exception as e:
            return jsonify({"status": "error", "message": "서버 오류가 발생했습니다."}), 500

@find_bp.route('/api/properties')
def get_properties():
    sw_lat, sw_lng = request.args.get('sw_lat', type=float), request.args.get('sw_lng', type=float)
    ne_lat, ne_lng = request.args.get('ne_lat', type=float), request.args.get('ne_lng', type=float)
    center_lat, center_lng = request.args.get('center_lat', type=float), request.args.get('center_lng', type=float)
    radius_m = request.args.get('radius', default=1000, type=int)

    if not all([sw_lat, sw_lng, ne_lat, ne_lng]): return jsonify([])

    query = {"location": {"$geoWithin": {"$box": [[sw_lng, sw_lat], [ne_lng, ne_lat]]}}}

    if center_lat is not None and center_lng is not None:
        radius_in_radians = radius_m / 6378100
        query["location"] = {"$geoWithin": {"$centerSphere": [[center_lng, center_lat], radius_in_radians]}}

    rent_type = request.args.get('type')
    if rent_type: query["rent_type"] = rent_type

    rooms_param = request.args.get('rooms')
    if rooms_param:
        room_list = rooms_param.split(',')
        room_conditions = []
        for r in room_list:
            r = r.strip()
            if r == '원룸': room_conditions.append({"room_counts": "1개"})
            elif r == '투룸': room_conditions.append({"room_counts": "2개"})
            elif r in ['쓰리룸+', '쓰리룸']: room_conditions.append({"room_counts": {"$regex": "[3-9]|[1-9][0-9]"}})
        if room_conditions: query.setdefault("$and", []).append({"$or": room_conditions})

    min_dep, max_dep = request.args.get('min_deposit', type=int), request.args.get('max_deposit', type=int)
    min_pri, max_pri = request.args.get('min_price', type=int), request.args.get('max_price', type=int)

    if rent_type == '전세':
        if min_dep is not None or max_dep is not None:
            query["price"] = {}
            if min_dep is not None: query["price"]["$gte"] = min_dep
            if max_dep is not None: query["price"]["$lte"] = max_dep
    else:
        if min_dep is not None or max_dep is not None:
            query["deposit"] = {}
            if min_dep is not None: query["deposit"]["$gte"] = min_dep
            if max_dep is not None: query["deposit"]["$lte"] = max_dep
        if min_pri is not None or max_pri is not None:
            query["price"] = {}
            if min_pri is not None: query["price"]["$gte"] = min_pri
            if max_pri is not None: query["price"]["$lte"] = max_pri

    min_size, max_size = request.args.get('min_size', type=float), request.args.get('max_size', type=float)
    if min_size is not None or max_size is not None:
        query["size_m2"] = {}
        if min_size is not None: query["size_m2"]["$gte"] = min_size
        if max_size is not None: query["size_m2"]["$lte"] = max_size

    if request.args.get('exclude_under') == 'true': query["floor"] = {"$not": {"$regex": "반지하"}}
    if request.args.get('parking') == '주차 가능': query["hasParking"] = "주차 가능"

    option_status = request.args.get('option_status')
    if option_status == '있음': query['options'] = {"$exists": True, "$not": {"$size": 0}}
    elif option_status == '없음': query['$or'] = [{'options': {"$exists": False}}, {'options': {"$size": 0}}]

    vfm_min = request.args.get('vfm_min', type=float)

    # 가성비 필터가 있을 경우: limit 없이 전체 조회 → vfm_score 계산 → 필터링 → 상위 300개
    # 가성비 필터가 없을 경우: 기존대로 limit(300) 후 vfm_score만 계산
    if vfm_min is not None:
        items = list(houses_col.find(query))  # 전체 조회 (limit 없음)
        result = []
        for item in items:
            item_dict = {**item, "_id": str(item['_id'])}
            item_dict['vfm_score'] = get_vfm_score_fp(item)
            if item_dict['vfm_score'] >= vfm_min:
                result.append(item_dict)
        result = result[:300]  # 필터링 후 최대 300개
    else:
        items = list(houses_col.find(query).limit(300))
        result = []
        for item in items:
            item_dict = {**item, "_id": str(item['_id'])}
            item_dict['vfm_score'] = get_vfm_score_fp(item)
            result.append(item_dict)

    return jsonify(result)

# =====================================================================
# 🔥 [AI 챗봇 완전 개편] 서울 제한 & 안전한 데이터 파싱 적용
# =====================================================================
@find_bp.route('/api/chat_search', methods=['POST'])
def chat_search():
    if not llm:
        return jsonify({"status": "error", "reply": "AI 서버 연결 오류입니다."})

    data = request.get_json()
    user_query = data.get('query', '')
    current_state = data.get('current_state', {})
    
    if not user_query: return jsonify({"status": "error", "reply": "조건을 입력해주세요!"})
    nickname = session.get('nickname', '고객')

    template = """당신은 상위 1% VIP를 전담하는 뛰어난 직관력을 가진 부동산 AI 수석 큐레이터입니다.
    사용자의 발화를 분석하여 [기존 조건]에 병합하고 검색 가능한 JSON 필터로 변환하세요.

    [⭐⭐⭐ AI 핵심 추론 및 업데이트 규칙 ⭐⭐⭐]
    1. 위치 분리 추론 (가장 중요)
       - 사용자가 "구/동"을 말하면 -> "address_keyword"에 저장 (예: 강남구, 역삼동)
       - 사용자가 "지하철역/장소"와 "거리/시간"을 말하면 -> "poi_name"과 "radius_m"로 분리 저장
         (예: "강남역 도보 10분" -> poi_name: "강남역", radius_m: 800) ※ 도보 1분 = 80m 계산
    2. '상관없음' 처리: 사용자가 "아무거나", "상관없어", "가격 무관" 등을 언급하면
       해당 필드의 값을 반드시 null로 두고, "is_ready_to_search": true 로 즉시 설정하여 귀찮게 묻지 마세요.
    3. 기존 조건 보존: 사용자가 명시적으로 바꾸거나 지우지 않는 한, [기존 조건]에 있던 값은 무조건 새 JSON에 복사하세요.
    4. 🚫 서울 한정 서비스 (엄격 적용): 본 서비스는 오직 **'서울시'** 내의 매물만 제공합니다. 
       - 사용자가 경기도 등 서울 외 지역을 검색하면, "is_ready_to_search"를 false로 하고 `reply_msg`에 "현재 저희 서비스는 서울 지역 매물만 다루고 있습니다."라고 안내하세요.

    [기존 누적 조건]
    {current_state}

    [현재 고객의 요청]
    {query}

    오직 아래 JSON 형식으로만 응답하세요:
    {{
        "address_keyword": "지역명 (구/동. 기존 유지 혹은 변경. 모르면 null)",
        "poi_name": "특정 장소/역 이름 (예: 신촌역. 모르면 null)",
        "radius_m": 거리 반경 (숫자만 입력. 예: 800. 모르면 null),
        "rent_type": "전세" 또는 "월세" (상관없으면 null),
        "max_deposit": 최대 보증금/전세금 (만원 단위 숫자. 예: 20000. 상관없으면 null),
        "max_rent": 최대 월세 (만원 단위 숫자. 상관없으면 null),
        "room_count": "1", "2", "3+" 중 하나 (상관없으면 null),
        "parking": true, false 또는 null,
        "is_ready_to_search": 충분한 정보가 모였거나 사용자가 "아무거나/상관없다"고 하면 무조건 true,
        "reply_msg": "HTML <br>을 활용한 자연스럽고 세련된 안내 멘트"
    }}
    """
    
    # 🔥 [추가] 안전하게 숫자로 변환하는 헬퍼 함수 (에러 원천 차단)
    def safe_int(val, default=None):
        if val in [None, "null", "", "상관없음", "무관"]: return default
        try: return int(float(val))
        except: return default

    raw_content = "" # 에러 로깅용
    try:
        prompt = PromptTemplate.from_template(template)
        chain = prompt | llm
        res = chain.invoke({
            "query": user_query, 
            "nickname": nickname, 
            "current_state": json.dumps(current_state, ensure_ascii=False)
        })
        
        # 🔥 [핵심 수정] AI 응답이 리스트(List)로 올 경우를 대비한 안전한 텍스트 추출
        ai_output = res.content
        if isinstance(ai_output, list):
            # 리스트 내부의 딕셔너리들에서 'text' 부분만 찾아 하나로 합칩니다.
            raw_content = "".join([block.get("text", "") for block in ai_output if isinstance(block, dict)])
        else:
            raw_content = str(ai_output)
            
        raw_content = raw_content.replace("```json", "").replace("```", "").strip()
        
        match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        parsed = json.loads(match.group(0) if match else raw_content)
        
        # 1. DB 쿼리 생성
        db_query = {}
        
        # 2. 위치 및 반경 로직 적용
        if parsed.get("poi_name"):
            coords = get_poi_coordinates(parsed["poi_name"])
            if coords:
                lat, lng = coords
                # 🔥 [수정] radius_m이 null로 들어와도 다운되지 않도록 safe_int 적용
                radius = safe_int(parsed.get("radius_m"), 1000) 
                rad_radians = radius / 6378100
                db_query["location"] = {"$geoWithin": {"$centerSphere": [[lng, lat], rad_radians]}}
            else:
                db_query["address"] = {"$regex": parsed["poi_name"]}
                
        elif parsed.get("address_keyword"):
            db_query["address"] = {"$regex": parsed["address_keyword"]}

        # 3. 거래 유형 및 예산 적용 (safe_int 적용)
        r_type = parsed.get("rent_type")
        if r_type and r_type not in ["상관없음", "null"]:
            db_query["rent_type"] = r_type
            
        max_dep = safe_int(parsed.get("max_deposit"))
        max_rent = safe_int(parsed.get("max_rent"))
        
        if r_type == '전세':
            if max_dep: db_query["price"] = {"$lte": max_dep}
        elif r_type == '월세':
            if max_dep: db_query["deposit"] = {"$lte": max_dep}
            if max_rent: db_query["price"] = {"$lte": max_rent}
        else:
            if max_dep: db_query["deposit"] = {"$lte": max_dep}
            if max_rent: db_query["price"] = {"$lte": max_rent}
                
        # 4. 방 개수 및 주차
        r_count = str(parsed.get("room_count"))
        if r_count == "1": db_query["room_counts"] = "1개"
        elif r_count == "2": db_query["room_counts"] = "2개"
        elif r_count in ["3", "3+"]: db_query["room_counts"] = {"$regex": "[3-9]|[1-9][0-9]"}
            
        if parsed.get("parking") is True or str(parsed.get("parking")).lower() == "true":
            db_query["hasParking"] = "주차 가능"
            
        # 5. 매물 검색
        items = list(houses_col.find(db_query).limit(100))
        formatted_items = [{**item, "_id": str(item['_id'])} for item in items]

        reply_html = parsed.get("reply_msg", f"{nickname}님, 분석 중입니다.")
        show_reset = False

        # 6. 결과 렌더링
        if parsed.get("is_ready_to_search"):
            if len(formatted_items) > 0:
                recommended = random.sample(formatted_items, min(3, len(formatted_items)))
                cards_html = "<div style='margin-top:15px; display:flex; flex-direction:column; gap:10px;'>"
                for it in recommended:
                    price_str = f"월세 {it.get('deposit', 0)}/{it.get('price', 0)}" if it.get('rent_type') == '월세' else f"전세 {it.get('price', 0)}"
                    cards_html += f"""
                    <div style='background:#f1f2f6; border:1px solid #e2e8f0; padding:15px; border-radius:12px; font-size:0.95rem;'>
                        <div style='font-weight:900; margin-bottom:5px; color:#111;'>📍 {it.get('address', '주소 없음')}</div>
                        <div style='color:#4facfe; font-weight:800; margin-bottom:10px;'>💰 {price_str}</div>
                        <button onclick="focusPropertyFromChat('{str(it['_id'])}')" style='background:#111; color:#fff; border:none; padding:8px 12px; border-radius:8px; cursor:pointer; width:100%; font-weight:bold; transition:0.2s;'>상세정보 보기</button>
                    </div>
                    """
                cards_html += "</div>"
                reply_html += cards_html
                show_reset = True
            else:
                reply_html += "<br><br><span style='color:#e03131; font-weight:bold;'>😥 원하시는 조건에 맞는 매물이 아직 없네요. 조건을 조금만 완화해 보시겠어요?</span>"
                show_reset = True
            
        return jsonify({
            "status": "success",
            "reply": reply_html,
            "items": formatted_items,
            "updated_state": parsed,
            "show_reset": show_reset
        })
        
    except Exception as e:
        import traceback
        print("=== [AI 챗봇 에러 발생] ===")
        print("LLM이 뱉은 날것의 데이터:", raw_content)
        print("에러 상세 내용:", traceback.format_exc())
        return jsonify({
            "status": "error", 
            "reply": "앗, 조건을 검색하는 중에 일시적인 서버 오류가 발생했어요. 다시 한번 시도해 주시겠어요?", 
            "items": [],
            "updated_state": current_state, 
            "show_reset": False
        })