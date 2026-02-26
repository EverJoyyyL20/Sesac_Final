import os
import json
import re 
import random
from flask import Blueprint, render_template, current_app, request, jsonify, session
from datetime import datetime
from database import houses_col, db, users_col
from bson.objectid import ObjectId

# 🔥 [챗봇 병합] LLM 모듈 추가
from dotenv import load_dotenv 
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

load_dotenv(override=True)

# ------------------------------------------------------------------
# 🔥 [챗봇 병합] AI 모델 초기화
# ------------------------------------------------------------------
api_key = os.getenv("OPENAI_API_KEY")
try:
    llm = ChatOpenAI(model="gpt-5.2", temperature=0.0, openai_api_key=api_key)
    print("✅ Find Property GPT 모델 초기화 성공 (gpt-5.2)")
except Exception as e:
    print(f"❌ GPT 초기화 실패: {e}")
    llm = None

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
        radius_in_radians = radius_m / 6378100
        query["location"] = {
            "$geoWithin": {
                "$centerSphere": [[center_lng, center_lat], radius_in_radians]
            }
        }

    rent_type = request.args.get('type')
    if rent_type: query["rent_type"] = rent_type

    rooms_param = request.args.get('rooms')
    if rooms_param:
        room_list = rooms_param.split(',')
        room_conditions = []
        for r in room_list:
            r = r.strip()
            if r == '원룸':
                room_conditions.append({"room_counts": "1개"})
            elif r == '투룸':
                room_conditions.append({"room_counts": "2개"})
            elif r in ['쓰리룸+', '쓰리룸']:
                room_conditions.append({"room_counts": {"$regex": "[3-9]|[1-9][0-9]"}})
        
        if room_conditions:
            query.setdefault("$and", []).append({"$or": room_conditions})

    min_dep = request.args.get('min_deposit', type=int)
    max_dep = request.args.get('max_deposit', type=int)
    min_pri = request.args.get('min_price', type=int)
    max_pri = request.args.get('max_price', type=int)

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

    # 🔥 [팀원 코드 유지] 옵션 여부 필터
    option_status = request.args.get('option_status')
    if option_status == '있음':
        query['options'] = {"$exists": True, "$not": {"$size": 0}}
    elif option_status == '없음':
        query['$or'] = [
            {'options': {"$exists": False}},
            {'options': {"$size": 0}}
        ]

    items = list(houses_col.find(query).limit(300))
    return jsonify([{**item, "_id": str(item['_id'])} for item in items])

# =====================================================================
# 🔥 [챗봇 병합] AI 자연어 검색 (단기 기억상실 완벽 차단 & 매물 포커스)
# =====================================================================
@find_bp.route('/api/chat_search', methods=['POST'])
def chat_search():
    if not llm:
        return jsonify({"status": "error", "reply": "현재 AI 서버 점검 중입니다. 일반 검색을 이용해주세요."})

    data = request.get_json()
    user_query = data.get('query', '')
    current_state = data.get('current_state', {})
    
    if not user_query:
        return jsonify({"status": "error", "reply": "검색하실 조건을 입력해주세요!"})

    nickname = session.get('nickname', '고객')

    template = """당신은 상위 1% VIP를 전담하는 친절하고 똑똑한 부동산 AI 챗봇입니다.
    가장 중요한 임무는 사용자가 알려준 조건을 [기존 누적 조건]에 계속 병합(업데이트)하여 필터를 완성하는 것입니다.

    [⭐⭐⭐ 기억 상실 방지 및 업데이트 절대 규칙 ⭐⭐⭐]
    1. [기존 누적 조건]에 이미 값이 들어있다면, 사용자가 "바꿔줘", "상관없어", "취소해줘"라고 지우지 않는 한 **절대 지우지 말고 무조건 그대로 복사**하여 출력 JSON에 유지하세요! (기존 조건 보존율 100% 필수)
    2. 사용자가 기존 조건을 변경하면(예: "2억 말고 1.5억으로"), 기존 값을 덮어쓰세요.
    3. 사용자가 새로운 조건을 추가하면(예: "방 2개로 해줘"), 기존 조건에 추가하세요.
    4. 이미 파악된 필수 조건(지역, 예산 등)을 또다시 물어보는 바보 같은 행동은 절대 금지합니다.
    5. 지역(location)과 예산(max_deposit 등)이 파악되었거나, 사용자가 "추천해줘", "알려줘"라고 요구하면 무조건 `"is_complete": true`로 설정하세요.

    [기존 누적 조건] (이 값을 베이스로 깔고 시작하세요)
    {current_state}

    [현재 질문]
    {query}

    출력은 오직 아래 JSON 형식으로만 작성하세요. (설명 텍스트 절대 금지)
    {{
        "location": "지역명 (예: 도봉구. 기존에 있으면 유지, 변경 시 수정, 모르면 null)",
        "rent_type": "전세 또는 월세 (기존 유지/변경, 모르면 null)",
        "max_deposit": 최대 보증금/전세금 (만원 단위 정수. 예: 2억->20000. 기존 유지/변경, 모르면 null),
        "max_rent": 최대 월세 (만원 단위 정수. 예: 60만원->60. 기존 유지/변경, 모르면 null),
        "room_count": 방 개수 (1, 2, 3 중 하나. 무관하면 null),
        "parking": 주차 필요 여부 (필요하면 true, 무관/모르면 false),
        "is_complete": true 또는 false,
        "reply_msg": "안내 멘트 (HTML <br><br> 적극 활용)"
    }}

    [reply_msg 작성 가이드]
    1. 호칭: "{nickname}님"을 사용하여 친근하게 대답하세요.
    2. 상태 확인 멘트: "현재 파악된 조건(예: 도봉구, 전세 2억 이하, 방 2개)을 바탕으로 찾아볼게요!"라며 기억하고 있음을 어필하세요.
    3. "is_complete": true인 경우, 추가 질문 없이 바로 매물을 보여준다는 멘트로 마무리하세요.
    4. "is_complete": false인 경우, 아직 비어있는(null) 핵심 조건만 콕 집어서 질문하세요.
    """
    
    try:
        prompt = PromptTemplate.from_template(template)
        chain = prompt | llm
        res = chain.invoke({
            "query": user_query, 
            "nickname": nickname, 
            "current_state": json.dumps(current_state, ensure_ascii=False)
        })
        
        raw_content = res.content.strip()
        raw_content = raw_content.replace("```json", "").replace("```", "").strip()
        
        match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        if match:
            raw_json = match.group(0)
        else:
            raw_json = raw_content
            
        parsed = json.loads(raw_json)
        
        db_query = {}
        
        loc = parsed.get("location")
        if loc:
            db_query["address"] = {"$regex": loc}
            
        r_type = parsed.get("rent_type")
        if r_type:
            db_query["rent_type"] = r_type
            
        max_dep = parsed.get("max_deposit")
        max_rent = parsed.get("max_rent")
        
        if r_type == '전세':
            if max_dep:
                db_query["price"] = {"$lte": int(max_dep)}
        elif r_type == '월세':
            if max_dep:
                db_query["deposit"] = {"$lte": int(max_dep)}
            if max_rent:
                db_query["price"] = {"$lte": int(max_rent)}
        else:
            if max_dep:
                db_query["deposit"] = {"$lte": int(max_dep)}
            if max_rent:
                db_query["price"] = {"$lte": int(max_rent)}
                
        r_count = parsed.get("room_count")
        if str(r_count) == "1":
            db_query["room_counts"] = "1개"
        elif str(r_count) == "2":
            db_query["room_counts"] = "2개"
        elif str(r_count) == "3":
            db_query["room_counts"] = {"$regex": "[3-9]|[1-9][0-9]"}
            
        parking_val = parsed.get("parking")
        if parking_val is True or str(parking_val).lower() == "true":
            db_query["hasParking"] = "주차 가능"
            
        items = list(houses_col.find(db_query).limit(100))
        
        formatted_items = []
        for item in items:
            formatted_items.append({**item, "_id": str(item['_id'])})

        reply_html = parsed.get("reply_msg", f"{nickname}님! 누적된 조건으로 검색 중입니다.")
        show_reset = False

        if parsed.get("is_complete") and len(formatted_items) > 0:
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
            
        elif parsed.get("is_complete") and len(formatted_items) == 0:
            reply_html += "<br><br>😥 죄송합니다. 원하시는 조건에 맞는 매물이 아직 없네요. 조건을 조금 완화해 보시겠어요?"
            show_reset = True
            
        updated_state = {
            "location": parsed.get("location"),
            "rent_type": parsed.get("rent_type"),
            "max_deposit": parsed.get("max_deposit"),
            "max_rent": parsed.get("max_rent"),
            "room_count": parsed.get("room_count"),
            "parking": parsed.get("parking")
        }
            
        return jsonify({
            "status": "success",
            "reply": reply_html,
            "items": formatted_items,
            "updated_state": updated_state,
            "show_reset": show_reset
        })
        
    except Exception as e:
        import traceback
        print("Chat Search Error:", traceback.format_exc())
        return jsonify({
            "status": "error", 
            "reply": "앗, 조건을 분석하는 중에 일시적인 오류가 발생했어요. 다시 한번 입력해 주시겠어요?", 
            "items": [],
            "updated_state": current_state, 
            "show_reset": False
        })