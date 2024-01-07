import pytest
import requests

from flathunter.crawler.switzerland.immoscout import Immoscout
from test.utils.config import StringConfigWithCaptchas
from unittest.mock import MagicMock, patch

DUMMY_CONFIG = """
urls:
  - https://www.immoscout24.ch/de/immobilien/mieten/ort-zuerich?pt=35h&nrf=2
    """

BASE_URL = 'https://www.immoscout24.ch/'

test_config = StringConfigWithCaptchas(string=DUMMY_CONFIG)
de_path = 'de/immobilien/mieten/ort-zuerich?pt=35h&nrf=2'
fr_path = 'fr/immobilier/louer/lieu-geneve?pt=35h&nrf=2'
it_path = 'it/immobili/affittare/luogo-lugano?pt=35h&nrf=2'
en_path = 'en/real-estate/rent/city-bern?pt=35h&nrf=2'


@pytest.fixture
def crawler():
    return Immoscout(test_config)


@pytest.mark.parametrize("path", [de_path, fr_path, it_path, en_path])
def test_get_page_and_extract_data_works_for_all_languages(crawler: Immoscout, path: str):
    url = BASE_URL + path
    soup = crawler.get_page(url)
    assert soup is not None
    entries = crawler.extract_data(soup)
    assert entries is not None
    print(crawler._get_paging(soup))
    assert len(entries) == crawler._get_paging(soup)['itemsOnPage']
    assert entries[0]['id'] > 0
    assert entries[0]['url'].startswith("https://www.immoscout24.ch/")
    for expose in entries:
        for attr in ['image', 'images', 'title', 'address', 'crawler', 'price', 'total_price', 'size', 'rooms', 'from']:
            assert expose[attr] is not None


@pytest.mark.skip(reason="Manually check that impossible path really does not find any flats before running the test")
def test_get_page_returns_empty_list_when_no_flats_are_found(crawler: Immoscout):
    impossible_path = 'de/immobilien/mieten/ort-zuerich?pt=5h&nrf=8'
    url = BASE_URL + impossible_path
    soup = crawler.get_page(url)
    assert soup is not None
    entries = crawler.extract_data(soup)
    assert entries == []


def test_get_results(crawler: Immoscout):
    url = BASE_URL + it_path
    entries = crawler.get_results(url)
    soup = crawler.get_page(url)
    assert len(entries) == crawler._get_paging(soup)['totalMatches']


@pytest.mark.parametrize("url,match_pattern", [(BASE_URL + fr_path, True), ('https://www.immoscout.ch/' + fr_path, False)])
@patch.object(Immoscout, 'get_results')
def test_crawl_gets_results_when_url_matches_url_pattern(mock_get_results: MagicMock, crawler: Immoscout, url: str,
                                                         match_pattern: bool):
    mock_get_results.return_value = []
    max_pages = 20
    entries = crawler.crawl(url, max_pages)
    if match_pattern:
        mock_get_results.assert_called_once_with(url, max_pages)
    else:
        mock_get_results.assert_not_called()
        assert entries == []
    mock_get_results.reset_mock()


@patch.object(Immoscout, 'get_results')
def test_crawl_returns_empty_list_when_get_result_throws_error(mock_get_results: MagicMock, crawler: Immoscout):
    mock_get_results.side_effect = requests.exceptions.ConnectionError('Get results throws an error')
    url = BASE_URL + de_path
    max_pages = 20
    entries = crawler.crawl(BASE_URL + de_path, max_pages)
    mock_get_results.assert_called_once_with(url, max_pages)
    assert entries == []
