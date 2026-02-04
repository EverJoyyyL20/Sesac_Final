import time
import json
import random

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ==============================
# 서울 25개 구 리스트
# ==============================

SEOUL_GU_LIST = [
    "강남구", "강동구", "강북구", "강서구", "관악구",
    "광진구", "구로구", "금천구", "노원구", "도봉구",
    "동대문구", "동작구", "마포구", "서대문구", "서초구",
    "성동구", "성북구", "송파구", "양천구", "영등포구",
    "용산구", "은평구", "종로구", "중구", "중랑구"
]


# ==============================
# 크롬 드라이버 생성
# ==============================

def create_driver():
    options = Options()

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    return driver


# ==============================
# 원/투룸 클릭
# ==============================

def click_one_two_room(driver):

    print("▶ 원/투룸 메뉴 찾는중")

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "a"))
    )

    menus = driver.find_elements(By.TAG_NAME, "a")

    for menu in menus:
        try:
            if "원/투룸" in menu.text:
                driver.execute_script("arguments[0].scrollIntoView(true);", menu)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", menu)

                print("✅ 원/투룸 클릭 완료")
                time.sleep(3)
                return
        except:
            continue

    raise Exception("❌ 원/투룸 메뉴 못찾음")


# ==============================
# 구 버튼 클릭
# ==============================

def click_gu_button(driver, gu_name):

    print(f"\n▶ {gu_name} 클릭")

    xpath = f"//*[contains(text(), '{gu_name}')]"

    btn = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )

    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});", btn)

    time.sleep(0.8)

    driver.execute_script("arguments[0].click();", btn)

    print(f"✅ {gu_name} 클릭 완료")

    time.sleep(3)


# ==============================
# 카트클릭 버튼 클릭
# ==============================

def crawl_room_list(driver):

    print("▶ 매물 카드 수집 시작")

    time.sleep(2)

    # 매물 카드들 (다방은 보통 article 또는 li)
    cards = driver.find_elements(By.XPATH, "//li//a | //article")

    print(f"▶ 발견된 카드 수: {len(cards)}")

    results = []

    for idx in range(len(cards)):

        try:
            print(f"\n▶ 매물 {idx+1} 클릭")

            cards = driver.find_elements(By.XPATH, "//li//a | //article")
            target = cards[idx]

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", target)

            time.sleep(0.8)

            driver.execute_script("arguments[0].click();", target)

            # ------------------
            # 상세 패널 로딩 대기
            # ------------------

            detail_section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//section[contains(@class,'sc-gbPaa')]"))
            )

            detail_text = detail_section.text

            results.append(detail_text)

            print("✅ 상세정보 수집 완료")

            # ------------------
            # 닫기 버튼 클릭
            # ------------------

            close_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@aria-label,'닫기')] | //button[contains(@aria-label,'close')]"))
            )

            driver.execute_script("arguments[0].click();", close_btn)

            time.sleep(1.5)

        except Exception as e:
            print("❌ 매물 처리 실패:", e)
            continue

    print(f"\n✅ 전체 매물 {len(results)}개 상세 수집 완료")

    return results


# ==============================
# 지도 축소(X) 클릭
# ==============================

def click_map_close(driver):

    print("▶ 지도 축소 클릭")

    close_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@aria-label='지도 축소']")
        )
    )

    driver.execute_script("arguments[0].click();", close_btn)

    time.sleep(2)

    print("✅ 지도 축소 완료")


# ==============================
# 서울 전체 구 반복 크롤링
# ==============================

def crawl_all_seoul_gu(driver):

    all_data = {}

    for gu in SEOUL_GU_LIST:

        try:
            click_gu_button(driver, gu)

            rooms = crawl_room_list(driver)

            all_data[gu] = rooms

            click_map_close(driver)

        except Exception as e:
            print(f"❌ {gu} 실패:", e)
            continue

    return all_data


# ==============================
# 메인 실행
# ==============================

if __name__ == "__main__":

    driver = create_driver()

    driver.get("https://www.dabangapp.com/")
    time.sleep(3)

    # 1. 원/투룸 클릭
    click_one_two_room(driver)

    # 2. 서울 전체 구 자동 반복
    data = crawl_all_seoul_gu(driver)

    # 3. 저장
    with open("dabang_seoul_room.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n🎉 전체 서울 25개구 크롤링 완료")

    driver.quit()
