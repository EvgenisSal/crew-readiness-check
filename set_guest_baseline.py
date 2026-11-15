#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
set_guest_baseline.py -- Writes the team's reference baseline (guest_baseline) into crew.json.

Standard library only. Changes ONLY the "guest_baseline" key. Everything else
stays the same (the script verifies this after writing) and a backup crew.json.bak is kept.

Each test is given as a pair  mean_rt_ms,lapses :

  python3 set_guest_baseline.py 251,0 247,1 263,0 255,0 249,0 258,1 244,0 252,0 260,0 248,1
  python3 set_guest_baseline.py --csv results.csv     # one line per test:  251,0  or  Maria,251,0
  python3 set_guest_baseline.py --dry-run 251,0 247,1 # compute only, write nothing
  python3 set_guest_baseline.py --show                # show the current value
  python3 set_guest_baseline.py --reset               # back to null

Rounding: same as the astronaut baselines (Python round(), integers).
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
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_pair(text):
    """'251,0' or '251:0' -> (251.0, 0)."""
    parts = text.replace(":", ",").replace(";", ",").split(",")
    if len(parts) != 2:
        fail(f"'{text}' is not in the form  mean_rt_ms,lapses  (e.g. 251,0)")
    try:
        rt = float(parts[0])
        lapses_f = float(parts[1])
    except ValueError:
        fail(f"'{text}' does not contain numbers")
    if not 100 <= rt <= 1000:
        fail(f"the time {rt} ms in '{text}' is outside the plausible range 100-1000 ms (seconds by mistake?)")
    if lapses_f != int(lapses_f) or not 0 <= lapses_f <= 200:
        fail(f"the lapses in '{text}' must be an integer 0-200")
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
                if len(cols) == 3:                 # name,ms,lapses
                    cols = cols[1:]
                elif len(cols) != 2:
                    fail(f"{path}: line '{line}' must have 2 columns (ms,lapses) or 3 (name,ms,lapses)")
                if not cols[0].replace(".", "", 1).isdigit():    # header such as mean_rt_ms,lapses
                    continue
                pairs.append(parse_pair(",".join(cols)))
    except OSError as exc:
        fail(f"cannot read {path}: {exc}")
    return pairs


def load_crew(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        fail(f"{path} not found. Run generate_crew.py first or pass --crew <path>")
    except ValueError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if not isinstance(data, dict) or "guest_baseline" not in data:
        fail(f"{path} has no guest_baseline key (wrong file?)")
    return data


def write_json_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def band_limits(base_rt):
    """Maximum ms for GREEN (diff <= 10%) and YELLOW (diff <= 20%), using the team's rules."""
    green = math.floor(base_rt * 1.10 + 1e-9)
    yellow = math.floor(base_rt * 1.20 + 1e-9)
    return green, yellow


def main():
    ap = argparse.ArgumentParser(description="Sets guest_baseline in crew.json")
    ap.add_argument("tests", nargs="*", help="pairs  mean_rt_ms,lapses  (one per test)")
    ap.add_argument("--csv", help="file with one line per test")
    ap.add_argument("--crew", default=DEFAULT_CREW, help="path to crew.json (default: next to this script)")
    ap.add_argument("--dry-run", action="store_true", help="compute only, do not write")
    ap.add_argument("--show", action="store_true", help="show the current guest_baseline and exit")
    ap.add_argument("--reset", action="store_true", help="set guest_baseline back to null")
    args = ap.parse_args()

    data = load_crew(args.crew)

    if args.show:
        print("Current guest_baseline:", json.dumps(data["guest_baseline"], ensure_ascii=False))
        return

    if args.reset:
        new_gb = {"mean_rt_ms": None, "lapses": None}
        print("Resetting guest_baseline to null.")
    else:
        pairs = [parse_pair(t) for t in args.tests]
        if args.csv:
            pairs += read_csv(args.csv)
        if not pairs:
            ap.error("give tests (e.g. 251,0 247,1 ...) or a --csv file or --show / --reset")

        rts = [p[0] for p in pairs]
        laps = [p[1] for p in pairs]
        mean_rt = statistics.mean(rts)
        mean_laps = statistics.mean(laps)
        new_gb = {"mean_rt_ms": int(round(mean_rt)), "lapses": int(round(mean_laps))}

        print(f"Tests counted: {len(pairs)}")
        for i, (rt, lp) in enumerate(pairs, 1):
            print(f"  {i:>2}. {rt:g} ms, {lp} lapses")
        print(f"Mean time: {mean_rt:.1f} ms -> {new_gb['mean_rt_ms']}   "
              f"Mean lapses: {mean_laps:.2f} -> {new_gb['lapses']}")
        if len(pairs) < 6:
            print("WARNING: few tests (suggested: 10 = 5 people x 2). The baseline will be noisy.")
        med = statistics.median(rts)
        outliers = [rt for rt in rts if abs(rt - med) / med > 0.25]
        if outliers:
            print(f"WARNING: values far from the median ({med:g} ms): {outliers}. "
                  f"Re-measure or remove them before writing.")
        g, y = band_limits(new_gb["mean_rt_ms"])
        print(f"Color limits for a judge with this baseline: "
              f"GREEN <= {g} ms and <= 1 lapse; YELLOW <= {y} ms or 2-3 lapses; RED > {y} ms or >= 4 lapses")

    print("Old guest_baseline:", json.dumps(data["guest_baseline"], ensure_ascii=False))
    print("New guest_baseline:", json.dumps(new_gb, ensure_ascii=False))

    if args.dry_run:
        print("--dry-run: nothing was written.")
        return

    original = json.loads(json.dumps(data))          # deep copy for verification
    shutil.copy2(args.crew, args.crew + ".bak")
    data["guest_baseline"] = new_gb
    write_json_atomic(args.crew, data)

    # Verify: everything except guest_baseline is unchanged
    check = load_crew(args.crew)
    a = {k: v for k, v in original.items() if k != "guest_baseline"}
    b = {k: v for k, v in check.items() if k != "guest_baseline"}
    if a != b or check["guest_baseline"] != new_gb:
        shutil.copy2(args.crew + ".bak", args.crew)
        fail("verification failed, original crew.json restored from .bak")
    print(f"Written to {args.crew} (backup: {args.crew}.bak). Nothing else changed.")


if __name__ == "__main__":
    main()
