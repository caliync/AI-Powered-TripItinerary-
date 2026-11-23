"""Places data layer: OSM import, status rules, merge and owner submissions.

Flow: osm_import (pbf -> OsmRecord) -> merge.merge_run (-> PlaceRecord upserts)
      submissions -> matching.best_match -> person approves -> matching.apply_owner_data
"""
