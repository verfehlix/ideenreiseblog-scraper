import scrapy


class IdeenreiseblogSpider(scrapy.Spider):
    name = "ideenreiseblog"

    def start_requests(self):
        urls = [
            'https://ideenreise-blog.de/category/mathematik',
            'https://ideenreise-blog.de/category/mathematik/page/2',
            'https://ideenreise-blog.de/category/mathematik/page/3',
            'https://ideenreise-blog.de/category/mathematik/page/4',
            'https://ideenreise-blog.de/category/mathematik/page/5',
            'https://ideenreise-blog.de/category/mathematik/page/6',
            'https://ideenreise-blog.de/category/mathematik/page/7',
            'https://ideenreise-blog.de/category/mathematik/page/8',
            'https://ideenreise-blog.de/category/mathematik/page/9',
            'https://ideenreise-blog.de/category/mathematik/page/10',
            'https://ideenreise-blog.de/category/mathematik/page/11',
            'https://ideenreise-blog.de/category/mathematik/page/12',
            'https://ideenreise-blog.de/category/mathematik/page/13',
            'https://ideenreise-blog.de/category/mathematik/page/14',
            'https://ideenreise-blog.de/category/mathematik/page/15',
            'https://ideenreise-blog.de/category/mathematik/page/16',
            'https://ideenreise-blog.de/category/mathematik/page/17',
            'https://ideenreise-blog.de/category/mathematik/page/18',
            'https://ideenreise-blog.de/category/mathematik/page/19'
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse_overview_page)

    def parse_overview_page(self, response):
        links_to_posts = self.get_all_post_links_from_category_page(response)

        for link in links_to_posts:
            yield scrapy.Request(url=link, callback=self.parse_post_page)

    def parse_post_page(self, response):
        links_to_file_downloads = self.get_all_file_download_links_from_post_page(
            response)

        yield {
            'post': self.get_title_from_post_page(response),
            'url': response.request.url,
            'date': response.request.url.split("/")[4] + "-" + response.request.url.split("/")[3],
            'files': links_to_file_downloads
        }

    def get_all_post_links_from_category_page(self, response):
        # collect hrefs from all "Weiterlesen" buttons
        return response.css('.post_more a::attr(href)').getall()

    def get_title_from_post_page(self, response):
        return response.css('.entry_title::text').get().strip()

    def get_all_file_download_links_from_post_page(self, response):
        all_links = response.css('.post_text a::attr(href)').getall()

        file_download_links_only = list(filter(
            lambda link: 'drive.google.com' in link or 'my.hidrive.com' in link or 'dropbox.com' in link, all_links))

        return file_download_links_only
