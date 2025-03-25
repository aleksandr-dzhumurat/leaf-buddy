import os

import pandas as pd
from tqdm import tqdm

from utils import (
    create_scraper, save_file,
    read_json, prepare_dirs,
    set_data_version
)
from scrape_tools import scrape_leafly_catalog

root_data_dir = os.environ['ROOT_DATA_DIR']
config = read_json(os.environ['CONFIG_DIR'], 'config.json')
data_version = set_data_version(config, root_data_dir)
base_url = 'https://www.leafly.com'


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

if __name__ == '__main__':
    print(f'Data version: {data_version}')
    items_description_dir, html_items_dir, html_dir = prepare_dirs(root_data_dir, data_version)
    catalog_path = os.path.join(root_data_dir, f'leafly_catalog_{data_version}.csv')
    if os.path.exists(catalog_path):
        catalog_df = pd.read_csv(catalog_path)
    else:
        catalog_df = scrape_leafly_catalog(html_dir, html_items_dir, items_description_dir, config['num_pages'])
        catalog_df.to_csv(catalog_path, index=False)
    print(f"Num items in catalog: {catalog_df.shape[0]}")
    precessed_files = os.listdir(items_description_dir)
    if len(precessed_files) == 0:
        prepare_catalog(catalog_df)
    print(f'Catalog saved to {catalog_path}')
