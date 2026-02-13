import numpy as np
from pymongo import MongoClient
from urllib.parse import quote_plus
from math import radians, cos, sin, asin, sqrt

# MongoDB 연결
user = "JS"
password = quote_plus("Z26SdTRgqMadKJST")
cluster_url = "cluster0.qpamvvh.mongodb.net"
uri = f"mongodb+srv://{user}:{password}@{cluster_url}/sesac_final?retryWrites=true&w=majority"

client = MongoClient(uri)
db = client['sesac_final']

house_col = db['properties_test3']
poi_col = db['infra']

poi_col.create_index([("location", "2dsphere")])

def get_nearby_pois(lng, lat, radius=1000):
    pipeline = [
        {
            "$geoNear": {
                "near": {
                    "type": "Point",
                    "coordinates": [lng, lat]
                },
                "distanceField": "distance",
                "maxDistance": radius,
                "spherical": True
            }
        },
        {
            "$project": {
                "_id": 0,
                "name": 1,
                "category": 1,
                "sub_category": 1,
                "distance": 1
            }
        }
    ]

    pois = list(poi_col.aggregate(pipeline))  # ⭐ 여기 수정
    return pois

house_lng = 127.0365
house_lat = 37.5013

nearby_pois = get_nearby_pois(house_lng, house_lat)

def init_raw_scores():
    return {
        "traffic": 0,
        "convenience": 0,
        "green": 0,
        "play": 0,
        "health": 0,
        "living": 0,
        "safety": 0
    }

def calc_traffic_score(pois, raw_scores):
    for poi in pois:
        if poi["category"] != "traffic":
            continue

        dist = poi["distance"]
        sub = poi["sub_category"]

        # 🚇 지하철
        if sub == "subway":
            if dist <= 500:
                raw_scores["traffic"] += 100
            elif dist <= 1000:
                raw_scores["traffic"] += 20

        # 🚌 버스정류장
        elif sub == "bus_stop":
            if dist <= 300:
                raw_scores["traffic"] += 4

    return raw_scores


def calc_convenience_score(pois, raw_scores):
    for poi in pois:
        if poi["category"] != "convenience":
            continue

        dist = poi["distance"]
        sub = poi["sub_category"]

        if sub == "large_mart" and dist <= 1000:
            raw_scores["convenience"] += 75

        elif sub == "convenience_store" and dist <= 300:
            raw_scores["convenience"] += 15

    return raw_scores


def calc_green_score(pois, raw_scores):
    for poi in pois:
        if poi["category"] != "green":
            continue

        dist = poi["distance"]
        sub = poi["sub_category"]

        if sub == "river" and dist <= 1000:
            raw_scores["green"] += 100

        elif sub == "park":
            if dist <= 500:
                raw_scores["green"] += 40
            elif dist <= 1000:
                raw_scores["green"] += 20

        elif sub == "mountain" and dist <= 1000:
            raw_scores["green"] += 30

    return raw_scores

def calc_play_score(pois, raw_scores):
    for poi in pois:
        if poi["category"] != "play":
            continue

        if poi["distance"] <= 500:
            raw_scores["play"] += 30

    return raw_scores

def calc_health_score(pois, raw_scores):
    for poi in pois:
        if poi["category"] != "health":
            continue

        dist = poi["distance"]
        sub = poi["sub_category"]

        if sub == "hospital" and dist <= 1000:
            raw_scores["health"] += 15

        elif sub == "clinic" and dist <= 300:
            raw_scores["health"] += 0.3

    return raw_scores

def calc_living_score(pois, raw_scores):
    for poi in pois:
        if poi["category"] != "living":
            continue

        dist = poi["distance"]
        sub = poi["sub_category"]

        if sub == "bank" and dist <= 500:
            raw_scores["living"] += 30

        elif sub == "public_library" and dist <= 1000:
            raw_scores["living"] += 20

        elif sub == "library" and dist <= 500:
            raw_scores["living"] += 10

    return raw_scores

def calc_safety_score(pois, raw_scores):
    for poi in pois:
        if poi["category"] != "safety":
            continue

        dist = poi["distance"]
        sub = poi["sub_category"]

        if sub == "police" and dist <= 1000:
            raw_scores["safety"] += 50

        elif sub == "police_substation" and dist <= 500:
            raw_scores["safety"] += 25

    return raw_scores

raw_scores = init_raw_scores()
raw_scores = calc_traffic_score(nearby_pois, raw_scores)
raw_scores = calc_convenience_score(nearby_pois, raw_scores)
raw_scores = calc_green_score(nearby_pois, raw_scores)
raw_scores = calc_play_score(nearby_pois, raw_scores)
raw_scores = calc_health_score(nearby_pois, raw_scores)
raw_scores = calc_living_score(nearby_pois, raw_scores)
raw_scores = calc_safety_score(nearby_pois, raw_scores)

print(raw_scores)


CATEGORY_CAP = {
    "traffic": 120,
    "convenience": 150,
    "green": 100,
    "play": 150,
    "health": 200,
    "living": 200,
    "safety": 50
}

MIN_SCORE = 0.05   # 🔥 floor 값
def normalize_category_scores(raw_scores):
    """
    raw_scores → 0~1 범위 category_scores 변환
    floor(최소값) 적용 버전
    """

    category_scores = {}

    for category in CATEGORY_CAP.keys():
        raw = raw_scores.get(category, 0)  # 혹시 누락 대비
        cap = CATEGORY_CAP[category]

        # 1️⃣ CAP 기준 비율 계산
        score = raw / cap

        # 2️⃣ 상한 제한 (1 초과 방지)
        score = min(score, 1)

        # 3️⃣ 하한 제한 (0 방지) ⭐ 핵심
        score = max(score, MIN_SCORE)

        # 4️⃣ 반올림 저장
        category_scores[category] = round(score, 4)

    return category_scores

category_scores = normalize_category_scores(raw_scores)
print(category_scores)

def process_all_houses():
    houses = list(house_col.find({}))
    total = len(houses)

    print(f"총 매물 수: {total}")

    for idx, house in enumerate(houses, 1):
        try:
            # 1️⃣ 좌표 가져오기
            loc = house.get("location")
            if not loc:
                print(f"[{idx}/{total}] 좌표 없음 → 스킵")
                continue

            lng, lat = loc["coordinates"]

            # 2️⃣ 주변 POI 조회
            nearby_pois = get_nearby_pois(lng, lat)

            # 3️⃣ raw 점수 계산
            raw_scores = init_raw_scores()
            raw_scores = calc_traffic_score(nearby_pois, raw_scores)
            raw_scores = calc_convenience_score(nearby_pois, raw_scores)
            raw_scores = calc_green_score(nearby_pois, raw_scores)
            raw_scores = calc_play_score(nearby_pois, raw_scores)
            raw_scores = calc_health_score(nearby_pois, raw_scores)
            raw_scores = calc_living_score(nearby_pois, raw_scores)
            raw_scores = calc_safety_score(nearby_pois, raw_scores)

            # 4️⃣ 정규화
            category_scores = normalize_category_scores(raw_scores)

            # 5️⃣ MongoDB 업데이트 (덮어쓰기)
            house_col.update_one(
                {"_id": house["_id"]},
                {
                    "$set": {
                        "raw_scores": raw_scores,
                        "category_scores": category_scores
                    }
                }
            )

            print(f"[{idx}/{total}] 완료")

        except Exception as e:
            print(f"[{idx}/{total}] 오류:", e)

    print("🎉 모든 매물 처리 완료!")

process_all_houses()


# 🔍 업데이트 확인용 테스트 코드
print("\n--- 실제 DB 데이터 확인 ---")
test_house = house_col.find_one({"raw_scores": {"$exists": True}})
if test_house:
    print("✅ 업데이트된 데이터를 찾았습니다!")
    print(f"매물명: {test_house.get('name', '이름없음')}")
    print(f"Raw 점수: {test_house.get('raw_scores')}")
    print(f"정규화 점수: {test_house.get('category_scores')}")
else:
    print("❌ 업데이트된 데이터가 DB에 하나도 없습니다.")