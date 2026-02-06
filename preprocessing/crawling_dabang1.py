import time
import json
import os
from multiprocessing import Pool, freeze_support
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# [설정 구역]
SEOUL_GU_LIST = [
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", 
    "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", 
    "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", 
    "종로구", "중구", "중랑구"
]

def create_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # 이미지 차단으로 속도 향상 (상세 정보 텍스트 수집 위주)
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

def get_detailed_info(driver, gu):
    """이미지 구조 반영: 가격 및 주소 추출"""
    item = {
        "address": [gu, "", ""], # [구, 동, 상세주소(공란)]
        "price_info": {"rent_type": "", "deposit": "", "price": ""},
        "details": {}
    }
    
    try:
        # 상세창 루트 요소 대기
        root = WebDriverWait(driver, 7).until(EC.presence_of_element_located((By.ID, "container-room-root")))
        full_text = root.text
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]

        # 1. 가격 정보 추출 (보내주신 이미지의 '월세', '200/175' 구조 파싱)
        for i, line in enumerate(lines):
            if line in ["월세", "전세"]:
                item["price_info"]["rent_type"] = line
                try:
                    price_val = lines[i+1] # 바로 다음 줄에 가격 정보 위치
                    if "/" in price_val:
                        dep, prc = price_val.split("/")
                        item["price_info"]["deposit"] = dep.strip()
                        item["price_info"]["price"] = prc.strip()
                    else:
                        item["price_info"]["deposit"] = price_val.strip()
                        item["price_info"]["price"] = "0"
                except: pass
                break

        # 2. 동 이름 추출 (주소 섹션 텍스트에서 'XX동' 찾기)
        for line in lines:
            if gu in line and "동" in line:
                parts = line.split()
                for p in parts:
                    if p.endswith("동"):
                        item["address"][1] = p
                        break
                if item["address"][1]: break

    except Exception as e:
        print(f"      ! 파싱 실패: {e}")
        
    return item

def crawl_worker(data_pack):
    gu_sublist, max_pages = data_pack
    driver = create_driver()
    save_dir = "result_json_final"
    if not os.path.exists(save_dir):
        try: os.makedirs(save_dir)
        except: pass

    try:
        driver.get("https://www.dabangapp.com/map/apt")
        time.sleep(5)

        for gu in gu_sublist:
            gu_results = []
            print(f"\n[*] {gu} 수집 시작 (페이지 제한: {max_pages if max_pages > 0 else '무제한'})")
            
            try:
                # 구 선택
                gu_btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, f"//*[text()='{gu}']")))
                driver.execute_script("arguments[0].click();", gu_btn)
                time.sleep(5)

                current_page = 1
                while True:
                    cards = driver.find_elements(By.XPATH, "//div[@id='apt-list']//li")
                    print(f"    -> {current_page}P 매물 {len(cards)}개 순회 중...")
                    
                    for i in range(len(cards)):
                        try:
                            # 리스트 갱신 대응
                            cards = driver.find_elements(By.XPATH, "//div[@id='apt-list']//li")
                            card = cards[i]
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
                            time.sleep(0.7)
                            driver.execute_script("arguments[0].click();", card)
                            
                            # 상세 데이터 수집
                            gu_results.append(get_detailed_info(driver, gu))
                            
                            # 상세창 닫기
                            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                            time.sleep(0.5)
                        except:
                            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                            continue
                    
                    # 페이지 제한 체크
                    if max_pages > 0 and current_page >= max_pages: break

                    # 다음 페이지 버튼
                    try:
                        next_btn = driver.find_element(By.XPATH, "//button[@aria-label='다음 페이지']")
                        if "disabled" in next_btn.get_attribute("class") or not next_btn.is_enabled(): break
                        driver.execute_script("arguments[0].click();", next_btn)
                        current_page += 1
                        time.sleep(3)
                    except: break
                
                # 구별 파일 즉시 저장
                if gu_results:
                    file_path = f"{save_dir}/dabang_{gu}.json"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(gu_results, f, ensure_ascii=False, indent=4)
                    print(f" ✅ {gu} 완료 ({len(gu_results)}건)")

            except Exception as e:
                print(f" ⚠️ {gu} 오류 발생: {e}")
                driver.get("https://www.dabangapp.com/map/apt")
                time.sleep(5)
                
    finally:
        driver.quit()

def divide_chunks(l, n):
    for i in range(0, len(l), n): yield l[i:i + n]

if __name__ == "__main__":
    freeze_support()
    
    # ------------------------------------------
    # 여기서 설정 변경
    # ------------------------------------------
    NUM_PROCS = 8            # 병렬 프로세스 개수
    MAX_PAGES_PER_GU = 100     # 구별 수집할 페이지 수 (0은 전체)
    # ------------------------------------------

    chunks = list(divide_chunks(SEOUL_GU_LIST, (len(SEOUL_GU_LIST) + NUM_PROCS - 1) // NUM_PROCS))
    work_params = [(chunk, MAX_PAGES_PER_GU) for chunk in chunks]
    
    print(f"🚀 서울 전역 매물 수집을 시작합니다. (프로세스: {NUM_PROCS})")
    with Pool(processes=NUM_PROCS) as pool:
        pool.map(crawl_worker, work_params)
    print("\n🏁 모든 수집 작업이 종료되었습니다.")