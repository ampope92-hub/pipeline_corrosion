# In-line inspection export — 2026-05-18

One row per pipeline segment, whitespace-delimited with a header line. `history.dat` is the
segments we have already run the tool through and adjudicated, with the defect count recorded.
`survey.dat` is the stretch we are planning next season — same columns, count not included.

## Columns

| column | source | description |
|---|---|---|
| `seg_id` | GIS | segment identifier |
| `length_km` | GIS | inspected length of the segment |
| `age_yr` | asset register | years since the segment was laid |
| `cp_mv` | CP survey | cathodic protection potential, mV (more negative is better protected) |
| `coat` | construction record | coating system: `fbe`, `tape` or `cte` |
| `soil` | soils survey | dominant soil along the segment: `sand`, `clay`, `loam` or `peat` |
| `op_press_bar` | SCADA | mean operating pressure over the period |
| `defects` | ILI report | metal-loss indications the tool called on that segment (history only) |

## Notes

Segments are not cut to a standard length. They are bounded by valves, road crossings and
survey breaks, so the shortest in this export is under a hundred metres and the longest is
about forty kilometres. Both cohorts are cut the same way and the length distribution is the
same in each.

The tool run is the same on every segment and the adjudication procedure has not changed
between the two cohorts. Nothing in this export has been rescaled or normalised on the way
out.
