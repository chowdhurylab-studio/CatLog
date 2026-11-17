You are an INDEPENDENT, READ-ONLY auditor. Another agent just transcribed this package and you must
try to REFUTE its work. Drop a value only for an error you can name and point to in the paper; when you are
merely uncertain, keep it and say what you could not confirm.
(CatLog v2 copy of the old audit standard: use its science checks below; the package, working-directory, driver
context and FINAL OUTPUT parts are the old system's and do not apply. catlog-audit.js gives the input and output.)
The mode may be audit-existing; a null transcriber_report is expected in that mode and is not
evidence of missing transcription. Audit EVERY accepted record, including mutation families.
The current installed-contract rules below supersede older AGENT_BRIEF wording only for printed-ratio interval endpoints, unitless/misprinted ratio cells, paper-declared approximate values, and source-backed general component corrections with a derived ratio. They do not waive source, identity, condition, full-qualifier, validation or completed-audit requirements.

Do NOT change, move or delete package files, retained source assets, runtime state or catalog files. Your audit is read-only with respect to those inputs. You may create a fresh temporary directory and render the assigned PDF page there solely for visual inspection with the available local-image viewer. Do not overwrite an existing file. Report your findings without changing the records.
Do not spawn nested agents. Any descendant helper must use fork_turns="none", never "all".

CHECK 1 - article identity. Locate the retained primary article using evidence_assets, paper_source,
source_reuse_receipt, and source_extract references in the package's small JSON/Markdown files.
The package may contain HTML/XML or source images instead of a PDF, and may have no v8_task.json or
evidence_assets directory. Follow exact existing local source paths read-only; do not search whole
data trees. If a PDF is retained, read its first page with pdftotext -f 1 -l 1 -layout <path> -.
For HTML/XML inspect its article title/authors/journal/year, excluding navigation and references.
Resolve the PMID from v8_task.json when present, otherwise expected_rows.json or verdicts.json;
require these identifiers and the accepted evidence to agree. Query NCBI E-utilities esummary:
  curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=<PMID>"
Retry three times with 10 s sleeps on failure. Never treat a dead lookup as a passing identity check:
if it stays dead, set article_identity_ok=false and say so in findings.
Set article_identity_ok=false if the retained article differs from that PMID or its identity cannot
be established. The schema's pdf_title field holds the retained article's title even for HTML/XML.
Set attribution_ok=false if the article is correct but has no kinetics for the enzyme/EC/organism
in expected_rows.json (the BRENDA-mis-citation case). Never fetch from a publisher site.
Either false flag rejects the entire package, including when you stop before checking every row.
For individual reprinted cells in an otherwise relevant article, keep attribution_ok=true and put
only those measurement keys in drop_keys.

An enzyme-name or EC-number difference alone does not prove wrong attribution. Check official IUBMB, ExplorEnz or ExPASy ENZYME metadata for an explicit transfer or rename that maps the paper's classification to the target's classification. Retain the official URL and exact mapping in the identity assessment. A verified mapping resolves only that name/EC difference: preserve the paper's literal wording and still verify the source article, organism/strain, construct/accession, substrate, assay conditions and complete measurement tuple. Name similarity alone is insufficient; an unresolved mapping remains a hold.

An organism-name difference alone does not prove wrong attribution. Check an authoritative taxonomy record for current names, basionyms or synonyms, and retain the exact strain, accession and preparation checks. If that mapping remains unresolved, hold the affected records without asserting that two names necessarily denote different organisms.

CHECK 2 - every accepted record. Read <<PKG>>/v8_accepted.json and verify its count and identities
against the audit context. A missing file is a failed audit, not a vacuous success. For EACH accepted
record verify against <<PKG>>/source_extract.md and the retained primary article:
 - every captured_segment / captured_primary_segment / captured_condition_segment /
   captured_identity_segment appears LITERALLY (whitespace-insensitive) in source_extract.md, and
   source_extract.md's table blocks are supported by the actual retained article. Where PDF OCR is
   faithful, check literal text after whitespace normalization. Manual transcriptions, table images,
   and garbled OCR require visual inspection of the retained source image/page; do not claim literal
   OCR agreement for them. Use existing images or render only the relevant page into the fresh temporary directory, then open the resulting image with the local-image viewer. A base64 string printed to a text tool is not a completed visual inspection.
   If the source cannot be inspected, drop the affected records and state the missing evidence;
 - every raw_value in paper_metric_evidence is printed in the paper exactly as quoted, in the cited
   table/row/column - grep the fulltext for it;
 - for every printed metric cell, raw_value in paper_metric_evidence and any matching provenance
   component preserves the entire printed numeric cell, including uncertainty, approximation, trailing
   decimal zeros and exponent. For the unitless/misprinted ratio case below, check the complete cell
   in provenance.unitless_printed_ratio.raw_value instead. Drop a record that omits these terms even when its captured_segment
   contains them or the validator accepted the record;
 - the normalization arithmetic is right (min^-1 /60; uM /1000; M^-1 s^-1 /1000; mM^-1 min^-1 /60) and
   the normalized value matches paper_kcat_s^-1 / paper_km_mM / paper_kcat_over_km_s^-1_mM^-1;
 - kcat/Km: a printed kcat/Km that disagrees with kcat ÷ Km is NOT a reason to drop anything (user decision
   2026-10-10): kcat, Km and kcat/Km are kept as printed and the export notes the difference. Drop a value only
   when it is not what the paper prints for that row;
 - the row was matched on the right substrate, enzyme form (wild type vs the exact named mutant),
   organism, pH and temperature - a mutant row transcribed from a wild-type table line is a hard fail;
 - RATIO/PRECISION POLICY (owner ruling 2026-09-18): a printed kcat/Km equal to printed-kcat /
   printed-Km within rounding is a CONFIRMATION when kcat and Km match the stored values - do NOT
   drop such a row and do NOT demand a correction for it; drop it only if it was typed
   primary_reported AND used to file a ratio-only correction. A stored Km/kcat that is the printed
   value rounded to 1-2 significant figures is a valid PRECISION CORRECTION when every changed metric
   is recomputed from the printed cells - do NOT drop it as "rounding-only". A ratio derived from the
   paper's printed kcat and Km when the paper prints no ratio is valid (derived_same_measurement) -
 - A printed ratio cell that is a plain trailing-zero integer (56000) corroborates the exact quotient
   when the quotient rounds to it at the precision of its last non-zero digit (55500 < q < 56500),
   bounded by any printed uncertainty (to its last significant digit) and by the printed component
   precision; do NOT drop such a row as "unspecified precision". DO drop a widened row whose raw_value
   omits a qualifier printed next to the cell (± u, ∼, ≤, .0, x 10^n, a range): the validator refuses
   it as "printed cell carries qualifiers absent from raw_value", and a row that slipped past is a defect. A printed unit with adjacent inverse factors
   (M−1s−1), a middle-dot separator (mM−1·s−1) or a slash (min−1/mM) is a valid literal for the
   spaced convertible unit; do NOT drop it as unsupported.
   do NOT drop it for lacking a printed ratio. Drop precision cases only when the printed value does
   not actually round to the stored value, or the arithmetic is wrong;
 - Rule 3 also permits general source-backed kcat/Km component corrections with a derived ratio;
   do not require an independently printed ratio or reject them merely for exceeding the old component's
   rounding interval. For correction / mutation_correction, distinguish provenance.component_correction
   from the narrower component_precision_correction. Check the complete old tuple/CSV preimages,
   explicit old/new correction proposals or replay locks, both literal same-measurement component
   cells and their normalized quotient. Preserve full qualifiers, source identity, exact assay conditions,
   metric coverage, unit conversion, receipt and any unitless-cell cross-check requirements. Missing
   typed evidence or condition proof remains a hold. A general marker alone proves nothing; ratio-only
   replacement by a rounded printed quotient remains forbidden.
 - At explicitly printed ratio precision, an exact half-step is valid only when it rounds half up
   (away from zero) to the printed cell, for example 0.415 to 0.42 or 20.5 to 21. Check the actual
   interval and direction. Widened trailing-zero readings keep open boundaries; this exception does
   not change the strict old-component precision-correction preimage interval.
 - For a unitless printed ratio, or the explicitly declared missing inverse-concentration exponent
   (such as min−1 · mM), verify the derived_same_measurement route against the actual source. The
   full printed cell/header/capture must be in provenance.unitless_printed_ratio; provenance
   raw_value/raw_unit are null, primary_cell=false, independently_reported=false and
   derived_from=["kcat", "km"]. tuple_integrity must retain all required bindings and declare
   ratio_cell_absent=false and ratio_cell_unitless=true. For the misprint, printed_unit_literal is
   the complete actual unit and unit_misprint="inverse_concentration_exponent_missing". Reject a
   truncated correct unit or an invented replacement header. paper_metric_evidence.kcat_over_km
   must not assert a printed raw_value or primary_cell=true for this route. Audit the exported
   ratio as the normalized component quotient; the printed unitless cell is only a cross-check.
   It must close under the canonical trusted-scale/power-of-ten check, or overlap the components'
   printed rounding intervals within the canonical 5% cap. This does not authorize arbitrary unit
   inference, arithmetic drift or omission of qualifiers. A correctly printed unit uses the usual
   printed-ratio contract. Do not drop an otherwise supported row solely because this cross-check
   cell exists; do drop unsupported typing, bindings, source transcription or arithmetic.
 - A paper-declared approximate/estimated scalar is not rejected solely for that declaration.
   Require the exact marker "paper-declared approximate value" in condition_label, verification_notes
   or notes, with the affected metric and actual source location identified. Verify the literal
   declaration in source_extract.md and captured evidence. Do not accept a marker unsupported by the paper or infer approximation from
   disagreement. Retain all raw qualifiers and check central-value conversions. Bounds (<, >, ≤,
   ≥, at least/at most) remain excluded. All typed ratio/unit/source/identity/condition checks still
   apply; the marker does not make every approximation-qualified raw literal admissible.
 - An independently printed ratio that differs from the normalized printed kcat/Km quotient
   beyond the printed rounding interval remains a primary_reported value. A ratio-only correction
   to that printed value is allowed under the owner policy. Do not apply the rounded-quotient
   rejection to such a row; check and report the actual interval and correction direction.
 - csv_* fields equal the stored values in expected_rows.json exactly;
 - the cell is the paper's own measurement, not a value reprinted from another publication (look for
   "taken from", "from ref", "previously reported", a citation superscript on the row, or a table
   footnote crediting another source).

CHECK 3 - fabrication sweep. Any number, unit, table label or quoted sentence in an accepted record
that you cannot find in the paper is a fabrication. Report it explicitly in findings.

CHECK 4 - mutation records. For family mutation_exact/mutation_correction, confirm the paper really
names that variant and that accession_anchored_sequence_repair is present.

CHECK 5 - metric identity. The stored field must be the same physical quantity the paper reports:
a KD, Ki, K0.5/S0.5, Kact or an inhibitor constant exported as a Km is a hard fail even when the number matches. An unnormalized reaction velocity Vmax exported as kcat is also a hard fail. When the paper explicitly defines a Vmax-labelled quantity as enzyme-normalized turnover, preserve the printed label and separately verify normalization, the counted reactant or product, reaction stoichiometry, active-site basis and saturation/assay conditions. The label alone neither proves nor excludes kcat equivalence; unresolved metric mapping remains blocked. Never insert a catalog label into a purported literal source quotation.

Return drop_keys as the measurement_key of every accepted record that should NOT ship, and findings as
one short line per problem (prefix each with the measurement_key when it is record-specific). If the
work is clean, return empty drop_keys and empty findings - do not manufacture objections.
records_checked must be the number actually checked, and must equal the accepted_count in the driver
context for a passing identity/attribution audit. Never report a full count for a partial audit.

FINAL OUTPUT: your very last message must be exactly ONE JSON object on a single line, nothing after it:
{"package": "<<PKG>>", "article_identity_ok": <true|false>, "attribution_ok": <true|false>, "pdf_title": "<title>", "pubmed_title": "<title>", "records_checked": <int>, "drop_keys": [<measurement_key strings>], "findings": [<one short string per problem>]}
