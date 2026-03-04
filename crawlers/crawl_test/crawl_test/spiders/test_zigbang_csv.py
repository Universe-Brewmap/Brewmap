import json
import scrapy
# 실행 코드: scrapy crawl test_zigbang_csv

class TestZigbangSpider(scrapy.Spider):
    name = "test_zigbang_csv"
    allowed_domains = ["apis.zigbang.com"]
    handle_httpstatus_list = [400]

    CSV_FIELDS = [
        "listing_id",
        "listing_status",
        "address",
        "lat",
        "lng",
        "business_type",
        "transaction_type",
        "sale_price",
        "key_money",
        "deposit",
        "monthly_rent",
        "maintenance_fee",
        "size_m2",
        "floor",
    ]

    custom_settings = {
        # JSON + CSV 동시 저장 (후처리 변환 없이 Scrapy가 직접 export)
        "FEEDS": {
            "test_zigbang.json": {
                "format": "json",
                "encoding": "utf-8",
                "overwrite": True,
                "indent": 2,
            },
            "test_zigbang.csv": {
                "format": "csv",
                "encoding": "utf-8-sig",
                "overwrite": True,
                "fields": CSV_FIELDS,
                "item_export_kwargs": {"quoting": 1},  # csv.QUOTE_ALL
            },
        }
    }

    COMMON_HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://www.zigbang.com",
        "Referer": "https://www.zigbang.com/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
    }

    # 크롤링 시작
    def start_requests(self):
        url = "https://apis.zigbang.com/v2/store/article/stores"
        payload = {
            "domain": "zigbang",
            "shuffle": False,
            "상권": [
                {
                    "lat": 37.51264572143555,
                    "lng": 127.0301513671875,
                    "radius": 1000,
                }  # 논현동 1km
            ],
            "sales_type": "전체",
            "first_floor": False,
            "업종": [],
        }

        self.logger.info(
            "settings_check BOT_NAME=%s SPIDER_MODULES=%s",
            self.settings.get("BOT_NAME"),
            self.settings.get("SPIDER_MODULES"),
        )

        yield scrapy.Request(
            url=url,
            method="POST",
            headers=self.COMMON_HEADERS,
            body=json.dumps(payload, ensure_ascii=False),
            callback=self.parse_stores,  # 응답 오면 parse_stores() 실행
            dont_filter=True,
        )

    # 매물 ID 수집
    def parse_stores(self, response):
        if response.status != 200:
            self.logger.warning(
                "stores_api_error status=%s body=%s",
                response.status,
                response.text[:1000],
            )
            return

        data = json.loads(response.text)  # JSON 파싱
        item_locations = []

        # item_locations 추출
        for section in data:
            if isinstance(section, dict) and "item_locations" in section:
                item_locations.extend(section["item_locations"])

        if not item_locations:
            self.logger.warning("no_item_locations")
            return

        self.logger.info("found_items=%s", len(item_locations))

        # ID만 추출
        item_ids = [item["item_id"] for item in item_locations if "item_id" in item]

        # 좌표 저장
        location_map = {
            item["item_id"]: {"lat": item.get("lat"), "lng": item.get("lng")}
            for item in item_locations
            if "item_id" in item
        }

        yield from self.request_store_details(item_ids, location_map)

    # 상세정보 요청
    def request_store_details(self, item_ids, location_map):
        url = "https://apis.zigbang.com/v2/store/article/stores/list"
        batch_size = 100  # 100개씩 묶어서 요청

        for i in range(0, len(item_ids), batch_size):
            batch = item_ids[i : i + batch_size]
            payload = {"item_ids": batch}

            yield scrapy.Request(
                url=url,
                method="POST",
                headers=self.COMMON_HEADERS,
                body=json.dumps(payload),
                callback=self.parse_details,
                meta={"location_map": location_map},  # 좌표 정보를 meta로 넘김
                dont_filter=True,
            )

    # 정적 method(self 사용 안 함)
    @staticmethod
    def _first(item, keys, default=None):
        """여러 키 중 처음 발견되는 값 반환"""
        for key in keys:
            if key in item and item.get(key) is not None:
                return item.get(key)
        return default

    @staticmethod
    def _to_won(value):
        """만원 단위 값을 원 단위로 변환 (예: 250 -> 2500000)"""
        if value is None:
            return None
        try:
            return int(float(value) * 10000)
        except (TypeError, ValueError):
            return value

    # 데이터 조합 & 저장
    def parse_details(self, response):
        data = json.loads(response.text)
        location_map = response.meta["location_map"]  # 아까 넘긴 좌표

        for item in data:
            item_id = item.get("item_id")
            loc = location_map.get(item_id, {})  # 좌표 찾기

            address_origin = item.get("addressOrigin")
            if isinstance(address_origin, dict):
                address = address_origin.get("fullText", "")
            else:
                address = address_origin or ""

            # 최종 데이터 구성
            row = {
                "listing_id": item_id,
                "listing_status": item.get("status"),
                "address": address,
                "lat": loc.get("lat"),
                "lng": loc.get("lng"),
                "business_type": self._first(item, ["업종", "building_type"]),
                "transaction_type": self._first(item, ["sales_title", "sales_type"]), # 월세
                "sale_price": self._first(item, ["매매금액", "sale_price"]),
                "key_money": self._to_won(self._first(item, ["권리금액", "key_money"])),
                "deposit": self._to_won(self._first(item, ["보증금액", "deposit"])),
                "monthly_rent": self._to_won(self._first(item, ["월세금액", "rent"])),
                "maintenance_fee": self._to_won(self._first(item, ["관리금액", "maintenance_fee"])),
                "size_m2": item.get("size_m2"),
                "floor": item.get("floor"),
            }
            yield row  # Scrapy가 JSON/CSV에 자동 저장
