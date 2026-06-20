# QA report

Date: 2026-06-20

Final automated result: **19 tests passed**. Separate accelerated 80-trial runs completed with 80 durable rows in both windowed and fullscreen code paths.

## Automated scope

- Design balance and all order constraints across 1,000 seeds.
- Exact default/test cell counts, side balance, cue reproducibility, and stratified outcomes.
- Pretrial learning histories exclude the current trial outcome.
- Hidden renderer audit reports no probability text and no informative wedge; visible renderer reports both.
- Incremental rows survive an intentional exception and collision handling preserves existing output.
- Marker logging starts without `pylsl`; test-mode automated presentation completes headlessly.
- Complete events schema and Monte Carlo duration assumptions are checked.

## Visual checklist

The screenshot utility uses the production `StimulusRenderer`. Review confirmed:

- Four factorial displays are legible and programmatically distinct.
- Hidden displays use the same fully opaque gray circular mask at 25% and 50%; no wedge edge or percentage is present.
- Gain/loss amounts remain visible in both information conditions.
- Selection highlights unambiguously surround only the chosen side.
- Safe-choice and missed feedback label the decision and reveal the counterfactual lottery result.
- Belief estimate controls and cue identity are legible at 1280 × 800.

## Laboratory checks still required

- Confirm font size, viewing distance, color/brightness, and fullscreen placement on the actual monitor.
- Confirm scanner/button-box key codes and LSL stream discovery on the acquisition computer.
- Measure real display flip timing and dropped-frame rate on study hardware.
- Pilot comprehension, learning, fatigue, PANAS placement, and bonus wording with the approved protocol.
