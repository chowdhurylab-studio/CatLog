#!/usr/bin/env python3
"""Stream the BRENDA 2026.1 JSON (inside tar.gz) one EC entry at a time and count
kinetic entries and cited PMIDs. Read-only; low memory (one EC entry in memory)."""
import io
import json
import re
import sys
import tarfile
from collections import Counter, defaultdict

from pathlib import Path  # noqa: E402
ARCHIVE = str(Path(__file__).resolve().parent.parent / "sources" / "brenda_2026_1.json.tar.gz")  # this repository's sources/
OUT = sys.argv[1]  # output dir

FIELDS = {"turnover_number": "TN", "km_value": "KM", "kcat_km_value": "TNKM", "ki_value": "KI"}
start_re = re.compile(r'^    "(.*)": \{\s*$')
end_re = re.compile(r'^    \},?\s*$')
num_re = re.compile(r'^\s*-?\d+(\.\d+)?([eE][-+]?\d+)?\s*$')

stats = {f: Counter() for f in FIELDS.values()}
pmid_field = defaultdict(Counter)        # pmid -> Counter(field)
pmid_sole = Counter()                    # pmid -> entries (TN/KM/TNKM) where it is the only cited ref
pmid_ecs = defaultdict(set)
ref_no_pmid_entries = Counter()
ident_all = set()
ident_kcat = set()
ec_count = 0
sample_printed = False


def valid_pmid(p):
    s = str(p or "").strip()
    return s if (s.isdigit() and s.strip("0")) else None


def handle(ec, entry):
    global sample_printed
    refs = entry.get("reference") if isinstance(entry.get("reference"), dict) else {}
    for field, tag in FIELDS.items():
        items = entry.get(field)
        if not isinstance(items, list):
            continue
        st = stats[tag]
        for it in items:
            if not isinstance(it, dict):
                continue
            if not sample_printed and tag == "TN":
                print("SAMPLE_ITEM", json.dumps(it)[:600])
                r0 = (it.get("references") or [None])[0]
                print("SAMPLE_REF", json.dumps(refs.get(str(r0)))[:600])
                sample_printed = True
            st["entries"] += 1
            v = str(it.get("value") or "")
            nv = it.get("num_value")
            if nv is not None:
                try:
                    if float(nv) == -999:
                        st["sentinel_-999"] += 1
                except (TypeError, ValueError):
                    pass
            if "-999" in v:
                st["value_has_-999"] += 1
            elif num_re.match(v.split("{")[0]):
                st["numeric_point"] += 1
            else:
                st["nonpoint_or_range"] += 1
            rids = [str(r) for r in (it.get("references") or [])]
            st["refs_%s" % ("0" if not rids else "1" if len(rids) == 1 else "2+")] += 1
            pm = []
            for r in rids:
                ref = refs.get(r) or {}
                p = valid_pmid(ref.get("pmid"))
                if p:
                    pm.append(p)
            pm = sorted(set(pm))
            if pm:
                st["with_pmid"] += 1
            else:
                st["no_pmid"] += 1
            if tag == "KI" or "-999" in v:
                continue
            sub = v.split("{", 1)[1].rsplit("}", 1)[0].strip().lower() if "{" in v else ""
            key = hash((ec, tuple(sorted(str(x) for x in (it.get("proteins") or []))), sub,
                        " ".join(str(it.get("comment") or "").lower().split())))
            ident_all.add(key)
            if tag in ("TN", "TNKM"):
                ident_kcat.add(key)
            for p in pm:
                pmid_field[p][tag] += 1
                pmid_ecs[p].add(ec)
            if len(pm) == 1 and len(rids) == 1:
                pmid_sole[pm[0]] += 1


def main():
    global ec_count
    with tarfile.open(ARCHIVE, "r|gz") as tf:
        member = None
        for m in tf:
            if m.isfile() and m.name.endswith(".json"):
                member = m
                break
        fh = (raw.decode("utf-8") for raw in tf.extractfile(member))
        in_data = False
        buf = None
        cur = None
        for line in fh:
            if not in_data:
                if line.startswith('  "data": {'):
                    in_data = True
                continue
            if buf is None:
                m = start_re.match(line)
                if m:
                    cur = m.group(1)
                    buf = ["{"]
                continue
            if end_re.match(line):
                buf.append("}")
                entry = json.loads("".join(buf))
                handle(cur, entry)
                ec_count += 1
                buf = None
                cur = None
                continue
            buf.append(line)
    tn_km = set(pmid_field)
    tn_any = {p for p, c in pmid_field.items() if c["TN"] or c["TNKM"]}
    summary = {
        "ec_entries_parsed": ec_count,
        "fields": {k: dict(v) for k, v in stats.items()},
        "distinct_pmids_TN_KM_TNKM": len(tn_km),
        "distinct_pmids_TN": sum(1 for c in pmid_field.values() if c["TN"]),
        "distinct_pmids_KM": sum(1 for c in pmid_field.values() if c["KM"]),
        "distinct_pmids_TNKM": sum(1 for c in pmid_field.values() if c["TNKM"]),
        "distinct_pmids_TN_or_TNKM": len(tn_any),
        "distinct_pmids_sole_ref": len(pmid_sole),
        "ec_pmid_pairs": sum(len(s) for s in pmid_ecs.values()),
        "est_identities_ec_protein_substrate_comment": len(ident_all),
        "est_identities_with_kcat": len(ident_kcat),
        "note": "PMID and identity counts exclude -999 sentinel items and Ki",
    }
    with open(f"{OUT}/brenda_summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    rows = sorted(pmid_field.items(), key=lambda kv: -sum(kv[1].values()))
    with open(f"{OUT}/brenda_pmids.tsv", "w") as f:
        f.write("pmid\tentries\tTN\tKM\tTNKM\tsole_ref_entries\tn_ecs\n")
        for p, c in rows:
            f.write(f"{p}\t{sum(c.values())}\t{c['TN']}\t{c['KM']}\t{c['TNKM']}\t{pmid_sole[p]}\t{len(pmid_ecs[p])}\n")
    print(json.dumps(summary, indent=1))


main()
