-- sql/02_triggers.sql

-- Create the function containing the logic
CREATE OR REPLACE FUNCTION update_team_points()
RETURNS TRIGGER AS $$
BEGIN
    -- Home team wins (3 points)
    IF NEW.home_team_goal > NEW.away_team_goal THEN
        UPDATE Team 
        SET total_points = total_points + 3 
        WHERE team_api_id = NEW.home_team_api_id;
        
    -- Away team wins (3 points)
    ELSIF NEW.away_team_goal > NEW.home_team_goal THEN
        UPDATE Team 
        SET total_points = total_points + 3 
        WHERE team_api_id = NEW.away_team_api_id;
        
    -- Draw (1 point each)
    ELSE
        UPDATE Team 
        SET total_points = total_points + 1 
        WHERE team_api_id = NEW.home_team_api_id;
        
        UPDATE Team 
        SET total_points = total_points + 1 
        WHERE team_api_id = NEW.away_team_api_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Bind the function to an AFTER INSERT trigger on the Match table
CREATE TRIGGER after_match_insert
AFTER INSERT ON Match
FOR EACH ROW
EXECUTE FUNCTION update_team_points();