import os
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import pandas as pd

#from src.utils import embedder, search_engine, get_candidates, rerank_candidates
from src.vector_storage import get_vector_db, search

root_data_dir = os.environ['ROOT_DATA_DIR']
catalog_df = pd.read_csv(os.path.join(root_data_dir, 'leafly_catalog.csv'))
vector_db = get_vector_db((catalog_df), debug=False)
app = FastAPI()

class SearchRequest(BaseModel):
    relief: List[str]
    positive_effects: List[str]
    query: str

class EmbedResult(BaseModel):
    embed: str

class ScoreResult(BaseModel):
    relief: List[str]
    positive_effects: List[str]
    query: str

class EmbeddingRequest(BaseModel):
    text: str

class SearchResult(BaseModel):
    title: str
    url: str
    explanation: str

class ScoreItem(BaseModel):
    title: str
    relevant: bool

class ScoreRequest(BaseModel):
    items: List[ScoreItem]

# Mock database or search logic
mock_data = [
    {"title": "Strain 1", "explanation": "Helps with anxiety and stress."},
    {"title": "Strain 2", "explanation": "Good for uplifting mood."},
    {"title": "Strain 3", "explanation": "Relieves depression and insomnia."},
]

@app.post("/search", response_model=List[SearchResult])
async def search_items(request: SearchRequest):
    # Placeholder search logic based on the request
    reliefs = f"reliefs: {', '.join(request.relief)}"
    positive_effects = f"positive effects: {', '.join(request.positive_effects)}"
    # query = f"{reliefs}; {positive_effects}"
    # q = embedder.encode(query)
    # result = search_engine.search(q, num_results=10)
    # results = get_candidates([i['doc'] for i in result])
    # if len(request.query) > 0:
    #     results = rerank_candidates(results, request.query)
    doc_ids = search(vector_db, request.query)
    base_url = 'https://www.leafly.com'
    results = [
        {'title': row['title'],  'url': f"{base_url}{row['link']}", 'explanation': row['category']} for _, row in catalog_df[catalog_df['doc_id'].isin([i['id'] for i in doc_ids])].iterrows()
    ]
    if not results:
        raise HTTPException(status_code=404, detail="No matching items found")
    
    return results

@app.post("/feedback")
async def score(data: ScoreRequest):
    # Process the scoring data here: for now, let's just return the received data
    return {"received_items": data.items}

@app.post("/embed", response_model=EmbedResult)
def embed_text(data: EmbeddingRequest):
    # embeddings = embedder.encode(data.text)
    return {'embed':json.dumps(embeddings.tolist()) }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
