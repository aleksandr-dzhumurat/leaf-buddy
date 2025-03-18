import os

import openai
import pandas as pd
import requests
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate

from utils import extract_json, read_html
from vector_storage import get_vector_db, search


base_url = 'https://www.leafly.com'
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
if os.getenv('OPENAI_API_KEY') is None:
    from dotenv import load_dotenv
    print(f'{os.path.dirname(current_dir)}/../.env')
    print(load_dotenv(f'{current_dir}/.env'))
root_data_dir = os.environ['ROOT_DATA_DIR']
catalog_df = pd.read_csv(os.path.join(root_data_dir, 'leafly_catalog.csv'))
vector_db = get_vector_db((catalog_df))

openai.api_key = os.getenv("OPENAI_API_KEY")
shop_assistant_prompt = read_html(current_dir, 'shop_assistant_prompt.txt')
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1)
prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        shop_assistant_prompt
    ),
    MessagesPlaceholder(variable_name="history"),
    HumanMessagePromptTemplate.from_template("{input}")
])
memory = ConversationBufferMemory(return_messages=True)
chat = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True,
    prompt=prompt,
)

def request_api(query, relief=[], positive_effects=[]):
    api_url = 'http://0.0.0.0:8000'
    headers = {"Content-Type": "application/json"}
    payload = {
        "relief": relief,
        "positive_effects": positive_effects,
        "query": query
    }
    response = requests.post(
        f"{api_url}/search",
        headers=headers,
        json=payload
    )
    resp = [
        (i['title'], i['url']) for i in response.json()
    ]

    return resp

def dialog_router(human_input: str, user: dict):
    llm_answer = chat.predict(input=human_input)
    json_answer = extract_json(llm_answer)
    if json_answer is not None:
        return {'final_answer': True, 'answer': json_answer}
    return {'final_answer': False, 'answer': llm_answer}

if __name__=='__main__':
    human_input = input("Start the dialog with AI bot: ")
    for k in range(10):
        answer = dialog_router(human_input=human_input, user={'name': 'Average Human'})
        if answer['final_answer']:
            # user_query = 'good for sleep'
            user_query = answer['answer']['user_query']
            # search_results = search(vector_db, user_query)
            # ids = [i['id'] for i in search_results]
            # for _, row in catalog_df[catalog_df['doc_id'].isin(ids)].iterrows():
            #     print(f"{base_url}{row['link']}")
            search_results = request_api(user_query)
            for i in search_results:
                print(i)
            break
        print(answer['answer'])
        human_input = input("Enter your response: ")
        print('\n..............\n')
    if k == 6:
        print("Conversation length overflow")
