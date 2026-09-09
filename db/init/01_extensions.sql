-- Extensions used by the project.
-- pgcrypto gives us gen_random_uuid() for surrogate keys where useful.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
