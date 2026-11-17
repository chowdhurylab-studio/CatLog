#!/usr/bin/env python3
"""Compare BRENDA kcat/Km/kcat-over-Km cited PMIDs with CatLog v2 papers.tsv / library.tsv. Read-only."""
import csv
import json
import sys

from pathlib import Path  # noqa: E402
V2 = str(Path(__file__).resolve().parent.parent)  # this repository
S = f"{V2}/sources"  # reads brenda_pmids.tsv, writes db_citations*.txt


def col(path, name):
    with open(path, newline="", encoding="utf-8") as f:
        return {r[name].strip() for r in csv.DictReader(f, delimiter="\t") if r.get(name)}


def lines(path):
    with open(path, encoding="utf-8") as f:
        return {ln.split()[0].strip() for ln in f if ln.strip() and ln.split()[0].strip().isdigit()}


brenda = {}
with open(f"{S}/brenda_pmids.tsv", encoding="utf-8") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        brenda[r["pmid"]] = r

lib = col(f"{V2}/library.tsv", "pmid")
papers = col(f"{V2}/papers.tsv", "pmid")
never = lines(f"{V2}/sources/fulltext_never_read.txt")
before = lines(f"{V2}/sources/fulltext_read_before.txt")
lib_kind = {}
with open(f"{V2}/library.tsv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        lib_kind.setdefault(r["pmid"], r["kind"])

B = set(brenda)
ent = lambda s: sum(int(brenda[p]["entries"]) for p in s)
kc = lambda s: sum(1 for p in s if int(brenda[p]["TN"]) + int(brenda[p]["TNKM"]) > 0)
out = {}
for name, s in [("brenda_all", B), ("in_library", B & lib), ("in_papers_tsv", B & papers),
                ("in_never_read_list", B & never), ("in_read_before_list", B & before),
                ("in_library_or_papers", B & (lib | papers)),
                ("not_in_v2", B - lib - papers)]:
    out[name] = {"pmids": len(s), "entries": ent(s), "pmids_with_kcat": kc(s)}
out["v2_sizes"] = {"library_pmids": len(lib), "papers_tsv_pmids": len(papers),
                   "never_read_list": len(never), "read_before_list": len(before),
                   "library_not_brenda": len(lib - B)}
kinds = {}
for p in B & lib:
    kinds[lib_kind[p]] = kinds.get(lib_kind[p], 0) + 1
out["brenda_in_library_by_kind"] = kinds
rest = sorted(B - lib - papers, key=lambda p: (-int(brenda[p]["entries"]), int(p)))
with open(f"{S}/db_citations.txt", "w") as f:
    for p in rest:
        f.write(p + "\n")
with open(f"{S}/db_citations_counts.tsv", "w") as f:
    f.write("pmid\tentries\tTN\tKM\tTNKM\n")
    for p in rest:
        r = brenda[p]
        f.write(f"{p}\t{r['entries']}\t{r['TN']}\t{r['KM']}\t{r['TNKM']}\n")
tiers = {">=20": 0, "8-19": 0, "3-7": 0, "1-2": 0}
tier_e = dict.fromkeys(tiers, 0)
for p in rest:
    e = int(brenda[p]["entries"])
    k = ">=20" if e >= 20 else "8-19" if e >= 8 else "3-7" if e >= 3 else "1-2"
    tiers[k] += 1
    tier_e[k] += e
out["not_in_v2_tiers_pmids"] = tiers
out["not_in_v2_tiers_entries"] = tier_e
print(json.dumps(out, indent=1))
