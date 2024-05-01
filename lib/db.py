import mysql.connector
import time
import json
import logging

logger = logging.getLogger(__name__)

############################################
# Export Data From MySQL implementations
############################################

def format_date(date: str) -> str:
    if date == '' or not isinstance(date, str):
        return ''
    return date[:4] + '-' + date[4:6] + '-' + date[6:8]

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

def export_data_from_mysql(query: str, file: str, config: dict) -> bool:
    data = read_data(config, query)
    with open(file, 'w') as f:
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

            f.write(json.dumps(row) + '\n')
    return True
