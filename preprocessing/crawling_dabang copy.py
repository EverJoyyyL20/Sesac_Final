import requests
import csv
import json
import time
import codecs
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def get_auth_info(complex_no):
    """셀레늄을 사용하여 최신 쿠키와 Bearer 토큰을 추출합니다."""
    chrome_options = Options()
    # 보안 스크립트 우회를 위한 설정
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    # 창을 띄우지 않으려면 아래 주석 해제 (단, 처음엔 확인을 위해 띄우는 것 추천)
    # chrome_options.add_argument("--headless") 
    
    driver = webdriver.Chrome(options=chrome_options)
    url = f'https://new.land.naver.com/complexes/{complex_no}'
    
    driver.get(url)
    time.sleep(3) # 페이지 로딩 대기

    # 1. 쿠키 추출
    selenium_cookies = driver.get_cookies()
    cookie_dict = {c['name']: c['value'] for c in selenium_cookies}
    
    # 2. Authorization 토큰 추출 (로컬 스토리지나 네트워크 로그 대신 실행 컨텍스트 활용)
    # 네이버는 보통 sessionStorage나 내부 변수에 토큰을 저장합니다.
    # 가장 확실한 방법은 네트워크 요청을 가로채는 것이지만, 
    # 일반적인 requests 전송을 위해 브라우저의 User-Agent를 그대로 복사합니다.
    user_agent = driver.execute_script("return navigator.userAgent")
    
    driver.quit()
    return cookie_dict, user_agent

def get_real_estate_data(complex_no, cookies, user_agent, page=1):
    # Authorization 토큰은 수시로 변하므로, 
    # 만약 Bearer 토큰 에러가 난다면 브라우저 세션 정보를 더 정밀하게 파싱해야 합니다.
    # 우선은 셀레늄에서 가져온 쿠키만으로도 접근 가능한 경우가 많습니다.
    
    headers = {
        'accept': '*/*',
        'accept-language': 'ko-KR,ko;q=0.9',
        'referer': f'https://new.land.naver.com/complexes/{complex_no}',
        'user-agent': user_agent,
    }

    api_url = f'https://new.land.naver.com/api/articles/complex/{complex_no}'
    params = {
        'realEstateType': 'APT',
        'tradeType': 'A1', # 매매(A1), 전세(A2), 월세(B1)
        'tag': '::::::::',
        'priceType': 'RETAIL',
        'page': str(page),
        'complexNo': str(complex_no),
        'type': 'list',
        'order': 'rank'
    }

    response = requests.get(api_url, params=params, cookies=cookies, headers=headers)
    return response.json()

# ... (save_to_csv 함수는 기존과 동일) ...

def main():
    complex_no = 2976
    try:
        print("인증 정보 추출 중...")
        cookies, ua = get_auth_info(complex_no)
        
        all_articles = []
        for page in range(1, 6): # 테스트를 위해 5페이지까지
            print(f"{page}페이지 수집 중...")
            data = get_real_estate_data(complex_no, cookies, ua, page)
            articles = data.get('articleList', [])
            
            if not articles: break
            all_articles.extend(articles)
            time.sleep(1.5)
            
        # 결과 저장 (파일명 생략)
        print(f"수집 완료: {len(all_articles)}건")
    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    main()