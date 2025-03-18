import os

from openai import OpenAI
import re
import ast

def eval_list(input_str):
    if input_str.count("'") < 10:
        input_str = input_str.replace("'", ' ')
    res = ast.literal_eval(input_str.replace('\n', '').replace('"', "'"))
    return res

def extract_lists(gpt_output):
    pattern = r'\bEntities:\s*(\[.*?\])\s*\n\s*Relationships:\s*(\[.*?\])'
    
    match = re.search(pattern, gpt_output, re.DOTALL)
    if match:
        entities_list_str = match.group(1)
        relationships_list_str = match.group(2)
        return entities_list_str, relationships_list_str


client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

def extract_entities_relationships(text):
    messages = [
        {
            "role": "system", "content": """"
            You are a helper tool for a knowedge graph builder application. Your task is to extract entities and relationships from the text provided by the user. 
            Format the output in such a way that it can be directly parsed into Python lists. 
            The format should include:

            1. A list of **Entities** in Python list format.
            2. A list of **Relationships**, where each relationship is represented as a tuple in the format: (Entity 1, "Relationship", Entity 2).

            Here is the format to follow:

            Entities: ["Entity 1", "Entity 2", ..., "Entity N"]

            Relationships: [("Entity 1", "Relationship", "Entity 2"), ..., ("Entity X", "Relationship", "Entity Y")]

            Example Input:
            Extract entities and relationships from the following text:
            "Michael Jackson, born in Gary, Indiana, was a famous singer known as the King of Pop. He passed away in Los Angeles in 2009."

            Expected Output:

            Entities: ["Michael Jackson", "Gary, Indiana", "Los Angeles", "singer", "King of Pop", "2009"]

            Relationships: [
            ("Michael Jackson", "born in", "Gary, Indiana"), 
            ("Michael Jackson", "profession", "singer"), 
            ("Michael Jackson", "referred to as", "King of Pop"), 
            ("Michael Jackson", "passed away in", "Los Angeles"), 
            ("Michael Jackson", "date of death", "2009")
            ]
            """
        },
        {"role": "user", "content": f"Extract entities and relationship tuples from the following text:\n\n{text}\n\n"}
    ]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
    )
    return response