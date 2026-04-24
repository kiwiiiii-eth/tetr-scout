# TETR Scout

Public TETR.IO statistics analysis toolkit powered by the official `TETRA CHANNEL API`.

TETR Scout is a public-data project for `TETR.IO`. Its intended scope is:

`manual username lookup, public stats viewer, post-match review`

The project is intended for public profile lookup, public league trend reporting, and post-match analysis. It is not intended to function as a gameplay aid, solver, or real-time competitive advantage tool.

## Fair Play Notice

Tetr Scout only uses publicly available data from the official `TETRA CHANNEL API`. It does not access the `TETR.IO` main game API, modify the game client, automate gameplay, provide solver output, or offer real-time move suggestions. The tool is intended for public profile lookup, post-match review, and league trend analysis.

In practical terms:

- Uses the official public API at `https://ch.tetr.io/api/`
- Does **not** use the main game API at `https://tetr.io/api/`
- Does **not** modify the `TETR.IO` client
- Does **not** automate gameplay
- Does **not** provide solver output, move suggestions, or real-time tactical advice
- Does **not** access hidden or private data
- Is intended only for public player statistics lookup, post-match review, and league trend reporting

## Project Scope

The repository currently contains two public-data components:

- `CLI / HTML analysis`
  Generates public statistics summaries, trend reports, and post-match style review views from official public endpoints
- `Browser-based public stats viewer`
  A small web-based interface for manual username lookup and public statistics viewing

The intended product positioning is a public statistics analysis toolkit, not a gameplay assistant.

## Data Sources

This project is designed to use only documented public endpoints from the official `TETRA CHANNEL API`, including:

- `/users/:user`
- `/users/:user/summaries/league`
- `/labs/leagueflow/:user`
- `/labs/league_ranks`
- `/users/:user/records/league/recent`

Official API documentation:

- `https://tetr.io/about/api/`

## API Usage Guidelines

When using the official API, the project aims to follow these basic guidelines:

- Respect API cache headers
- Avoid excessive requests
- Apply client-side caching when possible
- Use `X-Session-ID` for repeated related queries when appropriate
- Follow a conservative default rate of approximately `1 request per second`

These guidelines are intended to keep usage reasonable and aligned with the public API model.

## What The Tool Is For

- Public player statistics lookup
- League trend summaries
- Historical rating and win-rate reporting
- Post-match review and resilience-style reporting based on public records
- Self-review or general public profile analysis

## What The Tool Is Not For

- Real-time gameplay assistance
- Solver output
- Move recommendation
- Match-time tactical guidance
- Client modification
- Hidden-data inspection
- Automation or botting

## CLI Usage

```bash
python3 analyze_tetr.py <username>
```

Examples:

```bash
python3 analyze_tetr.py osk --timezone Asia/Taipei
python3 analyze_tetr.py osk --records-limit all --lang en
python3 analyze_tetr.py osk --records-limit all --html-report
```

Language options:

```bash
python3 analyze_tetr.py osk --lang zh
python3 analyze_tetr.py osk --lang en
python3 analyze_tetr.py osk --lang both
```

Optional CSV export:

```bash
python3 analyze_tetr.py osk --csv output/osk_leagueflow.csv
```

Optional HTML report:

```bash
python3 analyze_tetr.py osk --records-limit all --html-report
python3 analyze_tetr.py osk --records-limit all --html-report output/osk_full_report.html
```

## Browser-Based Interface

The repository also includes an optional browser-based interface under [extension/](extension/) for:

- manual username lookup
- public stats viewing
- post-match review style summaries

Its intended purpose is public statistics viewing only.

## Repository Note

This repository is being positioned conservatively around official public API usage and fair-play-safe public statistics analysis. If official feedback indicates that any part of the project should be revised, restricted, or removed, the project scope can be adjusted accordingly.
