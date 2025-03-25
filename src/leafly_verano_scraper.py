import os

import pandas as pd


from utils import prepare_dirs, read_json, set_data_version
from scrape_tools import scrape_leafly_catalog


root_data_dir = os.environ['ROOT_DATA_DIR']
config = read_json(os.environ['CONFIG_DIR'], 'config.json')
data_version = set_data_version(config, root_data_dir)
VERANO_URL_PATTERN = 'https://www.leafly.com/products/{category}?brands%5B%5D=Verano&page={page_num}'


if __name__ == '__main__':
    print(f'Data version: {data_version}')
    items_description_dir, html_items_dir, html_dir = prepare_dirs(root_data_dir, data_version, prefix='verano_')
    catalog_path = os.path.join(root_data_dir, f'verano_leafly_catalog_{data_version}.csv')
    if os.path.exists(catalog_path):
        catalog_df = pd.read_csv(catalog_path)
    else:
        catalog_df = scrape_leafly_catalog(html_dir, html_items_dir, items_description_dir, config['num_pages'], url_pattern=VERANO_URL_PATTERN)
        catalog_df.to_csv(catalog_path, index=False)
    print(f'Data exctracting complited, version={data_version}')