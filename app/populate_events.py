# app/populate_events.py
from app.parse_xml_util import extract_events_from_xml

def populate_match_events(sqlite_cursor, pg_cursor):
    print("[4/4] Parsing XML and Loading Match Events... (This is heavy!)")
    
    query = "SELECT match_api_id, goal, card, foulcommit, corner, cross FROM Match;"
    sqlite_cursor.execute(query)
    
    xml_cols = ['goal', 'card', 'foulcommit', 'corner', 'cross']
    all_events = []
    
    for row in sqlite_cursor:
        match_id = row[0]
        # row[1] to row[5] map to the xml_cols
        for i, event_type in enumerate(xml_cols, start=1):
            xml_data = row[i]
            extracted = extract_events_from_xml(xml_data, event_type, match_id)
            all_events.extend(extracted)
            

    batch_size = 10000
    for i in range(0, len(all_events), batch_size):
        pg_cursor.executemany(
            "INSERT INTO Match_Event (match_api_id, event_id, minute, event_type, player_id) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;", 
            all_events[i:i + batch_size]
        )