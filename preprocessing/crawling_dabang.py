import time
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# 서울시 구 리스트
SEOUL_GU_LIST = ["강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구"]

def create_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    # 이미지 로딩 차단
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    return driver

def perform_zoom_out_safe(driver):
    """상세창 간섭 회피를 위해 오른쪽 이동 후 줌아웃"""
    try:
        # 지도 요소 대기
        map_area = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "map")))
        
        # 상세창(왼쪽)을 피해 오른쪽으로 400픽셀 이동 후 클릭하여 포커스
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(map_area, 400, 0).click().perform()
        time.sleep(1)
        
        # 키보드 '-' 키 입력 (넘패드와 일반 키 둘 다 시도)
        for _ in range(3):
            actions.send_keys("-").perform()
            time.sleep(0.8)
        print("   🔍 지도 줌아웃 완료")
    except Exception as e:
        print(f"   ⚠️ 줌아웃 실패: {e}")

def get_detailed_info(driver):
    """상세 정보 추출 (가격, 관리비, 주소 등)"""
    info = {}
    try:
        root_element = driver.find_element(By.ID, "container-room-root")
        root_text = root_element.text
        rid = re.search(r"매물번호\s*[:\s]*(\d+)", root_text)
        prc = re.search(r"(전세|월세|매매)\s*([\d,./억\s]+)", root_text)
        info["매물번호"] = rid.group(1) if rid else "미확인"
        info["가격"] = prc.group(0).strip() if prc else "미확인"

        # 상세정보 섹션 수집
        detail_items = driver.find_elements(By.XPATH, "//section[@data-scroll-spy-element='detail-info']//ul/li")
        for item in detail_items:
            txt_parts = item.text.strip().split('\n')
            if len(txt_parts) >= 2:
                info[txt_parts[0].strip()] = txt_parts[1].strip()

        # 주소 수집
        try:
            info["주소"] = driver.find_element(By.XPATH, "//section[@data-scroll-spy-element='near']//p").text.strip()
        except: info["주소"] = "주소미확인"
    except: pass
    return info

def crawl_dabang():
    driver = create_driver()
    FINAL_DATA = []
    
    try:
        driver.get("https://www.dabangapp.com/")
        main_window = driver.current_window_handle # 메인 창 저장
        time.sleep(3)

        # 1. 아파트 메뉴 클릭 (새 탭으로 열리는 경우 대응)
        apt_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), '아파트')] | //p[text()='아파트']"))
        )
        apt_btn.click()
        time.sleep(3)

        # 새 창(탭)이 열렸는지 확인하고 핸들 전환
        all_windows = driver.window_handles
        for handle in all_windows:
            if handle != main_window:
                driver.switch_to.window(handle)
                print("✅ 새 탭으로 포커스 전환 완료")
                break

        # 2. 줌아웃 (서울 전체 구가 보이도록)
        perform_zoom_out_safe(driver)

        for gu in SEOUL_GU_LIST:
            print(f"\n🚀 {gu} 작업 시작")
            ActionChains(driver).send_keys(Keys.ESCAPE).perform() # 열린 상세창 닫기
            time.sleep(1)

            # 3. 지도 위 구 이름 클릭
            try:
                gu_label = WebDriverWait(driver, 7).until(
                    EC.element_to_be_clickable((By.XPATH, f"//*[text()='{gu}']"))
                )
                driver.execute_script("arguments[0].click();", gu_label)
                time.sleep(3)
            except:
                print(f"   ⚠️ {gu} 레이블을 찾을 수 없음")
                continue

            # 4. 매물 리스트 수집
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "apt-list")))
                cards = driver.find_elements(By.XPATH, "//div[@id='apt-list']//li[contains(@class, 'sc-')]")
                
                for idx in range(min(5, len(cards))): # 구별 5개 테스트
                    try:
                        cards = driver.find_elements(By.XPATH, "//div[@id='apt-list']//li[contains(@class, 'sc-')]")
                        driver.execute_script("arguments[0].click();", cards[idx])
                        time.sleep(2)

                        item_data = get_detailed_info(driver)
                        item_data["구"] = gu
                        FINAL_DATA.append(item_data)
                        print(f"   [{idx+1}] {item_data.get('가격')} 수집")

                        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                        time.sleep(1)
                    except:
                        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                        continue
            except: continue

            # 파일 저장
            with open("dabang_apt_data.json", "w", encoding="utf-8") as f:
                json.dump(FINAL_DATA, f, ensure_ascii=False, indent=4)

    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_dabang()