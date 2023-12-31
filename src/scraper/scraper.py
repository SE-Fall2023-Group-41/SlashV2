# package imports
from bs4 import BeautifulSoup
import requests

# local imports
import scraper.formattr as form
from scraper.configs import AMAZON, WALMART, COSTCO, BESTBUY


def httpsGet(URL):
    """makes HTTP called to the requested URL with custom headers

    Parameters
    ----------
    URL: str
        URL we are sending request to

    Returns
    ----------
    soup: str
        HTML of page we requested
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36',  # noqa: E501
        'Accept-Encoding': 'gzip, deflate',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'no-cache'
    }
    s = requests.Session()
    try: 
        page = s.get(URL, headers=headers,timeout=4)
        if page.status_code == 200:
            soup1 = BeautifulSoup(page.content, 'html.parser')
            return BeautifulSoup(soup1.prettify(), 'html.parser')
        else:
            # TODO add logger
            return None
    except requests.exceptions.RequestException as e:
        print(e)
    except requests.exceptions.ReadTimeout as timeerr:
        print(timeerr)


#######This will need to be edited so the dictionary is in the correct format
def search(query, config):
    """Scrape the given config for a specific item

    Parameters
    ----------
    query: str
        Query of item we are looking for
    config: dict
        Configuration for site we are scraping

    Returns
    ----------
    products: list
        List of items returned from website
    """
    if config['site'] == 'costco':
        query = form.formatSearchQueryForCostco(query)
    else:
        query = form.formatSearchQuery(query)
    URL = config['url'] + query

    # fetch url
    print("httpget")
    page = httpsGet(URL)
    print("httpgot")
    if not page:
        return []

    # begin parsing page content
    results = page.find_all(config['item_component'], config['item_indicator'])
    products = []
    for res in results:
        title = res.select(config['title_indicator'])
        price = res.select(config['price_indicator'])
        link = res.select(config['link_indicator'])
        image_urls = res.select(config['image_url_indicator'])
        product = form.formatResult(config['site'], title, price, link,image_urls)
        products.append(product)
    return products


def scrape(args, scrapers):
    """Conduct scraping of sites based on scrapers

    Parameters
    ----------
    args: dict
        Dictionary of arguments used for scraping

        search : str [query to search on]
        scrapers: list [List of scrapers to use]
    
    Returns
    ----------
    overall: list
        List of items returned from scrapers
    """

    query = args['search']

    overall = []
    for scraper in scrapers:
        if scraper == 'walmart':
            print('walmart')
            local = search(query, WALMART)
        elif scraper == 'amazon':
            print('amazon')
            local = search(query, AMAZON)
        elif scraper == 'costco':
            print('costco')
            local = search(query, COSTCO)
        elif scraper == 'bestbuy':
            print('bestbuy')
            local = search(query, BESTBUY)
        else:
            continue

        overall.extend(local)

    return overall
