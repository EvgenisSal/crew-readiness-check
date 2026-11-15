# Crew Readiness Check

**NASA Space Apps Challenge 2026 · Thessaloniki**
Challenge: *Create Health Monitoring Software for Astronauts on Space Missions*

A 3-minute reaction test (PVT-B, like NASA's Reaction Self Test on the ISS) tells an astronaut and the commander, without waiting for Earth, whether they are ready for the next critical task, and warns before fatigue builds up.

- **Self-test** (`selftest.html`): sleepiness and mood check-in, then a reaction test. The result (READY / CAUTION / NOT READY) compares the astronaut with their own pre-flight baseline.
- **Crew dashboard** (`dashboard.html`): the whole crew at a glance, vital signs from a wearable, trends, alerts, and who is cleared for the next EVA.
- Runs fully offline, as it would on a spacecraft's local network. Only the report to flight surgeons waits for the next communication window.

## Rules
- Readiness color from the reaction test only: diff% = (mean RT − baseline) / baseline × 100.
  NOT READY: diff > 20% or ≥ 4 lapses · CAUTION: diff > 10% or 2–3 lapses · READY otherwise.
- Lapse = response ≥ 355 ms (Basner et al., 2011). False start = response before the stimulus or < 130 ms.
- Vital signs are shown separately and do not change the readiness color.

## Run it
```
python3 -m http.server 8000
```
then open http://localhost:8000. The pages also work by double-clicking (crew data is embedded as a fallback).

## Data
All crew data are **simulated** (`generate_crew.py`, fixed seed). The rule "+4% reaction time per missing hour of sleep below 6 h" is our simplification for the demo, not a published finding.

## Prototype limitations
- Results are stored in the browser (localStorage), so the dashboard sees self-test results only in the same browser. On a spacecraft this would be a small server on the local network.
- Guest mode compares against a default baseline of 250 ms, because no guest baseline was measured.
- The 30-second demo test is for demonstration only and is labelled "30 s demo" on the dashboard; the lapse cutoffs are meant for the full 3-minute test.

## Use of AI
We used AI assistants (Claude by Anthropic, and Gemini by Google) to help write and debug the code of the self-test and dashboard, to extend the data generator, to script the screen recording of the demo video, and to look up and check sources. The team chose the concept, the rules and the thresholds, and reviewed and tested all code. The demo video is a screen recording of the real app, not AI-generated footage. All crew data are simulated.

## Team
- Evgenios: Science, Threshold and Sources
- Sarantis: Self-Test
- Vasilis: Crew Dashboard
- Periklis: Simulated Crew Data and Demo
- George: Pitch and Submission

## Live Site  
https://evgenissal.github.io/crew-readiness-check/

*Decision-support prototype, not a medical device.*
