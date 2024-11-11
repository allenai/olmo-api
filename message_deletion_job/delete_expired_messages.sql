SELECT id,
    role,
    creator
FROM message
WHERE expiration_time IS NOT NULL
    AND expiration_time <= CURRENT_TIMESTAMP AT TIME ZONE 'utc';

DELETE FROM message
WHERE expiration_time IS NOT NULL
    AND expiration_time <= CURRENT_TIMESTAMP AT TIME ZONE 'utc';