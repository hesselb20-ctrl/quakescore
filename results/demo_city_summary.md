# Demo city summary

Footprints and tags: **REAL** (OpenStreetMap contributors, ODbL), downtown San Francisco.
Structures, contributors, sessions, scores, anomalies and drift: **SIM**. No real session has been contributed.

Simulated scores attached to real footprints must never be presented as assessments of those buildings.
Footprints with neither a level count nor a height tag (95 of 687) were treated as single-storey.

Footprints: 687 (687 with a storey count). Simulated sessions: 30404.

| Status | Buildings |
|---|---|
| scored | 222 |
| needs_data | 255 |
| no_data | 210 |

| Storeys | Footprints | With at least one session | Scored |
|---|---|---|---|
| 1-3 | 231 | 72 | 7 |
| 4-7 | 180 | 136 | 21 |
| 8-14 | 134 | 127 | 63 |
| 15-29 | 86 | 86 | 76 |
| 30+ | 56 | 56 | 55 |

Against the simulated truth (scored buildings only):

- First-mode frequency: median absolute error 0.04%, 90th percentile 0.34%,
  within 5% in 94.1% of buildings; wrong mode picked in 13.
- Stiffness anomalies: 25 planted, 8 of them scored, 3 flags raised,
  2 correct.
- Simulated damage: 4 scored buildings lost 12% stiffness; 5 drift alerts, 4 correct.
- Score: median 84.65, median band width 23.5 points (class-based prior: 29.2).
