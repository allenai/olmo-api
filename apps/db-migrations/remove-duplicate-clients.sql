-- wrapped in transaction for safety

BEGIN;

-- filter down to duplicates first
WITH dupes AS (
    SELECT client
    FROM olmo_user
    GROUP BY client
    HAVING COUNT(*) > 1
),
-- select from dupes ordered by the most recent date (DESC - newest wins)
ordered_dupes AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY client
            ORDER BY GREATEST(
                terms_accepted_date,
                COALESCE(acceptance_revoked_date, '-infinity'::timestamptz),
                COALESCE(data_collection_accepted_date, '-infinity'::timestamptz),
                COALESCE(data_collection_acceptance_revoked_date, '-infinity'::timestamptz),
                COALESCE(media_collection_accepted_date, '-infinity'::timestamptz),
                COALESCE(media_collection_acceptance_revoked_date, '-infinity'::timestamptz)
            ) DESC
        ) AS row_number
    FROM olmo_user
    JOIN dupes ON olmo_user.client = dupes.client
)
DELETE FROM olmo_user
WHERE id IN (SELECT id FROM ordered_dupes WHERE row_number > 1);

ROLLBACK;
-- COMMIT;