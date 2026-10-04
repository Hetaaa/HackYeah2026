# Wellness evaluation

Four chronological test blocks per user; pooled training strictly before each cutoff.
Fixed seeds 0,1,2; paired test-day bootstrap (2000, seed 0).
Class order: bad=0, neutral=1, good=2; macro-F1 includes all three classes.
Night inputs are supplied pre-survey; calendar features are known in advance.
Input labels and composites are supplied targets. The source CSV calibrates them on
the full pre-lockdown window; offline results are conditional on that target definition.
The API freezes historical labels/composites using each day's available survey history.

| Variant | Test days | Macro-F1 (95% CI) | Balanced accuracy | Mean user F1 |
| --- | ---: | --- | ---: | ---: |
| safeguard | 557 | 0.4789 (0.4380, 0.5198) | 0.5081 | 0.3542 |
| without_safeguard | 557 | 0.4789 (0.4380, 0.5198) | 0.5081 | 0.3542 |

## safeguard

Eligible sleep-after-survey rows: 0.
- yesterday: macro-F1 0.4415; model minus baseline 95% CI [-0.0133, 0.0878].
- majority: macro-F1 0.2710; model minus baseline 95% CI [0.1580, 0.2590].
- Personas pooled macro-F1: 0.515030670083081.
- p01: 0.3026.
- p06: 0.4266.
- p10: 0.4079.
- p16: 0.5765.
The day bootstrap does not account for within-user temporal dependence.

## without_safeguard

Eligible sleep-after-survey rows: 0.
- yesterday: macro-F1 0.4415; model minus baseline 95% CI [-0.0133, 0.0878].
- majority: macro-F1 0.2710; model minus baseline 95% CI [0.1580, 0.2590].
- Personas pooled macro-F1: 0.515030670083081.
- p01: 0.3026.
- p06: 0.4266.
- p10: 0.4079.
- p16: 0.5765.
The day bootstrap does not account for within-user temporal dependence.