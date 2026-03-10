"""
Story Builder Engine (Phase 5) — assembles ranked clips into narrative timelines.

Sub-modules:
  template_loader  — load + validate story template JSON files
  clip_ranker      — multi-signal clip ranking
  slot_assigner    — assign ranked clips to narrative slots
  flow_enforcer    — deduplication, pacing, transition selection
  timeline_builder — persist Timeline + TimelineElement rows to DB
  mashup_engine    — multi-source clip combination
"""
