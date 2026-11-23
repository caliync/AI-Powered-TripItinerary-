# Seed data

These files are copies of the project Google Sheet, made on 2026-11-18. They load into an empty database the first time the API starts.

| File | Sheet tab | What it is |
| --- | --- | --- |
| `calamba_curated.csv` | Places | Hand-researched places. `alli_decision` controls status: Approve makes a place featured, Reject hides it, and blank keeps it listed. |
| `calamba_osm_places.csv` | Calamba_All_Places | 592 public places and businesses taken from OpenStreetMap. |

When the Sheet changes, export these two tabs as CSV with the same column names, replace these files, and delete `app.db` so the database reseeds.

Map data © OpenStreetMap contributors, ODbL.

## Public places and private venues

The seed splits rows in two. Walk-in public places go to the `places` table and can appear in plans.
Resorts, water parks and pools are checked for walk-in evidence (`app/places/rules.py`, `walk_in`):

- **Alli's call** in the Sheet's `alli_walk_in` column (Walk-in or Private) beats every rule below.
- **Walk-in** (stays a place): on Alli's curated list, has a website or Wikidata, or lists swim hours.
- **Private** (`walk_in = no`): "private" in the name, private access, or open 24/7 (whole-place rentals).
- **Unknown**: no evidence either way. A person decides.

Private and unknown resorts go to `private_venues`. The planner never reads that table. Its `partnership`
column (`none`, `contacted`, `partner`) tracks partnership work.
