# app/populate_events.py
from app.parse_xml_util import extract_events_from_xml

def populate_match_events(sqlite_cursor, pg_cursor):
    print("[4/4] Parsing XML and Loading Match Events... (This is heavy!)")
    
    # --- DATA CLEANSING: Fetch all valid players to prevent FK violations ---
    pg_cursor.execute("SELECT player_id FROM Player;")
    valid_players = {row[0] for row in pg_cursor.fetchall()}
    
    query = "SELECT match_api_id, goal, card, foulcommit, corner, cross FROM Match;"
    sqlite_cursor.execute(query)
    
    xml_cols = ['goal', 'card', 'foulcommit', 'corner', 'cross']
    all_events = []
    
    for row in sqlite_cursor:
        match_id = row[0]
        for i, event_type in enumerate(xml_cols, start=1):
            xml_data = row[i]
            extracted = extract_events_from_xml(xml_data, event_type, match_id)
            
            # Check each event against our valid players list
            for event in extracted:
                e_match_id, e_id, e_min, e_type, e_player_id = event
                
                # If player_id is not in our master list, set it to NULL
                if e_player_id is not None and e_player_id not in valid_players:
                    e_player_id = None 
                    
                all_events.append((e_match_id, e_id, e_min, e_type, e_player_id))

    batch_size = 10000
    for i in range(0, len(all_events), batch_size):
        pg_cursor.executemany(
            "INSERT INTO Match_Event (match_api_id, event_id, minute, event_type, player_id) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;", 
            all_events[i:i + batch_size]
        )