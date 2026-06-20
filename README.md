# tacs-riskamb

A research-oriented Pygame task for studying decisions under risk and learned ambiguity with symmetric and positively skewed monetary outcomes.

## Scientific design

The task is a 2 × 2 within-participant design. **Symmetric** and **positive skew** describe the distribution of monetary outcomes, not a distribution of probabilities. **Risk** means the exact probability is displayed. **Learned ambiguity** (`hidden_probability` in code) means the probability display is completely masked, while the run-specific cue and outcome amounts remain visible.

| Outcome distribution | Gain | Loss | Gain probability | Risk trials | Hidden-probability trials |
| --- | ---: | ---: | ---: | ---: | ---: |
| Symmetric | +$3.05 | −$3.05 | .50 | 20 | 20 |
| Positive skew | +$5.25 | −$1.75 | .25 | 20 | 20 |

The alternative is guaranteed $0. The default run contains 80 trials arranged into ten mini-blocks. Every mini-block contains two trials from each cell. Gamble side is balanced within every cell. The full schedule and all latent outcomes are generated and saved before the run begins.

There is no negative-skew condition. Published probabilities and amounts live only in [`config/default.json`](config/default.json).

### Learning manipulation

Each run maps two visually redundant cues (color plus shape) to the two gamble types. A visible-probability exposure to each cue precedes its first hidden-probability exposure in mini-block 1. The exact probability is shown on risk trials; hidden trials display a constant gray circle and `?`, with no probability text or informative wedge. The lottery outcome is normally shown after every trial, including safe choices and misses, so learning opportunities are comparable.

“Ambiguity” is not assumed to remain constant: exact-probability exposures and outcome feedback accumulate during the run. Each events row records the objective information state available before that choice.

## Installation

Python 3.9 or newer is supported.

```bash
git clone https://github.com/DVS-Lab/tacs-riskamb.git
cd tacs-riskamb
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`pylsl` is deliberately not a required dependency. Install it separately only on machines that use LSL.

## Running the task

```bash
python code/main.py
python code/main.py --subject 001 --session 1 --run 1
python code/main.py --test --windowed --subject 001 --session 1 --run 1
python code/main.py --subject 001 --session 1 --run 1 --seed 12345
```

If any identifier is missing, an experimenter-only Pygame setup screen collects subject, session, run, display, fullscreen, trigger mode, and test mode before the participant receives the display. CLI identifiers accept optional `sub-`/`ses-` prefixes and are validated.

The first run presents multi-page instructions, a comprehension check, and four practice trials using cues, amounts, and probabilities that never appear experimentally. Incorrect comprehension responses cause the relevant instruction page to reappear. Later runs use a short reminder. The post-run phase includes cue belief estimates (0–100%), confidence (1–9), and, when enabled, the standard 20-item PANAS “right now” questionnaire.

### Development automation

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  python code/main.py --test --windowed --subject AUTO --session 1 --run 1 \
  --auto-respond --skip-instructions
```

Automated mode simulates choices and RTs. Its output goes under `data/development/` unless `--data-dir` is supplied, so it cannot silently mix with participant data.

## Configuration

[`config/default.json`](config/default.json) contains all gamble values, timing, keys, display settings, cue definitions, payoff rules, paths, and markers. [`config/test.json`](config/test.json) recursively extends it with eight trials (two per cell) and millisecond-scale timings.

Default state timing, in milliseconds:

| State | Duration |
| --- | ---: |
| Fixation | uniform 400–700 |
| Choice | response-terminated, maximum 2500 |
| Selection highlight | 250 |
| Pre-feedback blank | uniform 400–600 |
| Feedback | 1000 |
| ITI | uniform 600–900 |
| Optional first-trial fixation buffer | 5000 |

Responses default to `F` (left) and `J` (right). Configurable button-box keys are also accepted. All waits pump Pygame events and use `time.perf_counter()`; no `time.sleep()` is used in presentation states. The event queue is cleared immediately before choice onset.

### Payoff modes

- `random_trial` (default): sample one valid completed trial after the run. The summary stores the eligible trial list, sampled trial, choice, and raw chosen outcome.
- `cumulative`: use the sum of all chosen outcomes.
- `points_only`: record outcomes without calculating a cash result.

Running wealth is logged but not displayed by default. Sites should define how negative raw outcomes, base compensation, exchange rates, and minimum bonuses are converted into payment before data collection.

## Counterbalancing and reproducibility

If `--seed` is omitted, SHA-256 of subject, session, run, and task name produces a stable NumPy seed. Python’s process-randomized `hash()` is never used. The seed is saved in events and metadata.

Cue pairs rotate over successive runs. On pair reuse, the mapping reverses. Subject identity determines the initial orientation reproducibly. Each planned schedule contains the exact cue mapping, RGB/name, shape, sides, probability disclosure, amounts, and latent outcome. Per-cell outcome counts are stratified to 10/10 gains/losses for each 20-trial symmetric cell and 5/15 for each positive-skew cell. Among valid stratifications, the generator prefers schedules without long identical-outcome runs but does not force alternation.

## Laboratory synchronization

`triggers.start_mode` accepts `space`, `scanner`, or `lsl`. Space remains a manual fallback. The scanner key defaults to `5`. When `pylsl` is installed and `lsl_enabled` is true, the task can listen for marker `203` and publish its configurable marker map. Otherwise it runs normally.

Every marker is flushed to a local marker CSV regardless of LSL state:

| Event | Default code |
| --- | ---: |
| Run start / end | 100 / 200 |
| Trial start | 10 |
| Symmetric risk / hidden onset | 11 / 12 |
| Positive-skew risk / hidden onset | 13 / 14 |
| Response | 20 |
| Gamble / safe selected | 21 / 22 |
| Gain / loss / miss feedback | 31 / 32 / 33 |

## Data files

Files use `sub-{ID}_ses-{SESSION}_run-{RUN}_task-riskambiguity_*`. A UTC timestamp and counter are added if a collision exists; existing data are never replaced. Automated data use a separate directory.

| Suffix | Contents |
| --- | --- |
| `_planned.csv` | Complete pre-generated design and latent outcomes, saved before trial 1 |
| `_events.csv` | Experimental trial rows, flushed and `fsync`'d after every completed trial |
| `_practice.csv` | Practice rows with `practice=True` |
| `_markers.csv` | Local marker labels, codes, monotonic timestamps, optional LSL timestamps |
| `_config.json` | Exact recursively resolved configuration |
| `_metadata.json` | IDs, seed, commit, cue mapping, output paths, completion/abort/error state |
| `_summary.json` | Beliefs, confidence, PANAS scores/responses, comprehension, payoff selection, duration |

On Escape, window close, an exception, or process interruption after a completed trial, prior rows remain readable. A caught abort/error is also written to metadata and summary. The planned schedule permits reconstruction after an uncatchable power loss.

### Events data dictionary

Blank means not applicable or unavailable. Times ending in `_ms` are milliseconds; onset/time columns are relative to run start and use a monotonic clock.

| Group | Columns | Definition |
| --- | --- | --- |
| Identification | `subject_id`, `session`, `run` | Validated run identifiers |
|  | `task_version`, `git_commit`, `configuration_file`, `random_seed`, `timestamp_utc` | Software/config provenance and wall-clock row time |
| Design | `trial_number`, `mini_block`, `practice` | Position and practice flag |
|  | `skew_condition`, `information_condition` | Outcome distribution and `risk`/`hidden_probability` cell |
|  | `cue_id`, `cue_color`, `cue_shape`, `cue_mapping` | Run cue and complete mapping label |
|  | `gamble_side`, `safe_side` | Spatial assignment |
|  | `p_gain_actual`, `p_gain_displayed` | Programmed probability and displayed value (blank when hidden) |
|  | `gain_amount`, `loss_amount`, `safe_amount`, `outcome_preassigned` | Configured outcomes and pre-generated latent result |
| Response | `response_key`, `response_side`, `choice` | Physical response and gamble/safe/miss interpretation |
|  | `gamble_selected`, `responded`, `reaction_time_ms`, `response_deadline_ms` | Response indicators and RT |
| Outcome | `realized_outcome_type`, `realized_outcome_amount` | Latent gain/loss and amount, whether chosen or counterfactual |
|  | `chosen_outcome_amount` | Amount affecting earnings; blank on miss |
|  | `counterfactual_outcome_shown`, `cumulative_total`, `bonus_eligible` | Feedback, running chosen total, and valid-trial eligibility |
| Timing | `run_elapsed_at_trial_start_ms`, `fixation_onset_ms`, `choice_onset_ms`, `response_time_ms`, `feedback_onset_ms`, `trial_end_ms` | State/event onsets |
|  | `fixation_duration_ms`, `pre_feedback_delay_ms`, `iti_duration_ms` | Sampled jitters |
|  | `dropped_frame_warning` | True if a timed state observed a frame interval over twice its budget |
| Learning | `prior_cue_exposures` | Previous trials with this cue |
|  | `prior_visible_probability_cue_exposures`, `prior_hidden_probability_cue_exposures` | Previous cue exposures by information condition |
|  | `prior_observed_gains`, `prior_observed_losses`, `prior_empirical_gain_rate` | Outcomes actually shown before this trial |
|  | `trials_since_cue_first_shown` | Current trial number minus first cue trial; blank at first exposure |
|  | `exact_probability_previously_displayed`, `most_recently_displayed_probability` | Prior exact-probability information |
|  | `most_recent_realized_outcome_for_cue` | Latest previously shown cue outcome |

Learning columns are computed before the current trial and updated only after its feedback, preventing current-outcome leakage.

## Timing simulation

Run:

```bash
python scripts/simulate_run_duration.py
```

With 10,000 simulations and the default 80 trials, the predicted run durations are:

| RT profile | Median | 90th percentile |
| --- | ---: | ---: |
| Fast younger adult (550 ms median RT) | 4.91 min | 4.95 min |
| Typical younger adult (800 ms) | 5.27 min | 5.32 min |
| Slower responder (1100 ms) | 5.70 min | 5.79 min |

These estimates **include** the optional five-second fixation buffer and exclude instructions, practice, waiting for a trigger, belief probes, and PANAS. Results and assumptions are saved in [`docs/timing_simulation.json`](docs/timing_simulation.json). Trial count can be changed to any positive multiple of eight (including 88 or 96) for piloting.

## Testing and visual QA

```bash
pytest -q
python scripts/generate_stimulus_screenshots.py
```

The suite includes a 1,000-seed headless schedule test, exact cell/side/outcome checks, cue reproducibility, learning-history leakage checks, probability-disclosure audits, crash persistence, collision protection, a missing-`pylsl` check, schema validation, timing simulation, and an eight-trial automated integration run.

Representative displays are in [`docs/screenshots/`](docs/screenshots/), and manual/automated findings are in [`docs/qa_report.md`](docs/qa_report.md).

## Extending probability learning

`ProbabilityGenerator.probability_for_trial()` in [`code/outcome_generation.py`](code/outcome_generation.py) is the boundary for a future distribution-learning model. A later generator can sample a trial-specific probability conditional on cue and write it to `p_gain_actual`; the renderer, trial loop, planned schedule, and events schema already consume that field and need not change. Any such change should also define how stratification operates when probabilities vary across trials.

## Known scientific decisions

- Learned ambiguity diminishes as participants see exact probabilities and outcomes. Analyses should model information history rather than treat hidden trials as a stationary uncertainty condition.
- The default symmetric value is the published $3.05 and is configurable if later variance-matching decisions change it.
- The current default provides full counterfactual lottery outcomes. Disabling them changes the learning process and should be treated as a protocol change.
- Final bonus conversion, negative-outcome handling, the final 80/88/96 trial count, and whether PANAS belongs before, after, or both around the run remain study-protocol decisions.

## Provenance and AI assistance

Architecture/workflow ideas were reviewed against `DVS-Lab/tacs_bandit`; flower assets, reversal logic, and bandit terminology were not reused. The available reference clone and its Git history did not contain a PANAS implementation, so this repository uses the standard 20-item PANAS adjectives and conventional positive/negative sums in a standalone module.

This repository was designed and implemented with substantial assistance from OpenAI Codex. Human investigators remain responsible for scientific validity, participant-safety review, payment rules, hardware validation, and final protocol approval.
