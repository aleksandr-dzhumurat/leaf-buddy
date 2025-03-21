import os
from typing import List, Set
from uuid import uuid4

from tqdm import tqdm
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_community.vectorstores import FAISS
from transformers import AutoTokenizer
from dotenv import load_dotenv


root_data_dir = os.environ['ROOT_DATA_DIR']
config_dir = os.getenv('CONFIG_DIR')
if config_dir is not None:
    print(load_dotenv(os.path.join(config_dir, '.env')))
html_data_dir = 'models'
cache_folder = os.path.join(root_data_dir, html_data_dir)
if not os.path.exists(cache_folder):
    os.mkdir(cache_folder)


def create_vector_database(docs_processed: List[Document]) -> FAISS:
    """Create a vector database from processed documents"""
    print(f"Embedding documents... This may take a few minutes")
    embedding_model_name="thenlper/gte-small"
    embedding_model = HuggingFaceEmbeddings(model_name=embedding_model_name, cache_folder=cache_folder)
    return FAISS.from_documents(
        documents=docs_processed,
        embedding=embedding_model,
        distance_strategy=DistanceStrategy.COSINE,
    )

def search(vectordb, query: str, limit: int = 10) -> str:
    assert isinstance(query, str), "Your search query must be a string"
    docs = vectordb.similarity_search(  # or .similarity_search_with_score
        query,
        k=limit,
    )
    results = [{'rank': i, 'id': doc.metadata.get('id')} for i, doc in enumerate(docs)]
    return results

def chunk_documents(text_splitter, documents: List[Document]) -> List[Document]:
    """Split documents into chunks and remove duplicates"""
    print("Splitting documents...")
    docs_processed = []
    unique_texts: Set[str] = set()
    for doc in tqdm(documents, desc="Chunking documents"):
        new_docs = text_splitter.split_documents([doc])
        for new_doc in new_docs:
            if new_doc.page_content not in unique_texts:
                unique_texts.add(new_doc.page_content)
                docs_processed.append(new_doc)
    print(f"Created {len(docs_processed)} unique document chunks")
    return docs_processed

def prepare_knowledge_base(catalog_df):
    knowledge_base = []
    for _, row in catalog_df[['processed_file_name', 'doc_id']].iterrows():
        file_path = row['processed_file_name']
        if os.getenv('RUN_ENV', '') == 'docker':
            file_path = file_path.replace('/Users/username/PycharmProjects/leaf-buddy', '/srv')
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
            knowledge_base.append({
                "text": text,
                "source": row['processed_file_name'],
                "doc_id": row['doc_id']
            })
    return knowledge_base

def prepare_corpus_documents(catalog_df):
    knowledge_base = prepare_knowledge_base(catalog_df)
    tokenizer_name = "thenlper/gte-small"
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, cache_folder=cache_folder)

    chunk_size = 200
    chunk_overlap = 20

    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
        strip_whitespace=True,
        separators=["\n\n", "\n", ".", " ", ""],
    )

    documents = [
        Document(
            page_content=doc["text"], 
            metadata={"id": doc['doc_id'], "source": doc["source"]}
        ) for doc in knowledge_base
    ]
    chunked_docs = chunk_documents(text_splitter, documents)
    return chunked_docs

def get_vector_db(catalog_df, debug=False):
    # print(f'Loading data from {items_description_dir}')
    if debug:
        catalog_df = catalog_df.sample(150)
    corpus = prepare_corpus_documents(catalog_df)
    vectordb = create_vector_database(corpus)
    return vectordb
