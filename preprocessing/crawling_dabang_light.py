import time
import json
import os
from datetime import datetime
from multiprocessing import Pool, freeze_support
from seleniumwire import webdriver
from seleniumwire.utils import decode as sw_decode
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# [설정]
MAX_PAGES_PER_GU = 1
NUM_PROCS = 1 # 안정성을 위해 일단 1로 권장
TARGET_GUS = ["강남구", "강서구", "관악구", "동작구", "마포구", "영등포구"] # 테스트용

def create_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    # selenium-wire 기본 설정
    driver = webdriver.Chrome(options=options)
    driver.scopes = ['.*api/3/room/list.*']
    return driver

def crawl_worker(gu_sublist):
    driver = create_driver()
    save_dir = "result_json_structured"
    if not os.path.exists(save_dir): os.makedirs(save_dir)
    
    try:
        driver.get("https://www.dabangapp.com/map/apt")
        time.sleep(7) # 초기 로딩 시간 확보

        for gu in gu_sublist:
            gu_results = []
            print(f"\n[*] {gu} 수집 시작...")
            
            try:
                # 구 클릭
                btn = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, f"//*[text()='{gu}']")))
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(5)

                page_num = 1
                while True:
                    found_in_page = False
                    # 응답 확인 (10초 대기)
                    for _ in range(10):
                        for request in list(driver.requests):
                            if request.response and 'api/3/room/list' in request.url:
                                try:
                                    body = sw_decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity'))
                                    data = json.loads(body.decode('utf-8'))
                                    rooms = data.get('result', {}).get('roomList', [])
                                    
                                    if rooms:
                                        for r in rooms:
                                            # 복잡한 필터링 제거, 있는 그대로 담기
                                            gu_results.append({
                                                "address": [gu, r.get('dongName', ''), ""], # 요청하신 리스트 구조
                                                "location": [r.get('randomLocation', {}).get('lat'), r.get('randomLocation', {}).get('lng')],
                                                "rent_type": r.get('priceTypeName'),
                                                "deposit": r.get('priceTitle').split('/')[0] if '/' in r.get('priceTitle') else r.get('priceTitle'),
                                                "price": r.get('priceTitle').split('/')[1] if '/' in r.get('priceTitle') else "0",
                                                "images": r.get('imgUrl'),
                                                "roomCount": r.get('roomTypeName'),
                                                "size": r.get('roomDesc'),
                                                "hasParking": "확인필요",
                                                "options": r.get('roomTitle'),
                                                "buildingUse": r.get('roomTypeName'),
                                                "floor": r.get('roomDesc').split(',')[0] if r.get('roomDesc') else ""
                                            })
                                        found_in_page = True
                                        break
                                except: continue
                        if found_in_page: break
                        time.sleep(1)

                    if found_in_page:
                        print(f"    -> {page_num}P 완료")
                        del driver.requests # 가로챈 기록 비우기
                    else:
                        print(f"    -> {page_num}P 누락/데이터없음")

                    # 다음 페이지 버튼 찾기
                    try:
                        next_btn = driver.find_element(By.XPATH, "//button[@aria-label='다음 페이지']")
                        if "disabled" in next_btn.get_attribute("class") or next_btn.get_attribute("disabled"): break
                        driver.execute_script("arguments[0].click();", next_btn)
                        page_num += 1
                        time.sleep(3)
                    except: break

                # 파일 저장
                if gu_results:
                    with open(f"{save_dir}/dabang_{gu}.json", 'w', encoding='utf-8') as f:
                        json.dump(gu_results, f, ensure_ascii=False, indent=4)
                
                # 리셋 후 다음 구로
                driver.get("https://www.dabangapp.com/map/apt")
                time.sleep(5)

            except Exception as e:
                print(f"    ! {gu} 오류: {e}")
                driver.get("https://www.dabangapp.com/map/apt"); time.sleep(5)
                
    finally:
        driver.quit()

if __name__ == "__main__":
    freeze_support()
    chunks = [TARGET_GUS[i::NUM_PROCS] for i in range(NUM_PROCS)]
    with Pool(processes=NUM_PROCS) as pool:
        pool.map(crawl_worker, chunks)