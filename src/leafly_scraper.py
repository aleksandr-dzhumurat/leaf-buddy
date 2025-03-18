import os
from uuid import uuid4

import pandas as pd
from tqdm import tqdm

from utils import save_html, request_smart, create_scraper, url_to_filename, save_file

root_data_dir = os.environ['ROOT_DATA_DIR']
html_data_dir = 'leafly_html_pages'
html_dir = os.path.join(root_data_dir, html_data_dir)
if not os.path.exists(html_dir):
    os.mkdir(html_dir)
html_items_dir = os.path.join(html_dir, 'items_html_pages')
if not os.path.exists(html_items_dir):
    os.mkdir(html_items_dir)
items_description_dir = os.path.join(html_dir, 'items_descriptions')
if not os.path.exists(items_description_dir):
    os.mkdir(items_description_dir)
print(items_description_dir)

base_url = 'https://www.leafly.com'

def scrape_leafly_catalog(html_dir):
    categories = [
        'cannabis/flower', 'cannabis/prerolls',
        'edibles/beverages', 'edibles/brownies', 'edibles/candy', 'edibles/edible-capsules',
        'concentrates/cartridges', 'concentrates/badder',
        'concentrates/hash', 'concentrates/terpenes', 'vaping/portable-vaporizers', 'vaping/desktop-vaporizers',
        'smoking/pipes', 'smoking/rolling-papers', 'smoking/rolling-papers'
    ]
    max_page = 10

    entries = []
    for category in categories:
        for page_num in range(1, max_page):
            url = f'https://www.leafly.com/products/{category}?page={page_num}'
            html_path = os.path.join(html_dir, url_to_filename(url))
            if not os.path.exists(html_path):
                save_html(request_smart(url), html_path)
            if os.path.exists(html_path):
                items_scraper = create_scraper(html_path)
                items = items_scraper.find_all(name='div', class_="grid grid-cols-1 mb-lg gap-md")
                for i in tqdm(items, desc="Processing items"):
                    title = i.find(name='div', class_="font-bold text-sm leading-normal").text
                    link = i.find('a')['href']
                    item_url = f'{base_url}{link}'
                    html_item_path = os.path.join(html_items_dir, url_to_filename(link))
                    if not os.path.exists(html_item_path):
                        save_html(request_smart(item_url), html_item_path)
                    doc_id = f"doc_{uuid4()}"
                    processed_file_name = os.path.join(items_description_dir, f"{doc_id}.txt")
                    entry = (doc_id, category, title, link, html_item_path, processed_file_name)
                    entries.append(entry)
    catalog_df = pd.DataFrame(entries, columns=['doc_id', 'category', 'title', 'link', 'file', 'processed_file_name'])
    return catalog_df

def prepare_catalog(catalog_df):
    errors = []
    for _, row in tqdm(catalog_df.iterrows(), desc="Processing items"):
        link=row['link']
        page_scraper = create_scraper(row['file'])
        item_descriprion = page_scraper.find(name='div', class_='flex flex-col gap-lg').find(name='div', class_="bg-white")
        try:
            save_file(item_descriprion.text, row['processed_file_name'])
        except AttributeError:
            errors.append(f'Parsing error: {base_url}{link}')
            save_file('', row['processed_file_name'])
    print(f'Catalog saved, num errors {len(errors)}')

catalog_path = os.path.join(root_data_dir, 'leafly_catalog.csv')
if os.path.exists(catalog_path):
    catalog_df = pd.read_csv(catalog_path)
else:
    catalog_df = scrape_leafly_catalog(html_dir)
    catalog_df.to_csv(catalog_path, index=False)
print(f"Num items in catalog: {catalog_df.shape[0]}")
precessed_files = os.listdir(items_description_dir)
if len(precessed_files) == 0:
    prepare_catalog(catalog_df)
