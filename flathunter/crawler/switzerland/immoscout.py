"""Expose crawler for ImmoScout24"""
import json
import re

import requests
from bs4 import BeautifulSoup
from flathunter.abstract_crawler import Crawler
from flathunter.logging import logger

STATIC_URL_PATTERN = re.compile(r'https://www\.immoscout24\.ch')


def get_image_url(image) -> str:
    url = image['url']
    return url.format(width=image['originalWidth'], height=image['originalHeight'], resizemode=1, quality=1000)


def get_address(street: str, plz: str, city_name: str) -> str:
    if street != '':
        return f'{street}, {plz} {city_name}'
    else:
        return f'{plz} {city_name}'


class Immoscout(Crawler):
    """Implementation of Crawler interface for ImmoScout24"""

    URL_PATTERN = STATIC_URL_PATTERN
    RESULT_LIMIT = 50
    JSON_PATTERN = re.compile(r'__INITIAL_STATE__')
    FLAT_LEFT_LIMIT = '"listData"'
    FLAT_RIGHT_LIMIT = '"pagingData"'
    PAGING_LEFT_LIMIT = '"pagingData"'
    PAGING_RIGHT_LIMIT = '"viewData"'

    def __init__(self, config):
        super().__init__(config)

    def get_results(self, search_url, max_pages=50) -> [{}]:
        """Loads the exposes from the ImmoScout24 site, starting at the provided URL"""
        if '&pn' in search_url:
            search_url = re.sub(r"&pn=[0-9]*", "&pn={0}", search_url)
        else:
            search_url = search_url + '&pn={0}'
        logger.debug("Got search URL %s", search_url)

        # load first page to get number of entries
        page_no = 1
        soup = self.get_page(search_url, None, page_no)

        # get data from first page
        entries = self.extract_data(soup)
        no_of_pages = self._get_paging(soup)['totalPages']

        # iterate over all remaining pages
        while page_no < no_of_pages and page_no < max_pages:
            logger.debug(
                '(Next page) Number of page: %d / Total number of pages: %d',
                page_no, no_of_pages)
            page_no += 1
            soup = self.get_page(search_url, None, page_no)
            cur_entry = self.extract_data(soup)
            entries.extend(cur_entry)

        return entries

    def get_page(self, search_url, driver=None, page_no=None) -> BeautifulSoup:
        """Applies a page number to a formatted search URL and fetches the exposes at that page"""
        return self.get_soup_from_url(search_url.format(page_no))

    def extract_data(self, soup) -> [{}]:
        """Should be implemented in subclass"""
        entries: [{}] = []
        script_data = str(soup.find('script', string=self.JSON_PATTERN).contents[0])
        flat_string = re.search(f'{self.FLAT_LEFT_LIMIT}:(.*?),{self.FLAT_RIGHT_LIMIT}', script_data).group(1)
        flat_data = json.loads(flat_string)
        for flat in flat_data:
            details = self._extract_details(flat)
            if details == {}:
                break
            for expose in entries:
                if details['id'] == expose['id']:
                    break
            entries.append(details)

        logger.debug('Number of entries found: %d', len(entries))
        return entries

    def crawl(self, url, max_pages=None):
        """Load as many exposes as possible from the provided URL"""
        if re.search(self.URL_PATTERN, url):
            try:
                return self.get_results(url, max_pages)
            except requests.exceptions.ConnectionError:
                logger.warning(
                    "Connection to %s failed. Retrying.", url.split('/')[2])
                return []
        return []

    def get_name(self):
        """Returns the name of this crawler"""
        return type(self).__name__

    def _get_paging(self, soup) -> {}:
        """Scrape the result count from the returned page"""
        script_data = str(soup.find('script', string=self.JSON_PATTERN).contents[0])
        paging_string = re.search(f'{self.PAGING_LEFT_LIMIT}:(.*?),{self.PAGING_RIGHT_LIMIT}', script_data).group(1)
        paging_data = json.loads(paging_string)
        return paging_data

    def _extract_details(self, flat: {}) -> {}:
        try:
            flat_id = flat['id']
            url = f'{self.URL_PATTERN.pattern.replace('\\', '')}{flat['propertyUrl']}'
        except KeyError:
            logger.error('Cannot load details from flat {' + flat + '}')
            return {}

        images = list(map(lambda image: get_image_url(image), flat['images'])) if 'images' in flat else []
        title = flat['title'] if 'title' in flat else 'Flat title'
        street = flat['street'] if 'street' in flat else ''
        plz = flat['zip'] if 'zip' in flat else ''
        city_name = flat['cityName'] if 'cityName' in flat else ''
        total_price = flat['price'] if 'price' in flat else -1
        price = flat['netPrice'] if 'netPrice' in flat else total_price
        size = str(flat['surfaceLiving']) if 'surfaceLiving' in flat else 'No info'
        rooms = str(flat['numberOfRooms']) if 'numberOfRooms' in flat else 'No info'
        available_from = str(flat['availableFromFormatted']) if 'availableFromFormatted' in flat else 'No info'

        return {
            'id': flat_id,
            'url': url,
            'image': images[0] if len(images) > 0 else None,
            'images': images,
            'title': title,
            'address': get_address(street, plz, city_name),
            'crawler': self.get_name(),
            'price': price,
            'total_price': total_price,
            'size': size,
            'rooms': rooms,
            'from': available_from,
        }
