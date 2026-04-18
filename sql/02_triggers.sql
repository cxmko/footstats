-- sql/02_triggers.sql

CREATE OR REPLACE FUNCTION update_team_points() RETURNS TRIGGER AS $$
BEGIN
    -- 1. Handle DELETE or UPDATE: Subtract the old points first
    IF (TG_OP = 'DELETE' OR TG_OP = 'UPDATE') THEN
        IF OLD.home_team_goal > OLD.away_team_goal THEN
            UPDATE Team SET total_points = total_points - 3 WHERE team_api_id = OLD.home_team_api_id;
        ELSIF OLD.home_team_goal < OLD.away_team_goal THEN
            UPDATE Team SET total_points = total_points - 3 WHERE team_api_id = OLD.away_team_api_id;
        ELSE
            UPDATE Team SET total_points = total_points - 1 WHERE team_api_id = OLD.home_team_api_id;
            UPDATE Team SET total_points = total_points - 1 WHERE team_api_id = OLD.away_team_api_id;
        END IF;
    END IF;

    -- 2. Handle INSERT or UPDATE: Add the new points
    IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') THEN
        IF NEW.home_team_goal > NEW.away_team_goal THEN
            UPDATE Team SET total_points = total_points + 3 WHERE team_api_id = NEW.home_team_api_id;
        ELSIF NEW.home_team_goal < NEW.away_team_goal THEN
            UPDATE Team SET total_points = total_points + 3 WHERE team_api_id = NEW.away_team_api_id;
        ELSE
            UPDATE Team SET total_points = total_points + 1 WHERE team_api_id = NEW.home_team_api_id;
            UPDATE Team SET total_points = total_points + 1 WHERE team_api_id = NEW.away_team_api_id;
        END IF;
    END IF;

    IF (TG_OP = 'DELETE') THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_points ON Match;
CREATE TRIGGER trigger_update_points
AFTER INSERT OR UPDATE OR DELETE ON Match
FOR EACH ROW EXECUTE FUNCTION update_team_points();