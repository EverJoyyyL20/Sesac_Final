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


def crawl_room_list(driver):

    print("▶ 현재 페이지 매물 수집")

    results = []

    cards_xpath = "//div[@id='onetwo-list']//li"

    cards = WebDriverWait(driver,10).until(
        EC.presence_of_all_elements_located(
            (By.XPATH,cards_xpath))
    )

    print("▶ 카드 수:", len(cards))

    for idx in range(len(cards)):

        try:

            cards = driver.find_elements(By.XPATH,cards_xpath)
            target = cards[idx]

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", target)
            time.sleep(0.5)

            driver.execute_script("arguments[0].click();", target)

            # 상세 로딩 대기
            WebDriverWait(driver,10).until(
                EC.presence_of_element_located(
                    (By.XPATH,"//section[@data-scroll-spy-element]"))
            )

            sections = driver.find_elements(
                By.XPATH,"//section[@data-scroll-spy-element]"
            )

            detail_data = {}

            for sec in sections:
                key = sec.get_attribute("data-scroll-spy-element")
                detail_data[key] = sec.text

            results.append(detail_data)

            print(f"✅ {idx+1} 완료")

            # 닫기
            close_btn = WebDriverWait(driver,10).until(
                EC.element_to_be_clickable(
                    (By.XPATH,"//button[contains(@aria-label,'닫기')]"))
            )

            driver.execute_script("arguments[0].click();", close_btn)

            time.sleep(1)

        except Exception as e:
            print("❌ 실패:",e)
            continue

    return results


def scroll_until_end(driver):

    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            break

        last_height = new_height


def go_next_page(driver):

    try:
        next_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@aria-label,'다음')]"))
        )

        driver.execute_script("arguments[0].click();", next_btn)
        time.sleep(2)

        print("▶ 다음 페이지 이동")

        return True

    except:
        print("▶ 마지막 페이지")
        return False


if __name__ == "__main__":

    BASE_URL = "https://www.dabangapp.com/"

    driver = create_driver()
    driver.get(BASE_URL)

    time.sleep(3)

    click_one_two_room(driver)

    ALL_RESULTS = []

    # ==========================
    # 서울 25개 구 반복
    # ==========================

    for gu in SEOUL_GU_LIST:

        print("\n==============================")
        print(f"▶▶ {gu} 수집 시작")
        print("==============================")

        click_gu_button(driver, gu)

        page = 1

        # ==========================
        # 페이지 반복
        # ==========================

        while True:

            print(f"\n[{gu}] PAGE {page}")

            scroll_until_end(driver)

            page_data = crawl_room_list(driver)

            ALL_RESULTS.extend(page_data)

            has_next = go_next_page(driver)

            if not has_next:
                break

            page += 1

        print(f"✅ {gu} 완료")

    print("\n🎉 전체 수집 완료")
    print("총 수집 매물:", len(ALL_RESULTS))
