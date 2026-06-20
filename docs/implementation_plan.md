# Implementation plan

This plan was written after inspecting `DVS-Lab/tacs_bandit` on 2026-06-20.

## Reference patterns to retain

- Central JSON configuration for timing, display, hardware, and paths.
- Experimenter-side identifier/display setup followed by participant-only screens.
- Optional `pylsl` import, trigger-or-space run start, and a local record for every marker.
- A pre-run fixation buffer, per-run cue selection/counterbalancing, and BIDS-inspired filenames.
- Clear operator logging and continued behavioral operation when laboratory hardware is absent.

The reference's flower stimuli, two-armed-bandit terminology, contingency reversals, and stimulation-specific logic will not be reused. A repository-wide and history-wide search found no PANAS code in the available reference clone; this project will therefore implement the standard 20 PANAS adjectives, a 1–5 "right now" response scale, and positive/negative subscale totals in a self-contained module.

## Build sequence

1. Create validated configuration models plus reproducible cue mapping, constrained schedule generation, stratified latent outcomes, and pretrial learning-history calculation.
2. Add crash-resistant CSV/JSON output, local/optional-LSL markers, payoff calculation, timing simulation, and a Pygame state-driven presentation layer.
3. Add participant instructions, practice and comprehension logic, PANAS, run-start synchronization, post-run belief probes, experimenter setup, and automated development mode.
4. Add headless tests (including 1,000 seeds), programmatic stimulus screenshots, a QA report, and a complete README/data dictionary.
5. Run automated tests and headless smoke runs, inspect representative screenshots, fix defects, then publish clear commits directly to `main`.

## Verification gates

- Every default mini-block has two trials per cell; all run-level balance/order/outcome constraints pass.
- Hidden displays expose neither a probability label nor an informative wedge.
- The planned schedule exists before trial one, trial rows are flushed incrementally, filenames do not overwrite, and abort metadata is recoverable.
- Pygame imports and task startup succeed without `pylsl`; automated test mode completes rapidly.
- Duration simulation reports median and 90th-percentile durations with the optional five-second buffer explicitly identified.
