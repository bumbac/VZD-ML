import scrapy

data = {
    'prace' : 'BP', # DP = diplomka, DR = disertace, RI = rigorozní
    'nazev' : '%%%', # alespoň tři písmena z názvu hledané práce
    'pocet' : '0',
    'klic' : '', # alespoň tři písmena z klíčových slov
    'kl' : 'c', # c = částečně odpovídá, n = plně odpovídá
    'hledat' : 'Vyhledat'
}

pages_to_crawl = 10

class UJAKSpider(scrapy.Spider):
    name = 'UJAKSpider'
    start_urls = ['https://kap.ujak.cz/index.php']

    custom_settings = {
        'USER_AGENT': 'Crawler',
        'DOWNLOAD_DELAY': 1,
        'ROBOTSTXT_OBEY': True
    }

    crawled_pages = 0

    core_page = 'https://kap.ujak.cz'
    
    def parse_page(self, response):
        print("Parsing single page")

        if self.crawled_pages >= pages_to_crawl:
        	return

        self.crawled_pages += 1

        for row in response.css("table").css('tr'):
        	data = row.css("td")

        	if len(data) > 0:
        		yield{
        			"Author": data[0].css("td::text").get(),
        			"Title": data[1].css("td").css("a::text").get(),
        			"Reference": data[1].css("td").css("a::attr(href)").get(),
        			"Supervisor": data[2].css("td::text").get(),
        			"Year": data[3].css("td::text").get(),
        			"Thesis type": data[4].css("td::text").get()
        		}

        next_page = response.css("p[class*=pp]").css("a::attr(href)").extract()[-1]

        yield scrapy.Request(self.core_page + "/" + next_page, callback=self.parse_page)

    
    def parse(self, response):
        """
        Parses the first page and starts the sequence in order to parse the rest of the website

        :param response: Response that will be parsed
        """

        print("Parsing started")

        for prace in ["BP", "DP"]:
        	print("Parsing", prace)
        	data['prace'] = prace

        	yield scrapy.FormRequest(self.start_urls[0], formdata=data, callback=self.parse_page)
