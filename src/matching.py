import json
import os
from itertools import chain

import requests
import pandas as pd
import backoff
from json.decoder import JSONDecodeError


def create_matcher(api_key=None, model="gpt-3.5-turbo"):
    openai_api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OpenAI API key must be provided or set as OPENAI_API_KEY environment variable")
    system_message ="""
        You are a professional product matching expert for comparing items across different catalogs. Follow these rules to find the best match:
        
        * Match by brand (most important). If brand not matched it is most probably mismatch
        * Match by product name.
        * Match by units of measure.
        
        Input format:
        
        You will receive one source product (name and brand).
        After the source product, you will get a numbered list of target products.
        Matching rules:
        
        Prioritize longer product names if multiple matches have similar confidence.
        If the brand doesn't match, the confidence should be low unless other factors strongly align.
        If no clear match is found or you are unsure, return "ERROR" (no structured output).
        Output format:
        Return only structured output in this format:
        
        {"best_match": "product_number", "confidence": "confidence_level"}
        
        Confidence levels:
        "high": Strong match across brand, product name, and unit.
        "medium": Good match but with some uncertainty (e.g., minor name differences).
        "low": Weak match, possibly only on product name or unit.
        Important:
        
        Do not include explanations.
        Focus on brand importance and prefer longer names for better matches.
    """
    def match_item(user_prompt):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai_api_key}"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1  # Low temperature for consistent translations
        }
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload)
        )
        if response.status_code == 200:
            result = response.json()
            matched_items = result["choices"][0]["message"]["content"].strip()
            return matched_items
        else:
            error_message = f"API Error {response.status_code}: {response.text}"
            raise Exception(error_message)
    
    return match_item

def prepare_prompt(df_dict):
    res = 'source pruduct: product name: {}, product brand:  {}\n\n'.format(df_dict[0]['sweed_product_name'], df_dict[0]['ProductBrand'])
    for i in df_dict:
        res += '{}: product name: {}, product brand: {}\n'.format(i['row_num'], i['title'], i['brand'])
    return res

matcher = create_matcher()

@backoff.on_exception(backoff.expo, JSONDecodeError, max_tries=3)
def find_match(sub_df):
    prompt = prepare_prompt(sub_df.to_dict(orient='records'))
    llm_resp = matcher(prompt)
    resp = json.loads(llm_resp)
    sub_df['match_confidence'] = sub_df['row_num'].apply(lambda x: resp['confidence'] if resp['best_match'] == str(x) else None)
    return sub_df

def validate_fields(df):
    field_list = [
        'tags', 'effects', 
    ]
    for f in field_list:
        print(f, list(chain(*df[f].values)))

def prepare_main_page_catalog(main_page_content):
    result_json = []
    for i in main_page_content:
        result_json += [{'carousel_id': i['id'], 'carousel_name': i['name'], **p} for p in i['products']]
    result_df = pd.json_normalize(result_json)
    print(result_df.shape)
    validate_fields(result_df)
    excluded_fields = (
        'tags', 'effects', 'qualityLine', 'productType', 'category.id', 'subcategory.id', 'brand.filter', 'brand.tagId',
        # 'strain.flavors', 'strain.terpenes', 'strain',
        'qualityLine.name', 'productType.name',
        'variants'
    )
    result_df['product_image'] = result_df['images'].apply(lambda x: x[0])
    print(result_df['category.name'].unique())
    ecom_catalog_df = result_df[[i for i in result_df.columns if i not in excluded_fields]]
    return ecom_catalog_df

def get_match(product_name, index):
    top_match_id = index.rank(product_name, top_n=2)[0][0]
    match_product_id = index.get_document(top_match_id)
    return match_product_id

def match_ecom_catalog_to_sweed_catalog(ecom_catalog_df, products_df, index):
    ecom_catalog_df['ProductID'] = ecom_catalog_df[['name', 'category.name']].apply(lambda row: f'{row.iloc[0]} {row.iloc[1]}'.lower(), axis=1).apply(lambda x: get_match(x, index))
    ecom_catalog_df = ecom_catalog_df.merge(products_df[['ProductID', 'ProductName', 'ProductCategory']], on='ProductID')
    return ecom_catalog_df
