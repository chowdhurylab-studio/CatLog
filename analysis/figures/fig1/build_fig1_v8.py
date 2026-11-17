#!/usr/bin/env python3
"""Fig. 1 of the CatLog v2 Nature Methods paper, design A ("v7, lean"), 2026-11-05.
The owner loved v7 (big step boxes in light role fills, a short label in each, a clear left-to-right path, the zoom
from a into b) and hated v8 ("too much writing and hard to follow", 486 words). This design keeps v7's composition and
cuts every panel to the same restraint:
a: the workflow (v7's layout, people added as the benchmark at the top left).
b: a's reading frame enlarged: each step's rule count and one real before -> after case on grey plates.
c: one row: papers, full text, reading, CatLog, one stored record (printed vs stored).
   W3 (6 Nov): under it a slim second row, "Linked by code": the enzyme to UniProt P00805 and its sequence, the paper's
   N248A to residue 270 counting the 22-residue signal peptide, the substrate to ChEBI 58048 and the structure drawn above.
d: co-learning: four nodes with one number each, who found the errors as a labelled split, the trap result.
H6 (6 Nov, the owner chose six additions from writing/research/fig1_review/MISSING_COMPONENTS_20261106.md, keeping the
figure simple): W3's "Linked by code" row under c (as built and checked in work/fig1_identity_20261106/W3); a foot line
in c's record (each value keeps the paper's line, the agents, instructions and code version); the bounds ('< x', 'not
detected') CatLog keeps apart, counted in c's CatLog box at the moment of its values count; d's second step written by
people with an agent and its third saying code re-checks every value (d's steps now two lines each, so the words fit
the loop); a's People box with today's count of records people reviewed and the benchmark wording for 2,158 papers.
R1 (6 Nov, from the independent review's synthesis): b's Check card shows a learned code rule (TL11, '378C' read as
37 °C) instead of an open failure kind; a's People box gives its two numbers as two facts; c's Papers box says the 343
locked papers are kept unread for a later test; one arrow out of Decide to the database errors of Fig. 4; d's third step
reads "Affected papers are read again"; c's record names its variant, pH, temperature and table, the Linked row says
"its N248A mutant", and c's CatLog box says its counts are so far.
Q1 (7 Nov, the owner: "the content and layout are final; improve the visual and the writing"): the 7 Nov edit plan
without its colour layer. b's Read card from 25658941 (a column headed Km beside Hill n = 2.2; 26142822 was c's own
enzyme), b's captions as plain clauses, d's three errors in the past tense, plain words for 'reconciled', 'bounds',
'so far' and the record's foot line, junction dots on Verify's inputs, a hairline in c's CatLog box, the residue-270
dot, solid Flag markers, 0.5-pt shafts on the inline 'becomes' arrows; the legend's new sentences go to
Q1_legend_draft.md beside the preview, every number in them from F.
Q2 (7 Nov, the owner: "if needed we do more colors maybe?"): Q1 plus one colour with one meaning, learning, in NPG cyan's
edge shade (#2E9BB7, 3.2:1 on white): a's four learning arrows (errors from people, findings back to them, rules into
the reading, the deciding agents' errors), the Co-learning outline and its loop icon; d's whole loop, the examples'
arrow into it and the outline of 'People write a rule'. Labels stay ink and no fills are added. The arrow to the
database errors of Fig. 4 is light grey, its label grey: it leaves the method. The three lines out of Decide then read
black (corrections), cyan (errors) and grey (out), in greyscale too. Each colour has its own group (a learning,
a exit) so the style check can hold it to its meaning; the legend states the colours in words. Checker: only colours
differ from Q1 (outlines 0.6 pt and shafts 0.75 pt as there).
Q1 checker (7 Nov): the substrate link says 'found in the reaction', not 'matched in'; the legend draft's sweeps
sentence no longer claims three refuters for every sweep (the reprint sweep had one, the n.d. check two and a third),
its date sentence names the CatLog box (the Papers box counts are today's lists) and defines 'limits', its Read
sentence gives both Hill coefficients (2.2, 1.9), and 'counted where they live' is said plainly.
S1 (7 Nov, the owner's nine points on Q2, inside its layout): red (NPG #E64B35) means errors only: the two 'errors'
arrows into Co-learning and their labels, the Flag pennant and the suspect mark of each Flag icon, d's flag, the red
marks of d's three errors and their arrow into the loop. b: each card says '1 of N rules' and draws N ticks, the case's
in ink, so a case reads as one rule of many. One notation: the slash only inside the name kcat/Km, no ÷ or ≠ on the
figure ('kcat, Km and kcat/Km disagree', 'its kcat and Km show a misprinted unit'). a's Flag names its five sources
with small line icons in the colour of who raises each (a person; a rate curve whose printed initial slope misses; two
pages with the same row; a die; a fold difference on a log axis) in place of bars: the Flag box 15 pt wider (a's CatLog
box 8 pt and Decide 7 pt narrower), the step row 5 pt taller. c: the CatLog box gives its two counts in bold at the top
and what it keeps separately as papers print it (ND, < 0.01), with counts; the record box is 'A record' with its
definition on the title's line; the Linked row loses its glyph icons and shows the predicted structure of P00805
(AlphaFold DB, CC BY 4.0) beside the UniProt link, the N248A link pointing at residue 270 in it. d: the three errors as
small pictures with short clauses, red only on the error (a reprint; a Km printed in mg/ml that code refused, CU8, in
place of catalase, whose kcat values are component rates of a two-Hill fit; a test paper read).
The 7 Nov ingests of people's reviews (human_review/decisions.jsonl rebuilt at 09:50 and 10:01, with reviews made before
the 6 Nov cut) moved the People count: it is now counted to the file's last decision (7 Nov 04:12 UTC).
S1r (7 Nov, the editor's review of S1, inside the owner's nine points and rules): red is a surface where errors are held
(a's Flag box and d's errors step, a light red fill and a red outline; the Flag's icons in one style, ink with red on the
suspect part; 'rejected by a reviewer', 'random 7% audit'); the catalogue filled in its own dark green (CAT_SOLID; False
gives the white box back), so green no longer reads as the agents' mint. a: people's reviewed papers come in at the paper
text, outside the blind frame ('rules' is the one arrow into it); each step names only who does it; Co-learning's glyph
is a person over an agent's page with a cyan arrow each way. b: each card leads with its count of rules ('16 rules'), the
ticks in cyan under it (the shown rule's tick in ink) and 'e.g.' before its case; a header over its cell is a two-row
table cell, no longer a fraction; Hill's n in italic. c: the CatLog box takes a third half-column from Papers, its two
counts on top and in words beside them what it keeps apart ('+ 20,961 not detected', '+ 1,334 only as < x or > x');
the record names its fields (enzyme, substrate, assay) in the column of kcat, Km and kcat/Km, its curve at the top right,
and each value's trail as five tags; the Linked row shows the structure one shade darker (T1: no name under it, the
legend credits AlphaFold DB), the sequence bar's signal and residue 270 named, the substrate's drawing (moved from the
record) at the end of its link with 'neutral form' under it (ChEBI 58048 is the zwitterion; CatLog stores the neutral form). d: the errors' step
red, its words in ink ('Errors found by people and agents'); person icons tan, agent icons mint, code's </> beside
'code re-checks'; the refused Km is its printed cell and an arrow struck by the red cross (refused, not wrong).
T1 (7 Nov, the owner's five points on S1r, inside its layout): the two CatLog boxes as the People box is drawn, a light
tint of the catalogue's NPG green (0.12 over white) outlined in that green (0.75 pt), the name in its darker shade, words
and icon in ink, so green keeps one meaning and the boxes no longer outweigh the steps; the Linked row as one of c's boxes (S2:
white, code's outline, its title 'Linked by code' and 'after reading', three links on two baselines, the structure and
the substrate larger, no name under the structure: the legend credits AlphaFold DB); b's ticks coloured by who first
found the error behind each rule (grey the earlier system's lessons, the agents' edge CatLog's agents and code, people's
edge people; the example's in ink, first in its group); the record's curve labelled with its own stored kcat and Km and
its axis's '[S]'; each value's five tags as one plain grey clause.
T1 round 2 (7 Nov, a cold editor's review of T1, applied inside the owner's five points and rules): slate and tan fills
lighter (as light as mint reads), the CatLog boxes' green outline 1 pt; icons only in a (steps, inputs, people, the flag),
none in c's boxes (U1: the owner asked for them in Papers and Reading), in Co-learning or on d's cards; b's ticks from
the card's left edge, the example's rule first in ink with a hairline down to its 'e.g.', the count after the row, every
line of a card on one left edge; c's Reading box a's four steps in words with small arrows, the CatLog counts on the
Papers sources' baselines, no curve in the record; the Linked row in three columns with thin rules, the structure
re-rendered in light grey, no 'after reading' or 'neutral form'; d's cards one style, white with a thin outline (red
errors, cyan the rule written), no icons.
T2 (7 Nov, the owner's point 3 the second way, "what the rules are"; only b differs from T1 round 2): each card's ticks in
one colour, the learning cyan of S1r (the owner of those ticks: "the rules thing looks nice"; TICK_ONE, one constant to
change), the example's rule in ink with its leader as in T1; under the other ticks, from the first of them, two or three
of the step's other rules named in plain grey words, 6.5 pt so the K of Km keeps a 5.5-pt subscript ('reprints, isozymes,
supplements'; 'Km in mg/ml, ± terms'; 'missed values, slipped decimals'; 'test papers, the wrong paper'), each a rule
of its card's own layer and not the example's (facts). Three of them are the rules d's three errors led to (the reprint,
the Km in mg/ml that code refused, the test paper read early), so b and d echo each other without an arrow. T1's
finder colours are not drawn (their facts stay asserted). b is 2.1 pt taller (the figure 169.9 mm): the ticks 0.6 pt
higher, the named line 1.9 pt under them (0.5 pt clear of the count's text box), the case row 1.5 pt under its
descenders (Verify's stacked print), the caption 14.6 pt under the row (16.3), the cards' foot 4.4 pt under the caption
(5.4) and the dashed frame 4.2 pt under the cards (5.0). The legend's b sentence says what each named rule does.
T2 checker (7 Nov): c's '+ 20,961 not detected' on the baseline of the Papers box's '343 kept unread' (it sat 0.4 pt
above it), as T1's checker set it in T1, so the two variants still differ in b alone.
U1 (7 Nov, the owner's five points on T2, inside its layout: plain words over internal terms, and a little more visual
help where c has the most words). b: each named rule a plain clause that says what CatLog does, one a line, two under
Read, Convert and Check and one under Verify ('an earlier paper's value is skipped', 'isozymes are not stored as
mutants'; 'a Km in mg/ml stays in mg/ml', 'no unit is ever assumed'; 'values the reader missed are found'; 'test papers
are locked until the test', 'a file with the wrong title is refused'), each a rule of its card's layer whose guard and
CatLog's code or instructions say so (facts). a: each Flag line says what raises its flag ('printed in an earlier paper
too', was 'reprinted value'; 'picked for a random 7% audit'; 'a database differs ≥1.5-fold'). c's Papers box: each source
with a line icon (the databases three stacked tables, the search a lens, the test papers d's locked page without its
lens), its count in bold over what it is in grey ('from a literature search', the search tool's words), the papers kept
unread under a hairline at the CatLog box's. c's Reading box: a's four step icons, small, their closed parts in the fill
of who acts, each beside its name. c's record as a card of the catalogue: a title strip in the catalogue's tint saying
what a record is, its enzyme and assay in two plain lines, its three values as a small table (the paper's print on grey
under 'printed in Table 2', 'code converts' over the arrows, what CatLog stores on the tint in green) and its trail under
a hairline ('each value traces back to ...'). b grew 2.55 pt with its second lines; c's row is 1 pt shorter and d's loop
1.4 pt higher, so the figure stays under 170 mm (169.98).
U1 round 2 (7 Nov, a cold Nature Methods figure editor's review of U1, applied inside the owner's five points, the layout
and the 170 mm): b: every rule an instruction in plain words, the example's own rule the list's last line in black with
its print directly under it (no caption at the card's foot, no ink leader, which "looks like a stray text cursor"), each
rule led by a small dot in the ticks' cyan, every tick cyan ('skip values copied from older work', 'never store an isozyme
as a mutant', 'skip a Hill constant printed as Km'; 'keep a Km in mg/ml in its own unit', 'never guess a unit the paper
omits', 'read exponents printed with spaces'; 'find the values the reader missed', 'check kcat/Km against kcat and Km';
'keep the test papers unread', 'refuse a file of the wrong paper', 'allow for ° shown as 8 in PDF text'), Verify's
header over its cell standing on the row's baseline. a: the Flag's 'same value in an older paper'; d: 'a copied value was
stored' (one word, 'copied', in b and d). c: every title left-aligned on one baseline; the Papers box's databases a
cylinder, its three icons one size; Reading a's four steps as small boxes filled in the colour of who acts, with a's icons
and bold names; the CatLog box a's table icon beside '243,749 values / from 7,514 papers'; the record titled 'A CatLog
record' ('A record' read as a panel letter; 'One record' the owner found odd), its fields named (enzyme, substrate,
assay), its three values a table of three shaded columns (the paper's print grey, code's step slate, what CatLog stores
on the catalogue's tint), no rule over its trail. Not applied, as they cut across the owner's rules or the 'everything
else is good': a's step subtitles, Co-learning, Decide and 'findings'; d's tags and 'Checked both ways'; ÷ and ≠ in the
Flag; numbered chips, unit factors and trail tags in the record; the CatLog box's longer footer. 169.7 mm.
P1 (9 Nov, the owner on U1 round 2: "we cannot mention other figures inside a figure, and where are the database names
we put before there? That look better than this"): the grey arrow to 'database errors (Fig. 4)' is gone; the databases are
a card again at a's top right (as in alternative 3, 5 Nov), in b's card style: a navy-tinted title strip ('Databases'),
the six names on one line at 6 pt (6.5 pt does not fit over Flag and Decide), a navy outline, over the after-reading boxes
and outside the blind frame. Its one arrow, navy, ends in Decide, the agent given the database's number beside CatLog's,
which decides from the paper and never changes a value; the check's output, the databases' own errors, is said in the
legend (nothing is sent back to the databases). Decide's red errors line now leaves from Decide's middle and runs under
the card (39.0, was the top row's middle), its label between Co-learning and the card; the corrections line 2 pt lower
(50.0). No arrow crosses another; the figure's height is unchanged.
X1 (9 Nov, the owner's three points on U1 round 2: the database names back with no figure named; "learned rules at each
step ... a better way to show the rules", examples that show why the rules matter, "not basic (378 to 37 °C)", "too much
writing"; "polishing and font size improving ... more clean"): P1's Databases card and V8b's decks together, then a
polish. a: the card spans CatLog's left edge to Decide's right (alternative 3's span, the card the owner remembers), so
the six names fit on one line at 6.5 pt; Decide's errors line keeps its route under the card and its label stands under
the line, just after its head. b: each step the top card of a small deck of its own rule cards in the step's colours,
'1 of N rules' on the strip, a grey line with the idea behind the rule shown, one real print and what CatLog does with
it: a Hill constant under a Km header (not a Km), a kcat printed per minute (converted by code, 60-fold), a kcat/Km
header misprinted by 10^6 (the paper's own numbers decide), one printed cell read twice 1,000-fold apart (the second
refused, struck by d's red cross); no ticks, lists or 'e.g.'. Text: the record's definition, field names and column
heads, the Linked row's sequence labels and d's years at 6.5 pt (6 before); only the count captions of c's Papers and
CatLog boxes stay at 6 pt ('from a literature search' does not fit its box at 6.5). Legend: b's sentence says what the
decks and the four cases show; red names b's refused reading, the fills b's decks. 166.8 mm.
X1 round 2 (9 Nov, a cold Nature Methods figure editor's review of X1, applied where it keeps the layout, the 170 mm and
the owner's rules). b: no decks (their offsets read as a double border at print size); each step one card, its rules a
row of cyan dots, one per rule, the rule shown dark and first, 'N rules' at the row's end (the count as a picture, and
cyan, the learning colour, back in b); the rule shown in one dark 7-pt line ('A Hill constant is not a Km', 'Code
converts the printed unit', 'The paper's own numbers decide', 'Two readings must agree'); under it the real print, what
CatLog does with it in bold on the cells' row, and on the header's row the error the rule stops with its size in red:
126 s^-1 struck (BRENDA, OED and SKiD's number, 60-fold), the header's µ struck (10^6-fold), the second reading 4,300
struck (1,000-fold); Read's Hill constant outlined in red; no red cross in b (d keeps its crossed arrow). c: no Reading
box (a's four steps were drawn three times); Papers and CatLog four half-columns each, under b's first two cards, all
their words 6.5 pt (no 6-pt text is left); the record's code column one slate arrow, 'code' in it; the Linked row
outlined in the Papers box's neutral grey (its slate edge read as navy) and its mutant 'its N248A mutant'. Not applied,
with the owner's rules as the reason: the zoom lines and b's frame (the zoom from a into b is v7's, kept at the PI's
request), a's grey band, the Flag's plain clauses and icons, d's loop wording and its examples' way into the loop, a
darker structure (light grey since T1 round 2, so residue 270 stands out), 'bounds' and a shorter record trail
(internal word; a fragment). 168.5 mm.
X1 checker (9 Nov, an independent check of round 2): every number, rule count, example and database name recomputed
from the repository, and true; the figure unchanged. The legend made exact: b's sentence says Read's error is the
outlined cell (no size) and the other three show their size; the Read case's Km and Hill columns 'share rows' (the
table prints three columns between them, so 'beside' is gone); the Verify case names the database that holds its
10^6-fold error, as Convert's does (SABIO-RK lists all 13 kcat/Km cells of the table 10^6-fold high; facts_b2).
Y2 (9 Nov, the owner's three points on X1: "dont you think putting back is a good idea but too many boxes to. maybe as a
part of the catlog box (2 box merge kinda)"; "can the databases get their boxex in names instead of a,b,c,d...."; "can the
rules thing still be improved - focusing on how many rules thetre are- as the expanse of the system kinda"), inside X1's
layout. c: the Reading box comes back inside the CatLog box, so c stays three boxes: under the title, a's four steps
(Read, Convert, Verify, Check) as small tiles in the role fills with a's icons, an arrow between each two and each step's
name under its tile; then the count (now on the Papers box's second source's baselines) and, under the hairline, what it
keeps apart, as before. a: the Databases card loses its navy strip; a plain bold title and each of the six names in a
small white box of its own with a navy outline, in one row (the card's place and foot unchanged, so the errors line, its
label and the navy arrow into Decide stay). b: the count leads: each step's rules as tally marks, one cyan stroke per
rule, crossed in fives (Read 3 fives and 1, Convert 2 fives, Verify 1 five and 2, Check 7 fives), 'N rules' after them,
and the total in b's title ('Learned rules at each step, 68 in all': 16 + 10 + 7 + 35; the database check's 3 rules are
named in the legend); no dark mark; the rule line and the real case as X1's, 1.71 pt lower. Facts since X1: the Papers
box's literature search stays the kcat search's 30,814 (the Km-only search joined coverage.tsv on 9 Nov, 93,868 papers in
its own tiers, left out: the owner's call), and 12591933's add line of the 9 Nov n.d. pass (kept=0) is left out of its one
read. 169.1 mm.
Y2 round 2 (9 Nov, a cold Nature Methods figure editor's comparison of Y1 and Y2, applied where it keeps the layout, the
170 mm and the owner's rules). b: 'N rules' at the right end of each card's strip, on the name's baseline at 7 pt, the
number bold (one look along the strips reads 16, 10, 7, 35), so each tally row ends with its last stroke; 0.8 mm more
white under the strokes; the title leads with the total, '68 rules learned, by step' (7 pt bold like every title; the
editor's 8-pt 68 is the panel letters' size); Verify's misprinted µ in red instead of struck by a hairline (a red outline
round it, as Read's, has no room in the header row); Check's struck reading with its unit, 4,300 mM^-1 s^-1, and its size
written 10^3-fold so the line fits. Not applied: labels 'read' and 'verify' over Check's arrows (the two readings are the
first reading of 11 Oct and a blind re-reading of 22 Oct, not the reader and the verifier; 6 pt is under the text size;
at 6.5 pt they do not fit between the rows), a reworded Verify rule ('Numbers outrank the header': the brief keeps each
card's rule line as the owner saw it, and 'the paper's own numbers decide' is verify.md's own wording), '68 rules' in a's
Co-learning box (that box holds all 71 rules; the database check's 3 are in code too). a: the name boxes outlined at 0.35
pt (half the card's 0.6), 2.6 mm tall and 1.2 mm clear of the card's foot, spread with even 1.4-mm gaps from the title's
left edge to 1.5 mm short of the navy arrow (the editor's full width would put STRENDA DB right over the arrow, so it
would read as one database's). c: the four step tiles white with their role outlines (mint on the catalogue's tint read
as an empty outline); the CatLog box's title, step row, count and hairline evenly 3.0 mm apart, and the Papers box's
second source moved onto the CatLog count's baselines, so the two counts stay level (the optional raised arrow into Read
is not drawn). Legend: b's counts on the strips, the red µ, the white tiles, 'The four steps drawn in the CatLog box are
the workflow of a'. 169.9 mm.
Z1 (9 Nov, the owner on Y1 and Y2: "i dont like tally - also we are not shoing that the example with eg (it is one of
the rules) ... maybe we just say how many rules (term it better maybe? like human co learning enforced) and then e.g.,
to show what kind of rules and in figure details in caption we guide to a supplementary for all rules"): Y2 without its
tally marks. b's title '68 co-learned rules at the four steps'; each card its count on the strip, then 'e.g.' (grey)
and the rule its case shows, then the case; no cyan in b. The legend points to a supplementary table of all 71 rules.
Y1's checker's strike fix (1.9 pt over the baseline) applied.
R1 (10 Nov, the owner on Z1, after calling it final: "the colearning examples not good and do we need those at all? overall
true for the colearning rules in b too - feels like too trivial and not wow ish and not publication or significant
sceince contribution worthy"; "the database boxes should be more polished and well done like you did long ago and the
linked by code segment i dont understand anything and its confusing for a casual reader - should pick better example or
show in a better way whats happening so needs significant rework"). Built by hand in one pass, then a cold editor, a
first-time reader and two independent fact checkers. a: the Databases card has its navy strip again, each name in a
box of its own under it (the top row 2 pt taller). b: each card's case now shows why its rule matters, in three rows:
the paper's print, the number a database lists for the same paper (red, with the error's size), what CatLog stores
(green); four cases, four databases (UniProt, BRENDA, SABIO-RK, OED); Check's case is new, a ± that a PDF's text layer
prints as 8 (6 ± 1.5 reads 681.5, the number BRENDA and OED list). c: no Linked row and no protein picture; the record
takes the right half and shows, row by row, what the paper prints, code, and what CatLog stores: the enzyme and its
UniProt entry with the sequence as a bar, the variant placed in it (N248A is N270A, 22 signal residues on), the
substrate and its ChEBI structure, the assay and the three values; Papers and CatLog stand in the left half. d: the
three examples are gone; the loop's four steps in one row, one real error told through them (24 copied values found by
an audit, the rule written within the hour, 296 papers compared, 973 values removed from 80 papers, 165 kept).
FIG1_D_PLAIN=1 draws d's loop alone. facts_r1 holds the new facts.
R4 (10 Nov, the owner on R3: "why is database names in segment b - i thought the database should be written in proper
boxes in a as the database segment, no? confuised"; "see ... you find mor design improvement, figure improvement,
quality and nature method likeliness and less ai ness"; three designers' proposals merged by a builder; no word, number
or box of the layout changed). The database a case of b names is drawn as a's Databases card draws it, by one function
(namebox): the same white box with a navy hairline, the name in the text's own face; it was a bold navy word at the head
of a line, a second way of drawing a database. Navy is the databases' line only (the card, the name boxes of a and b,
the arrow into Decide, the cylinder beside 'cited by databases' in c); code's outline is the lighter NPG slate (#8491B4;
#5D6A92 read as navy). a: the name boxes 8.5 pt high and on the title's left edge, the card 1.5 pt shorter, the errors
line 3.8 pt under it; every label 1.9 pt from its line. b: the print on flat grey plates, a white rule between a column's
header and its cell (no outlined cells: the database's box is the only outlined thing in a card); Convert's plate on the
second row; the line that says what the rows are follows the title. c: the record set as a table, three heads on one
line over the columns, the prints set left; Papers' two sources one line each, the dividers from margin to margin, the
step tiles larger. d: the return's label in the text's colour, 1 mm under the cards. Type and lines for print: text,
icons and arrows black (#000000; they were #3C3C3C and #262626), grey (#595959) only for asides ('e.g.', the entry's
length, the signal peptide, the two years); one neutral line grey (#808080); four line weights (0.35 hairlines, 0.5
outlines, icons and bonds, 0.75 arrows, red marks and the white rules, 1 the CatLog boxes); the strips of b and of the
record one height; one small corner radius; one distance from a panel's title to its boxes (5.5 pt), one text inset
(4.5 pt) and one foot (3.6 pt) in the cards of b, c and d. Not taken, because the owner had settled them or two designers disagreed:
the grey band (kept, and kept lighter than the plates), the zoom and b's frame, the outlines of the filled boxes, the
code arrow in the record, labels set inside a break of their line (an arrow stays one shape), a small-capital L (5.5 pt
is for sub- and superscripts only), the wording. 169.0 mm.
R5 (10 Nov, a cold editor compared R4 with the earlier version, found it the better figure and listed seven places;
applied inside the owner's rules, by one builder). a: 'After reading' is a dashed frame like 'Blind to databases and
reviews' (the same weight and dash, its words centred at the top; it was a grey band, the one grey area that did not
mean print), so the two stages are drawn one way and a grey area is what a paper prints; the CatLog box between the two
frames is 1 pt narrower, 5 pt from each, and the arrow from it into Flag as long as the arrows between the steps. The
databases' name boxes are outlined at the outlines' 0.5 pt in a and in b (0.35 pt of navy printed as black). b: the
dashed frame is its top edge only, from the first card's left edge to the last card's right, and the zoom's two lines
end on its two ends; title and cards stand on the page as c's and d's (a box in a card in a frame was one level too
many). The line that says what a card's rows are is back where the earlier version had it, at the right end of the
title's line, in the asides' grey (in black after the title it competed with the title). c: code is four short slate
arrows, one per part of the record, each as long as the head 'code' over them is wide (the slab without its word read
as a stock process arrow); the substrate's row 1.5 mm taller and the drawing's right edge on the column's text edge, so
the structure stands 0.8 mm or more inside its cell; the Papers box takes that height as white between its parts, set
so that the CatLog box's row of steps is level with the arrow into the record; the arrow from Papers into CatLog one
gutter long, as every short arrow. d: '973 copies removed from 80 papers' ('leave 80 papers' could be read as leaving
them behind). Dividers and the zoom's lines 0.5 pt, and the one neutral grey 60% black (#666666). Not taken: a key of
the rows' styles on b's title line (a colour key, which the owner ruled out); a navy tint in the name boxes (a light
navy is code's slate fill, the two share a hue, so the box would read as code in Convert's and Check's cards); the
names' row centred in the Databases card again (it starts on the title's left edge, and its right end keeps the arrow's
lane free). 169.0 mm.
R5 checker (10 Nov, an independent check of R5: every drawn text against a fresh build of the installed figure, every
assert of the blocks and of make.py against the earlier round's, the owner's rules, the picture at full and half size).
No word or number is false or unasserted, and no assert that guards a fact is gone; the People count is the review
file's own (5,117 records at this build; the installed preview's 5,024 was the file of that morning). Three places set
right, no word touched. The two dashed frames of a and b's dashed edge are drawn a side at a time, each side from its
two ends to its middle, so every corner and both ends of b's edge are whole dashes (as one dashed rectangle, three
corners of the new 'After reading' frame fell in a gap of the dashes and stood open, and b's edge ended in a gap). In
b's Convert card the printed 126 ± 6 stands on the left edge of the 126 s^-1 under it and of CatLog's value (it stood
0.8 pt to their right; the values' column of all four cards is now 5.0 pt after the widest name box, it was 4.2). In
b's Read card the two rows of print end on one right edge (they ended 0.7 pt apart). Reverting R5's two judgement
calls (a's grey band, b's full frame) takes more than the one line R5's note says: the asserts on the frames in
new_checks.py and, for the band, the neutral fills of check.py go back with them. 169.0 mm.
R6 (10 Nov, evening, the main chat's own pass over the round's result; the reader-clarity designer's proposals, which
the builder never saw, merged with it). a: 'After reading' is its words alone, on the Flag's left edge and on the
line of 'Blind to databases and reviews': the dashed frame round the two (R5) stood 5 pt outside the grid's right edge,
the one thing in the figure that did, and a second dashed frame made the blind steps' frame, which b enlarges, one of
two; the frame is now the blind steps' alone. b: the line that says what a card's rows are reads 'each example shows
what the paper prints, what a database wrongly lists and what CatLog stores' (the owner asked why a database is named
in b: because it lists that printed value wrongly). c: the count of values stands on the steps' line, a fourth arrow
from Check to it, and 'from 7,514 papers so far' under it on the steps' names' line (7,514 under 75,221 papers read
as one paper in ten giving values); '+ 20,961 printed as not detected' ('not detected' alone could be read as values
CatLog missed); in the record 'signal peptide adds 22' and the residue's dot in the stored green of N270A under it.
d: the clause's line 'skip a column copied from older work' (the clause of 14 Oct says column; one word, copied,
through all four steps) and '80 papers lose 973 copied values / a second check keeps 165 others'.
P1 (11 Nov, the owner on the installed figure, which has no worked examples: the stores "as in a database vibe", as the
earlier version drew them; "from papers to values, the paper segment isn't there a lot of empty space"; "we are writing
read convert verify [check] twice"; "are we missing something? Fundamental inner architecture"). a: CatLog is a cylinder
in its box's footprint (the catalogue's tint, its green outline at 1 pt, its name on the line of the steps' names), and
the databases are one navy cylinder over Decide that holds the six names in two rows (no card, no strip, no name
boxes), its lid as tall as CatLog's; the top row is 5 pt taller for it and the cylinder stands 8.5 pt over the row. Each step box says who does what in two lines (an agent copies each printed
cell; code computes every value; a second agent finds it again; code checks every value); Decide's icon and name stay
on the steps' lines. c: no step tiles; Papers and CatLog are of one make (title, a row, a hairline, a row), the two
sources side by side, CatLog's count on one line with the small cylinder in the catalogue's green.
Q1 (11 Nov, the owner: "Yes, move it"). The databases' cylinder stands over the Flag box, on its two side edges, and its
navy arrow drops from the middle of its foot into the middle of the Flag's top (it entered Decide; two first-time readers
read that as the databases helping to decide, against 'from the paper'). The arrow crosses the errors line and the
corrections line at right angles; 'corrections' stands between the arrow and the rise of its own line.
W1 (11 Nov, the owner on idea 2: "no point writing read convert verify check twice - we can include the rule thingy
somehow in a proper [compact] way in part a right? and get rid of part b"; "colearning should have some ai human visual
maybe?"; "c i like but underwhelming"). Three panels. a: each step box has a foot, a hairline in the box's outline
colour and under it the step's count of rules, the number bold ('16 rules'); the step boxes, CatLog, Flag, Decide and
the dashed frame are 7 pt taller for it. The Co-learning box shows a person and an agent side by side before its
title, and its line reads '68 rules in instructions and code'. The panel of four strips, its title, the zoom's lines
and its dashed edge are gone: Read, Convert, Verify and Check are written once. One new glyph, an agent (a plain robot
head: a rounded square, two dots, a short antenna; mint, in the agents' outline colour, the icons' 0.5 pt). b: the
papers-to-values strip drawn large (a pile of pages, one record with its three rows, the catalogue's cylinder with its
name), the counts in 7 pt, the trail as a dashed grey arrow back from the cylinder to the pages. c: the loop; each
box is a strip one line tall, its name at the left and at the right a picture of who acts (person, agent, code's sign).
W1 counts (11 Nov, the owner: "i think use the latest value for now and we will also update in the very end"). The
catalogue's counts in b (papers read, records and the papers they come from, values, not detected, limits, test papers
kept unread) and the legend's date for them are those of writing/fig1_v8/ref/catalogue_counts.json, which
ref/catalogue_counts.py <commit> writes for one data checkpoint; facts() streams that commit's files through git and
asserts its own counts against the file's. A refresh is: run the script with a newer commit, rebuild; no code names a
count. writing/PITCH.md still holds the 3 November numbers: the figure runs ahead of the manuscript on the owner's word
until the final freeze. Nothing else on the figure changed.
W1 review count (11 Nov, the owner: "Yes, use 5,838"). The People box's 'reviewed N records' is the number of records
people checked against their papers, as `catlog.py status` reports it, computed by the status's own functions
(tools/human_review.py _decisions and review_summary, tools/site_release.py _one_review and _review_basis); the records
with no PMID or DOI are not counted, and the legend says how many they are. Nothing else on the figure changed.
W1 review papers (11 Nov, the owner: "why the paper number is fixed? shouldnt it change or sth"; "we use only our catlog
(both for values and paper numbers)"). The People box reads 'reviewed N records' then 'from M papers': M is the number
of distinct papers the N records name in human_review/decisions.jsonl, counted at each build from the rows the status's
functions read, with the status's rule for a record that has a paper (review_summary's has_paper). The number quoted
from the CatRange paper is gone from facts(), the drawing and the legend. Nothing else on the figure changed.
W1 recovered papers (11 Nov): a blind recount confirmed N and M, and found that a few of the N records name no paper in
the review file (records of one review pack whose rows audits had dropped; the reviewer approved them in their copy).
Their papers, each found by two independent routes, are in ref/review_papers_recovered.tsv and are counted in M, so M is
exact; the legend's clause about them is gone.
M2 (11 Nov, the owner on the three versions of b's record: "2 or 3 is looking better to me"; before that, on W1's card:
"maybe we also mention other stuff we add - right? this is oversimplification, no? as in how it connects to multiple
database and grabs data - but more visually showing and less wordish"). Version 2, calmed. b's record is one card of
three cells under a header that holds the records' count: the enzyme (the prepared picture of one real record's UniProt
entry, the slate rendering of structure/, checked in facts(), the residue its paper's variant changes as dark spheres;
beside it one line of that record's stored sequence, seven letters, the changed residue boxed in code's colours), the
three rows kcat, Km, kcat/Km in the middle, and the substrate (that record's stored structure, drawn by RDKit);
hairlines part the cells. Neither is named on the figure; the legend says which record it is. Over the card stand the
sources, six cylinders of ONE size in a's Databases make, a name each at 5.5 pt (UniProt, PDB, NCBI; Rhea, ChEBI,
PubChem: facts_m2, asserted against tools/sequences.py, tools/structures.py, tools/ids.py and the export): each three
exactly over its cell, so the row is as wide as the card and nothing stands over the values. Each three meet in one
small box of code's fill with code's sign under their middle cylinder (the outer two by equal square-cornered legs),
and from each box one navy arrow of the figure's make (0.75-pt shaft, 9 pt long) drops onto the card's top line over
the middle of its cell; the header's count is centred between the two heads. Added words: the six names and one line
of seven sequence letters; no number added; the card is 39 pt tall (its cells 30 pt, as the pile and the cylinder, which
stand beside them on one foot line), the two black arrows as long as a's between its steps, b 30.0 mm tall (W1's 19.3
and 10.7 more; the allowance is 11); a and c are untouched (c stands lower).
M2 final check (12 Nov, an independent checker before M2 is installed): the header's line had 0.35 pt to spare beside
the navy arrowheads, less than one more digit, and the counts are refreshed at the freeze. The values' cell is 3 pt
wider (4.0 -> 5.5 pt of white each side of its rows), the count stands 2.5 pt from its papers (4.0) and an object's
words 4.5 pt from it (6.0), so the two black arrows keep their length; nothing else moved. The legend no longer says
code adds the enzyme's entry and the structure to every record: it looks both up for every record and adds them where
it finds them.
FINAL PASS (16 Nov 2026; the owner: finish everything for the handoff, after Fig. 1 had been parked since 11 Nov; the
list in work/fig1_rework_20261110/HANDOFF.md, 'LAST PASS'). Counts: every count drawn comes from the paper's freezes.
b's catalogue counts are paper/evidence/catalog_freeze_20261116/catalogue_counts.json (git tag
paper-catalog-freeze-20261116), recounted here from the tag, the records with whole rows (ref/catalogue_counts.py had
kept only the identity fields and so counted 884 records too many there); the People box is
paper/evidence/human_review_freeze_20261116/numbers.json, recounted from that freeze's own review file; the catalogue's
data files the facts read are the tag's, the export the freeze's copy. Rules: the feet count Fig. 4a's 73
(writing/figures/fig4/v2/evidence/rules/rules.csv by step): Read 16, Convert 12 (two rules written after the list of
2 November: figure captions, and drawn structures in table cells), Verify 7, Check 35, and a new foot on Decide, the
database check's 3, so the five add up to the Co-learning box's 73. Words: c's second step 'A rule is written' (the
owner: an agent drafts each rule and an author approves it; both icons kept); b's padlock line '343 kept unread for
the test' (the locked test has run, so 'a later' goes; the pass first wrote 'held out for the test', which its check
showed to clash with the legend and the Methods, where 'held out' names all 369 test papers). Arrows (writing/research/fig1_review/ARROWS_20261111.md, its seven changes; its three
owner decisions left as they are): the corrections leave Decide's foot and run under the Flag into CatLog's base, at
the level of the line into Verify, their word under the run; the right-hand 'errors' over its line at Decide's end;
'agent findings' for 'findings', on two lines; the databases' cylinder 2 pt higher and the errors line 0.5 pt higher;
the line into Verify 1.7 pt lower and the frame's foot 2.9 pt lower; a 1-mm opening in the dashed frame round each line
that crosses it, a whole dash under the rules head; b's trail words on the run left of the record. The record's cells,
the pile and b's cylinder 31.5 pt tall (the structure had 0.6-0.7 mm to its cell's lines), the room taken from under
the card, so b keeps its height. The legend draft follows (the freezes as sources, Fig. 4a's split of the rules, the
padlock's papers, 'an agent drafts it and an author approves it', the PDB route, the code sign). Look, layout, fonts
and colours are otherwise as approved; no .ai or PDF is made here.
Facts: every number drawn is a value of F from facts(), asserted against its file. Reads the repository only (git only
to read the freeze's tag); writes OUT + '_preview.png' (here fig1_v8_preview.png) and the legend draft into this folder,
and the SVG to FIG1_SVG_OUT (never the repository) when that is set. While the working tree's catalogue files differ
from the tag's, the tag's copies are written to a temporary folder (TMPDIR) and removed at exit.
Run: python3 -I -B build.py   (about 45 s and some 2 GB: it groups the frozen catalogue's whole rows and reads the export)"""
import ast, collections, csv, datetime, inspect, json, math, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = '<the CatLog folder>'
assert os.path.exists(os.path.join(ROOT, 'catlog.py')), ROOT
OUT = 'fig1_v8'
MM = 72 / 25.4
MARGIN = 5.0                # pt (1.76 mm) of white round the art on every side: nothing touches the page edge
W = 183 * MM - 2 * MARGIN   # the art's width; the page is 183 mm
HMAX = 170 * MM - 2 * MARGIN
FONT = 'Arial'
# Arial's faces by PostScript name (bold, italic): cairosvg, Quick Look and Illustrator then pick the same face, and
# the Illustrator route (unify_svg.py) reads the face from font-family alone
PS = {(False, False): 'ArialMT', (True, False): 'Arial-BoldMT', (False, True): 'Arial-ItalicMT', (True, True): 'Arial-BoldItalicMT'}
LETTER = 8
f2 = lambda v: f'{v:.2f}'.rstrip('0').rstrip('.')


# ------------------------------------------------------------------ final pass (16 Nov): the paper's freezes
# The owner, 16 Nov 2026, of the catalogue: "for the paper writing here is the freeze"; of people's review: "wrap for
# paper data report freeze". Every count the figure draws comes from a freeze:
#  - the catalogue: git tag paper-catalog-freeze-20261116 (paper/evidence/catalog_freeze_20261116/FREEZE.md). b's counts
#    are that folder's catalogue_counts.json, which this build reads (FREEZE_COUNTS) and recounts from the tag with
#    whole rows. writing/fig1_v8/ref/catalogue_counts.py, whose file the build read until this pass, kept only the
#    identity fields of each row, so join_lines (which works from each value's quoted line) joined nothing and it
#    counted 884 records too many at the tag (FREEZE.md, "Counting at the snapshot"); the script now keeps whole rows;
#  - people's review: paper/evidence/human_review_freeze_20261116/numbers.json (REVIEW_DIR; FREEZE.md there);
#  - the rules: Fig. 4's evidence (writing/figures/fig4/v2/evidence/rules/rules.csv, its cut of 15 Nov 00:30).
# The catalogue's data files that facts() reads (the catalogue, its refused rows and bounds, the log, the papers, the
# database checks and the provenance backfill) are read as the tag holds them (FROZEN_AT_TAG: the working tree's file
# when it is the tag's, else the tag's copy through git in a temporary folder), and the export and the database table
# from the freeze's own copies (FROZEN_COPIES, each checked against its sha256 in the freeze's record), so a later batch
# can neither move a fact nor stop the build. Code and notes (prompts, tools, CLAUDE.md) are read from the working tree.
FREEZE_DIR = os.path.join(ROOT, 'paper', 'evidence', 'catalog_freeze_20261116')
FREEZE_COUNTS = os.path.join(FREEZE_DIR, 'catalogue_counts.json')
REVIEW_DIR = os.path.join(ROOT, 'paper', 'evidence', 'human_review_freeze_20261116')
FREEZE_TAG = 'paper-catalog-freeze-20261116'
CK0 = json.load(open(FREEZE_COUNTS, encoding='utf-8'))['checkpoint']   # the tag's commit, as the counts file names it
GENV0 = dict(os.environ, GIT_OPTIONAL_LOCKS='0')                       # git only reads: not even an index refresh
assert subprocess.run(['git', '-C', ROOT, 'rev-parse', FREEZE_TAG + '^{commit}'], capture_output=True, text=True, check=True,
                      env=GENV0).stdout.startswith(CK0), (FREEZE_TAG, CK0)
FROZEN_AT_TAG = {'catalog.jsonl', 'rejected.jsonl', 'bounds.jsonl', 'log.tsv', 'papers.tsv', 'sources/database_corrections.tsv',
                 'sources/provenance_backfill.tsv', 'sources/coverage.tsv', 'sources/holdout_locked.txt',
                 'sources/blind_reread.txt', 'sources/natural_forms.tsv'}
FROZEN_COPIES = {'catlog_wide.jsonl': 'work/paper_freeze_20261116/catlog_wide.jsonl.gz',
                 'sources/db_values.tsv': 'work/paper_freeze_20261116/db_values.tsv.gz'}
_SHA_FROZEN = {}
for _ln in open(os.path.join(ROOT, 'work', 'paper_freeze_20261116', 'SHA256_originals.txt'), encoding='utf-8'):
    if _ln.strip():
        _h, _f = _ln.split(None, 1)
        assert _SHA_FROZEN.setdefault(_f.strip(), _h) == _h, _f
_FREEZE_MD = open(os.path.join(FREEZE_DIR, 'FREEZE.md'), encoding='utf-8').read()
assert all(_SHA_FROZEN[f_] in _FREEZE_MD for f_ in FROZEN_COPIES), 'the copies\' hashes are the freeze record\'s'
_FROZEN, _TMP = {}, []


def _sha256(path):
    import hashlib
    h_ = hashlib.sha256()
    with open(path, 'rb') as fh_:
        for b_ in iter(lambda: fh_.read(1 << 22), b''):
            h_.update(b_)
    return h_.hexdigest()


def _tmpdir():
    if not _TMP:
        import atexit, shutil, tempfile
        _TMP.append(tempfile.mkdtemp(prefix='fig1_freeze_'))
        atexit.register(shutil.rmtree, _TMP[0], True)
    return _TMP[0]


def frozen(rel):
    """The path to read rel from, as the freeze holds it (see above)."""
    if rel not in _FROZEN:
        live = os.path.join(ROOT, rel)
        if rel in FROZEN_AT_TAG:
            same_ = os.path.exists(live) and subprocess.run(['git', '-C', ROOT, 'diff', '--quiet', CK0, '--', rel],
                                                            env=GENV0).returncode == 0
            if not same_:
                path_ = os.path.join(_tmpdir(), rel.replace('/', '__'))
                with open(path_, 'wb') as fh_:
                    subprocess.run(['git', '-C', ROOT, 'show', f'{CK0}:{rel}'], stdout=fh_, check=True, env=GENV0)
                live = path_
        else:
            if not (os.path.exists(live) and _sha256(live) == _SHA_FROZEN[rel]):
                import gzip, shutil
                path_ = os.path.join(_tmpdir(), rel.replace('/', '__'))
                with gzip.open(os.path.join(ROOT, FROZEN_COPIES[rel]), 'rb') as src_, open(path_, 'wb') as dst_:
                    shutil.copyfileobj(src_, dst_, 1 << 22)
                assert _sha256(path_) == _SHA_FROZEN[rel], rel
                live = path_
        _FROZEN[rel] = live
    return _FROZEN[rel]


def P(*parts):
    rel = '/'.join(parts)
    if rel in FROZEN_AT_TAG or rel in FROZEN_COPIES:
        return frozen(rel)
    return os.path.join(ROOT, *parts)


# ------------------------------------------------------------------ Arial metrics (v3's wid, from the system's Arial)
def _metrics():
    from fontTools.ttLib import TTFont
    out = {}
    for key, fn in (('n', 'Arial.ttf'), ('b', 'Arial Bold.ttf'), ('i', 'Arial Italic.ttf'),
                    ('bi', 'Arial Bold Italic.ttf')):
        f = TTFont('/System/Library/Fonts/Supplemental/' + fn)
        out[key] = (f.getBestCmap(), f['hmtx'], f['head'].unitsPerEm)
    return out


_M = _metrics()


def wid(s, size, bold=False, italic=False):
    cmap, hm, upm = _M[('b' if bold else 'n') if not italic else ('bi' if bold else 'i')]
    return sum(hm[cmap[ord(c)]][0] for c in s) / upm * size


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ------------------------------------------------------------------ colours: Nature BPG (ggsci NPG), one meaning each
def flat(hex6, a=0.32):
    """An NPG colour at alpha a over white, as one opaque colour (the skill's #RRGGBB99 fill, flattened)."""
    c = [int(hex6[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(a * v + (1 - a) * 255):02X}' for v in c)


TXT = '#000000'          # text (R4: black, as a journal sets type; it was #3C3C3C)
INK = '#000000'          # outlines of things and icons, arrows (R4: black; it was #262626)
GREY = '#666666'         # R5: 60% black (the editor: 50% grey at these weights prints faint and uneven). R4: the one grey of neutral lines. dashed frames; the neutral outline of a box that more than one role works in
OPEN = '#8C8C8C'         # b: a kind of failure that is still open (no rule yet)
RULE = GREY              # thin rules (R4: #BDBDBD at 0.4 pt drops out in print)
BAND = '#F2F2F2'         # the after-reading bands
NPG = dict(red='#E64B35', cyan='#4DBBD5', green='#00A087', navy='#3C5488', salmon='#F39B7F', slate='#8491B4',
           mint='#91D1C2', darkred='#DC0000', brown='#7E6148', tan='#B09C85')
ROLE = {   # role: (fill, edge). Agents mint, code slate, people tan; things white: the catalogue with a green edge, the
    # error ledger (a record compiled after the fact, not an actor) with an ink edge (v4 CHECK.md A16)
    'agent': (flat(NPG['mint']), '#4E9C8B'),
    'code': (flat(NPG['slate']), '#5D6A92'),
    'people': (flat(NPG['tan']), '#8A7660'),
    'ledger': ('#FFFFFF', INK),
    'catalog': ('#FFFFFF', NPG['green']),
    'db': ('#FFFFFF', NPG['navy']),
}
GREEN, NAVY = NPG['green'], NPG['navy']
GREEN_TXT = '#00785F'    # "CatLog" set in words on white: the catalogue green, a shade darker
LEARN = '#2E9BB7'        # Q2: learning (errors in, findings and rules out, d's loop): NPG cyan's edge shade
OUT_GREY = '#B3B3B3'     # Q2: the one arrow that leaves the method (to the database errors of Fig. 4; P1: not drawn)
DB_TINT = flat(NAVY, 0.40)   # P1: the Databases card's strip, #B1BBCF (alternative 3's tint; CIELAB dE 11 from code's fill)
RED = NPG['red']         # S1: errors, and only errors (the owner: "use that red color for the errors part")
RED_TINT = flat(RED, 0.13)   # S1r: the surface of what holds errors (a's Flag box, d's errors step), red as a fill
#                              (the editor: "use red as a surface wherever errors are"); #FCE8E5, light as the role fills
TICK_GREY = '#BDBDBD'    # S1: b's rules not shown (the shown one's tick is ink)
# S1r (the editor: "make the catalogue stand apart from the agents"): both CatLog boxes filled in the catalogue's own
# dark green (#00785F, the green CatLog's name is set in), title and counts in white, so green no longer reads as mint
CAT_SOLID = False         # T1: no longer solid (the owner: "any other color from npg palette that we can use here like
#                           the people one maybe (for catlog) to make it less color ish")
CAT_FILL = '#00785F'
# T1: the catalogue as the People box is drawn, a light tint of its colour with a darker edge and title. Its colour stays
# NPG green, the one the record in c, its title and its curve already carry: every other NPG colour has its meaning
# (red errors, cyan learning, mint agents, slate code, tan people), and the rest read as one of those (salmon as red,
# navy as code's slate, brown as people's tan). At the role fills' alpha (0.5) green is mint; at 0.12 it stays lighter than
# the agents' mint (L* 95 against 90, a CIELAB difference of 7; 0.15 left 5), and its edge, the saturated green at 0.75 pt
# in both boxes, is not the agents' muted teal
CAT_TINT = flat(NPG['green'], 0.12)      # #E0F4F1
# T1 round 2 (the editor: with three blue-greens side by side, "CatLog reads as one more agent box rather than the
# product"): its two boxes keep the tint, the lightest fill of the figure, and take a 1-pt outline in the saturated green
# (the steps' outlines are 0.6 pt in their muted edges; the record in c keeps 0.75), so the catalogue stands apart by
# weight as well as by hue
CAT_SW = 1.0
ON_GREEN = '#FFFFFF'     # words on the catalogue green (5.4:1)
ON_GREEN2 = '#D5EEE8'    # the second rank of words on it (4.4:1): what CatLog keeps beside its values
# S1: the structure picture (AlphaFold DB AF-P00805-F1 v6, PyMOL; files and licence in structure/)
ASSETS = os.path.join(HERE, 'structure')               # the AlphaFold entry and its render records (structure/README.md)
# S1r (the editor: "draw it one shade darker in slate"): re-rendered from the same entry file in NPG slate, residue 270
# in ink at 1.2x its van der Waals radii; picture and provenance in this folder (the assets' picture is kept as it was)
# T1 round 2 (the editor: the slate ribbon "is the heaviest object in the box ... drawn in the code colour, so it reads as
# code"; "draw the cartoon in light grey ... so the dark residue sphere stands out"): re-rendered from the same entry file
# and view in light grey (#D6D6D6, outline #8C8C8C), residue 270 in ink as before; the slate picture stays in structure/
# M2 (11 Nov): the slate picture again (at b's 34 pt the light grey one is pale; slate is code's colour)
STRUCT_PNG = os.path.join(HERE, 'structure', 'P00805_AF_v6_N270_slate_600.png')     # the copy embedded in the SVG
STRUCT_PROV = os.path.join(HERE, 'structure', 'P00805_AF_v6_N270_slate.provenance.json')
STRUCT_SHA = '5b5ba2995c2fce9443adaecd83d98c266400b5ebd5b347fccd783d05148bb58f'
T7, TT, T6, T55, T5 = 7.0, 7.0, 6.5, 6.5, 6.0      # V1: panel and card titles 7 pt; text 6.5 pt; column heads 6 pt
ES = lambda size: 5.5 if size >= 6.5 else 5.0      # V1: sub- and superscripts 5.5 pt on 6.5-pt text
HL, HW, SHAFT = 3.8, 3.2, 0.75                       # arrowheads 1.87 mm long, 1.55 mm wide; shafts 0.8 pt
RC = 1.2                                            # corner radius of b's cards
STRIP = 12.0                                        # height of b's title strips
TITLE_X = 17.0                                      # a card title's inset (clear of its 9-pt icon)
PAD = 6.0                                           # text inset in a card
LS = 6.4                                            # line step, 5.5-pt text
LSB = 6.7                                           # b's lists: room for a subscript over the next line's capitals


# ------------------------------------------------------------------ facts: everything the art states, checked here
TAXONOMY = ('paper', 'figures', 'method_overview', 'v5', 'taxonomy.tsv')


def txt(*parts):
    return open(P(*parts), encoding='utf-8').read()


def facts():
    """The numbers, names and mechanisms the art shows, each checked against its file. Returns (F, S): values and
    their sources (S goes into the README)."""
    F, S = {}, {}
    # ---- a: as v6 (the taxonomy's status column, the audit rate, the database threshold, the six databases)
    tax = {r['id']: r for r in csv.DictReader(open(P(*TAXONOMY), encoding='utf-8'), delimiter='\t')}
    st = collections.Counter(r['status'] for r in tax.values())
    assert len(tax) == 85 and st == {'rule': 71, 'flag kept as printed': 4, 'open': 10}, (len(tax), st)
    F['kinds'], F['rules'], F['flagged'], F['open'] = len(tax), st['rule'], st['flag kept as printed'], st['open']
    S['ledger'] = 'paper/figures/method_overview/v5/taxonomy.tsv: 85 lines; status rule 71, flag kept as printed 4, open 10'
    m = re.search(r'^AUDIT_RATE = ([\d.]+)', txt('catlog.py'), re.M)
    assert m and float(m.group(1)) == 0.07, m
    F['audit_pct'] = '7'
    S['audit'] = 'catlog.py AUDIT_RATE = 0.07 (audit_size, cmd_sample); .claude/workflows/catlog-audit.js'
    assert 'by 1.5x or more' in txt('tools', 'dbcheck.py')
    F['db_fold'] = '1.5'
    S['db_fold'] = 'tools/dbcheck.py: dbdiff writes a paper check for every value that "differs by 1.5x or more"'
    src = txt('tools', 'dbcompare.py')
    sources = ast.literal_eval(re.search(r'^SOURCES = (\([^)]*\))', src, re.M).group(1))
    seen = set()
    with open(P('sources', 'db_values.tsv'), encoding='utf-8') as fh:
        for row in csv.DictReader(fh, delimiter='\t'):
            seen.add(row['source'])
    assert seen == set(sources) == {'BRENDA', 'SABIO-RK', 'OED', 'SKiD', 'STRENDA', 'UniProt'}, seen
    F['db_names'] = ['BRENDA', 'SABIO-RK', 'OED', 'SKiD', 'UniProt', 'STRENDA DB']
    S['db_names'] = 'tools/dbcompare.py SOURCES; sources/db_values.tsv source column'
    # P1: a's Databases card. Its six names are the sources the values are compared with ('STRENDA' is STRENDA DB, CLAUDE.md);
    # the comparison runs after reading, on verified rows; readers and verifiers never open database values; the agent that
    # checks a difference is given the database rows and decides from the paper, never changing a value (its arrow ends in
    # Decide); its verdicts stay in CatLog (sources/database_corrections.tsv, the website), so no arrow goes back to the card
    assert sorted(n_.replace(' DB', '') for n_ in F['db_names']) == sorted(sources), F['db_names']
    dbm0_ = re.sub(r'\s+', ' ', txt('prompts', 'dbcheck.md'))
    assert ("CatLog read this paper blind: an AI reader, a separate AI verifier and code that converts every printed cell. "
            "Then code compared CatLog's values with the enzyme databases (BRENDA, SABIO-RK, OED, SKiD, STRENDA, UniProt) for "
            "the same paper.") in dbm0_
    assert "`databases`: the database rows that differ, each with its `number` exactly as the database lists it" in dbm0_ \
        and 'the task file holds every database row you need, and the paper decides' in dbm0_ and 'You never change a value' in dbm0_ \
        and 'records them in `sources/database_corrections.tsv`, and the website then says, per value, what the check found' in dbm0_
    dbk0_ = re.sub(r'\s+', ' ', txt('tools', 'dbcheck.py'))
    assert 'this runs after `add`, on verified rows' in dbk0_ and "A task file names database numbers, so it is never a reader's input" in dbk0_ \
        and ('its row goes to work/audit_priority.txt, which `catlog.py sample` takes first, so the next /audit re-checks it '
             'against the paper') in dbk0_
    for f_, w_ in (('read.md', 'Read blind: use only this paper'), ('verify.md', 'Check blind: use only this paper')):
        p0_ = re.sub(r'\s+', ' ', txt('prompts', f_))
        assert w_ in p0_ and 'Never open database values' in p0_ and '`work/dbcheck_*`' in p0_, f_
    S['db_card'] = ('prompts/dbcheck.md ("Then code compared CatLog\'s values with the enzyme databases (BRENDA, SABIO-RK, OED, '
                    'SKiD, STRENDA, UniProt) for the same paper"; the task\'s `databases` rows; "You never change a value"); '
                    'tools/dbcheck.py ("this runs after `add`, on verified rows"); prompts/read.md and verify.md ("Never open '
                    'database values", `work/dbcheck_*`)')
    del dbm0_, dbk0_, p0_
    sys.path[:0] = [ROOT, P('tools')]
    sys.dont_write_bytecode = True                  # no __pycache__ outside this folder
    import catlog, units, fetch                     # CatLog's own code; importing it reads config.json only (U1: here,
    #                                                 before the Flag's facts, which read catlog.cmd_sample)
    # ---- S1, fix 8 (the owner: "the flag segment reads a bit AI-ish ... clever and scientifically clean icon"): the five
    # sources of a flag, each with a small line icon in the colour of who raises it, red only on what is suspect
    # 1 people's review (people): a reviewer's rejection is audited from the paper by an agent, never obeyed as it stands
    hr0_ = re.sub(r'\s+', ' ', txt('HUMAN_REVIEW.md'))
    assert 'each one is settled by an AI audit or a check against the paper' in hr0_ \
        and 'a rejection is audited, not obeyed' in hr0_ and 'rejected: an audit, never an automatic drop' in hr0_
    # 2 kcat, Km and kcat/Km disagree (code): the export's ratio check (1.5x widened by the printed uncertainties; noted,
    # nothing dropped) and the scale sweep; agents decide from the paper, 3 refuters to a unit change (asserted below)
    rc0_ = re.sub(r'\s+', ' ', txt('catlog.py').split('def ratio_check(by):', 1)[1][:900])
    assert '(ok, text) for one measurement with printed kcat, Km and kcat/Km: they agree within 1.5x, widened by the ' \
           'printed uncertainties' in rc0_ and 'A disagreement drops nothing' in rc0_
    assert txt('tools', 'scale_sweep.py').startswith('"""Measurements whose printed kcat/Km misses kcat ÷ Km by a unit factor')
    # 3 printed in an earlier paper too (code; until U1 'reprinted value'): the reprint scan lists papers sharing printed
    # cells; agents check them cell by cell
    rp0_ = re.sub(r'\s+', ' ', txt('tools', 'reprint_pairs.py'))
    assert 'two catalog papers sharing MIN or more identical specific printed cells' in rp0_ \
        and 'A list to check against the papers, never evidence' in rp0_
    # 4 picked for a random 7% audit (agents; code draws the 7% sample, at least 12): AUDIT_RATE above, audit_size
    assert 'return max(12, math.ceil(AUDIT_RATE * values_since_audit()))' in txt('catlog.py')
    # 5 a database differs >=1.5-fold (code writes the paper check; an agent checks the paper and never changes a value)
    assert 'You never change a value' in txt('prompts', 'dbcheck.md')
    # S1r (the editor: one style, no clip-art; the rate where there is one; the trigger, not the source): every icon in
    # ink with red only on what is suspect, the audit with its rate; people's review raises a flag when a reviewer
    # rejects a value (HUMAN_REVIEW.md, asserted above: the rejection is audited from the paper, not obeyed)
    # U1 (7 Nov, the owner: "the reprinted value in the flag, what does that mean?"): each line says what raises its flag.
    # The reprint scan pairs a later paper with an earlier one whose printed cells, or whose database values, it repeats
    # ('printed in an earlier paper too'); the audit's values are drawn at random ('picked for a random 7% audit'); 'a
    # database differs' cannot be read as 'taken from a database'
    assert 'Writes work/reprint_pairs.tsv (kind, later, earlier, shared, examples)' in rp0_ \
        and 'values that a database lists for an EARLIER paper' in rp0_
    assert 'random.sample(' in inspect.getsource(catlog.cmd_sample)
    # U1 round 2 (the editor: 'printed in an earlier paper too' did not say what is wrong; the owner's question was what
    # 'reprinted value' means): what raises the flag in the plainest words that fit the box's line, 'same value in an older
    # paper' (the scan's trigger: the same printed values in a catalogue paper or a database's entry for an EARLIER
    # paper). b's first Read rule and d's first error say the rest with one word, 'copied'
    assert 'two catalog papers sharing MIN or more identical specific printed cells' in rp0_   # the same values
    F['flag_items'] = [('people', 'person', 'rejected by a reviewer'), ('code', 'ratio', 'kcat, Km and kcat/Km disagree'),
                       ('code', 'reprint', 'same value in an older paper'),
                       ('agent', 'die', f"picked for a random {F['audit_pct']}% audit"),
                       ('code', 'fold', f"a database differs ≥{F['db_fold']}-fold")]
    S['flag'] = ('HUMAN_REVIEW.md (a rejection is audited, not obeyed); catlog.py ratio_check (1.5x widened, nothing '
                 'dropped) and tools/scale_sweep.py; tools/reprint_pairs.py (papers sharing printed cells with an earlier '
                 'paper, or values a database lists for an earlier paper: the same value in an older paper; a list to '
                 'check, never evidence); catlog.py AUDIT_RATE 0.07, audit_size at least 12; tools/dbcheck.py 1.5x, '
                 'prompts/dbcheck.md "You never change a value"')
    del hr0_, rc0_, rp0_

    # ---- b: inside reading one paper
    read, verify, wf = txt('prompts', 'read.md'), txt('prompts', 'verify.md'), txt('.claude', 'workflows', 'catlog-batch.js')
    # what the reader receives
    assert 'Input: `texts/<PMID>.txt` plus, if it exists, `texts/<PMID>.supp.txt`' in read
    assert 'If the text starts with `GLYPH WARNING`' in read and 'pdftoppm -r 200' in read
    assert "return ('GLYPH WARNING: the text layer of this PDF shows " in inspect.getsource(fetch.glyph_warning)
    S['inputs'] = ('prompts/read.md lines 3-4 (texts/<PMID>.txt, texts/<PMID>.supp.txt), "If the text starts with '
                   '`GLYPH WARNING`" (pdftoppm -r 200 page images); tools/fetch.py glyph_warning, two_points')
    # the one cell: read.md's own example of a text layer that draws a superscript minus as '21' and a ± as '6'
    assert '`38466.2 min21` is fine as the quote of `384 ± 6.2` min^-1' in read
    assert any(re.search(rx, '38466.2 min21') for rx in fetch.GLYPH_SIGNS.values())   # 'min21' sets the warning line
    S['cell'] = ('prompts/read.md: "`quote` stays the text-layer copy (`38466.2 min21` is fine as the quote of `384 ± '
                 '6.2` min^-1)"; fetch.GLYPH_SIGNS matches "min21" (a superscript minus as 21)')
    # the reader's fields, which code requires
    for f in ('metric', 'raw_value', 'raw_unit', 'quote', 'location'):
        assert f'"{f}"' in read and f in catlog.NEEDED, f
    assert 'Output: write `work/<PMID>.read.json`' in read
    S['fields'] = 'prompts/read.md "Each row" and "Output"; catlog.NEEDED'
    # code converts the cell, and add's check accepts it with its text-layer quote (the ± drawn as '6' counts)
    assert units.TIME['min'] == 60.0
    assert units.normalize('kcat', '384 ± 6.2', 'min^-1') == (6.4, 's^-1', None)
    row = dict(enzyme='E', variant='wild type', substrate='S', metric='kcat', raw_value='384 ± 6.2', raw_unit='min^-1',
               location='Table 2', quote='38466.2 min21')
    norm, bad = catlog.check(row, catlog.squash('Table 2 38466.2 min21'))
    assert norm == {'value': 6.4, 'unit': 's^-1'} and bad == [], (norm, bad)
    F['value'] = '6.4'
    S['convert'] = ("tools/units.py normalize('kcat', '384 ± 6.2', 'min^-1') = (6.4, 's^-1'); TIME['min'] = 60; "
                    "catlog.check on that row and quote: value 6.4 s^-1, no failure")
    # the verifier: three verdicts that echo their row, and a file for what the reader skipped (checked again)
    for v in ('`confirm`', '`fix`', '`reject`'):
        assert v in verify, v
    assert 'Output: `work/<PMID>.verify.json`, plus `work/<PMID>.missed.read.json`' in verify
    assert "copy that row's `metric` and `raw_value` into it exactly" in verify
    assert "verify(pmid, '.missed', model)" in wf
    # Q1 (a's junction dots: Verify gets the page images as well as the text): verify.md checks numbers on them
    vs_ = re.sub(r'\s+', ' ', verify)
    assert 'check every number, ±, unit prefix (µ vs m) and exponent on the rendered page image' in vs_ \
        and 'Confirm the sign and power of any header multiplier on the rendered page image' in vs_
    del vs_
    S['verify'] = ('prompts/verify.md (Verdicts; Output; "copy that row\'s `metric` and `raw_value` into it exactly"); '
                   "catlog-batch.js verify(pmid, '.missed', model)")
    # catlog.py add: the quote, the files' order, the verdict's echo, one value per slot, the two files, the stamp
    assert "'quote_not_in_paper'" in inspect.getsource(catlog.check)
    stl = inspect.getsource(catlog.stale)
    assert 'changed after' in stl and 'read again' in stl and 'verify again' in stl
    assert 'was for {v.get(\'metric\')} {v.get(\'raw_value\')}, not this row' in inspect.getsource(catlog.judge)
    assert 'one current value per slot' in inspect.getsource(catlog.slot)
    ap = inspect.getsource(catlog.append_rows)
    assert 'conflicts with accepted row' in ap and 'review which is right' in ap
    assert (catlog.CATALOG.name, catlog.REJECTED.name, catlog.LOG.name) == ('catalog.jsonl', 'rejected.jsonl', 'log.tsv')
    F['stamp'] = ('reader_model', 'verifier_model', 'read_prompt', 'verify_prompt', 'pipeline_commit')
    assert set(F['stamp']) <= set(catlog.STAMP), catlog.STAMP
    S['add'] = ('catlog.py check (quote_not_in_paper), stale (text < read < verify by mtime, else refused), judge (a '
                'verdict naming another metric or raw_value is void), slot and append_rows (one value per slot; '
                'a different value is a conflict, rejected "review which is right"), STAMP')
    # the lanes: 6 papers at a time, each agent in a scratch folder of its own, one retry on Sonnet
    assert 'parseInt(args && args.lanes, 10) || 6' in wf
    assert "(await step('sonnet'))" in wf
    assert 'named ${role}-${pmid}' in wf and "SCRATCH('read', pmid)" in wf
    assert "SCRATCH(which ? 'verify-missed' : 'verify', pmid)" in wf
    S['lanes'] = ("catlog-batch.js: LANES = parseInt(args.lanes) || 6; again(): a step that returns nothing or a problem "
                  "runs once more with model 'sonnet'; SCRATCH(role, pmid): a folder <role>-<PMID>")

    # ---- c: the whole system
    claude, pitch = txt('CLAUDE.md'), txt('writing', 'PITCH.md')
    assert 'BRENDA 2026.1' in claude and 'STRENDA DB' in claude and 'Europe PMC search' in claude
    cfg = __import__('json').loads(txt('config.json'))
    for s in ('sources/db_citations.txt', 'sources/old_catalog_pmids.txt', 'sources/strenda_pmids.txt',
              'sources/cited_not_queued.txt', 'sources/discovered_europepmc_20261014.txt'):
        assert s in cfg['sources'], s
    for f in ('brenda_values.py', 'sabio_values.py', 'uniprot_values.py', 'strenda_values.py', 'discover_europepmc.py'):
        assert os.path.exists(P('tools', f)), f
    S['sources'] = ('CLAUDE.md "Sources" (BRENDA 2026.1, SABIO-RK, OED, UniProt, STRENDA DB, the Europe PMC search); '
                    'config.json sources; tools/brenda_values.py, sabio_values.py, uniprot_values.py, '
                    'strenda_values.py, discover_europepmc.py')
    g = inspect.getsource(catlog.get)
    for k in ('local_asset(pmid)', "f'europepmc:", "f'pmc_cloud:", "f'elsevier_api:", "f'openalex_oa:",
              "'needs_browser'"):
        assert k in g, k
    assert 'def ocr_pdf' in txt('tools', 'fetch.py') and os.path.exists(P('.claude', 'workflows', 'catlog-chrome-lanes.js'))
    S['routes'] = ('catlog.py get: local copy (the library), europepmc, pmc_cloud, elsevier_api, openalex_oa, '
                   'pubmed_linkout, else needs_browser with a lane (DOWNLOADS.md: Codex, Claude in Chrome or the user); '
                   'fetch.ocr_pdf for scans')
    assert 'def cmd_enrich' in txt('catlog.py') and 'numbering frame' in txt('tools', 'sequences.py') \
        and 'SMILES' in txt('tools', 'structures.py') and txt('tools', 'structures.py').startswith(
            '"""Substrate structure: one neutral, single-component SMILES per catalog substrate')
    S['enrich'] = 'catlog.py cmd_enrich; tools/sequences.py (UniProt accession, numbering frames); tools/structures.py (SMILES)'
    assert "'ratio_check': ratio_check(m)[1]" in txt('catlog.py') and 'def cmd_export' in txt('catlog.py')
    S['export'] = 'catlog.py cmd_export -> catlog_wide; wide(): ratio_check (printed kcat/Km vs kcat ÷ Km, 1.5x widened)'
    assert "'dbdiff':" in txt('catlog.py') and os.path.exists(P('.claude', 'workflows', 'catlog-dbcheck.js'))
    assert os.path.exists(P('.claude', 'workflows', 'catlog-audit.js'))
    for f in ('scale_sweep.py', 'vmax_sweep.py', 'reprint_pairs.py', 'censored_scan.py'):
        assert os.path.exists(P('tools', f)), f
    S['after'] = ('catlog.py dbdiff -> catlog-dbcheck workflow (prompts/dbcheck.md); catlog-audit workflow; '
                  'tools/scale_sweep.py, vmax_sweep.py, reprint_pairs.py, censored_scan.py')
    # R1 (the review: Decide's one 'corrections' arrow made the database flag look like a way to correct CatLog toward
    # the databases): the agent that checks a database difference never changes a value, and most of its verdicts are
    # 'corrected', the paper prints CatLog's value and the database number is wrong; those are Fig. 4. So a carries one
    # arrow out of Decide to "database errors (Fig. 4)". Counted as a share, not a number, since checks keep being recorded
    dbm_ = txt('prompts', 'dbcheck.md')
    assert 'You never change a value' in dbm_ and \
        "`corrected`: the paper prints CatLog's value (CatLog converted it correctly) and the database number is wrong" in dbm_
    vd_ = collections.Counter(r['verdict'] for r in csv.DictReader(open(P('sources', 'database_corrections.tsv'),
                                                                        encoding='utf-8'), delimiter='\t'))
    assert set(vd_) == {'corrected', 'different_measurement', 'ambiguous', 'catlog_wrong'} \
        and 2 * vd_['corrected'] > sum(vd_.values()), vd_
    # FINAL PASS check (16 Nov): in the paper as it stands the database checks' verdicts are Fig. 3g (Fig. 4 is
    # co-learning; paper/manuscript/legends.md, whose 'Fig. 4 | Most database misreadings' this line read until now, is
    # the old drafts' numbering). Fig. 3's README counts them at the freeze, and most are the database's number wrong
    # (misread, or the paper's misprint copied), as the legend says
    f3g_ = re.search(r'^\| g Database values that differ \| the approved picture, at the freeze: ([\d,]+) database values '
                     r'in [\d,]+ papers, .*?\(misread ([\d,]+), copied a misprint ([\d,]+), both right ([\d,]+), the paper '
                     r'does not decide ([\d,]+), CatLog wrong ([\d,]+)\) \|', txt('writing', 'figures', 'fig3', 'v2', 'README.md'),
                     re.M)
    assert f3g_, 'Fig. 3g counts the database checks\' verdicts'
    n3g_ = [int(v_.replace(',', '')) for v_ in f3g_.groups()]
    assert n3g_[0] == sum(n3g_[1:]) and 2 * (n3g_[1] + n3g_[2]) > n3g_[0], n3g_
    S['db_errors'] = ('prompts/dbcheck.md ("You never change a value"; `corrected`: the database number is wrong); '
                      f'sources/database_corrections.tsv verdicts {dict(vd_)}; writing/figures/fig3/v2/README.md row "g '
                      f'Database values that differ": {n3g_[0]:,} values, misread {n3g_[1]:,}, copied a misprint {n3g_[2]:,}')
    del dbm_, vd_, f3g_, n3g_
    # ---- W1 counts (11 Nov, the owner: "i think use the latest value for now and we will also update in the very end"):
    # every catalogue count the figure draws comes from writing/fig1_v8/ref/catalogue_counts.json, which
    # ref/catalogue_counts.py <commit> writes for one data checkpoint (a git commit). Moving the figure to a newer
    # catalogue is: make a data checkpoint, run that script with its commit, rebuild. No code is edited: nothing below
    # names a count, a commit or a date. The build streams the same commit's catalog.jsonl, log.tsv, bounds.jsonl and
    # sources/holdout_locked.txt through git and asserts that its own counts equal the file's (git show, git log and
    # git rev-parse only read; GIT_OPTIONAL_LOCKS=0: not even an index refresh), the records too: it groups the commit's
    # values with CatLog's own grouping code (catlog.measurements, as status and export count them; some 5 s), so a
    # file whose records were counted by an older grouping code stops the build (count check 2, 11 Nov: until then the
    # records were only checked for adding up to the values, and a file two records off still drew).
    # writing/PITCH.md still holds the 3 November numbers (243,749 values of 7,514 papers, the catalogue of 3 Nov 23:41,
    # data checkpoint e06c5d3), to which these counts were pinned until this round: the figure runs ahead of the
    # manuscript on the owner's word until the final freeze, when both are set from one checkpoint.
    # FINAL PASS (16 Nov): that freeze is made. The counts are read from the catalogue's freeze for the paper,
    # paper/evidence/catalog_freeze_20261116/catalogue_counts.json (FREEZE_COUNTS; tag paper-catalog-freeze-20261116),
    # and no longer from writing/fig1_v8/ref/catalogue_counts.json; this build recounts each of them from the tag below,
    # the records with whole rows and the tag's own refused rows and bounds (join_lines reads both), as status counted
    # them at the freeze
    CJ = json.load(open(FREEZE_COUNTS, encoding='utf-8'))
    assert all(type(CJ[k_]) is int and CJ[k_] > 0 for k_ in ('values', 'papers_with_values', 'papers_read', 'records',
                                                             'not_detected', 'limits', 'test_papers', 'test_unread')), CJ
    CK = CJ['checkpoint']
    assert re.fullmatch(r'[0-9a-f]{7,40}', CK) and CK == CK0, CK
    # the freeze's record says the same counts (FREEZE.md and the status of the freeze)
    st_fz = open(os.path.join(FREEZE_DIR, 'status_at_freeze.md'), encoding='utf-8').read()
    assert f"**{CJ['values']:,} values** · **{CJ['records']:,} records** · **{CJ['papers_with_values']:,} papers with values**" in st_fz \
        and f"`{FREEZE_TAG}`, commit `{CK}`" in _FREEZE_MD and f"{CJ['values']:,} values" in _FREEZE_MD \
        and f"{CJ['records']:,} records" in _FREEZE_MD and f"{CJ['not_detected']:,} not detected, {CJ['limits']:,} limits" in _FREEZE_MD, \
        'the counts file and the freeze record agree'
    del st_fz
    F['ck'] = CJ                                    # the file as read: the blocks' asserts compare what is drawn with it
    GENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')

    def at_ck(f):
        """The non-empty lines of f as the checkpoint holds it, streamed (the catalogue is some 400 MB)."""
        with subprocess.Popen(['git', '-C', ROOT, 'show', f'{CK}:{f}'], stdout=subprocess.PIPE, text=True,
                              encoding='utf-8', env=GENV) as p_:
            for ln in p_.stdout:
                if ln.strip():
                    yield ln
        assert p_.returncode == 0, (f, p_.returncode)
    git_ = lambda *a_: subprocess.run(['git', '-C', ROOT, *a_], capture_output=True, text=True, check=True,
                                      env=GENV).stdout.strip()
    assert git_('rev-parse', CK + '^{commit}').startswith(CK), CK
    ck_when = git_('log', '-1', '--format=%ad', '--date=iso', CK)
    assert ck_when == CJ['committed'] and re.fullmatch(r'\d{4}-\d\d-\d\d \d\d:\d\d:\d\d [+-]\d{4}', ck_when), \
        (ck_when, CJ['committed'])
    MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
              'November', 'December']
    F['ck_date'] = f"{int(ck_when[8:10])} {MONTHS[int(ck_when[5:7]) - 1]} {ck_when[:4]}"   # Q1: the legend dates b's counts
    # the values and the papers they come from: one line of the checkpoint's catalog.jsonl per value
    n_ck, pm_ck, rows_ck = 0, set(), []
    # FINAL PASS: whole rows (some 2 GB for a few seconds). The grouping's last step, join_lines, joins the records of
    # one printed line by each value's quote, which the identity fields alone (kept here until this pass) left out
    for ln in at_ck('catalog.jsonl'):
        p_ = re.findall(r'"pmid": "([^"]+)"', ln)
        r_ = json.loads(ln)
        assert p_ == [r_['pmid']], ln[:80]
        n_ck += 1
        pm_ck.add(p_[0])
        rows_ck.append(r_)
    assert (n_ck, len(pm_ck)) == (CJ['values'], CJ['papers_with_values']), (n_ck, len(pm_ck), CJ)
    F['values'], F['papers'] = f"{CJ['values']:,}", f"{CJ['papers_with_values']:,}"
    # the records: counted as status and export count them (catlog.measurements), by the freeze's count and here
    # again; a record holds one, two or three values, so the records by size add up to the records and, weighted, to
    # the values
    rbs_ = {int(k_): v_ for k_, v_ in CJ['records_by_size'].items()}
    assert set(rbs_) == {1, 2, 3} and sum(rbs_.values()) == CJ['records'] \
        and sum(k_ * v_ for k_, v_ in rbs_.items()) == CJ['values'] == n_ck, CJ
    # join_lines also reads the rows kept out of the catalogue (catlog.load_rivals: rejected.jsonl and bounds.jsonl);
    # here the tag's, not the working tree's, which later batches extend
    # The recount needs the freeze's grouping code: while catlog.py is the tag's (it is on 16 Nov), the records are
    # grouped here and must equal the freeze's count; once a later change moves catlog.py, the drawn count stays the
    # freeze's, which this build and the freeze's own status checked, and the build says it did not regroup
    assert CJ['grouping_code_commit'] == git_('log', '-1', '--format=%h', CK, '--', 'catlog.py'), 'the freeze names its grouping code'
    if subprocess.run(['git', '-C', ROOT, 'diff', '--quiet', CK, '--', 'catlog.py'], env=GENV).returncode == 0:
        import pathlib
        rv_old = (catlog.REJECTED, catlog.BOUNDS)
        catlog.REJECTED, catlog.BOUNDS = pathlib.Path(P('rejected.jsonl')), pathlib.Path(P('bounds.jsonl'))
        try:
            meas_ck = collections.Counter(len(m_) for m_ in catlog.measurements(rows_ck))
        finally:
            catlog.REJECTED, catlog.BOUNDS = rv_old
        assert (sum(meas_ck.values()), dict(meas_ck)) == (CJ['records'], rbs_), \
            ('the records of the freeze, grouped by its catlog.py, are not the freeze\'s count',
             sum(meas_ck.values()), dict(meas_ck), CJ['records'], rbs_)
        F['records_regrouped'] = True
        del meas_ck, rv_old
    else:
        F['records_regrouped'] = False
        print('records: catlog.py has changed since the freeze, so the records were not grouped again; drawn: the '
              "freeze's count")
    del rows_ck
    F['records'] = f"{CJ['records']:,}"
    # the last change of the catalogue the checkpoint holds (its log's last add, drop or fix)
    changes = [ln.rstrip('\n').split('\t') for ln in at_ck('log.tsv')]
    last_ck = max(q[0] for q in changes if len(q) > 2 and q[2] in ('add', 'drop', 'drop_bound', 'unitfix', 'cellfix', 'pmfix',
                                                                    'limitfix', 'recover'))
    assert last_ck == CJ['last_change'], (last_ck, CJ['last_change'])
    S['counts'] = (f"paper/evidence/catalog_freeze_20261116/catalogue_counts.json (tag {FREEZE_TAG}, commit {CK} of "
                   f"{ck_when[:16]}, its log's last add, drop or fix {last_ck}): {F['values']} values of {F['papers']} "
                   f"papers in {F['records']} records; the build's own count of git show {CK}:catalog.jsonl gives the "
                   'same values and papers' + (', and the same records (catlog.measurements on whole rows, the tag\'s refused '
                                               'rows and bounds)' if F['records_regrouped'] else ''))
    # ---- H6 (MISSING_COMPONENTS item 3): the bounds CatLog keeps apart from its values (a kcat, Km or kcat/Km the paper
    # prints only as a bound, '< 0.01', '> 50', or as not detected), counted as the values are (one line of the file per
    # value) and at the same checkpoint: its bounds.jsonl, where add keeps the bounds apart from catalog.jsonl
    ck_b = [json.loads(ln) for ln in at_ck('bounds.jsonl')]
    assert all(r['censored'] in ('<', '>', 'not_detected') and r['metric'] in ('kcat', 'Km', 'kcat/Km') for r in ck_b)
    assert catlog.BOUNDS.name == 'bounds.jsonl' and 'apart from the numeric catalog' in inspect.getsource(catlog.append_bounds)
    # checker: most of them are not detected, and most of those print no number at all ('ND', 'n.d.', 'inactive': no
    # limit), so the figure names both, as the manuscript does ("printed only as a bound or as not detected, are kept
    # apart"; its claim check: "A not-detected value without a printed limit is not a bound"). 'bounds' alone misnamed
    # most of them
    kinds_ = collections.Counter(r['censored'] for r in ck_b)
    nd_lim_ = sum(1 for r in ck_b if r['censored'] == 'not_detected' and str(r.get('limit') or '').strip())
    assert (kinds_['not_detected'], kinds_['<'] + kinds_['>']) == (CJ['not_detected'], CJ['limits']) \
        and len(ck_b) == CJ['not_detected'] + CJ['limits'], (kinds_, CJ)
    assert kinds_['<'] and kinds_['>'] and kinds_['not_detected'] > kinds_['<'] + kinds_['>'] \
        and 2 * nd_lim_ < kinds_['not_detected'], (kinds_, nd_lim_)
    ms_ = re.sub(r'\s+', ' ', txt('paper', 'manuscript', 'discussion.md') + txt('paper', 'manuscript', 'discussion_check.md'))
    assert 'printed only as a bound or as not detected, are kept apart' in ms_ \
        and 'A not-detected value without a printed limit is not a bound' in ms_
    F['limits'] = f'{len(ck_b):,}'
    # S1, fix 5 (the owner: "how many not detected or limits is confusing term. We need to easily explain it"): what
    # papers print: 'ND', the commonest not-detected print ('n.d.' is another), and '< 0.01', CLAUDE.md's own example of
    # a bound, which some lines print exactly ('<0.01' others); the counts beside them are the not detected and the
    # values printed only as a limit, below or above a number ('<' or '>')
    rv_nd = collections.Counter(str(r.get('raw_value') or '').strip() for r in ck_b if r['censored'] == 'not_detected')
    rv_lt = collections.Counter(str(r.get('raw_value') or '').strip() for r in ck_b if r['censored'] == '<')
    assert rv_nd.most_common(1)[0][0] == 'ND' and rv_nd['n.d.'] > 0 and rv_lt['< 0.01'] > 0 and rv_lt['<0.01'] > 0, \
        (rv_nd.most_common(3), rv_lt['< 0.01'], rv_lt['<0.01'])
    nd_m_ = collections.Counter(r['metric'] for r in ck_b if r['censored'] == 'not_detected')
    assert set(nd_m_) == {'kcat', 'Km', 'kcat/Km'} and sum(nd_m_.values()) == CJ['not_detected'], nd_m_
    cl0_ = re.sub(r'\s+', ' ', claude)
    assert 'prints only as a bound (`< 0.01`, `> 50`) or as not detected (`ND` defined as not detected' in cl0_ \
        and 'is a row with `censored` = `<`, `>` or `not_detected`' in cl0_
    F['nd'] = dict(print='ND', n=f"{CJ['not_detected']:,}")
    F['lt'] = dict(print='< 0.01', n=f"{CJ['limits']:,}")
    # S1r (the editor: 'ND' is never defined and '< 0.01' without a unit reads as a p-value cut-off): words, not print.
    # 'not detected' as CLAUDE.md says it; the limits as the notation every paper uses for them, '< x or > x' (x italic:
    # the printed number), each line led by '+' because these are kept beside the values, not among them
    F['nd']['words'] = 'not detected'
    F['lt']['words'] = [('only as < ', ''), ('x', 'i'), (' or > ', ''), ('x', 'i')]
    S['bounds_print'] = (f"git show {CK}:bounds.jsonl: not detected {F['nd']['n']} ('ND' printed on {rv_nd['ND']:,}, 'n.d.' "
                         f"{rv_nd['n.d.']:,}), printed only as a limit {F['lt']['n']} ('<' {kinds_['<']:,}, '>' "
                         f"{kinds_['>']:,}; '< 0.01' on {rv_lt['< 0.01']:,}, '<0.01' {rv_lt['<0.01']:,}); CLAUDE.md's own "
                         "example of a bound '< 0.01' and of not detected 'ND'")
    del rv_nd, rv_lt, cl0_, nd_m_
    S['limits'] = (f"git show {CK}:bounds.jsonl (the data checkpoint of {ck_when[:16]} whose catalog.jsonl has the "
                   f"{F['values']} values of {F['papers']} papers; its log.tsv's last add, drop or fix {last_ck}): "
                   f"{len(ck_b):,} lines, one per censored value (kcat, Km or kcat/Km) of "
                   f"{len({r['pmid'] for r in ck_b}):,} papers: {F['lt']['n']} bounds ('<' {kinds_['<']:,}, '>' "
                   f"{kinds_['>']:,}) and {F['nd']['n']} not detected, {nd_lim_:,} of these with a printed limit; "
                   'catlog.py BOUNDS = bounds.jsonl, append_bounds: "apart from the numeric catalog"; '
                   'paper/manuscript/discussion.md "printed only as a bound or as not detected, are kept apart"')
    del kinds_, nd_lim_, ms_
    # Q1 (the legend dates the counts, so they do not read as a yield of the 75k papers listed): the papers read at the
    # checkpoint (an add line in its log: read by an agent, verified by a second, added), the papers with values among
    # them; the rest were waiting to be read
    read_ck = {q[1] for q in changes if len(q) > 2 and q[2] == 'add'}
    assert len(read_ck) == CJ['papers_read'] and pm_ck <= read_ck, (len(read_ck), len(pm_ck - read_ck), CJ['papers_read'])
    F['read_by_ck'] = f"{CJ['papers_read']:,}"
    # the test papers (sources/holdout_locked.txt as the checkpoint holds it) and those of them with no add line there
    locked_ck = {ln.strip() for ln in at_ck('sources/holdout_locked.txt') if not ln.startswith('#')}
    assert (len(locked_ck), len(locked_ck - read_ck)) == (CJ['test_papers'], CJ['test_unread']), \
        (len(locked_ck), len(locked_ck - read_ck), CJ)
    # checker: 'nearly all the others were waiting to be downloaded or read' (the legend): of the checkpoint's listed
    # papers not yet read, over 99% were todo or needs_browser (the rest: no kinetic terms, wrong paper, unavailable, no text)
    st_ck = collections.Counter(r['status'] for r in csv.DictReader(at_ck('papers.tsv'), delimiter='\t')
                                if r['pmid'] not in read_ck)
    assert (st_ck['todo'] + st_ck['needs_browser']) / sum(st_ck.values()) > 0.99 and st_ck['needs_browser'] > 0, st_ck
    del read_ck, st_ck, locked_ck
    del ck_b, changes, pm_ck
    # ---- d: the learning loop, recomputed from the failure taxonomy and matched to its numbers file
    J = json.load(open(P('paper', 'figures', 'method_overview', 'v5', 'taxonomy_numbers.json'), encoding='utf-8'))
    rows = list(tax.values())
    new = [r for r in rows if r['novelty'] == 'new']
    assert len(new) == J['new_in_v2'] == 59 and len(rows) - len(new) == J['old_system'] == 26
    F['old'] = len(rows) - len(new)                 # kinds the earlier system found before 7 Oct (its lessons)
    lags = [(datetime.date.fromisoformat(r['rule_date']) - datetime.date.fromisoformat(r['first_found'])).days
            for r in new if r['rule_date'] and r['status'] != 'open']
    F['lag_n'], F['same_day'] = len(lags), sum(1 for d in lags if d == 0)
    assert (F['lag_n'], F['same_day']) == (J['lag_days']['n'], J['lag_days']['same_day']) == (50, 45)
    after = [r['id'] for r in rows if r['rule_date'] and any(e and e.split(' ', 1)[0] > r['rule_date']
                                                             for e in r['found_again'].split('; '))]
    F['again'] = len(after)
    assert F['again'] == len(J['found_again_after_rule']) == 33
    later = {r['id']: r['rule_dates'].split('; ')[1:] for r in rows if r['rule_dates'].count(';')}
    F['later_classes'], F['later_commits'] = len(later), sum(len(v) for v in later.values())
    assert (F['later_classes'], F['later_commits']) == (J['later_rules']['classes'], J['later_rules']['commits']) == (30, 65)
    dates = ([r['first_found'] for r in new] + [e.split(' ', 1)[0] for r in rows for e in r['found_again'].split('; ') if e]
             + [d.split(' ')[0] for r in rows for d in r['rule_dates'].split('; ') if d])
    assert min(dates) == '2026-10-07' and max(dates) == '2026-11-02' and J['log_cutoff'] == '2026-11-02 08:00'
    F['span'] = '7 Oct – 2 Nov'
    assert (J['reads'], J['papers_read']) == (10049, 7533)
    adds = collections.Counter()
    with open(P('log.tsv'), encoding='utf-8') as fh:
        for ln in fh:
            q = ln.rstrip('\n').split('\t')
            if len(q) >= 3 and q[0] < J['log_cutoff'] and q[2] == 'add':
                adds[q[1]] += 1
    assert (sum(adds.values()), len(adds)) == (J['reads'], J['papers_read']) == (10049, 7533)
    F['reread_papers'] = sum(1 for v in adds.values() if v >= 2)   # papers with a second or later read: 2,345
    assert F['reread_papers'] == 2345, F['reread_papers']
    S['d'] = ('paper/figures/method_overview/v5/taxonomy.tsv recomputed as build_taxonomy.py does, matched to '
              'taxonomy_numbers.json: 85 kinds, 71 rules; lag_days 45 of 50 (v2 kinds with a rule, rule commit the day '
              'the finding was recorded); found_again_after_rule 33; later_rules 30 kinds, 65 commits; first finding '
              '7 Oct, last event 2 Nov (log lines before 2 Nov 08:00); log.tsv add lines before the cutoff: 10,049 '
              'reads of 7,533 papers (as taxonomy_numbers.json), 2,345 papers read more than once')
    # ---- b: one real stored value (catalog.jsonl rows of PMID 14676218, Table I), its stamp, one reader rule
    hold = set(open(P('sources', 'holdout_locked.txt'), encoding='utf-8').read().split())
    assert '14676218' not in hold, 'a held-out paper'
    RID = {'kcat/Km': '5473a85f40107ed8', 'kcat': 'e16aa0b15a4064d0', 'Km': '19dcf2cf3e09e7f8'}
    rec = {}
    with open(P('catalog.jsonl'), encoding='utf-8') as fh:
        for ln in fh:
            if '"14676218"' in ln:
                r = json.loads(ln)
                if r['row_id'] in RID.values():
                    rec[r['metric']] = r
    assert set(rec) == set(RID) and all(rec[m]['row_id'] == RID[m] for m in RID), rec.keys()
    k_, km_, e_ = rec['kcat'], rec['Km'], rec['kcat/Km']
    assert (k_['value'], k_['unit'], km_['value'], km_['unit'], e_['value'], e_['unit']) == \
        (6.79, 's^-1', 0.0041, 'mM', 1660.0, 'mM^-1 s^-1')
    assert all(r['enzyme'] == 'glutaredoxin 1 (Grx1)' and r['organism'] == 'Homo sapiens' and r['substrate'] == 'RNase-SG'
               and r['pH'] == 7.0 and r['location'] == 'Table I' and r['variant'] == 'wild type' for r in rec.values())
    assert (e_['raw_value'], e_['raw_unit'], e_['unit_for_conversion']) == ('1.66 × 10^6', 'µM^-1 s^-1', 'M^-1 s^-1')
    F['reader_note'] = 'the cells are in M^-1 s^-1 (read as µM^-1 s^-1 they would be 10^6 too high)'
    F['verifier_note'] = 'header prints µM^-1 s^-1 but every cell equals kcat/Km in M^-1 s^-1'
    assert F['reader_note'] in e_['metric_note'] and F['verifier_note'] in e_['verify_note']
    stamps = {}
    with open(P('sources', 'provenance_backfill.tsv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            if r['row_id'] in RID.values():
                stamps[r['row_id']] = r
    assert len(stamps) == 3 and not e_.get('reader_model')        # stored before stamping: its stamp was rebuilt
    st_ = {(r['reader_model'], r['verifier_model'], r['pipeline_commit'], r['how']) for r in stamps.values()}
    assert st_ == {('claude-opus-5-5', 'claude-opus-5-5', '893d0ad9bb4d', 'reconstructed')}, st_
    assert units.normalize('kcat/Km', e_['raw_value'], e_['unit_for_conversion']) == (1660.0, 'mM^-1 s^-1', None)
    F['rec'] = dict(raw_value=e_['raw_value'], raw_unit=e_['raw_unit'], conv_unit=e_['unit_for_conversion'],
                    location=e_['location'], substrate=e_['substrate'], pH=e_['pH'], kcat=k_['value'], km=km_['value'],
                    kcat_over_km=e_['value'], model='claude-opus-5-5', commit='893d0ad9bb4d')
    F['rule'] = 'Do not convert anything; code converts.'
    assert F['rule'] in read
    # ---- a and d: what people did and what comes back to them
    hr = txt('HUMAN_REVIEW.md')
    assert '4,214 of 4,793 values match' in pitch and '321 of the 579' in pitch and 4793 - 4214 == 579
    assert 'every reviewed paper CatLog has not read yet; `next` reads them before other papers' in hr
    F['approved'], F['differ'] = '4,793', '579'
    # H6 (the refuter's correction to item 6: PITCH.md's 3,280 is out of date): the records people reviewed, today. One
    # line per reviewed record of human_review/decisions.jsonl (rebuilt by every ingest, merged per record_key, never
    # review_key, which collides: HUMAN_REVIEW.md), records, not decisions (a line keeps every decision in its history:
    # checker, 4,375 decisions on the 3,758 records); the earlier catalogue's 2,770 pack records and this catalogue's 988,
    # one review as the site gives it (its "people checked ... records against their papers" leaves out the ones with no
    # PMID or DOI; "reviewed" here counts them, as the 3,280 it replaces did). Counted to the file's last decision of 6 Nov
    # (18:11 UTC), so a later ingest adds records instead of breaking this
    assert 'One line per reviewed value: the latest verdict, every earlier one' in hr
    assert 'per `record_key` (never `review_key`, which collides)' in re.sub(r'\s+', ' ', hr)
    # FINAL PASS (16 Nov, the owner: "this is a wrap from human review (for the paper not overall) the website and db will
    # keep growing but wrap for paper data report freeze"): the People box draws people's review as frozen for the paper,
    # paper/evidence/human_review_freeze_20261116/numbers.json (records_checked and papers; records_no_paper for the
    # legend), and no longer human_review/decisions.jsonl, which keeps taking results files for the website. The freeze
    # counted them with the functions below (its freeze.py); this build counts them again, by the same code, from the
    # frozen review file inside the freeze's review_inputs.tar.xz (each input's sha256 is in numbers.json), as
    # writing/figures/fig2/people_data.py does, and asserts both counts equal
    import hashlib, tarfile
    RV = json.load(open(os.path.join(REVIEW_DIR, 'numbers.json'), encoding='utf-8'))
    RN, rv_in = RV['numbers'], {d_['file']: d_['sha256'] for d_ in RV['inputs']}
    rv_tar = os.path.join(REVIEW_DIR, 'review_inputs.tar.xz')
    assert _sha256(rv_tar) == RV['review_inputs_sha256'], 'the frozen review inputs are the freeze\'s'
    with tarfile.open(rv_tar) as tf_:
        raw_ = tf_.extractfile('human_review/decisions.jsonl').read()
    assert hashlib.sha256(raw_).hexdigest() == rv_in['human_review/decisions.jsonl']
    dec = [json.loads(ln) for ln in raw_.decode('utf-8').splitlines() if ln.strip()]
    del raw_
    # S1: the 7 Nov ingests (09:50, 10:01) added reviews made before the 6 Nov cut (18:11 UTC), so a count to that cut
    # no longer gives 3,758 (it gives 3,809). Counted to the file's last decision as rebuilt at 10:01 (7 Nov 04:12 UTC):
    # every record people reviewed then. FINAL PASS: the frozen file's last decision, the freeze's own
    DCUT = max(h['at'] for r in dec for h in r['history'])
    assert DCUT == RV['last_decision_in_freeze'], (DCUT, RV['last_decision_in_freeze'])
    rev = [r for r in dec if min(h['at'] for h in r['history']) <= DCUT]
    assert all(re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z', h['at']) for r in dec for h in r['history'])
    assert len({r['key'] for r in rev}) == len(rev) == len(dec) == RN['records_in_file'], len(rev)
    # the legend names the freeze, by its day: 'as frozen for this paper on 16 November 2026'
    FZ_ = RV['frozen_at']
    assert re.fullmatch(r'\d{4}-\d\d-\d\d \d\d:\d\d', FZ_) and FZ_[:10] >= DCUT[:10], FZ_
    F['review_date'] = f"{int(FZ_[8:10])} {['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][int(FZ_[5:7]) - 1]} {FZ_[:4]}"
    # W1 review count (11 Nov, the owner: "Yes, use 5,838"): the box draws the records people checked against their
    # papers, the number of `catlog.py status` ("Human review: people checked N records against their papers (M more had
    # no PMID or DOI)"), from the status's own functions: human_review._decisions and review_summary (what its
    # status_line reads through compare()), then site_release._one_review and _review_basis (what _quality_lines makes
    # that line from). So the H6 comment above ('"reviewed" here counts them') held until this change: the M records
    # with no PMID or DOI are no longer counted. No rule of the build's own: a count by the lines' pmid and doi fields
    # gives another split
    import human_review, site_release               # tools/ is on the path since catlog's import; they read files only
    # FINAL PASS: the status's functions on the frozen rows (human_review._decisions only reads the live file's lines)
    assert "return [json.loads(l) for l in open(DECISIONS) if l.strip()]" in inspect.getsource(human_review._decisions)
    hrows_ = dec
    hsum_ = human_review.review_summary(hrows_)
    one_ = site_release._one_review(hsum_)
    basis_, nopaper_ = site_release._review_basis(one_)
    n_checked, n_nopaper = basis_['entries'], nopaper_ or 0
    assert len(hrows_) == len(dec) == len(rev) and one_['entries'] == len(dec), (len(hrows_), len(dec), one_['entries'])
    assert n_checked + n_nopaper == len(dec), (n_checked, n_nopaper, len(dec))     # every record of the file is one or the other
    assert (n_checked, n_nopaper) == (RN['records_checked'], RN['records_no_paper']), (n_checked, n_nopaper, RN)   # the freeze's
    said_ = human_review.one_review_text(hsum_)                                    # the status's own sentence
    assert f'people checked {n_checked:,} records against their papers' in said_, said_[:160]
    assert (f'({n_nopaper:,} more had no PMID or DOI)' in said_) == bool(n_nopaper), said_[:160]
    assert f'people checked {n_checked:,} records against their papers ({n_nopaper:,} more had no PMID or DOI)' in RV['status_line']
    F['checked'], F['no_paper'] = f"{RN['records_checked']:,}", f"{RN['records_no_paper']:,}"
    # W1 review papers (11 Nov, the owner: "why the paper number is fixed? shouldnt it change or sth"; "we use only our
    # catlog (both for values and paper numbers)"): the box's second line is the number of distinct papers behind those
    # n_checked records, from the same rows (hrows_) and by the status's own rule for a record that has a paper:
    # review_summary's has_paper, a function inside it, so its line is asserted in its source and repeated here, and the
    # two counts it gives are asserted against the status's (n_checked, n_nopaper). A record's paper is its PMID (for a
    # paper with no PMID, CatLog's stand-in id, which the pmid field holds), else its DOI
    src_ = inspect.getsource(human_review.review_summary)
    assert "return bool(r.get('checkable') or r.get('doi') or r.get('v2_pack'))" in src_
    assert 'every v2 entry was reviewed with its paper open' in re.sub(r'\s+', ' ', src_)
    pid_ = lambda r: str(r.get('pmid') or '').strip()
    doi_ = lambda r: str(r.get('doi') or '').strip().lower()
    has_ = [r for r in hrows_ if r.get('checkable') or r.get('doi') or r.get('v2_pack')]
    not_ = [r for r in hrows_ if not (r.get('checkable') or r.get('doi') or r.get('v2_pack'))]
    assert (len(has_), len(not_)) == (n_checked, n_nopaper), (len(has_), len(not_), n_checked, n_nopaper)
    # the records not counted are exactly the status's "no PMID or DOI": none of them names either
    assert not any(pid_(r) or doi_(r) for r in not_)
    assert all(pid_(r) for r in has_ if r.get('checkable'))                  # 'checkable' is a PMID
    by_pmid_ = {pid_(r) for r in has_ if pid_(r)}
    by_doi_ = {doi_(r) for r in has_ if not pid_(r) and doi_(r)}
    assert all(p_.isdigit() or catlog.STANDIN.fullmatch(p_) for p_ in by_pmid_), sorted(by_pmid_)[-3:]
    # the status's own paper counts (review_summary's 'papers', the records of the earlier catalogue and of this one)
    # are these PMIDs; a paper named in both parts is counted once here
    assert len({pid_(r) for r in hrows_ if pid_(r) and not r.get('v2_pack')}) == (hsum_.get('v1') or {}).get('papers', 0)
    assert len({pid_(r) for r in hrows_ if pid_(r) and r.get('v2_pack')}) == (hsum_.get('v2') or {}).get('papers', 0)
    # a paper under a PMID in one record and under its DOI alone in another would be counted twice: no DOI-only paper
    # is the DOI of a record with a PMID, nor of a paper of papers.tsv that these records name
    assert not by_doi_ & {doi_(r) for r in hrows_ if pid_(r) and doi_(r)}
    with open(P('papers.tsv'), encoding='utf-8') as fh_:
        assert not any(r['pmid'] in by_pmid_ and r['doi'].strip().lower() in by_doi_ for r in csv.DictReader(fh_, delimiter='\t'))
    # every counted record has a paper, and all but a few name it. The rest (W1 recovered papers, 11 Nov) are records
    # of one review pack of this catalogue that a reviewer approved in their copy of the pack after audits had dropped
    # their rows (values printed again from an earlier paper, partial constants): the pack's index was rebuilt without
    # them and ingest kept the verdict with no paper (pmid '', no rows, pack 'unknown'). The status counts them, since
    # every record of a pack was reviewed with its paper open. Their papers are in ref/review_papers_recovered.tsv,
    # each found by two independent routes (the record's id reproduced from the catalogue of the pack's day; the pack
    # as the reviewer received it), so the count of papers is exact. A record the review file comes to name itself
    # must name the paper found here
    unnamed_ = [r for r in has_ if not pid_(r) and not doi_(r)]
    assert all(r.get('v2_pack') == 'unknown' and not r.get('row_ids') for r in unnamed_), len(unnamed_)
    # FINAL PASS: the list as the review's freeze holds it (its sha256 in numbers.json)
    assert _sha256(P('writing', 'fig1_v8', 'ref', 'review_papers_recovered.tsv')) == rv_in['writing/fig1_v8/ref/review_papers_recovered.tsv']
    with open(P('writing', 'fig1_v8', 'ref', 'review_papers_recovered.tsv'), encoding='utf-8') as fh_:
        rec_ = {r['key']: r['pmid'].strip() for r in csv.DictReader((l_ for l_ in fh_ if not l_.startswith('#')), delimiter='\t')}
    assert rec_ and all(p_.isdigit() or catlog.STANDIN.fullmatch(p_) for p_ in rec_.values()), rec_
    assert all(r['key'] in rec_ for r in unnamed_), sorted(r['key'] for r in unnamed_ if r['key'] not in rec_)
    assert all(pid_(r) == rec_[r['key']] for r in hrows_ if r['key'] in rec_ and pid_(r)), 'the review file and the recovered papers differ'
    found_ = {rec_[r['key']] for r in unnamed_}
    with open(P('papers.tsv'), encoding='utf-8') as fh_:    # a recovered paper is none of those named by DOI alone
        assert not any(r['pmid'] in found_ and r['doi'].strip().lower() in by_doi_ for r in csv.DictReader(fh_, delimiter='\t'))
    n_papers, n_unnamed, n_found = len(by_pmid_ | found_) + len(by_doi_), len(unnamed_), len(found_ - by_pmid_)
    assert sum(1 for r in has_ if pid_(r)) + sum(1 for r in has_ if not pid_(r) and doi_(r)) + n_unnamed == n_checked
    assert n_unnamed * 100 < n_checked and 0 < n_papers <= n_checked, (n_unnamed, n_papers, n_checked)
    assert n_papers == RN['papers'], (n_papers, RN['papers'])                       # the freeze's count of papers
    F['review_papers'] = f"{RN['papers']:,}"
    S['people'] = (f'paper/evidence/human_review_freeze_20261116/numbers.json (frozen {FZ_}; records_checked '
                   f"{RN['records_checked']:,}, papers {RN['papers']:,}, records_no_paper {RN['records_no_paper']:,}), counted "
                   f'again here from its frozen decisions.jsonl (review_inputs.tar.xz): {len(rev):,} records (distinct record '
                   f'keys) to the last decision {DCUT}'
                   f'; drawn: the {n_checked:,} of them people checked against their papers, as `catlog.py status` counts '
                   f'them (human_review.review_summary, site_release._one_review and _review_basis); the {n_nopaper:,} with '
                   'no PMID or DOI are not counted'
                   f'; drawn: the {n_papers:,} distinct papers of those {n_checked:,} records: {len(by_pmid_):,} named by PMID '
                   f'or stand-in id and {len(by_doi_):,} by DOI alone in the review file, and {n_found:,} more that only the '
                   f'{n_unnamed:,} records with no paper named there come from (writing/fig1_v8/ref/'
                   'review_papers_recovered.tsv: two independent routes for each)')
    del dec, rev, hrows_, hsum_, one_, basis_, nopaper_, said_, src_, has_, not_, by_pmid_, by_doi_, unnamed_, rec_, found_
    # S1: human_review/compare.tsv's buckets (4,214 / 139 / 440) are no longer asserted: nothing draws them, and the 7 Nov
    # ingest rebuilt the file (4,163 agree today), as the V1V4 checker dropped the agent-findings sentence before
    assert 'rejected: an audit, never an automatic drop' in hr and 'never change a v2' in hr
    assert '6.79/4.1 µM = 1.66e6 M^-1 s^-1' in e_['verify_note']
    # Q1, b's Verify caption 'kcat ÷ Km shows a misprinted unit': each row's own kcat ÷ Km (6.79 s^-1 ÷ 4.1 µM =
    # 1.66 x 10^6 M^-1 s^-1) shows the column's µM^-1 s^-1 header is misprinted; the database check found it so for all
    # 13 cells of the table that SABIO-RK lists as headed
    dc_ = [r for r in csv.DictReader(open(P('sources', 'database_corrections.tsv'), encoding='utf-8'), delimiter='\t')
           if r['pmid'] == '14676218']
    assert len(dc_) == 13 and {(r['verdict'], r['cause']) for r in dc_} == {('corrected', 'paper_unit_misprint')}, len(dc_)
    assert (k_['value'], round(km_['value'] * 1e3, 9)) == (6.79, 4.1) and abs(6.79 / 4.1e-6 / 1.66e6 - 1) < 0.003
    # S1 (the owner: "the kcat divided by Km isn't equal to kcat divided by Km. Why are you using different sign"): the
    # figure writes the slash only inside the name kcat/Km and says the arithmetic in words; the row's own kcat and Km
    # (above) are what show the header misprinted
    F['verify_cap'] = 'its kcat and Km show a misprinted unit'
    del dc_
    F['locked'] = len([l for l in open(P('sources', 'holdout_locked.txt'), encoding='utf-8') if l.strip() and not l.startswith('#')])
    assert F['locked'] == CJ['test_papers'], (F['locked'], CJ['test_papers'])
    locked = {l.strip() for l in open(P('sources', 'holdout_locked.txt'), encoding='utf-8') if l.strip() and not l.startswith('#')}
    added = set()
    with open(P('log.tsv'), encoding='utf-8') as fh:
        for ln in fh:
            q = ln.rstrip('\n').split('\t')
            if len(q) >= 3 and q[2] == 'add':
                added.add(q[1])
    F['unread'] = len(locked - added)
    assert F['unread'] == CJ['test_unread'], (F['unread'], CJ['test_unread'])   # the build's own count, of the freeze's log
    F['locked'], F['unread'] = f"{CJ['test_papers']:,}", f"{CJ['test_unread']:,}"
    # R1 (the review: no reported test uses them yet): c says "kept unread for a later test"; the locked test is a design,
    # not yet run (a run rewrites this line, and the box's words then need a look). FINAL PASS (16 Nov): the locked test
    # has run (writing/manuscript/results.md), so 'a later' goes: b says '343 kept unread for the test'. The list is the
    # method paper's test set, which the loop never reads, audits or sweeps; only the frozen run of the test reads them,
    # and CatLog's catalogue holds none of the 343 (no add line at the freeze; 26 were read before they were held out).
    # Not 'held out for the test' (the pass's first wording): the legend and the Methods call all 369 held out
    hl0_ = ' '.join(l.lstrip('#').strip() for l in open(P('sources', 'holdout_locked.txt'), encoding='utf-8') if l.startswith('#'))
    assert "The method paper's test set" in hl0_ and 'Read for the first time only by the frozen harness after preregistration: the ' \
        'loop never reads, audits or sweeps them (catlog.locked(), CLAUDE.md)' in hl0_, hl0_
    assert inspect.getsource(catlog.locked).count('holdout_locked.txt') >= 1
    del hl0_
    assert len([l for l in open(P('sources', 'blind_reread.txt'), encoding='utf-8') if l.strip() and not l.startswith('#')]) == 303
    # Q1 (the legend): those 303 are the papers whose agents had opened database values or the earlier catalogue
    assert 'The 303 papers whose readers (173) or verifiers (130) had opened database values or earlier-catalog files ' \
           'before the blind_check guard (human_review/exposed.tsv, sources/blind_reread.txt) were read again blind' \
        in re.sub(r'\s+', ' ', claude)
    F['blind'] = 303
    db = [r for r in csv.DictReader(open(P('sources', 'db_values.tsv'), encoding='utf-8'), delimiter='\t')
          if r['pmid'] == '14676218' and 'SABIO 47543' in r['comment'] and r['metric'] == 'kcat/Km']
    assert len(db) == 1 and float(db[0]['value']) == 1.66e9, db
    assert re.search(r'Grx1\s+4\.1\s+6\.79\s+1\.66', txt('texts', '14676218.txt'))
    assert not txt('texts', '14676218.txt').startswith('GLYPH WARNING')
    # ---- 2026-11-04 night (the owner: "one paper ... undersells our approaches"; "more of our design or snippet or
    # comparison or error rules"): real cases, each tied to its record
    lay = collections.Counter(r['guard_layer'] for r in tax.values() if r['status'] == 'rule')
    assert (lay['reader prompt'], lay['code conversion'], lay['verifier prompt'], lay['code check'],
            lay['database check']) == (16, 10, 7, 35, 3) and sum(lay.values()) == 71, lay
    F['layers'] = [('the reader’s prompt', 16), ('the verifier’s prompt', 7), ('conversion code', 10), ('code checks', 35),
                   ('database checks', 3)]
    # ---- S1, fix 2 (the owner: "there are 15 other rules other than this one rule ... Otherwise people will feel like
    # that's the only one case ... focus on the numbers"): each b card shows one rule of its step's N ('1 of N rules', N
    # ticks, the shown rule's in ink). The 3 rules of the database check (DB1, DB3, PR17) have no card. The rule behind
    # each card's case is a rule at that card's own layer, in force when the case's paper was read
    assert sorted(k_ for k_, r in tax.items() if r['status'] == 'rule' and r['guard_layer'] == 'database check') == \
        ['DB1', 'DB3', 'PR17']
    F['case_rule'] = {'Read': 'RA1', 'Convert': 'CU1', 'Verify': 'RA4', 'Check': 'IP4'}      # V8b: b's four examples
    for st_name, (id_, layer_) in zip(F['case_rule'], (('RA1', 'reader prompt'), ('CU1', 'code conversion'),
                                                       ('RA4', 'verifier prompt'), ('IP4', 'code check'))):
        assert F['case_rule'][st_name] == id_ and (tax[id_]['status'], tax[id_]['guard_layer']) == ('rule', layer_), id_
    F['rules_n'] = {'Read': lay['reader prompt'], 'Convert': lay['code conversion'], 'Verify': lay['verifier prompt'],
                    'Check': lay['code check']}
    assert F['rules_n'] == {'Read': 16, 'Convert': 10, 'Verify': 7, 'Check': 35}
    # ---- T1 (7 Nov, the owner on b: "the rules thing looks nice ... but maybe better and more obvious way to show it or
    # what the rules are or feedback loop if that happens"): each tick takes the colour of who first found the kind of
    # error its rule guards against (the taxonomy's found_route, which records the first finding only): grey, the earlier
    # system's lessons, written into the first rules on 7-8 Oct; mint (the agents' edge), CatLog's own agents and code: the
    # agent that runs CatLog in the owner's chat ('operator'), code checks, AI reviews from outside the loop, audits, the
    # verifier, the scale sweep (code lists, agents check) and the database check; tan (people's edge), people: reviewers
    # and the owner. Who noticed an error first inside the owner's chat is not recorded (TAXONOMY.md, asserted with d's
    # steps), so those count with the agent that runs CatLog. The example's rule is drawn in ink, first in its own group
    FINDER = {'old system': 'earlier', 'reviewer': 'people', 'owner': 'people'}
    fcls_ = lambda r: FINDER.get(r['found_route'], 'agents')
    rl_ = [r for r in tax.values() if r['status'] == 'rule']
    assert {r['found_route'] for r in rl_} == {'old system', 'operator', 'code check', 'outside review', 'audit', 'reviewer',
                                                'verifier', 'sweep', 'owner', 'database check'}, {r['found_route'] for r in rl_}
    assert {r['rule_date'] for r in rl_ if fcls_(r) == 'earlier'} == {'2026-10-07', '2026-10-08'}    # the first rules
    assert all(r['rule_date'] for r in rl_)
    F['finder_n'], F['ticks'] = {}, {}
    for st_name, layer_ in (('Read', 'reader prompt'), ('Convert', 'code conversion'), ('Verify', 'verifier prompt'),
                            ('Check', 'code check'), ('database', 'database check')):
        ids_ = [k_ for k_, r in tax.items() if r['status'] == 'rule' and r['guard_layer'] == layer_]
        F['finder_n'][st_name] = tuple(sum(1 for k_ in ids_ if fcls_(tax[k_]) == c_) for c_ in ('earlier', 'agents', 'people'))
        if st_name in F['case_rule']:
            ex_ = F['case_rule'][st_name]
            F['ticks'][st_name] = [[(k_, c_, k_ == ex_) for k_ in sorted((k_ for k_ in ids_ if fcls_(tax[k_]) == c_),
                                                                      key=lambda k_: (k_ != ex_, tax[k_]['rule_date'], k_))]
                                   for c_ in ('earlier', 'agents', 'people') if any(fcls_(tax[k_]) == c_ for k_ in ids_)]
            assert sum(len(q_) for q_ in F['ticks'][st_name]) == F['rules_n'][st_name] and \
                sum(e_ for q_ in F['ticks'][st_name] for *_, e_ in q_) == 1
    assert F['finder_n'] == {'Read': (8, 7, 1), 'Convert': (3, 7, 0), 'Verify': (3, 4, 0), 'Check': (9, 22, 4),
                             'database': (1, 2, 0)}, F['finder_n']
    F['finder_all'] = tuple(sum(v_[i] for v_ in F['finder_n'].values()) for i in range(3))
    assert F['finder_all'] == (24, 42, 5) and sum(F['finder_all']) == F['rules']
    # the examples' own rules: RA1, RA4 and TL11 among the earlier system's lessons, CU3 found by the scale sweep (20 Oct)
    assert [fcls_(tax[F['case_rule'][s_]]) for s_ in ('Read', 'Convert', 'Verify', 'Check')] == \
        ['earlier', 'earlier', 'earlier', 'agents'] and tax['IP4']['found_route'] == 'outside review'
    assert tax['CU3']['found'].startswith('2026-10-20 sweep: scale sweep')   # T1 round 2: the legend's 'sweep for misprinted units'
    # the five found by people: the human review (IP6, 10 Oct), the website review rounds (DB5, IP7, IP9; 9-11 Oct, no
    # reviewer named) and the owner on the website (CU7, 27 Oct)
    assert sorted(k_ for k_, r in tax.items() if r['status'] == 'rule' and fcls_(r) == 'people') == \
        ['CU7', 'DB5', 'IP6', 'IP7', 'IP9']
    assert tax['IP6']['found'].startswith('2026-10-10 reviewer: human review') \
        and tax['CU7']['found'].startswith('2026-10-27 owner') \
        and all('website review' in tax[k_]['found'] for k_ in ('DB5', 'IP7', 'IP9'))
    S['finders'] = ("taxonomy.tsv status 'rule' by found_route (first finding): old system 24 (rule_date 7-8 Oct), "
                    "operator 20, code check 7, outside review 7, audit 4, verifier 2, sweep 1, database check 1 (42), "
                    "reviewer 4 and owner 1 (5); per card (earlier, agents, people): Read (8, 7, 1), Convert (3, 7, 0), "
                    "Verify (3, 4, 0), Check (9, 22, 4); database check (1, 2, 0)")
    del rl_
    # ---- T2 (7 Nov, the owner on b: "a better and more obvious way to show it or what the rules are"): under each card's
    # ticks two or three of its other rules, named in plain words. Each is a rule of the card's own layer in the taxonomy
    # (status 'rule'), never the rule the card's example shows, and its words are the taxonomy's own (the cue in its class
    # or guard). The first named under Read, Convert and Check are the rules of d's three errors (PP2, CU8 and PR5,
    # asserted with d's facts below)
    # U1 (7 Nov, the owner on T2: "the T2 named rules, the way they are written is hard to understand. Two words, what
    # will people understand? Being a bit more verbose or easily explaining is better than internal AI terms"): each named
    # rule is a plain clause that says what CatLog does, one rule a line, two under Read, Convert and Check and one under
    # Verify (its stacked print stands where a second line would go). Each is a rule of the card's own layer (status
    # 'rule'), never the card's example's, and its words restate its guard (the cues). The first under Read, Convert and
    # Check are the rules of d's three errors (PP2, CU8 and PR5, asserted with d's facts below)
    # U1 round 2 (a cold figure editor on U1: "the rules read as project shorthand that a reader cannot act on"; the
    # owner's point stands: plain words a first-time reader understands): every rule an instruction in plain words, as the
    # step's instructions or code give it, one a line ('skip values copied from older work', 'never store an isozyme as a
    # mutant'; 'keep a Km in mg/ml in its own unit', 'never guess a unit the paper omits'; 'find the values the reader
    # missed'; 'keep the test papers unread', 'refuse a file of the wrong paper'). The card's own example now has its rule
    # as the list's last line, in the same voice, its print directly under it (F['ex_rule'] below), in place of the
    # caption at the card's foot, so each example visibly shows one of the rules listed
    NAMED_ = {'Read': (('skip values copied from older work', 'PP2',
                        ('only values measured in this paper',
                         "a reference column identical to the cited paper's table is skipped")),
                       ('never store an isozyme as a mutant', 'IP6',
                        ("an isozyme, paralog, allele, splice or strain form is the enzyme's identity, variant wild type",))),
              'Convert': (('keep a Km in mg/ml in its own unit', 'CU8', ('such a Km stays in mg/mL', 'in their own export columns')),
                          ('never guess a unit the paper omits', 'CU1',
                           ('the value is refused with unknown_*_unit', 'no unit is ever defaulted'))),
              'Verify': (('find the values the reader missed', 'RA6',
                          ('the verifier writes skipped values to a missed file that a second checker verifies',)),),
              'Check': (('keep the test papers unread', 'PR5', ('leave the locked papers out',)),
                        ('refuse a file of the wrong paper', 'IP18',
                         ('a PDF is filed by title only when the title is printed near its top',
                          'files rejected for a paper are remembered by content')))}
    # the example's own rule, worded as the others (until U1 round 2 a caption at the card's foot said what the example
    # showed: 'a Hill constant is not a Km', 'the exponent is printed with spaces', 'its kcat and Km show a misprinted unit',
    # 'the PDF text shows ° as 8')
    EXR_ = {'Read': ('skip a Hill constant printed as Km', 'RA1', ('Hill constants', 'are not Km or kcat')),
            'Convert': ('read exponents printed with spaces', 'CU3', ("reads a spaced exponent ('2.76E + 03'",)),
            'Verify': ('check kcat/Km against kcat and Km', 'RA4',
                       ('all three cells when kcat/Km is 5x or more off kcat ÷ Km',)),
            'Check': ('allow for ° shown as 8 in PDF text', 'TL11', ("check() reads '378C'", "the glyph warning names ° as '8'"))}
    LAYER_ = {'Read': 'reader prompt', 'Convert': 'code conversion', 'Verify': 'verifier prompt', 'Check': 'code check'}
    # V8b: the named rules are no longer drawn (their checks against the case rule dropped)
    # and CatLog does what each line says (its code and instructions today)
    rd_ = re.sub(r'\s+', ' ', read)
    assert "a reference column identical to that paper's table is reprinted, so skip it" in rd_                  # PP2
    assert "is the enzyme's identity, not a variant" in rd_                                                     # IP6
    assert units.normalize('Km', '1.1 ± 0.12', 'mg/ml') == (1.1, 'mg/mL', None)                                # CU8
    assert units.normalize('kcat', '5.0', '') == (None, None, 'unknown_kcat_unit:') \
        and units.normalize('kcat', '5.0', 'U/mg') == (None, None, 'unknown_kcat_unit:U/mg')                    # CU1
    assert 'Output: `work/<PMID>.verify.json`, plus `work/<PMID>.missed.read.json`' in verify                     # RA6
    assert len(catlog.locked()) == CJ['test_papers'] and 'locked' in inspect.getsource(catlog.cmd_next)                       # PR5
    # U1 checker (the legend: 'the test papers are not read during development'): read first only by the frozen run;
    # downloading them is allowed, so the legend says 'not read', never 'left out of all work'
    cl2_ = re.sub(r'\s+', ' ', claude)
    assert 'are read for the first time only by the frozen run' in cl2_ and 'Downloading them is fine (not reading)' in cl2_
    del cl2_
    assert 'The title itself must be printed near the top.' in txt('catlog.py')                                  # IP18
    assert 'This holds even under a "Km"/"apparent Km" header' in rd_ and 'skip that Km and its kcat/Km' in rd_   # RA1
    assert units.normalize('kcat', '2.76E + 03', 's^-1') == (2760.0, 's^-1', None)                             # CU3
    vs1_ = re.sub(r'\s+', ' ', verify)
    assert 'A kcat/Km ≥5× away from kcat ÷ Km of the same row usually means a misread unit, prefix or header ' \
           'multiplier' in vs1_ and 'check all three cells on the page image' in vs1_                          # RA4
    assert "a PDF text layer that prints ° as 8: '378C'" in inspect.getsource(catlog.check) \
        and 'degree_as_8' in inspect.getsource(catlog.check)          # TL11 (its behaviour on 21455933: R1's facts below)
    del rd_, vs1_
    F['named'] = {s_: [w_ for w_, *_ in v_] for s_, v_ in NAMED_.items()}
    F['named_ids'] = {s_: [i_ for _, i_, _ in v_] for s_, v_ in NAMED_.items()}
    F['ex_rule'] = {s_: w_ for s_, (w_, *_) in EXR_.items()}
    assert F['named'] == {'Read': ['skip values copied from older work', 'never store an isozyme as a mutant'],
                          'Convert': ['keep a Km in mg/ml in its own unit', 'never guess a unit the paper omits'],
                          'Verify': ['find the values the reader missed'],
                          'Check': ['keep the test papers unread', 'refuse a file of the wrong paper']}, \
        F['named']
    # no internal words: no file, tool or field names, no 'locked', 'prompt', 'reprint' (the owner's question)
    assert not re.search(r'(?i)\.md|\.py|locked|prompt|reprint|catalog|glyph|parser|_', ' '.join(
        sum(F['named'].values(), []) + list(F['ex_rule'].values())))
    S['named'] = ('taxonomy.tsv status rule, guard_layer of the card, words from its guard: ' + '; '.join(
        f"{s_} {', '.join(i_ for _, i_, _ in v_)} ({LAYER_[s_]})" for s_, v_ in NAMED_.items()) + "; the examples' "
        'own rules RA1, CU3, RA4, TL11 as each list\'s last line; CatLog: read.md (PP2, IP6, RA1), units.normalize (CU8, '
        'CU1, CU3), verify.md (RA6, RA4), catlog.locked and cmd_next (PR5), the title check in catlog.py (IP18), '
        'catlog.check (TL11)')
    del NAMED_, LAYER_, EXR_
    log_ = open(P('log.tsv'), encoding='utf-8').read()
    # Read: RA1 since 7 Oct (f171ab3); the case's one read is of 29 Oct (asserted with F['hill'] below)
    assert (tax['RA1']['rule_commit'], tax['RA1']['rule_date']) == ('f171ab3', '2026-10-07')
    # Convert: CU3, whose own example is the card's 41657244 (read 18 Oct; its values re-converted under the rule on 20 Oct)
    c3_ = tax['CU3']
    assert c3_['class'] == 'Parser read a spaced exponent as none' \
        and c3_['example'].startswith("41657244: '2.76E + 03' read as 2.76") \
        and (c3_['rule_commit'], c3_['rule_date']) == ('2b61622', '2026-10-20'), c3_
    assert '\n2026-10-18 22:41\t41657244\tadd\tkept=29\t' in log_
    assert re.search(r"\n2026-10-20 10:04\t41657244\tunitfix\t[0-9a-f]{16}\t[^\n]*units\.parse_number now reads the "
                     r"spaced exponent 'aE \+ b' \(it read 2\.76E \+ 03 as 2\.76\)", log_)
    # Verify: RA4 (verify.md rule 3: kcat/Km 5x or more off kcat ÷ Km, check all three cells and give the unit that
    # converts), in the verifier instructions the case's values were verified with (049cc9dd437b, the rows' provenance:
    # added 11 Oct 09:57). The case is of class PP1 (a misprinted header) too, a Verify rule as well, whose own wording
    # came 12.5 h after that add (cb53ec3), so the ink tick is RA4's: one of the 7 either way
    r4_ = tax['RA4']
    assert r4_['class'] == 'Reader misreads a unit, prefix or multiplier' and r4_['rule_date'] == '2026-10-07' \
        and 'all three cells when kcat/Km is 5x or more off kcat ÷ Km; fix.unit_for_conversion' in r4_['guard'], r4_
    assert {(s_['verify_prompt'], s_['evidence'].split(';')[0]) for s_ in stamps.values()} == \
        {('049cc9dd437b', 'add 2026-10-11 09:57')}, stamps
    vp_b = open(P('sources', 'prompt_versions', '049cc9dd437b.md'), 'rb').read()
    import hashlib
    assert hashlib.sha256(vp_b).hexdigest()[:12] == '049cc9dd437b'
    vp_s = re.sub(r'\s+', ' ', vp_b.decode('utf-8'))
    assert 'A kcat/Km ≥5× away from kcat ÷ Km of the same row usually means a misread unit, prefix or header multiplier: ' \
           'check all three cells on the page image and fix the one that was misread.' in vp_s \
        and 'give a spelling that converts correctly in `fix.unit_for_conversion`' in vp_s
    assert (tax['PP1']['guard_layer'], tax['PP1']['status'], tax['PP1']['rule_commit']) == ('verifier prompt', 'rule', 'cb53ec3')
    pp1_when = subprocess.run(['git', '-C', ROOT, 'log', '-1', '--format=%ad', '--date=iso', 'cb53ec3'], capture_output=True,
                              text=True, check=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0')).stdout.strip()
    assert pp1_when.startswith('2026-10-11 22:34') and pp1_when.endswith('-0500'), pp1_when
    # Check: TL11's '378C' rule (3c3e3c6, 8 Oct 20:42) came before the card's paper was read (10 Oct 10:11)
    tl_when = subprocess.run(['git', '-C', ROOT, 'log', '-1', '--format=%ad', '--date=iso', '3c3e3c6'], capture_output=True,
                             text=True, check=True, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0')).stdout.strip()
    assert tl_when.startswith('2026-10-08 20:42') and '\n2026-10-10 10:11\t21455933\tadd\tkept=108\t' in log_, tl_when
    S['rules_n'] = ("taxonomy.tsv status 'rule' by guard_layer: reader prompt 16, code conversion 10, verifier prompt 7, "
                    "code check 35, database check 3 (DB1, DB3, PR17); the cases' rules RA1, CU3 (41657244 its own example; "
                    "log.tsv add 18 Oct 22:41, unitfix 20 Oct 10:04), RA4 (verify.md rule 3 in 049cc9dd437b, the "
                    "verifier instructions of 14676218's rows, added 11 Oct 09:57; PP1's own wording cb53ec3 came at "
                    "22:34), TL11 (3c3e3c6, 8 Oct 20:42, before 21455933's add of 10 Oct 10:11)")
    del c3_, r4_, vp_b, vp_s, pp1_when, tl_when
    org = collections.Counter(r['origin'] for r in tax.values())
    assert org == {'identity and pairing': 20, 'the process': 18, 'the reading agent': 14, 'the PDF text layer or OCR': 12,
                   'the printed paper': 8, 'conversion and units': 8, 'the databases': 5}, org
    F['origin'] = [('printed paper', 8), ('PDF text, OCR', 12), ('reading', 14), ('identity', 20), ('units', 8),
                   ('databases', 5), ('process', 18)]
    for id_, start, word in (('IP7', '2026-10-11 reviewer', 'SHV-14'), ('IP9', '2026-10-09 reviewer', 'PurT to a β-mannosidase'),
                             ('CU7', '2026-10-27 owner', "calculated 33 beside the printed '<0.02")):
        assert tax[id_]['found'].startswith(start) and word in tax[id_]['example'] and tax[id_]['status'] == 'rule', id_
    assert 'a form gets a sequence only from an entry of its own' in tax['IP7']['guard']
    assert 'NCBI CDS only from a one-CDS record' in tax['IP9']['guard']
    assert 'derives no kcat/Km where the paper prints it only as a bound' in tax['CU7']['guard']
    # Q1: b's Read card no longer draws RA1's own example (26142822's K0.5): that paper is c's enzyme, E. coli
    # L-asparaginase II, and cites c's paper for a Km 'assuming no cooperativity'. It draws 25658941, the paper RA1's
    # 'found' names as the earlier catalogue's wrong certified Hill row (its facts below, with F['hill'])
    assert '25658941 (Hill)' in tax['RA1']['found'] and 'wrong in old certified rows' in tax['RA1']['found']
    assert tax['RA1']['guard_layer'] == 'reader prompt' and tax['RA1']['status'] == 'rule' and 'Hill constants' in tax['RA1']['guard']
    assert 'Figure 7D prints the same scale' in tax['RA9']['example'] and '×10^5 s^-1' in tax['RA9']['example']
    # catalog rows of the cases
    need = {'11106175', '41657244', '36756200', '42249657', '36394293', '21455933',
            '25658941', '10767281', '12591933'}          # Q1: b's Read card, d's first two errors (S1: 10767281's
    #                                                      refused Km in place of 15760714's catalase)
    cat = collections.defaultdict(list)
    with open(P('catalog.jsonl'), encoding='utf-8') as fh:
        for ln in fh:
            if any(q_ in ln for q_ in need):
                r = json.loads(ln)
                if r['pmid'] in need:
                    cat[r['pmid']].append(r)
    asp = {r['metric']: r for r in cat['11106175']
           if r['row_id'] in ('b6b03f8089d0eaaf', '69a0cbccabbc7768', 'fde9c8a806405298')}
    assert (asp['kcat']['raw_value'], asp['kcat']['raw_unit'], asp['kcat']['value']) == ('2.4 (± 0.1) × 10^1', 's^-1', 24.0)
    assert (asp['Km']['raw_value'], asp['Km']['raw_unit'], asp['Km']['unit']) == ('1.5 (± 0.2) × 10^-5', 'mol L^-1', 'mM')
    assert abs(asp['Km']['value'] - 0.015) < 1e-9
    assert (asp['kcat/Km']['raw_value'], asp['kcat/Km']['raw_unit'], asp['kcat/Km']['value']) == ('1.6 × 10^6', 'M^-1 s^-1', 1600.0)
    assert '2.4~60.1!{10 1' in asp['kcat']['quote'] and '1.5~60.2!{10 25' in asp['Km']['quote']
    F['km_pdftext'] = '1.5~60.2!{10 25'                  # the Km cell of Table 2 in the PDF's text layer
    assert all(r['location'] == 'Table 2' for r in asp.values())
    assert any('it read 2.76E + 03 as 2.76' in (r.get('verify_note') or '') for r in cat['41657244'])
    assert any('2.76E + 03' in (r.get('quote') or '') for r in cat['41657244'])
    assert units.normalize('kcat', '2.76E + 03', 's^-1') == (2760.0, 's^-1', None)   # read as 2.76 x 10^3 today
    # Q1, the Convert caption 'the exponent is printed with spaces': the publisher's own table (its Europe PMC JATS, the
    # paper's text) prints the cell in Table 2 as '2.76E + 03', a space each side of the sign; the rows read from it are
    # Table 2's (the legend names the table)
    tb2_ = txt('texts', '41657244.txt').split('=== Table 2.', 1)[1].split('=== end table', 1)[0]
    assert '| 2.76E + 03 |' in tb2_ and 'Kinetic parameters for the hydrolysis of dAMP or dGMP' in tb2_
    src41_ = [r['text_source'] for r in csv.DictReader(open(P('papers.tsv'), encoding='utf-8'), delimiter='\t')
              if r['pmid'] == '41657244']
    assert len(src41_) == 1 and src41_[0].startswith('europepmc:') and src41_[0].endswith('.jats.xml'), src41_
    assert {r['location'] for r in cat['41657244'] if '2.76E + 03' in (r.get('quote') or '')} == {'Table 2'}
    F['convert_cap'] = 'the exponent is printed with spaces'
    del tb2_, src41_
    assert any(r['raw_unit'] == '×10^5 s^-1' and 'recovered' in (r.get('verify_note') or '') for r in cat['36756200'])
    assert any(r['metric'] == 'kcat/Km' and r['raw_unit'] == '×10^6 s^-1 mM^-1' and "'x10^6 S-1mM-1'" in (r.get('verify_note') or '')
               for r in cat['36756200'])
    assert 'it shows no kcat' in txt('paper', 'evidence', 'agent_highlights_20261028', 'finding_36756200_figure7d', 'README.md')
    assert any(r['row_id'] == 'a0a86a60a5ee60ca' and r['raw_value'] == '27,828 (24,558–31,987)'
               and 'recovered (bound_or_range)' in (r.get('verify_note') or '') for r in cat['42249657'])
    assert 'a bracketed interval goes with its value' in tax['CU4']['guard']
    assert any(r['row_id'] == '31bddf2a6ab75a25' and r['raw_value'] == '156 ± 4' and r['unit_for_conversion'] == 'mM-1 min-1'
               and 'blind re-read conflict judged from the paper, 3 of 3 refuters kept it' in (r.get('verify_note') or '')
               for r in cat['36394293'])
    assert 'a different value for an accepted slot is a conflict, kept apart and decided from the paper' in tax['IP4']['guard']
    # ---- R1 (the review: b's Check card drew 6354095's '0.0660.315', an OCR failure kind that is still open, TL7, whose 8
    # right Km values code refused and which are stored since 20 Oct from the full PDF, as if it were a learned rule). The
    # card's case is now TL11, a code check rule, chosen over IP4 (a re-read's conflict, 36394293: a misprinted unit header
    # again, as the Verify card, and not readable at a glance): a PDF text layer that draws the degree sign as 8 prints
    # 37 °C as '378C'; check() reads it as 37 °C, so a value keeps its temperature instead of losing it as not printed
    t11 = tax['TL11']
    assert (t11['status'], t11['guard_layer']) == ('rule', 'code check') and t11['class'].startswith('° drawn as 8') \
        and "check() reads '378C'" in t11['guard'], t11
    # the print as a real paper's text layer has it (TL11's own example, 20564561, prints the other form, 'at 378'):
    # 21455933 measured at 37 °C, which its text prints only as '378C' ('measured at 378C'). Every row of it keeps 37 °C,
    # and CatLog's own check() keeps it on its row through this rule alone: with the paper's text (less the warning line
    # CatLog writes over such a text) 37 °C is kept, and with the '378C' prints taken out the same row's temperature is
    # left empty as not printed
    t_ = txt('texts', '21455933.txt')
    assert t_.startswith("GLYPH WARNING: the text layer of this PDF shows ° as '8' (378C is 37 °C)")
    body_ = re.sub(r'^GLYPH WARNING[^\n]*\n+', '', t_)
    sq_ = catlog.squash(body_)
    assert 'measured at 378C' in body_ and 37.0 not in catlog.printed_numbers(sq_)
    r_ = cat['21455933']
    assert r_ and all(r['temperature_C'] == 37 for r in r_), len(r_)
    k_ = catlog.check(r_[0], sq_)[0]
    assert 'temperature_C' not in k_, k_                           # kept (check() returns a condition only to empty it)
    k_ = catlog.check(r_[0], re.sub(r'(?<![\d.])378 ?c\b', 'xxx', sq_))[0]
    assert k_.get('temperature_C', 0) is None and 'temperature_C 37 is not printed in the paper' in k_['condition_note'], k_
    assert any(re.search(rx, '378C') for rx in fetch.GLYPH_SIGNS.values())     # the warning line names it as well
    # Q1: the caption as CatLog's own warning line words it (the page prints °; only the PDF's text layer has 8)
    F['deg'] = dict(print='378C', kept='37 °C', cap='the PDF text shows ° as 8')
    assert "the text layer of this PDF shows ° as '8'" in t_.split('\n', 1)[0]
    S['check_card'] = ("paper/figures/method_overview/v5/taxonomy.tsv TL11 (status rule, guard_layer code check: check() "
                       "reads '378C' as 37 °C); texts/21455933.txt prints its 37 °C only as '378C' ('measured at 378C'); "
                       "catalog.jsonl: every 21455933 row at 37 °C; catlog.check on one keeps 37 °C, and leaves it empty "
                       "once the '378C' prints are taken out; fetch.GLYPH_SIGNS matches '378C'")
    del t11, t_, body_, sq_, r_, k_
    # the same record in the export: its protein, substrate, errors and checks
    wide = {}
    with open(P('catlog_wide.jsonl'), encoding='utf-8') as fh:
        for ln in fh:
            if 'cbb7818048a93f81' in ln or 'cb458776be25f46c' in ln or '"23214453"' in ln or '9b4f88de489c2372' in ln:
                r = json.loads(ln)
                if r['measurement_id'] == '9b4f88de489c2372':                # S1: d's refused Km, kept since in mg/mL
                    wide['xyl'] = r
                elif r['measurement_id'] == 'cbb7818048a93f81':
                    wide['asp'] = r
                elif r['measurement_id'] == 'cb458776be25f46c':          # W3: the paper's N248A, same substrate
                    wide['mut'] = r
                elif r['pubmed_id'] == '23214453' and r.get('kcat') == 10.0 and r.get('kcat_over_km') == 66.0:
                    wide['ratio'] = r
    w_ = wide['asp']
    assert (w_['pubmed_id'], w_['uniprot_id'], w_['ec_number'], w_['organism'], w_['substrate_name']) == \
        ('11106175', 'P00805', '3.5.1.1', 'Escherichia coli', 'L-asparagine')
    assert w_['gene'] == 'ansB'
    assert w_['enzyme_name'] == 'L-asparaginase II (EcA2)' and w_['wild_type'] and w_['smiles'] == 'NC(=O)C[C@H](N)C(=O)O'
    assert (w_['ph'], w_['temperature_c'], w_['kcat'], w_['kcat_err'], w_['km'], w_['km_err'], w_['kcat_over_km']) == \
        (7.0, 25, 24.0, 1.0, 0.015, 0.002, 1600.0)
    assert w_['ratio_check'].startswith('printed kcat/Km 1600 vs kcat/Km 1600 (1.00x')
    pv = w_['provenance']['Km']
    assert (pv['read_prompt'], pv['verify_prompt'], pv['pipeline_commit']) == ('71d79d74d63b', 'c4290cbd8f5e', '1f17a14f8b0f')
    F['asp'] = dict(uniprot=w_['uniprot_id'], ec=w_['ec_number'], sequence=w_['sequence'], smiles=w_['smiles'],
                    substrate=w_['substrate_name'], ph=w_['ph'], temp=w_['temperature_c'], location='Table 2',
                    p_kcat='2.4(±0.1)·10^1 s^-1', p_km='1.5(±0.2)·10^-5 mol L^-1', p_eff='1.6·10^6 M^-1 s^-1',
                    gene=w_['gene'],
                    read_prompt=pv['read_prompt'], verify_prompt=pv['verify_prompt'], commit=pv['pipeline_commit'],
                    enzyme=w_['enzyme_name'].split(' (')[0], organism=w_['organism'], kcat=w_['kcat'],
                    kcat_err=w_['kcat_err'], km=w_['km'], km_err=w_['km_err'], eff=w_['kcat_over_km'])
    assert F['asp']['enzyme'] == 'L-asparaginase II'
    # U1 (the record): its grey plates are its three catalogue rows' printed cells in the page's notation (the reader
    # wrote ' × ' for the page's centred dot and spaced the bracket), each with its column header's unit; no agent named
    # another unit (unit_for_conversion empty), and code converts each cell and its ± into the stored value
    # (units.normalize, catlog.printed_err), as the record's 'code converts' says
    for m_, k_ in (('kcat', 'p_kcat'), ('Km', 'p_km'), ('kcat/Km', 'p_eff')):
        r_ = asp[m_]
        assert re.sub(r'\s*×\s*', '·', r_['raw_value']).replace(' (± ', '(±') + ' ' + r_['raw_unit'] == F['asp'][k_], \
            (m_, r_['raw_value'])
        assert not r_.get('unit_for_conversion'), m_
    conv_ = {m_: units.normalize(m_, asp[m_]['raw_value'], asp[m_]['raw_unit'])[:2] for m_ in ('kcat', 'Km', 'kcat/Km')}
    assert [(round(v_, 9), u_) for v_, u_ in conv_.values()] == [(24.0, 's^-1'), (0.015, 'mM'), (1600.0, 'mM^-1 s^-1')], conv_
    assert [round(v_, 9) for v_, _ in conv_.values()] == [F['asp']['kcat'], F['asp']['km'], F['asp']['eff']]
    assert [catlog.printed_err(asp[m_]['raw_value'], conv_[m_][0], asp[m_]) for m_ in ('kcat', 'Km', 'kcat/Km')] == \
        [F['asp']['kcat_err'], F['asp']['km_err'], None]
    S['record_conv'] = ("catalog.jsonl b6b03f8089d0eaaf, 69a0cbccabbc7768, fde9c8a806405298 (11106175, Table 2): raw_value and "
                        "raw_unit = the plates; unit_for_conversion empty; units.normalize -> 24 s^-1, 0.015 mM, 1600 mM^-1 s^-1; "
                        "catlog.printed_err -> 1, 0.002, none")
    # R1 (the review: the drawn record leaves out what defines it, and the Linked row's N248A could be read as its own):
    # one grey line under the enzyme with its variant, pH, temperature and table, as the record and its three catalogue
    # rows hold them; the Linked row then calls N248A "its N248A mutant" (another record of the paper, wide['mut'] below)
    assert (w_['wild_type'], w_['mutation_signature'], w_['sequence_check']) == \
        (True, None, 'wild type: UniProt canonical sequence')
    assert all((r['variant'], r['pH'], r['temperature_C'], r['location']) == ('wild type', 7.0, 25, 'Table 2')
               for r in asp.values()) and {e['location'] for e in w_['evidence'].values()} == {'Table 2'}
    F['asp']['cond'] = f"wild type · pH {w_['ph']:.1f}, {w_['temperature_c']:g} °C · {F['asp']['location']}"
    assert F['asp']['cond'] == 'wild type · pH 7.0, 25 °C · Table 2', F['asp']['cond']
    # S1, fix 6 (the owner: "one record sounds odd ... properly explain it"): the box is 'A record', and on its title's line
    # what a record is, in CatLog's own definition (CLAUDE.md "State": one enzyme or variant, one substrate, one assay,
    # one paper, with up to three values; the code's measurement, one catlog_wide row). The drawn record is one: one
    # enzyme in one form (wild type), one substrate, one assay (pH 7.0, 25 °C, Table 2), one paper, three values
    cl1_ = re.sub(r'\s+', ' ', claude)
    assert '**record** (one row of the website: one enzyme or variant, one substrate, one assay, one paper, with up to ' \
           'three values)' in cl1_ and 'A record is what the code calls a measurement (one catlog_wide row)' in cl1_
    assert sum(1 for k_ in ('kcat', 'km', 'kcat_over_km') if w_[k_] is not None) == 3 and len(w_['evidence']) == 3
    F['record'] = dict(title='A record', define='one enzyme, substrate and assay of one paper')
    # U1 round 2 (the owner on U1: "the A record block, is that actually needed?"; the editor: bold 'A record' reads like
    # a panel letter, "the A record block"): 'A CatLog record', a record of the catalogue the box beside it counts; 'One
    # record' stays out (the owner, S1: "one record sounds odd")
    F['record']['title'] = 'A CatLog record'
    # S1r (the editor: "show what a record is rather than defining it"): the definition's parts become the record's own
    # field names, set in grey in the column of kcat, Km and kcat/Km: enzyme (with its organism and variant), substrate,
    # assay (pH, temperature and the table it is printed in, the paper's place); then its three values
    F['record']['fields'] = [('enzyme', [(f"{w_['enzyme_name'].split(' (')[0]}, ", ''), (w_['organism'], 'i'),
                                         (', wild type', '')]),
                             ('substrate', [(w_['substrate_name'], '')]),
                             ('assay', [(f"pH {w_['ph']:.1f}, {w_['temperature_c']:g} °C, Table 2", '')])]
    assert w_['wild_type'] and w_['substrate_name'] == 'L-asparagine' and (w_['ph'], w_['temperature_c']) == (7.0, 25)
    S['record_def'] = ('CLAUDE.md "State": record = one enzyme or variant, one substrate, one assay, one paper, with up to '
                       "three values (the code's measurement, one catlog_wide row); cbb7818048a93f81 holds three values")
    del cl1_
    # ---- W3 (6 Nov, the owner: "do we show the additional stuff we do like uniprot or substrate or even the mutation
    # sequence thing?"): c's second row, how code links the record (catlog_wide.jsonl, PMID 11106175): its enzyme to a
    # UniProt entry and that entry's sequence (signal peptide 1-22), a mutant of the same paper onto that sequence (the
    # paper numbers the mature chain), its substrate to ChEBI and the structure the record draws
    mu = wide['mut']
    for r in (w_, mu):
        assert (r['pubmed_id'], r['enzyme_name'], r['organism'], r['substrate_name']) == \
            ('11106175', 'L-asparaginase II (EcA2)', 'Escherichia coli', 'L-asparagine'), r['measurement_id']
        assert (r['uniprot_id'], r['uniprot_how'], r['ec_number']) == \
            ('P00805', 'gene ansB + organism, unique reviewed entry', '3.5.1.1'), r['measurement_id']
        assert (r['substrate_chebi'], r['smiles_id'], r['smiles_source'], r['smiles']) == \
            ('CHEBI:58048', 'CHEBI:58048', 'Rhea', w_['smiles']), r['measurement_id']
        assert r['smiles_how'].startswith('Rhea CHEBI:58048 "L-asparagine", a participant of the reactions of '
                                          'EC 3.5.1.1 and UniProt P00805 [name "L-asparagine" = given name]')
    us = w_['uniprot_sequence']
    assert w_['sequence'] == us and len(us) == 348 and w_['sequence_frame'] == 'UniProt canonical'
    assert us[:22] == 'MEFFKKTALAALVMGFSGAALA' and us[22:37] == 'LPNITILATGGTIAG'
    assert (mu['mutation_signature'], mu['wild_type'], mu['kcat'], mu['km'], mu['kcat_over_km']) == \
        ('N248A', False, 7.0, 0.095, 74.0)
    assert mu['sequence_frame'] == 'mature chain after the signal 1-22 (+22)'
    assert mu['sequence_check'] == ('mutations applied in mature chain after the signal 1-22 (+22) (G11 = G33, V27 = V49, '
                                    'G57 = G79, Q59 = Q81, G88 = G110, N248 = N270); every wild-type residue of the '
                                    "paper's mutations matches")
    ms = mu['sequence']
    assert mu['uniprot_sequence'] == ms and len(ms) == 348 and us[269] + ms[269] == 'NA' \
        and [i + 1 for i in range(348) if ms[i] != us[i]] == [270]          # the stored mutant: N270A of P00805, only
    F['link'] = dict(uniprot='P00805', ec='3.5.1.1', chebi='58048', residues=348, signal=22, mutation='N248A',
                     paper_pos=248, pos=270)
    L_ = F['link']
    assert (L_['mutation'][1:-1], L_['paper_pos'] + L_['signal'], len(us), f"CHEBI:{L_['chebi']}") == \
        (str(L_['paper_pos']), L_['pos'], L_['residues'], mu['substrate_chebi'])
    assert f"signal 1-{L_['signal']} (+{L_['signal']})" in mu['sequence_frame'] \
        and f"N{L_['paper_pos']} = N{L_['pos']}" in mu['sequence_check']
    # checker: 'substrate of EC 3.5.1.1' (not only 'a participant'): the Rhea reaction that smiles_how matched, the one
    # reaction of EC 3.5.1.1 and P00805 in CatLog's Rhea files, has L-asparagine (CHEBI:58048) on its left side
    rx = {r_[0].split(':')[1]: r_ for r_ in csv.reader(open(P('sources', 'ref', 'rhea_participants.tsv'), encoding='utf-8'),
                                                       delimiter='\t') if r_ and r_[0].startswith('RHEA:')}
    ec_rx = {r_[0] for r_ in csv.reader(open(P('sources', 'ref', 'rhea2ec.tsv'), encoding='utf-8'), delimiter='\t')
             if len(r_) == 4 and r_[3] == L_['ec']}
    up_rx = {r_[0] for r_ in csv.reader(open(P('sources', 'ref', 'rhea2uniprot_sprot.tsv'), encoding='utf-8'), delimiter='\t')
             if len(r_) == 4 and r_[3] == L_['uniprot']}
    assert ec_rx & up_rx == {'21016'}, (ec_rx, up_rx)
    # Q1 ('found in the reaction of EC 3.5.1.1'): EC 3.5.1.1 has this one Rhea reaction in CatLog's Rhea files
    assert ec_rx == {'21016'}, ec_rx
    eq, ids = rx['21016'][1], rx['21016'][2].split(';')
    assert eq.split(' = ')[0] == 'L-asparagine + H2O' and ids[0] == f"CHEBI:{L_['chebi']}" \
        and f"EC:{L_['ec']}" in rx['21016'][3].split(';'), rx['21016']
    S['links'] = ('catlog_wide.jsonl cbb7818048a93f81 (the record c draws) and cb458776be25f46c (N248A, L-asparagine): '
                  'uniprot_id P00805, uniprot_how "gene ansB + organism, unique reviewed entry", ec_number 3.5.1.1; '
                  'uniprot_sequence 348 residues, 1-22 MEFFKKTALAALVMGFSGAALA; sequence_frame "mature chain after the '
                  'signal 1-22 (+22)", sequence_check "... N248 = N270); every wild-type residue of the paper\'s mutations '
                  'matches", the stored sequence differs from P00805 at 270 only (N to A); substrate_chebi CHEBI:58048, '
                  'smiles_how "Rhea ... a participant of the reactions of EC 3.5.1.1 and UniProt P00805"')
    S['links'] += ('; sources/ref: RHEA:21016 "L-asparagine + H2O = L-aspartate + NH4(+)", the one reaction of EC 3.5.1.1 '
                   'and P00805 (rhea2ec.tsv, rhea2uniprot_sprot.tsv), CHEBI:58048 on its left side')
    # S1r (the editor: "ChEBI 58048 is the zwitterion that Rhea uses, while the drawing is the neutral form"): so it is.
    # CHEBI:58048 is L-asparagine zwitterion (Rhea's pH 7.3 form of CHEBI:17196); CatLog stores one neutral SMILES per
    # substrate (structures.py), which is the drawn one. The Linked row now ends on the drawing, marked 'neutral form'
    import gzip
    ch_ = [ln.rstrip('\n').split('\t') for ln in gzip.open(P('sources', 'ref', 'chebi_compact.tsv.gz'), 'rt', encoding='utf-8')
           if ln.startswith('CHEBI:58048\t') or ln.startswith('CHEBI:17196\t')]
    ch_ = {r_[0]: r_ for r_ in ch_}
    assert ch_['CHEBI:58048'][2:] == ['L-asparagine zwitterion', 'NC(=O)C[C@H]([NH3+])C(=O)[O-]'], ch_
    assert ch_['CHEBI:17196'][3] == w_['smiles'] == 'NC(=O)C[C@H](N)C(=O)O', ch_['CHEBI:17196']
    assert any(ln.rstrip('\n').split('\t')[:3] == ['CHEBI:17196', 'CHEBI:58048', 'Rhea pH 7.3 form']
               for ln in open(P('sources', 'ref', 'chebi_conj.tsv'), encoding='utf-8'))
    F['link']['drawn'] = 'neutral form'
    # T1 (S2; the owner on S1r: "the linked by code stuff needs more work, i think the whole box can be improved"): the
    # row's title says when code makes these links, 'after reading': /batch enriches after add, and cmd_enrich links every
    # catalogue row (UniProt accession and sequence, substrate SMILES); and the sequence bar's grey block is named in full,
    # 'signal peptide': residues 1-22 are UniProt's Signal feature of P00805, the span the mutant's frame counts (+22)
    assert 'get → read → verify → add → enrich → export' in txt('.claude', 'commands', 'batch.md')
    assert 'UniProt accession + sequence and substrate SMILES for every catalog row' in txt('catlog.py')
    F['link']['when'] = 'after reading'
    pl_ = json.load(open(P('enrich', 'protein_lookups.json'), encoding='utf-8'))['entry'][L_['uniprot']]['features']
    assert pl_ == [['Signal', 1, L_['signal']]], pl_
    F['link']['signal_name'] = 'signal peptide'
    S['links'] += ('; .claude/commands/batch.md "get → read → verify → add → enrich → export" and catlog.py cmd_enrich '
                   '("UniProt accession + sequence and substrate SMILES for every catalog row"): the links are made after '
                   'reading; enrich/protein_lookups.json P00805 features [Signal 1-22]')
    del pl_
    S['links'] += ('; sources/ref/chebi_compact.tsv.gz: CHEBI:58048 "L-asparagine zwitterion" NC(=O)C[C@H]([NH3+])C(=O)[O-], '
                   'CHEBI:17196 the neutral NC(=O)C[C@H](N)C(=O)O = the record\'s smiles; chebi_conj.tsv: 58048 is 17196\'s '
                   '"Rhea pH 7.3 form"')
    del ch_
    # ---- S1, fix 4 (the owner: "the linked by code ... icons ... a little bit AI-ish ... We can even get the structure
    # from the EMBL or UniProt"): the Linked row shows the predicted structure of the record's UniProt entry, P00805, in
    # place of the glyph icons. AlphaFold DB entry AF-P00805-F1 version 6 (CC BY 4.0), the mature chain (23-348) drawn
    # with open-source PyMOL, residue 270 (Asn, the paper's N248) as dark spheres; files in structure/.
    # Checked here: the picture is the prepared one, the entry file is the downloaded one, its sequence is the record's
    # UniProt sequence, its residue 270 is Asn, and the dark spheres sit where the row's pointer ends
    import hashlib
    pv0_ = json.load(open(STRUCT_PROV, encoding='utf-8'))
    png_b = open(STRUCT_PNG, 'rb').read()
    assert hashlib.sha256(png_b).hexdigest() == pv0_['images'][os.path.basename(STRUCT_PNG)]['sha256'] == STRUCT_SHA
    # S1r: the same entry file as the assets' picture (their provenance, read here, names the same download); T1 round 2:
    # and as the slate picture's, of the same view, only its cartoon and outline colours changed
    pva_ = json.load(open(os.path.join(ASSETS, 'P00805_AF_v6_N270.provenance.json'), encoding='utf-8'))
    pvs_ = json.load(open(os.path.join(ASSETS, 'P00805_AF_v6_N270_slate.provenance.json'), encoding='utf-8'))
    assert pva_['source'] == pv0_['source'] == pvs_['source'] and pv0_['render']['colours']['cartoon'].startswith('#8491B4')
    pvg_ = json.load(open(os.path.join(ASSETS, 'P00805_AF_v6_N270_grey.provenance.json'), encoding='utf-8'))   # M2: the grey one, kept
    assert pvg_['source'] == pv0_['source'] and pvg_['render']['view'] == pv0_['render']['view']
    del pvg_
    assert pv0_['render']['view'] == pvs_['render']['view'] and pv0_['render']['colours']['outline'] == '#3C4766' \
        and pv0_['render']['colours']['residue_270'] == pvs_['render']['colours']['residue_270']
    del pva_, pvs_
    assert (pv0_['source']['entry'], pv0_['source']['version'], pv0_['source']['database']) == \
        ('AF-P00805-F1', 6, 'AlphaFold Protein Structure Database (EMBL-EBI)') and pv0_['licence'].startswith('CC BY 4.0')
    cif_ = open(os.path.join(ASSETS, 'download', 'AF-P00805-F1-model_v6.cif'), 'rb').read()
    assert hashlib.sha256(cif_).hexdigest() == pv0_['source']['file_sha256'] == \
        'ff96faf388b66da74712e9099c52dc2d6a7446351340e75adf8b59ae9a8de4c0'
    cif_ = cif_.decode('utf-8')
    seq_ = re.search(r'_entity_poly\.pdbx_seq_one_letter_code_can\s*\n;([A-Z\s]+)\n;', cif_).group(1)
    assert re.sub(r'\s+', '', seq_) == us and len(us) == 348                     # the record's UniProt P00805 sequence
    assert re.search(r'\n1 n ASN 270 \n', cif_) and us[269] == 'N'
    assert '"Data in this file is available under a CC-BY-4.0 license."' in cif_ \
        and 'https://creativecommons.org/licenses/by/4.0/' in cif_
    from PIL import Image
    import io
    import numpy as np
    im_ = Image.open(io.BytesIO(png_b)).convert('RGBA')
    a_ = np.asarray(im_).astype(float)
    # S1r: the ink spheres only (luminance under 55; the darker cartoon's outline, #3C4766, is 71)
    dark_ = (a_[..., 3] > 200) & (0.2126 * a_[..., 0] + 0.7152 * a_[..., 1] + 0.0722 * a_[..., 2] < 55)
    ys_, xs_ = np.nonzero(dark_)
    mk_ = (xs_.mean() / im_.width, ys_.mean() / im_.height)
    assert im_.size == (600, 421) and all(abs(u - v) < 0.005 for u, v in zip(mk_, pv0_['images']['marker_centre_fraction_of_width_height'])), mk_
    assert xs_.max() - xs_.min() < 60 and ys_.max() - ys_.min() < 70, 'one cluster: the spheres'
    F['struct'] = dict(px=im_.size, marker=(round(mk_[0], 3), round(mk_[1], 3)),
                       dark=(xs_.min() / im_.width, (xs_.max() + 1) / im_.width, ys_.min() / im_.height, (ys_.max() + 1) / im_.height),
                       entry='AF-P00805-F1', version=6, plddt=pv0_['source']['global_plddt'])
    assert F['struct']['plddt'] == 94.81 and pv0_['residue_check']['residue_270'].startswith('ASN')
    S['struct'] = (f"{os.path.basename(STRUCT_PNG)} (sha256 {STRUCT_SHA[:8]}..., as its provenance in this folder): AlphaFold DB "
                   'AF-P00805-F1 v6, CC BY 4.0; the entry file (sha256 ff96faf3...) carries the 348-residue sequence of '
                   f"catlog_wide's P00805 and Asn at 270; dark spheres centred at {F['struct']['marker']} of the picture")
    del pv0_, png_b, cif_, seq_, im_, a_, dark_, ys_, xs_, mk_
    # ---- H6 (MISSING_COMPONENTS item 2): the foot line of c's record, "each value keeps the paper's line, the agents,
    # instructions and code version". Each of the drawn record's three values keeps the line of the paper it was read from
    # (its quote, as the PDF's text layer has it, and its place, Table 2), the reading and checking agents, the
    # instructions they followed (a hash whose full text is kept and hashes to it) and the code's version (a commit of
    # this repository). This record's stamp was rebuilt from the agents' logs ('reconstructed'), as for values stored
    # before stamping began on 21 Oct; the line names no model, so the switch its log shows needs no word
    import hashlib
    assert set(w_['evidence']) == set(w_['provenance']) == {'kcat', 'Km', 'kcat/Km'}
    for m_ in ('kcat', 'Km', 'kcat/Km'):
        ev_, pv_ = w_['evidence'][m_], w_['provenance'][m_]
        assert ev_['location'] == 'Table 2' and ev_['quote'].startswith('Wild-type') and '2.4~60.1!{10 1' in ev_['quote']
        assert pv_['read_by'] == 'reader' and pv_['how'] == 'reconstructed'
        assert pv_['reader_model'] and pv_['verifier_model'], m_
        assert (pv_['read_prompt'], pv_['verify_prompt'], pv_['pipeline_commit']) == ('71d79d74d63b', 'c4290cbd8f5e', '1f17a14f8b0f')
    for h_ in ('71d79d74d63b', 'c4290cbd8f5e'):
        assert hashlib.sha256(open(P('sources', 'prompt_versions', f'{h_}.md'), 'rb').read()).hexdigest()[:12] == h_
    assert subprocess.run(['git', '-C', ROOT, 'cat-file', '-t', '1f17a14f8b0f'], capture_output=True, text=True, check=True,
                          env=dict(os.environ, GIT_OPTIONAL_LOCKS='0')).stdout.strip() == 'commit'
    assert {'quote', 'location'} <= set(catlog.NEEDED) and set(F['stamp']) <= set(catlog.STAMP)
    S['trail'] = ('catlog_wide.jsonl cbb7818048a93f81: evidence (quote, location Table 2) and provenance (reader_model, '
                  'verifier_model, read_prompt 71d79d74d63b, verify_prompt c4290cbd8f5e, pipeline_commit 1f17a14f8b0f, how '
                  'reconstructed) for kcat, Km and kcat/Km; sources/prompt_versions/<hash>.md hash to their names; '
                  '1f17a14f8b0f is a commit; catlog.NEEDED (quote, location), catlog.STAMP')
    F['exp_print'], F['exp_once'] = '2.76E + 03', '2.76'      # 41657244: the code once read the spaced exponent as 2.76
    assert units.normalize('kcat', F['exp_print'], 's^-1')[0] == float(F['exp_once']) * 1000
    rt = wide['ratio']
    assert rt['ratio_check'].startswith('printed kcat/Km 66 vs kcat/Km 6.667 (9.90x') and 'kept as printed' in rt['ratio_check']
    assert rt['evidence']['kcat/Km']['raw_value'] == '6.6 (0.2) × 10^4' and rt['evidence']['kcat/Km']['raw_unit'] == 'M^{−1} s^{−1}'
    assert rt['evidence']['kcat/Km']['raw_value'] == '6.6 (0.2) × 10^4' and 'differs from kcat ÷ Km by 9.9×' in rt['kcat_over_km_note']
    # values CatLog refused, with their reasons
    rej = collections.defaultdict(list)
    with open(P('rejected.jsonl'), encoding='utf-8') as fh:
        for ln in fh:
            if any(q_ in ln for q_ in ('12591933', '21443518', '36394293', '25658941', '10767281')):
                r = json.loads(ln)
                rej[r.get('pmid')].append(json.dumps(r, ensure_ascii=False))
    # Q1: 26142822's refused K0.5 and 'K_m = 19 μM' are no longer drawn (b's Read card is 25658941's, below)
    assert any('kcat 622 s-1, Km 2.2 mM' in t and 'Chen et al. 2002' in t and '11694539' in t for t in rej['12591933'])
    assert any('505215' in t and '1065 ± 97 units/mg' in t and '28464 kDa' in t for t in rej['21443518'])
    # R1: 6354095's merged OCR cell ('0.0660.315', TL7, still open) is no longer drawn; b's Check card shows TL11 (above)
    assert any('505215 ± 3083' in t and '1065 ± 97 units/mg' in t for t in rej['21443518'])
    assert any('conflicts with accepted row 31bddf2a6ab75a25 (156 ± 4 mM^-1 s^-1)' in t and 'mM-1 min-1' in t
               for t in rej['36394293'])
    bd = [json.loads(ln) for ln in open(P('bounds.jsonl'), encoding='utf-8') if '10390216' in ln]
    assert any(r['metric'] == 'kcat/Km' and r['raw_value'] == '<0.02' and r['bound'] == 20.0 and 'ztreonam' in r['substrate']
               for r in bd), [(r['substrate'], r['metric'], r['raw_value'], r['bound']) for r in bd][:6]
    # approved values the agents read again (HUMAN_REVIEW.md: old_value_not_in_paper), and a database's copy
    um = {}
    found = {}
    for f_ in ('unmatched_20261010.tsv', 'unmatched_20261011.tsv', 'unmatched_20261012b.tsv'):
        for r in csv.DictReader(open(P('human_review', f_), encoding='utf-8'), delimiter='\t'):
            if r['verdict'] == 'old_value_not_in_paper':
                um[(r['pmid'], r['metric'])] = r
            found.setdefault(r['pmid'], []).append(r['cause'])
    a1 = um[('20522910', 'kcat')]
    assert a1['human_value_catalog_units'] == '0.012' and '7.1 ± 1.7 min^-1' in a1['paper_cell'] and '(0.118 s^-1)' in a1['cause']
    # what the comparison with people's approved records exposed (10 and 11 Oct), and the rule each became
    assert any("v2 puts the isoform name 'AKR1C21* (DD1)' in variant" in c_ and 'a natural isoform, not a mutant' in c_
               for c_ in found['15577209']) and any('v2 labels it AKR1C21 (DD3)' in c_ for c_ in found['15577209'])
    assert any(ln.startswith('15577209\tAKR1C21 (DD3)\t') for ln in open(P('sources', 'natural_forms.tsv'), encoding='utf-8'))
    assert tax['IP6']['found'].startswith('2026-10-10 reviewer: human review') and tax['IP6']['status'] == 'rule'
    assert any('v2 labelled lung PGFS Q3ZCJ2 (AK1A1_BOVIN aldehyde reductase)' in c_ for c_ in found['1339268'])
    assert 'lung PGFS, then EC 1.1.1.2, got aldehyde reductase AKR1A1' in txt('tools', 'sequences.py')
    c21 = [r for r in csv.DictReader(open(P('sources', 'database_corrections.tsv'), encoding='utf-8'), delimiter='\t')
           if r['row_id'] == 'e5f56c293359c5b3']
    assert c21 and c21[0]['database'] == 'BRENDA, OED' and c21[0]['database_value'].startswith('681.5') \
        and 'prints 6 ± 1.5' in c21[0]['evidence'] and 'prints the ± as 8' in c21[0]['evidence']
    # where papers come from
    cov = collections.Counter()
    for r in csv.DictReader(open(P('sources', 'coverage.tsv'), encoding='utf-8'), delimiter='\t'):
        cov['cited'] += r['db_values'] not in ('', '0')
        # Y2: the Km-only search (papers that print Km but no kcat, sources/discovered_km_20261109; commit 4df707d, 9 Nov)
        # joined the 'discovered' column as tiers km_table, km_abstract and km_body; the box counts the kcat search drawn
        # since U1 (its tiers table, abstract and body). Whether the box should also count the Km-only papers is the
        # owner's call
        cov['searched'] += r['discovered'] not in ('', '0') and not r['discovered'].startswith('km_')
        cov['tier ' + r['discovered']] += 1
    assert cov['searched'] == 30814 == cov['tier table'] + cov['tier abstract'] + cov['tier body'], cov
    assert (cov['tier table'], cov['tier abstract'], cov['tier body']) == (10799, 6297, 13718), cov
    assert {k_[5:] for k_ in cov if k_.startswith('tier ')} - {'', 'table', 'abstract', 'body'} \
        == {'km_table', 'km_abstract', 'km_body'}, cov
    cited = {r['pmid'] for r in csv.DictReader(open(P('sources', 'db_values.tsv'), encoding='utf-8'), delimiter='\t')}
    assert len(cited) == 44407, len(cited)      # the six databases of panel a (coverage.tsv's 40,788 leaves UniProt out)
    F['cited'], F['searched'] = '44,407', '30,814'
    # FINAL PASS check (16 Nov): b's frozen catalogue also holds papers of the second Europe PMC search, the Km-only one
    # (papers that mention a Km with kinetic words but no kcat; 30 of them read at the catalogue's freeze), so the legend
    # names both searches. Its count is the Europe PMC freeze's (paper/evidence/europepmc_freeze_20261116/numbers.json,
    # 'Papers listed by the search (new to CatLog)'), equal to the Km tiers of coverage.tsv at the catalogue's tag
    epmc_ = json.load(open(P('paper', 'evidence', 'europepmc_freeze_20261116', 'numbers.json'), encoding='utf-8'))
    km_ = epmc_['lists']['km']
    assert km_['listed'] == cov['tier km_table'] + cov['tier km_abstract'] + cov['tier km_body'] == 93868 and \
        km_['by_tier'] == {k_: cov['tier ' + k_] for k_ in ('km_table', 'km_abstract', 'km_body')} and \
        km_['listed_papers_in_database_table'] == 0 and epmc_['lists']['kcat']['listed'] == cov['searched'] and \
        epmc_['lists']['kcat']['listed_papers_in_database_table'] == 443 and epmc_['by_list']['km']['papers_read'] > 0, km_
    assert "Km mode (`km`, the user 2026-11-09: read AFTER the current queue): papers that print Km but no kcat." in \
        re.sub(r'\s+', ' ', txt('tools', 'discover_europepmc.py')) and \
        "NO_KCAT = 'NOT (kcat OR \"k cat\" OR \"turnover number\")'" in txt('tools', 'discover_europepmc.py')
    F['searched_km'] = f"{km_['listed']:,}"
    S['searched_km'] = ('paper/evidence/europepmc_freeze_20261116/numbers.json lists.km.listed (93,868; new to CatLog, none '
                        'in the database table) = coverage.tsv km_* tiers at the catalogue\'s tag; tools/discover_europepmc.py km')
    del epmc_, km_
    # U1 (the owner's point 2): the Papers box says 'from a literature search', the search tool's own words, and the
    # legend what it searched for: papers that mention kcat and Km and that no database cites
    ds_ = re.sub(r'\s+', ' ', txt('tools', 'discover_europepmc.py'))
    assert 'Papers with kinetics that NO database cites: a literature search in Europe PMC' in ds_ \
        and 'ALL (kcat OR "k cat" OR "turnover number") AND (Km OR "K m" OR Michaelis)' in ds_
    # U1 round 2 (the legend): 'that no database cited when the search was run', not 'that no database cites': the search
    # left out every paper the database table held then, but 443 of the 30,814 have UniProt values in today's table
    assert 'Left out: every PMID or DOI CatLog already knows (queue, coverage.tsv, every config.json source, the ' \
           'database table' in ds_
    srch_ = {r['pmid'] for r in csv.DictReader(open(P('sources', 'coverage.tsv'), encoding='utf-8'), delimiter='\t')
             if r['discovered'] not in ('', '0')}
    both_ = collections.Counter(r['source'] for r in csv.DictReader(open(P('sources', 'db_values.tsv'), encoding='utf-8'),
                                                                    delimiter='\t') if r['pmid'] in srch_)
    assert set(both_) <= {'UniProt'}, both_          # only UniProt's later entries cite any of them today
    del srch_, both_
    S['searched'] = ('tools/discover_europepmc.py: "a literature search in Europe PMC", kcat AND Km terms, papers no '
                     'database cites')
    del ds_
    # ---- Q1: b's Read card, 25658941 (YhdE, E. coli), in place of 26142822 (c's own enzyme, whose Table 1 cites c's paper
    # for a Km 'assuming no cooperativity'). Table 1 heads its column 'Km (mM)' and prints a Hill coefficient of 2.2 on
    # the dTTP row, and the paper calls the binding cooperative: the 'Km' is a Hill constant (a judgment trap, not a
    # misread character). read.md skips such a Km 'even under a "Km"/"apparent Km" header'. CatLog's one read (29 Oct)
    # skipped every Km and kcat/Km of the table and kept the two kcat with a Hill note; RA1 names this paper as a wrong
    # certified row of the earlier catalogue; BRENDA, OED and UniProt list the dTTP Km; a plain reading by the same model
    # stored all four trap cells (the hard cases of Fig. 2)
    t_h = txt('texts', '25658941.txt')
    assert re.search(r'Km \(mM\)\s+Vmax \(mM s-1\)\s+kcat \(s-1\)\s+kcat/Km \(mM-1 s-1\)\s+N \(Hill\)', t_h)
    assert re.search(r'\ndTTP\s+0\.09\s+0\.06\s+43\s+503\s+2\.2\n', t_h) and 'Table 1. Kinetic analysis of YhdE' in t_h
    t_hs = re.sub(r'\s+', ' ', t_h)
    assert "Hill’s coefficients are approximately two, indicating that two substrate molecules follow a non- " \
           "Michaelis-Menten model and participate in positive cooperative binding" in t_hs
    read_s = re.sub(r'\s+', ' ', read)
    assert 'This holds even under a "Km"/"apparent Km" header: if the same table or paragraph gives a Hill coefficient ' \
           'clearly ≠ 1 or calls the kinetics cooperative/non-Michaelis-Menten, skip that Km and its kcat/Km' in read_s
    assert 'Hill constants (K0.5, S0.5, or an "apparent Km" from a Hill fit with n clearly ≠ 1)' in read_s \
        and 'are NOT Km or kcat. Skip them.' in read_s
    rh_ = cat['25658941']
    assert sorted((r['metric'], r['raw_value'], r['substrate']) for r in rh_) == [('kcat', '43', 'dTTP'), ('kcat', '95', 'UTP')]
    assert any(r['row_id'] == '440679477253ba6a' and 'Hill fit, n = 2.2' in r['metric_note'] for r in rh_)
    assert not rej['25658941']                     # skipped by the reader, not refused afterwards
    adds_h = [ln.split('\t') for ln in open(P('log.tsv'), encoding='utf-8') if '\t25658941\tadd\t' in ln]
    assert len(adds_h) == 1 and adds_h[0][0] == '2026-10-29 07:38' and adds_h[0][3] == 'kept=2', adds_h
    rj_ = json.load(open(P('work', '25658941.read.json'), encoding='utf-8'))
    assert 'Km (0.09 / 0.5 mM) and kcat/Km (503 / 191 mM-1 s-1) are skipped: Table 1 gives Hill N = 2.2' in rj_['note']
    kmdb_ = {r['source'] for r in csv.DictReader(open(P('sources', 'db_values.tsv'), encoding='utf-8'), delimiter='\t')
             if r['pmid'] == '25658941' and r['metric'] == 'Km' and r['substrate'] == 'dTTP' and float(r['value']) == 0.09}
    assert kmdb_ == {'BRENDA', 'OED', 'UniProt'}, kmdb_
    # checker: the column holds two Hill constants, the UTP row's beside n = 1.9, and the three databases list that one as
    # a Km too (the legend says 'Hill coefficients of 2.2 and 1.9' and 'list them as Km')
    assert re.search(r'\nUTP\s+0\.5\s+0\.14\s+95\s+191\s+1\.9\n', t_h)
    kmdb2_ = {r['source'] for r in csv.DictReader(open(P('sources', 'db_values.tsv'), encoding='utf-8'), delimiter='\t')
              if r['pmid'] == '25658941' and r['metric'] == 'Km' and r['substrate'] == 'UTP' and float(r['value']) == 0.5}
    assert kmdb2_ == {'BRENDA', 'OED', 'UniProt'}, kmdb2_
    del kmdb2_
    hc_ = [r for r in json.load(open(P('paper', 'evidence', 'hard_cases_20261102', 'summary.json'), encoding='utf-8'))
           if r['pmid'] == '25658941']
    assert len(hc_) == 1 and (hc_[0]['class_id'], hc_[0]['model'], hc_[0]['cells'], hc_[0]['trap'], hc_[0]['catlog_trap'],
                              hc_[0]['catlog_first_fell_in']) == ('RA1', 'Opus 5.5', 4, 4, 0, False), hc_
    f2b_ = txt('paper', 'figures', 'fig2_plain_vs_catlog', 'build_fig2.py')
    assert 'hard_cases_20261102/summary.md' in f2b_ and "'RA1': 'Hill, Adair or K0.5 as Km'" in f2b_
    assert [r['status'] for r in csv.DictReader(open(P('papers.tsv'), encoding='utf-8'), delimiter='\t')
            if r['pmid'] == '25658941'] == ['done']
    F['hill'] = dict(print='Km, Hill n = 2.2', cap='a Hill constant is not a Km', table='Table 1', n='2.2', n2='1.9',
                     plain_cells=hc_[0]['trap'])
    assert F['hill']['n'] in F['hill']['print']
    S['read_card'] = ('texts/25658941.txt Table 1 ("Km (mM) ... N (Hill)", "dTTP 0.09 0.06 43 503 2.2"; Discussion: '
                      '"non-Michaelis-Menten model and participate in positive cooperative binding"); prompts/read.md '
                      '(Hill constants are NOT Km or kcat, "even under a \'Km\'/\'apparent Km\' header"); catalog.jsonl '
                      'holds kcat 43 and 95 only (440679477253ba6a "Hill fit, n = 2.2"); work/25658941.read.json note; '
                      'taxonomy RA1 found "25658941 (Hill) ... wrong in old certified rows"; db_values.tsv BRENDA, OED, '
                      'UniProt Km 0.09 mM dTTP; hard_cases_20261102/summary.json: plain Opus 5.5 stored 4 of 4 trap cells')
    del t_h, t_hs, read_s, rh_, adds_h, rj_, kmdb_, hc_, f2b_
    # the papers the figure draws from: c's record (11106175) and b's four examples (X1: Convert 25528584 and Check
    # 14769870 in place of 41657244's '2.76E + 03' and 21455933's '378C'; facts_b2 checks them)
    F['pmids'] = ['11106175', '25528584', '14676218', '14769870', '25658941']
    assert not set(F['pmids']) & locked, set(F['pmids']) & locked
    # ---- 2026-11-05: d as the loop, counted. Who first found each new kind of error (the taxonomy's found_route), the
    # rules by where they live, the agent-highlights chat's 162 checked agent findings, the hard-case test
    new_ = [r for r in tax.values() if r['novelty'] == 'new']
    fr = collections.Counter(r['found_route'] for r in new_)
    assert fr == {'operator': 24, 'code check': 9, 'outside review': 8, 'audit': 5, 'reviewer': 5, 'verifier': 4,
                  'sweep': 2, 'owner': 1, 'database check': 1}, fr
    F['finders'] = [('people', 'people (reviewers, the owner)', fr['reviewer'] + fr['owner']),
                    (('people', 'agent'), 'the owner and an agent, running CatLog', fr['operator']),
                    ('agent', 'agents (verifier, audits, database checks)', fr['verifier'] + fr['audit'] + fr['database check']),
                    ('code', 'code checks and scans', fr['code check'] + fr['sweep']),
                    ('outside', 'outside reviews', fr['outside review'])]
    F['new_kinds'] = len(new_)
    assert sum(n_ for *_, n_ in F['finders']) == F['new_kinds'] == 59
    lay = collections.Counter(r['guard_layer'] for r in tax.values() if r['status'] == 'rule')
    F['layers_n'] = dict(lay)
    F['n_prompt'] = lay['reader prompt'] + lay['verifier prompt']
    F['n_code'] = lay['code conversion'] + lay['code check']
    F['n_db'] = lay['database check']
    assert (F['n_prompt'], F['n_code'], F['n_db']) == (23, 45, 3) and sum(lay.values()) == 71
    # Y2 (the owner's point 3, "focusing on how many rules there are, as the expanse of the system"): b's title gives the
    # total, the sum of its four cards' counts (16 + 10 + 7 + 35); the database check's 3 rules act after reading and
    # have no card, so the legend names them
    F['rules_b'] = lay['reader prompt'] + lay['code conversion'] + lay['verifier prompt'] + lay['code check']
    assert F['rules_b'] == 68 == sum(lay.values()) - lay['database check'], F['rules_b']
    # ---- FINAL PASS (16 Nov): the rules drawn are Fig. 4a's 73, so that the two figures count one set. Fig. 4's evidence
    # (writing/figures/fig4/v2/evidence/rules/rules.csv, its cut of 15 Nov 00:30, 10,276 papers read) lists the 85 kinds
    # of the list of 2 November above (taxonomy.tsv) and two kinds found after it, both rules: X1, figure captions left
    # out of an article's text (found by a code check), and X2, a table cell holding only a drawn structure rendered empty
    # (found in the session with an agent); both act in Convert (the code that turns a paper into the text the agents
    # read). By the step each acts in (rules.csv rule_step): Read 16, Convert 12, Verify 7, Check 35, and the database
    # check after reading 3 (DB1, DB3, PR17, above), which Decide's foot now counts (it had none), so the five feet add
    # up to the Co-learning box's 73. Checked against the taxonomy (its 71 by guard_layer, each the same step) and
    # against Supplementary Table 4 (writing/figures/extended_data/rules_reach/rules_table.tsv, the 73 by step)
    rcsv_ = list(csv.DictReader(open(P('writing', 'figures', 'fig4', 'v2', 'evidence', 'rules', 'rules.csv'), encoding='utf-8')))
    st_all = collections.Counter(r['status'] for r in rcsv_)
    assert len(rcsv_) == 87 and st_all == {'rule': 73, 'flag kept as printed': 4, 'open': 10}, st_all
    STEP_OF = {'reader prompt': 'Read', 'code conversion': 'Convert', 'verifier prompt': 'Verify', 'code check': 'Check',
               'database check': 'Database check'}
    rl73_ = [r for r in rcsv_ if r['status'] == 'rule']
    assert {r['id'] for r in rl73_ if r['on_list_of_2_nov'] == 'yes'} == {k_ for k_, r in tax.items() if r['status'] == 'rule'} \
        and all(STEP_OF[tax[r['id']]['guard_layer']] == r['rule_step'] for r in rl73_ if r['id'] in tax), 'the list\'s 71, each in its step'
    later_ = sorted((r['id'], r['rule_step'], r['first_found_by'], r['first_found_route']) for r in rcsv_ if r['on_list_of_2_nov'] != 'yes')
    assert later_ == [('X1', 'Convert', 'code', 'code check'), ('X2', 'Convert', 'agents', 'operator')], later_
    assert rcsv_[[r['id'] for r in rcsv_].index('X1')]['kind'].startswith('Figure captions') and \
        rcsv_[[r['id'] for r in rcsv_].index('X2')]['kind'].startswith('A table cell holding only a drawn structure'), 'X1, X2'
    by_step_ = collections.Counter(r['rule_step'] for r in rl73_)
    assert by_step_ == {'Read': 16, 'Convert': 12, 'Verify': 7, 'Check': 35, 'Database check': 3}, by_step_
    st4_ = [r for r in csv.DictReader(open(P('writing', 'figures', 'extended_data', 'rules_reach', 'rules_table.tsv'),
                                           encoding='utf-8'), delimiter='\t') if r['status'] == 'rule']
    assert collections.Counter(r['step'] for r in st4_) == by_step_ and {r['id'] for r in st4_} == {r['id'] for r in rl73_}, \
        'Supplementary Table 4 counts the same rules by step'
    F['rules_drawn'] = {'Read': by_step_['Read'], 'Convert': by_step_['Convert'], 'Verify': by_step_['Verify'],
                        'Check': by_step_['Check'], 'Decide': by_step_['Database check']}
    F['rules_all'] = sum(F['rules_drawn'].values())
    assert F['rules_all'] == len(rl73_) == 73 and F['rules_drawn']['Decide'] == F['n_db'] == 3
    F['kinds_all'], F['rules_kinds'], F['flagged_all'], F['open_all'] = len(rcsv_), st_all['rule'], st_all['flag kept as printed'], st_all['open']
    # Fig. 4a's split of the 73 (its build, writing/figures/fig4/v2/final/build_fig4_v2.py: a_group, GROUP, LATER): 25
    # from checking databases against papers (the rules known at the start, slipped digits PP4 among them, its rule in
    # the first commit before an agent recorded the kind) and 48 learned from errors found by code checks, checking
    # agents, people with an agent (the owner's chat with the agent that runs CatLog) and people. Counted here the same
    # way from Fig. 4's learning file, and checked against Supplementary Table 4's 'Fig. 4a layer'
    G4 = {'old system': 'known', 'verifier': 'agents', 'operator': 'with', 'outside review': 'agents', 'audit': 'agents',
          'database check': 'agents', 'code check': 'code', 'sweep': 'code', 'reviewer': 'people', 'owner': 'people'}
    lr_ = [r for r in csv.DictReader(open(P('writing', 'figures', 'fig4', 'v2', 'evidence', 'learning', 'rules_by_papers.csv'),
                                          encoding='utf-8')) if r['status'] == 'rule']
    assert len(lr_) == 71 and {r['id'] for r in lr_} == {k_ for k_, r in tax.items() if r['status'] == 'rule'}
    grp_4a = collections.Counter(['known' if r['id'] == 'PP4' else G4[r['first_found_by']] for r in lr_] +
                                 [G4[r_[3]] for r_ in later_])
    assert grp_4a == {'known': 25, 'code': 9, 'agents': 13, 'with': 21, 'people': 5}, grp_4a
    L4A = {'known': 'From checking databases against papers', 'code': 'Code checks', 'agents': 'Checking agents',
           'with': 'People with an agent', 'people': 'People'}
    assert collections.Counter(r['Fig. 4a layer'] for r in st4_) == {L4A[k_]: v_ for k_, v_ in grp_4a.items()}, 'Supplementary Table 4 agrees'
    F['rules_4a'] = dict(grp_4a)
    S['rules_drawn'] = ("writing/figures/fig4/v2/evidence/rules/rules.csv status 'rule' (73) by rule_step: Read 16, Convert 12 "
                        "(10 on the list of 2 November and X1, X2 after it), Verify 7, Check 35, Database check 3 (Decide's foot); "
                        "taxonomy.tsv's 71 in the same steps; writing/figures/extended_data/rules_reach/rules_table.tsv "
                        "(Supplementary Table 4) the same 73 by step; Fig. 4a's split 25 known + 48 learned (code checks 9, "
                        "checking agents 13, people with an agent 21, people 5) from fig4/v2/evidence/learning/rules_by_papers.csv "
                        "and rules.csv as build_fig4_v2.py counts it")
    del rcsv_, st_all, rl73_, by_step_, st4_, lr_, grp_4a
    # the legend's three database-check rules (DB1, DB3, PR17) in plain words, each as its taxonomy guard and example say
    # and as CatLog's notes (CLAUDE.md) or code (tools/dbcompare.py) do it
    assert sorted(k_ for k_, r in tax.items() if r['status'] == 'rule' and r['guard_layer'] == 'database check') == \
        ['DB1', 'DB3', 'PR17']
    assert 'never catalogue rows or evidence; they are compared only after a paper is read' in tax['DB1']['guard'] \
        and 'Database rows are a paper list and a cross-check, never catalog rows' in re.sub(r'\s+', ' ', claude)
    assert 'metal ions under one name' in tax['DB3']['guard'] \
        and "UniProt's 'with magnesium ions as cofactor' did not match the paper's 'Mg2+'" in tax['DB3']['example'] \
        and '# Divalent metal ions under one name' in txt('tools', 'dbcompare.py')
    assert "a database number called wrong only when the paper's own kcat ÷ Km supports CatLog's" in tax['PR17']['guard'] \
        and "rule A: code states a correction only when the paper's own kcat ÷ Km supports CatLog's number" in \
        re.sub(r'\s+', ' ', txt('tools', 'dbcompare.py')).replace('# ', '')
    # V1V4 checker: the counts of paper/04_agent_case_tables.md (the agent-highlights chat's checked findings) are no
    # longer drawn (d shows three errors, no numbers), and that chat is still editing the file: its uncommitted copy said
    # 162/52/94 at HEAD, 233/72/144 at 11:06 and 233/71/145 at 11:29 on 6 Nov, so a hard-coded sentence stopped the build
    # twice. facts() checks what the art shows, so this undrawn assertion and its three values are left out
    hc = re.sub(r'\s+', ' ', txt('paper', 'evidence', 'hard_cases_20261102', 'README.md'))
    assert 'stored a trap value in 36 of the 51 of these papers it has read' in hc and 'its catalogue now in 8.' in hc
    assert "CatLog's catalogue holds the trap value in 8 of the 51 papers it has read" in hc
    F['trap_papers'], F['trap_first'], F['trap_now'] = 51, 36, 8
    # d (the owner, 5 Nov: errors "from a method or scientific perspective instead of numbers"): one error of each kind
    # (TAXONOMY.md: FA a wrong value reached the catalogue, FR a right value was refused or lost, PROC the process
    # failed), each a rule now; the wrong value is a judgment error, as the claim says (CLAIM_V2_20261102.md)
    # Q1 (the plan): the three in the past tense, so they read as errors that were found and went into the loop (in the
    # present the first said CatLog keeps reprints, the third that it reads its test papers)
    # S1, fix 7 (the owner: "the left writing is too much. Three lines, so can we not visualize it"): each error a small
    # picture of what happened, red only on the error, beside a short clause in the past tense. The second error is no
    # longer catalase (CU6): 15760714 says its catalase does not follow Michaelis-Menten kinetics and fits the sum of two
    # Hill equations, so each stored kcat is one component's maximal rate (the other papers the 10^7 limit refused are no
    # cleaner). It is CU8: a plain Km of xylanase 10A on xylan printed in mg/ml, which the verifier confirmed, refused by
    # code that knew only molar units, and kept since 12 Oct in mg/mL (the owner's decision: people's input to the loop)
    F['d_lines'] = ['a reprinted value was stored', 'a correct Km was refused', 'a test paper was read early']
    # S1r (the owner: "the left writing is too much"; the editor: two or three words a caption): each a short clause
    # still, in the past tense (the 5 Nov lesson: fragments read as a model's notes)
    F['d_lines'] = ['a reprint was stored', 'a correct Km was refused', 'a test paper was read early']
    # U1 round 2 (the owner: "the reprinted value in the flag, what does that mean?"; the editor: one word for it in a, b
    # and d): 'copied', as b's first Read rule says it; the two plates above it show the 2002 value printed again in 2003
    F['d_lines'][0] = 'a copied value was stored'
    for id_, kind_, word in (('PP2', 'FA', 'reprinted without credit'), ('CU8', 'FR', 'refused as unknown'),
                             ('PR5', 'PROC', 'read by the development loop')):
        assert tax[id_]['kind'] == kind_ and tax[id_]['status'] == 'rule' and word in tax[id_]['class'], id_
    # T2: these three rules are the first named under b's Read, Convert and Check ticks
    assert [F['named_ids'][s_][0] for s_ in ('Read', 'Convert', 'Check')] == ['PP2', 'CU8', 'PR5'], F['named_ids']
    t15_ = re.sub(r'\s+', ' ', txt('texts', '15760714.txt'))
    assert 'does not follow Michaelis–Menten kinetics' in t15_ and 'the result of adding two Hill equations' in t15_
    lg_ = [ln.rstrip('\n').split('\t') for ln in open(P('log.tsv'), encoding='utf-8')
           if '\t12591933\t' in ln or '\t10767281\t' in ln]
    # Q1, the first (PP2): 12591933's Table II repeats 22 of the 26 wild-type values of 11694539's Table III; its one read
    # stored the paper's values (add, kept 48, 14 Oct 15:40) and an audit dropped the reprinted ones the same afternoon
    assert "12591933: Table II's wild-type column repeats 11694539's Table III (22 of 26 values)" in tax['PP2']['example']
    assert '(PMID 12591933 Table II against 11694539 Table III: 22 of 26 wild-type values, dropped by audit 2026-10-14)' \
        in re.sub(r'\s+', ' ', read)
    # Y2: the n.d. pass of 9 Nov (15:02) logged a second add for 12591933 (kept=0, bounds=1, pass=censored): it reads
    # censored values only and leaves the paper's values as they were, so the paper's one read is the add without it
    pp_add = [q for q in lg_ if q[1] == '12591933' and q[2] == 'add' and 'pass=censored' not in q]
    assert all(q[3] == 'kept=0' for q in lg_ if q[1] == '12591933' and q[2] == 'add' and 'pass=censored' in q)
    pp_drop = [q for q in lg_ if q[1] == '12591933' and q[2] == 'audit_drop']
    assert len(pp_add) == 1 and pp_add[0][:4] == ['2026-10-14 15:40', '12591933', 'add', 'kept=48'], pp_add
    assert all(pp_add[0][0] < q[0] < '2026-10-15' for q in pp_drop) \
        and sum(1 for q in pp_drop if '11694539' in q[4] or 'ref 23' in q[4]) >= 22, len(pp_drop)
    assert not {q[3] for q in pp_drop} & {r['row_id'] for r in cat['12591933']}     # all out of the catalogue
    # S1 checker: the legend counts what the paper reprinted, from the log and both texts, not the '22 of 26' above. Every
    # audit_drop of 12591933 (the random sample's 2 at 15:54, the follow-up's 22 by 16:00) is a wild-type cell of its
    # Table II (six peptides: MMP-2 kcat, Km and kcat/Km, MMP-9 kcat/Km), and each equals 11694539's Table III cell: 24
    tb3c_ = txt('texts', '11694539.txt').split('=== Table III: Measuring peptide hydrolysis by a panel of MMPs', 1)[1] \
        .split('=== end table', 1)[0]
    cells_ = {c_[0]: c_[2:6] for c_ in ([x_.strip() for x_ in ln_.split('|')] for ln_ in tb3c_.splitlines())
              if len(c_) >= 6 and re.fullmatch(r'[ABC]\d+R?', c_[0])}
    ids_ = {q[3] for q in pp_drop}
    rr_ = [json.loads(t) for t in rej['12591933'] if json.loads(t)['row_id'] in ids_]
    col_ = {('MMP-2', 'kcat'): 0, ('MMP-2', 'Km'): 1, ('MMP-2', 'kcat/Km'): 2, ('MMP-9', 'kcat/Km'): 3}
    assert len(ids_) == len(pp_drop) == len(rr_) == 24 and \
        {(r['location'], r['variant']) for r in rr_} == {('Table II', 'wild type')}, (len(ids_), len(rr_))
    assert all(r['raw_value'].replace(' ', '') == cells_[r['quote'].split()[0]][
        col_[('MMP-9' if r['enzyme'].startswith('MMP-9') else 'MMP-2', r['metric'])]] for r in rr_)
    assert sorted({r['quote'].split()[0] for r in rr_}) == ['A13', 'A13R', 'A3', 'A34', 'B74', 'C9']
    F['reprint_n'] = len(rr_)
    del tb3c_, cells_, ids_, rr_, col_
    # S1, the first picture: one of those values in both papers, B74's MMP-2 kcat, 622 s^-1: 11694539 (2002, JBC 277:4485)
    # Table III and 12591933 (2003, JBC 278) Table II; the later paper's copy was stored and the audit dropped it at 15:59
    # (bd0705db79053d83); the rule's reprint wording came at 16:05 (078ea59)
    t11_ = txt('texts', '11694539.txt')
    tb3_ = t11_.split('=== Table III: Measuring peptide hydrolysis by a panel of MMPs', 1)[1].split('=== end table', 1)[0]
    assert '\n |  | s^{−1} | mm | m^{−1}s^{−1} |' in tb3_ and '\nB74 | SGESLAY ↓ YTA | 622 | 2.2 | 2.8E+05 | 2.6E+03 |' in tb3_
    x11_ = open(P('papers', '11694539.els.xml'), encoding='utf-8').read()
    assert '<prism:coverDate>2002-02-08</prism:coverDate>' in x11_ and '<prism:volume>277</prism:volume>' in x11_ \
        and '<prism:startingPage>4485</prism:startingPage>' in x11_
    t12_ = txt('texts', '12591933.txt')
    assert 'Vol. 278, No. 19, Issue of May 9, pp. 17158 –17163, 2003' in t12_ and '(2002) J. Biol. Chem. 277, 4485– 4491' in t12_
    assert re.search(r'\n\s*B74\s+SGESLAY 2 YTA\s+622\s+2\.2\s+2\.8E ⫹ 05', t12_)
    dr_ = [q for q in pp_drop if q[3] == 'bd0705db79053d83']
    assert len(dr_) == 1 and dr_[0][0] == '2026-10-14 15:59' and dr_[0][4].startswith(
        "reprinted: Table II row B74 MMP-2 kcat 622 s-1 is ref. 23's value (Chen et al. 2002 JBC 277:4485 = PMID 11694539, "
        "Table III row B74: 622"), dr_
    assert '2026-10-14 078ea59' in tax['PP2']['rule_dates']
    F['reprint'] = dict(value='622 s^-1', years=('2002', '2003'), pmids=('11694539', '12591933'))
    # S1, the second (CU8): xylanase 10A's Km on xylan, '1.1 ± 0.12' under a 'mg/ml' header (10767281 Table II), confirmed
    # by its verifier on 9 Oct, refused by code ('unknown_km_unit:mg/ml', the add of 9 Oct 12:16), recovered on 12 Oct
    # 17:21 once code kept such a Km in mg/mL (66d9143, 17:40; the owner's rule in CLAUDE.md); stored since, and exported
    # in its own column
    c8_ = tax['CU8']
    assert (c8_['class'], c8_['guard_layer'], c8_['rule_commit'], c8_['rule_date']) == \
        ('Km per mass concentration refused as unknown', 'code conversion', '66d9143', '2026-10-12') \
        and "then the owner's decision" in c8_['found'], c8_
    tb10_ = txt('texts', '10767281.txt').split('=== Table II: Activity of native and mutant forms of Xyl10A against xylan',
                                               1)[1].split('=== end table', 1)[0]
    assert '\nXyl10A | k_{cat} | K_m | k_{cat}/K_m\n | min^{−1} | mg/ml | ' in tb10_ \
        and '\nNative | 35306 ± 2818 | 1.1 ± 0.12 | 32096\n' in tb10_
    v79_ = [v for v in json.load(open(P('work', 'old', '10767281.verify.1792880849.json'), encoding='utf-8'))['verdicts']
            if v.get('i') == 79]
    assert len(v79_) == 1 and (v79_[0]['metric'], v79_[0]['raw_value'], v79_[0]['verdict']) == ('Km', '1.1 ± 0.12', 'confirm') \
        and 'no molar spelling exists, so code cannot convert it to mM' in v79_[0]['reason'], v79_
    rj8_ = [json.loads(t) for t in rej['10767281'] if '"d28576e2226ed6a4"' in t]
    assert len(rj8_) == 1 and rj8_[0]['why'] == ['unknown_km_unit:mg/ml'] \
        and (rj8_[0]['raw_value'], rj8_[0]['raw_unit'], rj8_[0]['location']) == ('1.1 ± 0.12', 'mg/ml', 'Table II'), rj8_
    assert ['2026-10-09 12:16', '10767281', 'add', 'kept=86', 'dup=0', 'rejected=12', 'status=done'] in lg_
    assert any(q[:4] == ['2026-10-12 17:21', '10767281', 'recover', 'kept=6'] and 'reason=unknown_km_unit' in q for q in lg_)
    assert any(q[:4] == ['2026-10-12 17:22', '10767281', 'recover', 'kept=6'] and 'reason=unknown_kcatkm_unit' in q
               for q in lg_)
    w66_ = subprocess.run(['git', '-C', ROOT, 'log', '-1', '--format=%ad %s', '--date=iso', '66d9143'], capture_output=True,
                          text=True, check=True, env=GENV).stdout
    assert w66_.startswith('2026-10-12 17:40') and 'Keep Km over a mass concentration (mg/mL)' in w66_, w66_
    xr_ = [r for r in cat['10767281'] if r['row_id'] == 'd28576e2226ed6a4']
    assert len(xr_) == 1 and (xr_[0]['metric'], xr_[0]['raw_value'], xr_[0]['raw_unit'], xr_[0]['value'], xr_[0]['unit'],
                              xr_[0]['location'], xr_[0]['variant'], xr_[0]['substrate']) == \
        ('Km', '1.1 ± 0.12', 'mg/ml', 1.1, 'mg/mL', 'Table II', 'wild type', 'xylan') \
        and xr_[0]['verify_note'].startswith('recovered (unknown_km_unit)') and xr_[0]['enzyme'].startswith('xylanase 10A')
    xw_ = wide['xyl']
    assert (xw_['pubmed_id'], xw_['km_mg_per_ml'], xw_['km'], xw_['substrate_name']) == ('10767281', 1.1, None, 'xylan')
    assert units.normalize('Km', '1.1 ± 0.12', 'mg/ml') == (1.1, 'mg/mL', None) \
        and units.MASS_UNIT == {'Km': 'mg/mL', 'kcat/Km': 'mL mg^-1 s^-1'}
    assert '(the user, 2026-10-12; `units.MASS_UNIT`)' in claude
    F['refused'] = dict(head='mg/ml', cell='1.1 ± 0.12', pmid='10767281', table='Table II', enzyme='xylanase 10A',
                        substrate='xylan')
    # Q1, the third (PR5): the locked test papers with an add line (the file's test papers less those unread), all
    # before the lock of 1 Nov
    F['locked_read'] = CJ['test_papers'] - CJ['test_unread']
    lk_ = {}
    for ln in open(P('log.tsv'), encoding='utf-8'):
        q = ln.split('\t', 3)
        if len(q) >= 3 and q[2] == 'add' and q[1] in locked:
            lk_[q[1]] = max(lk_.get(q[1], ''), q[0])
    assert len(lk_) == F['locked_read'] and max(lk_.values()) < '2026-11-01', (len(lk_), max(lk_.values()))
    assert "# The method paper's test set (the user, 2026-11-01)" in open(P('sources', 'holdout_locked.txt'),
                                                                         encoding='utf-8').readline()
    # S1: the first and last test-paper reads by the development loop (10 Oct 13:08, 31 Oct 14:28), all before the lock
    # (16d2764, 1 Nov 07:43): 'read early', before their test
    assert (min(lk_.values()), max(lk_.values())) == ('2026-10-10 13:08', '2026-10-31 14:28'), (min(lk_.values()), max(lk_.values()))
    w16_ = subprocess.run(['git', '-C', ROOT, 'log', '-1', '--format=%ad', '--date=iso', '16d2764'], capture_output=True,
                          text=True, check=True, env=GENV).stdout
    assert w16_.startswith('2026-11-01 07:43') and tax['PR5']['rule_commit'] == '16d2764', w16_
    S['d_examples'] = ('taxonomy PP2 (12591933 Table II repeats 22 of 26 of 11694539 Table III; log.tsv add kept=48 '
                       '14 Oct 15:40, audit_drop lines that afternoon, bd0705db79053d83 B74 kcat 622 s-1 at 15:59; '
                       'texts/11694539.txt Table III B74 622, papers/11694539.els.xml 2002; texts/12591933.txt 2003, Table '
                       'II B74 622), CU8 (texts/10767281.txt Table II Km mg/ml 1.1 ± 0.12; work/old/10767281.verify.'
                       '1792880849.json i=79 confirm; rejected.jsonl d28576e2226ed6a4 unknown_km_unit:mg/ml; log.tsv add '
                       '9 Oct 12:16, recover 12 Oct 17:21; 66d9143 12 Oct 17:40; catalog.jsonl d28576e2226ed6a4 1.1 mg/mL; '
                       f"catlog_wide 9b4f88de489c2372 km_mg_per_ml 1.1), PR5 ({F['locked_read']} of the {F['locked']} locked papers read, 10 Oct - 31 "
                       'Oct, all before the lock 16d2764 of 1 Nov)')
    del lg_, pp_add, pp_drop, lk_, t15_, t11_, tb3_, x11_, t12_, dr_, c8_, tb10_, v79_, rj8_, w66_, xr_, xw_, w16_
    # ---- H6 (MISSING_COMPONENTS items 4 and 5). d's second step, "People write a rule / with an agent, in instructions
    # or code" (the owner: "it is human handling and human co-learning"): the rules are written in the chat the owner
    # runs with an agent (CLAUDE.md "Improving as you go": this chat finds the cause and fixes it in the prompts or code;
    # bigger changes go to the owner first; the taxonomy's 'operator'). Who noticed each error first is not recorded, so
    # the step says who writes, not who found. d's third step, "Papers are read again / code re-checks every value" (R1:
    # "Affected papers are read again", at the step): after
    # any change the regression check re-runs the code checks on every stored value (tools/recheck.py), while a rule in
    # the instructions reaches a value only when its paper is read again (catlog.py reread; 2,345 papers read more than
    # once by 2 Nov, above), swept or audited, so the step no longer says every rule reaches every value
    claude_ = re.sub(r'\s+', ' ', claude)
    for s_ in ('This chat is expected to find and fix edge cases while it works', 'Find the cause in code or prompts',
               'Fix it in the smallest place (catlog.py, tools/*.py, prompts/*.md',
               'Bigger changes (new data sources, new routes, deleting data that cannot be rebuilt, scheduling) go to the '
               'user first.', '`python3 catlog.py export && python3 tools/recheck.py` must still pass: every row re-checked'):
        assert s_ in claude_, s_
    tx_ = txt('paper', 'figures', 'method_overview', 'v5', 'TAXONOMY.md')
    assert 'operator (the chat that runs the loop)' in tx_ and 'who noticed first is not recorded' in tx_
    rc_ = txt('tools', 'recheck.py')
    assert '1. Re-run the code checks on every catalog row' in rc_ and 'Usage: python3 tools/recheck.py   (exit 1 on any problem)' in rc_
    assert 'def cmd_reread' in txt('catlog.py')
    S['d_steps'] = ('CLAUDE.md "Improving as you go" (this chat finds the cause, fixes it in code or prompts; bigger changes go '
                    'to the user first); TAXONOMY.md routes ("operator (the chat that runs the loop)", "who noticed first is not '
                    'recorded"); tools/recheck.py docstring ("Re-run the code checks on every catalog row", exit 1 on any '
                    'problem); catlog.py cmd_reread')
    # ---- Q1: the legend's sentences on what the drawing leaves out (writing/research/fig1_review: the independent
    # review's items 1, 2 and 5-11, MISSING_COMPONENTS items 9-11, 14-17 and 19), each checked here; nothing is drawn
    # the agents: the model each stored value was read by (its stamp, else its rebuilt stamp): most by Claude Opus 5.5,
    # some by Opus 5 (alone, or after a switch within a run), and Sonnet 5.5 as the one retry of an agent that stops
    mods, nost = collections.Counter(), set()
    rx_m, rx_i = re.compile(r'"reader_model": "([^"]*)"'), re.compile(r'"row_id": "([0-9a-f]+)"')
    with open(P('catalog.jsonl'), encoding='utf-8') as fh:
        for ln in fh:
            m_ = rx_m.search(ln)
            if m_ and m_.group(1):
                mods[m_.group(1)] += 1
            else:
                nost.add(rx_i.search(ln).group(1))
    own_, bf_, rebuilt_ = sum(mods.values()), 0, 0      # values with their own trail; then those rebuilt from the logs
    with open(P('sources', 'provenance_backfill.tsv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            if r['row_id'] in nost:
                mods[r['reader_model'] or 'none'] += 1
                bf_ += 1
                rebuilt_ += r['how'] == 'reconstructed'
    nv_ = sum(mods.values())
    # checker (MISSING_COMPONENTS item 2, high; the record's foot line): trails are written as values are stored only
    # since 21 Oct; most values' trails (89% on 7 Nov), the drawn record's included (asserted with its facts: 'how'
    # reconstructed), were rebuilt from the agents' logs
    # W1 (11 Nov): 'most values' in the legend is more than half; the earlier bound of 0.8 was a margin that the
    # growing catalogue passed on 11 Nov (79.7%: new values carry their own trail)
    assert own_ + bf_ == nv_ and rebuilt_ > 0.5 * (own_ + len(nost)), (own_, len(nost), rebuilt_)
    assert 'Each new row is stamped for reproducibility (2026-10-21)' in re.sub(r'\s+', ' ', claude)
    del own_, bf_, rebuilt_
    # FINAL PASS: 'Opus 5.5 read most values' is more than half, as for the trails above; the earlier bound of 0.75 was
    # a margin that the catalogue passed before the freeze (72.1% at the freeze, of the catalogue as the tag holds it)
    assert mods['claude-opus-5-5'] > 0.5 * nv_ and mods['claude-opus-5'] > 0 and mods['claude-opus-5-5>claude-opus-5'] > 0 \
        and mods['claude-sonnet-5-5'] > 0 and set(mods) <= {'claude-opus-5-5', 'claude-opus-5', 'claude-opus-5-5>claude-opus-5',
                                                            'claude-sonnet-5-5', 'none'}, mods
    # the verifier: the reader's model by default (a model is named only for the retry), a fresh agent, and the third
    # agent for the values the verifier says the reader missed (asserted above: verify(pmid, '.missed', model))
    assert 'const read = (pmid, model) => run(' in wf and 'const verify = (pmid, which, model) => run(' in wf \
        and wf.count('...(model ? { model } : {})') == 2 and "(await step('sonnet'))" in wf
    # blinding: by instruction to the reader and the verifier, checked in their logs; the 303 exposed papers read again
    assert 'Read blind: use only this paper' in read and 'Check blind: use only this paper' in verify \
        and 'def blind_check' in txt('tools', 'human_review.py')
    # values change only through logged commands; refused values kept with their reasons
    cl_ = re.sub(r'\s+', ' ', claude)
    assert '`drop` is the only way a row leaves the catalog' in cl_ and 'Every step that changes something logs a line in log.tsv' in cl_
    cp_ = txt('catlog.py')
    assert all(f'def cmd_{c_}(' in cp_ for c_ in ('drop', 'unitfix', 'cellfix', 'pmfix', 'limitfix', 'recover'))
    # qualifiers as notes; kcat/Km computed from kcat ÷ Km only where the paper prints none, and marked
    rd_ = re.sub(r'\s+', ' ', read)
    assert '`metric_note`: anything that applies to this one value only: `apparent`' in rd_ \
        and '`paper-declared approximate value`' in rd_ and '`per active site`' in rd_
    assert "eff_src = 'printed' if eff is not None else ''" in cp_ and 'if eff is None and paired and kcat and km:' in cp_ \
        and "'derived: kcat / Km of this measurement'" in cp_
    # page images are rendered from the paper's PDF, so they exist only where the paper came as a PDF: about half of the
    # papers read (the rest came as publisher XML)
    assert 'For a PDF, the text is `pdftotext -layout`' in read and 'pdftoppm -r 200' in read
    src_ = collections.Counter()
    for r in csv.DictReader(open(P('papers.tsv'), encoding='utf-8'), delimiter='\t'):
        if r['status'] == 'done':
            s_ = (r['text_source'] or '').lower()
            src_['pdf' if s_.endswith('.pdf') else 'xml' if s_.endswith('.xml') else 'other'] += 1
    assert 0.4 < src_['pdf'] / sum(src_.values()) < 0.6 and src_['xml'] > 0.4 * sum(src_.values()), src_
    # sweeps: a change is made only after independent agents check it against the paper; for misprinted units and
    # maximal rates only if at most one of three independent refuters refutes it. Checker: not 'three' for every sweep:
    # the reprint sweep dropped a row once one refuter confirmed it (two more judges only in disputes), and the n.d.
    # check had two blind agents and a third on disagreements
    for wf_ in ('catlog-scale.js', 'catlog-vmax.js'):
        t_w = txt('.claude', 'workflows', wf_)
        assert 'const REFUTERS = 3' in t_w and 'const MAX_REFUTED = 1' in t_w, wf_
    assert 'every REPRINT row independently refuted or confirmed' in cl_ \
        and 'two blind agents each, a third on disagreements' in cl_
    S['legend_extra'] = (f'models of stored values {dict(mods)}; catlog-batch.js read/verify (model only on the retry); '
                         'read.md "Read blind", verify.md "Check blind", tools/human_review.py blind_check; CLAUDE.md '
                         '("`drop` is the only way a row leaves the catalog"; every change logs a line); catlog.py cmd_drop, '
                         'unitfix, cellfix, pmfix, limitfix, recover; read.md metric_note; catlog.py wide() derives kcat/Km '
                         f'only when none is printed; papers.tsv done papers by text source {dict(src_)}; catlog-scale.js and '
                         'catlog-vmax.js REFUTERS = 3, MAX_REFUTED = 1')
    del mods, nost, nv_, cl_, cp_, rd_, src_
    return F, S


F, S = facts()


def facts_b2(F):
    """V8b: the four examples of b's decks, each a real print, its rule a 'rule' of the card's own layer in the
    taxonomy, and what CatLog stored or refused, checked against the files (spliced after facts() for the trial)."""
    import catlog, units
    tax = {r['id']: r for r in csv.DictReader(open(P(*TAXONOMY), encoding='utf-8'), delimiter='\t')}
    locked = set(catlog.locked())
    log_ = open(P('log.tsv'), encoding='utf-8').read()
    st_ = {r['pmid']: r for r in csv.DictReader(open(P('papers.tsv'), encoding='utf-8'), delimiter='\t')}
    rows = {}
    want = {'1a4e80e86bf1448f', '590fa31bbf3ebfca'}
    with open(P('catalog.jsonl'), encoding='utf-8') as fh:
        for ln in fh:
            m = re.search(r'"row_id": "([0-9a-f]{16})"', ln)
            if m and m.group(1) in want:
                rows[m.group(1)] = json.loads(ln)
    assert set(rows) == want, set(rows)
    B = {}
    # ---- Read: RA1 (reader prompt). 25658941's Table 1 heads a column 'Km (mM)' and prints the Hill coefficient of
    # the same row under 'N (Hill)': dTTP 0.09 mM beside N = 2.2 (asserted with F['hill'] in facts()). CatLog's reader
    # skipped that Km; BRENDA, OED and UniProt list it as a Km (facts())
    assert (tax['RA1']['status'], tax['RA1']['guard_layer']) == ('rule', 'reader prompt')
    t_h = txt('texts', '25658941.txt')
    assert re.search(r'Km \(mM\)\s+Vmax \(mM s-1\)\s+kcat \(s-1\)\s+kcat/Km \(mM-1 s-1\)\s+N \(Hill\)', t_h)
    assert re.search(r'\ndTTP\s+0\.09\s+0\.06\s+43\s+503\s+2\.2\n', t_h)
    # X1 checker: b draws the two columns side by side, but the table prints three between them ('N (Hill)' is its last
    # column), so the legend says 'shares its rows with', 'the table's last column, drawn beside it here', not 'beside'
    assert re.search(r'\nSubstrate\s+Km \(mM\)\s+Vmax \(mM s-1\)\s+kcat \(s-1\)\s+kcat/Km \(mM-1 s-1\)\s+N \(Hill\)[ \t]*\n', t_h)
    B['read'] = dict(head=('Km (mM)', 'N (Hill)'), cell=('0.09', '2.2'), out='not a Km', pmid='25658941', rule='RA1')
    # ---- Convert: CU1 (code conversion: 'a printed cell and unit convert to catalogue units or the value is refused
    # ...; no unit is ever defaulted; a model never types a converted value'; the earlier system's converter had passed
    # a min^-1 value as s^-1). 25528584 (human aldose reductase, D-glucose): Table 1 prints the row 'kcat (min^-1)'
    # with 126 ± 6; code stored 2.1 s^-1, its ± 0.1 s^-1; BRENDA, OED and SKiD list 126 s^-1 (60-fold too high)
    c1 = tax['CU1']
    assert (c1['status'], c1['guard_layer']) == ('rule', 'code conversion') and 'a model never types a converted value' \
        in c1['guard'] and 'no unit is ever defaulted' in c1['guard'] and 'min^-1 value labelled s^-1' in c1['example']
    t_a = txt('texts', '25528584.txt')
    tb_ = t_a.split('=== Table 1: Kinetic parameters of bAR and hAR for d-glucose and l-idose.', 1)[1].split('=== end table', 1)[0]
    assert 'AR source | bAR [span] | bAR [span] | hAR [span] | hAR [span]' in tb_ \
        and 'Substrate | d-glucose | l-idose | d-glucose | l-idose' in tb_ \
        and 'k_{cat} (min^{−1}) | 29 ± 1 | 30 ± 2 | 126 ± 6 | 143 ± 15' in tb_
    r_ = rows['1a4e80e86bf1448f']
    assert (r_['pmid'], r_['metric'], r_['raw_value'], r_['raw_unit'], r_.get('unit_for_conversion'), r_['value'], r_['unit'],
            r_['enzyme'], r_['organism'], r_['substrate'], r_['variant'], r_['location']) == \
        ('25528584', 'kcat', '126 ± 6', 'min^-1', None, 2.1, 's^-1', 'aldose reductase (hAR)', 'Homo sapiens', 'D-glucose',
         'wild type', 'Table 1'), r_
    assert units.normalize('kcat', '126 ± 6', 'min^-1') == (2.1, 's^-1', None) and units.TIME['min'] == 60.0
    assert catlog.printed_err('126 ± 6', 2.1, r_) == 0.1, catlog.printed_err('126 ± 6', 2.1, r_)
    dc_ = [r for r in csv.DictReader(open(P('sources', 'database_corrections.tsv'), encoding='utf-8'), delimiter='\t')
           if r['row_id'] == '1a4e80e86bf1448f']
    assert len(dc_) == 1 and (dc_[0]['database'], dc_[0]['database_value'], dc_[0]['verdict'], dc_[0]['cause']) == \
        ('BRENDA, OED, SKiD', '126 s^-1', 'corrected', 'time_unit'), dc_
    assert st_['25528584']['status'] == 'done' and '25528584' not in locked
    B['convert'] = dict(head='kcat (min^-1)', cell='126 ± 6', out='2.1 ± 0.1 s^-1', pmid='25528584', rule='CU1')
    # ---- Verify: PP1 / RA4 (verifier prompt), as before: 14676218's Table I heads its kcat/Km column µM^-1 s^-1 over
    # the Grx1 cell 1.66 × 10^6; the row's own kcat 6.79 s^-1 and Km 4.1 µM give 1.66 × 10^6 M^-1 s^-1 (F['rec'], facts())
    t_g = txt('texts', '14676218.txt')
    assert re.search(r'Km\s+kcat\s+kcat/Km\s+Km', t_g) and re.search(r'Grx1\s+4\.1\s+6\.79\s+1\.66 ⫻ 106', t_g)
    assert (F['rec']['raw_value'], F['rec']['raw_unit'], F['rec']['conv_unit']) == ('1.66 × 10^6', 'µM^-1 s^-1', 'M^-1 s^-1')
    B['verify'] = dict(head='kcat/Km (µM^-1 s^-1)', cell='1.66 × 10^6', out='M^-1 s^-1', pmid='14676218', rule='RA4')
    # ---- Check: IP4 (code check: 'a different value for an accepted slot is a conflict, kept apart and decided from the
    # paper'). 14769870 (Micrococcus luteus B-P 26 UPP synthase, Y71S, IPP), Table 1's kcat/Km cell '4.3': stored on
    # 11 Oct as 4.3 mM^-1 s^-1; the blind second reading of 22 Oct converted the same cell to 4,300 mM^-1 s^-1; code
    # refused it ('same printed cell as accepted row ... but converted differently ...; review which is right'), logged a
    # conflict, and the paper decided for the stored value (the row's own kcat over Km, 110 / 25.4 = 4.33)
    i4 = tax['IP4']
    assert (i4['status'], i4['guard_layer']) == ('rule', 'code check') and \
        'a different value for an accepted slot is a conflict, kept apart and decided from the paper' in i4['guard']
    a_ = rows['590fa31bbf3ebfca']
    assert (a_['pmid'], a_['metric'], a_['raw_value'], a_['raw_unit'], a_['unit_for_conversion'], a_['value'], a_['unit'],
            a_['variant'], a_['substrate'], a_['location']) == \
        ('14769870', 'kcat/Km', '4.3', 's^-1/µM', '10^-3 s^-1 µM^-1', 4.3, 'mM^-1 s^-1', 'Y71S', 'IPP', 'Table 1'), a_
    assert a_['enzyme'] == 'undecaprenyl diphosphate synthase (UPP synthase)' and a_['organism'] == 'Micrococcus luteus'
    rj_ = None
    with open(P('rejected.jsonl'), encoding='utf-8') as fh:
        for ln in fh:
            if '180c46e2be7f68bd' in ln:
                rj_ = json.loads(ln)
    assert rj_ and (rj_['metric'], rj_['raw_value'], rj_['raw_unit'], rj_['value'], rj_['unit']) == \
        ('kcat/Km', '4.3', 's^-1/µM', 4300.0, 'mM^-1 s^-1') and rj_['why'] == [
        'same printed cell as accepted row 590fa31bbf3ebfca but converted differently (4.3 mM^-1 s^-1); review which is right']
    assert '\n2026-10-22 20:17\t14769870\tconflict\t590fa31bbf3ebfca\t180c46e2be7f68bd\n' in log_
    assert "same printed cell as accepted row {old['row_id']} but converted differently" in inspect.getsource(catlog.append_rows)
    cj_ = json.load(open(P('work', 'blindcheck_20261022', 'conflict_14769870.json'), encoding='utf-8'))
    d_ = [d for d in cj_['decisions'] if d['accepted_row_id'] == '590fa31bbf3ebfca']
    assert len(d_) == 1 and d_[0]['re_read_row_id'] == '180c46e2be7f68bd' and d_[0]['decision'] == 'KEEP_ACCEPTED' \
        and 'displayed kcat ÷ Km(µM) = 110/25.4 = 4.33, printed 4.3' in d_[0]['evidence'], d_
    # X1 (the legend's Check sentence): the page image's headers, and why the first reading holds
    assert "headers: 'Km (µM)', 'kcat (×10^3) (s^-1)', 'kcat/Km (s^-1/µM)'" in d_[0]['evidence'] \
        and "so the column carries the kcat column's ×10^3" in d_[0]['evidence'], d_[0]['evidence']
    assert st_['14769870']['status'] == 'done' and '14769870' not in locked
    B['check'] = dict(cell='4.3', kept='4.3 mM^-1 s^-1', refused='4,300 mM^-1 s^-1', pmid='14769870', rule='IP4')
    assert not ({b_['pmid'] for b_ in B.values()} & locked)
    # ---- X1: each top card's grey line is the idea behind the rule it shows, in the words of that rule's guard or its
    # instructions: RA1 (what a printed number is: these constants are not Km or kcat), CU1 ('a model never types a
    # converted value'; CLAUDE.md "A model never types a converted value: code converts the printed cell and unit"), RA4
    # with verify.md rule 3 (a header the paper itself shows is misprinted; "the paper's own numbers decide"), IP4 (a
    # second reading that differs from the accepted one is a conflict, decided from the paper)
    vf_ = re.sub(r'\s+', ' ', txt('prompts', 'verify.md'))
    assert 'are not Km or kcat' in tax['RA1']['guard'] and 'a model never types a converted value' in tax['CU1']['guard'] \
        and "the paper's own numbers decide" in vf_ and "when the paper itself shows that a header's unit is a misprint" in vf_ \
        and 'A model never types a converted value: code converts the printed cell and unit' in txt('CLAUDE.md') \
        and 'is a conflict, kept apart and decided from the paper' in i4['guard']
    for k_, t_ in (('read', 'what each number is'), ('convert', 'code converts, never an agent'),
                   ('verify', 'the paper’s own numbers decide'), ('check', 'two readings must agree')):
        B[k_]['topic'] = t_
    # X1 round 2 (the editor: one dark line that states the rule; the error each rule stops, with its size): each card's
    # rule in plain words, as its guard or instructions say it, and the error the example's rule stops
    # Read (RA1: 'Hill constants ... are not Km or kcat'; read.md 'Hill constants (K0.5, S0.5, ...) are NOT Km or kcat.
    # Skip them.'): the reader skipped the Km column (its note, asserted in facts()), so the card says 'skipped'
    assert 'Hill constants' in tax['RA1']['guard'] and 'are not Km or kcat' in tax['RA1']['guard']
    B['read'].update(rule_words='A Hill constant is not a Km', out='skipped')
    # Convert (CU1: 'a printed cell and unit convert to catalogue units or the value is refused'; the earlier converter
    # passed a min^-1 value as s^-1): the error stopped is 126 s^-1, the number BRENDA, OED and SKiD list (asserted above),
    # 60-fold the stored 2.1 s^-1
    assert 'a printed cell and unit convert to catalogue units or the value is refused' in c1['guard']
    assert units.normalize('kcat', '126', 's^-1') == (126.0, 's^-1', None) and round(126.0 / r_['value'], 9) == 60.0
    B['convert'].update(rule_words='Code converts the printed unit', stopped='126 s^-1', fold='60-fold')
    # Verify (verify.md: "the paper's own numbers decide"): the header's µ is the misprint; read as printed (µM^-1 s^-1)
    # the cell would be 10^6-fold the value the row's own kcat and Km give (M^-1 s^-1, stored as 1,660 mM^-1 s^-1)
    v_lit_ = units.normalize('kcat/Km', '1.66 × 10^6', 'µM^-1 s^-1')
    v_ok_ = units.normalize('kcat/Km', '1.66 × 10^6', 'M^-1 s^-1')
    assert v_ok_ == (1660.0, 'mM^-1 s^-1', None) and v_lit_[1] == 'mM^-1 s^-1' and round(v_lit_[0] / v_ok_[0]) == 10 ** 6, \
        (v_lit_, v_ok_)
    assert round(F['rec']['kcat'] / (F['rec']['km'] * 1e-3) / 1e6, 2) == 1.66          # 6.79 s^-1 / 4.1 µM, in M^-1 s^-1
    # 9 Nov, after the owner asked whether any rules should change: the rule line says what the paper's own numbers
    # decide (in words: S1's rule keeps ÷ off the figure), in verify.md rule 3's words (a kcat/Km far from kcat ÷ Km of its row means a misread unit; a block whose
    # printed kcat/Km closes only in another unit by an exact factor shows the header's unit is a misprint)
    assert 'A kcat/Km ≥5× away from kcat ÷ Km of the same row usually means a misread unit, prefix or header ' \
        'multiplier' in vf_ and 'closes only in that unit by an exact unit factor' in vf_
    B['verify'].update(rule_words='kcat and Km decide the unit', head_parts=('kcat/Km (', 'µ', 'M^-1 s^-1)'),
                       fold='10^6-fold')
    assert ''.join(B['verify']['head_parts']) == B['verify']['head']
    # X1 checker (the legend's Verify sentence, as Convert's names its databases): the error this rule stops is in a
    # database. The table prints 13 kcat/Km cells (5 rows x 3 substrates, 2 ND), every column headed µM^-1 s^-1; CatLog
    # stores all 13 (Table I, read in M^-1 s^-1), and SABIO-RK lists each of them 10^6-fold higher, as the header prints
    # them (database_corrections.tsv: 13 lines, all 'corrected', paper_unit_misprint)
    tI_ = t_g.split('TABLE I', 1)[1].split('TABLE II', 1)[0]
    assert len(re.findall(r'\d ⫻ 10\d', '\n'.join(l_ for l_ in tI_.splitlines() if re.match(r'\s+Grx\d', l_)))) == 13 \
        and len(re.findall(r'␮M⫺1 s⫺1', tI_)) == 3          # the three kcat/Km columns' headers, each µM^-1 s^-1
    vrows_ = {}
    with open(P('catalog.jsonl'), encoding='utf-8') as fh:
        for ln in fh:
            if '"14676218"' in ln:
                r0_ = json.loads(ln)
                if (r0_['pmid'], r0_['metric'], r0_['location']) == ('14676218', 'kcat/Km', 'Table I'):
                    vrows_[r0_['row_id']] = r0_
    assert len(vrows_) == 13 and all((r0_['raw_unit'], r0_.get('unit_for_conversion')) == ('µM^-1 s^-1', 'M^-1 s^-1')
                                     for r0_ in vrows_.values()), len(vrows_)
    dcv_ = [r0_ for r0_ in csv.DictReader(open(P('sources', 'database_corrections.tsv'), encoding='utf-8'), delimiter='\t')
            if r0_['pmid'] == '14676218']
    assert {r0_['row_id'] for r0_ in dcv_} == set(vrows_) and len(dcv_) == 13 and all(
        (r0_['database'], r0_['metric'], r0_['verdict'], r0_['cause']) == ('SABIO-RK', 'kcat/Km', 'corrected',
                                                                          'paper_unit_misprint')
        and r0_['database_value'].endswith(' mM^-1 s^-1')
        and round(float(r0_['database_value'].split()[0]) / vrows_[r0_['row_id']]['value']) == 10 ** 6 for r0_ in dcv_), dcv_
    B['verify'].update(db='SABIO-RK', db_n=len(vrows_))
    del tI_, vrows_, dcv_, r0_
    # Check (IP4: 'a different value for an accepted slot is a conflict, kept apart and decided from the paper'): the
    # refused second reading, 4,300 mM^-1 s^-1, is 1,000-fold the stored 4.3 (rejected.jsonl and catalog.jsonl, above)
    assert round(rj_['value'] / a_['value'], 9) == 1000.0
    # Y2 round 2 (the editor: the struck 4,300 had no unit, so its 1,000-fold error could not be read from the drawing):
    # the refused reading with its unit, as stored (rejected.jsonl, asserted above), and its size as 10^3-fold (Verify's
    # 10^6-fold; '1,000-fold' and the unit do not fit the card's line together); the legend keeps '1,000-fold'
    assert rj_['unit'] == a_['unit'] == 'mM^-1 s^-1' and 10 ** 3 == 1000
    B['check'].update(rule_words='Two readings must agree', struck=f"{rj_['value']:,.0f} {rj_['unit']}", fold='10^3-fold',
                      fold_words='1,000-fold')
    assert B['check']['struck'] == '4,300 mM^-1 s^-1'
    del vf_, v_lit_, v_ok_
    F['b2'] = B


facts_b2(F)


def facts_r1(F):
    """R1 (10 Nov, the owner on Z1: b's and d's examples "too trivial and not wow ish", "do we need those at all";
    the database boxes "more polished ... like you did long ago"; the Linked row "confusing for a casual reader ...
    needs significant rework"). The facts the reworked panels draw, each asserted against its file:
    b, every case with the wrong number a database lists for the same paper; c, one record (the paper's N248A) as
    printed and as stored; d, one error once round the loop (the copied values)."""
    import units                              # CatLog's own conversion code (on the path since facts())
    R = {}
    tax = {r['id']: r for r in csv.DictReader(open(P(*TAXONOMY), encoding='utf-8'), delimiter='\t')}
    locked = set(txt('sources', 'holdout_locked.txt').split())
    B = F['b2']
    # ---- the databases' numbers for b's four papers (sources/db_values.tsv, catalogue units)
    want = {'25658941', '25528584', '14676218', '21757926'}
    dbv = collections.defaultdict(list)
    with open(P('sources', 'db_values.tsv'), encoding='utf-8') as fh:
        rd = csv.DictReader(fh, delimiter='\t')
        for r in rd:
            if r['pmid'] in want:
                dbv[r['pmid']].append((r['source'], r['metric'], float(r['value'])))
    cor = [r for r in csv.DictReader(open(P('sources', 'database_corrections.tsv'), encoding='utf-8'), delimiter='\t')
           if r['pmid'] in want]
    # Read (RA1, 25658941): the Hill constant 0.09 mM is a Km in UniProt, BRENDA and OED
    assert {s_ for s_, m_, v_ in dbv['25658941'] if m_ == 'Km' and abs(v_ - 0.09) < 1e-9} == {'BRENDA', 'OED', 'UniProt'}
    assert B['read']['cell'] == ('0.09', '2.2') and B['read']['head'] == ('Km (mM)', 'N (Hill)') and B['read']['out'] == 'skipped'
    R['read'] = dict(chips=list(zip(B['read']['head'], B['read']['cell'])), db='UniProt', db_all=('UniProt', 'BRENDA', 'OED'),
                     db_value='Km 0.09 mM', tag='not a Km', catlog='not stored', rule=B['read']['rule_words'],
                     quote='“positive cooperative binding”')
    t25 = re.sub(r'\s+', ' ', txt('texts', '25658941.txt'))
    assert 'follow a non- Michaelis-Menten model and participate in positive cooperative binding' in t25   # the paper's own words
    # Convert (CU1, 25528584): 126 per minute is 126 per second in BRENDA, OED and SKiD, 60-fold too high
    assert {s_ for s_, m_, v_ in dbv['25528584'] if m_ == 'kcat' and v_ == 126.0} == {'BRENDA', 'OED', 'SKiD'}
    c_ = [r for r in cor if r['pmid'] == '25528584' and r['database_value'] == '126 s^-1']
    assert len(c_) == 1 and (c_[0]['database'], c_[0]['verdict'], c_[0]['cause']) == ('BRENDA, OED, SKiD', 'corrected', 'time_unit')
    assert (B['convert']['head'], B['convert']['cell'], B['convert']['out'], B['convert']['stopped'], B['convert']['fold']) == \
        ('kcat (min^-1)', '126 ± 6', '2.1 ± 0.1 s^-1', '126 s^-1', '60-fold')
    assert 'a model never types a converted value' in tax['CU1']['guard']
    R['convert'] = dict(chips=[(B['convert']['head'], B['convert']['cell'])], db='BRENDA', db_all=('BRENDA', 'OED', 'SKiD'),
                        db_value=B['convert']['stopped'], tag='60×', fold='60-fold', catlog=B['convert']['out'],
                        rule='Only code converts units')
    # Verify (RA4, 14676218): SABIO-RK lists the misprinted header's values, 10^6-fold too high (all 13; facts_b2)
    assert (B['verify']['head'], B['verify']['cell'], B['verify']['fold'], B['verify']['db'], B['verify']['db_n']) == \
        ('kcat/Km (µM^-1 s^-1)', '1.66 × 10^6', '10^6-fold', 'SABIO-RK', 13)
    assert {s_ for s_, m_, v_ in dbv['14676218'] if m_ == 'kcat/Km' and abs(v_ / 1.66e9 - 1) < 1e-9} == {'SABIO-RK'}
    assert F['rec']['conv_unit'] == 'M^-1 s^-1' and F['rec']['raw_value'] == '1.66 × 10^6'
    # the row's own kcat and Km (6.79 s^-1, 4.1 µM: facts(), F['rec']) over the misprinted kcat/Km cell; the stored value in
    # the catalogue's unit (1,660 mM^-1 s^-1: facts_b2)
    assert F['rec']['kcat'] == 6.79 and abs(F['rec']['km'] * 1e3 - 4.1) < 1e-9
    R['verify'] = dict(chips=[('kcat', '6.79 s^-1'), ('Km', '4.1 µM')], chips2=[(B['verify']['head'], B['verify']['cell'])],
                       head_parts=B['verify']['head_parts'],
                       db='SABIO-RK', db_all=('SABIO-RK',), db_value='keeps the µ', tag='10^6×', fold=B['verify']['fold'],
                       catlog='1,660 mM^-1 s^-1', rule=B['verify']['rule_words'])
    assert units.normalize('kcat/Km', F['rec']['raw_value'], F['rec']['conv_unit']) == (1660.0, 'mM^-1 s^-1', None)
    assert R['verify']['rule'] == 'kcat and Km decide the unit'
    # Check (TL2, 21757926): Table 1 prints kcat/Km 6 ± 1.5 s^-1 mM^-1 for methyl p-coumarate (its own kcat 7.5 over Km
    # 1.25 mM is 6.0); the PDF's text layer prints every ± of the table as the digit 8, so the cell reads 681.5 there;
    # the text carries code's warning and the reader and the verifier read the page image; BRENDA and OED list 681.5
    t2 = tax['TL2']
    assert (t2['status'], t2['guard_layer'], t2['class']) == ('rule', 'code check', '± drawn as a digit merges two numbers')
    assert 'BRENDA and OED list 681.5' in t2['values'] and t2['example'].startswith('21757926: Table 1 prints 6 ± 1.5')
    assert 'readers and verifiers then read the page image' in t2['guard'] and 'fetch.two_points warns' in t2['guard']
    rows = {}
    with open(P('catalog.jsonl'), encoding='utf-8') as fh:
        for ln in fh:
            if '"21757926"' in ln:
                r = json.loads(ln)
                if r['pmid'] == '21757926' and r['substrate'].startswith('Methyl ρ-coumarate'):
                    rows[r['metric']] = r
    assert set(rows) == {'kcat', 'Km', 'kcat/Km'}, set(rows)
    e_ = rows['kcat/Km']
    assert (e_['row_id'], e_['raw_value'], e_['raw_unit'], float(e_['value']), e_['unit'], e_['location']) == \
        ('e5f56c293359c5b3', '6 ± 1.5', 's–1 mM–1', 6.0, 'mM^-1 s^-1', 'Table 1'), e_
    assert float(rows['kcat']['value']) / float(rows['Km']['value']) == 6.0 and rows['kcat']['raw_value'] == '7.5 ± 1.0'
    assert "read from the page image" in e_['reasoning'] and "text layer prints ± as '8'" in e_['reasoning']
    t_ = txt('texts', '21757926.txt')
    assert t_.startswith('GLYPH WARNING: the text layer of this PDF shows numbers with two decimal points')
    ln_ = [l_ for l_ in t_.splitlines() if l_.startswith('Methyl ␳-coumarate')]
    assert len(ln_) == 1 and ln_[0].split()[-5:] == ['2.580.4', '1.2580.04', '4.580.5', '7.581.0', '681.5'], ln_
    assert {s_ for s_, m_, v_ in dbv['21757926'] if m_ == 'kcat/Km' and v_ == 681.5} == {'BRENDA', 'OED'}
    c_ = [r for r in cor if r['pmid'] == '21757926']
    assert len(c_) == 1 and (c_[0]['row_id'], c_[0]['database'], c_[0]['database_value'], c_[0]['verdict']) == \
        ('e5f56c293359c5b3', 'BRENDA, OED', '681.5 mM^-1 s^-1', 'corrected'), c_
    fold_ = 681.5 / 6.0
    assert round(fold_) == 114 and '21757926' not in locked
    R['check'] = dict(chips=[('kcat/Km (s^-1 mM^-1)', e_['raw_value'])], chips2=[('PDF text', '681.5')], db='OED',
                      db_all=('BRENDA', 'OED'), db_value='681.5 mM^-1 s^-1', tag=f'{round(fold_)}×',
                      fold=f'{round(fold_)}-fold', catlog=f"{e_['raw_value']} mM^-1 s^-1",
                      rule='PDF text can print ± as 8', pmid='21757926', text_cell='681.5', enzyme='feruloyl esterase EstF27')
    assert R['check']['tag'] == '114×' and R['check']['catlog'] == '6 ± 1.5 mM^-1 s^-1'
    for k_ in ('read', 'convert', 'verify'):
        R[k_]['pmid'] = B[k_]['pmid']
    assert [R[k_]['pmid'] for k_ in ('read', 'convert', 'verify', 'check')] == ['25658941', '25528584', '14676218', '21757926']
    assert not {R[k_]['pmid'] for k_ in R} & locked
    # each card's rule is a rule of its own step (taxonomy guard_layer)
    for k_, id_, layer_ in (('read', 'RA1', 'reader prompt'), ('convert', 'CU1', 'code conversion'),
                            ('verify', 'RA4', 'verifier prompt'), ('check', 'TL2', 'code check')):
        assert (tax[id_]['status'], tax[id_]['guard_layer']) == ('rule', layer_), id_
        R[k_]['rule_id'] = id_
    # ---- c: one record, the paper's N248A with L-asparagine (export cb458776be25f46c; facts() checked its links)
    mu = None
    with open(P('catlog_wide.jsonl'), encoding='utf-8') as fh:
        for ln in fh:
            if 'cb458776be25f46c' in ln:
                mu = json.loads(ln)
    assert mu and (mu['pubmed_id'], mu['mutation_signature'], mu['substrate_name'], mu['uniprot_id']) == \
        ('11106175', 'N248A', 'L-asparagine', 'P00805')
    assert (mu['kcat'], mu['kcat_err'], mu['km'], mu['km_err'], mu['kcat_over_km'], mu['kcat_over_km_source'], mu['ph'],
            mu['temperature_c']) == (7.0, 0.1, 0.095, 0.006, 74.0, 'printed', 7.0, 25)
    assert mu['uniprot_how'] == 'gene ansB + organism, unique reviewed entry' and mu['organism'] == 'Escherichia coli'
    assert mu['smiles'] == F['asp']['smiles'] and mu['substrate_chebi'] == 'CHEBI:58048'
    crow = {}
    with open(P('catalog.jsonl'), encoding='utf-8') as fh:
        for ln in fh:
            if '"11106175"' in ln:
                r = json.loads(ln)
                if r['row_id'] in mu['row_ids']:
                    crow[r['metric']] = r
    assert [crow[m_]['row_id'] for m_ in ('kcat', 'Km', 'kcat/Km')] == mu['row_ids'] == \
        ['6155bbf16ca7787b', '2e2f23da4547bb35', 'cd7eec48420b4276']
    pr = lambda r: re.sub(r'\s*×\s*', '·', r['raw_value']).replace(' (± ', '(±') + ' ' + r['raw_unit']
    printed = [pr(crow[m_]) for m_ in ('kcat', 'Km', 'kcat/Km')]
    assert printed == ['7.0(±0.1)·10^0 s^-1', '9.5(±0.6)·10^-5 mol L^-1', '7.4·10^4 M^-1 s^-1'], printed
    assert all(crow[m_]['location'] == 'Table 2' and crow[m_]['variant'] == 'N248A' for m_ in crow)
    t11 = txt('texts', '11106175.txt')
    assert 'The use of Escherichia coli asparaginase II as a drug for the treatment of acute lymphoblastic leukemia' in t11
    assert 'In variant N248A' in t11
    L_ = F['link']
    assert (L_['uniprot'], L_['mutation'], L_['paper_pos'], L_['signal'], L_['pos'], L_['residues'], L_['chebi']) == \
        ('P00805', 'N248A', 248, 22, 270, 348, '58048')
    R['record'] = dict(
        enzyme='asparaginase II', organism=mu['organism'], variant=mu['mutation_signature'], substrate=mu['substrate_name'],
        printed=printed,
        stored=[f"{mu['kcat']:.1f} ± {mu['kcat_err']:g} s^-1", f"{mu['km']:g} ± {mu['km_err']:g} mM",
                f"{mu['kcat_over_km']:g} mM^-1 s^-1"],
        assay=f"pH {mu['ph']:.1f}, {mu['temperature_c']:g} °C", location='Table 2', pmid='11106175',
        uniprot=mu['uniprot_id'], stored_variant=f"N{L_['pos']}A", chebi=L_['chebi'], smiles=mu['smiles'],
        signal=L_['signal'], residues=L_['residues'], pos=L_['pos'], paper_pos=L_['paper_pos'])
    assert R['record']['stored'] == ['7.0 ± 0.1 s^-1', '0.095 ± 0.006 mM', '74 mM^-1 s^-1'], R['record']['stored']
    assert R['record']['assay'] == 'pH 7.0, 25 °C' and R['record']['stored_variant'] == 'N270A'
    # ---- d: one error once round the loop, the copied values (PP2). Found: the audit of 14 Oct dropped the 24 wild-type
    # values 12591933 (2003) had copied from 11694539 (2002) (facts: F['reprint'], F['reprint_n']). Rule: the two
    # instruction files' "only values measured in this paper". Read again: the sweep compared, cell by cell, the 296
    # papers that shared three or more printed cells with an earlier paper. Checked: a second agent tried to refute each
    # copy; 973 values in 80 papers left the catalogue and 165 stayed (log.tsv's 'pair scan' drops; the taxonomy)
    assert F['reprint'] == dict(value='622 s^-1', years=('2002', '2003'), pmids=('11694539', '12591933')) and F['reprint_n'] == 24
    rd_ = re.sub(r'\s+', ' ', txt('prompts', 'read.md'))
    assert '- Only values measured in THIS paper. Skip values the text attributes to other work' in rd_
    # the rule written after the audit (078ea59, 14 Oct 16:05, 25 minutes after the copied values were stored at 15:40;
    # facts() checks the add, the audit's drops and the commit's date): a reference column that repeats the cited
    # paper's table is skipped
    assert ("compare the cells: a reference column identical to that paper's table is reprinted, so skip it and keep the "
            "new columns (PMID 12591933 Table II against 11694539 Table III") in rd_
    assert '2026-10-14 078ea59' in tax['PP2']['rule_dates']
    assert '7. The value was measured in this paper: not "taken from", "previously reported", a cited row' in \
        re.sub(r'\s+', ' ', txt('prompts', 'verify.md'))
    p2 = tax['PP2']
    assert (p2['status'], p2['class']) == ('rule', "Earlier paper's values reprinted without credit")
    assert 'the sweep dropped 973 rows in 80 papers and kept 165 its refuters refuted' in p2['values']
    assert 'each pair checked cell by cell with an independent refuter' in p2['guard']
    cl = re.sub(r'\s+', ' ', txt('CLAUDE.md'))
    assert 'Every pair with 3+ (296 papers) was checked cell by cell' in cl and '973 rows in 80 papers dropped' in cl
    drops = collections.defaultdict(int)
    with open(P('log.tsv'), encoding='utf-8') as fh:
        for ln in fh:
            q = ln.rstrip('\n').split('\t')
            if len(q) > 4 and q[2] == 'drop' and 'pair scan' in ln:
                drops[q[1]] += 1
    assert (sum(drops.values()), len(drops)) == (973, 80), (sum(drops.values()), len(drops))
    # BRENDA lists the copied kcat under both papers
    for pm_ in F['reprint']['pmids']:
        with open(P('sources', 'db_values.tsv'), encoding='utf-8') as fh:
            assert any(q[0] == 'BRENDA' and q[1] == pm_ and q[3] == 'kcat' and float(q[4]) == 622.0
                       for q in (l_.split('\t') for l_ in fh) if len(q) > 4 and q[1] == pm_), pm_
    R['loop'] = dict(value=F['reprint']['value'], years=F['reprint']['years'], n=F['reprint_n'],
                     rule=('the agent adds a clause that hour:', 'skip a column copied from older work'), compared=296, removed=973, papers=80, kept=165)
    F['r1'] = R


facts_r1(F)



def facts_m2(F):
    """L2 (11 Nov, the owner on b's record: "how it connects to multiple database and grabs data - but more visually
    showing and less wordish"): the six sources drawn over the record, each asserted against the code that asks it and
    against the export, where at least one record must owe its entry, sequence or structure to it. The names are all
    the figure adds; no count of these is drawn (the counts here are tripwires, never numbers of the figure).
    M2 (11 Nov): the same six, and one line of the drawn record's stored sequence, seven residues with the residue the
    paper's variant changes in their middle; the record's own entry, sequence frame and structure source are asserted
    from the export here too."""
    seq_, stru_, ids_, cat_ = txt('tools', 'sequences.py'), txt('tools', 'structures.py'), txt('tools', 'ids.py'), txt('catlog.py')
    # ---- the enzyme: UniProt (the entry and its sequence), PDB (a printed structure's chains, through SIFTS; the
    # chains' author numbering as a frame for a variant), NCBI (a printed nucleotide or protein record, its coding
    # sequence translated)
    assert "UNIPROT = 'https://rest.uniprot.org'" in seq_ and "NCBI = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'" in seq_
    assert "SIFTS_XML = 'https://ftp.ebi.ac.uk/pub/databases/msd/sifts/split_xml/'" in seq_
    assert '    # 2. printed PDB -> local SIFTS\n' in seq_ and '    # 3. printed GenBank / EMBL / RefSeq / NCBI Gene ID\n' in seq_
    assert "src = 'SIFTS' if have_sifts() else 'UniProt xref:pdb-'" in seq_ and "f'{src}: PDB {" in seq_
    assert 'def ncbi_cds(nuc):' in seq_ and 'def ncbi_protein(pid):' in seq_ and "f'translation of NCBI CDS {cds[0][0]} (the only CDS of {ident})'" in seq_
    assert 'PDB entries whose primary citation is this PMID (local SIFTS pdb_pubmed.tsv.gz, ordinal 0)' in seq_
    # ---- the substrate: Rhea (the participants of the enzyme's own reactions), ChEBI (an exact name or synonym),
    # PubChem (the name; and, in ids.py, the compound id of the stored structure). The routes' order is the code's
    order_ = [l_.split('.', 1)[1].split()[0] for l_ in stru_.split('"""')[1].splitlines() if re.match(r'\s+\d+\. ', l_)]
    assert [n_ for n_ in order_ if n_ in ('Rhea', 'ChEBI', 'PubChem')] == ['Rhea', 'ChEBI', 'PubChem', 'ChEBI'], order_
    assert 'def rhea_hit(name, ec=\'\', uniprot=\'\', loose=False):' in stru_ and 'def chebi_hit(name, min_stars=3):' in stru_ \
        and 'def pubchem(name):' in stru_ and "'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/'" in stru_
    assert "'how': f'Rhea {p} \"" in stru_ and "'how': f'ChEBI {best[0]} \"" in stru_ and "how = f'PubChem CID {p.get(\"CID\")} \"" in stru_
    assert '    substrate PubChem CID PubChem, from that InChIKey' in ids_ and 'The ChEBI id needs no lookup' in ids_ \
        and "f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/" in ids_
    # the export names a structure's source by the first word of how it was found
    assert "w['smiles_source'] = re.split(r'[ :(]', w.get('smiles_how') or '')[0] if w.get('smiles') else ''" in cat_
    # ---- each source is used: records of the export that owe it their entry, their sequence or their structure
    n_, rest_ = collections.Counter(), collections.Counter()
    drawn_rec = {}                              # M2: the record whose pictures are drawn, and its wild-type record
    with open(P('catlog_wide.jsonl'), encoding='utf-8') as fh:
        for ln in fh:
            if '"uniprot_how"' not in ln:
                continue
            r = json.loads(ln)
            if r.get('measurement_id') in ('cb458776be25f46c', 'cbb7818048a93f81'):
                drawn_rec[r['measurement_id']] = r
            how_ = r.get('uniprot_how') or ''
            n_['records'] += 1
            n_['UniProt'] += bool(r.get('uniprot_id') and r.get('uniprot_sequence'))
            n_['PDB'] += how_.startswith('SIFTS: PDB ') or (r.get('sequence_frame') or '').startswith('PDB ')
            n_['NCBI'] += ' -> NCBI CDS ' in how_ or (r.get('sequence_source') or '').startswith('translation of NCBI CDS ')
            if r.get('smiles'):
                n_['structures'] += 1
                rest_[r.get('smiles_source') or ''] += r.get('smiles_source') not in ('Rhea', 'ChEBI', 'PubChem')
            if r.get('smiles') and r.get('smiles_source') in ('Rhea', 'ChEBI', 'PubChem'):
                assert (r.get('smiles_how') or '').startswith(r['smiles_source'] + ' '), r['measurement_id']
                n_[r['smiles_source']] += 1
    F['sources'] = {'enzyme': ['UniProt', 'PDB', 'NCBI'], 'substrate': ['Rhea', 'ChEBI', 'PubChem']}
    drawn_ = F['sources']['enzyme'] + F['sources']['substrate']
    assert all(n_[k_] >= 1000 for k_ in drawn_), dict(n_)          # each feeds a thousand records or more (11 Nov: the least, NCBI, 1,500)
    # the order drawn is the code's order of asking, in each kind: sequences.py's routes 1 to 3, structures.py's 3, 4, 7
    assert seq_.index('    # 1. printed UniProt accession(s), checked active and same species\n') < seq_.index('    # 2. printed PDB -> local SIFTS\n') \
        < seq_.index('    # 3. printed GenBank / EMBL / RefSeq / NCBI Gene ID\n')
    assert F['sources']['substrate'] == [n_k for n_k in order_ if n_k in ('Rhea', 'ChEBI', 'PubChem')][:3]
    # the legend: the three drawn give "most structures"; the others come from SABIO-RK's and SKiD's compound entries,
    # a peptide's residues written out, a name-to-structure tool (OPSIN) and, for a few, the structure the authors deposited
    rest_ = +rest_
    assert set(rest_) == {'SABIO-RK', 'peptide', 'OPSIN', 'SKiD', 'deposited'}, dict(rest_)
    assert n_['Rhea'] + n_['ChEBI'] + n_['PubChem'] > 0.75 * n_['structures'] and rest_['deposited'] < 0.002 * n_['structures'], (dict(n_), dict(rest_))
    F['sources_most'], F['sources_rest'] = True, sorted(rest_)
    # M2, the legend: these look-ups are made by code after a value is stored, and give no kinetic value. cmd_enrich runs
    # after add (/batch: "add → enrich", asserted in facts()), reads the catalogue and never writes it (its results go to
    # its own files under enrich/); the code that finds an entry, a sequence or a compound id handles no kinetic number
    import catlog                               # already imported by facts() (bytecode writing is off since then)
    assert sys.dont_write_bytecode
    src_ = inspect.getsource(catlog.cmd_enrich)
    assert 'get → read → verify → add → enrich → export' in txt('.claude', 'commands', 'batch.md') and F['link']['when'] == 'after reading'
    assert src_.count('open(CATALOG)') == len(re.findall(r'open\(CATALOG\b', src_)) >= 1 and 'from sequences import find_protein' in src_ \
        and 'from structures import find_smiles' in src_ and "Cache(ROOT / 'enrich' / 'protein.json'), Cache(ROOT / 'enrich' / 'structures.json')" in src_
    assert not re.search(r'(?i)kcat|raw_value|\bkm\b', seq_) and not re.search(r'(?i)kcat|raw_value|\bkm\b', ids_) and \
        not re.search(r'(?i)kcat|raw_value', stru_), 'the look-ups handle no kinetic value'
    F['sources_when'] = 'after a value is stored'
    # the record whose pictures are drawn is fed by two of the six: its entry is UniProt's, its structure Rhea's
    assert F['link']['uniprot'] == 'P00805' and F['asp']['smiles'] == 'NC(=O)C[C@H](N)C(=O)O' and F['struct']['entry'] == 'AF-P00805-F1'
    # ---- M2: the line of sequence drawn in the record. The record is the export's cb458776be25f46c (the paper's N248A
    # with L-asparagine, PMID 11106175; facts() checked its links): its stored sequence is UniProt P00805's with the
    # variant placed at 270 (the paper counts from the mature chain, 22 signal residues on), so it differs from the
    # wild-type record's sequence at that one residue. Drawn: residues 267-273, seven letters, 270 the fourth
    mu_, wt_, L_ = drawn_rec['cb458776be25f46c'], drawn_rec['cbb7818048a93f81'], F['link']
    assert (mu_['pubmed_id'], mu_['mutation_signature'], mu_['uniprot_id'], wt_['pubmed_id'], wt_['wild_type'], wt_['uniprot_id']) == \
        ('11106175', L_['mutation'], L_['uniprot'], '11106175', True, L_['uniprot']), mu_['measurement_id']
    ms_, us_ = mu_['sequence'], wt_['sequence']
    assert us_ == wt_['uniprot_sequence'] and len(ms_) == len(us_) == L_['residues'] and \
        [i_ + 1 for i_ in range(len(ms_)) if ms_[i_] != us_[i_]] == [L_['pos']], 'the stored sequence: the entry\'s, changed at one residue'
    assert mu_['sequence_frame'] == f"mature chain after the signal 1-{L_['signal']} (+{L_['signal']})"
    lo_ = L_['pos'] - 3
    line_ = ms_[lo_ - 1:lo_ + 6]
    assert line_ == 'GNGALYK' and line_[3] == ms_[L_['pos'] - 1] == L_['mutation'][-1] == 'A' and us_[L_['pos'] - 1] == L_['mutation'][0] == 'N', line_
    assert us_[lo_ - 1:lo_ + 6] == 'GNGNLYK' and not re.search(r'[^A-Z]|Q', line_), 'capitals with no tail under the line'
    L_['stretch'] = dict(line=line_, first=lo_, last=lo_ + 6, col=3)
    # the record drawn owes its entry to UniProt (found by gene and organism, no PDB or NCBI id printed) and its
    # structure to Rhea: the six names are the code's sources for every record, not this record's own six
    assert mu_['uniprot_how'] == 'gene ansB + organism, unique reviewed entry' and mu_['smiles_source'] == 'Rhea' and \
        mu_['smiles'] == F['asp']['smiles']
    S['sequence_line'] = (f"catlog_wide.jsonl cb458776be25f46c: stored sequence ({L_['residues']} residues, frame \"{mu_['sequence_frame']}\") "
                          f"differs from the wild-type record cbb7818048a93f81 (UniProt {L_['uniprot']}) at {L_['pos']} only; drawn: "
                          f"residues {lo_}-{lo_ + 6}, {line_}, the fourth letter is {L_['pos']} (N in the entry, A stored)")
    S['sources'] = ('tools/sequences.py (UNIPROT, NCBI and SIFTS_XML; routes "2. printed PDB -> local SIFTS", "3. printed GenBank / '
                    'EMBL / RefSeq / NCBI Gene ID"), tools/structures.py (routes 3 Rhea, 4 ChEBI 3-star, 7 PubChem name, 9 ChEBI '
                    '2-star), tools/ids.py (PubChem CID from the InChIKey); catlog_wide.jsonl: records with a UniProt entry and '
                    f"sequence {n_['UniProt']:,}, found or numbered through a PDB entry {n_['PDB']:,}, through an NCBI coding "
                    f"sequence {n_['NCBI']:,}; structures from Rhea {n_['Rhea']:,}, ChEBI {n_['ChEBI']:,}, PubChem {n_['PubChem']:,} "
                    f"(of {n_['records']:,} records; none of these counts is drawn)")


facts_m2(F)



# ------------------------------------------------------------------ the canvas (v4's kit)
class Fig:
    def __init__(self, w, h):
        self.W, self.H = w, h
        self.groups, self.boxes, self.holders, self.arrows = [], [], {}, []

    def g(self, gid, items):
        self.groups.append((gid, [i for i in items if i]))

    def box(self, x0, y0, x1, y1, what, kind='text', inside=None):
        self.boxes.append((x0, y0, x1, y1, what, kind, inside))

    def holder(self, name, x, y, w, h, pad=1.5):
        """A block or card: texts drawn with inside=name must stay within it (less pad)."""
        self.holders[name] = (x + pad, y + pad, x + w - pad, y + h - pad)

    def text(self, x, y, s, size=T6, anchor='start', weight='normal', fill=TXT, italic=False, inside=None, what=None):
        w = wid(s, size, weight == 'bold', italic)
        xs = {'middle': x - w / 2, 'end': x - w}.get(anchor, x)
        self.box(xs, y - 0.72 * size, xs + w, y + 0.21 * size, what or s, 'text', inside)
        at = '' if anchor == 'start' else f' text-anchor="{anchor}"'   # v8: the anchor itself, so a centred label
        xa = xs if anchor == 'start' else x                             # stays centred in Illustrator
        return (f'<text x="{f2(xa)}" y="{f2(y)}"{at} font-family="{PS[(weight == "bold", italic)]}" font-size="{size}" '
                f'fill="{fill}">{esc(s)}</text>')

    def _w(self, s, k, size, weight):
        s2 = s.replace('-', '−') if k == 'sup' else s
        return wid(s2, ES(size) if k in ('sup', 'sub') else size,
                   (weight == 'bold' or 'b' in k) and k not in ('sub', 'sup'), 'i' in k)

    def rwidth(self, parts, size=T6, weight='normal'):
        parts = [p if len(p) == 3 else (p[0], p[1], None) for p in parts]
        return sum(self._w(s, k, size, weight) for s, k, _ in parts)

    def rich(self, x, y, parts, size=T6, anchor='start', weight='normal', fill=TXT, inside=None, what=None):
        """One live text object. parts: (string, kind[, fill]); kind '' plain, 'i' italic, 'b' bold, 'bi' bold
        italic, 'sup'/'sub' 5-pt raised or lowered (a '-' in 'sup' becomes U+2212)."""
        es = ES(size)
        parts = merge(parts)
        ws = [self._w(s, k, size, weight) for s, k, _ in parts]
        width = sum(ws)
        xs = {'middle': x - width / 2, 'end': x - width}.get(anchor, x)
        out, shift = [], 0.0
        top, bot = y - 0.72 * size, y + 0.21 * size
        for (s, k, col), w_ in zip(parts, ws):
            target = -size * 0.38 if k == 'sup' else (size * 0.2 if k == 'sub' else 0.0)
            at = []
            if abs(target - shift) > 1e-9:
                at.append(f'dy="{f2(target - shift)}"')
                shift = target
            if k in ('sup', 'sub'):
                at.append(f'font-size="{es}"')
                top = min(top, y + target - 0.72 * es)
                bot = max(bot, y + target + 0.21 * es)
            face = PS[((weight == 'bold' or 'b' in k) and k not in ('sup', 'sub'), 'i' in k)]
            if face != PS[(weight == 'bold', False)]:      # the run's own Arial face, by PostScript name
                at.append(f'font-family="{face}"')
            if col:
                at.append(f'fill="{col}"')
            s = esc(s.replace('-', '−') if k == 'sup' else s)
            out.append(f'<tspan {" ".join(at)}>{s}</tspan>' if at else s)
        self.box(xs, top, xs + width, bot, what or ''.join(p[0] for p in parts), 'text', inside)
        # rich text keeps its computed start: cairosvg sets a centred text with several tspans apart (seen in v8:
        # 'refused values · log' drawn with a gap), and every rich text here is one line
        return (f'<text x="{f2(xs)}" y="{f2(y)}" font-family="{PS[(weight == "bold", False)]}" font-size="{size}" '
                f'fill="{fill}">' + ''.join(out) + '</text>')

    def text_nb(self, x, y, s, n, size=T6, weight='normal', fill=TXT, inside=None, what=None):
        """Text that follows another on its baseline with a gap of n no-break spaces, set as part of the text (x: where
        the first ends). Illustrator's unified text joins the two into one object and keeps exactly this gap."""
        pad = '\u00a0' * n
        t = self.text(x, y, pad + s, size, weight=weight, fill=fill, inside=inside, what=what or s)
        b = self.boxes[-1]
        self.boxes[-1] = (b[0] + wid(pad, size, weight == 'bold'),) + b[1:]   # the box starts at the first glyph
        return t

    def panel_letter(self, x, y, letter, title):
        a = self.text(x, y, letter, LETTER, weight='bold', fill='#000000')
        # v8: v4's 4-pt gap as two no-break spaces of the 7-pt bold title (3.89 pt), so the letter and its title stay
        # one Illustrator text object without moving the title
        t = self.text_nb(x + wid(letter, LETTER, True), y, title, 2, T7, weight='bold', fill='#000000')
        return [a, t]

    def rect(self, x, y, w, h, fill='none', stroke=None, sw=0.5, rx=0.0, dash=None, mark=None):
        st = f' stroke="{stroke}" stroke-width="{f2(sw)}"' if stroke else ''
        ds = f' stroke-dasharray="{dash}"' if dash else ''
        r = f' rx="{f2(rx)}"' if rx else ''
        if mark:
            self.box(x, y, x + w, y + h, mark, 'mark')
        return f'<rect x="{f2(x)}" y="{f2(y)}" width="{f2(w)}" height="{f2(h)}"{r} fill="{fill}"{st}{ds}/>'

    def line(self, x0, y0, x1, y1, stroke=GREY, sw=0.5, dash=None, mark=None):
        ds = f' stroke-dasharray="{dash}"' if dash else ''
        if mark:
            self.box(min(x0, x1) - sw, min(y0, y1) - sw, max(x0, x1) + sw, max(y0, y1) + sw, mark, 'mark')
        return (f'<path d="M{f2(x0)},{f2(y0)} L{f2(x1)},{f2(y1)}" fill="none" stroke="{stroke}" '
                f'stroke-width="{f2(sw)}"{ds}/>')

    def arrow(self, pts, shaft=SHAFT, hl=HL, hw=HW, fill=INK, what='arrow'):
        """One closed polygon: a shaft along the polyline pts (right-angle bends, mitred) and a solid head at the last
        point (the tip)."""
        pts = [tuple(p) for p in pts]
        (ax, ay), (bx, by) = pts[-2], pts[-1]
        n = math.hypot(bx - ax, by - ay)
        assert n > hl + 0.8, (what, n)
        ux, uy = (bx - ax) / n, (by - ay) / n
        base = (bx - ux * hl, by - uy * hl)
        path = pts[:-1] + [base]
        h = shaft / 2
        segs = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
        norms = []
        for (p, q) in segs:
            L = math.hypot(q[0] - p[0], q[1] - p[1])
            norms.append((-(q[1] - p[1]) / L, (q[0] - p[0]) / L))
        left, right = [], []
        for i, p in enumerate(path):
            if i in (0, len(path) - 1):
                nx, ny = norms[0] if i == 0 else norms[-1]
            else:
                n1, n2 = norms[i - 1], norms[i]
                d = 1 + n1[0] * n2[0] + n1[1] * n2[1]
                nx, ny = (n1[0] + n2[0]) / d, (n1[1] + n2[1]) / d
            left.append((p[0] + nx * h, p[1] + ny * h))
            right.append((p[0] - nx * h, p[1] - ny * h))
        nx, ny = norms[-1]
        head = [(base[0] + nx * hw / 2, base[1] + ny * hw / 2), (bx, by), (base[0] - nx * hw / 2, base[1] - ny * hw / 2)]
        poly = left + head + right[::-1]
        for (p, q) in segs + [(base, (bx, by))]:     # one mark box per segment
            pad = hw / 2 if (p, q) == (base, (bx, by)) else h
            self.box(min(p[0], q[0]) - pad, min(p[1], q[1]) - pad, max(p[0], q[0]) + pad, max(p[1], q[1]) + pad,
                     what, 'mark')
        self.arrows.append((what, n, hl))
        return '<path d="M' + ' L'.join(f'{f2(a)},{f2(b)}' for a, b in poly) + f' Z" fill="{fill}"/>'

    # ---- checks
    def overlaps(self, tol=0.25):
        bad = []
        bx = self.boxes
        for i in range(len(bx)):
            for j in range(i + 1, len(bx)):
                a, b = bx[i], bx[j]
                if a[5] == 'mark' and b[5] == 'mark':
                    continue
                if a[0] < b[2] - tol and b[0] < a[2] - tol and a[1] < b[3] - tol and b[1] < a[3] - tol:
                    bad.append((a[4], b[4]))
        return bad

    def escaped(self):
        bad = []
        for b in self.boxes:
            if b[6]:
                x0, y0, x1, y1 = self.holders[b[6]]
                if b[0] < x0 - 0.01 or b[2] > x1 + 0.01 or b[1] < y0 - 0.01 or b[3] > y1 + 0.01:
                    bad.append((b[6], b[4], [round(v, 1) for v in (b[0] - x0, x1 - b[2], b[1] - y0, y1 - b[3])]))
        return bad

    def clipped(self):
        return [b[4] for b in self.boxes if b[0] < -0.01 or b[1] < -0.01 or b[2] > self.W + 0.01 or b[3] > self.H + 0.01]

    def svg(self):
        m = MARGIN
        body = [f'<rect id="background" x="{f2(-m)}" y="{f2(-m)}" width="{f2(self.W + 2 * m)}" height="{f2(self.H + 2 * m)}" '
                f'fill="#FFFFFF"/>']
        ids, cur = set(), None
        for gid, its in self.groups:            # v8: each panel one named group (an Illustrator layer), its pieces inside
            pan = 'b' if gid == 'zoom lines' else 'd' if gid == 'zoom lines d' else \
                next(q for q in 'abcd' if gid.startswith((q + ' ', 'panel letter ' + q)))
            if pan != cur:
                if cur:
                    body.append('</g>')
                assert f'panel_{pan}' not in ids, pan
                ids.add(f'panel_{pan}')
                body.append(f'<g id="panel_{pan}">')
                cur = pan
            i = re.sub(r'[^A-Za-z0-9_\-]', '', gid.replace(' ', '_'))
            assert i not in ids, i
            ids.add(i)
            body.append(f'<g id="{i}">' + ''.join(its) + '</g>')
        body.append('</g>')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
               f'width="{f2((self.W + 2 * m) / MM)}mm" '
               f'height="{f2((self.H + 2 * m) / MM)}mm" viewBox="{f2(-m)} {f2(-m)} {f2(self.W + 2 * m)} {f2(self.H + 2 * m)}">'
               + '\n'.join(body) + '</svg>\n')
        # S1: one <image>, the structure picture of c's Linked row, embedded as PNG data (set aside for these checks)
        bare = re.sub(r'xlink:href="data:image/png;base64,[A-Za-z0-9+/=]+"', 'xlink:href=""', svg)
        assert bare.count('<image') == 1 and len(bare) < len(svg), 'M2: one embedded picture, the enzyme of b\'s record'
        for bad in ('<filter', '<mask', '<clipPath', 'opacity', 'Gradient'):
            assert bad not in bare, bad
        sizes = [float(v) for v in re.findall(r'font-size="([\d.]+)"', svg)]
        strokes = [float(v) for v in re.findall(r'stroke-width="([\d.]+)"', svg)]
        fams = set(re.findall(r'font-family="([^"]+)"', svg))
        body_sizes = [s for s in sizes if s != LETTER]
        assert min(sizes) >= 5 and max(body_sizes) <= 7 and min(strokes) >= 0.25 and fams <= set(PS.values()), \
            (min(sizes), max(body_sizes), min(strokes), fams)
        self.stats = dict(text_objects=svg.count('<text'), groups=len(ids), min_font=min(sizes),
                          max_text_font=max(body_sizes), min_stroke=min(strokes), elements=svg.count('<'),
                          size_mm=[round((self.W + 2 * m) / MM, 1), round((self.H + 2 * m) / MM, 1)])
        return svg


def merge(parts):
    """Rich parts as (s, kind, fill), neighbours with the same kind and fill joined (one tspan each)."""
    out = []
    for p in parts:
        p = p if len(p) == 3 else (p[0], p[1], None)
        if out and out[-1][1:] == p[1:]:
            out[-1] = (out[-1][0] + p[0],) + p[1:]
        else:
            out.append(p)
    return out


def kin(s, fill=None):
    """A label as rich parts: kcat, Km, kcat/Km, K0.5, KmA and KmB as italic letters with roman subscripts."""
    out = []
    for tok in re.split(r'(kcat|KmA|KmB|Km|K0\.5)', s):
        if tok == 'kcat':
            out += [('k', 'i', fill), ('cat', 'sub', fill)]
        elif tok in ('Km', 'KmA', 'KmB', 'K0.5'):
            out += [('K', 'i', fill), (tok[1:], 'sub', fill)]
        elif tok:
            out.append((tok, '', fill))
    return out


# ------------------------------------------------------------------ icons: simple line art, drawn here (v4's, plus a loop)
def icon(cv, kind, cx, cy, s=14, col=INK, fill='#FFFFFF', sw=0.6, what=None, accent=None):
    """A line icon of size s (pt) centred at (cx, cy): doc, image, table, code, check, db, flag, book, tick, docglass,
    doctick, scales, loop. Returns one SVG group string."""
    h = s / 2
    st = f'fill="none" stroke="{col}" stroke-width="{f2(sw)}" stroke-linejoin="round" stroke-linecap="round"'
    sf = f'fill="{fill}" stroke="{col}" stroke-width="{f2(sw)}" stroke-linejoin="round"'
    o = []
    if kind in ('doc', 'image', 'table'):                   # a page with a folded corner
        pw, ph, c = 0.74 * s, 0.94 * s, 0.24 * s
        x0, y0, x1, y1 = cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2
        o.append(f'<path d="M{f2(x0)},{f2(y0)} L{f2(x1 - c)},{f2(y0)} L{f2(x1)},{f2(y0 + c)} L{f2(x1)},{f2(y1)} '
                 f'L{f2(x0)},{f2(y1)} Z" {sf}/>')
        o.append(f'<path d="M{f2(x1 - c)},{f2(y0)} L{f2(x1 - c)},{f2(y0 + c)} L{f2(x1)},{f2(y0 + c)}" {st}/>')
        if kind == 'doc':                                    # lines of text
            for k, f in enumerate((0.55, 0.78, 0.78, 0.5)):
                yy = y0 + ph * (0.36 + 0.15 * k)
                o.append(f'<path d="M{f2(x0 + 0.16 * pw)},{f2(yy)} L{f2(x0 + (0.16 + 0.68 * f) * pw)},{f2(yy)}" {st}/>')
        elif kind == 'image':                                # a rendered page: a picture (hills and sun)
            fx0, fy0, fx1, fy1 = x0 + 0.14 * pw, y0 + 0.34 * ph, x1 - 0.14 * pw, y1 - 0.14 * ph
            o.append(f'<rect x="{f2(fx0)}" y="{f2(fy0)}" width="{f2(fx1 - fx0)}" height="{f2(fy1 - fy0)}" {st}/>')
            o.append(f'<path d="M{f2(fx0)},{f2(fy1)} L{f2(fx0 + 0.38 * (fx1 - fx0))},{f2(fy0 + 0.45 * (fy1 - fy0))} '
                     f'L{f2(fx0 + 0.62 * (fx1 - fx0))},{f2(fy0 + 0.75 * (fy1 - fy0))} '
                     f'L{f2(fx0 + 0.78 * (fx1 - fx0))},{f2(fy0 + 0.55 * (fy1 - fy0))} L{f2(fx1)},{f2(fy1)}" {st}/>')
            o.append(f'<circle cx="{f2(fx0 + 0.75 * (fx1 - fx0))}" cy="{f2(fy0 + 0.28 * (fy1 - fy0))}" '
                     f'r="{f2(0.06 * s)}" {st}/>')
        else:                                                # a table: rules and cells
            tx0, tx1 = x0 + 0.14 * pw, x1 - 0.14 * pw
            for k in range(4):
                yy = y0 + ph * (0.36 + 0.15 * k)
                o.append(f'<path d="M{f2(tx0)},{f2(yy)} L{f2(tx1)},{f2(yy)}" {st}/>')
            for f in (0.42, 0.7):
                xx = tx0 + f * (tx1 - tx0)
                o.append(f'<path d="M{f2(xx)},{f2(y0 + ph * 0.36)} L{f2(xx)},{f2(y0 + ph * 0.81)}" {st}/>')
    elif kind == 'code':                                     # </>
        a, b = 0.2 * s, 0.26 * s
        o.append(f'<path d="M{f2(cx - 0.18 * s)},{f2(cy - b)} L{f2(cx - 0.18 * s - a)},{f2(cy)} '
                 f'L{f2(cx - 0.18 * s)},{f2(cy + b)}" {st}/>')
        o.append(f'<path d="M{f2(cx + 0.18 * s)},{f2(cy - b)} L{f2(cx + 0.18 * s + a)},{f2(cy)} '
                 f'L{f2(cx + 0.18 * s)},{f2(cy + b)}" {st}/>')
        o.append(f'<path d="M{f2(cx + 0.08 * s)},{f2(cy - 0.34 * s)} L{f2(cx - 0.08 * s)},{f2(cy + 0.34 * s)}" {st}/>')
    elif kind == 'check':                                    # a checklist
        bw, bh = 0.78 * s, 0.9 * s
        x0, y0 = cx - bw / 2, cy - bh / 2
        o.append(f'<rect x="{f2(x0)}" y="{f2(y0)}" width="{f2(bw)}" height="{f2(bh)}" rx="{f2(0.08 * s)}" {sf}/>')
        for k in range(3):
            yy = y0 + bh * (0.26 + 0.25 * k)
            o.append(f'<path d="M{f2(x0 + 0.14 * bw)},{f2(yy)} L{f2(x0 + 0.22 * bw)},{f2(yy + 0.07 * s)} '
                     f'L{f2(x0 + 0.36 * bw)},{f2(yy - 0.08 * s)}" {st}/>')
            o.append(f'<path d="M{f2(x0 + 0.48 * bw)},{f2(yy)} L{f2(x0 + 0.84 * bw)},{f2(yy)}" {st}/>')
    elif kind == 'db':                                       # a cylinder
        rx, ry, hh = 0.4 * s, 0.13 * s, 0.68 * s
        x0, x1, yt, yb = cx - rx, cx + rx, cy - hh / 2, cy + hh / 2
        o.append(f'<path d="M{f2(x0)},{f2(yt)} L{f2(x0)},{f2(yb)} A{f2(rx)},{f2(ry)} 0 0 0 {f2(x1)},{f2(yb)} '
                 f'L{f2(x1)},{f2(yt)}" {sf}/>')
        o.append(f'<ellipse cx="{f2(cx)}" cy="{f2(yt)}" rx="{f2(rx)}" ry="{f2(ry)}" {sf}/>')
        for f in (0.36, 0.7):
            yy = yt + f * hh
            o.append(f'<path d="M{f2(x0)},{f2(yy)} A{f2(rx)},{f2(ry)} 0 0 0 {f2(x1)},{f2(yy)}" {st}/>')
    elif kind == 'flag':
        px = cx - 0.26 * s
        o.append(f'<path d="M{f2(px)},{f2(cy + 0.45 * s)} L{f2(px)},{f2(cy - 0.45 * s)}" {st}/>')
        o.append(f'<path d="M{f2(px)},{f2(cy - 0.42 * s)} L{f2(cx + 0.36 * s)},{f2(cy - 0.27 * s)} '
                 f'L{f2(px)},{f2(cy - 0.08 * s)} Z" fill="{accent or col}" stroke="{accent or col}" '
                 f'stroke-width="{f2(sw)}" stroke-linejoin="round"/>')
    elif kind == 'book':                                     # an open book with ruled pages (the error ledger)
        y0, y1, sp = cy - 0.34 * s, cy + 0.38 * s, 0.06 * s
        for d in (-1, 1):
            o.append(f'<path d="M{f2(cx)},{f2(y0 + sp)} C{f2(cx + d * 0.18 * s)},{f2(y0 - 0.04 * s)} '
                     f'{f2(cx + d * 0.36 * s)},{f2(y0 - 0.04 * s)} {f2(cx + d * 0.48 * s)},{f2(y0 + 0.02 * s)} '
                     f'L{f2(cx + d * 0.48 * s)},{f2(y1)} C{f2(cx + d * 0.36 * s)},{f2(y1 - 0.06 * s)} '
                     f'{f2(cx + d * 0.18 * s)},{f2(y1 - 0.06 * s)} {f2(cx)},{f2(y1)} Z" {sf}/>')
        for k in range(3):
            yy = y0 + 0.2 * s + 0.15 * s * k
            o.append(f'<path d="M{f2(cx - 0.38 * s)},{f2(yy)} L{f2(cx - 0.1 * s)},{f2(yy)}" {st}/>')
            o.append(f'<path d="M{f2(cx + 0.1 * s)},{f2(yy)} L{f2(cx + 0.38 * s)},{f2(yy)}" {st}/>')
    elif kind == 'tick':
        o.append(f'<path d="M{f2(cx - 0.36 * s)},{f2(cy)} L{f2(cx - 0.1 * s)},{f2(cy + 0.28 * s)} '
                 f'L{f2(cx + 0.4 * s)},{f2(cy - 0.3 * s)}" fill="none" stroke="{col}" stroke-width="{f2(sw)}" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')
    elif kind in ('docglass', 'doctick'):                    # a page being read / a page checked
        pw, ph, c = 0.62 * s, 0.82 * s, 0.2 * s
        x0, y0 = cx - 0.46 * s, cy - 0.47 * s
        x1, y1 = x0 + pw, y0 + ph
        o.append(f'<path d="M{f2(x0)},{f2(y0)} L{f2(x1 - c)},{f2(y0)} L{f2(x1)},{f2(y0 + c)} L{f2(x1)},{f2(y1)} '
                 f'L{f2(x0)},{f2(y1)} Z" {sf}/>')
        o.append(f'<path d="M{f2(x1 - c)},{f2(y0)} L{f2(x1 - c)},{f2(y0 + c)} L{f2(x1)},{f2(y0 + c)}" {st}/>')
        for k, f in enumerate((0.7, 0.7, 0.45)):
            yy = y0 + ph * (0.38 + 0.17 * k)
            o.append(f'<path d="M{f2(x0 + 0.16 * pw)},{f2(yy)} L{f2(x0 + (0.16 + 0.7 * f) * pw)},{f2(yy)}" {st}/>')
        bx_, by_, br = cx + 0.22 * s, cy + 0.18 * s, 0.22 * s
        o.append(f'<circle cx="{f2(bx_)}" cy="{f2(by_)}" r="{f2(br)}" fill="{fill}" stroke="{col}" '
                 f'stroke-width="{f2(sw)}"/>')
        if kind == 'docglass':
            o.append(f'<path d="M{f2(bx_ + 0.7 * br)},{f2(by_ + 0.7 * br)} L{f2(cx + 0.5 * s)},{f2(cy + 0.48 * s)}" '
                     f'fill="none" stroke="{col}" stroke-width="{f2(sw * 1.8)}" stroke-linecap="round"/>')
        else:
            o.append(f'<path d="M{f2(bx_ - 0.5 * br)},{f2(by_ + 0.02 * s)} L{f2(bx_ - 0.12 * br)},{f2(by_ + 0.4 * br)} '
                     f'L{f2(bx_ + 0.55 * br)},{f2(by_ - 0.4 * br)}" fill="none" stroke="{accent or col}" '
                     f'stroke-width="{f2(sw * 1.3)}" stroke-linecap="round" stroke-linejoin="round"/>')
    elif kind == 'scales':                                   # a balance: an agent decides
        top, bot, beam = cy - 0.42 * s, cy + 0.42 * s, cy - 0.26 * s
        o.append(f'<path d="M{f2(cx)},{f2(top + 0.06 * s)} L{f2(cx)},{f2(bot)}" {st}/>')
        o.append(f'<path d="M{f2(cx - 0.22 * s)},{f2(bot)} L{f2(cx + 0.22 * s)},{f2(bot)}" {st}/>')
        o.append(f'<path d="M{f2(cx - 0.42 * s)},{f2(beam)} L{f2(cx + 0.42 * s)},{f2(beam)}" {st}/>')
        o.append(f'<circle cx="{f2(cx)}" cy="{f2(top + 0.02 * s)}" r="{f2(0.05 * s)}" fill="{col}"/>')
        for sx in (-1, 1):
            ax_ = cx + sx * 0.42 * s
            py = cy + 0.06 * s
            o.append(f'<path d="M{f2(ax_ - 0.14 * s)},{f2(py)} L{f2(ax_)},{f2(beam)} L{f2(ax_ + 0.14 * s)},{f2(py)}" {st}/>')
            o.append(f'<path d="M{f2(ax_ - 0.17 * s)},{f2(py)} Q{f2(ax_)},{f2(py + 0.22 * s)} {f2(ax_ + 0.17 * s)},'
                     f'{f2(py)} Z" {sf}/>')
    elif kind == 'loop':                                     # a circular arrow: the loop runs again (new in v6)
        r = 0.34 * s
        t0, t1 = math.radians(-40), math.radians(225)       # clockwise from upper right round to upper left
        p0 = (cx + r * math.cos(t0), cy + r * math.sin(t0))
        p1 = (cx + r * math.cos(t1), cy + r * math.sin(t1))
        o.append(f'<path d="M{f2(p0[0])},{f2(p0[1])} A{f2(r)},{f2(r)} 0 1 1 {f2(p1[0])},{f2(p1[1])}" {st}/>')
        tx, ty = -math.sin(t1), math.cos(t1)                 # the arc's direction at its end
        nx, ny = -ty, tx
        hl_, hw_ = 0.3 * s, 0.26 * s                         # a solid head, as the figure's arrows
        tip = (p1[0] + tx * hl_ * 0.8, p1[1] + ty * hl_ * 0.8)
        b0 = (p1[0] - tx * hl_ * 0.2, p1[1] - ty * hl_ * 0.2)
        o.append(f'<path d="M{f2(tip[0])},{f2(tip[1])} L{f2(b0[0] + nx * hw_ / 2)},{f2(b0[1] + ny * hw_ / 2)} '
                 f'L{f2(b0[0] - nx * hw_ / 2)},{f2(b0[1] - ny * hw_ / 2)} Z" fill="{col}" stroke="{col}" '
                 f'stroke-width="{f2(sw * 0.6)}" stroke-linejoin="round"/>')
    elif kind == 'person':                                   # head and shoulders: people, a's first role
        o.append(f'<circle cx="{f2(cx)}" cy="{f2(cy - 0.2 * s)}" r="{f2(0.2 * s)}" {sf}/>')
        o.append(f'<path d="M{f2(cx - 0.38 * s)},{f2(cy + 0.42 * s)} A{f2(0.38 * s)},{f2(0.38 * s)} 0 0 1 '
                 f'{f2(cx + 0.38 * s)},{f2(cy + 0.42 * s)} Z" {sf}/>')
    elif kind == 'folder':                                   # a folder with a tab: an agent's own scratch folder (v7)
        x0, x1, y0, y1 = cx - 0.46 * s, cx + 0.46 * s, cy - 0.26 * s, cy + 0.38 * s
        tw, th = 0.34 * s, 0.13 * s
        o.append(f'<path d="M{f2(x0)},{f2(y1)} L{f2(x0)},{f2(y0 - th)} L{f2(x0 + tw)},{f2(y0 - th)} '
                 f'L{f2(x0 + tw + th)},{f2(y0)} L{f2(x1)},{f2(y0)} L{f2(x1)},{f2(y1)} Z" {sf}/>')
    else:
        raise ValueError(kind)
    hx = 0.6 * s if kind == 'scales' else h            # the scales' pans reach 0.59 s from the centre
    cv.box(cx - hx, cy - h, cx + hx, cy + h, what or f'icon {kind}', 'mark')
    return f'<g>{"".join(o)}</g>'


def cylinder(x0, x1, ytop, ybot, ry, edge, sw=0.75):
    """A cylinder in outline: white body and white top ellipse, one edge colour (the catalogue's line style).
    ytop: the top ellipse's centre; ybot: the lowest point of the bottom arc."""
    rx = (x1 - x0) / 2
    cx = (x0 + x1) / 2
    return [f'<path d="M{f2(x0)},{f2(ytop)} L{f2(x0)},{f2(ybot - ry)} A{f2(rx)},{f2(ry)} 0 0 0 {f2(x1)},'
            f'{f2(ybot - ry)} L{f2(x1)},{f2(ytop)}" fill="#FFFFFF" stroke="{edge}" stroke-width="{f2(sw)}"/>',
            f'<ellipse cx="{f2(cx)}" cy="{f2(ytop)}" rx="{f2(rx)}" ry="{f2(ry)}" fill="#FFFFFF" stroke="{edge}" '
            f'stroke-width="{f2(sw)}"/>']

# ================================================================== build
# 2026-11-05, the owner: "example heavy ... it should be more generalized", "the icons and the figures and the color
# thing is still a bit AI-ish", "the co-learning or the agentic workflow and the human input ... should also be
# focused", and the other chats' work used where it helps. So: white square boxes, a thin bar in the colour of who
# acts, no icons, no key, no cylinders; b states each step's rules in general with one example; c is one row; d is the
# loop people and agents run, counted from the record (the error taxonomy, the agent-highlights chat's 162 checked
# findings, the hard-case test).
cv = Fig(W, 600)
g = cv.g
GREY_TXT = '#595959'                       # R4: asides only (it was #6E6E6E, and on statements of fact too)
EDGE = '#9A9A9A'                           # a box's outline
BARW = 2.2                                 # the role bar
TXI = BARW + 4.0                           # text inset in a box with a bar
RC_ = {'agent': NPG['cyan'], 'code': NPG['navy'], 'people': NPG['brown'], 'catalog': NPG['green'], 'outside': '#8C8C8C'}
IN0, IN1 = 7.0, W - 7.0                    # b's, c's and d's content edges
SPACE = 1.6


def sup(s, fill=None):
    """Plain text with '^-1' and '^6' set as superscripts."""
    out = []
    for tok in re.split(r'(\^-?\d+)', s):
        if tok.startswith('^'):
            out.append((tok[1:], 'sup', fill))
        elif tok:
            out.append((tok, '', fill))
    return out


def rk(s, fill=None):
    """Rich parts: '^-1' and '^6' raised; kcat, Km and K0.5 as italic letters with roman subscripts."""
    out = []
    for tok in re.split(r'(\^-?\d+)', s):
        if tok.startswith('^'):
            out.append((tok[1:], 'sup', fill))
        elif tok:
            out += kin(tok, fill)
    return out


def mixed(gid, x, y, segs, size=T55, inside=None, weight='normal'):
    """One line: ('t', words) set plain; ('p', print) on a grey plate, as the paper or its PDF text prints it."""
    out, xx = [], x
    for kind, s in segs:
        parts = sup(s) if kind == 'v' else rk(s)
        if kind in 'pv':
            w_ = cv.rwidth(parts, size)
            out.append(cv.rect(xx, y - 6.1, w_ + 3.0, 8.0, BAND, None, rx=0.6))
            out.append(cv.rich(xx + 1.5, y, parts, size, inside=inside, what=f'{gid} print {s}'))
            xx += w_ + 3.0 + SPACE
        else:
            if s[0] in ',;:.':
                xx -= SPACE + 0.5
            w_ = cv.rwidth(parts, size, weight)
            out.append(cv.rich(xx, y, parts, size, weight=weight, fill=GREY_TXT if kind == 'g' else TXT,
                               inside=inside, what=f'{gid} words {s}'))
            xx += w_ + SPACE
    return out, xx - SPACE


def molecule(smiles, x, y, w, h, what):
    """A skeletal formula from RDKit as plain paths in ink (bonds stroked, atom labels and wedges filled), in w x h."""
    from rdkit import Chem
    from rdkit.Chem.Draw import rdMolDraw2D
    pw = int(round(300 * w / 54.0))       # T1 (S2): the canvas grows with the drawing, so its labels stay 6.5 pt
    ph = int(round(pw * h / w))
    d = rdMolDraw2D.MolDraw2DSVG(pw, ph)
    o = d.drawOptions()
    o.clearBackground = False
    o.padding = 0.06
    o.bondLineWidth = 2
    o.useBWAtomPalette()
    # checker: the atom labels in Arial at the figure's 6.5 pt (RDKit's own font at 30 drew them 5.3 pt, under the
    # 5.5-pt floor, and smaller than every other word once the text went to 6.5 pt)
    o.fontFile = '/System/Library/Fonts/Supplemental/Arial.ttf'
    o.minFontSize = o.maxFontSize = 36
    d.DrawMolecule(Chem.MolFromSmiles(smiles))
    d.FinishDrawing()
    k = w / pw
    out, glyphs = [], []
    for el in re.findall(r'<path[^>]*/>', d.GetDrawingText()):
        dd = re.search(r"d='([^']+)'", el).group(1)
        n = [0]

        def tr(m_):
            v = float(m_.group(0))
            n[0] += 1
            return f2(x + v * k) if n[0] % 2 else f2(y + v * k)
        dd = re.sub(r'-?\d+\.?\d*', tr, dd.replace('\n', ' '))
        dd = re.sub(r'\s+', ' ', dd).strip()
        if 'fill:none' in el:
            out.append(f'<path d="{dd}" fill="none" stroke="{INK}" stroke-width="{f2(SWB)}" stroke-linecap="round"/>')
        else:
            glyphs.append((len(out), dd))
            out.append(f'<path d="{dd}" fill="{INK}"/>')
    xy = lambda dd_: [float(v) for v in re.findall(r'-?\d+\.?\d*', dd_)]    # every number a coordinate (M, L, Q)
    glyph_h = [max(xy(dd_)[1::2]) - min(xy(dd_)[1::2]) for _, dd_ in glyphs]
    cap = max(glyph_h)
    # checker: a capital (N, H, O) as tall as 6.5-pt Arial's (cap height 0.716 em), so the labels read as 6.5-pt text
    assert abs(cap - 0.716 * 6.5) < 0.45, (what, round(cap, 2))
    # checker (V1V4): RDKit sets a label's subscript (the 2 of NH2) at about 0.66 of the label: 4.3 pt here, under the
    # 5.5-pt floor and Nature's 5 pt. Each subscript digit is scaled about its own baseline and left edge to the figure's
    # subscript size (ES: 5.5 pt, as the 'cat' of kcat in the same box); the 2's ink is 0.719 em tall in Arial
    from fontTools.ttLib import TTFont
    from fontTools.pens.boundsPen import BoundsPen
    af = TTFont('/System/Library/Fonts/Supplemental/Arial.ttf')
    bp = BoundsPen(af.getGlyphSet())
    af.getGlyphSet()[af.getBestCmap()[ord('2')]].draw(bp)
    dig = (bp.bounds[3] - bp.bounds[1]) / af['head'].unitsPerEm
    subs, sizes = 0, []
    for (i, dd_), h_ in zip(glyphs, glyph_h):
        if h_ < 0.8 * cap:
            v = xy(dd_)
            f_ = ES(T55) * dig / h_
            x0_, y1_ = min(v[0::2]), max(v[1::2])
            nv = iter([x0_ + (c - x0_) * f_ if j % 2 == 0 else y1_ + (c - y1_) * f_ for j, c in enumerate(v)])
            dd_ = re.sub(r'-?\d+\.?\d*', lambda m_: f2(next(nv)), dd_)
            out[i] = f'<path d="{dd_}" fill="{INK}"/>'
            v = xy(dd_)
            assert x - 0.05 <= min(v[0::2]) and max(v[0::2]) <= x + w + 0.05 and max(v[1::2]) <= y + h + 0.05, (what, 'sub')
            subs += 1
        v = xy(dd_)
        sizes.append((max(v[1::2]) - min(v[1::2])) / dig)
    assert subs == 2, (what, subs)                                   # the 2 of each NH2 in asparagine
    assert min(sizes) >= ES(T55) - 0.05, (what, [round(s_, 2) for s_ in sizes])   # every letter and digit 5.5 pt or more
    cv.box(x, y, x + w, y + h, what, 'mark')
    return out


def boxr(gid, x, y, w, h, role=None, edge=EDGE, sw=0.5, dash=None):
    """A white, square-cornered box; role: a bar of that colour along its left edge (a pair of roles: two halves)."""
    cv.holder(gid, x, y, w, h, 1.0)
    it = [cv.rect(x, y, w, h, '#FFFFFF', edge, sw, 0, dash)]
    if role:
        roles = role if isinstance(role, tuple) else (role,)
        hh = h / len(roles)
        for k, r_ in enumerate(roles):
            it.append(cv.rect(x, y + k * hh, BARW, hh, RC_[r_], None))
    return it


def tick(x, y, role, h=5.0):
    """A short bar in the colour of who acts, in front of a line of text (baseline y)."""
    roles = role if isinstance(role, tuple) else (role,)
    hh = h / len(roles)
    return [cv.rect(x, y - 4.1 + k * hh, 1.6, hh, RC_[r_], None) for k, r_ in enumerate(roles)]


def step(gid, x, y, w, h, role, title, lines, size=T55, ls=6.9, tfill=TXT):
    """A box of a: who acts (the bar), the step in bold, two short lines, set left and centred top to bottom."""
    it = boxr(gid, x, y, w, h, role)
    block = 0.72 * TT + 3.4 + 0.72 * size + ls * (len(lines) - 1)
    yy = y + (h - block) / 2 + 0.72 * TT
    it.append(cv.text(x + TXI, yy, title, TT, weight='bold', fill=tfill, inside=gid))
    yy += 3.4 + 0.72 * size
    for ln in lines:
        it.append(cv.text(x + TXI, yy, ln, size, inside=gid))
        yy += ls
    g(gid, it)



# ================================================================== design A: "v7, lean"
# The owner loved v7's look (big step boxes filled in the colour of who acts, one icon and a short label in each, one
# left-to-right path, the zoom from a into b) and hated v8's words. So every box says one thing, rule lists and
# explanations go to the legend, and real print appears only on grey plates, one case per step.
AF = 0.5                                   # role fills: the NPG colour at alpha 0.5 over white, flattened
# T1 round 2 (the editor: "the tints are not equally light: tan and slate are darker than mint, so the People box and
# the two code tiles catch the eye first"; the owner: "less color ish"): slate and tan lighter, toward mint's lightness
# (L* 86.0 and 86.4 against mint's 89.6, from 80.6 and 83.3: their lower chroma reads as lighter at equal L*), so the
# three roles carry the same weight; mint stays as it was, so the catalogue's tint stays the lightest fill
AFR = {'agent': AF, 'code': 0.36, 'people': 0.40}
FILL = {'agent': flat(NPG['mint'], AFR['agent']), 'code': flat(NPG['slate'], AFR['code']),
        'people': flat(NPG['tan'], AFR['people'])}
assert FILL == {'agent': '#C8E8E0', 'code': '#D3D7E4', 'people': '#DFD7CE'}, FILL
EDGEC = {'agent': '#4E9C8B', 'code': NPG['slate'], 'people': '#8A7660'}   # R4: code's outline the lighter slate (#8491B4, L* 60
#                                            as the agents'): #5D6A92 sat on navy's hue, so b's Convert and Check cards looked
#                                            framed in the databases' colour
assert EDGEC['code'] == '#8491B4'
RX = 1.6                                   # every box's corner radius
SWB = 0.5                                  # box outlines (R4: 0.5 against the arrows' 0.75, so the flow reads first)
HAIR = 0.35                                # R4: hairlines: strip rules, dividers, zoom lines, the databases' name boxes
LGAP = 1.9                                 # R4: the white between a line and its label, one distance in a and d
WRULE = 0.75                               # R4: the white rules on the grey plates and the record's columns
TGAP = 5.5                                 # R4: from a panel title's baseline to its boxes, one distance in a, b, c and d
ISW = 0.5                                  # icon strokes: one weight for every icon (R4: the outlines' weight)
NEUT = GREY                                # outline of a white box no single role owns (R4: the one neutral grey)
PLATE = '#E9E9E9'                          # grey plate: print as the paper or its PDF text has it (R3: darker than the band)
PRX = 0.85                                 # R4: one corner radius (0.3 mm) for plates, name boxes, step tiles and the record's columns
XL, XR = 0.45, W - 0.45                    # outlines on the art's edges stay inside it (half a 0.75-pt stroke)


def ico(kind, cx, cy, s, what, accent=None, ink=INK, bg='#FFFFFF'):
    """A line icon of one stroke weight, ink on white, about s wide, centred at (cx, cy). accent: the flag's pennant
    filled in that colour (S1: red, errors). S1r: ink, the stroke colour (white on the catalogue green); bg, the fill of
    its closed parts (a person tan, an agent's page mint: who acts, as the role fills)."""
    st = f'fill="none" stroke="{ink}" stroke-width="{f2(ISW)}" stroke-linejoin="round" stroke-linecap="round"'
    sf = f'fill="{bg}" stroke="{ink}" stroke-width="{f2(ISW)}" stroke-linejoin="round"'
    o = []

    def P_(pts, closed=False, style=st):
        d = 'M' + ' L'.join(f'{f2(a)},{f2(b)}' for a, b in pts) + (' Z' if closed else '')
        o.append(f'<path d="{d}" {style}/>')

    def page(x0, y0, pw, ph, c, rows=(0.8, 1.0, 1.0, 0.55)):
        P_([(x0, y0), (x0 + pw - c, y0), (x0 + pw, y0 + c), (x0 + pw, y0 + ph), (x0, y0 + ph)], True, sf)
        P_([(x0 + pw - c, y0), (x0 + pw - c, y0 + c), (x0 + pw, y0 + c)])
        for k, f in enumerate(rows):
            yy = y0 + ph * (0.36 + 0.16 * k)
            P_([(x0 + 0.2 * pw, yy), (x0 + (0.2 + 0.6 * f) * pw, yy)])

    hx = s / 2
    if kind == 'page':                     # the paper's text
        pw, ph = 0.72 * s, 0.94 * s
        page(cx - pw / 2, cy - ph / 2, pw, ph, 0.22 * s)
    elif kind == 'image':                  # a rendered page: a picture on the page
        pw, ph, c = 0.72 * s, 0.94 * s, 0.22 * s
        x0, y0 = cx - pw / 2, cy - ph / 2
        P_([(x0, y0), (x0 + pw - c, y0), (x0 + pw, y0 + c), (x0 + pw, y0 + ph), (x0, y0 + ph)], True, sf)
        P_([(x0 + pw - c, y0), (x0 + pw - c, y0 + c), (x0 + pw, y0 + c)])
        fx0, fy0, fx1, fy1 = x0 + 0.16 * pw, y0 + 0.38 * ph, x0 + 0.84 * pw, y0 + 0.84 * ph
        P_([(fx0, fy0), (fx1, fy0), (fx1, fy1), (fx0, fy1)], True)
        P_([(fx0, fy1), (fx0 + 0.36 * (fx1 - fx0), fy0 + 0.42 * (fy1 - fy0)), (fx0 + 0.6 * (fx1 - fx0), fy0 + 0.72 * (fy1 - fy0)),
            (fx0 + 0.78 * (fx1 - fx0), fy0 + 0.52 * (fy1 - fy0)), (fx1, fy1)])
    elif kind in ('read', 'verify'):       # a page and a lens (read); a page and a tick (verify)
        pw, ph = 0.62 * s, 0.84 * s
        x0, y0 = cx - 0.48 * s, cy - 0.46 * s
        page(x0, y0, pw, ph, 0.2 * s, (0.8, 1.0, 0.6))
        bx_, by_, r = cx + 0.2 * s, cy + 0.17 * s, 0.21 * s
        o.append(f'<circle cx="{f2(bx_)}" cy="{f2(by_)}" r="{f2(r)}" {sf}/>')
        if kind == 'read':
            P_([(bx_ + 0.71 * r, by_ + 0.71 * r), (cx + 0.5 * s, cy + 0.47 * s)])
        else:
            P_([(bx_ - 0.5 * r, by_ + 0.02 * s), (bx_ - 0.12 * r, by_ + 0.42 * r), (bx_ + 0.55 * r, by_ - 0.4 * r)])
        hx = 0.52 * s
    elif kind == 'code':                   # </>
        a, b, q = 0.25 * s, 0.30 * s, 0.2125 * s   # P1 check: 1.25 times (0.925 x 0.8 of s), as large as its neighbours
        P_([(cx - q, cy - b), (cx - q - a, cy), (cx - q, cy + b)])
        P_([(cx + q, cy - b), (cx + q + a, cy), (cx + q, cy + b)])
        P_([(cx + 0.0875 * s, cy - 0.40 * s), (cx - 0.0875 * s, cy + 0.40 * s)])
    elif kind == 'checks':                 # a checklist
        bw, bh = 0.76 * s, 0.9 * s
        x0, y0 = cx - bw / 2, cy - bh / 2
        o.append(f'<rect x="{f2(x0)}" y="{f2(y0)}" width="{f2(bw)}" height="{f2(bh)}" rx="{f2(0.07 * s)}" {sf}/>')
        for k in range(3):
            yy = y0 + bh * (0.27 + 0.24 * k)
            P_([(x0 + 0.15 * bw, yy), (x0 + 0.23 * bw, yy + 0.06 * s), (x0 + 0.37 * bw, yy - 0.07 * s)])
            P_([(x0 + 0.5 * bw, yy), (x0 + 0.84 * bw, yy)])
    elif kind == 'table':                  # the catalogue: a table
        bw, bh = 0.86 * s, 0.7 * s
        x0, y0 = cx - bw / 2, cy - bh / 2
        P_([(x0, y0), (x0 + bw, y0), (x0 + bw, y0 + bh), (x0, y0 + bh)], True, sf)
        for f in (0.3, 0.55, 0.78):
            P_([(x0, y0 + f * bh), (x0 + bw, y0 + f * bh)])
        for f in (0.34, 0.67):
            P_([(x0 + f * bw, y0), (x0 + f * bw, y0 + bh)])
    elif kind == 'scales':                 # a balance: decided from the paper
        beam, bot = cy - 0.27 * s, cy + 0.42 * s
        P_([(cx, cy - 0.4 * s), (cx, bot)])
        P_([(cx - 0.2 * s, bot), (cx + 0.2 * s, bot)])
        P_([(cx - 0.44 * s, beam), (cx + 0.44 * s, beam)])
        for sx in (-1, 1):
            ax_ = cx + sx * 0.44 * s
            py = cy + 0.06 * s
            P_([(ax_ - 0.15 * s, py), (ax_, beam), (ax_ + 0.15 * s, py)])
            o.append(f'<path d="M{f2(ax_ - 0.18 * s)},{f2(py)} Q{f2(ax_)},{f2(py + 0.24 * s)} {f2(ax_ + 0.18 * s)},{f2(py)} Z" {sf}/>')
        hx = 0.63 * s
    elif kind == 'person':                 # head and shoulders
        o.append(f'<circle cx="{f2(cx)}" cy="{f2(cy - 0.21 * s)}" r="{f2(0.19 * s)}" {sf}/>')
        o.append(f'<path d="M{f2(cx - 0.37 * s)},{f2(cy + 0.43 * s)} A{f2(0.37 * s)},{f2(0.37 * s)} 0 0 1 '
                 f'{f2(cx + 0.37 * s)},{f2(cy + 0.43 * s)} Z" {sf}/>')
    elif kind == 'agent':                  # W1: an agent: a plain robot head (a rounded square, two dots for eyes, a short antenna)
        hw_, top_, bot_ = 0.36 * s, cy - 0.23 * s, cy + 0.43 * s
        o.append(f'<rect x="{f2(cx - hw_)}" y="{f2(top_)}" width="{f2(2 * hw_)}" height="{f2(bot_ - top_)}" rx="{f2(0.15 * s)}" {sf}/>')
        for sx in (-1, 1):
            o.append(f'<circle cx="{f2(cx + sx * 0.155 * s)}" cy="{f2(cy + 0.07 * s)}" r="{f2(0.062 * s)}" fill="{ink}"/>')
        P_([(cx, top_), (cx, cy - 0.33 * s)])
        o.append(f'<circle cx="{f2(cx)}" cy="{f2(cy - 0.35 * s)}" r="{f2(0.05 * s)}" fill="{ink}"/>')
        hx = hw_ + 0.3
    elif kind == 'book':                   # an open book with ruled pages: the error rules
        y0, y1 = cy - 0.34 * s, cy + 0.36 * s
        for d_ in (-1, 1):
            o.append(f'<path d="M{f2(cx)},{f2(y0 + 0.05 * s)} Q{f2(cx + d_ * 0.24 * s)},{f2(y0 - 0.06 * s)} '
                     f'{f2(cx + d_ * 0.48 * s)},{f2(y0)} L{f2(cx + d_ * 0.48 * s)},{f2(y1)} '
                     f'Q{f2(cx + d_ * 0.24 * s)},{f2(y1 - 0.08 * s)} {f2(cx)},{f2(y1)} Z" {sf}/>')
            for j in range(3):
                yy = y0 + 0.2 * s + 0.15 * s * j
                P_([(cx + d_ * 0.1 * s, yy), (cx + d_ * 0.38 * s, yy)])
    elif kind == 'flag':
        px = cx - 0.28 * s
        P_([(px, cy + 0.46 * s), (px, cy - 0.46 * s)])
        sp_ = (f'fill="{accent}" stroke="{accent}" stroke-width="{f2(ISW)}" stroke-linejoin="round"' if accent else sf)
        P_([(px, cy - 0.42 * s), (cx + 0.38 * s, cy - 0.25 * s), (px, cy - 0.06 * s)], True, sp_)
    elif kind in ('chain', 'mutant'):      # W3: a chain of residues, a protein; one residue filled: a mutant
        pts = [(cx + f * s, cy + (0.13 if k % 2 else -0.13) * s) for k, f in enumerate((-0.4, -0.13, 0.13, 0.4))]
        P_(pts)
        for k, (px_, py_) in enumerate(pts):
            fc = INK if kind == 'mutant' and k == 2 else '#FFFFFF'
            o.append(f'<circle cx="{f2(px_)}" cy="{f2(py_)}" r="{f2(0.1 * s)}" fill="{fc}" stroke="{INK}" '
                     f'stroke-width="{f2(ISW)}"/>')
    elif kind == 'molecule':               # W3: a compound as a skeletal formula
        # checker: no ring (the hexagon stood beside 'L-asparagine', which has none, under its own drawn structure): a
        # 120-degree zig-zag of three bonds, a C=O up from its second atom (two lines) and a branch down from its third
        b_ = 0.29 * s
        dx_, dy_ = 0.866 * b_, 0.5 * b_
        zz = [(cx + (k - 1.5) * dx_, cy + (dy_ if k % 2 == 0 else -dy_) / 2) for k in range(4)]
        P_(zz)
        P_([zz[1], (zz[1][0], zz[1][1] - b_)])
        P_([(zz[1][0] + 0.1 * s, zz[1][1] - 0.06 * s), (zz[1][0] + 0.1 * s, zz[1][1] - b_)])
        P_([zz[2], (zz[2][0], zz[2][1] + b_)])
    elif kind == 'tables':                 # U1: three tables stacked, the databases (a table each; no cylinder)
        tw, th, d_ = 0.72 * s, 0.56 * s, 0.14 * s
        x0, y0 = cx - (tw + 2 * d_) / 2, cy - (th + 2 * d_) / 2 + 2 * d_     # the front table's top left
        for j in (2, 1):                   # the two behind it, up and to the right
            P_([(x0 + j * d_, y0 - j * d_), (x0 + j * d_ + tw, y0 - j * d_), (x0 + j * d_ + tw, y0 - j * d_ + th),
                (x0 + j * d_, y0 - j * d_ + th)], True, sf)
        P_([(x0, y0), (x0 + tw, y0), (x0 + tw, y0 + th), (x0, y0 + th)], True, sf)
        for f_ in (0.34, 0.67):
            P_([(x0, y0 + f_ * th), (x0 + tw, y0 + f_ * th)])
        P_([(x0 + 0.38 * tw, y0), (x0 + 0.38 * tw, y0 + th)])
    elif kind == 'db':                     # U1 round 2 (the editor: the stacked tables read as spreadsheets): a database,
        #                                    the usual cylinder of three discs, white, in a's line weight
        rx, ry = 0.36 * s, 0.12 * s
        yt, yb = cy - 0.36 * s, cy + 0.32 * s      # the top ellipse's centre; the bottom arc's ends
        o.append(f'<path d="M{f2(cx - rx)},{f2(yt)} L{f2(cx - rx)},{f2(yb)} A{f2(rx)},{f2(ry)} 0 0 0 {f2(cx + rx)},'
                 f'{f2(yb)} L{f2(cx + rx)},{f2(yt)} Z" {sf}/>')
        for f_ in (1 / 3, 2 / 3):          # the discs' seams
            yy = yt + f_ * (yb - yt)
            o.append(f'<path d="M{f2(cx - rx)},{f2(yy)} A{f2(rx)},{f2(ry)} 0 0 0 {f2(cx + rx)},{f2(yy)}" {st}/>')
        o.append(f'<ellipse cx="{f2(cx)}" cy="{f2(yt)}" rx="{f2(rx)}" ry="{f2(ry)}" {sf}/>')
        hx = rx + 0.4
    elif kind == 'search':                 # U1: a lens alone (d's lens, in ink): a search of the literature
        r = 0.27 * s
        lx, ly = cx - 0.1 * s, cy - 0.1 * s
        o.append(f'<circle cx="{f2(lx)}" cy="{f2(ly)}" r="{f2(r)}" {sf}/>')
        hx_, hy_ = lx + 0.71 * r, ly + 0.71 * r
        o.append(f'<path d="M{f2(hx_)},{f2(hy_)} L{f2(hx_ + 0.25 * s)},{f2(hy_ + 0.25 * s)}" fill="none" stroke="{ink}" '
                 f'stroke-width="1" stroke-linecap="round"/>')
    elif kind == 'locked':                 # U1: d's test paper (a page and a padlock) without d's red lens; s 10.4 is
        k_ = s / 10.4                      # d's page, 8.0 x 10.4 pt with a 2.2-pt corner
        pw0, ph0, cc0 = 8.0 * k_, 10.4 * k_, 2.2 * k_
        px0, py0 = cx - pw0 / 2, cy - ph0 / 2
        P_([(px0, py0), (px0 + pw0 - cc0, py0), (px0 + pw0, py0 + cc0), (px0 + pw0, py0 + ph0), (px0, py0 + ph0)], True, sf)
        P_([(px0 + pw0 - cc0, py0), (px0 + pw0 - cc0, py0 + cc0), (px0 + pw0, py0 + cc0)])
        lkx, lky, lr = px0 + 3.8 * k_, py0 + 6.3 * k_, 1.15 * k_      # the padlock, centred on the page below its corner
        o += [f'<path d="M{f2(lkx - lr)},{f2(lky - 0.9 * k_)} L{f2(lkx - lr)},{f2(lky - 2.0 * k_)} A{f2(lr)},{f2(lr)} 0 0 1 '
              f'{f2(lkx + lr)},{f2(lky - 2.0 * k_)} L{f2(lkx + lr)},{f2(lky - 0.9 * k_)}" fill="none" stroke="{ink}" '
              f'stroke-width="{f2(SWB)}"/>',
              f'<rect x="{f2(lkx - 1.9 * k_)}" y="{f2(lky - 0.9 * k_)}" width="{f2(3.8 * k_)}" height="{f2(3.0 * k_)}" '
              f'rx="{f2(0.4 * k_)}" fill="{ink}"/>']
        hx = pw0 / 2 + 0.3
    else:
        raise ValueError(kind)
    cv.box(cx - hx, cy - s / 2, cx + hx, cy + s / 2, what, 'mark')
    return '<g>' + ''.join(o) + '</g>'


GW = {'person': 0.74, 'agent': 0.72, 'code': 0.74}   # W1: a glyph's ink width, in the picture's size s
GSIDE = 0.32                               # the white between two glyphs side by side, in s


def glyph(kind, cx, cy, s, what):
    """W1: one of the three who act, as a glyph of size s: a person (tan, people's fill, as the reviewer in a's Flag), an
    agent (the robot head: mint, in the agents' outline colour) or code (the sign of a's Convert box, 0.8 as large, so
    it is as wide as the other two)."""
    if kind == 'person':
        return ico('person', cx, cy, s, what, bg=FILL['people'])
    if kind == 'agent':
        return ico('agent', cx, cy, s, what, ink=EDGEC['agent'], bg=FILL['agent'])
    assert kind == 'code', kind
    return ico('code', cx, cy, 0.8 * s, what)


def actors(seq, x, cy, s, what):
    """W1: a small picture of who acts: glyphs in a row from x (the first glyph's ink edge), middle line cy. seq holds
    glyph kinds and, between them, how they stand: None side by side, 'plus' joined by a plus sign, 'both' with a
    two-way arrow between them (ink, the arrows' 0.75 pt; its heads small, as the fold icon's in a's Flag). Returns the
    items and the picture's right edge."""
    it, xx = [], x
    st_ = f'fill="none" stroke="{INK}" stroke-width="{f2(SHAFT)}"'
    ym = cy + 0.015 * s                    # the glyphs' ink is centred 0.015 s under cy
    for e in seq:
        if e in GW:
            it.append(glyph(e, xx + GW[e] * s / 2, cy, s, f'{what} {e}'))
            xx += GW[e] * s
        elif e is None:
            xx += GSIDE * s
        elif e == 'plus':
            a_ = 0.2 * s
            c_ = xx + 0.3 * s + a_
            it.append(f'<path d="M{f2(c_ - a_)},{f2(ym)} L{f2(c_ + a_)},{f2(ym)} M{f2(c_)},{f2(ym - a_)} L{f2(c_)},{f2(ym + a_)}" {st_}/>')
            cv.box(c_ - a_, ym - a_, c_ + a_, ym + a_, f'{what} plus', 'mark')
            xx = c_ + a_ + 0.3 * s
        else:
            assert e == 'both', e
            hl_, hw_ = 0.24 * s, 0.26 * s
            x0_, x1_ = xx + 0.26 * s, xx + 1.26 * s
            it.append(f'<path d="M{f2(x0_ + hl_)},{f2(ym)} L{f2(x1_ - hl_)},{f2(ym)}" {st_}/>')
            for xt_, d_ in ((x0_, 1), (x1_, -1)):
                it.append(f'<path d="M{f2(xt_)},{f2(ym)} L{f2(xt_ + d_ * hl_)},{f2(ym - hw_ / 2)} L{f2(xt_ + d_ * hl_)},'
                          f'{f2(ym + hw_ / 2)} Z" fill="{INK}"/>')
            cv.box(x0_, ym - hw_ / 2, x1_, ym + hw_ / 2, f'{what} both ways', 'mark')
            xx = x1_ + 0.26 * s
    return it, xx


SIW, SIH = 10.0, 7.6                       # S1r: a Flag source's icon, 10 x 7.6 pt (S1: 9 x 7)


def src_icon(kind, cx, cy, what, bg=RED_TINT):
    """S1 (fix 8), S1r: a small line icon for one source of a flag, SIW x SIH centred at (cx, cy), in one style: ink
    strokes, closed parts filled with the box's tint, red only on what is suspect (the editor: the S1 icons mixed two or
    three colours each). person: a reviewer (tan, people's fill); ratio: a rate curve rising to its plateau and a red
    straight line from the origin whose slope (a printed kcat/Km) misses the curve's start; reprint: two pages printing the
    same row (red); die: a die with three pips (a random draw); fold: two values as ticks on a log axis, a red double
    arrow for the fold between them."""
    w2, h2 = SIW / 2, SIH / 2
    x0, x1, y0, y1 = cx - w2, cx + w2, cy - h2, cy + h2
    sw = ISW
    col = INK
    st = lambda c, w=sw: f'fill="none" stroke="{c}" stroke-width="{f2(w)}" stroke-linejoin="round" stroke-linecap="round"'
    o = []

    def P_(pts, style, closed=False):
        o.append('<path d="M' + ' L'.join(f'{f2(a)},{f2(b)}' for a, b in pts) + (' Z' if closed else '') + f'" {style}/>')

    if kind == 'person':                   # a's person, smaller, in people's tan
        s = SIH
        o.append(f'<circle cx="{f2(cx)}" cy="{f2(cy - 0.21 * s)}" r="{f2(0.19 * s)}" fill="{FILL["people"]}" '
                 f'stroke="{col}" stroke-width="{f2(sw)}"/>')
        o.append(f'<path d="M{f2(cx - 0.37 * s)},{f2(cy + 0.43 * s)} A{f2(0.37 * s)},{f2(0.37 * s)} 0 0 1 '
                 f'{f2(cx + 0.37 * s)},{f2(cy + 0.43 * s)} Z" fill="{FILL["people"]}" stroke="{col}" '
                 f'stroke-width="{f2(sw)}" stroke-linejoin="round"/>')
    elif kind == 'ratio':                  # v = kcat S / (Km + S); a printed kcat/Km as a line through the origin
        ox, oy, top = x0 + 0.5, y1 - 0.3, y0 + 1.0
        K = 0.16
        pts = [(ox + (x1 - 0.3 - ox) * t, oy - (oy - top) * t / (K + t)) for t in [i / 24 for i in range(25)]]
        P_([(ox, top - 0.7), (ox, oy), (x1 - 0.2, oy)], st(col, HAIR))                    # the axes
        P_(pts, st(col))
        P_([(ox, oy), (x1 - 1.2, oy - 0.6 * (oy - top))], st(RED, SHAFT))                  # the printed kcat/Km
    elif kind == 'reprint':                # two papers (pages with a folded corner, apart), the same row red in each
        pw, ph, c_ = 4.0, SIH - 0.4, 1.2
        for px_ in (x0 + 0.4, x1 - 0.4 - pw):
            py_ = y0 + 0.2
            P_([(px_, py_), (px_ + pw - c_, py_), (px_ + pw, py_ + c_), (px_ + pw, py_ + ph), (px_, py_ + ph)],
               f'fill="{bg}" stroke="{col}" stroke-width="{f2(sw)}" stroke-linejoin="round"', True)
            for j, f_ in enumerate((0.42, 0.62, 0.82)):
                yy = py_ + ph * f_
                P_([(px_ + 0.75, yy), (px_ + pw - 0.75, yy)], st(RED if j == 1 else col, SHAFT if j == 1 else HAIR))
    elif kind == 'die':                    # a die: a random draw
        d = SIH - 0.6
        o.append(f'<rect x="{f2(cx - d / 2)}" y="{f2(cy - d / 2)}" width="{f2(d)}" height="{f2(d)}" rx="1.1" '
                 f'fill="{bg}" stroke="{col}" stroke-width="{f2(sw)}"/>')
        for f_ in (-0.26, 0.0, 0.26):
            o.append(f'<circle cx="{f2(cx + f_ * d)}" cy="{f2(cy + f_ * d)}" r="0.66" fill="{col}"/>')
    elif kind == 'fold':                   # two values on a log axis, the fold between them
        ya = y1 - 0.5
        P_([(x0 + 0.3, ya), (x1 - 0.3, ya)], st(col, HAIR))
        xa_, xb_ = cx - 3.1, cx + 3.1
        for xx in (xa_, xb_):
            P_([(xx, ya), (xx, ya - 3.2)], st(col))
        yr, hl_, hw_ = ya - 5.0, 1.3, 1.6
        P_([(xa_ + hl_, yr), (xb_ - hl_, yr)], st(RED, SWB))
        for xt, d_ in ((xa_, 1), (xb_, -1)):
            o.append(f'<path d="M{f2(xt)},{f2(yr)} L{f2(xt + d_ * hl_)},{f2(yr - hw_ / 2)} L{f2(xt + d_ * hl_)},'
                     f'{f2(yr + hw_ / 2)} Z" fill="{RED}"/>')
    else:
        raise ValueError(kind)
    cv.box(x0, y0, x1, y1, what, 'mark')
    return '<g>' + ''.join(o) + '</g>'


def stack(cx, y0, what, n=3, pw=17.0, ph=22.0, dx=2.6, dy=2.6):
    """A stack of n pages in outline (one stroke weight), the front page with text lines; top-left page at y0."""
    o = []
    st = f'fill="none" stroke="{INK}" stroke-width="{f2(ISW)}" stroke-linecap="round"'
    for k in range(n - 1, -1, -1):
        x0, yy = cx - pw / 2 + k * dx - (n - 1) * dx / 2, y0 + (n - 1 - k) * dy
        o.append(f'<rect x="{f2(x0)}" y="{f2(yy)}" width="{f2(pw)}" height="{f2(ph)}" fill="#FFFFFF" stroke="{INK}" '
                 f'stroke-width="{f2(ISW)}"/>')
    x0, yy = cx - pw / 2 - (n - 1) * dx / 2, y0 + (n - 1) * dy
    for j, f in enumerate((0.75, 1.0, 1.0, 0.6)):
        ly = yy + ph * (0.24 + 0.17 * j)
        o.append(f'<path d="M{f2(x0 + 0.18 * pw)},{f2(ly)} L{f2(x0 + (0.18 + 0.64 * f) * pw)},{f2(ly)}" {st}/>')
    cv.box(cx - pw / 2 - (n - 1) * dx / 2, y0, cx + pw / 2 + (n - 1) * dx / 2, y0 + ph + (n - 1) * dy, what, 'mark')
    return '<g>' + ''.join(o) + '</g>'


FOOTH = 12.0                               # W1: a step box's foot: the count of rules under a hairline
FOOTI = 6.0                                # the hairline's inset from the box's sides


def big(gid, x, y, w, h, role, kind, title, lines, tfill=TXT, fill=None, edge=None, size=T6, ls=7.0, isz=14.0,
        ink=INK, bg='#FFFFFF', sw=SWB, rows=0, foot=None, footh=0.0):
    """A step box of a, as v7: filled in the colour of who acts; one icon, the step in bold, a short label. S1r: ink and
    bg colour the icon (white lines on the catalogue's green). W1: footh, the height of a foot at the box's lower edge
    (icon, name and lines are centred in the box over it); foot, the foot's one line (rich parts), its capitals centred
    in the foot under a hairline in the box's outline colour. footh without foot keeps the foot's room white (Decide),
    so every name of the row stands on one line."""
    f_ = fill or FILL[role]
    e_ = edge or EDGEC[role]
    cv.holder(gid, x, y, w, h, 2.0)
    nl_ = max(len(lines), rows)            # P1: rows, the lines the block is centred for (Decide: one line, set as the steps' two)
    block = isz + 5.2 + 0.72 * TT + ((3.8 + 0.72 * size + ls * (nl_ - 1)) if nl_ else 0.0)
    top = y + (h - footh - block) / 2
    it = [cv.rect(x, y, w, h, f_, e_, sw, RX), ico(kind, x + w / 2, top + isz / 2, isz, f'{gid} icon', ink=ink, bg=bg)]
    yy = top + isz + 5.2 + 0.72 * TT
    it.append(cv.text(x + w / 2, yy, title, TT, 'middle', 'bold', fill=tfill, inside=gid))
    yy += 3.8 + 0.72 * size
    for ln in lines:
        it.append(cv.text(x + w / 2, yy, ln, size, 'middle', inside=gid))
        yy += ls
    if foot:
        yf = y + h - footh
        assert yy - ls + 0.21 * size + 4.0 <= yf, (gid, 'the foot stands clear of the lines over it')
        it.append(cv.line(x + FOOTI, yf, x + w - FOOTI, yf, e_, HAIR))
        it.append(cv.rich(x + w / 2, yf + (footh + 0.716 * size) / 2, foot, size, 'middle', inside=gid, what=f'{gid} rules'))
    return it


PT, PB = 6.9, 2.8                          # V1: a plate reaches 6.9 pt above its baseline (a 5.5-pt superscript) and 2.8 below


def plate(gid, x, y, s, size=T55, inside=None, w_min=0.0, top=None, bot=None):
    """Print on a grey plate, text baseline y; returns (items, right edge)."""
    parts = rk(s)
    w_ = max(cv.rwidth(parts, size), w_min)
    tw = cv.rwidth(parts, size)
    top, bot = PT if top is None else top, PB if bot is None else bot
    it = [cv.rect(x, y - top, w_ + 3.0, top + bot, PLATE, None, rx=PRX),
          cv.rich(x + 1.5 + (w_ - tw) / 2, y, parts, size, inside=inside, what=f'{gid} print {s}')]
    return it, x + w_ + 3.0


# ================================================================== V1 "tight grid" (6 Nov): one column grid
# b's four cards (6 pt in from the art, 10-pt gutters, where they were) set the grid; c's and d's boxes stand on its
# columns and half-columns, a's steps, catalogue and top row on its half-columns; the gaps between panels, the zoom from
# a into b and the padding inside b's cards and c's boxes are cut; text 6.5 pt, titles 7 pt
G = 10.0                                   # one gutter everywhere
GX0, GX1 = 6.0, W - 6.0                    # the grid's outer edges: b's cards, c's and d's boxes, Decide's right edge
C16 = (GX1 - GX0 - 15 * G) / 16            # a half-column: b's card is four of them, a's step two


def gl(k):
    return GX0 + k * (C16 + G)


def gr(k):
    return gl(k) + C16


DASH, DGAP = 2.0, 1.5                      # the frames' dashes: 2 pt on, about 1.5 pt off


def dashed(x0, y0, x1, y1):
    """A dashed line of the frames' make that starts and ends with a whole dash: drawn from each end to its middle,
    the gap tuned (within 0.1 pt of 1.5) so that the two halves meet in the middle of a gap. R5 checker: a dashed
    rectangle starts its dashes at one corner and lets the others fall where they fall; three corners of the 'After
    reading' frame fell in a gap."""
    half = math.hypot(x1 - x0, y1 - y0) / 2
    n = round((half - DASH - DGAP / 2) / (DASH + DGAP))
    gap = (half - (n + 1) * DASH) / (n + 0.5)
    assert n >= 1 and abs(gap - DGAP) <= 0.1, (half, n, gap)
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    return (f'<path d="M{f2(x0)},{f2(y0)} L{f2(xm)},{f2(ym)} M{f2(x1)},{f2(y1)} L{f2(xm)},{f2(ym)}" fill="none" '
            f'stroke="{GREY}" stroke-width="{f2(SWB)}" stroke-dasharray="{f2(DASH)} {gap:.3f}"/>')


def dframe(x, y, w, h):
    """A dashed frame with closed corners: four dashed() sides, each half a line's weight longer at both ends, so the
    two whole dashes that meet at a corner make it square."""
    e = SWB / 2
    return [dashed(x - e, y, x + w + e, y), dashed(x + w, y - e, x + w, y + h + e),
            dashed(x - e, y + h, x + w + e, y + h), dashed(x, y - e, x, y + h + e)]


# ================================================================== a: the CatLog workflow
g('panel letter a', cv.panel_letter(GX0, 8.0, 'a', 'CatLog workflow'))   # V1: every letter on the grid's left edge
PY0, PH = 8.0 + TGAP, 36.0                       # the top row: people and co-learning (4.5 pt under the title, as c and d)
YT = PY0 + PH + 12.0                       # the reading frame and the after-reading band
BY0, BH = YT + 10.0, 71.0                  # W1: 7 pt taller, for the steps' feet (8 would put the frame's sides
#                                            0.1 pt off the dashes' gap)
#                 # the step boxes (S1: 5 pt taller, for the Flag's five icon rows; S1r: 2
#                                            more, for its larger icons)
YM = BY0 + BH / 2                          # the pipeline's arrows
YCH = BY0 + BH + 6.7                       # the inputs' line to Verify (its last leg holds a head). FINAL PASS (ARROWS item 5,
#                                            the editor: its head sat on a 0.5-mm stub after the elbow; the cold reader took
#                                            the run for part of the frame): 1.7 pt (0.6 mm) lower
YCH_A = YCH                                # (b names its own YCH: the checks use this one)
YB = YCH + 5.7                             # FINAL PASS: the frame's foot 2.9 pt (1 mm) lower, 5.7 pt under the run (4.5): with
#                                            1.7 pt the sides' dashes would leave their gap (1.63 pt), and the run stands further
#                                            from the frame it was taken for
BW = 2 * C16 + G                           # a step: two half-columns, as wide as c's Reading and CatLog boxes
bx = [gl(1 + 2 * i) for i in range(4)]     # Read, Convert, Verify, Check
FX0, FX1 = bx[0] - 5.0, bx[3] + BW + 5.0
XPA = bx[0] + BW + G / 2                   # the gutter between Read and Convert: people's reviewed papers come in
XRU = bx[2] + BW + G / 2                   # the gutter between Verify and Check: the rules come in

# ---- inputs: the paper's text and its page images (their two lines, which cross the frame's left side)
IX, ISI = 15.0, 12.0
YI1, YI2 = BY0 + 12.5, BY0 + 42.5          # W1: 3.5 pt lower, centred in the taller row
#          # S1: 2.5 pt lower, centred in the taller row

# ---- the reading frame: blind to what the databases and the reviewers hold
# FINAL PASS (ARROWS_20261111.md item 6, the editor): where an arrow crosses the dashed frame, the frame opens a 1-mm gap
# (a dash had sat across two of the four shafts), and a whole dash stands under the rules head (its tip had landed on
# the end of a dash, half over a gap). Each side keeps the dashes it had (2 pt on, the gap tuned near 1.5 pt, a whole
# dash at each corner, as dashed() lays them); a 1-mm opening is cut round each crossing, and a dash fragment under
# 0.8 pt left beside an opening is dropped with it. The top side is laid as two runs that meet in a whole dash centred on
# the rules head. Each side is one path of its dashes drawn as short lines (no dash pattern), so the openings stay
# where they are in any program
GAPC = MM                                  # the opening round a crossing: 1 mm
FRAG = 0.8                                 # a dash fragment shorter than this beside an opening goes with it (it would read as a dot)


def dash_runs(a, b, n_gaps_extra=0):
    """Dashes (2 pt) laid from a to b with a gap tuned as near 1.5 pt as the length allows; whole dashes at both ends
    (n_gaps_extra=1: a gap first, a whole dash at b). Returns the intervals and the gap."""
    L_, best_ = b - a, None
    for k_ in range(1, int(L_ / DASH) + 1):
        ng_ = k_ - 1 + n_gaps_extra
        if ng_ <= 0:
            continue
        gp_ = (L_ - DASH * k_) / ng_
        if gp_ > 0 and (best_ is None or abs(gp_ - DGAP) < abs(best_[1] - DGAP)):
            best_ = (k_, gp_)
    k_, gp_ = best_
    x_ = a + (gp_ if n_gaps_extra else 0.0)
    return [(x_ + i_ * (DASH + gp_), x_ + i_ * (DASH + gp_) + DASH) for i_ in range(k_)], gp_


def dash_side(x0, y0, x1, y1, cuts=(), anchor=None):
    """One side of the dashed frame, axis-aligned, from (x0, y0) to (x1, y1): dashed()'s dashes (from each end to the
    middle), or two runs meeting in a whole dash centred on anchor; then a GAPC opening centred on each crossing in
    cuts (positions along the side). Returns (the path, the dash intervals along the side, the gaps tuned)."""
    hor_ = abs(y1 - y0) < 1e-9
    a_, b_ = (x0, x1) if hor_ else (y0, y1)
    if anchor is None:
        half_ = (b_ - a_) / 2
        n_ = round((half_ - DASH - DGAP / 2) / (DASH + DGAP))
        gp_ = (half_ - (n_ + 1) * DASH) / (n_ + 0.5)
        iv_ = [(a_ + i_ * (DASH + gp_), a_ + i_ * (DASH + gp_) + DASH) for i_ in range(n_ + 1)]
        iv_ += [(b_ - i_ * (DASH + gp_) - DASH, b_ - i_ * (DASH + gp_)) for i_ in range(n_ + 1)]
        gaps_ = [gp_]
    else:
        r1_, g1_ = dash_runs(a_, anchor + DASH / 2)
        r2_, g2_ = dash_runs(anchor + DASH / 2, b_, n_gaps_extra=1)
        iv_, gaps_ = r1_ + r2_, [g1_, g2_]
    assert all(abs(gp_ - DGAP) <= 0.1 for gp_ in gaps_), ('the dashes keep their gap', gaps_)
    iv_ = sorted(iv_)
    for c_ in cuts:
        lo_, hi_ = c_ - GAPC / 2, c_ + GAPC / 2
        nv_ = []
        for p_, q_ in iv_:
            for s_, e_ in ((p_, min(q_, lo_)), (max(p_, hi_), q_)):
                if e_ - s_ >= FRAG - 1e-9 and (e_ <= lo_ + 1e-9 or s_ >= hi_ - 1e-9):
                    nv_.append((s_, e_))
        iv_ = sorted(set(nv_))
    d_ = ' '.join((f'M{f2(p_)},{f2(y0)} L{f2(q_)},{f2(y0)}' if hor_ else f'M{f2(x0)},{f2(p_)} L{f2(x0)},{f2(q_)}')
                  for p_, q_ in iv_)
    return f'<path d="{d_}" fill="none" stroke="{GREY}" stroke-width="{f2(SWB)}"/>', iv_, gaps_


lab = 'Blind to databases and reviews'
XFL = (XPA + XRU) / 2
_e = SWB / 2                               # each side half a line's weight longer at both ends: square corners (dframe)
FR_SIDES = {'top': dash_side(FX0 - _e, YT, FX1 + _e, YT, anchor=XRU),
            'right': dash_side(FX1, YT - _e, FX1, YB + _e, cuts=(YM,)),
            'bottom': dash_side(FX0 - _e, YB, FX1 + _e, YB),
            'left': dash_side(FX0, YT - _e, FX0, YB + _e, cuts=(YI1, YI2, YCH))}
g('a reading frame', [s_[0] for s_ in FR_SIDES.values()] + [cv.text(XFL, YT + 6.6, lab, T55, 'middle')])
assert XPA + 4.0 < XFL - wid(lab, T55) / 2 and XFL + wid(lab, T55) / 2 < XRU - 4.0, 'the frame label clears both arrows'
g('a inputs', [ico('page', IX, YI1, ISI, 'a icon paper text'),
               cv.text(IX, YI1 + 12.6, 'Paper', T55, 'middle'), cv.text(IX, YI1 + 19.5, 'text', T55, 'middle'),
               ico('image', IX, YI2, ISI, 'a icon page images'),
               cv.text(IX, YI2 + 12.6, 'Page', T55, 'middle'), cv.text(IX, YI2 + 19.5, 'images', T55, 'middle')])

# ---- the four steps: the step in bold, who does it under it
ISZ = 16.0
# S1r (the editor: 'Convert / code converts' and 'Check / code checks' repeat their titles, and 'agent copies' can read as
# copies of an agent): one pattern, the step's verb in bold and only who does it under it
# P1 (11 Nov, the owner: "are we missing something? Fundamental inner architecture that shows the scientific
# contribution"): the method's core in the boxes themselves, two short lines each, as the earlier version had: the
# agent copies what is printed and never computes, code does the arithmetic, a second agent finds each value again in
# the paper, code checks
STEP_WHO = {'Read': 'agent', 'Convert': 'code', 'Verify': 'agent', 'Check': 'code'}   # who acts: the box's fill
STEP_LINES = {'Read': ['an agent copies', 'each printed cell'], 'Convert': ['code computes', 'every value'],
              'Verify': ['a second agent', 'finds it again'], 'Check': ['code checks', 'every value']}
assert all(len(l_) == 2 and max(wid(t_, T6) for t_ in l_) <= BW - 4.0 for l_ in STEP_LINES.values()), 'two lines, in the boxes as they are'
assert all((STEP_WHO[n_] in l_[0]) for n_, l_ in STEP_LINES.items()), 'each first line names who acts'
assert F['rules_n'] == {'Read': 16, 'Convert': 10, 'Verify': 7, 'Check': 35}, F['rules_n']   # W1: each step's count, the foot of its box
# FINAL PASS: the feet count Fig. 4a's 73 rules by step (facts: rules.csv): Convert's two written after the list of
# 2 November are in it (12), and Decide's foot holds the database check's 3, so the five feet add up to the 73 of the
# Co-learning box
assert F['rules_drawn'] == {'Read': 16, 'Convert': 12, 'Verify': 7, 'Check': 35, 'Decide': 3} and F['rules_all'] == 73, F['rules_drawn']
NRL = lambda n_: [(str(F['rules_drawn'][n_]), 'b'), (' rules', '')]   # '16 rules', the number bold
g('a read', big('a read', bx[0], BY0, BW, BH, 'agent', 'read', 'Read', STEP_LINES['Read'], isz=ISZ,
                  foot=NRL('Read'), footh=FOOTH))
g('a convert', big('a convert', bx[1], BY0, BW, BH, 'code', 'code', 'Convert', STEP_LINES['Convert'], isz=ISZ,
                  foot=NRL('Convert'), footh=FOOTH))
g('a verify', big('a verify', bx[2], BY0, BW, BH, 'agent', 'verify', 'Verify', STEP_LINES['Verify'], isz=ISZ,
                  foot=NRL('Verify'), footh=FOOTH))
g('a check', big('a check', bx[3], BY0, BW, BH, 'code', 'checks', 'Check', STEP_LINES['Check'], isz=ISZ,
                  foot=NRL('Check'), footh=FOOTH))
YNAME = BY0 + (BH - FOOTH - (ISZ + 5.2 + 0.72 * TT + 3.8 + 0.72 * T6 + 7.0)) / 2 + ISZ + 5.2 + 0.72 * TT   # the steps' names' line (W1: over the feet)
XBUS = 29.0                                # the inputs' line to Verify, between the input labels and the frame
assert IX + wid('images', T55) / 2 + 3.0 < XBUS < FX0 - 3.0
xv = bx[2] + BW / 2
arr = [cv.arrow([(IX + 6.0, YI1), (bx[0], YI1)], what='arrow paper text to read'),
       cv.arrow([(IX + 6.0, YI2), (bx[0], YI2)], what='arrow page images to read'),
       cv.arrow([(XBUS, YI1 - SHAFT / 2), (XBUS, YCH), (xv, YCH), (xv, BY0 + BH)], what='arrow inputs to verify')]
for i in range(3):
    arr.append(cv.arrow([(bx[i] + BW, YM), (bx[i + 1], YM)], what=f'arrow step {i}'))
# Q1: junction dots where the paper text and the page images join the line to Verify (it crossed the page images' arrow
# with no dot, which by convention means no connection, as if Verify got the text only; verify.md checks numbers, units
# and exponents on the page images)
arr += [f'<circle cx="{f2(XBUS)}" cy="{f2(yy_)}" r="1.1" fill="{INK}"/>' for yy_ in (YI1, YI2)]

# ---- the catalogue: a white box with the catalogue's green edge
CX0, CX1 = gl(9), gl(9) + 37.0            # S1: 8 pt narrower (its icon and name fit), room for the Flag's words; S1r: 2
#                                            more, so the Flag's words keep 5 pt of white on their right
ccx = (CX0 + CX1) / 2
def store(x0, x1, ytop, ybot, ry, fill, lid, edge, sw):
    """P1 (11 Nov, the owner: the stores "as in a database vibe", as the earlier version drew them): a store of values is
    a cylinder: straight sides, a full ellipse across the top as its lid, and the bottom edge the lower half of the same
    ellipse. ytop: the lid's highest point; ybot: the bottom's lowest; ry: half the lid's height. Returns the body and
    the lid; the sides run from the lid's middle (ytop + ry) to ybot - ry."""
    rx_, cx_ = (x1 - x0) / 2, (x0 + x1) / 2
    return [f'<path d="M{f2(x0)},{f2(ytop + ry)} L{f2(x0)},{f2(ybot - ry)} A{f2(rx_)},{f2(ry)} 0 0 0 {f2(x1)},'
            f'{f2(ybot - ry)} L{f2(x1)},{f2(ytop + ry)}" fill="{fill}" stroke="{edge}" stroke-width="{f2(sw)}"/>',
            f'<ellipse cx="{f2(cx_)}" cy="{f2(ytop + ry)}" rx="{f2(rx_)}" ry="{f2(ry)}" fill="{lid}" stroke="{edge}" '
            f'stroke-width="{f2(sw)}"/>']


# P1: CatLog where its box was, in the same footprint: the catalogue's tint, its green outline at the CatLog boxes' 1 pt,
# its name in the catalogue's green on the line of the steps' names (within 1.6 pt of the body's middle); no icon (the
# shape says store). The lid's top is the footprint's top, so the corrections arrow ends on it as it ended on the box;
# the arrows from Check and into Flag end on the straight sides
CRY = 4.4                                  # half the lid's height (the lid a quarter as tall as it is wide, as the earlier version's)
assert not CAT_SOLID
cv.holder('a catalog', CX0, BY0 + 2 * CRY, CX1 - CX0, BH - 3 * CRY, 2.0)
g('a catalog', store(CX0, CX1, BY0, BY0 + BH, CRY, CAT_TINT, CAT_TINT, GREEN, CAT_SW) +
  [cv.text(ccx, YNAME, 'CatLog', TT, 'middle', 'bold', fill=GREEN_TXT, inside='a catalog')])
assert BY0 + CRY + 4.0 <= YM <= BY0 + BH - CRY - 4.0, "the arrows from Check and into Flag end on the cylinder's straight sides"
# W1: the names' line stands over the steps' feet, so the name is in the body's upper half (7.5 pt over its middle; it
# was within 1.6 pt of it): on the steps' names' line, 19 pt or more under the lid and just over the arrows' line
assert BY0 + 2 * CRY + 19.0 <= YNAME - 0.716 * TT and abs(YNAME - YM) <= 1.0 and \
    abs((YNAME - 0.716 * TT / 2) - (BY0 + CRY + BH / 2)) <= 7.6, "CatLog's name on the names' line, in the body"
arr.append(cv.arrow([(bx[3] + BW, YM), (CX0, YM)], what='arrow check to catalog'))

# ---- after reading: a grey band with Flag and Decide; Decide ends on the grid's right edge, 6 pt of band each side
AX0 = CX1 + 5.0                            # R5: 5 pt, as the reading frame stands from the box's other side
assert abs((AX0 - CX1) - (CX0 - FX1)) < 1e-9 and abs(AX0 + 5.0 - CX1 - G) < 1e-9, 'the CatLog box midway between the two frames, one gutter from Flag'
FLX0 = AX0 + 5.0                           # S1r: 5 pt of band before the Flag (6 before), the label on its edge
DW = 47.0                                  # S1: 7 pt narrower ('from the paper' fits), room for the Flag
DX0 = GX1 - DW
FLW = DX0 - G - FLX0
ALAB = 'After reading'
XAL = FLX0                                 # R6: its words alone, on the Flag's left edge, where the band had them (the R5
#                                            frame stood 5 pt outside the grid's right edge; the dashed frame is the blind steps' alone)
g('a after label', [cv.text(XAL, YT + 6.6, ALAB, T55)])
cv.holder('a flag', FLX0, BY0, FLW, BH, 1.5)
# S1 (fix 8): each source a small line icon, red only on what is suspect; the pennant red (fix 1). One notation (fix 3):
# 'kcat, Km and kcat/Km disagree', no ÷ or ≠. S1r (the owner: "the flag cases can be the red kind of colorish"; the
# editor: "tint the Flag box"): the box is red, an outline and a light fill, as d's errors; its icons in one style (ink,
# the box's tint, red on the suspect part, a person tan); the audit with its rate
FIC = FLX0 + 9.0                           # the icons' centre line, the title's flag on it too
FTX = FLX0 + 16.5                          # the words' left edge (2.5 pt after the icons)
fl = [cv.rect(FLX0, BY0, FLW, BH, RED_TINT, RED, SWB, RX),
      ico('flag', FIC, BY0 + 9.9, 9.5, 'a flag icon', accent=RED, bg=RED_TINT),
      cv.text(FTX, BY0 + 12.5, 'Flag', TT, weight='bold', inside='a flag')]
ty = BY0 + 24.1
FPITCH = 10.0                              # W1: 10 pt in the taller box (P1 check: 9.0 in the box of 64 pt)
assert abs((BY0 + 24.1 + 4 * FPITCH) - (BY0 + BH - 6.9)) < 1e-9 and len(F['flag_items']) == 5
for role, kind, lab in F['flag_items']:
    fl.append(src_icon(kind, FIC, ty - 2.3, f'a flag icon {kind}'))
    fl.append(cv.rich(FTX, ty, kin(lab), T55, inside='a flag', what=f'a flag {kind}'))
    ty += FPITCH
assert ty - FPITCH + 0.21 * T55 <= BY0 + BH - 2.0, 'the last source stays in the box'
assert FTX + max(cv.rwidth(kin(l_), T55) for *_, l_ in F['flag_items']) <= FLX0 + FLW - 5.0, 'the words fit the box'
g('a flag', fl)
arr.append(cv.arrow([(CX1, YM), (FLX0, YM)], what='arrow catalog to flag'))
# P1: its icon and name on the steps' lines. P1 check (the cold reader's first note: "Who decides? ... the box does not
# say 'agent'"; each step box now names who acts, so Decide does too): two lines as the steps', 'agents decide / from
# the paper' (the flag's five sources are each settled by agents reading the paper: the database check, the audit,
# the unit and reprint sweeps with their refuters, a reviewer's rejection checked against the paper)
DEC_LINES = ['agents decide', 'from the paper']
assert max(wid(t_, T6) for t_ in DEC_LINES) <= DW - 4.0 and 'agent' in DEC_LINES[0]
# W1 check: no foot and no room kept for one: icon, name and lines centred in the box. FINAL PASS: a foot as the steps
# have, the database check's 3 rules (they act here: values are compared with the databases only after reading, and
# what a difference means is decided from the paper), so Decide's icon, name and lines stand over it as the steps' do
# and its name is on the steps' names' line
g('a decide', big('a decide', DX0, BY0, DW, BH, 'agent', 'scales', 'Decide', DEC_LINES, isz=ISZ, rows=2,
                  foot=NRL('Decide'), footh=FOOTH))
arr.append(cv.arrow([(FLX0 + FLW, YM), (DX0, YM)], what='arrow flag to decide'))

# ---- people (top left, as wide as b's first card): what they reviewed; the papers they reviewed are read first
PX0, PX1 = gl(0), gr(3)
PW = PX1 - PX0
# W1 review papers: both lines count CatLog's own review file at this build (facts): the records people checked
# against their papers, as the status counts them, then the distinct papers those records name
PL1 = f"reviewed {F['checked']} records"
PL2 = f"from {F['review_papers']} papers"
ptxt = max(wid(PL1, T55), wid(PL2, T55))
pic = PX0 + (PW - (6.5 + 11.5 + ptxt)) / 2 + 6.5      # the icon's centre: icon and words centred in the box
cv.holder('a people', PX0, PY0, PW, PH, 1.5)
g('a people', [cv.rect(PX0, PY0, PW, PH, FILL['people'], EDGEC['people'], SWB, RX),
               ico('person', pic, PY0 + PH / 2, 13.0, 'a people icon'),
               cv.text(pic + 11.5, PY0 + 12.4, 'People', TT, weight='bold', inside='a people'),
               cv.text(pic + 11.5, PY0 + 20.0, PL1, T55, inside='a people'),
               cv.text(pic + 11.5, PY0 + 27.2, PL2, T55, inside='a people')])
# S1r (the editor: an arrow from People into the box titled 'Blind to databases and reviews' seems to feed reviews into
# the blind reading, the first thing a referee will check): people choose which papers are read first, not what is read
# in them, so the arrow ends on the paper text, outside the blind frame; the 'rules' arrow is the only one that enters it
YPT = YI1 - 0.47 * ISI - 0.9               # just above the paper text's page
arr.append(cv.arrow([(IX, PY0 + PH), (IX, YPT)], what='arrow people to papers'))
plab = 'reviewed papers are read first'   # Q1: with its verb, so it cannot read as 'papers are reviewed first'
# S1r: on the arrow's right, over the frame's top-left corner and under the People box
g('a people label', [cv.text(IX + 3.5, YT - 3.6, plab, T55)])
assert IX + 3.5 + wid(plab, T55) < XFL - wid(lab, T55) / 2 - 4.0 or YT - 3.6 + 0.21 * T55 < YT - 1.5, 'the labels keep apart'
assert IX - SHAFT < FX0 - 10.0, 'the arrow stays outside the blind frame'

# ---- co-learning (the owner, 5 Nov: "co-learning instead of error rules ... both way since human and agent both
# work together"): above Verify and Check. People's errors go in and the agents' findings come back to people; the
# deciding agents' errors come back along the top; rules go down into the reading
CLX0, CLX1 = bx[2], bx[3] + BW
CLW = CLX1 - CLX0


CLT = [(str(F['rules_all']), 'b'), (' rules in instructions and code', '')]   # W1: the rules, said in a (the panel of rules is gone)
assert F['rules_all'] == sum(F['rules_drawn'].values()) == 73   # FINAL PASS: Fig. 4a's 73, the five feet's sum (it said the four steps' 68)
# W1 (the owner: "colearning should have some ai human visual maybe?"): the figure's picture of people and agents working
# together, a person and an agent side by side, stands before the title, as the pennant before 'Flag'; pair and title
# are centred in the box as one line, the line of rules centred under them. (Left of both lines the pair does not fit:
# the line of rules is 94 pt in a box of 117.) T1 round 2 had dropped a person-over-page composite here; this is two
# plain glyphs, the same two that c's loop uses
CLS = 10.5                                 # the pair's glyphs
CLG = 4.5                                  # white between the pair and the title
CLPW = (GW['person'] + GSIDE + GW['agent']) * CLS
CLXP = CLX0 + (CLW - (CLPW + CLG + wid('Co-learning', TT, True))) / 2   # the pair's left edge
YCL1, YCL2 = PY0 + 15.0, PY0 + 26.2        # the title's line and the line of rules
cv.holder('a rules', CLX0, PY0, CLW, PH, 1.5)
pair_, xpe_ = actors(('person', None, 'agent'), CLXP, YCL1 - 0.716 * TT / 2, CLS, 'a rules pair')
assert abs(xpe_ - CLXP - CLPW) < 1e-9 and CLX0 + 4.5 <= CLX0 + CLW / 2 - cv.rwidth(CLT, T55) / 2, 'pair, title and line fit the box'
g('a rules', [cv.rect(CLX0, PY0, CLW, PH, '#FFFFFF', LEARN, SWB, RX)] + pair_ + [
              cv.text(xpe_ + CLG, YCL1, 'Co-learning', TT, weight='bold', inside='a rules'),
              cv.rich(CLX0 + CLW / 2, YCL2, CLT, T55, 'middle', inside='a rules', what='a rules line')])
YPE, YPF = PY0 + PH / 2 - 4.0, PY0 + PH / 2 + 4.0
learn = []                                 # Q2: the learning arrows, cyan, in a group of their own
errs = []                                  # S1 (fix 1): the errors that go into co-learning, red, with their labels
errs.append(cv.arrow([(PX1, YPE), (CLX0, YPE)], fill=RED, what='arrow people to co-learning'))
learn.append(cv.arrow([(CLX0, YPF), (PX1, YPF)], fill=LEARN, what='arrow findings to people'))
XPM = (PX1 + CLX0) / 2
# FINAL PASS (ARROWS item 3: 'findings' said neither whose nor what, the weakest label for all three readers): 'agent
# findings', the plainer of the two wordings offered (the other, 'unsupported rejections', names one kind only; the
# agents' findings also cover what they find in the catalogue and the databases). One line would fill the 41.7 pt
# between the boxes, so it is set as two, 'agent' over 'findings', under the arrow
FIND_L = ['agent', 'findings']
assert max(wid(t_, T55) for t_ in FIND_L) + 8.0 < CLX0 - PX1 < wid(' '.join(FIND_L), T55) + 4.0, 'the people arrows carry their words'
learn.append(cv.arrow([(XRU, PY0 + PH), (XRU, YT)], fill=LEARN, what='arrow rules to reading'))
dcx = DX0 + DW / 2                         # P1: Decide's middle, so its three lines stand 15.5 pt apart
# ---- P1 (9 Nov, the owner: "where are the database names we put before there? That look better than this"): the
# databases as a card at a's top right, in b's card style, over the after-reading boxes (Flag's left edge to Decide's
# right) and outside the blind frame. Its one arrow, navy, ends in Decide: the agent given the database's number beside
# CatLog's, which decides from the paper and never changes a value (facts). Nothing goes back to the databases, so the
# check's output, their own errors, is said in the legend
# X1 (the owner: "font size improving"): the card spans the catalogue and the after-reading band, CatLog's left edge to
# Decide's right, as alternative 3's did (the card the owner remembers), so the six names fit on one line at 6.5 pt, the
# figure's text size (over Flag and Decide alone they needed 6 pt); its left edge on the grid (c's record column, gl(9))
# Y2 (the owner: "can the databases get their boxex in names instead of a,b,c,d...."): no strip; a plain bold title and
# each name in a small white box of its own with a navy outline, in one row; the card's place and foot as X1's, so the
# errors line under it, its label and the navy arrow into Decide do not move (the row ends 5.7 pt left of the arrow)
# P1 (11 Nov, the owner on the installed figure: "the databases as like a ... rounded ball or something. I forget the
# shape, but we did it instead of the current shape. As in a database vibe"): the databases are one cylinder, in the
# make of the earlier version and of a's CatLog (store()): the databases' navy line at the outlines' 0.5 pt, a white
# body, the lid in the databases' tint (the tint the card's strip had). It holds its title and the six names in two
# rows of three, in the text's face and colour; there is no card, no strip and no box round a name (the cylinder holds
# them). The names of a row are set apart by a centred dot, as the earlier version set them ('STRENDA DB' is two words).
# Q1 (11 Nov, the owner: "Yes, move it"): it stands over the Flag box, on the Flag's two side edges, and its arrow
# drops from the middle of its foot into the middle of the Flag's top: a value that differs from a database is flagged,
# and agents then decide from the paper (two first-time readers had read the arrow into Decide as 'the databases help
# decide'). The space between Co-learning and it, and over Decide, is white. Its lid is as
# tall as CatLog's, so the two stores are of one make. Three lines and the lid need 36.5 pt, and the errors line must
# pass under the cylinder into Co-learning's right edge, so the cylinder stands 8.5 pt over the top row's top line (the
# row itself is 5 pt taller): its foot is where the card's was over the errors line (3.8 pt). The errors line and the
# corrections line run under it, from Decide to Co-learning and to CatLog, and its arrow crosses both at right angles
DBW = FLW                                  # Q1: the cylinder as wide as the Flag box it stands over
DBX0, DBX1 = FLX0, FLX0 + FLW
DBCX, DBRX = (DBX0 + DBX1) / 2, DBW / 2
DRY = CRY                                  # half the lid's height, as CatLog's
DBT = PY0 - 10.5                           # the lid's highest point. FINAL PASS (ARROWS item 4, the editor: the errors line ran
#                                            1.3 mm under the cylinder, which seemed to stand on it, and the navy arrow had no
#                                            stem before the crossing): the cylinder 2 pt (0.7 mm) higher
DBSEP = ' · '
assert len(F['db_names']) == 6
DBL = [DBSEP.join(F['db_names'][:3]), DBSEP.join(F['db_names'][3:])]   # two rows of three, in the databases' order
assert not re.search(r'[gjpqy,;]', ''.join(F['db_names'])), F['db_names']   # no descenders: a row ends on its baseline
YDBT = DBT + 2 * DRY + 2.4 + 0.716 * TT    # the title: its capitals 2.4 pt under the lid's front edge
YDBN = [YDBT + 7.6, YDBT + 7.6 + 7.2]      # the two rows of names (7.6 and 7.2 pt apart, as the lines of the People box)
DBE = math.sqrt(1 - (max(wid(l_, T55) for l_ in DBL) / 2 / DBRX) ** 2)   # the bottom arc's height at the wider row's ends
DBY1 = YDBN[1] + 3.6 + DRY * (1 - DBE)     # the bottom's lowest point: the arc 3.6 pt under the last row at the row's ends
XDB = DBCX                                 # Q1: the databases' arrow, from the middle of the cylinder's foot into the Flag
assert 95.0 <= DBW <= 115.0 and DBX0 - CLX1 >= 2 * G and DBX1 + G <= DX0 + 1e-9, 'the cylinder over the Flag, white each side of it'
assert DBX0 + 4.0 <= DBCX - max(wid(l_, T55) for l_ in DBL) / 2, 'the rows stand inside the sides'
assert DBT >= 3.0, 'the lid stays under the page\'s top margin'
cv.holder('a databases', DBX0, DBT + 2 * DRY, DBW, YDBN[1] + 3.6 - DBT - 2 * DRY, 0.7)
dbs_ = store(DBX0, DBX1, DBT, DBY1, DRY, '#FFFFFF', DB_TINT, NAVY, SWB) + [
    cv.text(DBCX, YDBT, 'Databases', TT, 'middle', 'bold', inside='a databases')]
dbs_ += [cv.text(DBCX, y_, l_, T55, 'middle', inside='a databases', what=f'a databases names {k}')
         for k, (l_, y_) in enumerate(zip(DBL, YDBN))]
# the arrow starts on the bottom arc's middle line (so it joins the arc's own line) and ends on the Flag's top
assert DBX0 + 4.0 <= XDB <= DBX1 - 4.0
YDBA = DBY1 - DRY + DRY * math.sqrt(1 - ((XDB - DBCX) / DBRX) ** 2)   # the bottom edge at the arrow (its lowest point)
assert abs(XDB - (FLX0 + FLW / 2)) < 1e-9 and abs(YDBA - DBY1) < 1e-9, 'from the foot\'s middle into the Flag\'s middle'
dba_ = [cv.arrow([(XDB, YDBA), (XDB, BY0)], fill=NAVY, what='arrow databases to flag')]   # its own group (checker)
YRU = DBY1 + 5.3                           # P1: the deciding agents' errors run under the card (was the top row's middle).
#                                            FINAL PASS (ARROWS item 4): 5.3 pt under the cylinder's foot (3.8), the line itself
#                                            0.5 pt higher than it was, so it enters Co-learning a little further from its corner
assert PY0 + PH - YRU >= HW / 2 + 2.0, "the errors arrow ends on the straight part of Co-learning's right edge"
errs.append(cv.arrow([(dcx, BY0), (dcx, YRU), (CLX1, YRU)], fill=RED, what='arrow decide to co-learning'))
# FINAL PASS (ARROWS item 1, the cold reader and the editor: over the Flag three lines of three colours met within 5 mm,
# the red errors line, the black corrections line and the navy arrow crossing both, and two lines left Decide's top side
# by side): the corrections leave Decide from the middle of its foot, run left under the Flag at the level of the line
# into Verify, and enter CatLog from below, at the middle of its base; the word stands under the run. One crossing is
# left (navy over red), 'After reading' reads as the Flag's heading, and the return runs under the row, as c's does
XCOR = (ccx + dcx) / 2                     # 'corrections' in the middle of its run
YCOR = YCH + SHAFT / 2 + LGAP + 0.716 * T55   # its capitals LGAP under the run, as 'findings' under its arrow
arr.append(cv.arrow([(dcx, BY0 + BH), (dcx, YCH), (ccx, YCH), (ccx, BY0 + BH)], what='arrow decide to catalog'))
assert FX1 + 5.0 <= ccx - HW / 2 and dcx <= GX1 and YCH - (BY0 + BH) >= HL + 2.5, \
    'the run outside the blind frame, under the Flag; the head on a stub of 2.5 pt or more after its elbow'
assert CLX1 < XDB < dcx and ccx < XDB < dcx and DBY1 < YRU < BY0, 'the databases\' arrow crosses the errors line only'
assert BY0 - YRU >= HL + 6.0 and YRU - SHAFT / 2 - (DBY1 + SWB / 2) >= 4.5, \
    'the head clear of the crossing; the errors line 1.5 mm or more under the cylinder, the navy arrow a stem before it'
assert XCOR - wid('corrections', T55) / 2 >= ccx + HW / 2 + 6.0 and XCOR + wid('corrections', T55) / 2 <= dcx - HW / 2 - 6.0, \
    'the word between the run\'s two legs'
assert (YCOR - 0.716 * T55) - (YCH + SHAFT / 2) >= LGAP - 1e-9 and YCOR + 0.21 * T55 <= YB + 4.0, 'under its run, near the frame\'s foot'
# X1: the card now starts one gutter right of Co-learning, so the errors line's label stands under the line, just after
# its head, between Co-learning's edge and the corrections line's way down into CatLog (as 'findings' under its arrow).
# FINAL PASS (ARROWS item 2, the editor; the cold reader: the label stood 50 mm from where its line starts): at the
# Decide end, over its line, in the white between the cylinder's side and the line's rise, so both 'errors' stand over
# their lines and what leaves Decide is named there
XEL = (DBX1 + dcx) / 2
YEL = YRU - SHAFT / 2 - LGAP               # its baseline LGAP over the line (the word has no descender)
assert DBX1 + 4.0 <= XEL - wid('errors', T55) / 2 and XEL + wid('errors', T55) / 2 <= dcx - SHAFT / 2 - 4.0, 'the label fits'
assert not re.search(r'[gjpqy]', 'errors') and YEL - 0.716 * T55 >= DBY1 - DRY, 'the label beside the cylinder\'s foot, over its line'
errs += [cv.text(XPM, YPE - SHAFT / 2 - LGAP, 'errors', T55, 'middle', fill=RED),
         cv.text(XEL, YEL, 'errors', T55, 'middle', fill=RED)]
YFI = YPF + SHAFT / 2 + LGAP + 0.716 * T55   # 'agent', then 'findings' a line under it
g('a loop labels', [cv.text(XPM, YFI, FIND_L[0], T55, 'middle'), cv.text(XPM, YFI + 7.2, FIND_L[1], T55, 'middle'),
                    cv.text(XRU + 3.5, YT - 3.6, 'rules', T55),
                    cv.text(XCOR, YCOR, 'corrections', T55, 'middle')])
g('a arrows', arr)
g('a learning', learn)
g('a errors', errs)
g('a databases', dbs_)
g('a databases arrow', dba_)
A_BOTTOM = YB

# ================================================================== (no panel of rules) the grid the loop's boxes stand on
# W1 (11 Nov, the owner on idea 2: "no point writing read convert verify check twice - we can include the rule thingy
# somehow in a proper [compact] way in part a right? and get rid of part b"). The panel of four strips is gone, with its
# title, the zoom's two lines from a's frame and the dashed edge they ended on. Each step's count of rules is the foot
# of its box in a (make.py, W1), and a's Co-learning box says the 68; Read, Convert, Verify and Check are written once.
# What is left here is the four-column grid (the columns the strips had; a's People and Co-learning boxes stand on its
# first two), the loop's text inset and the facts the counts come from. (W1 check: the loop's strips are as wide as
# their names and pictures need, new_d.py, so they no longer stand on these columns.)
WCB = 4 * C16 + 3 * G                      # a column of four half-columns: 116.69 pt (the loop's boxes)
XCB = [gl(4 * k) for k in range(4)]
BI = 4.5                                   # the text inset of the loop's boxes
LR = F['layers_n']
assert F['rules_b'] == sum(F['rules_n'].values()) == 68
assert [LR[l_] for l_ in ('reader prompt', 'code conversion', 'verifier prompt', 'code check')] == \
    [F['rules_n'][n_] for n_ in ('Read', 'Convert', 'Verify', 'Check')] == [16, 10, 7, 35], 'each step\'s count is its layer\'s'
assert abs(XCB[0] - GX0) < 1e-9 and abs(XCB[3] + WCB - GX1) < 1e-9, 'the four columns fill the grid'
TICK_ONE = None                            # no rule marks are drawn, so the colour sentence names none
A_ = F['asp']                              # the wild-type record's facts (the legend)
B_ = F['b2']


# ================================================================== b: from papers to values, three objects in one row
# V2 (11 Nov, the owner on the baseline: "does c look underwhelming ?? ... or better visual?"): the panel is drawn, not
# written into two boxes: a pile of pages (the papers), a record, and the catalogue's cylinder, joined by the figure's
# black arrows, each with its count beside it.
# W1 (11 Nov, the owner on V2's strip: "c i like but underwhelming"). The same three objects, with weight and no added
# sentence. They are larger and of one height (30 pt), on one line: the pile of pages; ONE record, drawn as a record: a
# card 40 x 30 pt with a header strip in the catalogue's tint and three rows that say what a record holds, kcat, Km and
# kcat/Km (the figure's kinetics type; no value, no other mark); and the catalogue's cylinder, as wide as a's CatLog,
# with its lid as tall as a's and its name in it in the catalogue's green, as in a. The counts are 7 pt, each bold with
# its noun, on one line across the three objects; under each, in the text's 6.5 pt, its side facts (the papers kept
# unread, with their padlock; the papers the records come from; what CatLog keeps apart, on two lines, the second on
# the cylinder's foot). The two black arrows are one length and level with the objects' middles; each starts 6 pt after
# the words before it and its head ends on the next object's outline. The trail is drawn: one thin dashed line in the
# neutral grey leaves the cylinder's foot, runs back under the row and ends, with the figure's arrowhead, on the front
# page of the pile; on it, 'each value traced to its printed line' (the words left the values' line). The letter is b:
# the panel of rules is gone (new_b.py), so the groups are b's.
# Q2 (11 Nov, the owner: the papers cited by databases and found by a search "are not like the catalog numbers,
# right? So we should use the paper's catalog searched or the records we went through"): the panel counts what CatLog
# has done, at the catalogue's checkpoint: the papers read and those of them that gave values (the pool the papers come
# from, 44,407 cited and 30,814 found, is the legend's), its records and its values, counted as status and export count
# them.
# W1 counts (11 Nov, the owner: "i think use the latest value for now and we will also update in the very end"): every
# count drawn here is a value of F that facts() took from writing/fig1_v8/ref/catalogue_counts.json (F['ck'], written by
# ref/catalogue_counts.py <commit>) and checked against that commit; no count is written in this block. FINAL PASS: F['ck']
# is the freeze's file, paper/evidence/catalog_freeze_20261116/catalogue_counts.json, checked against the tag
# L2 (11 Nov, the owner on the record card: "maybe we also mention other stuff we add - right? this is oversimplification,
# no? as in how it connects to multiple database and grabs data - but more visually showing and less wordish"): a record
# holds more than three values. For every record code looks up the enzyme's UniProt entry and its sequence (through PDB
# chains and NCBI records where the paper prints those), places a variant in that sequence, and looks up the
# substrate's structure. L2 drew that as two pictures in the card and six small cylinders over it, joined in code's sign.
# M2 (11 Nov, the owner on the three versions: "2 or 3 is looking better to me"; the checker on L2: the busiest, lopsided,
# stub arrows of another weight, the row wider than the card, no sequence, an empty header, no divider): version 2,
# calmed. The record is one card of three cells under a header that holds the records' count: the enzyme (the prepared
# picture of one real record's UniProt entry, in code's slate, the residue its paper's variant changes as dark spheres;
# beside it one line of the stored sequence, seven letters, that residue in a box of code's colours), the three rows
# kcat, Km and kcat/Km in the middle, and the substrate (that record's stored structure, drawn by RDKit). Hairlines
# part the cells. Neither enzyme nor substrate is named: the legend says which record it is. Over the card stand the
# sources, six cylinders of one size in a's Databases make (navy line, white body, tinted lid, the name alone inside):
# UniProt, PDB and NCBI exactly over the enzyme's cell, Rhea, ChEBI and PubChem exactly over the substrate's, so the
# row is as wide as the card and nothing stands over the values, which no database gives. Each three meet in one small
# box of code's fill with code's sign (a's Convert box, small) under their middle cylinder: the middle one drops
# straight onto it, the outer two come down and in by equal square-cornered legs. From each box ONE navy arrow of the
# figure's make (0.75-pt shaft, the figure's head) drops onto the card's top line, over the middle of its cell. The two
# halves mirror each other about the card's middle, and the header's line (the records' count and the papers they come
# from) is centred between the two arrowheads. The pile and the catalogue's cylinder are as tall as the card's cells
# (30 pt) and stand beside them on the card's foot line, so the two black arrows (as long as a's between its steps) run
# on the cells' middle line; the trail runs under the card with its words on it, in the middle of its run, as before.
YLB = YB + 14.8                            # the title's line, 14.8 pt under a's frame (as the panels stood apart before)
BT = YLB - 8.0                             # the panel's top (for the size print)
g('panel letter b', cv.panel_letter(GX0, YLB, 'b', 'From papers to values'))
SRC = F['sources']                         # {'enzyme': [UniProt, PDB, NCBI], 'substrate': [Rhea, ChEBI, PubChem]}
assert SRC == {'enzyme': ['UniProt', 'PDB', 'NCBI'], 'substrate': ['Rhea', 'ChEBI', 'PubChem']}, SRC
SNAMES = SRC['enzyme'] + SRC['substrate']
T_S = ES(T55)                              # the sources' names: 5.5 pt, the subscripts' size (at 6.5 pt six cylinders of one
#                                            size are wider than the room between the papers' words and the catalogue)
SRY = 1.5                                  # a source's lid: 3 pt tall
SPAD = 1.5                                 # white between the longest name and its cylinder's sides (the line's middle)
SGAP = 2.85                                # white between two cylinders of one kind: 1 mm
SW_ = max(wid(n_, T_S) for n_ in SNAMES) + 2 * SPAD   # ONE width for the six, set by the longest name
TRIO = 3 * SW_ + 2 * SGAP                  # three cylinders and the white between them
YS0 = YLB - 0.716 * T7                     # the lids' tops: level with the title's capitals
YSN = YS0 + 2 * SRY + 1.5 + 0.716 * T_S    # the names' line: capitals 1.5 pt under the lid's front edge
YS1 = YSN + 1.6 + SRY                      # the cylinders' feet (the arc's ends 1.6 pt under the names' line)
CHW, CHH = 10.0, 7.0                       # code's box, where a kind's three lines meet: 10 x 7 pt
CSIGN = 5.5                                # the sign in it (ink 5.1 x 4.4 pt)
SLEG = 4.3                                 # the middle cylinder's line, from its foot onto the box's top: 1.5 mm
YCH = YS1 + SLEG + CHH / 2                 # the box's middle, and the level of the outer two's runs
SARR = 9.0                                 # the arrow from a box onto the card: the figure's head (3.8 pt) and 5.2 pt of its shaft
CARD_TOP = YCH + CHH / 2 + SARR
B1 = CARD_TOP + 9.0                        # the objects' top: the card's header line. The pile and the cylinder are as tall as
#                                            the card's cells and stand beside them, on the card's foot line; the header rises over the row
assert YS0 - YB >= 9.0, ('the sources stand clear of a\'s frame', YS0 - YB)
NB = '\xa0'
CJ_ = F['ck']                              # the catalogue's counts at its checkpoint, as facts() read and checked them
assert (F['read_by_ck'], F['papers'], F['records'], F['values'], F['nd']['n'], F['lt']['n'], F['unread']) == \
    tuple(f'{CJ_[k_]:,}' for k_ in ('papers_read', 'papers_with_values', 'records', 'values', 'not_detected', 'limits',
                                    'test_unread')), 'the counts drawn are the file\'s'
assert CJ_['test_unread'] <= CJ_['test_papers'] and CJ_['papers_with_values'] <= CJ_['papers_read'] and \
    CJ_['records'] <= CJ_['values'] <= 3 * CJ_['records'], 'unread among the test papers, papers with values among the papers read, one to three values to a record'

OBJ_H = 31.5                               # the pile and the cylinder: one height, 30 pt. FINAL PASS (the record card's checker,
#                                            12 Nov: the structure's ink stood 0.64 and 0.74 mm from its cell's lines): 31.5 pt,
#                                            the room taken from the trail's 11 pt under the card, which its words no longer use
PILE_PH, PILE_D, PILE_C = 26.1, 2.7, 5.2   # the pile: a page 26.1 pt tall (a's page, 0.76 as wide as tall), two more behind it
PILE_PW = 19.84
CARD_HEAD, CELL_H = 9.0, 31.5              # the record: a header that holds the count (7 pt) and, under it, its cells
CARD_H = CARD_HEAD + CELL_H                # 39 pt: the cells 30 pt, as tall as the pile and the cylinder, so that the drawing
#                                            (26 pt, the least height at which molecule() sets this structure) stands free
ROWS = ['kcat', 'Km', 'kcat/Km']           # what a record holds: up to three values
ROWW = max(cv.rwidth(kin(l_), T55) for l_ in ROWS)
VPAD = 5.5                                 # white between the values' cell's lines and its rows (final check: 4.0 before; the cell
#                                            3 pt wider sets the navy arrows 3 pt further apart, room for longer counts in the header)
CELLW = [TRIO, ROWW + 2 * VPAD, TRIO]      # the cells: the enzyme, the three values, the substrate; a side cell is exactly as
#                                            wide as the three cylinders over it
CARD_W = sum(CELLW)
ROW_PITCH = 8.0
ROW_Y0 = CARD_HEAD + (CELL_H - (0.72 * T55 + 2 * ROW_PITCH + 1.4)) / 2 + 0.72 * T55   # the three rows centred in their cell
HEAD_Y = (CARD_HEAD + 0.716 * T7) / 2      # the header's baseline: the count's capitals centred in the header
HEAD_GAP = 2.5                             # white between the count and its side fact (final check: 4.0 before)
IMH = 26.0                                 # the enzyme's picture: 26 pt tall in its 30-pt cell, as the drawing, as wide as its pixels make it
IMW = IMH * F['struct']['px'][0] / F['struct']['px'][1]
ST_ = F['link']['stretch']                 # one line of the stored sequence, the changed residue in its middle (facts_m2)
# set as ONE string, with a space before and after the changed residue: its box takes half of each space, so the box's
# line stands in white, clear of the letters beside it
SEQ_S = ST_['line'][:ST_['col']] + '\xa0' + ST_['line'][ST_['col']] + '\xa0' + ST_['line'][ST_['col'] + 1:]
SEQ_W = wid(SEQ_S, T55)
SEQ_BOX = (wid(ST_['line'][ST_['col']], T55) + wid('\xa0', T55), 0.716 * T55 + 3.4)   # the changed residue's box
MOLW, MOLH = 54.0, 26.0                    # the substrate's drawing: molecule() as it is (its atom labels 6.5 pt; under 26 pt of
#                                            height its subscripts leave the drawing's box and it stops)
CYL_W, CYL_RY = CX1 - CX0, CRY             # the cylinder: as wide as a's CatLog, its lid as tall as a's
assert abs(PILE_PH + 2 * PILE_D - OBJ_H) < 1e-9 and abs(PILE_PW / PILE_PH - 0.76) < 0.005 and abs(CYL_W - 37.0) < 1e-9
assert 26.0 <= OBJ_H <= 31.5 and CARD_H == 40.5 and abs(CELLW[0] - CELLW[2]) < 1e-9, 'the pile and the cylinder 31.5 pt, the record 40.5, its side cells one width'
EGAP = (CELLW[0] - IMW - SEQ_W) / 3        # the enzyme's cell: picture and sequence with one white before, between and after
assert EGAP >= 4.0 and IMH + 4.0 <= CELL_H >= MOLH + 4.0 and MOLW + 8.0 <= CELLW[2], (EGAP, 'the pictures stand free in their cells')


def pile(cx, cy, what, pw=PILE_PW, ph=PILE_PH, c=PILE_C, d=PILE_D, n=3):
    """A pile of n pages, a's page (its folded corner, its lines) drawn large: the front page lowest and leftmost, each
    page behind it d up and d to the right. One stroke weight, ink on white; centred at (cx, cy). Returns the group
    and the front page's middle x (where the trail ends)."""
    st = f'fill="none" stroke="{INK}" stroke-width="{f2(ISW)}" stroke-linejoin="round" stroke-linecap="round"'
    sf = f'fill="#FFFFFF" stroke="{INK}" stroke-width="{f2(ISW)}" stroke-linejoin="round"'
    wt, ht = pw + (n - 1) * d, ph + (n - 1) * d
    o = []
    P_ = lambda pts, style, closed=False: o.append(
        '<path d="M' + ' L'.join(f'{f2(a)},{f2(b)}' for a, b in pts) + (' Z' if closed else '') + f'" {style}/>')
    for k in range(n - 1, -1, -1):
        x0, y0 = cx - wt / 2 + k * d, cy - ht / 2 + (n - 1 - k) * d
        P_([(x0, y0), (x0 + pw - c, y0), (x0 + pw, y0 + c), (x0 + pw, y0 + ph), (x0, y0 + ph)], sf, True)
        P_([(x0 + pw - c, y0), (x0 + pw - c, y0 + c), (x0 + pw, y0 + c)], st)
    for k, f_ in enumerate((0.8, 1.0, 1.0, 1.0, 0.55)):   # the front page's lines: a's page has four, the larger page five
        yy = y0 + ph * (0.34 + 0.125 * k)
        P_([(x0 + 0.2 * pw, yy), (x0 + (0.2 + 0.6 * f_) * pw, yy)], st)
    cv.box(cx - wt / 2, cy - ht / 2, cx + wt / 2, cy + ht / 2, what, 'mark')
    return '<g>' + ''.join(o) + '</g>', x0 + pw / 2


def record(x0, y0, gid, cw=CARD_W, ch=CARD_H, hh=CARD_HEAD, r=RX):
    """M2: one record, as one card of three cells: the boxes' corner radius, ink on white in the icons' weight; a
    header in the catalogue's tint (a record is CatLog's) that holds the records' count and their papers; under it
    three cells of one height parted by hairlines: the enzyme and the substrate (groups of their own, drawn by the
    caller) and, between them, the three rows kcat, Km and kcat/Km in the figure's kinetics type. No value. Its top
    left corner at (x0, y0). Returns the card and the cells' edges."""
    cv.holder(gid, x0, y0, cw, ch, 0.5)
    cv.holder(gid + ' head', x0, y0, cw, hh, 0.4)
    head = (f'<path d="M{f2(x0)},{f2(y0 + hh)} L{f2(x0)},{f2(y0 + r)} A{f2(r)},{f2(r)} 0 0 1 {f2(x0 + r)},{f2(y0)} '
            f'L{f2(x0 + cw - r)},{f2(y0)} A{f2(r)},{f2(r)} 0 0 1 {f2(x0 + cw)},{f2(y0 + r)} L{f2(x0 + cw)},{f2(y0 + hh)} Z" '
            f'fill="{CAT_TINT}"/>')
    it = [f'<rect x="{f2(x0)}" y="{f2(y0)}" width="{f2(cw)}" height="{f2(ch)}" rx="{f2(r)}" fill="#FFFFFF" '
          f'stroke="{INK}" stroke-width="{f2(ISW)}" stroke-linejoin="round"/>', head,
          f'<rect x="{f2(x0)}" y="{f2(y0)}" width="{f2(cw)}" height="{f2(ch)}" rx="{f2(r)}" fill="none" '
          f'stroke="{INK}" stroke-width="{f2(ISW)}" stroke-linejoin="round"/>',
          f'<path d="M{f2(x0)},{f2(y0 + hh)} L{f2(x0 + cw)},{f2(y0 + hh)}" fill="none" stroke="{INK}" stroke-width="{f2(ISW)}"/>']
    xc = [x0 + sum(CELLW[:k]) for k in range(len(CELLW) + 1)]
    for x_ in xc[1:-1]:                    # the cells' hairlines, from the header's line to the card's foot
        it.append(f'<path d="M{f2(x_)},{f2(y0 + hh)} L{f2(x_)},{f2(y0 + ch)}" fill="none" stroke="{INK}" stroke-width="{f2(HAIR)}"/>')
        cv.box(x_ - HAIR / 2, y0 + hh, x_ + HAIR / 2, y0 + ch, f'{gid} cell line', 'mark')
    for k, lab_ in enumerate(ROWS):
        it.append(cv.rich(xc[1] + VPAD, y0 + ROW_Y0 + k * ROW_PITCH, kin(lab_), T55, inside=gid, what=f'{gid} row {lab_}'))
    # the count and its papers: one line, centred in the header, so that it stands between the two arrows that land
    # on the card's top line (each 1 mm or more from the line's ends) and the header mirrors like the rest
    xh = x0 + (cw - HEAD_W) / 2
    it.append(cv.rich(xh, y0 + HEAD_Y, CNT[1], T7, fill=TXT, inside=gid + ' head', what='b record count'))
    it.append(cv.text(xh + cv.rwidth(CNT[1], T7) + HEAD_GAP, y0 + HEAD_Y, FROM, T55, fill=TXT,
                      inside=gid + ' head', what='b record from'))
    # each arrow's head ends in a point on the card's top line; the header's line of words begins under that line (its
    # capitals centred in the header) and ends beside the point: 1 mm or more from it, and never under the head
    hgap_ = (CELLW[1] + CELLW[0]) / 2 - HEAD_W / 2
    assert hgap_ >= HW / 2 + 1.0 and math.hypot(hgap_, (hh - 0.716 * T7) / 2) >= MM, ('the header\'s line ends clear of each arrow\'s head', HEAD_W, hgap_)
    return it, xc


def sequence(xl, ym, gid):
    """M2: one line of the record's stored sequence, set as one string from xl, its capitals centred on ym; behind the
    changed residue a box of code's fill and outline (code places the paper's variant in the sequence)."""
    cap = 0.716 * T55
    xb = xl + wid(ST_['line'][:ST_['col']], T55) + wid('\xa0', T55) / 2
    assert xb - xl >= 0 and SEQ_BOX[1] <= CELL_H - 6.0 and wid('\xa0', T55) / 2 - SWB / 2 >= 0.6, 'the box\'s line in the white beside the letter'
    return [f'<rect x="{f2(xb)}" y="{f2(ym - SEQ_BOX[1] / 2)}" width="{f2(SEQ_BOX[0])}" height="{f2(SEQ_BOX[1])}" rx="0.8" '
            f'fill="{FILL["code"]}" stroke="{EDGEC["code"]}" stroke-width="{f2(SWB)}"/>',
            cv.text(xl, ym + cap / 2, SEQ_S, T55, fill=TXT, inside='b record', what=f'{gid} line')]


YI = B1 + OBJ_H / 2                        # the objects' middle, and the two arrows
PITCH = 8.9                                # the lines beside an object, 8.6 pt apart (the third then stands on the cylinder's foot).
#                                            FINAL PASS: 8.9, so that it still does on the taller cylinder
YB1 = YI - PITCH / 2 + 0.716 * T7 / 2      # the counts' line: its capitals centred 4.3 pt over the objects' middle
YB2 = YI + PITCH / 2 + 0.716 * T55 / 2     # the side facts' line: 4.3 pt under it
YB3 = YB2 + PITCH                          # the values' second side fact
TG = 4.5                                   # white between an object and its words (final check: 6.0 before; the row gives back
#                                            the 3 pt the card took, so the two black arrows keep their length)
AGAP = 6.0                                 # white between the words and the arrow that follows them (its head ends on the next outline)
CLK = 8.0                                  # the padlock's page: 6.2 x 8 pt (it stands in a line of words)
LKW = 8.0 * CLK / 10.4

CNT = [[(F['read_by_ck'] + NB + 'papers', 'b'), (' read so far', '')],
       [(F['records'] + NB + 'records', 'b')],
       [(F['values'] + NB + 'values', 'b')]]
# FINAL PASS (the final-pass list, item 4; ARROWS item 7: the cold reader set 9,151 - 8,807 = 344 against the 343): the
# locked test has run, so 'a later' goes. The pass's check: 'held out' is the legend's and the Methods' word for all 369
# test papers (26 read before the lock), so the line names what the 343 are, the papers kept unread for the test
KEPT = f"{F['unread']} kept unread for the test"
FROM = f"from {F['papers']} of them"        # of the papers read: the papers with values are the papers the records come from
KP1 = [(f"+ {F['nd']['n']}", ''), (NB + 'printed as ' + F['nd']['words'], '')]   # the paper prints them so
KP2 = [(f"+ {F['lt']['n']}", ''), (NB, '')] + F['lt']['words']
HEAD_W = cv.rwidth(CNT[1], T7) + HEAD_GAP + wid(FROM, T55)   # the header's line: the count, a white, its papers
TRAIL = 'each value traced to its printed line'   # 'each' is each value: a record's values can come from different lines
OW = [PILE_PW + 2 * PILE_D, CARD_W, CYL_W + CAT_SW]   # the objects' widths
TW = [max(cv.rwidth(CNT[0], T7), LKW + 3.0 + wid(KEPT, T55)), 0.0,
      max(cv.rwidth(CNT[2], T7), cv.rwidth(KP1, T55), cv.rwidth(KP2, T55))]     # their words' widths: the longest line
#                                            (M2: the record's words stand in its header, none beside it)
BWD = [OW[0] + TG + TW[0], OW[1], OW[2] + TG + TW[2]]
ALAND = [0.0, CAT_SW / 2]                  # where a head ends, from the object's left edge: on the record's left line, and
#                                            on the middle of the cylinder's 1-pt side (as a's arrow from Check ends on CatLog's)
AL = (GX1 - GX0 - sum(BWD) - AGAP + ALAND[1]) / 2   # the second arrow leaves the card's right edge, as a's leave their boxes
BX = [GX0, GX0 + BWD[0] + AGAP + AL, GX1 - BWD[2]]
OX = [BX[k] + OW[k] / 2 for k in range(3)]  # the objects' middles
TX = [BX[k] + OW[k] + TG for k in range(3)]  # their words' left edges (the record has none beside it)
assert AL >= 9.9, ('the two arrows as long as a\'s between its steps (10 pt), or longer', AL)
YC0 = B1 - CARD_HEAD                       # the card's top: its cells level with the pile and the cylinder
assert OBJ_H == CELL_H and abs(YI - (YC0 + CARD_HEAD + CELL_H / 2)) < 1e-9, 'the two black arrows on the cells\' middle line'
YTR = YC0 + CARD_H + 9.5                   # the trail's run, 11 pt under the card. FINAL PASS: 9.5 pt; its words stand on the
#                                            run left of the card, so the 1.5 pt the cells gained comes from here and b keeps its height
TLG = LGAP + 0.8                           # its words over it: 0.8 pt more than a's labels, for the p of 'printed'
BB = YTR + SWB / 2                         # the panel ends with the trail
cv.holder('b row', GX0, B1, GX1 - GX0, BB - B1, 0.0)

# ---- the papers: a pile of pages; the count; the papers kept unread, with their padlock
pile_, XPF = pile(OX[0], YI, 'b papers pile')
g('b papers', [pile_,
               cv.rich(TX[0], YB1, CNT[0], T7, fill=TXT, inside='b row', what='b papers count'),
               ico('locked', TX[0] + LKW / 2, YB2 - 0.716 * T55 / 2, CLK, 'b papers icon locked'),
               cv.text(TX[0] + LKW + 3.0, YB2, KEPT, T55, fill=TXT, inside='b row', what='b papers kept')])
# ---- the records: one record, a card of three cells; the count and the papers the records come from in its header
assert abs(YC0 - CARD_TOP) < 1e-9, 'the card\'s top is where the sources\' arrows end'
card_, XC = record(BX[1], YC0, 'b record')
YCL = YC0 + CARD_HEAD                      # the cells' top
YCM = YCL + CELL_H / 2                     # their middle line
g('b record', card_)
# ---- what code adds to a record, in the card's two side cells. The enzyme: the one <image> of the figure (the prepared
# picture of the record's UniProt entry, embedded so the SVG stands alone; its provenance is checked in facts()) and,
# beside it, one line of the stored sequence with the changed residue boxed. The substrate: the record's stored
# structure, drawn by RDKit as plain paths. Each cell's contents are centred in it
import base64
XIM, YIM = XC[0] + EGAP, YCM - IMH / 2
XSQ = XIM + IMW + EGAP
cv.box(XIM, YIM, XIM + IMW, YIM + IMH, 'b record enzyme picture', 'mark')
g('b record enzyme', [f'<image x="{f2(XIM)}" y="{f2(YIM)}" width="{f2(IMW)}" height="{f2(IMH)}" preserveAspectRatio="none" '
                      f'xlink:href="data:image/png;base64,{base64.b64encode(open(STRUCT_PNG, "rb").read()).decode("ascii")}"/>'])
g('b record sequence', sequence(XSQ, YCM, 'b record sequence'))
XMO, YMO = XC[2] + (CELLW[2] - MOLW) / 2, YCM - MOLH / 2
g('b record substrate', molecule(A_['smiles'], XMO, YMO, MOLW, MOLH, 'b record substrate structure'))
assert A_['smiles'] == F['asp']['smiles'] and F['link']['uniprot'] == F['asp']['uniprot'] == F['struct']['entry'].split('-')[1], \
    'one record: the picture is its UniProt entry\'s, the drawing its stored structure'
XEC, XSC = (XC[0] + XC[1]) / 2, (XC[2] + XC[3]) / 2   # the two side cells' middles: where the sources' arrows end
# ---- the sources, over the card: three cylinders of one size exactly over the enzyme's cell, three exactly over the
# substrate's. Each a cylinder of a's make with its name alone inside
SX = {}                                    # each cylinder's left edge
for x0_, k_ in ((XC[0], 'enzyme'), (XC[2], 'substrate')):
    for j_, n_ in enumerate(SRC[k_]):
        SX[n_] = x0_ + j_ * (SW_ + SGAP)
SCX = {n_: SX[n_] + SW_ / 2 for n_ in SX}
assert abs(SCX['PDB'] - XEC) < 1e-9 and abs(SCX['ChEBI'] - XSC) < 1e-9, 'each middle cylinder straight over the middle of its cell'
assert abs(SX['UniProt'] - BX[1]) < 1e-9 and abs(SX['PubChem'] + SW_ - (BX[1] + CARD_W)) < 1e-9 and \
    abs(SX['NCBI'] + SW_ - XC[1]) < 1e-9 and abs(SX['Rhea'] - XC[2]) < 1e-9, 'the row as wide as the card, each three as wide as its cell'
src_ = []
for n_ in SNAMES:
    # the name stays between the lid's front edge and the foot's arc, which at the name's two ends is 2.2 pt or more
    # under the names' line
    assert 1.6 + SRY * math.sqrt(1 - (wid(n_, T_S) / SW_) ** 2) >= 2.2, n_
    cv.holder(f'b source {n_}', SX[n_], YS0 + 2 * SRY, SW_, YS1 - SRY + 0.5 - YS0 - 2 * SRY, 0.6)
    cv.box(SX[n_], YS0, SX[n_] + SW_, YS0 + 2 * SRY, f'b source {n_} lid', 'mark')
    src_ += store(SX[n_], SX[n_] + SW_, YS0, YS1, SRY, '#FFFFFF', DB_TINT, NAVY, SWB)
    src_.append(cv.text(SCX[n_], YSN, n_, T_S, 'middle', inside=f'b source {n_}', what=f'b source name {n_}'))
# the lines, in the outlines' weight, square-cornered: the middle cylinder's drops from its foot onto the box's top; the
# outer two's come down from their feet to the box's middle line and in, onto its sides. The two outer lines of a kind
# mirror each other, and the two kinds mirror each other about the card's middle
nav_ = f'fill="none" stroke="{NAVY}" stroke-width="{f2(SWB)}" stroke-linejoin="miter"'


def feed(n_, xb_):
    """The line from the foot of the source n_ to code's box at xb_ (each run's ink is marked, so no word may stand on it)."""
    cx_ = SCX[n_]
    if abs(cx_ - xb_) < 1e-9:
        pts_ = [(cx_, YS1), (cx_, YCH - CHH / 2)]
    else:
        pts_ = [(cx_, YS1), (cx_, YCH), (xb_ + (CHW / 2) * (1 if cx_ > xb_ else -1), YCH)]
    for (a_, b_), (c_, d_) in zip(pts_, pts_[1:]):
        cv.box(min(a_, c_) - SWB / 2, min(b_, d_) - SWB / 2, max(a_, c_) + SWB / 2, max(b_, d_) + SWB / 2, f'b source line {n_}', 'mark')
    return '<path d="M' + ' L'.join(f'{f2(a_)},{f2(b_)}' for a_, b_ in pts_) + f'" {nav_}/>'


for k_, xb_ in (('enzyme', XEC), ('substrate', XSC)):
    src_ += [feed(n_, xb_) for n_ in SRC[k_]]
g('b sources', src_)
# code's box where each kind's lines meet: a's Convert box, small (code's fill, code's outline, the sign in ink)
code_ = []
for k_, xb_ in (('enzyme', XEC), ('substrate', XSC)):
    code_.append(cv.rect(xb_ - CHW / 2, YCH - CHH / 2, CHW, CHH, FILL['code'], EDGEC['code'], SWB, RX, mark=f'b sources code box {k_}'))
    code_.append(ico('code', xb_, YCH, CSIGN, f'b sources sign {k_}'))
g('b sources code', code_)
# ONE arrow from each box onto the card, on the middle of its cell: navy, the figure's shaft and head
g('b sources arrows', [cv.arrow([(x_, YCH + CHH / 2), (x_, CARD_TOP)], fill=NAVY, what=f'arrow sources to record {k_}')
                       for k_, x_ in (('enzyme', XEC), ('substrate', XSC))])
assert min(SX.values()) >= GX0 + wid('b', LETTER, True) + wid('\xa0\xa0From papers to values', T7, True) + 12.0, \
    'the sources stand clear of the panel\'s title'
assert max(SX[n_] + SW_ for n_ in SX) <= BX[1] + CARD_W + 1e-9 and min(SX.values()) >= BX[1] - 1e-9, 'the row no wider than the card'
# ---- the values: the catalogue's cylinder (a's CatLog: its width, its lid, its name); the count; what CatLog keeps apart
YCY0, YCY1 = YI - OBJ_H / 2 + CAT_SW / 2, YI + OBJ_H / 2 - CAT_SW / 2
YCN = YCY0 + CYL_RY + (YCY1 - YCY0) / 2 + 0.716 * TT / 2   # its name: the capitals centred in the body, as a's rule had it
cv.holder('b store', OX[2] - CYL_W / 2, YCY0 + 2 * CYL_RY, CYL_W, YCY1 - YCY0 - 3 * CYL_RY, 1.0)
g('b store', store(OX[2] - CYL_W / 2, OX[2] + CYL_W / 2, YCY0, YCY1, CYL_RY, CAT_TINT, CAT_TINT, GREEN, CAT_SW) +
  [cv.text(OX[2], YCN, 'CatLog', TT, 'middle', 'bold', fill=GREEN_TXT, inside='b store'),
   cv.rich(TX[2], YB1, CNT[2], T7, fill=TXT, inside='b row', what='b store count'),
   cv.rich(TX[2], YB2, KP1, T55, fill=TXT, inside='b row', what='b store kept 1'),
   cv.rich(TX[2], YB3, KP2, T55, fill=TXT, inside='b row', what='b store kept 2')])
# ---- the two arrows: from the papers' words onto the record, from the record's right edge onto the cylinder's side
AX = [(BX[0] + BWD[0] + AGAP, BX[1] + ALAND[0]), (BX[1] + CARD_W, BX[2] + ALAND[1])]   # M2: the second leaves the card's right edge
assert all(abs(x1_ - x0_ - AL) < 1e-9 for x0_, x1_ in AX), 'the two arrows one length'
g('b arrows', [cv.arrow([(AX[k][0], YI), (AX[k][1], YI)], what=f'arrow b {k}') for k in (0, 1)])
# ---- the trail: every value keeps the line of the paper it was printed in. One dashed line of the frame's make (the
# neutral grey, the outlines' 0.5 pt, 2 pt on and about 1.5 off) from the cylinder's foot, back under the row, up to the
# front page of the pile, where the figure's arrowhead ends on the page's lower edge. One path, so the dashes run round
# the two corners; the gap is tuned (within 0.1 pt of 1.5) so that the line starts and ends with a whole dash
XT0, XT1 = OX[2], XPF                      # down from the cylinder's foot; up into the front page
YT0, YT1 = YI + OBJ_H / 2, YI + OBJ_H / 2  # the cylinder's lowest point; the front page's lower edge
TLEN = (YTR - YT0) + (XT0 - XT1) + (YTR - YT1 - HL)
TN = round((TLEN - DASH) / (DASH + DGAP))
TGAP_ = (TLEN - (TN + 1) * DASH) / TN
assert abs(TGAP_ - DGAP) <= 0.1 and YTR - YT1 - HL >= 2 * DASH, (TGAP_, 'the trail ends in whole dashes')
trail = [f'<path d="M{f2(XT0)},{f2(YT0)} L{f2(XT0)},{f2(YTR)} L{f2(XT1)},{f2(YTR)} L{f2(XT1)},{f2(YT1 + HL)}" fill="none" '
         f'stroke="{GREY}" stroke-width="{f2(SWB)}" stroke-dasharray="{f2(DASH)} {TGAP_:.3f}"/>',
         f'<path d="M{f2(XT1)},{f2(YT1)} L{f2(XT1 - HW / 2)},{f2(YT1 + HL)} L{f2(XT1 + HW / 2)},{f2(YT1 + HL)} Z" fill="{GREY}"/>']
cv.box(XT0 - SWB / 2, YT0, XT0 + SWB / 2, YTR + SWB / 2, 'b trail down', 'mark')
cv.box(XT1, YTR - SWB / 2, XT0, YTR + SWB / 2, 'b trail run', 'mark')
cv.box(XT1 - HW / 2, YT1, XT1 + HW / 2, YTR + SWB / 2, 'b trail up', 'mark')
XTL = (XT0 + XT1) / 2                      # its words, in the middle of the run and LGAP over it (as c's label over its return)
# FINAL PASS (the record card's checker, 12 Nov, item (c); ARROWS item 7: under the card the words could read as the
# record's caption): centred on the part of the run left of the card, from the pile's front page to the card's left edge
XTL = (XT1 + BX[1]) / 2
trail.append(cv.text(XTL, YTR - SWB / 2 - TLG, TRAIL, T55, 'middle', fill=TXT, inside='b row', what='b trail label'))
g('b trail', trail)
assert XTL + wid(TRAIL, T55) / 2 <= BX[1] - 6.0 and XTL - wid(TRAIL, T55) / 2 >= XT1 + HW / 2 + 6.0, \
    'the trail\'s words on the run left of the card, 6 pt or more from the card and from the run\'s rise'
assert (YTR - SWB / 2 - TLG - 0.72 * T55) - (YC0 + CARD_H) >= 1.5 and \
    (YTR - SWB / 2 - TLG - 0.72 * T55) - (YB2 + 0.21 * T55) >= 6.0, 'the words under the objects\' foot line and clear of the papers\' words'

# ================================================================== c: co-learning, the loop; each step shows who acts
# N1 (11 Nov, the owner: "let us do it without examples"): the loop alone: its four steps in one row on the grid's four
# columns, the cyan arrows between them and the cyan return under them with 'the next error' on it.
# W1 (11 Nov, the owner on idea 2: "colearning should have some ai human visual maybe?"). Each box keeps its title; in
# place of its second line of words stands a small picture of who acts there, built from three glyphs of one family and
# one size (12 pt): the person (tan, as a's reviewer), the agent (a plain robot head, mint, in the agents' outline
# colour) and code's sign (the sign of a's Convert box). The picture stands the same way in all four boxes: at the
# right end of the title's line (W1 check, below). Errors found: a person and an agent, side by side. People write a rule: a person,
# a plus sign, an agent. Affected papers are read again: an agent and code's sign, side by side. Checked both ways: a
# person and an agent with a two-way arrow between them. The four lines of words ('by people and agents', 'with an
# agent', 'and code re-checks every value', 'by people and agents') left the figure; the legend says what they said.
# The letter is c (the panel of rules is gone), so the groups are c's.
D_CASE = False                             # N1: the loop alone
YLC = BB + 14.8
CT = YLC - 8.0                             # the panel's top (for the size print)
D_TITLE = 'Co-learning'
g('panel letter c', cv.panel_letter(GX0, YLC, 'c', D_TITLE))
# W1 check (11 Nov; the owner dislikes empty space in boxes): with the picture under its name at the left end, each box
# of 41 mm was mostly empty. Each step is now a strip one line tall: its name at the left, its picture at the right end
# of the same line, nothing under them. The four strips are of one make (one height, the same inset at both ends, the
# same white between name and picture), so each is as wide as its own name and picture need: on four equal columns the
# longest name ('Affected papers are read again', 102 pt in a column of 117) leaves no room for a picture on its line.
# The row still runs from the grid's left edge to its right, the arrows between the strips are one gutter long as
# before, and the glyphs are 12 pt (were 11), so that they read at half size.
YD0 = YLC + TGAP                           # the steps' tops, 5.5 pt under the title (as b's objects)
PICS = 12.0                                # the glyphs' size in a step's picture
HD = 0.83 * PICS + ISW + 2 * 3.6           # a step's height: the glyphs' ink (0.83 of their size) and 3.6 pt of white over and under it
YDM = YD0 + HD / 2                         # the strips' middle line: names' capitals, pictures and arrows are centred on it
YDT = YDM + 0.716 * TT / 2                 # a step's name
YDP = YDM - 0.015 * PICS                   # the picture's line (the glyphs' ink is centred 0.015 of their size under it)
# FINAL PASS (the final-pass list, items (a) and (h); the owner, 16 Nov: an agent drafted each rule after an error was
# found and an author approved it, which every rule's commit bears out): the second step reads 'A rule is written', with
# both icons, the person and the agent joined by the plus sign ('People write a rule' named people alone)
STEPS = {   # gid: (name, who acts, fill, edge)
    'c found': ('Errors found', ('person', None, 'agent'), RED_TINT, RED),
    'c written': ('A rule is written', ('person', 'plus', 'agent'), '#FFFFFF', LEARN),
    'c applied': ('Affected papers are read again', ('agent', None, 'code'), '#FFFFFF', NEUT),
    'c check': ('Checked both ways', ('person', 'both', 'agent'), '#FFFFFF', NEUT)}
PJOIN = {None: GSIDE, 'plus': 1.0, 'both': 1.52}   # what stands between two glyphs, as wide as actors() draws it (in the glyphs' size)
PICW = [sum(GW[e_] if e_ in GW else PJOIN[e_] for e_ in STEPS[gid][1]) * PICS for gid in STEPS]   # each picture's width
NAMEW = [wid(STEPS[gid][0], TT, True) for gid in STEPS]
NGAP = (GX1 - GX0 - 3 * G - sum(NAMEW) - sum(PICW) - 8 * BI) / 4   # the white between a name and its picture: the same in all four
assert NGAP >= 8.0, ('name and picture stand apart', NGAP)
WST = [2 * BI + NAMEW[k] + NGAP + PICW[k] for k in range(4)]   # the strips' widths
XST = [GX0 + sum(WST[:k]) + k * G for k in range(4)]           # their left edges, one gutter apart
assert abs(XST[3] + WST[3] - GX1) < 1e-9, "the row runs from the grid's left edge to its right"
for k, gid in enumerate(STEPS):
    name_, who_, fill_, edge_ = STEPS[gid]
    x, w_ = XST[k], WST[k]
    cv.holder(gid, x, YD0, w_, HD, 1.5)
    pic_, xe_ = actors(who_, x + w_ - BI - PICW[k], YDP, PICS, f'{gid} picture')
    assert abs(xe_ - (x + w_ - BI)) < 1e-9, (gid, 'the picture ends one inset before the strip\'s right edge')
    assert abs((x + w_ - BI - PICW[k]) - (x + BI + NAMEW[k]) - NGAP) < 1e-9, (gid, 'the same white between name and picture')
    g(gid, [cv.rect(x, YD0, w_, HD, fill_, edge_, SWB, RX),
            cv.text(x + BI, YDT, name_, TT, weight='bold', inside=gid)] + pic_)
# the loop, in the learning colour: step to step along the boxes' middle line, then back under the row to the first step
YLA = YDM
YRT = YD0 + HD + 9.8                       # the track's return, under the row, with room over it for its label
XR0, XR1 = XST[0] + WST[0] / 2, XST[3] + WST[3] / 2
lp = [cv.arrow([(XST[k] + WST[k], YLA), (XST[k + 1], YLA)], fill=LEARN, what=f'arrow c {k}') for k in range(3)]
lp.append(cv.arrow([(XR1, YD0 + HD), (XR1, YRT), (XR0, YRT), (XR0, YD0 + HD)], fill=LEARN, what='arrow c back'))
g('c loop', lp)
BACK = 'the next error'                    # what the track brings back, said on it
g('c back label', [cv.text((XR0 + XR1) / 2, YRT - SHAFT / 2 - LGAP, BACK, T55, 'middle', fill=TXT, what='c back label')])
CB = YRT + SHAFT / 2 + 0.3                 # the return's lower edge stays on the art
cv.H = CB



# ================================================================== checks
bad, esc_, clip = cv.overlaps(tol=-0.5), cv.escaped(), cv.clipped()   # every text 0.5 pt clear of text and marks
for name, v in (('closer than 0.5 pt', bad), ('outside their block', esc_), ('outside the page', clip)):
    if v:
        print(name, len(v))
        for x_ in v[:40]:
            print('  ', x_)
svg = cv.svg()
plain = re.sub(r'<[^>]+>', ' ', svg).replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
for banned in ('NAME', '21757926', 'EstF27', 'raw_value', 'raw_unit', 'read.md', 'units.py', 'catalog.jsonl',
               'rejected.jsonl', 'dbdiff', 'dbcheck', 'catlog-audit', 'catlog-batch', 'reader_model', 'pipeline_commit',
               '&lt;PMID&gt;', 'CatLog-27k', 'measurement', 'entries', ';'):
    assert banned not in plain, banned
# H6: no AI jargon on the figure (checker: in any case, and 'pipeline' too)
jargon_ = re.findall(r'(?i)model|prompt|\bLLM|token|hash|stamp|pipeline', plain)
assert not jargon_, jargon_
assert '<line' not in svg and 'text-decoration' not in svg


# each colour in the groups whose meaning it carries, and nowhere else
def _lum(h_):
    c_ = [int(h_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c_ = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c_]
    return 0.2126 * c_[0] + 0.7152 * c_[1] + 0.0722 * c_[2]


def _lstar(h_):
    y_ = _lum(h_)
    return 116 * (y_ ** (1 / 3) if y_ > 216 / 24389 else (24389 / 27 * y_ + 16) / 116) - 16


def _hue(h_):
    import colorsys
    return 360 * colorsys.rgb_to_hsv(*[int(h_[i:i + 2], 16) / 255 for i in (1, 3, 5)])[0]


grp_ = {re.sub(r'[^A-Za-z0-9_\-]', '', gid_.replace(' ', '_')): ''.join(its_) for gid_, its_ in cv.groups}   # as svg() ids
col_groups = lambda c_: sorted(k_ for k_, v_ in grp_.items() if c_.lower() in v_.lower())
BSTEPS = ('read', 'convert', 'verify', 'check')
# cyan, learning: a's co-learning box and its two arrows out, c's loop and the step where a rule is written
assert col_groups(LEARN) == ['a_learning', 'a_rules', 'c_loop', 'c_written'], col_groups(LEARN)
assert grp_['a_learning'].count(f'fill="{LEARN}"') == 2 and grp_['c_loop'].count(f'fill="{LEARN}"') == 4
# navy, the databases: a's card and its arrow, (R4) the box of the database named in each of b's cases and the cylinder
# beside 'cited by databases' in c; the tint, the card's strip. Navy is a line only: no word is set in it
# L2, M2: and the sources over b's record (six cylinders and their lines) with the two arrows that drop onto the card
assert col_groups(NAVY) == ['a_databases', 'a_databases_arrow', 'b_sources', 'b_sources_arrows'], col_groups(NAVY)
assert not re.search(r'<(text|tspan)[^>]*fill="%s"' % NAVY, svg), 'no navy words'
assert not any(k_.endswith('_database') for k_ in grp_)
assert col_groups(DB_TINT) == ['a_databases', 'b_sources'] and col_groups(OUT_GREY) == [], (col_groups(DB_TINT), col_groups(OUT_GREY))
# red, errors: a's errors and flag, c's first step
assert col_groups(RED) == ['a_errors', 'a_flag', 'c_found'], col_groups(RED)
assert col_groups(RED_TINT) == ['a_flag', 'c_found'], col_groups(RED_TINT)
assert grp_['a_flag'].count(f'fill="{RED_TINT}" stroke="{RED}"') == 1 and grp_['c_found'].count(f'fill="{RED_TINT}" stroke="{RED}"') == 1
# green, the catalogue: its tint fills CatLog, a cylinder in a (P1: its body and its lid) and in b (W1: the same make,
# a's width and lid), and the header strip of b's record (a record is CatLog's)
assert col_groups(CAT_TINT) == ['a_catalog', 'b_record', 'b_store'] and (
    grp_['a_catalog'].count(f'fill="{CAT_TINT}" stroke="{GREEN}" stroke-width="{f2(CAT_SW)}"') == 2
    and grp_['b_store'].count(f'fill="{CAT_TINT}" stroke="{GREEN}" stroke-width="{f2(CAT_SW)}"') == 2
    and grp_['b_record'].count(f'fill="{CAT_TINT}"') == 1 and GREEN not in grp_['b_record']), col_groups(CAT_TINT)
assert _lstar(CAT_TINT) - _lstar(FILL['agent']) >= 3.0 and CAT_TINT not in FILL.values()
# the catalogue's green as text: the name CatLog in its two cylinders (W1: b's cylinder is named, as a's)
assert col_groups(GREEN_TXT) == ['a_catalog', 'b_store'], col_groups(GREEN_TXT)
assert not re.search(r'(?i)#DC0000|#F39B7F', svg), 'one red only'
assert grp_['a_errors'].count(f'fill="{RED}"') == 4
red_text = [re.sub(r'<[^>]+>', '', t_) for t_ in re.findall(r'<text[^>]*fill="#E64B35"[^>]*>(.*?)</text>', svg)]
# a's two labels; then, card by card, what the database lists and the size of its error (Verify: the header's µ first)
assert red_text == ['errors', 'errors'] and not re.search(r'<tspan[^>]*fill="#E64B35"', svg), red_text   # N1: a's two labels only


def texts_of(gid_):
    """The words of a group's text elements, one string each (tspans joined, entities read)."""
    return [re.sub(r'<[^>]+>', '', t_).replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('\xa0', ' ')
            for t_ in re.findall(r'<text[^>]*>(.*?)</text>', grp_[gid_])]


assert '÷' not in plain and '≠' not in plain, 'no ÷ or ≠ on the figure'
assert 'kcat, Km and kcat/Km disagree' in texts_of('a_flag')
assert [t_ for t_ in texts_of('a_flag') if t_ != 'Flag'] == [w_ for *_, w_ in F['flag_items']], texts_of('a_flag')
# P1: a's CatLog is a cylinder (a body with one arc as its bottom edge, an ellipse as its lid, no box and no icon), in
# its box's footprint: the lid's top where the corrections arrow ends, the sides where the arrows from Check and into
# Flag end; its name alone in it, on the line of the steps' names
gc_ = grp_['a_catalog']
assert '<rect' not in gc_ and '<g>' not in gc_ and gc_.count('<path') == 1 and gc_.count('<ellipse') == 1 and texts_of('a_catalog') == ['CatLog'], gc_
assert f'<ellipse cx="{f2(ccx)}" cy="{f2(BY0 + CRY)}" rx="{f2((CX1 - CX0) / 2)}" ry="{f2(CRY)}"' in gc_ and \
    f'd="M{f2(CX0)},{f2(BY0 + CRY)} L{f2(CX0)},{f2(BY0 + BH - CRY)} A' in gc_ and f'L{f2(CX1)},{f2(BY0 + CRY)}"' in gc_, 'the footprint of the box it was'
NAME_RE = r'<text x="[\d.]+" y="([\d.]+)"[^>]*font-family="Arial-BoldMT" font-size="7.0"'
ya_names = set(re.findall(NAME_RE, ''.join(grp_[k_] for k_ in ('a_read', 'a_convert', 'a_verify', 'a_check', 'a_catalog', 'a_decide'))))
assert ya_names == {f2(YNAME)}, ("the four steps' names, CatLog's and (FINAL PASS: over its foot) Decide's on one line", ya_names)
# W1 check: Decide has no foot, so its icon, name and two lines are centred in its box (the foot's room kept white under
# them left a band of 19 pt against 9 pt over the icon); its name stands half a foot under the steps' names. FINAL PASS:
# Decide has a foot (the database check's rules), so its name is on the steps' line (asserted above)
yd_name = [float(y_) for y_ in re.findall(NAME_RE, grp_['a_decide'])]
assert len(yd_name) == 1 and abs(yd_name[0] - YNAME) < 0.011, ('Decide over its foot', yd_name, YNAME)
# P1: who does what, two lines under each step's name, and under Decide's (P1 check). W1: each step's count of rules
# is one more line, the foot of its box. FINAL PASS: Fig. 4a's 73 by step, Decide's foot the database check's 3
assert [texts_of(k_) for k_ in ('a_read', 'a_convert', 'a_verify', 'a_check', 'a_decide')] == [
    ['Read', 'an agent copies', 'each printed cell', '16 rules'], ['Convert', 'code computes', 'every value', '12 rules'],
    ['Verify', 'a second agent', 'finds it again', '7 rules'], ['Check', 'code checks', 'every value', '35 rules'],
    ['Decide', 'agents decide', 'from the paper', '3 rules']]
YFOOT = BY0 + BH - FOOTH                   # the feet's hairline
for s_, n_, name_, role_, x_b, w_b in (('read', 16, 'Read', 'agent', bx[0], BW), ('convert', 12, 'Convert', 'code', bx[1], BW),
                                       ('verify', 7, 'Verify', 'agent', bx[2], BW), ('check', 35, 'Check', 'code', bx[3], BW),
                                       ('decide', 3, 'Decide', 'agent', DX0, DW)):
    m_ = re.search(r'<text x="([\d.]+)" y="([\d.]+)" text-anchor="middle" font-family="ArialMT" font-size="6.5" fill="[^"]+">'
                   r'<tspan font-family="Arial-BoldMT">(\d+)</tspan> rules</text>', grp_['a_' + s_]) or \
        re.search(r'<text x="([\d.]+)" y="([\d.]+)" font-family="ArialMT" font-size="6.5" fill="[^"]+">'
                  r'<tspan font-family="Arial-BoldMT">(\d+)</tspan> rules</text>', grp_['a_' + s_])
    assert m_ and int(m_.group(3)) == n_ == F['rules_drawn'][name_] and abs(float(m_.group(2)) - (YFOOT + (FOOTH + 0.716 * T6) / 2)) < 0.01, (s_, m_)
    assert grp_['a_' + s_].count(f'stroke="{EDGEC[role_]}" stroke-width="{f2(HAIR)}"') == 1 and \
        f'd="M{f2(x_b + FOOTI)},{f2(YFOOT)} L{f2(x_b + w_b - FOOTI)},{f2(YFOOT)}"' in grp_['a_' + s_], (s_, 'the foot\'s hairline, in the box\'s outline colour')
assert HAIR not in (SWB, SHAFT) and BH == 71.0 and sum(F['rules_drawn'].values()) == F['rules_all'] == 73, 'the five feet add up to the 73'
# W1: a's Co-learning box: a person and an agent before the title, and the rules in its line (FINAL PASS: 73, the feet's sum)
assert texts_of('a_rules') == ['Co-learning', '73 rules in instructions and code'], texts_of('a_rules')
assert '<tspan font-family="Arial-BoldMT">73</tspan> rules in instructions and code</text>' in grp_['a_rules']
PERSON_RE = r'<circle [^>]*fill="%s" stroke="%s"' % (FILL['people'], INK)                    # a person's head, tan in ink
AGENT_RE = r'<rect [^>]*fill="%s" stroke="%s" stroke-width="%s"' % (FILL['agent'], EDGEC['agent'], f2(ISW))   # an agent's head
who_in = lambda k_: (len(re.findall(PERSON_RE, grp_[k_])), len(re.findall(AGENT_RE, grp_[k_])))
assert who_in('a_rules') == (1, 1), ('one person and one agent in a\'s Co-learning box', who_in('a_rules'))
# a (P1): the databases' cylinder holds the six names in two rows of three, in their order, with no box round a name; a
# body and a lid in the databases' navy line, the lid in their tint; no other figure is named on the figure
assert texts_of('a_databases') == ['Databases', ' · '.join(F['db_names'][:3]), ' · '.join(F['db_names'][3:])] \
    and 'Fig.' not in plain, texts_of('a_databases')
assert ' · '.join(texts_of('a_databases')[1:]).split(' · ') == F['db_names'] == ['BRENDA', 'SABIO-RK', 'OED', 'SKiD', 'UniProt', 'STRENDA DB']
gd_ = grp_['a_databases']
assert gd_.count(f'stroke="{NAVY}" stroke-width="{f2(SWB)}"') == 2 == gd_.count('stroke=') and gd_.count(DB_TINT) == 1 \
    and '<rect' not in gd_ and gd_.count('<path') == 1 and gd_.count(f'<ellipse cx="{f2(DBCX)}" cy="{f2(DBT + DRY)}" rx="{f2(DBW / 2)}" ry="{f2(CRY)}"') == 1, gd_
assert abs(DBX0 - FLX0) < 1e-9 and abs(DBX1 - FLX0 - FLW) < 1e-9 and DBY1 + SWB / 2 + 2.0 <= YRU - SHAFT / 2, 'over the Flag, on its two edges, the errors line under it'
# Q1: the databases' arrow ends on the Flag's top, at its middle; nothing navy touches Decide
assert [w_ for w_, *_ in cv.arrows if 'databases' in w_] == ['arrow databases to flag'] and FLX0 < XDB < FLX0 + FLW and XDB + HW / 2 + G <= DX0
# FINAL PASS (ARROWS items 1 and 2): the corrections run under the Flag, from Decide's foot to CatLog's base, with their
# word under the run; the right-hand 'errors' over its line at Decide's end; 'agent findings' under its arrow
assert texts_of('a_loop_labels') == ['agent', 'findings', 'rules', 'corrections'], texts_of('a_loop_labels')
assert re.search(r'<text x="%s" y="%s" text-anchor="middle"[^>]*>corrections</text>' % (f2(XCOR), f2(YCOR)), grp_['a_loop_labels'])
assert re.search(r'<text x="%s" y="%s" text-anchor="middle"[^>]*fill="%s">errors</text>' % (f2(XEL), f2(YEL), RED), grp_['a_errors'])
assert YCH_A > BY0 + BH and YCOR > YCH_A and YEL < YRU and DBX1 < XEL < dcx, 'the corrections under the row, the errors over their line'
# W1: no panel of rules: no strip, no title of its own, no zoom and no dashed edge; the four steps are written once in
# the figure, in a, and the counts stand there
assert not any(k_ in grp_ for k_ in ('b_read', 'b_convert', 'b_verify', 'b_check', 'b_outline', 'zoom_lines', 'b_note')) and \
    not any(k_.startswith('b_') and k_.endswith(('_database', '_error')) for k_ in grp_), sorted(grp_)
assert all(plain.split().count(n_) == 1 for n_ in ('Read', 'Convert', 'Verify', 'Check')), 'each step is named once'
assert 'co-learned rules' not in plain and sum(1 for t_ in re.findall(r'<text[^>]*>(.*?)</text>', svg)
                                               if re.sub(r'<[^>]+>', '', t_).endswith(' rules')) == 5, 'five counts of rules, in a (FINAL PASS: Decide\'s too)'
assert sorted(k_ for k_ in grp_ if k_.startswith('panel_letter')) == ['panel_letter_a', 'panel_letter_b', 'panel_letter_c'], 'three panels'
R1_ = F['r1']
# R5 checker: every dashed line is of one make (the neutral grey, the outlines' weight, 2 pt on and the gap within
# 0.1 pt of 1.5) and starts and ends with a whole dash. W1: five of them: the four sides of a's frame and b's trail
DASH_RE = r'stroke="%s" stroke-width="%s" stroke-dasharray="2 (1\.\d+)"' % (GREY, f2(SWB))
# FINAL PASS: the frame's sides are drawn as their dashes (short lines, no dash pattern) to keep the openings round the
# crossings, so the trail is the one dashed pattern left
assert all(abs(float(v_) - DGAP) <= 0.1 for v_ in re.findall(DASH_RE, svg)) and \
    svg.count('stroke-dasharray') == len(re.findall(DASH_RE, svg)) == 1, 'the trail, one make'
assert len(re.findall(DASH_RE, grp_['b_trail'])) == 1 and 'stroke-dasharray' not in grp_['a_reading_frame']
# R6: the dashed frame is the blind steps' alone (four dashed sides, its words centred at the top); 'After reading' is its
# words alone, on the Flag's left edge and on the same line; no grey band, so a grey area is a paper's print only
assert 'a_after_band' not in grp_ and 'a_after_frame' not in grp_ and BAND.lower() not in svg.lower(), 'no band, one frame'
gid_ = 'a_reading_frame'
assert '<rect' not in grp_[gid_] and grp_[gid_].count('<path') == 4 == \
    grp_[gid_].count(f'fill="none" stroke="{GREY}" stroke-width="{f2(SWB)}"/>'), grp_[gid_][:300]
# FINAL PASS (ARROWS item 6): each side's dashes are 2 pt (or a fragment of 0.8 pt or more beside an opening) with the
# side's tuned gap between them, except a 1-mm opening, or up to a dash more where a fragment went, round each crossing:
# the input lines and the line into Verify on the left side, Check's arrow into CatLog on the right; the top side has a
# whole dash centred under the rules head; and every corner is closed by two whole dashes
for side_, cuts_ in (('top', ()), ('right', (YM,)), ('bottom', ()), ('left', (YI1, YI2, YCH_A))):
    _p, iv_, gaps_ = FR_SIDES[side_]
    assert all(FRAG - 1e-6 <= q_ - p_ <= DASH + 1e-6 for p_, q_ in iv_), (side_, 'dashes of 2 pt, fragments of 0.8 pt or more')
    holes_ = [(q_, p2_) for (p_, q_), (p2_, q2_) in zip(iv_, iv_[1:]) if p2_ - q_ > max(gaps_) + 1e-6]
    assert len(holes_) == len(cuts_) and all(lo_ < c_ < hi_ and c_ - lo_ >= GAPC / 2 - 1e-6 and hi_ - c_ >= GAPC / 2 - 1e-6
                                             and hi_ - lo_ <= GAPC + 2 * (FRAG + max(gaps_)) + 1e-6 for (lo_, hi_), c_ in zip(holes_, cuts_)), \
        (side_, 'one opening of about 1 mm round each crossing, and none elsewhere', holes_, cuts_)
    a_s, b_s = (FX0 - _e, FX1 + _e) if side_ in ('top', 'bottom') else (YT - _e, YB + _e)
    assert abs(iv_[0][0] - a_s) < 1e-6 and abs(iv_[0][1] - iv_[0][0] - DASH) < 1e-6 and abs(iv_[-1][1] - b_s) < 1e-6 \
        and abs(iv_[-1][1] - iv_[-1][0] - DASH) < 1e-6, (side_, 'a whole dash at each corner')
assert any(abs((p_ + q_) / 2 - XRU) < 1e-6 and abs(q_ - p_ - DASH) < 1e-6 for p_, q_ in FR_SIDES['top'][1]), 'a whole dash under the rules head'
assert XBUS < FX0 < bx[0] and IX + 6.0 < FX0 and FX1 < CX0, 'the four lines that cross the frame: two inputs and the line into Verify on the left, Check\'s arrow on the right'
assert texts_of(gid_) == ['Blind to databases and reviews'] and 'text-anchor="middle"' in grp_[gid_]
assert texts_of('a_after_label') == [ALAB] and 'text-anchor' not in grp_['a_after_label'] and '<path' not in grp_['a_after_label']
ya_ = set(re.findall(r'<text x="[\d.]+" y="([\d.]+)"', grp_['a_reading_frame'] + grp_['a_after_label']))
assert len(ya_) == 1 and XAL == FLX0, ('the two stages\' words on one line', ya_)
assert ALAB == 'After reading' and XAL + wid(ALAB, T55) + 6.0 <= XDB - SHAFT / 2, 'the words clear the databases\' arrow (FINAL PASS: no other line runs over the Flag now)'
assert all(c_.lower() in ('#ffffff', PLATE.lower()) or c_.upper() in (FILL['agent'], FILL['code'], FILL['people'], CAT_TINT, RED_TINT, DB_TINT,
                                                                   INK, GREY, RED, NAVY, LEARN, EDGEC['code'], EDGEC['agent'], GREEN_TXT)
           for c_ in set(re.findall(r'fill="(#[0-9A-Fa-f]{6})"', re.sub(r'<text.*?</text>', '', svg)))), 'the fills: who acts, the catalogue, errors, the databases, print (W1: the agent glyph\'s eyes in the agents\' outline colour)'
assert len(re.findall(r'<(?!text|tspan)[a-z]+[^>]*fill="%s"' % GREEN_TXT, svg)) == 0, 'the stored green fills no mark (N1: no record, no residue dot)'
# b (W1): three objects in one row, one height, each with its count (7 pt, bold with its noun) and its side facts beside
# it; no box, no title inside, no hairline. No step is drawn in b (the steps are a's)
assert texts_of('b_papers') == [f"{F['read_by_ck']} papers read so far", f"{F['unread']} kept unread for the test"], texts_of('b_papers')   # FINAL PASS: no 'a later'
assert not re.search(r'held\s+out', plain), "the art's padlock line is not 'held out': the legend's 369 held out include 26 papers read before the lock"
assert not any(n_ in plain for n_ in (F['cited'], F['searched'])), 'Q2: the pool of papers is the legend\'s, not the figure\'s'
assert (F['cited'], F['searched']) == ('44,407', '30,814') and F['unread'] == f"{F['ck']['test_unread']:,}"
assert texts_of('b_record') == ['kcat', 'Km', 'kcat/Km', f"{F['records']} records", f"from {F['papers']} of them"] and \
    FROM == f"from {F['ck']['papers_with_values']:,} of them", texts_of('b_record')
assert texts_of('b_store') == ['CatLog', f"{F['values']} values", f"+ {F['nd']['n']} printed as not detected",
                               f"+ {F['lt']['n']} only as < x or > x"], texts_of('b_store')
assert texts_of('b_trail') == ['each value traced to its printed line'] == [TRAIL] and plain.count('traced to its printed line') == 1
assert texts_of('b_arrows') == [] and 'with values' not in plain, 'no words on the arrows (the papers with values stand under the records)'
# W1 counts: what is drawn is what writing/fig1_v8/ref/catalogue_counts.json holds for its checkpoint (facts() checked
# the file against the commit); no count is written here. FINAL PASS: the freeze's file (F['ck']), checked against its tag
assert (F['read_by_ck'], F['records'], F['values'], F['papers'], F['nd']['n'], F['lt']['n']) == \
    tuple(f"{F['ck'][k_]:,}" for k_ in ('papers_read', 'records', 'values', 'papers_with_values', 'not_detected', 'limits'))
# each count and its noun bold, 7 pt, on one line across the three objects; the side facts regular, 6.5 pt
assert f'<tspan font-family="Arial-BoldMT">{F["values"]}\xa0values</tspan>' in grp_['b_store'], 'the count of values bold'
assert f'<tspan font-family="Arial-BoldMT">{F["read_by_ck"]}\xa0papers</tspan>' in grp_['b_papers'] and \
    f'<tspan font-family="Arial-BoldMT">{F["records"]}\xa0records</tspan>' in grp_['b_record'], 'the counts of papers and records bold'
assert [grp_[k_].count('Arial-BoldMT') for k_ in ('b_papers', 'b_record', 'b_store', 'b_arrows', 'b_trail')] == [1, 1, 2, 0, 0], \
    'three counts and the catalogue\'s name in bold, nothing else'
yc7_ = [re.findall(r'<text x="[\d.]+" y="([\d.]+)" font-family="ArialMT" font-size="7.0"', grp_[k_]) for k_ in ('b_papers', 'b_record', 'b_store')]
# M2: the papers' and the values' counts on one line beside their objects; the records' count in the card's header,
# its capitals centred in it, and the papers the records come from after it on the same line
assert yc7_ == [[f2(YB1)], [f2(YC0 + HEAD_Y)], [f2(YB1)]], ('the counts 7 pt: two on one line, the records\' in the header', yc7_)
assert all(grp_[k_].count(f'y="{f2(YB2)}" font-family="ArialMT" font-size="6.5"') == 1 for k_ in ('b_papers', 'b_store')) and \
    grp_['b_record'].count(f'y="{f2(YC0 + HEAD_Y)}" font-family="ArialMT" font-size="6.5"') == 1 and \
    [grp_[k_].count(f'y="{f2(YB3)}"') for k_ in ('b_papers', 'b_record', 'b_store')] == [0, 0, 1], 'the side facts on one line, the values\' second under it'
assert abs((YC0 + HEAD_Y - 0.716 * T7 / 2) - (YC0 + CARD_HEAD / 2)) < 1e-9 and \
    HEAD_W + 2 * (1.0 + HW / 2) <= XSC - XEC, 'the count and its papers in the header, centred between the two arrows'
assert abs((YB1 - 0.716 * T7 / 2 + YB2 - 0.716 * T55 / 2) / 2 - YI) < 1e-9, "counts and side facts centred on the objects' middle"
assert abs(YB3 - (YI + OBJ_H / 2)) <= 0.5, "the values' second side fact stands on the cylinder's foot (within half a point)"
assert (not any(f'stroke="{EDGEC[r_]}"' in grp_[k_] for r_ in ('agent', 'code') for k_ in ('b_papers', 'b_record', 'b_store'))
        and not any(w_.startswith('b store arrow') for w_, *_ in cv.arrows)
        and not any(n_ in ' '.join(texts_of('b_store') + texts_of('b_papers') + texts_of('b_record')) for n_ in ('Read', 'Convert', 'Verify', 'Check'))), \
    "P1: no step tiles, names or arrows in b"
# W1: CatLog is a cylinder in a and in b, one make: a body and a lid in the catalogue's tint and its green 1-pt line, no
# seams; b's is as wide as a's, its lid as tall, and holds the name in the catalogue's green, 7 pt bold, as a's
gs_ = grp_['b_store']
assert '<rect' not in gs_ and '<g>' not in gs_ and gs_.count('<path') == 1 and gs_.count('<ellipse') == 1 and gs_.count('stroke=') == 2 \
    and not any('<ellipse' in grp_[k_] for k_ in ('b_papers', 'b_record', 'b_trail')), 'one cylinder in b, the catalogue\'s'
assert f'<ellipse cx="{f2(OX[2])}" cy="{f2(YCY0 + CYL_RY)}" rx="{f2(CYL_W / 2)}" ry="{f2(CYL_RY)}"' in gs_
assert abs(CYL_W - (CX1 - CX0)) < 1e-9 and CYL_RY == CRY and abs(YCY1 - YCY0 + CAT_SW - OBJ_H) < 1e-9, "as wide as a's CatLog, the lid as tall, 31.5 pt with its line"
assert re.search(r'<text x="%s" y="%s" text-anchor="middle" font-family="Arial-BoldMT" font-size="7.0" fill="%s">CatLog</text>'
                 % (f2(OX[2]), f2(YCN), GREEN_TXT), gs_) and \
    re.search(r'text-anchor="middle" font-family="Arial-BoldMT" font-size="7.0" fill="%s">CatLog</text>' % GREEN_TXT, grp_['a_catalog']), 'the name as in a'
assert abs((YCN - 0.716 * TT / 2) - (YCY0 + CYL_RY + (YCY1 - YCY0) / 2)) < 1e-9 and YCN - 0.716 * TT >= YCY0 + 2 * CYL_RY + 2.0, "the name in the middle of the body, under the lid"
# the pile and the record are ink on white in the icons' weight; the record: one card with the boxes' corners, a header
# strip in the catalogue's tint and three rows, kcat, Km and kcat/Km in the kinetics type (italic letter, subscript), nothing else
for k_, ok_, sw_ in (('b_papers', {'#FFFFFF', 'none', INK}, {(INK, f2(ISW))}),
                     ('b_record', {'#FFFFFF', 'none', CAT_TINT}, {(INK, f2(ISW)), (INK, f2(HAIR))})):   # M2: the cells' hairlines
    assert set(re.findall(r'stroke="(#[0-9A-Fa-f]{6})" stroke-width="([\d.]+)"', grp_[k_])) == sw_ and \
        set(re.findall(r'<(?:path|rect)[^>]* fill="(#[0-9A-Fa-f]{6}|none)"', grp_[k_])) <= ok_, k_
assert grp_['b_papers'].count(' Z" fill="#FFFFFF"') == 4, 'three pages and the padlock\'s page'
gr_ = grp_['b_record']
assert gr_.count('<rect') == 2 and gr_.count('<path') == 4 and gr_.count('<text') == 5 and '<circle' not in gr_ and '<g>' not in gr_, \
    'one card (its white, its outline), the header strip and its line, (M2) two hairlines between its three cells, three rows and the header\'s two texts'
# M2: a hairline on each side of the values' cell, from the header's line to the card's foot: the enzyme's picture and
# sequence left of the first, the substrate's drawing right of the second
assert all(f'<path d="M{f2(x_)},{f2(YCL)} L{f2(x_)},{f2(YC0 + CARD_H)}" fill="none" stroke="{INK}" stroke-width="{f2(HAIR)}"/>' in gr_ for x_ in XC[1:3]) \
    and gr_.count(f'stroke-width="{f2(HAIR)}"') == 2 and XSQ + SEQ_W + EGAP <= XC[1] + 1e-9 and XC[2] + 4.0 <= XMO and XMO + MOLW + 4.0 <= XC[3], \
    'hairlines part the enzyme, the values and the substrate'
assert abs(XC[1] - XC[0] - (XC[3] - XC[2])) < 1e-9 and abs((XC[1] + XC[2]) / 2 - (BX[1] + CARD_W / 2)) < 1e-9, 'the card mirrors about its middle'
assert ROWS == ['kcat', 'Km', 'kcat/Km'] and gr_.count('<tspan font-family="Arial-ItalicMT">') == 4 and gr_.count('font-size="5.5"') == 4, 'the kinetics type'
assert not re.search(r'\d', ''.join(texts_of('b_record')[:3])), 'no value in the record'
assert f'<rect x="{f2(BX[1])}" y="{f2(YC0)}" width="{f2(CARD_W)}" height="{f2(CARD_H)}" rx="{f2(RX)}" fill="#FFFFFF"' in gr_
assert abs(OW[0] - (PILE_PW + 2 * PILE_D)) < 1e-9 and 26.0 <= PILE_PH + 2 * PILE_D <= 31.5 and CARD_H == 40.5 and CARD_W <= 215.0, 'the objects\' sizes'
# no box, hairline, band or title inside: the groups hold no neutral line but the trail's
assert all(RULE not in grp_[k_] and NEUT not in grp_[k_] for k_ in ('b_papers', 'b_record', 'b_store', 'b_arrows')) and \
    grp_['b_papers'].count('<rect') == 1 and not any(t_ in plain.split() for t_ in ('Papers',)), 'no frame, hairline or band in b'
# the row from the grid's left edge to its right; the two arrows one length, level with the objects' middles
assert abs(BX[0] - GX0) < 1e-9 and abs(TX[2] + TW[2] - GX1) < 1e-9, "from the grid's left edge to its right"
ab_ = [(n_, hl_) for w_, n_, hl_ in cv.arrows if w_.startswith('arrow b ')]
assert len(ab_) == 2 and abs(ab_[0][0] - ab_[1][0]) < 1e-9 and ab_[0][1] == HL, 'two arrows of one length, the figure\'s head'
# the heads end on outlines, as the figure's other arrows: the first on the record's left line, at its middle; the second
# on the cylinder's straight side; each arrow starts AGAP after the words before it
assert abs(AX[0][1] - BX[1]) < 1e-9 and abs(YI - YCM) < 1e-9, 'the first head on the record, on its cells\' middle line'
assert f'<path d="M{f2(AX[1][1])},{f2(YCY0 + CYL_RY)} L{f2(AX[1][1])},' in gs_ and \
    YCY0 + CYL_RY + HW / 2 <= YI <= YCY1 - CYL_RY - HW / 2, "the second head on the cylinder's straight side"
assert abs(AX[0][0] - (TX[0] + TW[0] + AGAP)) < 1e-9 and abs(AX[1][0] - (BX[1] + CARD_W)) < 1e-9, \
    'the first arrow starts 6 pt after the papers\' words, the second on the card\'s right edge (M2: its count is in its header)'
assert abs(ab_[0][0] - AL) < 1e-9 and AL >= 9.9, 'as long as a\'s arrows between its steps, or longer'
assert [w_ for w_, *_ in cv.arrows if w_.startswith('arrow b ')] == ['arrow b 0', 'arrow b 1'], 'papers to records, records to values'
# the trail: one dashed line from the cylinder's foot, under the row, up to the front page of the pile, and one head in
# the same grey, the figure's size, its tip on the page's lower edge; its words over the run
gt_ = grp_['b_trail']
assert gt_.count('<path') == 2 and gt_.count('<text') == 1 and '<rect' not in gt_, gt_
assert f'<path d="M{f2(OX[2])},{f2(YI + OBJ_H / 2)} L{f2(OX[2])},{f2(YTR)} L{f2(XPF)},{f2(YTR)} L{f2(XPF)},{f2(YI + OBJ_H / 2 + HL)}" fill="none"' in gt_
assert f'<path d="M{f2(XPF)},{f2(YI + OBJ_H / 2)} L{f2(XPF - HW / 2)},{f2(YI + OBJ_H / 2 + HL)} L{f2(XPF + HW / 2)},{f2(YI + OBJ_H / 2 + HL)} Z" fill="{GREY}"/>' in gt_
assert abs(XPF - (BX[0] + PILE_PW / 2)) < 1e-9 and abs(XTL - (XPF + BX[1]) / 2) < 1e-9, 'the head on the front page\'s middle, the words in the middle of the run left of the card (FINAL PASS)'
assert (BB - BT) / MM <= 30.3, ('b at most 11 mm taller than W1\'s 19.3 mm', (BB - BT) / MM)
# no record of a paper and no code arrows
assert not any(k_.startswith('c_record') for k_ in grp_) and 'Linked by code' not in plain
# L2: what code adds to a record, shown and not written. One picture in the whole figure, the enzyme's, alone in its
# group: the prepared picture (its sha256 is the one facts() checked), placed by x, y, width and height in its own shape
import base64, hashlib
im_ = re.findall(r'<image x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" preserveAspectRatio="none" '
                 r'xlink:href="data:image/png;base64,([A-Za-z0-9+/=]+)"/>', svg)
assert len(im_) == 1 == svg.count('<image') and grp_['b_record_enzyme'].count('<') == 1 and grp_['b_record_enzyme'].startswith('<image '), len(im_)
assert hashlib.sha256(base64.b64decode(im_[0][4])).hexdigest() == STRUCT_SHA
assert abs(float(im_[0][2]) / float(im_[0][3]) - F['struct']['px'][0] / F['struct']['px'][1]) < 0.002, 'the picture keeps its shape'
# the substrate's drawing: RDKit's paths in ink (bonds stroked in the outlines' weight, atom labels filled), no text
gm_ = grp_['b_record_substrate']
assert '<text' not in gm_ and '<image' not in gm_ and gm_.count('<path') >= 12 and \
    set(re.findall(r'stroke="(#[0-9A-Fa-f]{6})" stroke-width="([\d.]+)"', gm_)) == {(INK, f2(SWB))} and \
    set(re.findall(r' fill="(#[0-9A-Fa-f]{6}|none)"', gm_)) == {'none', INK}, 'the drawing: ink paths only'
# both pictures inside their cells, 1.5 pt or more from the cells' lines; neither is named: no name of an enzyme, a
# substrate, an organism, an entry or a compound anywhere on the figure, and no number added to it
assert XC[0] + 4.0 <= XIM and XIM + IMW + 4.0 <= XSQ and YCL + 1.5 <= min(YIM, YMO) and \
    max(YIM + IMH, YMO + MOLH) <= YC0 + CARD_H - 1.5, 'the pictures in their cells'
assert abs((XIM - XC[0]) - (XSQ - XIM - IMW)) < 1e-9 and abs((XSQ - XIM - IMW) - (XC[1] - XSQ - SEQ_W)) < 1e-9 and \
    abs((XMO - XC[2]) - (XC[3] - XMO - MOLW)) < 1e-9, 'evenly spaced: one white before, between and after the enzyme\'s two things; the drawing centred'
# M2: one line of the record's stored sequence, set as ONE string in the text's 6.5 pt; behind its middle letter (the
# residue the paper's variant changes) a box in code's fill and outline. Nothing else in the group
gz_ = grp_['b_record_sequence']
assert [t_.replace(' ', '') for t_ in texts_of('b_record_sequence')] == [ST_['line']] == ['GNGALYK'] and texts_of('b_record_sequence') == [SEQ_S.replace('\xa0', ' ')] and gz_.count('<text') == 1 and gz_.count('<rect') == 1 and gz_.count('<') == 3 \
    and f'fill="{FILL["code"]}" stroke="{EDGEC["code"]}" stroke-width="{f2(SWB)}"' in gz_ and f'font-size="{T55}"' in gz_, gz_[:200]
xb_ = float(re.search(r'<rect x="([\d.]+)"', gz_).group(1))
assert abs(xb_ + SEQ_BOX[0] / 2 - (XSQ + wid(SEQ_S[:4], T55) + wid(ST_['line'][3], T55) / 2)) < 0.011 and ST_['col'] == 3 == len(ST_['line']) // 2, \
    'the box on the middle letter'
assert not any(re.search(w_, plain, re.I) for w_ in ('asparagin', 'P00805', 'CHEBI:', '58048', 'Escherichia', 'N248A', 'AlphaFold', 'wild type')), \
    'the pictures are not a worked example: nothing names them'
# the sources: six cylinders of a's make (a body and a lid in the navy line at the outlines' weight, the lid in the
# databases' tint, a white body), each with its name alone, in the text's face and colour; six lines; nothing else
gq_ = grp_['b_sources']
assert texts_of('b_sources') == SRC['enzyme'] + SRC['substrate'] == ['UniProt', 'PDB', 'NCBI', 'Rhea', 'ChEBI', 'PubChem'], texts_of('b_sources')
assert gq_.count('<ellipse') == 6 == gq_.count(f'fill="{DB_TINT}" stroke="{NAVY}" stroke-width="{f2(SWB)}"') and gq_.count('<path') == 12 \
    and gq_.count(f'fill="#FFFFFF" stroke="{NAVY}" stroke-width="{f2(SWB)}"') == 6 \
    and gq_.count(f'fill="none" stroke="{NAVY}" stroke-width="{f2(SWB)}" stroke-linejoin="miter"') == 6 \
    and gq_.count('stroke=') == 18 and '<rect' not in gq_ and gq_.count('<text') == 6, 'six cylinders, six names, six lines'
assert all(re.search(r'<text x="%s" y="%s" text-anchor="middle" font-family="ArialMT" font-size="5.5" fill="%s">%s</text>'
                     % (f2(SCX[n_]), f2(YSN), TXT, n_), gq_) for n_ in SCX) and T_S == 5.5, 'the names on one line, centred, 5.5 pt, black'
# M2: six cylinders of ONE size, the white between two of a kind 1 mm; each three exactly over its cell, so the row is
# as wide as the card; each kind's lines mirror about its middle cylinder, and the two kinds about the card's middle
el_ = re.findall(r'<ellipse cx="([\d.]+)" cy="([\d.]+)" rx="([\d.]+)" ry="([\d.]+)"', gq_)
assert len({(e_[1], e_[2], e_[3]) for e_ in el_}) == 1 and [e_[0] for e_ in el_] == [f2(SCX[n_]) for n_ in SNAMES], 'one size, one line'
assert SGAP >= MM - 0.01 and all(abs(SX[b_] - SX[a_] - SW_ - SGAP) < 1e-9 for k_ in SRC for a_, b_ in zip(SRC[k_], SRC[k_][1:])), 'equal gaps of 1 mm'
assert abs(SX['UniProt'] - BX[1]) < 1e-9 and abs(SX['PubChem'] + SW_ - BX[1] - CARD_W) < 1e-9 and abs(SX['NCBI'] + SW_ - XC[1]) < 1e-9 \
    and abs(SX['Rhea'] - XC[2]) < 1e-9, 'the row as wide as the card, nothing over the values\' cell'
for k_, xb_ in (('enzyme', XEC), ('substrate', XSC)):
    a_, m_, b_ = SRC[k_]
    assert abs(SCX[m_] - xb_) < 1e-9 and abs((xb_ - SCX[a_]) - (SCX[b_] - xb_)) < 1e-9, (k_, 'the box under the middle cylinder, the outer two equally far')
    assert f'<path d="M{f2(SCX[m_])},{f2(YS1)} L{f2(SCX[m_])},{f2(YCH - CHH / 2)}" ' in gq_ and \
        f'<path d="M{f2(SCX[a_])},{f2(YS1)} L{f2(SCX[a_])},{f2(YCH)} L{f2(xb_ - CHW / 2)},{f2(YCH)}" ' in gq_ and \
        f'<path d="M{f2(SCX[b_])},{f2(YS1)} L{f2(SCX[b_])},{f2(YCH)} L{f2(xb_ + CHW / 2)},{f2(YCH)}" ' in gq_, (k_, 'three lines, each from a foot onto the box')
assert abs((XEC + XSC) / 2 - (BX[1] + CARD_W / 2)) < 1e-9 and SLEG >= 1.5 * MM and YCH - YS1 >= 1.5 * MM, 'the two kinds mirror; no leg under 1.5 mm'
assert all(plain.split().count(n_) == (2 if n_ == 'UniProt' else 1) for n_ in SCX), 'each source named once (UniProt is also one of a\'s databases)'
# the six words are all the figure gains: the words of every other group of b are as they were (asserted above)
assert sorted(k_ for k_ in grp_ if k_.startswith('b_')) == ['b_arrows', 'b_papers', 'b_record', 'b_record_enzyme', 'b_record_sequence',
                                                             'b_record_substrate', 'b_sources', 'b_sources_arrows', 'b_sources_code',
                                                             'b_store', 'b_trail'], sorted(grp_)
assert sum(len(t_.split()) for k_ in ('b_record_enzyme', 'b_record_substrate', 'b_sources', 'b_sources_arrows', 'b_sources_code')
           for t_ in texts_of(k_)) == 6 and len(texts_of('b_record_sequence')) == 1 and len(SEQ_S.replace('\xa0', '')) == 7, \
    'added: the six names and one line of sequence letters (one text, seven letters)'
# code's box twice (a's Convert box, small: code's fill, code's outline in the outlines' weight, the boxes' corners) with
# code's sign in ink at the icons' weight; two navy arrows of the figure's make (0.75-pt shaft, the figure's head), each
# from its box's foot onto the card's top line, on the middle of its cell
gk_ = grp_['b_sources_code']
assert gk_.count('<g>') == 2 and gk_.count('<path') == 6 and gk_.count('<rect') == 2 and \
    set(re.findall(r'stroke="(#[0-9A-Fa-f]{6})" stroke-width="([\d.]+)"', gk_)) == {(INK, f2(ISW)), (EDGEC['code'], f2(SWB))} and \
    all(f'<rect x="{f2(x_ - CHW / 2)}" y="{f2(YCH - CHH / 2)}" width="{f2(CHW)}" height="{f2(CHH)}" rx="{f2(RX)}" fill="{FILL["code"]}" stroke="{EDGEC["code"]}"' in gk_
        for x_ in (XEC, XSC)), 'two boxes of code\'s fill, each with its sign'
assert 0.925 * CSIGN + 3.0 <= CHW and 0.8 * CSIGN + 2.5 <= CHH, 'the sign stands free in its box'
sa_ = [(w_, n_, hl_) for w_, n_, hl_ in cv.arrows if w_.startswith('arrow sources to record ')]
assert [w_ for w_, *_ in sa_] == ['arrow sources to record enzyme', 'arrow sources to record substrate'] and all(hl_ == HL and abs(n_ - SARR) < 1e-9 for _, n_, hl_ in sa_)
assert grp_['b_sources_arrows'].count(f'fill="{NAVY}"') == 2 == grp_['b_sources_arrows'].count('<path') and 'stroke' not in grp_['b_sources_arrows']
assert abs(XEC - (XC[0] + XC[1]) / 2) < 1e-9 and abs(XSC - (XC[2] + XC[3]) / 2) < 1e-9 and abs(XSC - (XMO + MOLW / 2)) < 1e-9 \
    and abs(CARD_TOP - YC0) < 1e-9, 'each arrow lands on the middle of the cell it feeds'
assert SARR == 9.0 and SHAFT == 0.75 and SARR - HL >= 5.0, 'the arrows: a visible shaft of the figure\'s weight'
# the sources stand between a's frame and the card, clear of the title and of the counts' lines
assert YS0 - YB >= 9.0 and abs(YS1 + SLEG - (YCH - CHH / 2)) < 1e-9 and abs(YCH + CHH / 2 + SARR - CARD_TOP) < 1e-9 and abs(CARD_TOP + CARD_HEAD + CELL_H / 2 - YI) < 1e-9
assert (BB - BT) / MM <= 54.75 / MM + 11.0, ('b grows by 11 mm at most (it was 54.75 pt, 19.3 mm)', (BB - BT) / MM)
assert not any(f'fill="{EDGEC["code"]}"' in v_ for v_ in grp_.values()), 'slate fills no mark'
# c: the loop's four steps: a title each and, in place of words, a picture of who acts
assert texts_of('panel_letter_c')[-1].strip() == D_TITLE
assert not D_CASE and D_TITLE == 'Co-learning' and texts_of('c_back_label') == ['the next error']   # N1: the loop alone
assert [texts_of(k_) for k_ in ('c_found', 'c_written', 'c_applied', 'c_check')] == [
    ['Errors found'], ['A rule is written'], ['Affected papers are read again'], ['Checked both ways']] and PLATE not in grp_['c_found'], \
    'each step its title alone: no case, no second line of words'
assert not any(t_ in plain for t_ in ('by people and agents', 'with an agent', 're-checks every value')), 'W1: the four lines of words left the figure'
# who acts, as drawn: (persons, agents) in each step's picture; code's sign with the agent where papers are read again;
# a plus sign where people write a rule with an agent; a two-way arrow where the result is checked both ways
assert [STEPS[k_][1] for k_ in STEPS] == [('person', None, 'agent'), ('person', 'plus', 'agent'), ('agent', None, 'code'), ('person', 'both', 'agent')]
assert [who_in(k_) for k_ in ('c_found', 'c_written', 'c_applied', 'c_check')] == [(1, 1), (1, 1), (0, 1), (1, 1)], 'who acts in each step'
CODE_RE = r'<g>(?:<path d="M[^"]*" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round"/>){3}</g>' % (INK, f2(ISW))
assert [len(re.findall(CODE_RE, grp_[k_])) for k_ in ('c_found', 'c_written', 'c_applied', 'c_check', 'a_convert')] == [0, 0, 1, 0, 1], "code's sign: a's Convert, and c's third step"
JOIN_RE = r'fill="none" stroke="%s" stroke-width="%s"/>' % (INK, f2(SHAFT))
assert [len(re.findall(JOIN_RE, grp_[k_])) for k_ in ('c_found', 'c_written', 'c_applied', 'c_check')] == [0, 1, 0, 1] and \
    grp_['c_check'].count(f' Z" fill="{INK}"/>') == 2 and grp_['c_written'].count(f' Z" fill="{INK}"/>') == 0, 'a plus sign in the second step, a two-way arrow in the fourth'
assert 10.0 <= PICS <= 12.0 and len({b_[1] for b_ in cv.boxes if ' picture ' in b_[4] and b_[4].endswith(('person', 'agent'))}) == 1, 'the pictures 10 to 12 pt, on one line'
assert sum(1 for w_, *_ in cv.arrows if w_.startswith('arrow c ')) == 4, 'three steps on, one back'
# W1 check: each step is a strip one line tall (no band under its name): one height, name and picture on one middle line,
# the picture ending one inset before the right edge, the same white between name and picture, the arrows one gutter long
rc_ = [re.search(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"', grp_[k_]).groups() for k_ in ('c_found', 'c_written', 'c_applied', 'c_check')]
assert len({(y_, h_) for _, y_, _, h_ in rc_}) == 1 and float(rc_[0][3]) == float(f2(HD)) <= 0.83 * PICS + ISW + 8.0, ('one height, one line tall', rc_)
assert abs(float(rc_[0][0]) - GX0) < 0.01 and abs(float(rc_[3][0]) + float(rc_[3][2]) - GX1) < 0.01 and \
    all(abs(float(rc_[k_ + 1][0]) - float(rc_[k_][0]) - float(rc_[k_][2]) - G) < 0.011 for k_ in range(3)), ('edge to edge, one gutter apart', rc_)
pb_ = {gid: [b_ for b_ in cv.boxes if b_[4].startswith(f'{gid} picture ')] for gid in STEPS}
PTOL = 0.15 * PICS                         # a glyph's box is its square, up to 0.14 of its size wider than its ink on each side
assert all(abs(max(b_[2] for b_ in pb_[gid]) - (XST[k_] + WST[k_] - BI)) <= PTOL and
           abs(min(b_[0] for b_ in pb_[gid]) - (XST[k_] + BI + NAMEW[k_] + NGAP)) <= PTOL for k_, gid in enumerate(STEPS)), 'each picture at the right end of its name\'s line'
assert abs((YDT - 0.716 * TT / 2) - YDM) < 1e-9 and abs(YLA - YDM) < 1e-9, 'names, pictures and arrows on the strips\' middle line'
assert 'reprint' not in plain and 'ND' not in plain.split() and '< 0.01' not in plain
# the learning colour reads on white (3:1, non-text contrast), apart from ink and the agents' mint edge
assert (1.05 / (_lum(LEARN) + 0.05)) >= 3.0 and abs(_lstar(LEARN) - _lstar(INK)) >= 35.0 \
    and abs(_hue(LEARN) - _hue(EDGEC['agent'])) >= 20.0 and abs(_hue(LEARN) - _hue(GREEN)) >= 20.0
assert (1.05 / (_lum(RED) + 0.05)) >= 3.0 and min(abs(_hue(RED) - _hue(c_)) for c_ in (LEARN, GREEN, EDGEC['agent'])) >= 60
# the catalogue's green carries words in b and navy thin lines: both read on white as text would (4.5:1)
assert (1.05 / (_lum(NAVY) + 0.05)) >= 4.5 and (1.05 / (_lum(GREEN_TXT) + 0.05)) >= 4.5
# R4: type and lines as a journal prints them. Text is black or one of the meaning colours; grey is for asides only
txt_fills = collections.Counter(re.findall(r'<text[^>]*? fill="(#[0-9A-Fa-f]{6})"', svg))
assert set(txt_fills) == {TXT, GREEN_TXT, RED} and TXT == INK == '#000000', txt_fills   # N1: no grey asides left
grey_words = [re.sub(r'<[^>]+>', '', t_) for t_ in re.findall(r'<text[^>]*fill="%s"[^>]*>(.*?)</text>' % GREY_TXT, svg)]
grey_words += re.findall(r'<tspan[^>]*fill="%s"[^>]*>(.*?)</tspan>' % GREY_TXT, svg)
assert grey_words == [], grey_words   # N1: the asides went with the examples (e.g., the note, the entry's length, the years)
# four line weights and no other: hairlines; outlines, icons and bonds; arrow shafts, red marks and the white rules; the
# CatLog boxes
sw_ = collections.Counter(re.findall(r'stroke-width="([\d.]+)"', svg))
assert set(sw_) == {f2(HAIR), f2(SWB), f2(SHAFT), f2(CAT_SW)} == {'0.35', '0.5', '0.75', '1'} and WRULE == SHAFT, sw_

# words per panel (as the style check counts them: tokens with a letter or digit)
words = collections.Counter()
for gid, its in cv.groups:
    p = 'b' if gid == 'zoom lines' else next((q for q in 'abcd' if gid.startswith((q + ' ', 'panel letter ' + q))), '-')
    for s in its:
        for t in re.findall(r'<text[^>]*>(.*?)</text>', s):
            t = re.sub(r'<[^>]+>', '', t).replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
            words[p] += sum(1 for w_ in t.split() if any(c.isalnum() for c in w_))

import cairosvg
cairosvg.svg2png(bytestring=svg.encode('utf-8'), write_to=os.path.join(HERE, OUT + '_preview.png'), output_width=2400)
# Until the owner calls the figure final only the PNG preview is written here; the SVG goes to FIG1_SVG_OUT, a path
# outside this folder, when that is set (for the style check)
if os.environ.get('FIG1_SVG_OUT'):
    # the check copy never goes into the repository
    # (checker: by its real path, so a link into the repository is refused too)
    assert not (os.path.realpath(os.environ['FIG1_SVG_OUT']) + os.sep).startswith(os.path.realpath(ROOT) + os.sep), \
        'the check copy stays out of the repository'
    open(os.environ['FIG1_SVG_OUT'], 'w', encoding='utf-8').write(svg)
print(dict(cv.stats, a_mm=round(A_BOTTOM / MM, 1), b_mm=round((BB - BT) / MM, 1), c_mm=round((CB - CT) / MM, 1),
           words=dict(words), words_all=sum(words.values())))

print('LAYOUT', json.dumps(dict(A_BOTTOM=A_BOTTOM, BT=BT, BB=BB, CT=CT, CB=CB, H=cv.H, B_ARROW=round(AL, 2), CARD=[round(CARD_W, 2), CARD_H],
                                CELLS=[round(v_, 2) for v_ in CELLW], SOURCE=[round(SW_, 2), round(YS1 - YS0, 2), SGAP], PICTURE=[round(IMW, 2), IMH],
                                DRAWING=[MOLW, MOLH], EGAP=round(EGAP, 2), SOURCES_TOP=round(YS0 - YB, 2), B_MM=round((BB - BT) / MM, 2))))   # T1: the panels' edges, for the crops
assert not (bad or esc_ or clip), 'fix the layout'
assert cv.H <= HMAX, cv.H / MM


# ================================================================== the legend draft: every number from F
def sp(s):
    """'^-1' and '^6' as Unicode superscripts (the legend is plain text)."""
    return re.sub(r'\^(-?\d+)', lambda m_: m_.group(1).translate(str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹')), s)


R_, H_, RP_ = F['rec'], F['hill'], F['reprint']
B2_ = F['b2']
R1L = F['r1']
RCL, LPL = R1L['record'], R1L['loop']
assert sp(R_['raw_value']) == '1.66 × 10⁶' and sp(R_['raw_unit']) == 'µM⁻¹ s⁻¹' and sp(R_['conv_unit']) == 'M⁻¹ s⁻¹'
L_ = F['link']
NUM_W = ['No', 'One', 'Two', 'Three', 'Four']
assert F['n_db'] == 3 and NUM_W[F['n_db']] == 'Three'
lst = lambda names: ', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else names[0]
# Q2 (the independent count check, 11 Nov): 443 of the papers the search found are cited by UniProt, and by no other
# database, so "that no database cited" was not exact; the legend says so, and the two sources hold 74,778 papers together
_src = collections.defaultdict(set)
for _r in csv.DictReader(open(os.path.join(ROOT, 'sources', 'db_values.tsv'), encoding='utf-8'), delimiter='\t'):
    _src[_r['pmid']].add(_r['source'])
_found = {l_.strip() for l_ in open(os.path.join(ROOT, 'sources', 'discovered_europepmc_20261014.txt'), encoding='utf-8')
          if l_.strip() and not l_.startswith('#')}
assert len(_found) == 30814 == int(F['searched'].replace(',', '')) and len(_src) == 44407 == int(F['cited'].replace(',', ''))
_both = _found & set(_src)
assert len(_both) == 443 and all(_src[p_] == {'UniProt'} for p_ in _both) and len(_found | set(_src)) == 74778, len(_both)
OVERLAP_UNIPROT = len(_both)
# M2 (11 Nov): the record's picture and the sources over it. One sentence says what the record's picture shows, which
# record it is and what the protein picture is (a predicted model shown as a picture of the enzyme: a record stores
# the entry and the sequence, no model); one says what the cylinders are, that code looks them up after a value is
# stored and that they give no kinetic value. Every name and number in them is a fact of facts() (F['asp'], F['link'],
# F['struct'], F['sources'], F['sources_when'])
assert (A_['enzyme'], A_['substrate'], L_['uniprot'], L_['mutation'], L_['pos'], L_['signal'], F['struct']['entry']) == \
    ('L-asparaginase II', 'L-asparagine', 'P00805', 'N248A', 270, 22, 'AF-' + L_['uniprot'] + '-F1')
ST_L = L_['stretch']
assert (ST_L['line'], ST_L['first'], ST_L['last'], ST_L['first'] + ST_L['col']) == ('GNGALYK', 267, 273, L_['pos']) and F['sources_when'] == 'after a value is stored'
REC_SENT = ("The record's two outer cells show what code looks up for every record beside its values, and adds where it "
            "finds it, drawn for one real record "
            f"({A_['enzyme']} of *Escherichia coli* with {A_['substrate']}): on the left the enzyme, as a picture and as residues "
            f"{ST_L['first']}–{ST_L['last']} of its stored sequence, on the right the substrate's stored structure; the protein "
            f"picture is a predicted model (the AlphaFold model of UniProt {L_['uniprot']}) shown only as a picture of the "
            "enzyme, since a record stores the UniProt entry and the sequence and no model, and the boxed letter and the dark "
            f"spheres mark residue {L_['pos']}, where code places the paper's variant {L_['mutation']} after counting the "
            f"{L_['signal']}-residue signal peptide.")
# FINAL PASS (the record card's checker, 12 Nov, items (e) and (f)): the PDB route as the code takes it (an entry the
# paper prints, or one whose primary citation is the paper: tools/sequences.py, asserted in facts_m2), and what the small
# code sign where each three lines meet is
SRC_SENT = (f"The small cylinders over the record are the databases that code looks up {F['sources_when']}: "
            f"{lst(F['sources']['enzyme'])} for the enzyme's entry and sequence (a PDB entry the paper prints or that "
            f"cites the paper, an NCBI record the paper prints) and {lst(F['sources']['substrate'])} for the substrate's "
            "structure (these three give most structures; the others come from compound entries of SABIO-RK and SKiD, "
            "from a peptide's residues written out, from a tool that reads a structure from a systematic name or, for a "
            "few, from the authors' own deposit in STRENDA DB); the small sign where each three meet, code's sign as in "
            "**a**'s Convert box, is the code that looks them up, and these look-ups supply no kinetic value (UniProt is "
            "also one of the six databases of **a**, to all of which the reading is blind).")
assert F['sources_most'] and 'SABIO-RK' in F['sources_rest'] and 'SKiD' in F['sources_rest'] and 'OPSIN' in F['sources_rest'] \
    and 'peptide' in F['sources_rest'] and 'deposited' in F['sources_rest'], F['sources_rest']
RD_, R4_ = F['rules_drawn'], F['rules_4a']
LEGEND = [
    '# Fig. 1 legend (final pass, 16 November): draft sentences',
    '',
    'Each bracket says where a sentence goes; the sentences are legend text as they stand.',
    '',
    '[after the panel descriptions]',
    # FINAL PASS: the counts are the paper's freezes (paper/evidence/catalog_freeze_20261116/catalogue_counts.json and
    # paper/evidence/human_review_freeze_20261116/numbers.json); the art states them once, the legend their source
    f"The counts in **b** are those of the catalogue as frozen for this paper on {F['ck_date']}: {F['read_by_ck']} papers "
    f"had been read, {F['papers']} of them with values, and CatLog held {F['values']} values in {F['records']} records. "
    f"Beside the cylinder, the two lines under the count give the constants a paper reports only as not detected ({F['nd']['n']}) and those it prints "
    f"only as an upper or lower limit, < *x* or > *x* ({F['lt']['n']}); CatLog keeps both apart from its values. People's "
    f"review in **a** is counted as frozen for this paper on {F['review_date']}: the {F['checked']} records people checked "
    f"against their papers come from {F['review_papers']} papers"
    # 'PubMed identifier' spelled out: the legend's own guard below ('no case in the legend') refuses the string 'PMID'
    + (f"; {F['no_paper']} more records, with no PubMed identifier or DOI, are not counted" if F['no_paper'] != '0' else '')
    + '.',
    '',
    '[a, the frame]',
    'The dashed frame in **a** holds the four steps that read blind to databases and reviews; Flag and Decide follow '
    "after reading. The foot of each step's box gives the number of rules that act in that step (Decide's, those of the "
    f"database check); the five add up to the {F['rules_all']} of the Co-learning box.",
    '',
    '[a, the flag]',
    "The flag's sources: a reviewer's rejection (checked against the paper, never obeyed as it stands); a printed "
    '*k*cat/*K*m that does not match the printed *k*cat and *K*m of the same record (its icon: a straight line from the '
    'origin, the printed *k*cat/*K*m as an initial slope, missing the rate curve that *k*cat and *K*m draw); the same '
    f"value printed in an older paper, so it may have been copied from there rather than measured; a random audit of "
    f"{F['audit_pct']}% of new values; and a value {F['db_fold']}-fold or "
    "more from a database's number for the same paper (its icon: two values on a log axis).",
    '',
    '[a, the databases]',
    f"The databases' numbers meet CatLog's values only after reading: where a value is {F['db_fold']}-fold or more from a "
    "database's number for the same paper it is flagged (the navy arrow), and an agent given both numbers decides from "
    "the paper which one it prints; it "
    "changes nothing itself (a value it finds wrong goes first into the next audit), and most such checks have found the "
    # FINAL PASS check: Fig. 3g draws these verdicts (Fig. 4 is co-learning)
    "database's number wrong (Fig. 3g).",
    '',
    '[a, the rules]',
    # FINAL PASS (the final-pass list, item (b)): no dating of the work from 7 October and no earlier system (one
    # CatLog); Fig. 4a's words for the 25 and its split of the 48
    f"The feet of the step boxes in **a** count CatLog's {F['rules_all']} rules by the step each acts in: "
    f"{RD_['Read']} in the reading agent's instructions, {RD_['Convert']} in the code that turns a paper into text and "
    f"converts its printed cells and units, {RD_['Verify']} in the verifying agent's instructions, {RD_['Check']} in the "
    # FINAL PASS check: Decide's 3 (DB1, DB3, PR17) are code and design of the database comparison, not the deciding
    # agents' instructions, so the legend names where they live, as it does for the other four feet
    f"rest of the code, which checks every value, and {RD_['Decide']} in the code of the database check after reading, "
    "drawn on Decide's foot: "
    "database values never become CatLog values, a condition a database words otherwise, such as a metal ion named in "
    "full, still matches, and code calls a database's number wrong only when the paper's own *k*cat and *K*m support "
    f"CatLog's. All {F['rules_all']}, each with the error it came from, are listed in Supplementary Table 4; "
    f"{R4_['known']} came from checking databases against papers and {F['rules_all'] - R4_['known']} were learned from "
    f"errors found by code checks ({R4_['code']}), checking agents ({R4_['agents']}), people with an agent "
    f"({R4_['with']}) and people ({R4_['people']}), as in Fig. 4a.",
    '',
    '[b]',
    f"The papers come from six databases ({', '.join(F['db_names'][:-1])} and {F['db_names'][-1]}), which cite "
    # FINAL PASS check: both Europe PMC searches (the frozen catalogue holds papers of each), the Km-only one in the Europe
    # PMC freeze's own words, 'new to CatLog'
    f"{F['cited']} papers for their values, and from two literature searches of Europe PMC, one for papers that mention "
    f"a *k*cat or turnover number together with a *K*m ({F['searched']} papers that the other five databases do not "
    f"cite; UniProt cites {OVERLAP_UNIPROT} of them) and one for papers that mention a *K*m with kinetic words but no "
    f"*k*cat ({F['searched_km']} more papers, new to CatLog). Nearly all the papers not yet read were waiting to be downloaded "
    # FINAL PASS (the final-pass list, item 4): the locked test has run; the padlock's papers are its held-out set
    f"or read. Of the {F['locked']} papers held out for the locked test, {F['unread']} had not been read into CatLog "
    f"(the padlock): only the test reads them; the other {F['locked_read']} had been read before they were held out. "
    "**b** draws three objects: a pile of pages for the papers read, one record for the records "
    "made from them (its header counts them; the three rows in its middle name the values a record can hold, *k*cat, "
    "*K*m and *k*cat/*K*m) and a green "
    "cylinder for the values, which is the CatLog of **a**. The dashed grey arrow from the cylinder back to the pages "
    "is the trail: each value is stored with the line of the paper it was printed in. "
    + REC_SENT + ' ' + SRC_SENT,
    '',
    '[c]',
    # FINAL PASS (the final-pass list, items (a) and (h); the owner, 16 Nov): an agent drafts each rule and an author
    # approves it; code checks found errors too (Fig. 4a)
    '**c**, the co-learning loop. An error found by a person, an agent or code becomes a rule: an agent drafts it and an '
    "author approves it (A rule is written), in the agents' instructions or in code; the papers the rule affects are "
    "read again and code re-checks every stored value; the result is checked both ways (people review the agents' "
    'records, and agents re-read values people approved); and the next error starts the loop again. The small picture '
    "in each box shows who acts there: a person, an agent (the robot head) and code (its sign, as in **a**'s Convert "
    # FINAL PASS check: the first box draws a person and an agent (STEPS), while code checks found the errors behind 9
    # of the 48 learned rules (Fig. 4a); the art stays as approved and the legend says what it leaves out
    f"box); code's own checks, which found the errors behind {R4_['code']} rules (Fig. 4a), are not drawn in the first "
    'box. A plus sign joins the agent that drafts a rule and the person who approves it, and a two-way arrow stands '
    "between them where each checks the other. The same person and agent stand in **a**'s Co-learning box.",
    '',
    '[at the end: what the drawing leaves out]',
    'A record is one enzyme or variant, one substrate and one assay of one paper, with up to three values; each value '
    'is stored with its printed line, the agents that read and checked it, the instructions they followed and the '
    'version of the code. '
    "CatLog's agents are Claude models: Opus 5.5 read most values, Opus 5 read some (alone or after a switch within a "
    'run), and Sonnet 5.5 is the one retry for an agent that stops. The verifier is the same model in a fresh context: it '
    'finds each value in the paper itself, confirms, fixes or rejects it, and lists values the reader missed, which a '
    'third agent verifies. Agents are blind by instruction, and their logs are checked afterwards; the '
    # FINAL PASS (item (b)'s rule, one CatLog: writing/manuscript/BRIEF.md names "the earlier catalogue" among the words
    # to avoid): the files those agents opened were database values or values CatLog already held for the paper
    f"{F['blind']} papers whose agents had opened database values, or values CatLog already held for them, were read "
    'again blind. '
    'Trails have been written as values are stored only since 21 October 2026; for most values '
    'the trail was rebuilt from the agents\' logs. Values '
    'leave or change only through logged commands that keep the printed cell; refused values are kept with their '
    "reasons. Values keep the paper's qualifiers (apparent, approximate, per active site) as notes; *k*cat/*K*m is "
    'computed from *k*cat and *K*m only where the paper prints none, and is marked so. Page images exist only where the '
    'paper is a PDF, about half of the papers read; the rest came as publisher XML. Sweeps of the catalogue change a '
    'value only after independent agents have checked the change against the paper; in the sweeps for misprinted units '
    'and for maximal rates, at most one of three may refute it. Of the '
    f"{F['kinds_all']} kinds of error found, {F['rules_kinds']} became rules, {F['flagged_all']} are kept as printed with a "
    f"flag and {F['open_all']} are open.",
    '',
    '[colours]',
    'Fills show who acts: mint for agents, slate for code and tan for people (the reviewer in '
    "**a**'s flag, and the person and the agent in **a**'s Co-learning box and in **c** too). "
    'Green marks the catalogue: CatLog is a cylinder in **a** and in **b**, tinted and outlined in green, and the '
    "header of **b**'s record has its tint. "
    'Cyan marks learning: the co-learning box in **a** with the agent findings and rules that come out of it, and the '
    'loop in **c** with the step where a rule is written. Red marks errors: the flag in **a** and the first step in '
    '**c** are filled and outlined in it; the arrows that carry errors into co-learning in **a** and the suspect part '
    'of each flag icon are drawn in it. Navy marks the databases, always as a line: in **a** their cylinder, which '
    'holds the six names, and the arrow into the flag (their values meet CatLog\'s only after reading); in **b** the '
    'six small cylinders code asks for a record\'s enzyme and substrate, and their lines. Black arrows '
    'carry papers and what is read from them.',
]
# every number the legend gives is one the figure or the facts hold
assert (F['n_db'], F['blind'], F['kinds'], F['rules'], F['flagged'], F['open']) == (3, 303, 85, 71, 4, 10)
assert (F['kinds_all'], F['rules_kinds'], F['flagged_all'], F['open_all']) == (87, 73, 4, 10), 'FINAL PASS: Fig. 4\'s 87 kinds'
assert len(F['db_names']) == 6 and (F['cited'], F['searched']) == ('44,407', '30,814')
# W1 counts: the catalogue's counts and their date are those of writing/fig1_v8/ref/catalogue_counts.json (F['ck']; facts()
# checked the file against its commit); the legend writes none of them itself. FINAL PASS: the freeze's file
assert (F['unread'], F['locked'], F['locked_read']) == (f"{F['ck']['test_unread']:,}", f"{F['ck']['test_papers']:,}",
                                                        F['ck']['test_papers'] - F['ck']['test_unread'])
assert (F['read_by_ck'], F['papers'], F['values'], F['records'], F['nd']['n'], F['lt']['n']) == \
    tuple(f"{F['ck'][k_]:,}" for k_ in ('papers_read', 'papers_with_values', 'values', 'records', 'not_detected', 'limits'))
assert F['ck_date'].split()[0] == str(int(F['ck']['committed'][8:10])) and F['ck_date'].endswith(F['ck']['committed'][:4]) \
    and any(f"The counts in **b** are those of the catalogue as frozen for this paper on {F['ck_date']}: {F['read_by_ck']} papers"
            in s_ for s_ in LEGEND), 'the legend dates b\'s counts by the freeze\'s commit'
assert F['rules_n'] == {'Read': 16, 'Convert': 10, 'Verify': 7, 'Check': 35} and F['rules_b'] == 68 == sum(F['rules_n'].values())
assert any("16 in the reading agent's instructions, 12 in the code that turns a paper into text and converts its printed "
           "cells and units, 7 in the verifying agent's instructions, 35 in the rest of the code" in s_ and
           "3 in the code of the database check after reading, drawn on Decide's foot" in s_ and '25 came from checking '
           'databases against papers and 48 were learned from errors found by code checks (9), checking agents (13), people '
           'with an agent (21) and people (5)' in s_ for s_ in LEGEND), 'the rules as drawn and as Fig. 4a splits them'
# FINAL PASS check (16 Nov): the legend's figure numbers are the paper's as it stands (Fig. 3g the database verdicts,
# Fig. 4a the rules); code's checks are named where c's first box leaves them out; both Europe PMC searches are named
assert any("most such checks have found the database's number wrong (Fig. 3g)." in s_ for s_ in LEGEND) and \
    not any('(Fig. 4)' in s_ for s_ in LEGEND), 'the database verdicts are Fig. 3g'
assert list(STEPS)[0] == 'c found' and STEPS['c found'][:2] == ('Errors found', ('person', None, 'agent')) and \
    R4_['code'] == 9 and any("code's own checks, which found the errors behind 9 rules (Fig. 4a), are not drawn in the "
                             "first box" in s_ for s_ in LEGEND), 'the legend says what c\'s first box leaves out'
assert any(f"from two literature searches of Europe PMC, one for papers that mention a *k*cat or turnover number together "
           f"with a *K*m ({F['searched']} papers" in s_ and f"({F['searched_km']} more papers, new to CatLog)" in s_
           for s_ in LEGEND) and F['searched_km'] == '93,868', 'both searches'
assert not any(re.search(r'7 October|earlier system|earlier catalogue|carried over', s_) for s_ in LEGEND), 'FINAL PASS: item (b)'
assert not any(w_ in s_ for s_ in LEGEND for w_ in ('tick', 'deck', 'top card', '2.76E', '378C', 'Linked by code',
                                                    'Reading box', 'catalase'))
# no worked example: the figure draws no case, and the legend describes none. L2, M2: the record's pictures are of one
# real record, which the legend names once, in the one sentence about them, and nowhere else
assert not any(w_ in s_ for s_ in LEGEND for w_ in ('PMID', 'e.g.', '681.5', '0.09 mM', '622 s', 'The record drawn')), 'no case in the legend'
assert [sum(s_.count(w_) for s_ in LEGEND) for w_ in ('asparaginase', 'AlphaFold', 'P00805', 'N248A')] == [1, 1, 1, 1] and \
    all(w_ in REC_SENT for w_ in ('asparaginase', 'AlphaFold', 'P00805', 'N248A')) and REC_SENT.count('. ') == 0, 'the pictured record is named once, in one sentence'
assert sum(REC_SENT in s_ and SRC_SENT in s_ for s_ in LEGEND) == 1 and not any('shows only which values a record holds' in s_ for s_ in LEGEND)
# what the sources' sentence says is the code's: OPSIN is the name-to-structure tool of tools/structures.py
assert '   8. OPSIN systematic name' in txt('tools', 'structures.py') and 'printed PDB' in txt('tools', 'sequences.py')
assert 'PDB entries whose primary citation is this PMID' in txt('tools', 'sequences.py') and 'a PDB entry the paper prints or that cites the paper' in SRC_SENT
assert not D_CASE and PLATE.lower() not in svg.lower() and not re.search(r'\d', ''.join(texts_of('b_record')[:3])), 'no case, no grey plates, no value in the record drawn'
assert LEGEND[-1].startswith('Fills show who acts') and 'Cyan marks learning' in LEGEND[-1] and 'Red marks errors' in LEGEND[-1]
assert 'Navy marks the databases, always as a line' in LEGEND[-1]
assert any('The dashed frame in **a** holds the four steps that read blind' in s_ for s_ in LEGEND) and 'a_after_frame' not in grp_
assert 'A rule is written' in [s_[0] for s_ in STEPS.values()] and 'People write a rule' not in plain   # FINAL PASS
assert all(c_ in svg for c_ in (FILL['agent'], FILL['code'], FILL['people'], GREEN, LEARN, NAVY, RED, DB_TINT))
assert not any('≠' in s_ or '÷' in s_ for s_ in LEGEND)
# W1: b is three drawn objects and a trail, and the legend says what each is; no box of b is described; the legend
# keeps what the loop's four lines of words said, and says what its pictures are
assert any('a pile of pages for the papers read, one record for the records' in s_ and 'is the trail' in s_ for s_ in LEGEND) and \
    any('an agent drafts it and an author approves it (A rule is written)' in s_ and 'code re-checks every stored value' in s_
        and 'An error found by a person, an agent or code' in s_
        and 'The small picture in each box shows who acts' in s_ for s_ in LEGEND) and \
    any('The foot of each step' in s_ for s_ in LEGEND) and not any('**d**' in s_ for s_ in LEGEND) and \
    not any('CatLog box' in s_ or 'the box counts' in s_ or 'a box in **c**' in s_ for s_ in LEGEND), 'the legend follows c as drawn'
assert any(f"Of the {F['locked']} papers held out for the locked test, {F['unread']} had not been read into CatLog (the padlock)" in s_
           for s_ in LEGEND) and not any('later test' in s_ for s_ in LEGEND), 'FINAL PASS: item 4'
leg_ = '\n'.join(LEGEND) + '\n'
assert not re.search(r'\{[A-Za-z_]', leg_), 'every legend number filled in'
assert not re.search(r'(?i)prompt|\bLLM|token|hash|stamp|pipeline', leg_), 'no internal words in the legend'
open(os.path.join(HERE, OUT + '_legend_draft.md'), 'w', encoding='utf-8').write(leg_)
print('legend draft:', os.path.join(HERE, OUT + '_legend_draft.md'), len(re.findall(r'\w+', leg_)), 'words')
