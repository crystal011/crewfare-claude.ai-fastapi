from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
import pinecone
from .config import *
from .utils import *
from .prompts import *
import time

from calendar import monthrange
from datetime import datetime

import mysql.connector
import time
import json
import logging

logger = logging.getLogger(__name__)

############################################
# Export Data From MySQL implementations
############################################

config = {
    'user': USER_NAME,
    'password': PASSWORD,
    'host': HOST,
    'database': DATABASE_NAME,
    'raise_on_warnings': True
}

def format_date(date: str) -> str:
    if date == '' or not isinstance(date, str):
        return ''
    ret = datetime.strptime(date[:4] + '-' + date[4:6] + '-' + date[6:8], '%Y-%m-%d').date()

    return ret

def connect_to_mysql(config, attempts=3, delay=2):
    attempt = 1
    # Implement a reconnection routine
    while attempt < attempts + 1:
        try:
            return mysql.connector.connect(**config)
        except (mysql.connector.Error, IOError) as err:
            if (attempts is attempt):
                # Attempts to reconnect failed; returning None
                logger.info("Failed to connect, exiting without a connection: %s", err)
                return None
            logger.info(
                "Connection failed: %s. Retrying (%d/%d)...",
                err,
                attempt,
                attempts-1,
            )
            # progressive reconnect delay
            time.sleep(delay ** attempt)
            attempt += 1
    return None

def read_data(config, _query):
    query = ''
    with open(_query, 'r') as f:
        query = f.read()

    cnx = connect_to_mysql(config, attempts=3)
    data= {}

    if cnx and cnx.is_connected():
        with cnx.cursor() as cursor:
            # title
            cursor.execute(query)
        
            data = cursor.fetchall()

        cnx.close()
        return data
    else:
        print("Could not connect")

def export_data_from_mysql(query: str, config: dict) -> bool:
    data = read_data(config, query)
    ret = []
    
    for dt in data:
        record = list(map(lambda x: '' if x is None else x, list(dt)))

        # row = {
        #     'text': f'ID: {record[0]}\n\nEvent Name: {record[1]}\n\nEvent Location: {record[2]}\n\nEvent Dates: {format_date(record[3])}\n\nEvent End Dates: {format_date(record[5])}\n\nAbout Event: {record[4]}\n\nEvent Type: {record[6]}\n\nEvent Category: {record[7]}\n\nEvent URL: {record[8]}'
        # }

        row = {
            "ID": record[0],
            "Event Name": record[1],
            "Event Location": record[2],
            "Event Dates": format_date(record[3]), 
            "Event End Dates": format_date(record[5]), 
            "About Event": record[4], 
            "Event Type": record[6], 
            "Event Category": record[7], 
            "Event URL": record[8]
        }

        ret.append(row)

    return ret

def convert_to_date_object(date_input):
    # Define a function that gets the last day for the given year and month
    def get_last_day(year, month):
        last_day = monthrange(year, month)[1]
        return last_day
    
    # Default date dictionary structure
    date_dict = {
        "start": {"year": "", "month": "", "day": ""},
        "end": {"year": "", "month": "", "day": ""}
    }

    if date_input == '':
        return ''
    
    date_parts = date_input.split('-')
    year = int(date_parts[0])  # Convert year to integer for the monthrange function
        
    if ' to ' in date_input:
        # Input indicates a date range
        start_date_str, end_date_str = date_input.split(' to ')
        start = datetime.strptime(start_date_str, "%Y-%m-%d")
        end = datetime.strptime(end_date_str, "%Y-%m-%d")
        date_dict["start"] = {"year": str(start.year), "month": str(start.month).zfill(2), "day": str(start.day).zfill(2)}
        date_dict["end"] = {"year": str(end.year), "month": str(end.month).zfill(2), "day": str(end.day).zfill(2)}
    else:
        # Input is not a range
        if len(date_parts) == 1:
            # Only year is provided; return the first and last day of the year
            date_dict["start"] = {"year": date_parts[0], "month": "01", "day": "01"}
            date_dict["end"] = {"year": date_parts[0], "month": "12", "day": "31"}
        elif len(date_parts) == 2:
            # Year and month are provided; return the first and last day of the month
            month = int(date_parts[1])  # Convert month to integer for the monthrange function
            last_day = get_last_day(year, month)
            date_dict["start"] = {"year": date_parts[0], "month": date_parts[1], "day": "01"}
            date_dict["end"] = {"year": date_parts[0], "month": date_parts[1], "day": str(last_day)}
        elif len(date_parts) == 3:
            # Full date is provided; return the specific day and the last day of the month
            month = int(date_parts[1])  # Convert month to integer for the monthrange function
            last_day = get_last_day(year, month)
            date_dict["start"] = {"year": date_parts[0], "month": date_parts[1], "day": date_parts[2]}
            date_dict["end"] = {"year": date_parts[0], "month": date_parts[1], "day": str(last_day)}

    return date_dict

def is_event_in_date_range(event, date_range):
    # Convert the date range to datetime objects for comparison
    start_date = datetime(int(date_range['start']['year']), int(date_range['start']['month']), int(date_range['start']['day']))
    end_date = datetime(int(date_range['end']['year']), int(date_range['end']['month']), int(date_range['end']['day']))
    
    # Convert event's start and end dates to datetime objects
    event_start_date = datetime(event['Event Dates'].year, event['Event Dates'].month, event['Event Dates'].day)
    event_end_date = datetime(event['Event End Dates'].year, event['Event End Dates'].month, event['Event End Dates'].day,)

    # Check if the event's date range overlaps with the specified date range
    return start_date <= event_end_date and end_date >= event_start_date

class Assistant():
    def __init__(self) -> None:
        self.prompt = ""
        self.history = []
        self.initialize()

    def initialize(self):
        self.model = Anthropic(api_key=ANTHROPIC_API_KEY, max_retries=3)
        self.pinecone = pinecone.Index(PINECONE_INDEX)

    def query_knowledge_base(self, query, top_k=10):
        query_vector = get_embedding(query)
        result = self.pinecone.query(vector=query_vector, top_k=top_k)
        matches = result.to_dict()["matches"]
        # scores = [match['score'] for match in matches]
        # print(scores)
        ids = [match["id"] for match in matches]
        data = self.pinecone.fetch(ids).to_dict()["vectors"]
        descriptions = [data[id]["metadata"] for id in ids]
        return descriptions
    
    def query_knowledge_base_id(self, query, top_k=10, score=0.75):
        query_vector = get_embedding(query)
        result = self.pinecone.query(vector=query_vector, top_k=top_k)
        matches = result.to_dict()["matches"]
        # scores = [match['score'] for match in matches]
        # print(scores)
        ids = [match["id"] for match in matches if match['score'] >= 0.75]
        if len(ids) == 0:
            return []
        data = self.pinecone.fetch(ids).to_dict()["vectors"]
        relevant_results = [int(data[id]["metadata"]['ID']) for id in ids]
        return relevant_results

    def run(self, user_input):
        start_time = time.time()
        self.history.append({HUMAN_PROMPT: user_input})
        function_prompt = function_call_prompt(user_input)
        function_response = self.model.completions.create(
            prompt=function_prompt,
            stop_sequences=["\n\nHuman:", "</parameters>"],
            model="claude-2.1",
            max_tokens_to_sample = 1000,
            temperature = 0)
        partial_completion, stop_reason, stop_seq = function_response.completion, function_response.stop_reason, function_response.stop
        
        if stop_reason == 'stop_sequence' and stop_seq == '</parameters>':
            xml = ElementTree.fromstring('<parameters>\n' + partial_completion + '</parameters>')
            param_dict = etree_to_dict(xml)
            parameters = param_dict["parameters"]
            print(parameters)

            date = parameters.get('date', '')
            location = parameters.get('location', '')
            descriptor = parameters.get('description', '')
            category = parameters.get('category', '')

            dates = convert_to_date_object(date)
            
            relevant_results = []
            if descriptor != '':
                relevant_results = self.query_knowledge_base(user_input, top_k=50)
                if category != '':
                    relevant_results = [record for record in relevant_results if record['Event Category'] in category.split(',')]
                if location != '':
                    relevant_results = [record for record in relevant_results if location.lower() in record['Event Location'].lower()]
                if dates != '':
                    relevant_results = [record for record in relevant_results if is_event_in_date_range(record, dates)]
            else:
                relevant_results = export_data_from_mysql("data/query.sql", config)
                if dates != '':
                    relevant_results = [record for record in relevant_results if is_event_in_date_range(record, dates)]
                if location != '':
                    relevant_results = [record for record in relevant_results if location.lower() in record['Event Location'].lower()]
            
            ret = [int(record['ID']) for record in relevant_results]

            end_time = time.time()
            print(end_time - start_time)
    
        return ret