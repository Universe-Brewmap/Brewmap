import re
import time
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

wait = WebDriverWait(driver, 15)

# =========================
# 설정
# =========================
BASE_URL = "https://www.nemoapp.kr/store"
KEYWORD = "노량진동"  # 예시
OUT_CSV = "nemo_one_listing.csv"

# 너가 준 selector들 (가능한 그대로 유지)
SEARCH_INPUT_CSS = "#wrap > div.top-menu > div > div.search > input[type=search]"
AUTO_ITEM_LEFT_CSS = "#wrap > div.top-menu > div > div.search > ul > li > div.left"

FIRST_LISTING_IMG_CSS = (
    "#wrap > div.layout-wrap > div.flex.flex-row > div > aside > div > div.simplebar-wrapper "
    "> div.simplebar-mask > div > div > div > div.article-menu > ul > li:nth-child(1) "
    "> div > div.relative > div > img"
)

# 상세 패널 "상가 임대 정보" 텍스트를 anchor로 (Copy selector보다 훨씬 안정)
DETAIL_SECTION_XPATH = "//*[normalize-space()='상가 임대 정보']"


# =========================
# 유틸
# =========================
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def js_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.2)
    driver.execute_script("arguments[0].click();", el)

def wait_css(driver, css: str, timeout=20):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css))
    )

def wait_clickable_css(driver, css: str, timeout=20):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, css))
    )

def wait_xpath(driver, xp: str, timeout=20):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, xp))
    )

def wait_visible_xpath(driver, xp: str, timeout=20):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.XPATH, xp))
    )

def safe_text(el) -> str:
    try:
        return norm(el.text)
    except Exception:
        return ""


# =========================
# 1) 검색 + 자동완성 클릭
# =========================
def do_search(driver, keyword: str):
    inp = wait_clickable_css(driver, SEARCH_INPUT_CSS, timeout=25)
    inp.click()
    inp.clear()

    # 입력(천천히)
    for ch in keyword:
        inp.send_keys(ch)
        time.sleep(0.05)

    # 자동완성 뜰 때까지 대기
    item = wait_clickable_css(driver, AUTO_ITEM_LEFT_CSS, timeout=25)
    js_click(driver, item)

    # 검색 후 화면 안정화
    time.sleep(1.5)


# =========================
# 2) 첫 매물 클릭 (리스트에서 상세 열기)
# =========================
def open_first_listing(driver):
    # 첫 매물 이미지가 "존재"할 때까지
    img = wait_css(driver, FIRST_LISTING_IMG_CSS, timeout=25)
    js_click(driver, img)

    # 상세 패널의 anchor 텍스트가 보일 때까지
    wait_visible_xpath(driver, DETAIL_SECTION_XPATH, timeout=25)
    time.sleep(0.8)


# =========================
# 3) 상세 패널에서 ERD 필드 파싱
#    - "상가 임대 정보" 섹션 주변에서 li들을 읽어 label/value로 만들고
#    - ERD 필드명으로 매핑
# =========================
def parse_erd_fields(driver):
    data = {
        # ERD key들을 "전부" 만들어 둠(빈값이라도 컬럼 유지)
        "are_fee": "",
        "are_deposit": "",
        "are_key_money": "",
        "are_maintain": "",
        "are_cur_type": "",
        "are_mone_iv_dt": "",
        "are_floor": "",
        "are_con_m2": "",
        "are_net_m2": "",
        "are_park": "",
        "are_toilet": "",
        "are_direct": "",
        "are_violation": "",
        "are_realtor": "",
        "are_realtor_tel": "",
        "are_max_broker_fee": "",
        "are_building_feat": "",
        "reg_no": "",
    }

    # 등록번호도 있으면 같이 추출 (예: 등록번호 919738)
    try:
        reg_el = driver.find_element(By.XPATH, "//*[contains(normalize-space(),'등록번호')]")
        m = re.search(r"등록번호\s*(\d+)", safe_text(reg_el))
        if m:
            data["reg_no"] = m.group(1)
    except Exception:
        pass

    # "상가 임대 정보" 헤더를 기준으로 상위 컨테이너를 잡고 li 텍스트 수집
    header = driver.find_element(By.XPATH, DETAIL_SECTION_XPATH)
    # header의 적절한 상위 div(너무 상위면 잡텍스트 많아짐)
    panel = header.find_element(By.XPATH, "./ancestor::div[2]")

    lis = panel.find_elements(By.TAG_NAME, "li")

    # li 텍스트를 label/value로 단순 분리(아이콘+텍스트 구조라 보통 가능)
    kv = {}
    for li in lis:
        t = safe_text(li)
        if not t:
            continue
        # 예: "전용면적/계약면적 76m² / 76m²"
        parts = t.split(" ", 1)
        if len(parts) == 2:
            label, value = norm(parts[0]), norm(parts[1])
            if label:
                kv[label] = value
        else:
            kv[f"raw_{len(kv)}"] = t

    # ===== 매핑 규칙(텍스트 라벨 → ERD 필드) =====
    # 라벨이 사이트에서 어떻게 나오든 어느 정도 대응되도록 키워드 기반 처리
    def pick_by_keywords(value_map, keywords):
        for k, v in value_map.items():
            if any(kw in k for kw in keywords):
                return v
        return ""

    # 면적(전용/계약)
    area = pick_by_keywords(kv, ["전용면적", "전용"])
    con = pick_by_keywords(kv, ["계약면적", "계약"])
    if con:
        data["are_con_m2"] = con
    if area:
        data["are_net_m2"] = area

    # 층/입주/현재업종 등
    data["are_cur_type"] = pick_by_keywords(kv, ["현재 업종", "현재업종"])
    data["are_mone_iv_dt"] = pick_by_keywords(kv, ["입주 가능일", "입주가능일"])
    data["are_floor"] = pick_by_keywords(kv, ["임대 상가층", "상가층", "층"])
    data["are_park"] = pick_by_keywords(kv, ["주차", "주차가능"])
    data["are_toilet"] = pick_by_keywords(kv, ["화장실"])
    data["are_direct"] = pick_by_keywords(kv, ["방향"])
    data["are_building_feat"] = pick_by_keywords(kv, ["이런 특징", "특징"])

    # ===== 가격/중개/위반 등은 섹션이 다른 곳에 있을 수 있어 보강 추출 =====
    # 화면 어디든 라벨 텍스트 기준으로 값 찾기(가장 튼튼)
    def find_value_by_label(label_text: str):
        """
        '보증금', '월세', '권리금' 같은 라벨 근처의 값을 XPath로 찾는 보강 함수.
        DOM 구조가 바뀌어도 '라벨 텍스트'만 남으면 따라갈 수 있게 함.
        """
        # 라벨 텍스트 포함 요소
        xp_label = f"//*[contains(normalize-space(), '{label_text}')]"
        els = driver.find_elements(By.XPATH, xp_label)
        for el in els:
            txt = safe_text(el)
            if label_text not in txt:
                continue
            # 같은 블록 내에서 숫자/금액처럼 보이는 텍스트를 탐색
            try:
                box = el.find_element(By.XPATH, "./ancestor::div[1]")
                box_text = safe_text(box)
                if box_text and len(box_text) <= 80:
                    return box_text
            except Exception:
                pass
        return ""

    # 월세/보증금/권리금/관리비/중개보수 등(표현 방식이 다양해서 텍스트 블록으로 먼저 저장)
    # 필요하면 후처리(숫자만 추출)도 가능
    data["are_fee"] = find_value_by_label("월세") or data["are_fee"]
    data["are_deposit"] = find_value_by_label("보증금") or data["are_deposit"]
    data["are_key_money"] = find_value_by_label("권리금") or data["are_key_money"]
    data["are_maintain"] = find_value_by_label("관리비") or data["are_maintain"]
    data["are_max_broker_fee"] = find_value_by_label("중개보수") or data["are_max_broker_fee"]
    data["are_violation"] = find_value_by_label("위반") or data["are_violation"]
    data["are_realtor"] = find_value_by_label("중개사") or data["are_realtor"]
    data["are_realtor_tel"] = find_value_by_label("중개사 번호") or find_value_by_label("전화") or data["are_realtor_tel"]

    return data


def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get(BASE_URL)

        # 0) 초기 로딩 대기(검색창이 나타날 때까지)
        wait_css(driver, SEARCH_INPUT_CSS, timeout=30)

        # 1) 검색 + 자동완성 클릭
        do_search(driver, KEYWORD)

        # 2) 첫 매물 클릭해서 상세 열기
        open_first_listing(driver)

        # 3) ERD 필드 추출
        row = parse_erd_fields(driver)

        print("====== 출력 시작 ======")
        for k, v in row.items():
            print(k, "=>", v)
        print("====== 출력 끝 ======")

        # 4) CSV 저장(컬럼 누락 없이)
        df = pd.DataFrame([row])
        df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
        print(f"Saved: {OUT_CSV}")

        time.sleep(5)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
