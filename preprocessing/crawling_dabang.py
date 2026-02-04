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
# 지도 버튼 클릭 (구 목록으로 돌아가기)
# ==============================

def click_map_button(driver):
    """
    한 구의 크롤링이 끝난 후 지도 버튼을 눌러서 구 선택 화면으로 돌아감
    """
    print("\n▶ 지도 버튼 클릭 (구 목록으로 돌아가기)")
    
    try:
        # 지도 버튼 클릭
        map_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[@aria-label='지도 축소']")
            )
        )
        driver.execute_script("arguments[0].click();", map_btn)
        time.sleep(2)
        print("✅ 지도 버튼 클릭 완료")
        
    except Exception as e:
        print(f"❌ 지도 버튼 클릭 실패: {e}")
        raise



import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

import time
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

def crawl_room_list(driver):
    """
    매물 상세정보 크롤링
    - 옵션 정보 (옷장, 냉장고 etc)
    - 상세정보 (건물명, 방종류, 면적 etc)
    """
    print("▶ 현재 페이지 매물 수집")
    results = []
    
    cards_xpath = "//div[@id='onetwo-list']//li"
    
    # 초기 카드 개수 확인
    try:
        cards = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, cards_xpath))
        )
        total_cards = len(cards)
        print(f"▶ 카드 수: {total_cards}")
    except TimeoutException:
        print("❌ 매물 카드를 찾을 수 없습니다.")
        return results
    
    for idx in range(total_cards):
        detail_data = {
            'index': idx + 1,
            'options': [],
            'details': {},
            'location': None  # 이 줄 추가
        }
        
        try:
            # === 1. 카드 클릭 ===
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    # 카드 재탐색 (Stale Element 방지)
                    cards = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, cards_xpath))
                    )
                    
                    if idx >= len(cards):
                        print(f"❌ {idx+1}번 카드가 존재하지 않습니다.")
                        break
                    
                    target = cards[idx]
                    
                    # 스크롤 및 클릭
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center', behavior:'smooth'});", 
                        target
                    )
                    time.sleep(0.8)
                    
                    driver.execute_script("arguments[0].click();", target)
                    print(f"  → {idx+1}번 카드 클릭")
                    break
                    
                except StaleElementReferenceException:
                    retry_count += 1
                    print(f"  ⚠ Stale element, 재시도 {retry_count}/{max_retries}")
                    time.sleep(1)
                    if retry_count >= max_retries:
                        raise Exception("카드 클릭 실패 (Stale Element)")
            
            # === 2. 상세 페이지 로딩 대기 ===
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//section[@data-scroll-spy-element='detail-info']")
                    )
                )
                time.sleep(1.5)  # 추가 안정화
            except TimeoutException:
                raise Exception("상세 페이지 로딩 타임아웃")
            
            # === 3. 옵션 정보 수집 ===
            try:
                option_container = driver.find_element(
                    By.XPATH, 
                    "//ul[contains(@class,'sc-cjaHrD') or contains(@class,'ebbBmJ')]"
                )
                
                option_items = option_container.find_elements(
                    By.XPATH, 
                    ".//p[contains(@class,'sc-sQEHi') or contains(@class,'wKFfz')]"
                )
                
                detail_data['options'] = [item.text.strip() for item in option_items if item.text.strip()]
                print(f"  ✓ 옵션: {', '.join(detail_data['options'][:5])}..." if len(detail_data['options']) > 5 
                      else f"  ✓ 옵션: {', '.join(detail_data['options'])}")
                
            except Exception as e:
                print(f"  ⚠ 옵션 수집 실패: {e}")
            
           # === 4. 상세정보 수집 ===
            try:
                detail_section = driver.find_element(
                    By.XPATH, 
                    "//section[@data-scroll-spy-element='detail-info']"
                )
                
                # li 항목들 파싱
                list_items = detail_section.find_elements(
                    By.XPATH, 
                    ".//ul[contains(@class,'sc-jiqrhf')]//li"
                )
                
                for item in list_items:
                    try:
                        # 키 추출 (h1 태그)
                        h1_element = item.find_element(By.TAG_NAME, 'h1')
                        key = h1_element.text.strip().replace('\n', ' ')
                        
                        # 값 추출 (p 태그들)
                        value_elements = item.find_elements(
                            By.XPATH, 
                            ".//div//p[contains(@class,'sc-jTzgvQ') or contains(@class,'fybIii')]"
                        )
                        
                        values = [v.text.strip() for v in value_elements if v.text.strip()]
                        value = ' | '.join(values) if values else ''
                        
                        if key and value:
                            detail_data['details'][key] = value
                            
                    except Exception as e:
                        continue
                
                print(f"  ✓ 상세정보: {len(detail_data['details'])}개 항목")
                
            except Exception as e:
                print(f"  ⚠ 상세정보 수집 실패: {e}")
            
            # === 5. 위치 정보 수집 (추가) ===
            # === 5. 위치 정보 수집 (수정) ===
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//section[@data-scroll-spy-element='near']//p")
                    )
                )

                location_section = driver.find_element(
                    By.XPATH,
                    "//section[@data-scroll-spy-element='near']"
                )

                location_info = location_section.find_element(
                    By.XPATH,
                    ".//p"
                ).text.strip()

                detail_data['location'] = location_info
                print(f"  ✓ 위치: {location_info}")

            except Exception as e:
                print(f"  ⚠ 위치 정보 수집 실패: {e}")
                detail_data['location'] = None
            
            # 결과 저장
            results.append(detail_data)
            print(f"✅ {idx+1}번 매물 완료")
            
        except Exception as e:
            print(f"❌ {idx+1}번 매물 실패: {str(e)}")
            results.append(detail_data)  # 부분 데이터라도 저장
        
        finally:
            # === 5. 닫기 버튼 클릭 (반드시 실행) ===
            try:
                # 정확한 닫기 버튼 선택자
                close_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button.sc-lnRjOp.cDzwDA")
                    )
                )
                driver.execute_script("arguments[0].click();", close_btn)
                time.sleep(1.5)
                print(f"  ✓ 닫기 완료\n")
                
            except Exception as close_error:
                print(f"  ⚠ 닫기 버튼 클릭 실패, ESC 시도")
                # ESC 키로 대체 시도
                try:
                    from selenium.webdriver.common.keys import Keys
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(1.5)
                    print(f"  ✓ ESC로 닫기 완료\n")
                except:
                    print(f"  ⚠ 닫기 실패, 계속 진행\n")
    
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



def save_to_json(data, filename='room_data.json'):
    """
    크롤링 결과를 JSON 파일로 저장
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 데이터 저장 완료: {filename}")
    print(f"📊 총 {len(data)}개 매물 저장됨")


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

    for idx, gu in enumerate(SEOUL_GU_LIST):

        print("\n==============================")
        print(f"▶▶ {gu} 수집 시작 ({idx+1}/{len(SEOUL_GU_LIST)})")
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

        print(f"✅ {gu} 완료 (수집: {len([r for r in ALL_RESULTS if gu in str(r)])}건)")
        
        # ==========================
        # 다음 구로 넘어가기 전에 지도로 돌아가기
        # ==========================
        if idx < len(SEOUL_GU_LIST) - 1:  # 마지막 구가 아니면
            click_map_button(driver)

    # ==========================
    # 전체 크롤링 완료 후 JSON 저장
    # ==========================
    print("\n🎉 전체 수집 완료")
    print(f"📊 총 수집 매물: {len(ALL_RESULTS)}개")
    
    # JSON 파일 저장
    save_to_json(ALL_RESULTS, 'seoul_oneroom_data.json')
    
    driver.quit()