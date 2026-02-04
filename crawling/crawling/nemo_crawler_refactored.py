import re
import time
import json

import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ----------설정----------

BASE_URL = "https://www.nemoapp.kr/store"
KEYWORD = "여의도동"
OUT_CSV = "crawling_nemo_nemo.csv"
OUT_JSON = "crawling_nemo.json"
MAX_LISTINGS = None  # None이면 하단까지 전체 수집

# 팝업 닫기 selector
POPUP_CLOSE_BTN_CSS = "#portal > div > div > div > div > button:nth-child(1)"

# 검색 selector
SEARCH_INPUT_CSS = "#wrap > div.top-menu > div > div.search > input[type=search]"
AUTO_ITEM_LEFT_CSS = "#wrap > div.top-menu > div > div.search > ul > li > div.left"

# 매물 리스트 selector
LISTING_ITEMS_CSS = (
    "#wrap > div.layout-wrap > div.flex.flex-row > div > aside > div > div.simplebar-wrapper "
    "> div.simplebar-mask > div > div > div > div.article-menu > ul > li"
)
LISTING_ITEM_IMG_CSS = f"{LISTING_ITEMS_CSS} > div > div.relative > div > img"
LISTING_ASIDE_CSS = "#wrap > div.layout-wrap > div.flex.flex-row > div > aside"

# 매물 상세
DETAIL_SECTION_XPATH = "//*[normalize-space()='상가 임대 정보']"

# 가격 정보
FEE_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.title-wrapper > div.price-container > table > tbody > tr.navy > th"
FEE_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.title-wrapper > div.price-container > table > tbody > tr.navy > td"

DEPOSITE_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.title-wrapper > div.price-container > table > tbody > tr:nth-child(2) > th"
DEPOSITE_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.title-wrapper > div.price-container > table > tbody > tr:nth-child(2) > td"

KEY_MONEY_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.title-wrapper > div.price-container > table > tbody > tr:nth-child(3) > th"
KEY_MONEY_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.title-wrapper > div.price-container > table > tbody > tr:nth-child(3) > td"

MAINTAIN_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.title-wrapper > div.price-container > table > tbody > tr:nth-child(4) > th"
MAINTAIN_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.title-wrapper > div.price-container > table > tbody > tr:nth-child(4) > td"

# 매물 상세 정보
CUR_TYPE_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(2) > div > h6"
CUR_TYPE_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(2) > div > p"

MONE_IV_DT_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(3) > div > h6"
MONE_IV_DT_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(3) > div > p"

FLOOR_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(4) > div > h6"
FLOOR_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(4) > div > p"

M2_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(5) > div > h6"
M2_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(5) > div > p"

PARK_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(7) > div > h6"
PARK_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(7) > div > p"

TOILET_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(8) > div > h6"
TOILET_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(8) > div > p"

DIRECT_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(11) > div > h6"
DIRECT_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div:nth-child(6) > div.flex.flex-row.flex-wrap.flex-1.mt-2 > li:nth-child(11) > div > p"

VIOLATION_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.building-register-information.bg-white.px-5.py-8.m-0 > div.detail-table.head-line > table > tbody > tr:nth-child(12) > th"
VIOLATION_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.building-register-information.bg-white.px-5.py-8.m-0 > div.detail-table.head-line > table > tbody > tr:nth-child(12) > td"

REALTOR_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.broker.bg-white.px-5.py-8.m-0 > div.content > div.flex-1 > h6"

REALTOR_TEL_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.broker.bg-white.px-5.py-8.m-0 > div.content > div.flex-1 > dl:nth-child(4) > dt"
REALTOR_TEL_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.broker.bg-white.px-5.py-8.m-0 > div.content > div.flex-1 > dl:nth-child(4) > dd"

MAX_BROKER_FEE_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.brokerage-fee.bg-white.px-5.py-8.m-0 > div.detail-table > table > tbody > tr.blue > th"
MAX_BROKER_FEE_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.brokerage-fee.bg-white.px-5.py-8.m-0 > div.detail-table > table > tbody > tr.blue > td"

BUILDING_FEAT_TH_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.feature.bg-white.px-5.py-8.m-0 > ul > li:nth-child(3) > div > h6"
BUILDING_FEAT_TD_CSS = "#ArticleDetail > div > div.simplebar-scrollable-y > div.simplebar-wrapper > div.simplebar-mask > div > div > div > div > div.feature.bg-white.px-5.py-8.m-0 > ul > li:nth-child(3) > div > p"


# ----------동작----------

#유틸

def norm(s: str) -> str:
    """문자열 정규화 (공백 제거)"""
    return re.sub(r"\s+", " ", (s or "")).strip()


def extract_number(text: str) -> int:
    """
    텍스트 금액을 원 단위 int로 변환
    예: "월세 50만원" -> 500000
    예: "351만원" -> 3510000
    예: "3억 2,000만원" -> 320000000
    예: "없음" → 0
    """
    if not text:
        return 0

    s = norm(text).replace(",", "")
    if not re.search(r"\d", s):
        return 0

    total = 0
    eok = re.search(r"(\d+(?:\.\d+)?)\s*억", s)
    man = re.search(r"(\d+(?:\.\d+)?)\s*만", s)

    if eok:
        total += int(float(eok.group(1)) * 100_000_000)
    if man:
        total += int(float(man.group(1)) * 10_000)

    if total > 0:
        return total

    digits = re.sub(r"[^0-9]", "", s)
    return int(digits) if digits else 0


def js_click(driver, el):
    """JavaScript로 요소 클릭 (일반 클릭이 막힐 때 사용)"""
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.15)
    driver.execute_script("arguments[0].click();", el)


def get_text_css(driver, css: str, timeout=10) -> str:
    """
    CSS로 요소 찾아서 텍스트 반환
    - 요소가 없으면 빈 문자열 반환 (에러 안 남)
    """
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css))
        )
        return norm(el.text)
    except Exception:
        return ""


def wait_css(driver, css: str, timeout=20):
    """CSS로 요소가 나타날 때까지 대기"""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css))
    )


def wait_clickable_css(driver, css: str, timeout=20):
    """CSS로 요소가 클릭 가능할 때까지 대기"""
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, css))
    )


def wait_visible_xpath(driver, xp: str, timeout=20):
    """XPath로 요소가 보일 때까지 대기"""
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.XPATH, xp))
    )


# 팝업 닫기

def close_popup_if_exists(driver, timeout=4):
    """팝업이 있으면 닫기"""
    try:
        short_wait = WebDriverWait(driver, timeout)
        btn = short_wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, POPUP_CLOSE_BTN_CSS))
        )
        js_click(driver, btn)
        time.sleep(0.3)
        print(" 팝업 닫기 완료")
    except Exception:
        print("ℹ 팝업 없음 (스킵)")


# 검색
def do_search(driver, keyword: str):
    """검색창에 키워드 입력 후 자동완성 클릭"""
    inp = wait_clickable_css(driver, SEARCH_INPUT_CSS, timeout=25)
    inp.click()
    inp.clear()

    # 한 글자씩 입력 (너무 빠르면 자동완성 안 뜸)
    for ch in keyword:
        inp.send_keys(ch)
        time.sleep(0.04)

    # 자동완성 첫 번째 항목 클릭
    item = wait_clickable_css(driver, AUTO_ITEM_LEFT_CSS, timeout=25)
    js_click(driver, item)
    time.sleep(1.2)

#매물 상세 pasing
def parse_detail(driver) -> dict:
    """
    현재 열린 매물 상세 페이지에서 데이터 추출
    반환: 딕셔너리 (한 매물 = 한 row)
    """
    data = {
        # 금액 정보 (int로 변환할 필드)
        "are_fee": 0,              # 월세
        "are_deposit": 0,          # 보증금
        "are_key_money": 0,        # 권리금
        "are_maintain": 0,         # 관리비
        "are_max_broker_fee": 0,   # 중개비
        
        # 기타 정보 (문자열)
        "are_cur_type": "",        # 현재업종
        "are_mone_iv_dt": "",      # 입주가능일
        "are_floor": "",           # 층
        "are_con_m2": "",          # 계약면적
        "are_net_m2": "",          # 전용면적
        "are_park": "",            # 주차
        "are_toilet": "",          # 화장실
        "are_direct": "",          # 방향
        "are_violation": "",       # 위반건축물
        "are_realtor": "",         # 중개사
        "are_realtor_tel": "",     # 중개사 전화번호
        "are_building_feat": "",   # 상가특징
    }

    # 금액 정보 (int 변환)
    fee_text = get_text_css(driver, FEE_TD_CSS, timeout=10)
    data["are_fee"] = extract_number(fee_text)
    
    deposit_text = get_text_css(driver, DEPOSITE_TD_CSS, timeout=10)
    data["are_deposit"] = extract_number(deposit_text)
    
    key_money_text = get_text_css(driver, KEY_MONEY_TD_CSS, timeout=10)
    data["are_key_money"] = extract_number(key_money_text)
    
    maintain_text = get_text_css(driver, MAINTAIN_TD_CSS, timeout=10)
    data["are_maintain"] = extract_number(maintain_text)
    
    broker_fee_text = get_text_css(driver, MAX_BROKER_FEE_TD_CSS, timeout=10)
    data["are_max_broker_fee"] = extract_number(broker_fee_text)

    # ---- 현재업종 / 입주가능일 / 층 ----
    data["are_cur_type"] = get_text_css(driver, CUR_TYPE_TD_CSS, timeout=10)
    data["are_mone_iv_dt"] = get_text_css(driver, MONE_IV_DT_TD_CSS, timeout=10)
    data["are_floor"] = get_text_css(driver, FLOOR_TD_CSS, timeout=10)

    # ---- 면적 (계약/전용 같이 나오는 값 분해) ----
    m2_text = get_text_css(driver, M2_TD_CSS, timeout=10)  # 예: "76m² / 76m²"
    if m2_text:
        parts = [norm(x) for x in m2_text.split("/") if norm(x)]
        if len(parts) >= 1:
            data["are_con_m2"] = parts[0]
        if len(parts) >= 2:
            data["are_net_m2"] = parts[1]

    # ---- 주차/화장실/방향 ----
    data["are_park"] = get_text_css(driver, PARK_TD_CSS, timeout=10)
    data["are_toilet"] = get_text_css(driver, TOILET_TD_CSS, timeout=10)
    data["are_direct"] = get_text_css(driver, DIRECT_TD_CSS, timeout=10)

    # ---- 위반건축물 ----
    data["are_violation"] = get_text_css(driver, VIOLATION_TD_CSS, timeout=10)

    # ---- 중개사 / 전화번호 ----
    data["are_realtor"] = get_text_css(driver, REALTOR_TH_CSS, timeout=10)
    data["are_realtor_tel"] = get_text_css(driver, REALTOR_TEL_TD_CSS, timeout=10)

    # ---- 상가특징 ----
    feat = get_text_css(driver, BUILDING_FEAT_TD_CSS, timeout=5)
    if not feat:
        feat = get_text_css(driver, BUILDING_FEAT_TH_CSS, timeout=5)
    data["are_building_feat"] = feat

    return data


def scroll_listing_panel_to_bottom(driver, max_idle_rounds=4):
    """좌측 매물 패널을 끝까지 내려서 lazy loading된 항목까지 로드"""
    stable_rounds = 0
    prev_count = -1

    while stable_rounds < max_idle_rounds:
        try:
            current_count = len(driver.find_elements(By.CSS_SELECTOR, LISTING_ITEM_IMG_CSS))
            if current_count == prev_count:
                stable_rounds += 1
            else:
                stable_rounds = 0
                prev_count = current_count

            moved = driver.execute_script(
                """
                const aside = document.querySelector(arguments[0]);
                if (!aside) return false;
                const scroller = aside.querySelector('.simplebar-content-wrapper')
                    || aside.querySelector('.simplebar-mask');
                if (!scroller) return false;
                const before = scroller.scrollTop;
                scroller.scrollTop = scroller.scrollHeight;
                return scroller.scrollTop > before;
                """,
                LISTING_ASIDE_CSS,
            )
            time.sleep(0.4)
            if not moved and stable_rounds >= 2:
                break
        except Exception:
            break


def collect_all_listings(driver, max_count=None):
    """
    매물 리스트에서 N개 매물을 순회하며 데이터 수집
    
    Args:
        driver: Selenium WebDriver
        max_count: 수집할 최대 매물 수
    
    Returns:
        list[dict]: 수집된 매물 데이터 리스트
    """
    rows = []
    
    # 스크롤해서 전체 매물 로드
    scroll_listing_panel_to_bottom(driver)

    # 매물 개수 확인
    try:
        wait_css(driver, LISTING_ITEM_IMG_CSS, timeout=15)
        total_items = len(driver.find_elements(By.CSS_SELECTOR, LISTING_ITEM_IMG_CSS))
        total = min(total_items, max_count) if isinstance(max_count, int) and max_count > 0 else total_items
        print(f"\n 총 {total_items}개 매물 중 {total}개 수집 시작\n")
    except Exception as e:
        print(f" 매물 리스트 로딩 실패: {e}")
        return rows
    
    # 각 매물 순회
    for idx in range(total):
        print(f"🔍 [{idx + 1}/{total}] 매물 처리 중...")

        try:
            # 매번 요소를 다시 가져와서 StaleElementReference 방지
            imgs = driver.find_elements(By.CSS_SELECTOR, LISTING_ITEM_IMG_CSS)
            if idx >= len(imgs):
                print("   리스트 끝에 도달하여 중단")
                break

            img = imgs[idx]
            js_click(driver, img)

            # 상세 페이지 로딩 대기
            wait_visible_xpath(driver, DETAIL_SECTION_XPATH, timeout=10)
            time.sleep(0.6)

            # 데이터 추출
            data = parse_detail(driver)
            data["listing_index"] = idx + 1  # 순서 기록
            rows.append(data)

            # 간단한 정보 출력
            print(f"    완료: {data.get('are_cur_type', 'N/A')} | "
                  f"월세 {data['are_fee']:,}원 | "
                  f"보증금 {data['are_deposit']:,}원")

        except Exception as e:
            print(f"    실패: {e}")
            continue
        
        time.sleep(0.5)  # 다음 매물로 넘어가기 전 대기
    
    return rows


def to_output_item(row: dict) -> dict:
    """요청한 출력 포맷(짧은 키)으로 변환"""
    return {
        "fee": row.get("are_fee", 0),
        "deposit": row.get("are_deposit", 0),
        "key_money": row.get("are_key_money", 0),
        "maintain": row.get("are_maintain", 0),
        "broker_fee": row.get("are_max_broker_fee", 0),
        "cur_type": row.get("are_cur_type", ""),
        "floor": row.get("are_floor", ""),
        "con_m2": row.get("are_con_m2", ""),
        "net_m2": row.get("are_net_m2", ""),
    }


# ----------실행----------

def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")  # 백그라운드 실행 (필요시 주석 해제)

    driver = webdriver.Chrome(options=options)
    try:
        # 1. 페이지 요청
        print(f" 페이지 로딩: {BASE_URL}")
        driver.get(BASE_URL)

        # 초기 로딩: 검색창 뜰 때까지 대기
        wait_css(driver, SEARCH_INPUT_CSS, timeout=30)
        print(" 페이지 로딩 완료")

        # 2. 팝업 닫기
        close_popup_if_exists(driver, timeout=4)

        # 3. 검색
        print(f"\n검색 시작: '{KEYWORD}'")
        do_search(driver, KEYWORD)
        print(" 검색 완료")

        # 4~6. 매물 리스트 전체 수집
        rows = collect_all_listings(driver, max_count=MAX_LISTINGS)

        # 7. 결과 출력 (요청 포맷)
        print("\n" + "="*60)
        print(f"수집 완료: 총 {len(rows)}개 매물")
        print("="*60 + "\n")
        
        if rows:
            output_items = [to_output_item(row) for row in rows]
            print("출력 예시:")
            for item in output_items[:5]:
                print(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
        
        # 8. JSON 저장 (요청 포맷)
        if rows:
            output_items = [to_output_item(row) for row in rows]
            with open(OUT_JSON, "w", encoding="utf-8") as f:
                json.dump(output_items, f, ensure_ascii=False, indent=2)
            print(f"\nJSON 저장 완료: {OUT_JSON}")
            print(f" 저장 위치: {OUT_JSON}")

            # 필요 시 CSV도 함께 저장
            df = pd.DataFrame(rows)
            df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
            print(f"CSV도 함께 저장: {OUT_CSV}")
        else:
            print("\n 수집된 데이터 없음")

        # DevTools 확인용 (필요 시)
        input("\n⏸ Enter를 누르면 브라우저를 닫습니다: ")

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()
        print("\n브라우저 종료")


if __name__ == "__main__":
    main()
