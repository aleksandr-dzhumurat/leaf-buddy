import os

from utils import get_id_hash, url_to_filename, create_scraper

from tqdm import tqdm
import pandas as pd

from utils import save_html, request_smart

searh_url = 'https://www.leafly.com/shop?q={q}'
brand_filter = '&filter%5Bbrand_name%5D={brand}'


root_data_dir = os.environ['ROOT_DATA_DIR']
data_version = 'e6da18c153cb' # set_data_version()

root_html_dir = os.path.join(root_data_dir, 'search', f'search_{data_version}')
if not os.path.exists(root_html_dir):
    os.mkdir(root_html_dir)

leafly_catalog_url = 'https://www.leafly.com/shop'
def brand_matching():
    html_path = os.path.join(root_data_dir, 'search', 'leafly_shop_2.html')
    if os.path.exists(html_path):
        print('-->')
        items_scraper = create_scraper(html_path)
        # all_filters = items_scraper.find_all(name='div', class_="overflow-auto max-h-80", attrs={"data-testid": "filter-checkbox-list"})
        all_filters = items_scraper.find_all(name='div', class_='border-t border-b border-light-grey', attrs={"data-testid": "filter-section"})
        for f in all_filters:
            filter_group = f.find(name='span', class_='font-bold').text
            if filter_group == 'Brands':
                current_filter = f.find(name='div', class_="overflow-auto max-h-80", attrs={"data-testid": "filter-checkbox-list"})
                for i in current_filter.find_all('a'):
                    print(i['href'])
            # input_element = f.find(name='input', id="Dispensary-search-input", attrs={"type": "text", "name": "search"})
            # print(input_element.get('aria-label'))
            #items = items_scraper.find_all(name='div', class_="relative shadow-low rounded p-lg mb-md")
    else:
        raise RuntimeError

def prepare_verano_product():
    get_product_brand = {
        'Verano': 'Verano',
        'MÜV': 'Verano',
        '(the) Essence': '(the)+Essence',
    }

    sweed_catalog_df = pd.read_csv(os.path.join(os.environ['ROOT_DATA_DIR'], 'pipelines-data', 'products_dataset_ffb59da3.csv.gzip'))
    print(f"Catalog length {sweed_catalog_df.shape[0]}, {sweed_catalog_df['ProductCategory'].unique()}")
    res = [
        {
            'q': i['ProductName'].replace(' ', '+'),
            'brand': get_product_brand.get(i['ProductBrand']),
            'sweed_product_name': i['ProductName'],
            'sweed_product_id': i['ProductID'],
        }
        for i in sweed_catalog_df.to_dict(orient='records')
    ]
    return res 

# to do: prepare verano products list
queries = [
    {'q': 'Ghost+Milk', 'brand': 'Verano'}
]
queries = prepare_verano_product()


def process_item(i, base_url = 'https://www.leafly.com'):
    brand = i.find(name='div', class_="text-secondary text-xs").text
    title = i.find(name='div', class_='font-bold mb-xs md:truncate').text
    link = i.find('a')['href']
    item_url = f'{base_url}{link}'
    doc_id = f"doc_{get_id_hash()}"
    price_section = i.find(name='div', class_='flex items-baseline mb-xs')
    if price_section is not None:
        price = price_section.find(name='div', class_='font-bold text-lg mr-xs').text
        uom = price_section.find(name='div', class_='text-xs').text
    else:
        price = uom = 'N/A'
    return [title, doc_id, brand, link, item_url, price, uom]

# from utils import clear_exprired_files
# clear_exprired_files(root_html_dir, 0)

for q in queries:
    url = searh_url.format(**q)
    if q['brand'] is not None:
        url = url + brand_filter.format(**q)
    html_path = os.path.join(root_html_dir, url_to_filename(url))
    if not os.path.exists(html_path):
        code = save_html(request_smart(url), html_path)
    output_path = os.path.join(root_html_dir, f"{q['q']}_search_results_{data_version}.csv")
    if os.path.exists(output_path):
        print(f'Search results exists: {output_path}')
        continue
    if os.path.exists(html_path):
        items_scraper = create_scraper(html_path)
        items = items_scraper.find_all(name='div', class_="relative shadow-low rounded p-lg mb-md")
        entries = []
        for i in tqdm(items, desc="Processing items"):
            entries.append([q['sweed_product_name'], q['sweed_product_id']] + process_item(i))
        search_df = pd.DataFrame(entries, columns=['sweed_product_name', 'sweed_product_id', 'title', 'doc_id', 'brand', 'link', 'item_url', 'price', 'uom'])
        search_df.to_csv(output_path, index=False)
