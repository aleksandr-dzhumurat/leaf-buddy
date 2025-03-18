import os
import re
import json

from bs4 import BeautifulSoup
import pandas as pd
import requests
from tqdm import tqdm

from utils import save_html, create_scraper

root_data_dir = os.environ['ROOT_DATA_DIR']
print(os.listdir(root_data_dir))


def preprocess_source_html(items_scraper, catalog_data_path):
    if not os.path.exists(catalog_data_path):
        print('Extracting from HTML')
        df_entries = []
        items = items_scraper.find_all(name='div', class_="col-sm-6 col-md-4 col-lg-3")
        for i in tqdm(items, desc="Processing items"):
            title = i.find(class_='object-title').find(class_='visible-xs').text
            link = i.find(class_='object-title').find('a')['href']
            tags = '|'.join([t.strip() for t in i.find(class_='subtitle').text.split('\n') if len(t.strip()) > 1])
            percentages = re.sub(r'\s+', ' ', i.find(class_='details').find(class_='percentages').text.replace('\n', ' '))
            num_favorites = i.find(class_='details').find(class_='favorites').text.replace('\n', ' ')
            avg_rating = i.find(class_='details').find(class_='ratings').find(class_='rating-num').text
            num_ratings = i.find(class_='details').find(class_='ratings').find(class_='rating-votes').find(class_='product-rating-votes').text.strip()
            df_entries.append((title, link, num_favorites, avg_rating, num_ratings, percentages, tags))
            catalog_df = pd.DataFrame(df_entries, columns=['title','link','num_favorites','avg_rating','num_ratings','percentages','tags'])
        catalog_df.to_csv(catalog_data_path, index=False)
    else:
        print('reading from dump')
        catalog_df = pd.read_csv(catalog_data_path)
    print(f'Num rows in catalog {catalog_df.shape[0]}')

def download_html_pages(catalog_data_path, html_dir):
    catalog_df = pd.read_csv(catalog_data_path)
    if not os.path.exists(html_dir):
        os.mkdir(html_dir)
    if len(os.listdir(html_dir)) == 0:
        for ind, row in tqdm(catalog_df.iterrows()):
            url = f"https://www.allbud.com{row['link']}"
            html_path = os.path.join(html_dir, f"{row['link'].replace('/', '_')}.html")
            if not os.path.exists(html_path):
                response = requests.get(url)
                save_html(response, html_path)
            else:
                pass
            if ind % 50 == 0:
                print(f'{ind} out of {catalog_df.shape[0]}')
    print('All done!')

def create_content_cards(root_data_dir, html_dir):
    descriptions_json_path = os.path.join(root_data_dir, 'item_cards.json')
    reviews_json_path = os.path.join(root_data_dir, 'reviews.json')

    descrs = []
    reviews = []
    errors = []
    if not os.path.exists(descriptions_json_path):
        for i in os.listdir(html_dir):
            if len(descrs) % 500 == 0:
                print('Processed: %s' % len(descrs))
            description_dict = {}
            input_file_path = os.path.join(html_dir, i)
            with open(input_file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            item_card_scraper = BeautifulSoup(
                markup=html_content, features="html.parser"
            )
            description_dict.update({
                "description": re.sub(r'\s+', ' ', item_card_scraper.find(class_='panel-body well description').text.replace('\n', ' '))
            })
            # details
            positive_effects = re.sub(r'\s+', ' ', item_card_scraper.find(name='section', id='positive-effects-mobile').text.replace('\n', ''))
            relieved_effects = re.sub(r'\s+', ' ', item_card_scraper.find(name='section', id='relieved-mobile').text.replace('\n', ''))
            flavours = re.sub(r'\s+', ' ', item_card_scraper.find(name='section', id='flavors-mobile').text.replace('\n', ''))
            aromas = re.sub(r'\s+', ' ', item_card_scraper.find(name='section', id='aromas-mobile').text.replace('\n', ''))
            description_dict.update({
                'item': i,
                'positive_effects': positive_effects,
                'relieved_effects': relieved_effects,
                'flavours': flavours,
                'aromas': aromas,
            })
            descrs.append(description_dict)
            revs = item_card_scraper.find(name='div', id='collapse_reviews')
            try:
                for r in revs.find_all(class_='infopanel review mobile-panel'):
                    reviews.append({
                        'item': i,
                        'review': re.sub(r'\s+', ' ', r.find(class_='text').text.replace('\n', ''))
                    })
            except AttributeError:
                errors.append(i)
        with open(descriptions_json_path, 'w') as json_file:
            json.dump(descrs, json_file)
        with open(reviews_json_path, 'w') as json_file:
            json.dump(reviews, json_file)
    print('All done, num descriptions %s' % len(descrs))
    print('Num errors %d' % len(errors))

if __name__ == '__main__':
    raw_html_path = os.path.join(root_data_dir, 'AllBud.html')
    catalog_data_path = os.path.join(root_data_dir, 'allbud_catalog.csv')
    if not os.path.exists(catalog_data_path):
        items_scraper = create_scraper(raw_html_path)
        preprocess_source_html(items_scraper, catalog_data_path)
    print(f'Data created to {catalog_data_path}')
    html_data_dir = 'allbuds_html_pages'
    html_dir = os.path.join(root_data_dir, html_data_dir)
    download_html_pages(catalog_data_path, html_dir)
    print('Data created')
    create_content_cards(root_data_dir, html_dir)
    print('Content cards created')
