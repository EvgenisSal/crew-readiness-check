#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_crew.py -- Simulated crew data for the demo "Crew Readiness Check".

* Standard library only, fixed random seed -> the same crew.json on every run.
* ALL DATA ARE SIMULATED (they do not come from real astronauts).
* Writes crew.json next to this script and then runs a scenario check.
"""
import json
import os
import random
import sys

SEED = 2026
FIRST_DAY, LAST_DAY = -100, 30
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crew.json")

# ---------------------------------------------------------------------------
# NOTE -- A SIMPLIFICATION FOR THE DEMO, NOT A FINDING FROM THE LITERATURE:
# The rule "+4% of baseline for every hour of sleep missing below 6" and the
# "+5% accumulated fatigue" are OUR OWN simplification to get a clear demo.
# The literature only says that sleep <= 6 h is associated with slower
# responses (study of 24 ISS astronauts). No such linear formula exists.
# ---------------------------------------------------------------------------
SLEEP_PENALTY_PER_HOUR = 0.04   # fraction of baseline per hour missing below 6
ACCUMULATED_FATIGUE = 0.05      # extra fraction if the previous 3 nights were < 6 h

# id, role, "true" baseline RT (ms), hr, spo2, temp, bp_sys, bp_dia (personal baselines)
CREW = [
    (1, "Commander",          236, 60, 98, 36.6, 112, 70),
    (2, "Pilot",              244, 64, 98, 36.7, 110, 69),
    (3, "Flight Engineer",    229, 62, 97, 36.5, 114, 72),
    (4, "Flight Engineer",    238, 66, 98, 36.6, 113, 71),
    (5, "Mission Specialist", 246, 63, 98, 36.7, 114, 72),
]
# Our team as the crew (in this order)
NAMES = {1: "Evgenios", 2: "Sarantis", 3: "Vasilis", 4: "Periklis", 5: "George"}
BP_ASTRONAUT = 5   # George: high blood pressure scenario

# Scattered YELLOW days for realism (id -> flight days). Deliberately scripted:
# a 5.6-5.9 h night + lapses = 2. Everyone else stays GREEN.
SCATTERED_YELLOW = {2: [9, 21], 3: [15]}

# Random "short" nights (5.6-5.9 h) only up to this day, so the end of the
# flight is clean. Astronaut 4 stops earlier (his fatigue starts suddenly
# on day 25, not gradually out of nowhere).
LAST_RANDOM_SHORT_NIGHT = 23
LAST_RANDOM_SHORT_NIGHT_ASTRONAUT_4 = 20

# George scenario (id 5): high blood pressure while the test stays GREEN
GEORGE_BP = {28: (142, 92), 29: (144, 93), 30: (145, 94)}


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def pick_short_nights(rng, forced, last_day):
    """Random short nights at least 4 days apart (never 3 in a row)."""
    days = set(forced)
    target = rng.randint(3, 5) + len(forced)
    tries = 0
    while len(days) < target and tries < 500:
        tries += 1
        d = rng.randint(2, last_day)
        if all(abs(d - x) >= 4 for x in days):
            days.add(d)
    return days


def sleepiness_for(sleep_h, rng):
    """Sleepiness 1-9: follows sleep."""
    if sleep_h >= 6.5:
        return rng.randint(2, 4)
    if sleep_h >= 6.0:
        return rng.randint(3, 5)
    if sleep_h > 5.5:
        return rng.randint(4, 6)
    return rng.randint(5, 7)


def build_astronaut(spec):
    aid, role, rt_base, hr_b, spo2_b, temp_b, sys_b, dia_b = spec
    # Separate rng per astronaut: a change to one does not affect the others.
    rng = random.Random(SEED * 1000 + aid)
    forced = SCATTERED_YELLOW.get(aid, [])
    last_short = LAST_RANDOM_SHORT_NIGHT_ASTRONAUT_4 if aid == 4 else LAST_RANDOM_SHORT_NIGHT
    short_nights = pick_short_nights(rng, forced, last_short)

    # Phase 1: sleep for all days (needed for the "previous 3 nights")
    sleep = {}
    for d in range(FIRST_DAY, LAST_DAY + 1):
        if d < 0:
            s = clip(rng.gauss(7.5, 0.25), 7.0, 8.0)          # preflight 7.0-8.0
        elif aid == 4 and 25 <= d <= 30:
            s = rng.uniform(5.0, 5.5)                          # SCENARIO astronaut 4
        elif d in short_nights:
            s = rng.uniform(5.6, 5.9)                          # occasional short night
        else:
            s = clip(rng.gauss(6.5, 0.25), 6.0, 7.0)          # inflight 6.0-7.0
        sleep[d] = round(s, 1)

    # Phase 2: everything else
    days = []
    for d in range(FIRST_DAY, LAST_DAY + 1):
        s = sleep[d]
        accumulated = all((sleep.get(d - k) is not None and sleep[d - k] < 6.0) for k in (1, 2, 3))

        # Reaction time
        noise = rng.uniform(-0.03, 0.03)
        rt = rt_base * (1 + noise)
        if s < 6.0:
            rt += (6.0 - s) * SLEEP_PENALTY_PER_HOUR * rt_base
        if accumulated:
            rt += ACCUMULATED_FATIGUE * rt_base
        mean_rt = int(round(rt))

        # Lapses (>= 355 ms)
        if d in forced:
            lapses = 2                                  # scripted scattered YELLOW
        elif accumulated and s < 6.0:
            lapses = rng.randint(4, 6)                  # accumulated fatigue
        elif s <= 5.5:
            lapses = rng.randint(2, 3)
        elif s < 6.0:
            lapses = rng.choice([0, 1])
        else:
            lapses = 1 if rng.random() < 0.15 else 0
        false_starts = rng.choices([0, 1, 2], weights=[50, 35, 15])[0]

        # Sleepiness / mood
        sleepiness = sleepiness_for(s, rng)
        mood = rng.choice([3, 4, 4, 4, 5, 5])
        if s < 6.0:
            mood = max(2, mood - 1)
        exercise = rng.randint(40, 90) if d < 0 else rng.randint(30, 90)

        # Biometrics. Keep sys <= 119 and dia <= 79 so "normal" values are
        # also OK under the BP categories (>= 120 or >= 80 = elevated).
        hr = int(clip(round(hr_b + rng.uniform(-5, 5)), 55, 80))
        spo2 = int(clip(spo2_b + rng.choice([-1, 0, 0, 0, 1]), 96, 99))
        temp = round(clip(temp_b + rng.uniform(-0.15, 0.15), 36.4, 36.9), 1)
        bp_sys = int(clip(round(sys_b + rng.uniform(-4, 4)), 105, 119))
        bp_dia = int(clip(round(dia_b + rng.uniform(-3, 3)), 65, 79))

        # --- Scenarios (overrides, after all random calls) ---
        if aid == 4 and 25 <= d <= 30:
            sleepiness = rng.randint(2, 3)              # "I feel fine" while the data show fatigue
            mood = rng.choice([4, 4, 5])
            # Steadily increasing lapses (within the rules: 2-3 on +25..+27, 4-6 on +28..+30),
            # so the demo shows a clear trend getting worse over 6 days.
            lapses = {25: 2, 26: 2, 27: 3, 28: 4, 29: 5, 30: 6}[d]
        if aid == BP_ASTRONAUT and d in GEORGE_BP:
            bp_sys, bp_dia = GEORGE_BP[d]

        days.append({
            "day": d,
            "phase": "preflight" if d < 0 else "inflight",
            "sleep_h": s,
            "hr_bpm": hr,
            "spo2": spo2,
            "temp_c": temp,
            "bp_sys": bp_sys,
            "bp_dia": bp_dia,
            "exercise_min": exercise,
            "test": {"mean_rt_ms": mean_rt, "lapses": lapses, "false_starts": false_starts},
            "sleepiness": sleepiness,
            "mood": mood,
        })

    pre = [x for x in days if x["phase"] == "preflight"]
    baseline = {
        "mean_rt_ms": int(round(sum(x["test"]["mean_rt_ms"] for x in pre) / len(pre))),
        "lapses": int(round(sum(x["test"]["lapses"] for x in pre) / len(pre))),
    }
    return {"id": aid, "name": NAMES[aid], "role": role, "baseline": baseline, "days": days}


def build_crew():
    return {
        "mission": {
            "name": "Demo Mission",
            "current_day": 30,
            "next_critical_task": {"name": "EVA (spacewalk)", "day": 31, "time": "09:00"},
        },
        "guest_baseline": {"mean_rt_ms": None, "lapses": None},
        "astronauts": [build_astronaut(spec) for spec in CREW],
    }


# ---------------------------------------------------------------------------
# CHECK (color rules as defined -- they do NOT change)
# ---------------------------------------------------------------------------
def diff_pct(day, baseline):
    return (day["test"]["mean_rt_ms"] - baseline["mean_rt_ms"]) / baseline["mean_rt_ms"] * 100


def color(day, baseline):
    diff = diff_pct(day, baseline)
    lapses = day["test"]["lapses"]
    if diff > 20 or lapses >= 4:
        return "RED"
    if diff > 10 or lapses >= 2:
        return "YELLOW"
    return "GREEN"


EMOJI = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}


def bio_flags(day):
    """Returns dict: hr/spo2/temp -> bool (OK), bp -> 'ok' | 'mild' | 'severe'."""
    sys_, dia = day["bp_sys"], day["bp_dia"]
    if sys_ >= 140 or dia >= 90:
        bp = "severe"
    elif sys_ >= 120 or dia >= 80:
        bp = "mild"
    else:
        bp = "ok"
    return {
        "hr": 55 <= day["hr_bpm"] <= 100,
        "spo2": day["spo2"] >= 95,
        "temp": 36.1 <= day["temp_c"] <= 37.2,
        "bp": bp,
    }


def bio_ok(flags):
    return flags["hr"] and flags["spo2"] and flags["temp"] and flags["bp"] == "ok"


def mark(ok):
    return "✓" if ok else "⚠️"


def run_check(crew):
    failures = []

    def expect(label, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {label}")
        if not cond:
            failures.append(label)

    ast = {a["id"]: a for a in crew["astronauts"]}
    colors = {a["id"]: {d["day"]: color(d, a["baseline"]) for d in a["days"] if d["phase"] == "inflight"}
              for a in crew["astronauts"]}
    by_day = {a["id"]: {d["day"]: d for d in a["days"]} for a in crew["astronauts"]}

    print("\n=== CHECK: status on the last day (day +30) ===")
    header = (f"{'#':>2} {'Role':<19} {'base':>4}/{'L':<1} {'RT':>4} {'diff%':>6} {'lap':>3} "
              f"{'color':<6} {'sleep':>5} {'slpy':>4} {'mood':>5}  HR SpO2 Temp BP")
    print(header)
    print("-" * len(header))
    available = []
    for a in crew["astronauts"]:
        d = by_day[a["id"]][30]
        c = colors[a["id"]][30]
        f = bio_flags(d)
        bp_txt = {"ok": "✓", "mild": "⚠️ elevated", "severe": "⚠️ HIGH"}[f["bp"]]
        print(f"{a['id']:>2} {a['role']:<19} {a['baseline']['mean_rt_ms']:>4}/{a['baseline']['lapses']:<1} "
              f"{d['test']['mean_rt_ms']:>4} {diff_pct(d, a['baseline']):>+6.1f} {d['test']['lapses']:>3} "
              f"{EMOJI[c]:<6} {d['sleep_h']:>5.1f} {d['sleepiness']:>4} {d['mood']:>5}   "
              f"{mark(f['hr'])}   {mark(f['spo2'])}    {mark(f['temp'])}   {d['bp_sys']}/{d['bp_dia']} {bp_txt}")
        if c == "GREEN" and bio_ok(f):
            available.append(a["id"])

    print("\nPeriklis -- colors on days +22..+30:")
    print("  " + "  ".join(f"{d:+d}:{EMOJI[colors[4][d]]}" for d in range(22, 31)))
    d4 = [by_day[4][d] for d in range(25, 31)]
    print("  sleep:      " + " ".join(f"{x['sleep_h']:.1f}" for x in d4))
    print("  lapses:     " + " ".join(str(x["test"]["lapses"]) for x in d4))
    print("  sleepiness: " + " ".join(str(x["sleepiness"]) for x in d4))
    print("  diff%:      " + " ".join(f"{diff_pct(x, ast[4]['baseline']):+.1f}" for x in d4))

    print("\nGeorge -- blood pressure on days +27..+30 and test color:")
    for d in range(27, 31):
        x = by_day[BP_ASTRONAUT][d]
        print(f"  {d:+d}: {x['bp_sys']}/{x['bp_dia']}  test {EMOJI[colors[BP_ASTRONAUT][d]]}")

    scattered = {i: [d for d, c in colors[i].items() if c != "GREEN"] for i in ast if i not in (4,)}
    scattered = {i: v for i, v in scattered.items() if v}
    print(f"\nScattered non-GREEN days (except Periklis): {scattered}")
    print(f"Available for EVA (GREEN and all biometrics OK): {available}  (total {len(available)})")

    print("\n=== SCENARIO CHECKS ===")
    expect("Periklis: days +25..+27 = YELLOW",
           all(colors[4][d] == "YELLOW" for d in (25, 26, 27)))
    expect("Periklis: days +28..+30 = RED (so also +30)",
           all(colors[4][d] == "RED" for d in (28, 29, 30)))
    expect("Periklis: sleep 5.0-5.5 h on days +25..+30",
           all(5.0 <= by_day[4][d]["sleep_h"] <= 5.5 for d in range(25, 31)))
    expect("Periklis: sleepiness 2-3 on days +25..+30 (mismatch)",
           all(2 <= by_day[4][d]["sleepiness"] <= 3 for d in range(25, 31)))
    expect("Periklis: non-decreasing lapses on days +25..+30 (worsening trend)",
           all(by_day[4][d]["test"]["lapses"] <= by_day[4][d + 1]["test"]["lapses"] for d in range(25, 30)))
    expect("Periklis: GREEN on all days before +25",
           all(colors[4][d] == "GREEN" for d in range(0, 25)))
    expect("George: blood pressure 142/92..145/94 on days +28..+30 (high)",
           all(142 <= by_day[BP_ASTRONAUT][d]["bp_sys"] <= 145 and 92 <= by_day[BP_ASTRONAUT][d]["bp_dia"] <= 94
               and bio_flags(by_day[BP_ASTRONAUT][d])["bp"] == "severe" for d in (28, 29, 30)))
    expect("George: test GREEN on days +28..+30",
           all(colors[BP_ASTRONAUT][d] == "GREEN" for d in (28, 29, 30)))
    expect("George: normal blood pressure before +28",
           all(bio_flags(by_day[BP_ASTRONAUT][d])["bp"] == "ok" for d in range(0, 28)))
    others = [i for i in ast if i != 4]
    expect("Everyone else: GREEN on day +30",
           all(colors[i][30] == "GREEN" for i in others))
    expect("Scattered YELLOW: 1-2 astronauts (except Periklis), 1-2 days each, never RED",
           1 <= len(scattered) <= 2
           and all(1 <= len(v) <= 2 for v in scattered.values())
           and all(colors[i][d] == "YELLOW" for i, v in scattered.items() for d in v))
    expect("At least 3 astronauts GREEN and available for EVA on day +31", len(available) >= 3)
    expect("Only George has a biometric flag on day +30",
           [a["id"] for a in crew["astronauts"] if not bio_ok(bio_flags(by_day[a["id"]][30]))] == [BP_ASTRONAUT])
    expect("131 records per astronaut (days -100..+30, one per day)",
           all([d["day"] for d in a["days"]] == list(range(-100, 31)) for a in crew["astronauts"]))
    expect("Crew: Evgenios, Sarantis, Vasilis, Periklis, George (in this order)",
           [a["name"] for a in crew["astronauts"]] == ["Evgenios", "Sarantis", "Vasilis", "Periklis", "George"])
    return failures


def load_existing_guest_baseline(path):
    """If crew.json already exists and guest_baseline has been filled in (by
    set_guest_baseline.py), return it so it is not lost on a new run.
    Otherwise None (missing/broken file or guest_baseline = null)."""
    try:
        with open(path, encoding="utf-8") as fh:
            gb = json.load(fh).get("guest_baseline")
    except (OSError, ValueError, AttributeError):
        return None

    def is_num(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    if isinstance(gb, dict) and is_num(gb.get("mean_rt_ms")) and is_num(gb.get("lapses")):
        return {"mean_rt_ms": gb["mean_rt_ms"], "lapses": gb["lapses"]}
    return None


def main():
    crew = build_crew()
    kept = load_existing_guest_baseline(OUT)      # BEFORE overwriting the file
    if kept is not None:
        crew["guest_baseline"] = kept
        print(f"Kept guest_baseline from the existing crew.json: {kept}")
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(crew, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Written: {OUT}")
    failures = run_check(crew)
    print("\nRESULT:", "ALL SCENARIOS PASS ✓" if not failures else f"FAILED ({len(failures)})")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
