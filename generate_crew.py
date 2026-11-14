#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_crew.py -- Προσομοιωμένα δεδομένα πληρώματος για το demo "Crew Readiness Check".

* Μόνο standard library, σταθερό random seed -> ίδιο crew.json σε κάθε εκτέλεση.
* ΟΛΑ ΤΑ ΔΕΔΟΜΕΝΑ ΕΙΝΑΙ ΠΡΟΣΟΜΟΙΩΜΕΝΑ (δεν προέρχονται από πραγματικούς αστροναύτες).
* Γράφει το crew.json δίπλα στο script και στο τέλος τρέχει έλεγχο σεναρίων.
"""
import json
import os
import random
import sys

SEED = 2026
FIRST_DAY, LAST_DAY = -100, 30
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crew.json")

# ---------------------------------------------------------------------------
# ΠΡΟΣΟΧΗ -- ΑΠΛΟΠΟΙΗΣΗ ΓΙΑ ΤΟ DEMO, ΟΧΙ ΕΥΡΗΜΑ ΤΗΣ ΒΙΒΛΙΟΓΡΑΦΙΑΣ:
# Ο τύπος "+4% της βάσης για κάθε ώρα ύπνου που λείπει κάτω από 6" και το
# "+5% συσσωρευμένη κόπωση" είναι ΔΙΚΗ ΜΑΣ απλοποίηση για να βγαίνει καθαρό
# demo. Η βιβλιογραφία λέει μόνο ότι ύπνος <= 6 ωρών συνδέεται με πιο αργή
# αντίδραση (μελέτη 24 αστροναυτών στο ISS). Δεν υπάρχει τέτοιος γραμμικός τύπος.
# ---------------------------------------------------------------------------
SLEEP_PENALTY_PER_HOUR = 0.04   # ποσοστό της βάσης ανά ώρα που λείπει κάτω από 6
ACCUMULATED_FATIGUE = 0.05      # επιπλέον ποσοστό αν οι 3 προηγούμενες νύχτες ήταν < 6

# id, ρόλος, "πραγματική" βάση RT (ms), hr, spo2, temp, bp_sys, bp_dia (προσωπικές βάσεις)
CREW = [
    (1, "Commander",          236, 60, 98, 36.6, 112, 70),
    (2, "Pilot",              244, 64, 98, 36.7, 110, 69),
    (3, "Flight Engineer",    229, 62, 97, 36.5, 114, 72),
    (4, "Flight Engineer",    238, 66, 98, 36.6, 113, 71),
    (5, "Flight Engineer",    251, 61, 97, 36.8, 109, 68),
    (6, "Mission Specialist", 223, 68, 98, 36.6, 115, 73),
    (7, "Mission Specialist", 246, 63, 98, 36.7, 114, 72),
    (8, "Mission Specialist", 232, 67, 97, 36.5, 111, 70),
    (9, "Medical Officer",    258, 65, 98, 36.6, 110, 69),
    (10, "Science Officer",   241, 62, 98, 36.7, 112, 71),
]

# Σκόρπιες 🟡 μέρες για ρεαλισμό (id -> μέρες πτήσης). Σκόπιμα σεναριακές:
# νύχτα 5.6-5.9 ώρες + lapses = 2. Όλοι οι υπόλοιποι μένουν 🟢.
SCATTERED_YELLOW = {2: [9, 21], 9: [15]}

# Τυχαίες "σύντομες" νύχτες (5.6-5.9) μόνο μέχρι αυτή τη μέρα, ώστε το τέλος
# της πτήσης να είναι καθαρό. Ο αστροναύτης 4 σταματά νωρίτερα (η κόπωσή του
# ξεκινά ξαφνικά στη μέρα 25, όχι σταδιακά από το πουθενά).
LAST_RANDOM_SHORT_NIGHT = 23
LAST_RANDOM_SHORT_NIGHT_ASTRONAUT_4 = 20

# Σενάριο αστροναύτη 7: σοβαρά αυξημένη πίεση, ενώ το τεστ μένει 🟢
ASTRONAUT_7_BP = {28: (142, 92), 29: (144, 93), 30: (145, 94)}


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def pick_short_nights(rng, forced, last_day):
    """Τυχαίες σύντομες νύχτες με απόσταση >= 4 ημερών (ποτέ 3 συνεχόμενες)."""
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
    """Υπνηλία 1-9: ακολουθεί τον ύπνο."""
    if sleep_h >= 6.5:
        return rng.randint(2, 4)
    if sleep_h >= 6.0:
        return rng.randint(3, 5)
    if sleep_h > 5.5:
        return rng.randint(4, 6)
    return rng.randint(5, 7)


def build_astronaut(spec):
    aid, role, rt_base, hr_b, spo2_b, temp_b, sys_b, dia_b = spec
    # Ξεχωριστό rng ανά αστροναύτη: αλλαγή σε έναν δεν επηρεάζει τους άλλους.
    rng = random.Random(SEED * 1000 + aid)
    forced = SCATTERED_YELLOW.get(aid, [])
    last_short = LAST_RANDOM_SHORT_NIGHT_ASTRONAUT_4 if aid == 4 else LAST_RANDOM_SHORT_NIGHT
    short_nights = pick_short_nights(rng, forced, last_short)

    # 1η φάση: ύπνος για όλες τις μέρες (χρειάζεται για τις "3 προηγούμενες νύχτες")
    sleep = {}
    for d in range(FIRST_DAY, LAST_DAY + 1):
        if d < 0:
            s = clip(rng.gauss(7.5, 0.25), 7.0, 8.0)          # preflight 7.0-8.0
        elif aid == 4 and 25 <= d <= 30:
            s = rng.uniform(5.0, 5.5)                          # ΣΕΝΑΡΙΟ αστροναύτη 4
        elif d in short_nights:
            s = rng.uniform(5.6, 5.9)                          # περιστασιακή σύντομη νύχτα
        else:
            s = clip(rng.gauss(6.5, 0.25), 6.0, 7.0)          # inflight 6.0-7.0
        sleep[d] = round(s, 1)

    # 2η φάση: όλα τα υπόλοιπα
    days = []
    for d in range(FIRST_DAY, LAST_DAY + 1):
        s = sleep[d]
        accumulated = all((sleep.get(d - k) is not None and sleep[d - k] < 6.0) for k in (1, 2, 3))

        # Χρόνος αντίδρασης
        noise = rng.uniform(-0.03, 0.03)
        rt = rt_base * (1 + noise)
        if s < 6.0:
            rt += (6.0 - s) * SLEEP_PENALTY_PER_HOUR * rt_base
        if accumulated:
            rt += ACCUMULATED_FATIGUE * rt_base
        mean_rt = int(round(rt))

        # Lapses (>= 355 ms)
        if d in forced:
            lapses = 2                                  # σεναριακή σκόρπια 🟡
        elif accumulated and s < 6.0:
            lapses = rng.randint(4, 6)                  # συσσωρευμένη κόπωση
        elif s <= 5.5:
            lapses = rng.randint(2, 3)
        elif s < 6.0:
            lapses = rng.choice([0, 1])
        else:
            lapses = 1 if rng.random() < 0.15 else 0
        false_starts = rng.choices([0, 1, 2], weights=[50, 35, 15])[0]

        # Υπνηλία / διάθεση
        sleepiness = sleepiness_for(s, rng)
        mood = rng.choice([3, 4, 4, 4, 5, 5])
        if s < 6.0:
            mood = max(2, mood - 1)
        exercise = rng.randint(40, 90) if d < 0 else rng.randint(30, 90)

        # Biometrics. Κρατάμε sys <= 119 και dia <= 79 ώστε οι "φυσιολογικοί" να
        # είναι ✓ και με τις κατηγορίες πίεσης (>= 120 ή >= 80 = ήπιο ⚠️).
        hr = int(clip(round(hr_b + rng.uniform(-5, 5)), 55, 80))
        spo2 = int(clip(spo2_b + rng.choice([-1, 0, 0, 0, 1]), 96, 99))
        temp = round(clip(temp_b + rng.uniform(-0.15, 0.15), 36.4, 36.9), 1)
        bp_sys = int(clip(round(sys_b + rng.uniform(-4, 4)), 105, 119))
        bp_dia = int(clip(round(dia_b + rng.uniform(-3, 3)), 65, 79))

        # --- Σενάρια (overrides, μετά από όλες τις τυχαίες κλήσεις) ---
        if aid == 4 and 25 <= d <= 30:
            sleepiness = rng.randint(2, 3)              # "νιώθω καλά" ενώ τα δεδομένα δείχνουν κόπωση
            mood = rng.choice([4, 4, 5])
            # Σταθερά αυξανόμενα lapses (εντός των κανόνων: 2-3 στις +25..+27, 4-6 στις +28..+30),
            # ώστε το demo να δείχνει καθαρή τάση που χειροτερεύει 6 μέρες.
            lapses = {25: 2, 26: 2, 27: 3, 28: 4, 29: 5, 30: 6}[d]
        if aid == 7 and d in ASTRONAUT_7_BP:
            bp_sys, bp_dia = ASTRONAUT_7_BP[d]

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
    return {"id": aid, "name": f"Astronaut {aid}", "role": role, "baseline": baseline, "days": days}


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
# ΕΛΕΓΧΟΣ (κανόνες χρώματος όπως ορίστηκαν -- ΔΕΝ αλλάζουν)
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
    """Επιστρέφει dict: hr/spo2/temp -> bool (OK), bp -> 'ok' | 'mild' | 'severe'."""
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

    print("\n=== ΕΛΕΓΧΟΣ: κατάσταση τελευταίας μέρας (day +30) ===")
    header = (f"{'#':>2} {'Ρόλος':<19} {'base':>4}/{'L':<1} {'RT':>4} {'diff%':>6} {'lap':>3} "
              f"{'χρώμα':<6} {'ύπνος':>5} {'υπν.':>4} {'διάθ.':>5}  HR SpO2 Temp BP")
    print(header)
    print("-" * len(header))
    available = []
    for a in crew["astronauts"]:
        d = by_day[a["id"]][30]
        c = colors[a["id"]][30]
        f = bio_flags(d)
        bp_txt = {"ok": "✓", "mild": "⚠️ ήπια", "severe": "⚠️ ΣΟΒΑΡΗ"}[f["bp"]]
        print(f"{a['id']:>2} {a['role']:<19} {a['baseline']['mean_rt_ms']:>4}/{a['baseline']['lapses']:<1} "
              f"{d['test']['mean_rt_ms']:>4} {diff_pct(d, a['baseline']):>+6.1f} {d['test']['lapses']:>3} "
              f"{EMOJI[c]:<6} {d['sleep_h']:>5.1f} {d['sleepiness']:>4} {d['mood']:>5}   "
              f"{mark(f['hr'])}   {mark(f['spo2'])}    {mark(f['temp'])}   {d['bp_sys']}/{d['bp_dia']} {bp_txt}")
        if c == "GREEN" and bio_ok(f):
            available.append(a["id"])

    print("\nΑστροναύτης 4 -- χρώματα μέρες +22..+30:")
    print("  " + "  ".join(f"{d:+d}:{EMOJI[colors[4][d]]}" for d in range(22, 31)))
    d4 = [by_day[4][d] for d in range(25, 31)]
    print("  ύπνος:      " + " ".join(f"{x['sleep_h']:.1f}" for x in d4))
    print("  lapses:     " + " ".join(str(x["test"]["lapses"]) for x in d4))
    print("  υπνηλία:    " + " ".join(str(x["sleepiness"]) for x in d4))
    print("  diff%:      " + " ".join(f"{diff_pct(x, ast[4]['baseline']):+.1f}" for x in d4))

    print("\nΑστροναύτης 7 -- πίεση μέρες +27..+30 και χρώμα τεστ:")
    for d in range(27, 31):
        x = by_day[7][d]
        print(f"  {d:+d}: {x['bp_sys']}/{x['bp_dia']}  τεστ {EMOJI[colors[7][d]]}")

    scattered = {i: [d for d, c in colors[i].items() if c != "GREEN"] for i in ast if i not in (4,)}
    scattered = {i: v for i, v in scattered.items() if v}
    print(f"\nΣκόρπιες μη-🟢 μέρες (πλην αστροναύτη 4): {scattered}")
    print(f"Διαθέσιμοι για EVA (🟢 και όλα τα biometrics ✓): {available}  (σύνολο {len(available)})")

    print("\n=== ΕΠΙΒΕΒΑΙΩΣΗ ΣΕΝΑΡΙΩΝ ===")
    expect("Αστρ. 4: μέρες +25..+27 = 🟡",
           all(colors[4][d] == "YELLOW" for d in (25, 26, 27)))
    expect("Αστρ. 4: μέρες +28..+30 = 🔴 (άρα και η +30)",
           all(colors[4][d] == "RED" for d in (28, 29, 30)))
    expect("Αστρ. 4: ύπνος 5.0-5.5 τις μέρες +25..+30",
           all(5.0 <= by_day[4][d]["sleep_h"] <= 5.5 for d in range(25, 31)))
    expect("Αστρ. 4: υπνηλία 2-3 τις μέρες +25..+30 (ασυμφωνία)",
           all(2 <= by_day[4][d]["sleepiness"] <= 3 for d in range(25, 31)))
    expect("Αστρ. 4: lapses μη φθίνοντα τις μέρες +25..+30 (τάση που χειροτερεύει)",
           all(by_day[4][d]["test"]["lapses"] <= by_day[4][d + 1]["test"]["lapses"] for d in range(25, 30)))
    expect("Αστρ. 4: 🟢 σε όλες τις μέρες πριν την +25",
           all(colors[4][d] == "GREEN" for d in range(0, 25)))
    expect("Αστρ. 7: πίεση 142/92..145/94 τις μέρες +28..+30 (σοβαρό ⚠️)",
           all(142 <= by_day[7][d]["bp_sys"] <= 145 and 92 <= by_day[7][d]["bp_dia"] <= 94
               and bio_flags(by_day[7][d])["bp"] == "severe" for d in (28, 29, 30)))
    expect("Αστρ. 7: τεστ 🟢 τις μέρες +28..+30",
           all(colors[7][d] == "GREEN" for d in (28, 29, 30)))
    expect("Αστρ. 7: πίεση φυσιολογική (✓) πριν την +28",
           all(bio_flags(by_day[7][d])["bp"] == "ok" for d in range(0, 28)))
    others = [i for i in ast if i != 4]
    expect("Όλοι οι άλλοι: 🟢 τη μέρα +30",
           all(colors[i][30] == "GREEN" for i in others))
    expect("Σκόρπιες 🟡: 1-2 αστροναύτες (εκτός 4), 1-2 μέρες ο καθένας, ποτέ 🔴",
           1 <= len(scattered) <= 2
           and all(1 <= len(v) <= 2 for v in scattered.values())
           and all(colors[i][d] == "YELLOW" for i, v in scattered.items() for d in v))
    expect("Τουλάχιστον 3 αστροναύτες 🟢 και διαθέσιμοι για EVA τη μέρα +31", len(available) >= 3)
    expect("Μόνο ο αστρ. 7 έχει ⚠️ στα biometrics τη μέρα +30",
           [a["id"] for a in crew["astronauts"] if not bio_ok(bio_flags(by_day[a["id"]][30]))] == [7])
    expect("131 εγγραφές ανά αστροναύτη (μέρες -100..+30, μία ανά μέρα)",
           all([d["day"] for d in a["days"]] == list(range(-100, 31)) for a in crew["astronauts"]))
    roles = sorted(a["role"] for a in crew["astronauts"])
    expect("Ρόλοι: 1 Commander, 1 Pilot, 3 Flight Engineer, 3 Mission Specialist, 1 Medical Officer, 1 Science Officer",
           roles == sorted(["Commander", "Pilot"] + ["Flight Engineer"] * 3 + ["Mission Specialist"] * 3
                           + ["Medical Officer", "Science Officer"]))
    return failures


def load_existing_guest_baseline(path):
    """Αν το crew.json υπάρχει ήδη και το guest_baseline έχει συμπληρωθεί (από το
    set_guest_baseline.py), το επιστρέφει ώστε να μην χαθεί σε νέα εκτέλεση.
    Αλλιώς None (ανύπαρκτο/χαλασμένο αρχείο ή guest_baseline = null)."""
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
    kept = load_existing_guest_baseline(OUT)      # ΠΡΙΝ το overwrite του αρχείου
    if kept is not None:
        crew["guest_baseline"] = kept
        print(f"Διατηρήθηκε το guest_baseline από το υπάρχον crew.json: {kept}")
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(crew, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Γράφτηκε: {OUT}")
    failures = run_check(crew)
    print("\nΑΠΟΤΕΛΕΣΜΑ:", "ΟΛΑ ΤΑ ΣΕΝΑΡΙΑ ΒΓΑΙΝΟΥΝ ✓" if not failures else f"ΑΠΟΤΥΧΙΑ ({len(failures)})")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
