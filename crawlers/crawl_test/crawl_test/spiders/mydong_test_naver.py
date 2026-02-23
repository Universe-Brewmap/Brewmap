import scrapy
from urllib.parse import quote


class MyDongTestNaverSpider(scrapy.Spider):
    name = "mydong_test_naver"
    allowed_domains = ["m.map.naver.com", "m.place.naver.com"]

    def start_requests(self):
        query = "삼양동 카페"
        url = f"https://m.map.naver.com/search?query={quote(query)}"
        yield scrapy.Request(
            url,
            callback=self.parse,
            meta={"playwright": True, "playwright_include_page": True},
        )

    async def parse(self, response):
        items = response.css("#ct > div > ul > li")
        hrefs = response.css(
            "#ct > div > ul > li > div._item_info_sis14_45 > div._item_info_wrap_sis14_59 > a"
        )
        is_same_li_a_count = len(items) == len(hrefs)

        yield {
            "final_url": response.url,
            "status": response.status,
            "has_html": bool(response.text),
            # "content_length": len(response.text) if response.text else 0,
            "li_a_count_match": is_same_li_a_count,
        }

        # for idx, li in enumerate(items, start=1):
        #     a = li.css("div._item_info_sis14_45 > div._item_info_wrap_sis14_59 > a")
        #     yield {
        #         "index": idx,
        #         "href": a.attrib.get("href") if a else None,
        #         "html": li.get(),
        #         }

        cafe_list = []
        
        for li in items:
            a = li.css("div._item_info_sis14_45 > div._item_info_wrap_sis14_59 > a")
            detail_url = a.attrib.get("href") if a else None
            cafe_list.append(detail_url)
            if detail_url:
                yield response.follow(detail_url, callback=self.parse_detail)

        # yield {"cafe_list": cafe_list}

    def parse_detail(self, response):
        name = response.css("span.GHAhO::text").get()
        type = response.css("span.lnJFt::text").get()
        address = response.css("span.pz7wy::text").get()
        rating = response.xpath('//*[@id="app-root"]/div/div/div[2]/div[1]/div[2]/span[1]/text()').get()

        yield {
            "url": response.url,
            "name": name,
            "type": type,
            "address": address,
            "rating": rating,
        }
