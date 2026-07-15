BEGIN;

ALTER TABLE visitor_interaction
    DROP COLUMN IF EXISTS satisfaction_score;

COMMIT;
