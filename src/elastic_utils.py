import os
import json
import datetime
import hashlib

import numpy as np
import pandas as pd
import backoff
import openai
from openai import OpenAI
from elasticsearch import Elasticsearch, ConnectionError



def get_pytorch_model(models_dir, model_name='multi-qa-distilbert-cos-v1'):
  from sentence_transformers import SentenceTransformer

  model_path = os.path.join(models_dir, model_name)

  if not os.path.exists(model_path):
      print('huggingface model loading...')
      embedder = SentenceTransformer(model_name)
      embedder.save(model_path)
  else:
      print('pretrained model loading...')
      embedder = SentenceTransformer(model_name_or_path=model_path)
  print('model loadind done')
  return embedder

embedder = None
def get_or_create_embedder(models_dir, model_name):
    global embedder
    print('Loading embed...')
    if embedder is None:
        embedder = get_pytorch_model(models_dir, model_name)
    return embedder

def get_id_hash(input_text):
    seed_phrase = f'{str(datetime.datetime.now().timestamp())}{input_text}'
    res = str(hashlib.md5(seed_phrase.encode('utf-8')).hexdigest())[:12]
    return res

class VectorSearchEngine:
    def __init__(self, documents, embeddings):
        self.documents = documents
        self.embeddings = embeddings

    def search(self, v_query, num_results=10):
        scores = self.embeddings.dot(v_query)
        idx = np.argsort(-scores)[:num_results]
        return [{'score': scores[i], 'doc': self.documents[i]} for i in idx]

class ElasticSearchEngine:
    def __init__(self):
        self.es_client = Elasticsearch('http://localhost:9200')

    def search(self, query, v_query, num_results=10):
        index_name = 'greenbro-content'
        knn_query = {
            "field": "text_vector",
            "query_vector": v_query,
            "k": 5,
            "num_candidates": 10000
        }
    
        response = self.es_client.search(
            index=index_name,
            query={
                    "bool": {
                        "must": {
                            "multi_match": {
                                "query": query,
                                "fields": ["relief", "positive_effects", "flavours"],
                                "type": "best_fields"
                            }
                        },
                        "filter": {  # TODO: add filter as parameter
                            "term": {
                                "category": "flower"
                            }
                        }
                    }
            },
            knn=knn_query,
            size=5
        )
        response = response['hits']['hits'][:num_results]
        response = [{'score': i['_score'], 'res': i['_source']['item_name']} for i in response]
        return response

def get_search_instance(type='vector'):
    if type == 'vector':
        root_dir = os.environ['API_DATA_PATH']
        models_dir = os.path.join(root_dir, 'pipelines-data', 'models')

        index_file_path = os.path.join(models_dir, 'embeds_index.json')
        embeds_file_path = os.path.join(models_dir, 'embeds.npy')
        with open(index_file_path, 'r') as f:
            index = json.load(f)
        embeds = np.load(embeds_file_path)
        print(embeds.shape, len(index))
        search_engine = VectorSearchEngine(documents=index, embeddings=embeds)
    elif type == 'elasticsearch':
        search_engine = ElasticSearchEngine()
    return search_engine


root_dir = os.environ['API_DATA_PATH']
csvfile_path = os.path.join(root_dir, 'pipelines-data', 'api_db.csv')
content_db = pd.read_csv(csvfile_path)

def get_candidates(content_names_list):
    res = [
        {
            'title': row['title'], 'url': row['url'], 'explanation': f"{row['tags']}: {row['positive_effects']}",
            'flavours': row['flavours']
        }
        for _, row in content_db[content_db['item_name'].isin(content_names_list)].iterrows()
    ]
    return res

class VectorDB:
    def __init__(self, index, embeddings):
        self.db = {}
        for i, embed in enumerate(embeddings):
            self.db[index[i]] = embed

    def get_item_vector(self, item_name):
        return self.db[item_name]

def get_vector_db():
    root_dir = os.environ['API_DATA_PATH']
    models_dir = os.path.join(root_dir, 'pipelines-data', 'models')
    index_file_path = os.path.join(models_dir, 'embeds_index.json')
    embeds_file_path = os.path.join(models_dir, 'embeds.npy')
    with open(index_file_path, 'r') as f:
        index = json.load(f)
    embeds = np.load(embeds_file_path)
    print(embeds.shape, len(index))
    vector_db = VectorDB(index=index, embeddings=embeds)
    return vector_db

vector_db = get_vector_db()
search_engine = get_search_instance()
embedder = get_or_create_embedder(os.path.join(os.environ['API_DATA_PATH'], 'models'), model_name='multi-qa-distilbert-cos-v1')


@backoff.on_exception(backoff.expo, openai.APIError)
@backoff.on_exception(backoff.expo, openai.RateLimitError)
@backoff.on_exception(backoff.expo,openai.Timeout)
@backoff.on_exception(backoff.expo, RuntimeError)
def gpt_query(gpt_params, verbose: bool = False, avoid_fuckup: bool = False) -> dict:
    print('connecting OpenAI...')
    if verbose:
        print(gpt_params["messages"][1]["content"])
    response = client.chat.completions.create(
        **gpt_params
    )
    gpt_response = response.choices[0].message.content
    if avoid_fuckup:
        if '[' in gpt_response or '?' in gpt_response or '{' in gpt_response:
            raise RuntimeError
    res = {'recs': gpt_response}
    res.update({'completion_tokens': response.usage.completion_tokens, 'prompt_tokens': response.usage.prompt_tokens, 'total_tokens': response.usage.total_tokens})
    res.update({'id': get_id_hash(gpt_response)})
    return res

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

def generate_promt(candidates, query) -> str:
  prompt = f"""
      Below you can find items with description in format `title: description`
      {candidates}
      Rerank items and return reranked item ids base on user query. Return only reranked items, comma-separate
      Do not add any explanation, just result. Do not filter irrelevannt, just rank lower.
      User query: {query}
      expected result: [title, title, title]
      reranked:
  """
  return prompt

def generate(gpt_prompt, verbose=False):
    gpt_params = {
        'model': 'gpt-3.5-turbo',
        'max_tokens': 500,
        'temperature': 0.7,
        'top_p': 0.5,
        'frequency_penalty': 0.5,
    }
    if verbose:
        print(gpt_prompt)
    messages = [
        {
          "role": "system",
          "content": "You are a helpful assistant for medicine shopping",
        },
        {
          "role": "user",
          "content": gpt_prompt,
        },
    ]
    gpt_params.update({'messages': messages})
    res = gpt_query(gpt_params, verbose=False)
    return res

def rerank_candidates(candidates, query):
    prompt_candidates = [f"{i['title']}: {i['explanation']}, {i['flavours']}" for i in candidates]
    prompt = generate_promt(prompt_candidates, query)
    generated_result = generate(prompt)
    ranked_titles = generated_result['recs'].split(',')
    res = []
    for i in ranked_titles:
        current_title = i.strip()
        filtered_candidates = [j for j in candidates if j['title']==current_title]
        if len(filtered_candidates) > 0:
            res.append(filtered_candidates[0])
    return res
