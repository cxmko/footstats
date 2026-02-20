from graphviz import Graph

def create_er_graph(name="FootStats_ER_Clean"):
    # 1. Switched engine from 'neato' to 'dot' for clean, hierarchical layouts
    dot = Graph(name, format='png', engine='dot')
    
    # 2. Added global graph attributes for an efficient layout
    dot.attr(rankdir='TB')       # Top-to-Bottom layout (fixes the extreme horizontal spread)
    dot.attr(splines='true')     # Uses smooth, curved lines to navigate around nodes gracefully
    dot.attr(nodesep='0.7')      # Horizontal spacing between nodes
    dot.attr(ranksep='1.0')      # Vertical spacing between layers
    
    return dot

def add_entity(dot, name, is_weak=False):
    peripheries = '2' if is_weak else '1'
    dot.node(name, name, shape='box', peripheries=peripheries)

def add_attribute(dot, parent_name, attr_name, is_pk=False, is_partial_key=False):
    node_id = f"{parent_name}_{attr_name}"
    if is_pk:
        label = f"<<U>{attr_name}</U>>" 
    elif is_partial_key:
        label = f"{attr_name} (Partial)"
    else:
        label = attr_name
    
    # Added margin='0.05' to make attribute ovals slightly smaller and tighter
    dot.node(node_id, label, shape='ellipse', margin='0.05')
    dot.edge(parent_name, node_id)

def add_relationship(dot, name, entity1, entity2, is_identifying=False, total_part_e1=False, total_part_e2=False, arrow_from_e1=False, arrow_from_e2=False):
    peripheries = '2' if is_identifying else '1'
    dot.node(name, name, shape='diamond', peripheries=peripheries)
    
    pen1 = '3.0' if total_part_e1 else '1.0'
    pen2 = '3.0' if total_part_e2 else '1.0'
    
    dir1 = 'forward' if arrow_from_e1 else 'none'
    dir2 = 'forward' if arrow_from_e2 else 'none'
    
    dot.edge(entity1, name, penwidth=pen1, dir=dir1)
    dot.edge(entity2, name, penwidth=pen2, dir=dir2)


# --- Build the Diagram ---
er = create_er_graph()

# 1. Core Entities
add_entity(er, "Country")
add_entity(er, "League")
add_entity(er, "Team")
add_entity(er, "Player")
add_entity(er, "Match")

# Weak Entities
add_entity(er, "Match_Event", is_weak=True)
add_entity(er, "Betting_Odds", is_weak=True)

# 2. Attributes
add_attribute(er, "Country", "id", is_pk=True)
add_attribute(er, "Country", "name")

add_attribute(er, "League", "id", is_pk=True)
add_attribute(er, "League", "name")

add_attribute(er, "Team", "team_api_id", is_pk=True)
add_attribute(er, "Team", "team_long_name")
add_attribute(er, "Team", "team_short_name")

add_attribute(er, "Player", "player_api_id", is_pk=True)
add_attribute(er, "Player", "player_name")

add_attribute(er, "Match", "match_api_id", is_pk=True)
add_attribute(er, "Match", "date")
add_attribute(er, "Match", "home_team_goal")
add_attribute(er, "Match", "away_team_goal")

add_attribute(er, "Match_Event", "event_id", is_partial_key=True)
add_attribute(er, "Match_Event", "event_type")

add_attribute(er, "Betting_Odds", "bookmaker", is_partial_key=True)
add_attribute(er, "Betting_Odds", "home_win")

# 3. Relationships & Constraints (Arrows from entity to relationship)
add_relationship(er, "Located_In", "League", "Country", total_part_e1=True, arrow_from_e1=True)
add_relationship(er, "Belongs_To", "Match", "League", total_part_e1=True, arrow_from_e1=True)
add_relationship(er, "Plays_Home", "Match", "Team", total_part_e1=True, arrow_from_e1=True)
add_relationship(er, "Plays_Away", "Match", "Team", total_part_e1=True, arrow_from_e1=True)
add_relationship(er, "Occurs_In", "Match_Event", "Match", is_identifying=True, total_part_e1=True, arrow_from_e1=True)
add_relationship(er, "Offered_For", "Betting_Odds", "Match", is_identifying=True, total_part_e1=True, arrow_from_e1=True)

add_relationship(er, "Appearance", "Player", "Match")
add_attribute(er, "Appearance", "X_coordinate")

# 4. Legend (Forced to the bottom of the layout)
legend_html = '''<
    <table border="0" cellborder="1" cellspacing="0" cellpadding="5">
        <tr><td colspan="2" align="center"><b>ER Diagram Legend (Course Style)</b></td></tr>
        <tr><td align="left">Regular Entity</td><td>Rectangle</td></tr>
        <tr><td align="left">Weak Entity</td><td>Double Rectangle</td></tr>
        <tr><td align="left">Relationship</td><td>Diamond</td></tr>
        <tr><td align="left">Identifying Relationship</td><td>Double Diamond</td></tr>
        <tr><td align="left">Regular Attribute</td><td>Oval</td></tr>
        <tr><td align="left">Primary Key</td><td><u>Underlined Text</u></td></tr>
        <tr><td align="left">Total Participation</td><td><b>Thick Line</b></td></tr>
        <tr><td align="left">Key Constraint</td><td>Arrow pointing to Diamond</td></tr>
    </table>
>'''

# Create a specific subgraph locked to the bottom ('sink') for the legend
with er.subgraph(name='cluster_legend') as s:
    s.attr(rank='sink')
    s.attr(color='white') # Hide the cluster bounding box
    s.node('Legend', shape='none', margin='0', label=legend_html)

er.save("FootStats_ER_Clean.gv")
print("Diagram code generated successfully! Render it via GraphvizOnline to see the clean layout.")