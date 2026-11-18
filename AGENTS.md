This project is a notebook containing analytics for my fantasy football league.

Your goal is to transform this notebook into a reproducible repository.

ESPN authentication uses espn_s2 and SWID cookies. Credentials are stored outside this repository at ~/Projects/.secrets/espn.env. Environment variables are named ESPN_S2 and ESPN_SWID. Never read, print, log, copy, modify, or expose the contents of the credentials file. Never hardcode credentials or commit them to Git. Code may reference environment variable names and the external configuration path. Do not execute authenticated ESPN API requests without explicit user approval. Use mocked or sanitized data for testing whenever possible.