import datetime
import hashlib
import os
import json
import random
import re
from uuid import uuid4

import backoff
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from tqdm import tqdm


get_data_version = lambda f_name: f_name.split('_')[-1].split('.')[0]

def read_json(dirname, filename):
    input_file_path = os.path.join(dirname, filename)
    with open(input_file_path, 'r', encoding='utf-8') as f:
        json_content = json.load(f)
    return json_content

def get_random(my_list):
    random_index = random.randint(0, len(my_list) - 1)
    random_element = my_list[random_index]
    return random_element

def get_id_hash(input_text=None):
    if input_text is None:
        input_text = str(datetime.datetime.now().timestamp())
    seed_phrase = f'{input_text}'
    res = str(hashlib.md5(seed_phrase.encode('utf-8')).hexdigest())[:12]
    return res

@backoff.on_exception(backoff.expo, requests.exceptions.ReadTimeout)
def request_smart(url):
    ua = UserAgent()
    session = requests.Session()
    
    headers = {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    # 4. Add a referrer to make it look like you're coming from Google
    headers['Referer'] = 'https://www.google.com/'
    
    response = session.get(url, headers=headers, timeout=10)
    return response

def save_file(file_content, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(file_content)

def save_html(response, file_path):
    if response.status_code == 200:
        html_content = response.text
        save_file(html_content, file_path)
    else:
        print("Failed to retrieve webpage %s. Status code: %s" % (response.url, response.status_code))
    return response.status_code

def read_html(html_dir, i):
    input_file_path = os.path.join(html_dir, i)
    with open(input_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    return html_content

def create_scraper(input_file_path):
    with open(input_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    items_scraper = BeautifulSoup(
        markup=html_content, features="html.parser"
    )
    return items_scraper

def extract_json(text):
    """
    Extracts the first JSON object found in the given text and returns it as a dictionary.
    If no valid JSON is found, returns None.
    """
    json_pattern = re.compile(r'\{.*?\}', re.DOTALL)
    match = json_pattern.search(text)
    
    if match:
        json_str = match.group()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    return None

url_to_filename = lambda url: f"{url.replace('www.', '').replace('https://', '').replace('/', '_').replace('?', '_').replace('.', '_')}.html"


import math
from collections import Counter

def tokenize(text):
    return text.lower().split()

def compute_tf(term, doc):
    return doc.count(term)

def compute_idf(term, corpus):
    docs_containing_term = sum(1 for doc in corpus if term in doc)
    return math.log((len(corpus) - docs_containing_term + 0.5) / (docs_containing_term + 0.5) + 1.0)

def bm25_score(query, doc, corpus, idf_scores, k1=1.5, b=0.75):
    score = 0
    doc_len = len(doc)
    avg_doc_len = sum(len(d) for d in corpus) / len(corpus)
    
    for term in query:
        tf = doc.count(term)
        idf = idf_scores.get(term, 0)  # 0 if the term does not appear in corpus
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_doc_len)))
    
    return score

class BM25Index:
    """
        index = BM25Index()
        index.build_index(corpus)
        print('Index built')
    """
    def __init__(self):
        self.idf_scores = None
        self.corpus_tokens = None

    def build_index(self, corpus):
        print(f'num documents: {len(corpus)}')
        self.corpus_tokens = [tokenize(doc) for doc in corpus]
        self.idf_scores = {}
        all_terms = set([term for doc in self.corpus_tokens for term in doc])
        for term in all_terms:
            self.idf_scores[term] = compute_idf(term, self.corpus_tokens)
        print('Idf score prepared')

    def query(self, query):
        query = tokenize(query)
        scores = [bm25_score(query, doc, self.corpus_tokens, self.idf_scores) for doc in self.corpus_tokens]
        res = []
        for idx, score in enumerate(scores):
            if score > 0:
                res.append( (idx, score))
        res = sorted(res, key = lambda x: -x[1])
        return res


import os
import time

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TfidfRanker:
    def __init__(self, documents, stop_words='english', ngram_range=(1, 1)):
        self.documents = [i[1] for i in documents]
        self.doc_ids = [i[0] for i in documents]
        self.vectorizer = TfidfVectorizer(
            stop_words=stop_words,
            ngram_range=ngram_range
        )
        self.document_vectors = self.vectorizer.fit_transform(self.documents)
    
    def rank(self, query, top_n=5):
        query_vector = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, self.document_vectors)[0]
        top_indices = np.argsort(similarities)[::-1][:top_n]
        return [(idx, similarities[idx]) for idx in top_indices]
    
    def get_document(self, index):
        return self.doc_ids[index]

def clear_exprired_files(directory, expire_days = 90):
    time_threshold = datetime.datetime.now() - datetime.timedelta(days=expire_days)

    # Convert threshold time to timestamp format
    time_threshold_timestamp = time.mktime(time_threshold.timetuple())

    # Loop through files in the directory
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            file_mod_time = os.path.getmtime(file_path)
            if file_mod_time < time_threshold_timestamp:
                os.remove(file_path)
                print(f"Removed: {file_path}")

def get_fecent_file(data_dir, name_pattern):
    files = [i for i in os.listdir(data_dir) if name_pattern in i]
    sorted_files = list(sorted(files, key=lambda x: os.path.getctime(os.path.join(data_dir, x))))
    most_recent_file = None
    if len(sorted_files) > 0:
        most_recent_file = sorted_files[-1]
    return most_recent_file

def prepare_dirs(root_data_dir, data_version, prefix=''):
    root_html_dir = os.path.join(root_data_dir, f'{prefix}leafly_html_pages_{data_version}')
    if not os.path.exists(root_html_dir):
        os.mkdir(root_html_dir)
    html_items_dir = os.path.join(root_html_dir, f'{prefix}items_html_pages_{data_version}')
    if not os.path.exists(html_items_dir):
        os.mkdir(html_items_dir)
    items_description_dir = os.path.join(root_html_dir, f'{prefix}items_descriptions_{data_version}')
    if not os.path.exists(items_description_dir):
        os.mkdir(items_description_dir)
    return items_description_dir, html_items_dir, root_html_dir

def set_data_version(config, root_data_dir):
    print(config)
    data_version = None
    if not config['overwrite']:
        print('recent ', get_fecent_file(root_data_dir, 'leafly_html_pages'))
        data_version = get_data_version(get_fecent_file(root_data_dir, 'leafly_html_pages'))
    if data_version is None:
        data_version = get_id_hash()
    print(f'Starting with data version={data_version}'), get_id_hash()
    return data_version

def process_item(i, base_url = 'https://www.leafly.com'):
    title = i.find(name='div', class_="font-bold text-sm leading-normal").text
    link = i.find('a')['href']
    item_url = f'{base_url}{link}'
    doc_id = f"doc_{uuid4()}"
    return title, link, item_url, doc_id

def prepare_plaintext_files(catalog_df):
    base_url = 'https://www.leafly.com'
    errors = []
    for _, row in tqdm(catalog_df.iterrows(), desc="Processing items"):
        link=row['link']
        page_scraper = create_scraper(row['file'])
        try:
            item_descriprion = page_scraper.find(name='div', class_='bg-white border-t border-light-grey').find(name='section', class_="max-w-[700px]").find(name='p')
            res = item_descriprion.text
            save_file(res, row['processed_file_name'])
        except AttributeError:
            errors.append(f'Parsing error: {base_url}{link}')
            save_file('', row['processed_file_name'])
    print(f'Catalog saved, num errors {len(errors)}')
