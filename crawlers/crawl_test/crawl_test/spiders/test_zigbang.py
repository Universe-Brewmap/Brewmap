import json
import scrapy


class TestZigbangSpider(scrapy.Spider):
    name = "test_zigbang"
    allowed_domains = ["apis.zigbang.com"]

    custom_settings = {
        "FEEDS": {
            "test_zigbang.json": {
                "format": "json",
                "encoding": "utf-8",
                "overwrite": True,
            }
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
                }
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
            callback=self.parse_stores,
            dont_filter=True,
        )

    def parse_stores(self, response):
        data = json.loads(response.text)

        item_locations = []
        for section in data:
            if "item_locations" in section:
                item_locations.extend(section["item_locations"])

        if not item_locations:
            self.logger.warning("no_item_locations")
            return

        self.logger.info(f"found_items={len(item_locations)}")

        item_ids = [item["item_id"] for item in item_locations]

        location_map = {
            item["item_id"]: {"lat": item["lat"], "lng": item["lng"]}
            for item in item_locations
        }

        yield from self.request_store_details(item_ids, location_map)

    def request_store_details(self, item_ids, location_map):
        url = "https://apis.zigbang.com/v2/store/article/stores/list"
        batch_size = 100

        for i in range(0, len(item_ids), batch_size):
            batch = item_ids[i : i + batch_size]

            payload = {
                "item_ids": batch,
            }

            yield scrapy.Request(
                url=url,
                method="POST",
                headers=self.COMMON_HEADERS,
                body=json.dumps(payload),
                callback=self.parse_details,
                meta={"location_map": location_map},
                dont_filter=True,
            )

    def parse_details(self, response):
        data = json.loads(response.text)
        location_map = response.meta["location_map"]

        for item in data:
            item_id = item.get("item_id")

            if item_id in location_map:
                item["lat"] = location_map[item_id]["lat"]
                item["lng"] = location_map[item_id]["lng"]

            if "addressOrigin" in item:
                item["addressOrigin"] = item["addressOrigin"].get("fullText", "")

            yield item
