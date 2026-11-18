# Hagerstown FF League Analytics

## Description
This project is a notebook containing analytics for my fantasy football league.
Full-PPR, redraft.

Your goal is to transform this notebook into a reproducible repository which
can support a simple analytics webpage.

## Secrets notice

ESPN authentication uses espn_s2 and SWID cookies. Credentials are stored outside this repository at ~/Projects/.secrets/espn.env. Environment variables are named ESPN_S2 and ESPN_SWID. Never read, print, log, copy, modify, or expose the contents of the credentials file. Never hardcode credentials or commit them to Git. Code may reference environment variable names and the external configuration path. Do not execute authenticated ESPN API requests without explicit user approval. Use mocked or sanitized data for testing whenever possible.

## League setup

Every season, the regular season is about 13-14 weeks. Then, the playoffs begin, ending in
the penultimate week of the season. The final week of the NFL season is excluded.

For playoff performance, we want to monitor games only in which teams had something to play for.

### Teams that make the playoffs

Playoff teams have stakes until they either lose or reach the championship. Once a playoff team has lost, their season is over. 3rd place games, 5th place games, etc are meaningless.

### Teams that miss the playoffs

The league has a punishment for losing out of the consolation bracket, so playoff missers have stakes until they either win or reach the "toilet bowl finals", where the two teams that have continued to lose through the playoff weeks meet.