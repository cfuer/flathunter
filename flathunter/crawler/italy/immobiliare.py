"""Expose crawler for Immobiliare"""
import re

from flathunter.logging import logger
from flathunter.abstract_crawler import Crawler


class Immobiliare(Crawler):
    """Implementation of Crawler interface for Immobiliare"""

    URL_PATTERN = re.compile(r'https://www\.immobiliare\.it')

    def __init__(self, config):
        super().__init__(config)
        self.config = config

    # pylint: disable=too-many-locals
    def extract_data(self, soup):
        """Extracts all exposes from a provided Soup object"""
        entries = []

        results = soup.find(
            'ul', {"class": "in-realEstateResults"})

        items = results.find_all(lambda l: l.has_attr(
            'class') and "in-realEstateResults__item" in l['class']
            and "in-realEstateResults__carouselAgency" not in l["class"])

        for row in items:
            title_row = row.find('a', {"class": "in-reListCard__title"})
            title = title_row.text.strip()
            url = title_row['href']
            flat_id = title_row['href'].split("/")[-2:][0]

            image_item = row.find_all('img')
            image = image_item[0]['src'] if image_item else ""

            # the items arrange like so:
            # 0: price
            # 1: number of rooms
            # 2: size of the apartment
            details_list = row.find(
                "ul", {"class": "in-reListCard__features"})

            price_li = row.find(
                "div", {"class": "in-reListCardPrice"})

            price_re = re.match(
                r".*\s([0-9]+.*)$",
                # if there is a discount on the price, then there will be a <div>,
                # otherwise the text we are looking for is directly inside the <li>
                (price_li.find("div") if price_li.find(
                    "div") else price_li).text.strip()
            )
            price = "???"
            if price_re is not None:
                price = price_re[1]

            rooms_el = details_list.find(attrs={"aria-label":re.compile(r'local[ie]')})
            rooms = None
            if rooms_el is not None:
                rooms = rooms_el.text.strip()
            size_el = details_list.find(attrs={"aria-label":"superficie"})
            size = None
            if size_el is not None:
                size = size_el.text.strip()

            address_match = re.match(r"\w+\s(.*)$", title)
            address = address_match[1] if address_match else ""

            details = {
                'id': int(flat_id),
                'image': image,
                'url': url,
                'title': title,
                'price': price,
                'size': size,
                'rooms': rooms,
                'address': address,
                'crawler': self.get_name()
            }

            entries.append(details)

        logger.debug('Number of entries found: %d', len(entries))

        return entries
