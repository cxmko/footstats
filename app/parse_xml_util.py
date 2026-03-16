# app/parse_xml_util.py
import xml.etree.ElementTree as ET

def extract_events_from_xml(xml_data, event_type, match_id):
    """Parses Kaggle XML blobs and returns a list of event tuples."""
    events = []
    if not xml_data:
        return events
    
    try:
        root = ET.fromstring(xml_data)
        for value_node in root.findall('value'):
            e_id_node = value_node.find('id')
            e_min_node = value_node.find('elapsed')
            player1_node = value_node.find('player1') # The goalscorer/carded player!
            
            if e_id_node is not None and e_min_node is not None:
                # Safely extract player_id if it exists
                player_id = None
                if player1_node is not None and player1_node.text and player1_node.text.isdigit():
                    player_id = int(player1_node.text)

                events.append((
                    match_id, 
                    int(e_id_node.text), 
                    int(e_min_node.text), 
                    event_type,
                    player_id # Added to the tuple
                ))
    except ET.ParseError:
        pass # Safely ignore malformed XML chunks
    
    return events