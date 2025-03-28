import os

from utils import get_id_hash, url_to_filename, create_scraper

from tqdm import tqdm
import pandas as pd

from utils import save_html, request_smart, save_file, prepare_dirs
from matching import find_match

searh_url = 'https://www.leafly.com/shop?q={q}'
brand_filter = '&filter%5Bbrand_name%5D={brand}'


root_data_dir = os.environ['ROOT_DATA_DIR']
data_version = 'e6da18c153cb' # set_data_version()

root_html_dir = os.path.join(root_data_dir, 'search', f'search_{data_version}')
if not os.path.exists(root_html_dir):
    os.mkdir(root_html_dir)
output_dir = os.path.join(root_data_dir, 'pipelines-data', 'matched_data')
if not os.path.exists(output_dir):
    os.mkdir(output_dir)
app_file_output_path = os.path.join(root_data_dir, 'app_matched_leafly_sweed_dataset.csv')


leafly_catalog_url = 'https://www.leafly.com/shop'
def brand_matching():
    """NOTE: NOT USED!!!"""
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
    sales_df = pd.read_csv(os.path.join(os.environ['ROOT_DATA_DIR'], 'pipelines-data', 'sales_dataset_ffb59da3.csv.gzip'))
    sweed_catalog_df = (
        sweed_catalog_df
        .join(sales_df.select(['ProductID']), on='ProductID')
    )
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

def prepare_search_results(queries, root_html_dir):
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
    print('Data prepared in {root_html_dir}')

def concat_search_results(leafly_search_results, sweed_catalog_df):
    matched_catalog = (
             pd.concat([
                pd.read_csv(os.path.join(leafly_search_results, i))
                for i in os.listdir(leafly_search_results) if '.csv' in i
            ])
     )
    search_results_df = (
        sweed_catalog_df
        .merge(matched_catalog.rename(columns={'sweed_product_id': 'ProductID', 'purchase_count': 'sweed_purchases'}), on='ProductID')
        .sort_values(by='purchase_count', ascending=False)
    )
    print(search_results_df.shape[0])
    search_results_df.to_csv(os.path.join('/Users/username/PycharmProjects/leaf-buddy/data/search', 'sweed_leafly_mapping.csv'), index=False)
    return search_results_df

def prepare_sweed_catalog():
    data_version = 'ffb59da3'
    sweed_catalog_df = pd.read_csv(os.path.join(os.environ['ROOT_DATA_DIR'], 'pipelines-data', f'products_dataset_{data_version}.csv.gzip'))
    print(f"Catalog length {sweed_catalog_df.shape[0]}, {sweed_catalog_df['ProductCategory'].unique()}")
    sales_df = pd.read_csv(os.path.join(os.environ['ROOT_DATA_DIR'], 'pipelines-data', f'sales_dataset_{data_version}.csv.gzip'))
    product_sales_df = (
        sales_df
        .groupby('ProductID')['CustomerID'].count()
        .reset_index(name='purchase_count').sort_values(by='purchase_count', ascending=False)
    )
    res = (
        product_sales_df
        .merge(sweed_catalog_df[['ProductID', 'ProductName', 'ProductCategory', 'ProductBrand']], on='ProductID')
    )
    return res
import random

def prepare_matching(mapping_df, output_dir, products_list):
    for i in products_list:
        output_file_name = f'{i}.csv'
        output_file = os.path.join(output_dir, output_file_name)
        if not os.path.exists(output_file):
            sub_df = mapping_df[mapping_df['ProductID'] == i].copy()
            sub_df['row_num'] = sub_df.reset_index().index + 1
            sub_df = find_match(sub_df)
            sub_df.to_csv(output_file, index=False)
        else:
            # print(f'File exists: {output_file_name}')
            pass
    print(f'All done! Num files: {len(os.listdir(output_dir))}')

def dowlnload_leafly_items(html_dir, items_description_dir):
    base_url = 'https://www.leafly.com'
    entries = []
    for rn, row in ecom_catalog_prepared_df.iterrows():
        title, url = row['title'], base_url+row['link']
        if rn % 50 == 0:
            print(f'{url}: {title}'))
        html_path = os.path.join(html_dir, url_to_filename(url))
        doc_id = f"doc_{get_id_hash()}"
        if not os.path.exists(html_path):
            code = save_html(request_smart(url), html_path)
        if os.path.exists(html_path):
            processed_file_name = os.path.join(items_description_dir, f"{doc_id}.txt")
            entry = (doc_id, title, row['link'], html_path, processed_file_name)
            entries.append(entry)
    catalog_df = pd.DataFrame(entries)
    catalog_df = pd.DataFrame(entries, columns=['doc_id', 'title', 'link', 'file', 'processed_file_name'])
    return catalog_df

def prepare_ecom_catalog(catalog_df):
    base_url = 'https://www.leafly.com'
    errors = []
    for _, row in tqdm(catalog_df.iterrows(), desc="Processing items"):
        link=row['link']
        page_scraper = create_scraper(row['file'])
        try:
            item_descriprion = page_scraper.find(name='div', class_='bg-white border-t border-light-grey').find(name='section', class_="max-w-[700px]").find(name='p')
            res = item_descriprion.text
            item_reviews = page_scraper.find_all(name='div', class_='inline-block mb-lg w-full')
            for review in item_reviews:
                print('=)')
                res += '\n' + review.find(name='div', class_='mb-lg').text
            save_file(res, row['processed_file_name'])
        except AttributeError:
            errors.append(f'Parsing error: {base_url}{link}')
            save_file('', row['processed_file_name'])
    print(f'Catalog saved, num errors {len(errors)}')

if __name__ == '__main__':
    # from utils import clear_exprired_files
    # clear_exprired_files(root_html_dir, 0)

    # queries = [
    #     {'q': 'Ghost+Milk', 'brand': 'Verano'}
    # ]
    queries = prepare_verano_product()
    prepare_search_results(queries, root_html_dir)
    sweed_catalog_df = prepare_sweed_catalog()
    search_results_df = concat_search_results(root_html_dir, sweed_catalog_df)
    search_link_dedupled_df = search_results_df[['title', 'link']].groupby('title').agg(lambda x: x.iloc[0]).reset_index()
    mapping_df = search_results_df[['ProductID', 'ProductName', 'ProductBrand', 'sweed_product_name', 'title', 'brand', 'doc_id']].drop_duplicates()
    products_list = mapping_df['ProductID'].unique().tolist()
    print(f'Num products in list {len(products_list)}')
    # prepare_matching(output_dir, products_list)
    file_list = os.listdir(output_dir)
    final_df = pd.concat([pd.read_csv(os.path.join(output_dir, i)) for i in file_list])
    ecom_catalog_prepared_df = (
        final_df[~final_df['match_confidence'].isna()][['ProductID', 'ProductName', 'ProductBrand', 'title', 'brand', 'match_confidence']]
        .merge(search_link_dedupled_df, on='title')
    )
    print(f'Num rows: {ecom_catalog_prepared_df.shape[0]}')
    ecom_catalog_prepared_df.to_csv(app_file_output_path, index=False)
    print(f'data saved to {app_file_output_path}')
    items_description_dir, html_items_dir, html_dir = prepare_dirs(root_data_dir, data_version, prefix='catalog_ecom_')
    catalog_path = os.path.join(root_data_dir, f'leafly_ecom_catalog_{data_version}.csv')
    if os.path.exists(catalog_path):
        catalog_df = pd.read_csv(catalog_path)
    else:
        catalog_df = dowlnload_leafly_items(html_dir, items_description_dir)
        catalog_df.to_csv(catalog_path, index=False)
    print(f"Num items in catalog: {catalog_df.shape[0]}")
    precessed_files = os.listdir(items_description_dir)
    prepare_ecom_catalog(catalog_df)
    