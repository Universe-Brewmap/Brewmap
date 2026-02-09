import scrapy
from urllib.parse import quote
from scrapy_playwright.page import PageMethod

class MyDongTestKakaoSpider(scrapy.Spider):
    name = "mydong_test_kakao"
    allowed_domains = ["m.map.kakao.com"]

    def start_requests(self):
        query = "삼양동 카페"
        url = f"https://m.map.kakao.com/actions/searchView?q={quote(query)}"

        yield scrapy.Request(
            url,
            callback=self.parse,
            errback=self.errback,
            meta={
                "playwright": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_load_state", "domcontentloaded"),
                    PageMethod(
                        "click",
                        "#daumWrap > div.comm_popup.leverage_popup.hide > div > "
                        "div.popup_foot > a.btn_close",
                        timeout=5000,
                        force=True,
                    ),
                    PageMethod("wait_for_timeout", 1000),  # 초기 로딩 대기
                    PageMethod("evaluate", """
                        async () => {
                            const buttonSelector = '#daumContent > div.list_content_wrap > div.search_result_wrap > div.search_result_place_body > a';
                            let clickCount = 0;
                            const maxClicks = 50; // 무한루프 방지
                            
                            while (clickCount < maxClicks) {
                                const button = document.querySelector(buttonSelector);
                                
                                if (!button || button.offsetParent === null) {
                                    console.log('더보기 버튼 없음 또는 숨겨짐');
                                    break;
                                }
                                
                                button.click();
                                clickCount++;
                                
                                // 새로운 데이터 로딩 대기
                                await new Promise(resolve => setTimeout(resolve, 800));
                            }
                            
                            console.log(`총 ${clickCount}번 클릭 완료`);
                        }
                    """),
                    PageMethod("wait_for_timeout", 1000),  # 최종 렌더링 대기
                ],
            },
        )

    def parse(self, response):
        items = response.css("#placeList > li")

        if not items:
            self.logger.warning("no_places")

            yield {
                "debug": "no_places",
                "final_url": response.url,
                "status": response.status,
                "html_len": len(response.text) if response.text else 0,
                "title": response.css("title::text").get(),
            }
            return

        else:
            yield{
                "len": len(items)
            }

        for place in items:
            name = place.css("a.link_result span.info_result span.txt_tit strong::text").get()
            address = place.css("a.link_result span.info_result span.txt_g::text").get()
            type = place.css("a.link_result span.info_result span.txt_tit span::text").get()
            rating = place.css(
                "a.link_result span.info_result span.info_detail "
                "span.ico_comm.star_rate em::text"
            ).get()

            yield {
                "name": name,
                "address": address,
                "type": type,
                "rating": rating,
            }


    def errback(self, failure):
        self.logger.error(f"request_failed={failure.value}")