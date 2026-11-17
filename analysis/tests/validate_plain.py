#!/usr/bin/env python3
"""Format check of a kinetic-constant list (JSON). It never judges a value: no ranges, no ratio check, no lookup.

  python3 check_rows.py FILE      prints 'OK <n> rows', or one line per problem (exit 1)

Checks: the file is a JSON object with pmid, model, note and a rows list; each row's metric is kcat, Km or kcat/Km
and its value a finite number above 0; unit is exactly s^-1, mM or mM^-1 s^-1, the one for that metric; raw_value,
enzyme, variant and substrate are non-empty strings; pH and temperature_C are numbers or null."""
import json, math, sys

UNIT = {'kcat': 's^-1', 'Km': 'mM', 'kcat/Km': 'mM^-1 s^-1'}
TEXT = ('raw_value', 'enzyme', 'variant', 'substrate')


def number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def problems(d):
    out = []
    if not isinstance(d, dict):
        return ['the file is not a JSON object']
    for k in ('pmid', 'model', 'note'):
        if k not in d:
            out.append(f'missing key "{k}"')
        elif not isinstance(d[k], str):
            out.append(f'"{k}" must be a string')
    rows = d.get('rows')
    if not isinstance(rows, list):
        return out + ['"rows" must be a list']
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            out.append(f'row {i}: not an object')
            continue
        m = r.get('metric')
        if m not in UNIT:
            out.append(f'row {i}: metric must be kcat, Km or kcat/Km (got {m!r})')
        v = r.get('value')
        if not number(v) or not math.isfinite(v) or v <= 0:
            out.append(f'row {i}: value must be a finite number above 0 (got {v!r})')
        if m in UNIT and r.get('unit') != UNIT[m]:
            out.append(f'row {i}: unit for {m} must be exactly "{UNIT[m]}" (got {r.get("unit")!r})')
        elif m not in UNIT and r.get('unit') not in UNIT.values():
            out.append(f'row {i}: unit must be s^-1, mM or mM^-1 s^-1 (got {r.get("unit")!r})')
        for k in TEXT:
            if not isinstance(r.get(k), str) or not r.get(k).strip():
                out.append(f'row {i}: {k} must be a non-empty string')
        for k in ('pH', 'temperature_C'):
            x = r.get(k)
            if x is not None and not (number(x) and math.isfinite(x)):
                out.append(f'row {i}: {k} must be a number or null (got {x!r})')
    return out


def check_file(path):
    """(ok, rows, problems) for one file."""
    try:
        with open(path) as fh:
            d = json.load(fh)
    except FileNotFoundError:
        return False, 0, [f'{path}: no such file']
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return False, 0, [f'not valid JSON: {e}']
    p = problems(d)
    n = len(d.get('rows') or []) if isinstance(d, dict) and isinstance(d.get('rows'), list) else 0
    return not p, n, p


def main(argv):
    if len(argv) != 2:
        print('usage: python3 check_rows.py FILE')
        return 2
    ok, n, p = check_file(argv[1])
    if ok:
        print(f'OK {n} rows')
        return 0
    for line in p:
        print(line)
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
