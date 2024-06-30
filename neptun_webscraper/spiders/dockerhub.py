import scrapy
from scrapy_splash import SplashRequest
from scrapy.selector import Selector

# Splash (needed for JS support, if websites load content dynamically lazy) Settings

SPLASH_SETTINGS = {
    'SPLASH_URL': 'http://localhost:8050',

    'DOWNLOADER_MIDDLEWARES': {
        'scrapy_splash.SplashCookiesMiddleware': 723,
        'scrapy_splash.SplashMiddleware': 725,
        'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
    },

    'SPIDER_MIDDLEWARES': {
        'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
    },

    'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter',
    'HTTPCACHE_STORAGE': 'scrapy_splash.SplashAwareFSCacheStorage'
}

# HTML response with cookies, headers, body and method
splash_script = """
function main(splash)
  splash:init_cookies(splash.args.cookies)
  assert(splash:go{
    splash.args.url,
    headers=splash.args.headers,
    http_method=splash.args.http_method,
    body=splash.args.body,
    })
  assert(splash:wait(0.5))

  local entries = splash:history()
  local last_response = entries[#entries].response
  return {
    url = splash:url(),
    headers = last_response.headers,
    http_status = last_response.status,
    cookies = splash:get_cookies(),
    html = splash:html(),
  }
end
"""

# docker run -p 8050:8050 scrapinghub/splash --disable-private-mode
class DockerhubDockerRegistrySpider(scrapy.Spider):
    name = "dockerhubDockerRegistrySpider"
    custom_settings = SPLASH_SETTINGS

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(url, self.parse,
                endpoint='execute',
                cache_args=['lua_source'],
                args={
                    'wait': 5,
                    'images': 0,
                    'lua_source': splash_script
                },
                headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Referer': 'https://duckduckgo.com/',
                    'Connection': 'keep-alive'
                }) # (0 to 30 seconds)

    def parse(self, response):
        responseHTML = response.data['html']
        selector = Selector(text=responseHTML)
        print("response", responseHTML) # response.text is raw, response.body is splash html
        search_results = selector.css('#searchResults')

        if search_results:
            for result in search_results.xpath('./div'):
                yield self.parse_result(result)
        else:
            print("No search results found...")

    def parse_result(self, result):
        # extracts name, description, uploader, chips, downloads, stars, last update, pulls last week
        item = {}

        # Extract name
        name_elem = result.css('[data-testid="product-title"]::text').get()
        item['name'] = name_elem if name_elem else None

        # Extract uploader
        uploader_elem = result.css('span::text').re(r'^By (.+)')
        if uploader_elem:
            item['uploader'] = uploader_elem[0].strip()
        else:
            official_icon = result.css('[data-testid="official-icon"]')
            verified_publisher_icon = result.css('[data-testid="verified_publisher-icon"]')

            item['is_official_image'] = bool(official_icon)
            item['is_verified_publisher'] = bool(verified_publisher_icon)

        # Extract last update and description
        update_elem = result.css('span:contains("Updated")::text').get()
        if update_elem:
            item['last_update'] = update_elem.strip()
            desc_elem = result.xpath('following-sibling::p/text()').get()
            item['description'] = desc_elem.strip() if desc_elem else None
        else:
            item['last_update'] = None
            item['description'] = None

        # Extract chips (categories)
        chips = result.css('[data-testid="productChip"]::text').getall()
        item['chips'] = chips

        # Extract downloads (total pulls)
        download_icon = result.css('[data-testid="FileDownloadIcon"]')
        if download_icon:
            downloads = download_icon.xpath('following-sibling::p/text()').get()
            item['downloads'] = downloads.strip() if downloads else None

        # Extract pulls last week
        pulls_elem = result.css('span:contains("Pulls:")').xpath('following-sibling::p/text()').get()
        item['pulls_last_week'] = pulls_elem.replace(',', '') if pulls_elem else None

        # Extract stars
        stars_elem = result.css('[data-testid="StarOutlineIcon"] + span::text').get()
        item['stars'] = stars_elem.strip() if stars_elem else None

        return item

"""
SEARCH RESULT FORMAT (30.6.2024):

<div id="searchResults">
    <div>
        <!-- official image, no uploader -->
        <a class="MuiTypography-root MuiTypography-inherit MuiLink-root MuiLink-underlineAlways css-y94fv1" data-testid="imageSearchResult" href="/_/python">
            <div class="MuiPaper-root MuiPaper-outlined MuiPaper-rounded MuiCard-root css-g1ftw1">
                <div class="MuiCardContent-root css-18mhetb">
                    <div class="MuiStack-root css-n7cdi3">
                        <div class="MuiAvatar-root MuiAvatar-square css-1e4fgfe">
                            <img alt="python logo" src="https://djeqr6to3dedg.cloudfront.net/repo-logos/library/python/live/logo.png" data-testid="repository-logo" class="MuiAvatar-img css-j5vld0" />
                        </div>
                        <div class="MuiStack-root css-hw3iwf">
                            <div class="MuiStack-root css-95g4uk">
                                <div class="MuiStack-root css-u4p24i">
                                    <span class="MuiTypography-root MuiTypography-body1 css-60kwwm" data-testid="python-card"><strong data-testid="product-title">python</strong></span>
                                    <div class="MuiStack-root css-j7zhmx" data-testid="productLabel" aria-label="Docker Official Image">
                                        <svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeMedium css-6zii7g" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="official-icon">
                                            <path
                                                d="M9.68 13.69 12 11.93l2.31 1.76-.88-2.85L15.75 9h-2.84L12 6.19 11.09 9H8.25l2.31 1.84zM20 10c0-4.42-3.58-8-8-8s-8 3.58-8 8c0 2.03.76 3.87 2 5.28V23l6-2 6 2v-7.72c1.24-1.41 2-3.25 2-5.28m-8-6c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6 2.69-6 6-6"
                                            ></path>
                                        </svg>
                                    </div>
                                </div>
                                <div class="MuiStack-root css-19hiiex" data-testid="product-badges-and-data-count">
                                    <div class="MuiStack-root css-1prte9v">
                                        <svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeSmall css-17skkz3" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="FileDownloadIcon">
                                            <path d="M19 9h-4V3H9v6H5l7 7zM5 18v2h14v-2z"></path>
                                        </svg>
                                        <p class="MuiTypography-root MuiTypography-body1 css-12r72vy">1B+</p>
                                    </div>
                                    <span class="MuiBox-root css-19vr0ck">•</span>
                                    <div class="MuiStack-root css-3rf8ca">
                                        <svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeSmall css-17skkz3" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="StarOutlineIcon">
                                            <path d="m22 9.24-7.19-.62L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.63-7.03zM12 15.4l-3.76 2.27 1-4.28-3.32-2.88 4.38-.38L12 6.1l1.71 4.04 4.38.38-3.32 2.88 1 4.28z"></path>
                                        </svg>
                                        <span class="MuiTypography-root MuiTypography-body1 css-60kwwm"><strong>9.7K</strong></span>
                                    </div>
                                </div>
                            </div>
                            <div class="MuiStack-root css-19hiiex"><span class="MuiTypography-root MuiTypography-body1 css-1mod47s">Updated 3 days ago</span></div>
                            <p class="MuiTypography-root MuiTypography-body1 css-60kwwm">Python is an interpreted, interactive, object-oriented, open-source programming language.</p>
                            <div class="MuiStack-root css-1ulq31o">
                                <div
                                    class="MuiButtonBase-root MuiChip-root MuiChip-filled MuiChip-sizeSmall MuiChip-colorDefault MuiChip-clickable MuiChip-clickableColorDefault MuiChip-filledDefault css-1dymsti"
                                    tabindex="0"
                                    role="button"
                                    data-testid="productChip"
                                >
                                    <span class="MuiChip-label MuiChip-labelSmall css-12bfyr8">Languages &amp; Frameworks</span>
                                </div>
                            </div>
                        </div>
                        <div class="MuiStack-root css-nila4t">
                            <div class="MuiBox-root css-130f8nx">
                                <div class="MuiBox-root css-1ltqed5">
                                    <div class="MuiBox-root css-10klw3m">
                                        <div class="MuiBox-root css-6jxscl">
                                            <p class="MuiTypography-root MuiTypography-body1 css-60kwwm">Pulls:</p>
                                            <p class="MuiTypography-root MuiTypography-body1 css-60kwwm">6,904,987</p>
                                        </div>
                                        <p class="MuiTypography-root MuiTypography-body2 css-bsnwjs">Last week</p>
                                    </div>
                                    <div class="MuiBox-root css-1q8u9tk">
                                        <svg stroke="#1D63ED" viewBox="0 0 100 20" style="overflow: visible;">
                                            <line x1="0" y1="0" x2="12.5" y2="1.076822706961076" stroke-width="0.8"></line>
                                            <line x1="12.5" y1="1.076822706961076" x2="25" y2="1.808431138801808" stroke-width="0.8"></line>
                                            <line x1="25" y1="1.808431138801808" x2="37.5" y2="1.056464143021057" stroke-width="0.8"></line>
                                            <line x1="37.5" y1="1.056464143021057" x2="50" y2="1.1399469939011395" stroke-width="0.8"></line>
                                            <line x1="50" y1="1.1399469939011395" x2="62.5" y2="2.4877951956024873" stroke-width="0.8"></line>
                                            <line x1="62.5" y1="2.4877951956024873" x2="75" y2="1.0558844010010546" stroke-width="0.8"></line>
                                            <line x1="75" y1="1.0558844010010546" x2="87.5" y2="0.7186019326207173" stroke-width="0.8"></line>
                                            <line x1="87.5" y1="0.7186019326207173" x2="100" y2="2.0488290966020486" stroke-width="0.8"></line>
                                        </svg>
                                    </div>
                                    <div class="MuiBox-root css-s2uf1z">
                                        <a class="MuiTypography-root MuiTypography-inherit MuiLink-root MuiLink-underlineAlways DDSExternalLink-root css-1bbslhi" href="https://www.docker.com/partners/publisher-insights/" target="_blank">
                                            Learn more
                                            <span style="white-space: nowrap;">
                                                <svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeInherit DDSExternalLink-icon css-1cw4hi4" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="OpenInNewIcon">
                                                    <path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3z"></path>
                                                </svg>
                                            </span>
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </a>

        <!-- verified publisher, has uploader -->
        <a class="MuiTypography-root MuiTypography-inherit MuiLink-root MuiLink-underlineAlways css-y94fv1" data-testid="imageSearchResult" href="/r/cimg/python">
            <div class="MuiPaper-root MuiPaper-outlined MuiPaper-rounded MuiCard-root css-g1ftw1">
                <div class="MuiCardContent-root css-18mhetb">
                    <div class="MuiStack-root css-n7cdi3">
                        <div class="MuiAvatar-root MuiAvatar-square css-1e4fgfe">
                            <img alt="python logo" src="https://www.gravatar.com/avatar/0cbfb7f53476ae35e7f14c7ab3cef284?s=60&amp;r=g&amp;d=404" data-testid="repository-logo" class="MuiAvatar-img css-j5vld0" />
                        </div>
                        <div class="MuiStack-root css-hw3iwf">
                            <div class="MuiStack-root css-95g4uk">
                                <div class="MuiStack-root css-u4p24i">
                                    <span class="MuiTypography-root MuiTypography-body1 css-60kwwm" data-testid="cimg/python-card"><strong data-testid="product-title">cimg/python</strong></span>
                                    <div class="MuiStack-root css-mqw62i" data-testid="productLabel" aria-label="Verified Publisher">
                                        <svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeMedium css-6zii7g" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="verified_publisher-icon">
                                            <path
                                                d="m23 12-2.44-2.79.34-3.69-3.61-.82-1.89-3.2L12 2.96 8.6 1.5 6.71 4.69 3.1 5.5l.34 3.7L1 12l2.44 2.79-.34 3.7 3.61.82L8.6 22.5l3.4-1.47 3.4 1.46 1.89-3.19 3.61-.82-.34-3.69zm-12.91 4.72-3.8-3.81 1.48-1.48 2.32 2.33 5.85-5.87 1.48 1.48z"
                                            ></path>
                                        </svg>
                                    </div>
                                </div>
                                <div class="MuiStack-root css-19hiiex" data-testid="product-badges-and-data-count">
                                    <div class="MuiStack-root css-1prte9v">
                                        <svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeSmall css-17skkz3" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="FileDownloadIcon">
                                            <path d="M19 9h-4V3H9v6H5l7 7zM5 18v2h14v-2z"></path>
                                        </svg>
                                        <p class="MuiTypography-root MuiTypography-body1 css-12r72vy">100M+</p>
                                    </div>
                                    <span class="MuiBox-root css-19vr0ck">•</span>
                                    <div class="MuiStack-root css-3rf8ca">
                                        <svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeSmall css-17skkz3" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="StarOutlineIcon">
                                            <path d="m22 9.24-7.19-.62L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27 18.18 21l-1.63-7.03zM12 15.4l-3.76 2.27 1-4.28-3.32-2.88 4.38-.38L12 6.1l1.71 4.04 4.38.38-3.32 2.88 1 4.28z"></path>
                                        </svg>
                                        <span class="MuiTypography-root MuiTypography-body1 css-60kwwm"><strong>18</strong></span>
                                    </div>
                                </div>
                            </div>
                            <div class="MuiStack-root css-19hiiex">
                                <span class="MuiTypography-root MuiTypography-body1 css-1mod47s"><span>By CircleCI</span></span><span class="MuiBox-root css-19vr0ck">•</span>
                                <span class="MuiTypography-root MuiTypography-body1 css-1mod47s">Updated 3 months ago</span>
                            </div>
                            <div class="MuiStack-root css-1ulq31o">
                                <div
                                    class="MuiButtonBase-root MuiChip-root MuiChip-filled MuiChip-sizeSmall MuiChip-colorDefault MuiChip-clickable MuiChip-clickableColorDefault MuiChip-filledDefault css-1dymsti"
                                    tabindex="0"
                                    role="button"
                                    data-testid="productChip"
                                >
                                    <span class="MuiChip-label MuiChip-labelSmall css-12bfyr8">Languages &amp; Frameworks</span>
                                </div>
                                <div
                                    class="MuiButtonBase-root MuiChip-root MuiChip-filled MuiChip-sizeSmall MuiChip-colorDefault MuiChip-clickable MuiChip-clickableColorDefault MuiChip-filledDefault css-1dymsti"
                                    tabindex="0"
                                    role="button"
                                    data-testid="productChip"
                                >
                                    <span class="MuiChip-label MuiChip-labelSmall css-12bfyr8">Integration &amp; Delivery</span>
                                </div>
                                <div
                                    class="MuiButtonBase-root MuiChip-root MuiChip-filled MuiChip-sizeSmall MuiChip-colorDefault MuiChip-clickable MuiChip-clickableColorDefault MuiChip-filledDefault css-1dymsti"
                                    tabindex="0"
                                    role="button"
                                    data-testid="productChip"
                                >
                                    <span class="MuiChip-label MuiChip-labelSmall css-12bfyr8">Security</span>
                                </div>
                            </div>
                        </div>
                        <div class="MuiStack-root css-nila4t">
                            <div class="MuiBox-root css-130f8nx">
                                <div class="MuiBox-root css-1ltqed5">
                                    <div class="MuiBox-root css-10klw3m">
                                        <div class="MuiBox-root css-6jxscl">
                                            <p class="MuiTypography-root MuiTypography-body1 css-60kwwm">Pulls:</p>
                                            <p class="MuiTypography-root MuiTypography-body1 css-60kwwm">1,126,615</p>
                                        </div>
                                        <p class="MuiTypography-root MuiTypography-body2 css-bsnwjs">Last week</p>
                                    </div>
                                    <div class="MuiBox-root css-1q8u9tk">
                                        <svg stroke="#1D63ED" viewBox="0 0 100 20" style="overflow: visible;">
                                            <line x1="0" y1="0" x2="12.5" y2="1.754451921751445" stroke-width="0.8"></line>
                                            <line x1="12.5" y1="1.754451921751445" x2="25" y2="1.8079710598978238" stroke-width="0.8"></line>
                                            <line x1="25" y1="1.8079710598978238" x2="37.5" y2="0.5447823853027046" stroke-width="0.8"></line>
                                            <line x1="37.5" y1="0.5447823853027046" x2="50" y2="1.2713259896988605" stroke-width="0.8"></line>
                                            <line x1="50" y1="1.2713259896988605" x2="62.5" y2="2.309527091661758" stroke-width="0.8"></line>
                                            <line x1="62.5" y1="2.309527091661758" x2="75" y2="0.7630362043685863" stroke-width="0.8"></line>
                                            <line x1="75" y1="0.7630362043685863" x2="87.5" y2="0.4038247051894189" stroke-width="0.8"></line>
                                            <line x1="87.5" y1="0.4038247051894189" x2="100" y2="1.1753156969142537" stroke-width="0.8"></line>
                                        </svg>
                                    </div>
                                    <div class="MuiBox-root css-s2uf1z">
                                        <a class="MuiTypography-root MuiTypography-inherit MuiLink-root MuiLink-underlineAlways DDSExternalLink-root css-1bbslhi" href="https://www.docker.com/partners/publisher-insights/" target="_blank">
                                            Learn more
                                            <span style="white-space: nowrap;">
                                                <svg class="MuiSvgIcon-root MuiSvgIcon-fontSizeInherit DDSExternalLink-icon css-1cw4hi4" focusable="false" aria-hidden="true" viewBox="0 0 24 24" data-testid="OpenInNewIcon">
                                                    <path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3z"></path>
                                                </svg>
                                            </span>
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </a>
    </div>
</div>
"""