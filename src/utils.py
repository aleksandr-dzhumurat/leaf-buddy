import datetime
import hashlib
import os
import json
import random
import re

import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup


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

def request_smart(url):
    ua = UserAgent()
    session = requests.Session()
    
    # 3. Add common headers that browsers send
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
