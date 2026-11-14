#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
set_guest_baseline.py -- Γράφει τη βάση αναφοράς της ομάδας (guest_baseline) στο crew.json.

Μόνο standard library. Αλλάζει ΜΟΝΟ το κλειδί "guest_baseline". Όλα τα υπόλοιπα
μένουν ίδια (το script το επαληθεύει μετά το γράψιμο) και κρατά αντίγραφο crew.json.bak.

Κάθε τεστ δίνεται ως ζεύγος  μέσος_χρόνος_ms,αστοχίες  (lapses):

  python3 set_guest_baseline.py 251,0 247,1 263,0 255,0 249,0 258,1 244,0 252,0 260,0 248,1
  python3 set_guest_baseline.py --csv results.csv     # μία γραμμή ανά τεστ:  251,0  ή  Μαρία,251,0
  python3 set_guest_baseline.py --dry-run 251,0 247,1 # μόνο υπολογισμός, δεν γράφει τίποτα
  python3 set_guest_baseline.py --show                # δείχνει τι υπάρχει τώρα
  python3 set_guest_baseline.py --reset               # ξανά null

Στρογγυλοποίηση: όπως στα baselines των αστροναυτών (round() της Python, ακέραιοι).
"""
import argparse
import json
import math
import os
import shutil
import statistics
import sys

DEFAULT_CREW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crew.json")


def fail(msg):
    print(f"ΣΦΑΛΜΑ: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_pair(text):
    """'251,0' ή '251:0' -> (251.0, 0)."""
    parts = text.replace(":", ",").replace(";", ",").split(",")
    if len(parts) != 2:
        fail(f"το «{text}» δεν είναι της μορφής  μέσος_χρόνος_ms,αστοχίες  (π.χ. 251,0)")
    try:
        rt = float(parts[0])
        lapses_f = float(parts[1])
    except ValueError:
        fail(f"το «{text}» δεν περιέχει αριθμούς")
    if not 100 <= rt <= 1000:
        fail(f"ο χρόνος {rt} ms στο «{text}» είναι εκτός λογικού εύρους 100-1000 ms (μήπως δευτερόλεπτα;)")
    if lapses_f != int(lapses_f) or not 0 <= lapses_f <= 200:
        fail(f"οι αστοχίες στο «{text}» πρέπει να είναι ακέραιος 0-200")
    return rt, int(lapses_f)


def read_csv(path):
    pairs = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                cols = [c.strip() for c in line.replace(";", ",").split(",")]
                if len(cols) == 3:                 # όνομα,ms,lapses
                    cols = cols[1:]
                elif len(cols) != 2:
                    fail(f"{path}: η γραμμή «{line}» πρέπει να έχει 2 στήλες (ms,αστοχίες) ή 3 (όνομα,ms,αστοχίες)")
                if not cols[0].replace(".", "", 1).isdigit():    # επικεφαλίδα τύπου mean_rt_ms,lapses
                    continue
                pairs.append(parse_pair(",".join(cols)))
    except OSError as exc:
        fail(f"δεν διαβάζεται το {path}: {exc}")
    return pairs


def load_crew(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        fail(f"δεν βρέθηκε το {path}. Τρέξε πρώτα generate_crew.py ή δώσε --crew διαδρομή")
    except ValueError as exc:
        fail(f"το {path} δεν είναι έγκυρο JSON: {exc}")
    if not isinstance(data, dict) or "guest_baseline" not in data:
        fail(f"το {path} δεν έχει κλειδί guest_baseline (λάθος αρχείο;)")
    return data


def write_json_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def band_limits(base_rt):
    """Μέγιστοι ms για 🟢 (diff <= 10%) και 🟡 (diff <= 20%), με τους κανόνες της ομάδας."""
    green = math.floor(base_rt * 1.10 + 1e-9)
    yellow = math.floor(base_rt * 1.20 + 1e-9)
    return green, yellow


def main():
    ap = argparse.ArgumentParser(description="Ορίζει το guest_baseline στο crew.json")
    ap.add_argument("tests", nargs="*", help="ζεύγη  μέσος_χρόνος_ms,αστοχίες  (ένα ανά τεστ)")
    ap.add_argument("--csv", help="αρχείο με μία γραμμή ανά τεστ")
    ap.add_argument("--crew", default=DEFAULT_CREW, help="διαδρομή crew.json (προεπιλογή: δίπλα στο script)")
    ap.add_argument("--dry-run", action="store_true", help="μόνο υπολογισμός, χωρίς γράψιμο")
    ap.add_argument("--show", action="store_true", help="δείχνει το τρέχον guest_baseline και βγαίνει")
    ap.add_argument("--reset", action="store_true", help="ξαναβάζει guest_baseline = null")
    args = ap.parse_args()

    data = load_crew(args.crew)

    if args.show:
        print("Τρέχον guest_baseline:", json.dumps(data["guest_baseline"], ensure_ascii=False))
        return

    if args.reset:
        new_gb = {"mean_rt_ms": None, "lapses": None}
        print("Επαναφορά guest_baseline σε null.")
    else:
        pairs = [parse_pair(t) for t in args.tests]
        if args.csv:
            pairs += read_csv(args.csv)
        if not pairs:
            ap.error("δώσε τεστ (π.χ. 251,0 247,1 ...) ή --csv αρχείο ή --show / --reset")

        rts = [p[0] for p in pairs]
        laps = [p[1] for p in pairs]
        mean_rt = statistics.mean(rts)
        mean_laps = statistics.mean(laps)
        new_gb = {"mean_rt_ms": int(round(mean_rt)), "lapses": int(round(mean_laps))}

        print(f"Τεστ που μετρήθηκαν: {len(pairs)}")
        for i, (rt, lp) in enumerate(pairs, 1):
            print(f"  {i:>2}. {rt:g} ms, {lp} αστοχίες")
        print(f"Μέσος χρόνος: {mean_rt:.1f} ms -> {new_gb['mean_rt_ms']}   "
              f"Μέσες αστοχίες: {mean_laps:.2f} -> {new_gb['lapses']}")
        if len(pairs) < 6:
            print("ΠΡΟΣΟΧΗ: λίγα τεστ (πρόταση: 10 = 5 άτομα x 2). Η βάση θα είναι θορυβώδης.")
        med = statistics.median(rts)
        outliers = [rt for rt in rts if abs(rt - med) / med > 0.25]
        if outliers:
            print(f"ΠΡΟΣΟΧΗ: τιμές πολύ μακριά από τη διάμεσο ({med:g} ms): {outliers}. "
                  f"Ξαναμέτρησέ τες ή βγάλ' τες πριν γράψεις.")
        g, y = band_limits(new_gb["mean_rt_ms"])
        print(f"Όρια χρώματος για τον κριτή με αυτή τη βάση: "
              f"🟢 ≤ {g} ms και ≤ 1 αστοχία · 🟡 ≤ {y} ms ή 2-3 αστοχίες · 🔴 > {y} ms ή ≥ 4 αστοχίες")

    print("Παλιό guest_baseline:", json.dumps(data["guest_baseline"], ensure_ascii=False))
    print("Νέο  guest_baseline:", json.dumps(new_gb, ensure_ascii=False))

    if args.dry_run:
        print("--dry-run: δεν γράφτηκε τίποτα.")
        return

    original = json.loads(json.dumps(data))          # βαθύ αντίγραφο για την επαλήθευση
    shutil.copy2(args.crew, args.crew + ".bak")
    data["guest_baseline"] = new_gb
    write_json_atomic(args.crew, data)

    # Επαλήθευση: ό,τι άλλο εκτός από το guest_baseline μένει ίδιο
    check = load_crew(args.crew)
    a = {k: v for k, v in original.items() if k != "guest_baseline"}
    b = {k: v for k, v in check.items() if k != "guest_baseline"}
    if a != b or check["guest_baseline"] != new_gb:
        shutil.copy2(args.crew + ".bak", args.crew)
        fail("η επαλήθευση απέτυχε, επανήλθε το αρχικό crew.json από το .bak")
    print(f"Γράφτηκε στο {args.crew} (αντίγραφο ασφαλείας: {args.crew}.bak). Τίποτα άλλο δεν άλλαξε.")


if __name__ == "__main__":
    main()
