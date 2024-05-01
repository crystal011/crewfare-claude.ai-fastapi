import openai
import uuid
import pinecone
import os
import json
from .config import *
from defusedxml import ElementTree
from collections import defaultdict
from anthropic import HUMAN_PROMPT, AI_PROMPT
from openai import OpenAI


BATCH_SIZE = 100
embedding_model = "text-embedding-ada-002"

client = OpenAI(api_key=OPENAI_KEY)

pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)

def get_embedding(text):
    return client.embeddings.create(input=text, model=embedding_model).data[0].embedding

def get_embeddings(sentences):
    embeddings = []
    for sentence in sentences:
        embeddings.append(get_embedding(sentence))
    return embeddings
 
def upsert_pinecone(data):
    index = pinecone.Index(PINECONE_INDEX)
    for i in range(0, len(data), BATCH_SIZE):
        print('batch', i)
        item_ids, embeddings, metadata = [], [], []
        i_end = min(i + BATCH_SIZE, len(data))
        for record in data[i:i_end]:
            embeddings.append(record["embedding"])
            item_ids.append(str(uuid.uuid4()))
            metadata.append(record['metadata'])
        records = zip(item_ids, embeddings, metadata)
        upsert_results = index.upsert(vectors=records)
    return upsert_results

def build_knowledge_base(fpath):
    with open(fpath, 'r', encoding='utf-8') as file:
        data = json.load(file)
    new_data = []
    for d in data:
        embedding_text = d['About Event']
        new_data.append(
            {
                'metadata': d,
                'embedding': get_embedding(str(embedding_text))
            }
        )
    print('start_upserting!')
    upsert_pinecone(new_data)

def json_to_text(data):
    text = ''
    for key, value in data.items():
        text += f"{key}: {str(value)}\n"
    return text

def get_document_ids(data):
    return [int(d['ID']) for d in data]

def documents_to_prompt(data):
    prompt = '<documents>\n'
    for document in data:
        prompt += "<document>\n"
        for key, value in document.items():
            prompt += f"<{str(key)}>\n{str(value)}\n</{str(key)}>\n"
        prompt += "</document>\n"
    prompt += "</documents>"
    return prompt

def history_to_prompt(history):
    prompt = ''
    for message in history:
        for key, value in message.items():
            prompt += key + '\n' + value
    return prompt
        
def etree_to_dict(t):
    d = {t.tag: ''}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[t.tag].update(("@" + k, v) for k, v in t.attrib.items())
    if t.text and t.text.strip():
        if children or t.attrib:
            d[t.tag]["#text"] = t.text
        else:
            d[t.tag] = t.text
    return d