from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import houses_col, db
from bson.objectid import ObjectId
from datetime import datetime
from collections import Counter
import os
from dotenv import load_dotenv 
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# ------------------------------------------------------------------
# 환경변수 로드 및 GPT 초기화
# ------------------------------------------------------------------
load_dotenv(override=True)
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    api_key = api_key.strip()
    print(f"🔑 [최종 로드된 키] 끝자리 확인: ...{api_key[-4:]}")
else:
    print("❌ .env 파일을 찾을 수 없거나 비어있습니다!")

try:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, openai_api_key=api_key)
    print("✅ GPT 모델 초기화 성공")
except Exception as e:
    print(f"❌ GPT 초기화 실패: {e}")

# ------------------------------------------------------------------
# Blueprint
# ------------------------------------------------------------------
survey_bp = Blueprint('survey', __name__, template_folder='.')

# 카테고리 매핑
category_map = {
    "traffic": "교통", "convenience": "편의", "green": "녹지",
    "play": "놀이", "health": "건강", "living": "생활", "safety": "안전"
}

# ------------------------------------------------------------------
# AI 추천 사유 생성 함수
# ------------------------------------------------------------------
def generate_recommendation_reason(user_weights, house_info):
    sorted_weights = sorted(user_weights.items(), key=lambda x: x[1], reverse=True)
    top_interests = [category_map.get(k,k) for k,_ in sorted_weights[:2]]

    scores = house_info.get('scores', {})
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_strengths = [f"{category_map.get(k.lower(),k)}({int(v*100)}점)" for k,v in sorted_scores[:2]]

    template = """
    당신은 전문 부동산 컨설턴트입니다. 
    사용자의 선호도와 매물의 데이터를 분석하여, 이 집을 추천하는 이유를 **한 문장으로** 매력 있게 작성해주세요.
    
    [사용자 선호]
    - 중요 가치: {top_interests}
    
    [매물 정보]
    - 주소: {address}
    - 가격: {price}
    - 핵심 강점: {top_strengths}
    
    [작성 가이드]
    - "~하기 때문에 고객님께 딱 맞는 매물입니다" 또는 "~한 점이 매력적입니다" 같은 말투를 사용하세요.
    - 공백 포함 80자 이내로 짧게 요약하세요.
    - 너무 기계적인 말투는 피하세요.
    """
    
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm
    try:
        response = chain.invoke({
            "top_interests": ", ".join(top_interests),
            "address": house_info['address'],
            "price": house_info['price_display'],
            "top_strengths": ", ".join(top_strengths)
        })
        return response.content
    except Exception as e:
        print(f"GPT 호출 에러: {e}")
        return "데이터를 기반으로 딱 맞는 집을 찾았습니다!"

# ------------------------------------------------------------------
# 설문 저장
# ------------------------------------------------------------------
@survey_bp.route('/survey/save', methods=['POST'])
def save_survey():
    if 'user_id' not in session:
        return jsonify({"status":"error","message":"로그인이 필요한 서비스입니다."}),401

    user_id = session['user_id']
    data = request.get_json()
    if not data:
        return jsonify({"status":"error","message":"전송된 데이터가 없습니다."}),400

    budget_raw = data.get('budget',{})
    new_survey = {
        "user_id": user_id,
        "location": data.get('location',""),
        "contract_type": data.get('contract_type',""),
        "budget": {
            "min_dep": int(budget_raw.get('min_dep',0)),
            "max_dep": int(budget_raw.get('max_dep',0)),
            "min_rent": int(budget_raw.get('min_rent',0)),
            "max_rent": int(budget_raw.get('max_rent',0))
        },
        "category_log": data.get('category_log',[]),
        "created_at": datetime.now()
    }

    surveys = list(db.survey_results.find({"user_id":user_id}).sort("created_at",-1))
    if len(surveys) >= 3:
        db.survey_results.delete_one({"_id": surveys[-1]['_id']})

    db.survey_results.insert_one(new_survey)
    return jsonify({"status":"success","target_index":0})

# ------------------------------------------------------------------
# 추천 매물 가공 함수
# ------------------------------------------------------------------
def get_matched_properties(survey):
    total_counts = {'traffic':6,'convenience':10,'green':7,'play':6,'health':6,'living':13,'safety':10}
    user_log = survey.get('category_log',[])
    log_counts = Counter(user_log)
    raw_weights = {cat:(log_counts.get(cat,0)+1)/total for cat,total in total_counts.items()}
    sum_raw = sum(raw_weights.values())
    user_weights = {k:v/sum_raw for k,v in raw_weights.items()}

    # 쿼리
    query = {}
    loc = survey.get('location')
    if loc and loc.strip(): query['address'] = {"$regex": loc}
    c_type = survey.get('contract_type')
    mapping = {"jeonse":"전세","monthly":"월세"}
    target_rent_type = mapping.get(c_type,c_type)
    if c_type: query['rent_type'] = target_rent_type

    budget = survey.get('budget',{})
    min_dep,max_dep = budget.get('min_dep',0), budget.get('max_dep',0)
    min_rent,max_rent = budget.get('min_rent',0), budget.get('max_rent',0)

    if target_rent_type=="전세":
        price_q = {}
        if min_dep>0: price_q["$gte"]=min_dep
        if max_dep>0: price_q["$lte"]=max_dep
        if price_q: query['price']=price_q
    else:
        dep_q,rent_q={},{}
        if min_dep>0: dep_q["$gte"]=min_dep
        if max_dep>0: dep_q["$lte"]=max_dep
        if min_rent>0: rent_q["$gte"]=min_rent
        if max_rent>0: rent_q["$lte"]=max_rent
        if dep_q: query['deposit']=dep_q
        if rent_q: query['price']=rent_q

    houses = list(houses_col.find(query).limit(500))
    if len(houses)<5:
        relaxed_query={}
        if loc and loc.strip(): relaxed_query['address']={"$regex": loc}
        if c_type: relaxed_query['rent_type']=target_rent_type
        houses=list(houses_col.find(relaxed_query).limit(100))

    # 가공
    matched=[]
    for house in houses:
        scores=house.get('category_scores',{})
        score=sum(scores.get(cat,0)*user_weights.get(cat,0) for cat in total_counts.keys())
        house['match_score']=round(score*100,1)
        house['_id_str']=str(house['_id'])

        rent_type=house.get('rent_type')
        main_price=house.get('price',0)
        if rent_type=="전세":
            house['price_display']=f"{main_price}"
        else:
            dep_amount=house.get('deposit',0)
            house['price_display']=f"{dep_amount}/{main_price}"
        house['sort_key']=main_price

        imgs=house.get('images',[])
        if imgs and imgs[0]:
            house['main_image']=imgs[0]+('&w=800' if '?' in imgs[0] else '?w=800')
        else:
            house['main_image']=url_for('static', filename='img/default_room.jpg')
        matched.append(house)

    matched=sorted(matched,key=lambda x:(-x['match_score'],x['sort_key']))[:10]
    top_3=matched[:3]
    others=matched[3:]

    for house in top_3:
        try:
            info={"address":house['address'],"price_display":house['price_display'],"scores":house.get('category_scores',{})}
            house['ai_comment']=generate_recommendation_reason(user_weights,info)
        except:
            house['ai_comment']="고객님의 라이프스타일에 최적화된 추천 매물입니다."

    return top_3, others

# ------------------------------------------------------------------
# 쇼츠 라우트
# ------------------------------------------------------------------
@survey_bp.route('/survey/short/<int:index>')
def survey_short(index):
    if 'user_id' not in session:
        return "<script>alert('로그인이 필요한 서비스입니다.'); window.location.href='/login';</script>"

    user_id=session['user_id']
    surveys=list(db.survey_results.find({"user_id":user_id}).sort("created_at",-1))
    if not surveys or index>=len(surveys):
        return "<script>alert('해당 설문 내역이 없습니다.'); window.location.href='/mypage';</script>"

    top_3,others=get_matched_properties(surveys[index])
    return render_template('shorts.html', recommendations=top_3+others)

# ------------------------------------------------------------------
# 결과 페이지 라우트
# ------------------------------------------------------------------
@survey_bp.route('/survey/result/<int:index>')
def survey_result(index):
    if 'user_id' not in session:
        return "<script>alert('로그인이 필요한 서비스입니다.'); window.location.href='/login';</script>"

    user_id=session['user_id']
    surveys=list(db.survey_results.find({"user_id":user_id}).sort("created_at",-1))
    if not surveys or index>=len(surveys):
        return "<script>alert('해당 설문 내역이 없습니다.'); window.location.href='/mypage';</script>"

    top_3,others=get_matched_properties(surveys[index])
    return render_template('result.html', survey=surveys[index], top_3=top_3, others=others, current_index=index, survey_id=str(surveys[index]['_id']))