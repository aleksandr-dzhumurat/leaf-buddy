import os
from collections import defaultdict

import pandas as pd
from tqdm import tqdm

from utils import (
    save_html, request_smart, create_scraper, url_to_filename,
    get_id_hash, process_item
)

def scrape_leafly_catalog(html_dir, html_items_dir, items_description_dir, max_page=10, url_pattern='https://www.leafly.com/products/{category}?page={page_num}'):
    categories = [
        'cannabis/flower', 'cannabis/prerolls',
        'topicals/balms', 'topicals/lotions',
        'topicals/lubricants-oils',
        'edibles/beverages', 'edibles/brownies', 'edibles/candy', 'edibles/edible-capsules', 'edibles/cookies', 'edibles/gummies',
        'concentrates/cartridges', 'concentrates/badder',
        'concentrates/hash', 'concentrates/terpenes', 'vaping/portable-vaporizers', 'vaping/desktop-vaporizers',
        'smoking/pipes', 'smoking/rolling-papers', 'smoking/rolling-papers'
    ]
    entries = []
    cat_dict = defaultdict(int)
    CATEGORY_PAGE_TRIES = 1
    for category in categories:
        for page_num in range(1, max_page):
            if cat_dict[f'{category}_404'] > CATEGORY_PAGE_TRIES:
                break
            url = url_pattern.format(category=category, page_num=page_num)
            html_path = os.path.join(html_dir, url_to_filename(url))
            if not os.path.exists(html_path):
                code = save_html(request_smart(url), html_path)
                cat_dict[f'{category}_{code}'] += 1
            if os.path.exists(html_path):
                items_scraper = create_scraper(html_path)
                items = items_scraper.find_all(name='div', class_="grid grid-cols-1 mb-lg gap-md")
                for i in tqdm(items, desc="Processing items"):
                    title, link, item_url, doc_id = process_item(i)
                    html_item_path = os.path.join(html_items_dir, url_to_filename(link))
                    if len(html_item_path) > 120:
                        html_item_path = os.path.join(html_items_dir, f'{get_id_hash(url)}.html')
                    if not os.path.exists(html_item_path):
                        save_html(request_smart(item_url), html_item_path)
                    processed_file_name = os.path.join(items_description_dir, f"{doc_id}.txt")
                    entry = (doc_id, category, title, link, html_item_path, processed_file_name)
                    entries.append(entry)
    catalog_df = pd.DataFrame(entries, columns=['doc_id', 'category', 'title', 'link', 'file', 'processed_file_name'])
    return catalog_df


def dowlnload_leafly_items(ecom_catalog_prepared_df, html_dir, items_description_dir):
    base_url = 'https://www.leafly.com'
    entries = []
    for rn, row in ecom_catalog_prepared_df.iterrows():
        title, url = row['title'], base_url+row['link']
        # if rn % 50 == 0:
        #     display(HTML(f'<a href="{url}" target="_blank">{title}</a>'))
        html_path = os.path.join(html_dir, url_to_filename(url))
        # doc_id = f"doc_{get_id_hash()}"
        if not os.path.exists(html_path):
            code = save_html(request_smart(url), html_path)
        if os.path.exists(html_path):
            processed_file_name = os.path.join(items_description_dir, f"{row['ProductID']}.txt")
            entry = (row['ProductID'], title, row['link'], html_path, processed_file_name)
            entries.append(entry)
    catalog_df = pd.DataFrame(entries)
    catalog_df = pd.DataFrame(entries, columns=['doc_id', 'title', 'link', 'file', 'processed_file_name'])
    return catalog_df
