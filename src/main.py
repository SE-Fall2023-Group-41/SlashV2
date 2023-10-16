# package imports
import uvicorn
from typing import Optional
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse
from pydantic import BaseModel
import csv
import psycopg2
import os 
from dotenv import load_dotenv

# local imports
import scraper.scraper as scr

deployment_env = os.getenv('DEPLOYMENT_ENV')
if deployment_env == 'production':
    load_dotenv('.env.prod')
elif deployment_env == 'compose':
    load_dotenv('.env.compose')
else:
    load_dotenv('.env.dev')

dbname = "quarkus"
user = "quarkus"
password = "quarkus"
host = os.getenv('DATABASE_HOST')
port="5432"
# response type define
class jsonScraps(BaseModel):
    timestamp: str
    title: str
    price: str
    website: str
    link: Optional[str] = None


# response type for variety count api
class analysisVarietyCountJson(BaseModel):
    website: str
    count: int


# response type for top cosy value per item over the website
class analysisTopCostJson(BaseModel):
    website: str
    lowest_price: float
    lowest_price_link: str
    highest_price: float
    highest_price_link: str


app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def read_root():
    '''Get documentation of API

    Parameters
    ----------
    None

    Returns
    ----------
    documentation redirect
    '''
    response = RedirectResponse(url='/redoc')
    return response

@app.get("/scrape")
def scrape():
    '''This function will trigger the scraper that will add items to our databse

    Parameters
    ----------
    None

    Returns
    ----------
    ideally, it will return something like "done"
    '''
    search_items_API("all","laptops")
    response = "done"
    return response

# @app.get("/{site}/{item_name}", response_model=List[jsonScraps])
def search_items_API(
    site: str,
    item_name: str,
    relevant: Optional[str] = None,
    order_by_col: Optional[str] = None,
    reverse: Optional[bool] = False,
    listLengthInd: Optional[int] = 50,
    export: Optional[bool] = False
):
    '''Wrapper API to fetch AMAZON, WALMART and TARGET query results

    Parameters
    ----------
    item_name: string of item to be searched

    Returns
    ----------
    itemListJson: JSON List
        list of search results as JSON List
    '''
    # logging in file
    file = open("logger.txt", "a")
    file.write(site +' query:' + str(item_name)+'\n')

    # building argument
    args = {
        'search': item_name,
        'sort': 'pr' if order_by_col == 'price' else 'pr',  # placeholder TDB
        'des': reverse,  # placeholder TBD
        'num': listLengthInd,
        'relevant': relevant
    }

    scrapers = []

    if site == 'az' or site == 'all':
        scrapers.append('amazon')
    if site == 'wm' or site == 'all':
        scrapers.append('walmart')
    if site == 'tg' or site == 'all':
        scrapers.append('target')
    if site == 'cc' or site == 'all':
        scrapers.append('costco')
    if site == 'bb' or site == 'all':
        scrapers.append('bestbuy')
    if site == 'eb' or site == 'all':
        scrapers.append('ebay')

    # calling scraper.scrape to fetch results
    itemList = scr.scrape(args=args, scrapers=scrapers)

    if not export and len(itemList) > 0:
        file.close()
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host,port=port)
        cursor = conn.cursor()
        # print(itemList)
        insert_sql = """
        INSERT INTO item (name, itemType, itemURl,itemImageURl,store,price,discountPrice) VALUES (%(title)s,%(item_type)s, %(link)s,%(link)s, %(website)s,%(price)s,%(price)s);
        """
        for items in itemList: 
            print(items)
            items["title"] = items["title"][:1024]
            items["item_type"] = item_name
            cursor.execute(insert_sql,items)
        conn.commit()
        cursor.close()
        conn.close()
    elif len(itemList) > 0:
        # returning CSV
        with open('slash.csv', 'w', encoding='utf8', newline='') as f:
            dict_writer = csv.DictWriter(f, itemList[0].keys())
            dict_writer.writeheader()
            dict_writer.writerows(itemList)
        return FileResponse('slash.csv', media_type='application/octet-stream', filename='slash_'+item_name+'.csv')
    else:
        # No results
        return None


@app.get("/analysis/varietyCount/all/{item_name}", response_model=List[analysisVarietyCountJson])
async def items_variety_count_analysis_API(
    item_name: str,
    order_by_col: Optional[str] = None,
    reverse: Optional[bool] = False
):
    ''' Wrapper API to fetch the count of number of varieties for a particular item found  in 
    AMAZON, WALMART, TARGET, COSTCO, BESTBUY, EBAY query results
    Parameters
    ----------
    item_name: string of item to be searched

    Returns
    ----------
    itemListJson: JSON List
        list of count of varieties of the item across all websites as JSON List
    '''

    # building argument
    args = {
        'search': item_name,
        'sort': 'pr' if order_by_col == 'price' else 'pr',  # placeholder TDB
        'des': reverse,  # placeholder TBD
    }

    itemList = getItemInfoByItemName(args)

    variety_count_dict = getVarietyCountByWebsite(itemList)

    variety_count_list = []
    for key, value in variety_count_dict.items():
        temp = {
            "website": key,
            "count": value
        }
        variety_count_list.append(temp)

    return variety_count_list


@app.get("/analysis/topCost/all/{item_name}", response_model=List[analysisTopCostJson])
async def items_top_cost_analysis_API(
    item_name: str,
    order_by_col: Optional[str] = None,
    reverse: Optional[bool] = False
):
    ''' Wrapper API to fetch the top lowest and highest price of item found in 
    AMAZON, WALMART, TARGET, COSTCO, BESTBUY, EBAY query results
    Parameters
    ----------
    item_name: string of item to be searched

    Returns
    ----------
    itemListJson: JSON List
        list of lowest and highest price of the item across all websites as JSON List
    '''

    # building argument
    args = {
        'search': item_name,
        'sort': 'pr' if order_by_col == 'price' else 'pr',  # placeholder TDB
        'des': reverse,  # placeholder TBD
    }

    itemList = getItemInfoByItemName(args)

    lowest_price_dict, lowest_price_link_dict,  highest_price_dict, highest_price_link_dict = getLowestHighestPriceByWebsite(itemList)

    price__list = []
    for key, value in lowest_price_dict.items():
        website = key
        lowest_price = value
        lowest_price_link = lowest_price_link_dict[key]
        highest_price = highest_price_dict[key]
        highest_price_link = highest_price_link_dict[key]
        temp = {
            "website": website,
            "lowest_price": lowest_price,
            "lowest_price_link": lowest_price_link,
            "highest_price": highest_price,
            "highest_price_link": highest_price_link
        }
        price__list.append(temp)

    return price__list


def getItemInfoByItemName(args):

    scrapers = []
    scrapers.append('amazon')
    scrapers.append('walmart')
    scrapers.append('costco')
    scrapers.append('bestbuy')

    # calling scraper.scrape to fetch results
    itemList = scr.scrape(args=args, scrapers=scrapers)
    return itemList


def getVarietyCountByWebsite(itemList):
    variety_count_dict = {
        'amazon': 0, 'walmart': 0, 'costco': 0, 'bestbuy': 0
    }

    # iterate and parse the itemlist to create a dict of website vs count
    for item in itemList:
        website = item['website']
        variety_count_dict[website] += 1

    return variety_count_dict


def getLowestHighestPriceByWebsite(itemList):
    lowest_price_dict = {
        'amazon': float('inf'), 'walmart': float('inf'), 'target': float('inf'), 'costco': float('inf'), 'bestbuy': float('inf'), 'ebay': float('inf')
    }

    lowest_price_link_dict = {
        'amazon': "", 'walmart': "", 'target': "", 'costco': "", 'bestbuy': "", 'ebay': ""
    }

    highest_price_dict = {
        'amazon': 0, 'walmart': 0, 'target': 0, 'costco': 0, 'bestbuy': 0, 'ebay': 0
    }

    highest_price_link_dict = {
        'amazon': "", 'walmart': "", 'target': "", 'costco': "", 'bestbuy': "", 'ebay': ""
    }

    for item in itemList:

        if(item['price'] == ''):
            continue
        website = item['website']
        price = getFloatPrice(item['price'])


        if(price < lowest_price_dict[website]):
            lowest_price_dict[website] = price
            lowest_price_link_dict[website] = item['link']
        
        if(price > highest_price_dict[website]):
            highest_price_dict[website] = price
            highest_price_link_dict[website] = item['link']

    return lowest_price_dict, lowest_price_link_dict, highest_price_dict, highest_price_link_dict


def getFloatPrice(price):
    temp = ""
    float_price = 0
    
    for ch in price:
        if (ch >= '0' and ch <= '9') or (ch == '.'):
            temp += ch
    if temp:
        float_price = float(temp)
    return float_price


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)