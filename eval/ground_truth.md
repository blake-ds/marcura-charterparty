# Manual ground truth — every numbered clause in Part II

Built by reading every page of `voyage-charter-example.pdf` (pages 6–39) line by line, classifying each numbered clause as **kept** (substantive visible content), **heading-only** (title visible, body wholly struck — like *Essar Rider clause 18 CLINGAGE – NOT APPLICABLE FOR THIS CHARTER*), or **wholly struck** (title struck too — must drop).

The output JSON should match this exactly. Any divergence is a parser bug.

Legend:
- ✅ kept — clause has substantive visible body (with or without title), goes to output
- 🏷 heading-only — title visible, body fully struck, goes to output with `text=""`
- 💀 wholly struck — title + body all struck, must drop
- 🔀 anchor-less replacement — original clause struck wholesale but a bold replacement text exists without its own visible anchor; semantically belongs to this ordinal but parser can't reach it; documented as a known limitation

Total expected: **87 clauses** (38 SHELLVOY + 28 Additional + 21 Essar).

---

## SHELLVOY 5 (pages 6–17), ordinals 1..44, expected 38 kept

| Ord | Status | Title | Notes |
|----:|:------:|:------|:------|
| 1   | ✅ | Condition Of vessel | Y2K bold paragraph survives |
| 2   | ✅ | Cleanliness Of tanks | Original struck, bold replacement is the body |
| 3   | ✅ | Voyage | Struck *"in sufficient time…"* filtered between paragraphs |
| 4   | ✅ | Safe berth | Ends *"…in the giving of the order,"* — rest struck |
| 5   | ✅ | Freight | No edits |
| 6   | ✅ | Dues and other charges | *"and any taxes on freight whatsoever"* struck; bold *NO FREIGHT FAX…* kept |
| 7   | ✅ | Loading and discharging cargo | No edits |
| 8   | ✅ | Deadfreight | Bold *"HOWEVER IF VESSEL IS RESTRICTED…"* kept |
| 9   | ✅ | Shifting | No edits |
| 10  | ✅ | Charterers' failure to give orders | No edits |
| 11  | ✅ | Laydays/Termination | *noon* struck → *2359 HRS*; *4 days* struck → *48 RUNING HOURS …* |
| 12  | ✅ | Laytime | No edits |
| 13  | ✅ | Notice of readiness/Running time | *(ii)* struck, bold replacement *Recommence two hours…* kept; *(2)* same shape |
| 14  | ✅ | Suspension of time | Bold *"unless vessel ordered to a port or place where tug or pilot strike already exists…"* added |
| 15  | ✅ | Demurrage | *(3)* struck, bold replacement kept |
| 16  | ✅ | Vessel inspection | — |
| 17  | ✅ | Cargo inspection | — |
| 18  | ✅ | Cargo measurement | — |
| 19  | ✅ | Inert gas | — |
| 20  | ✅ | Crude oil washing | Struck original + bold replacement *"shall have the right to require the vessel to crude oil wash, concurrently with discharge…"* |
| 21  | 💀 | Over age insurance | DROP — wholly struck (title + body) |
| 22  | ✅ | Ice | — |
| 23  | ✅ | Quarantine | — |
| 24  | ✅ | Agency | *"of loading"* struck (small edit) |
| 25  | ✅ | Charterers' obligation at shallow draft port/Lightening in port | — |
| 26  | ✅ | Charterers' orders/Change of orders/Part cargo transhipment | — |
| 27  | 💀 | Heating of cargo | DROP — wholly struck |
| 28  | 🔀 | ETA | Original struck; bold replacement *MASTER TO GIVE ETA NOTICES AS REQUIRED IN CHARTERERS VOYAGE ORDERS* has no visible anchor — known parser limitation, content currently appended to clause 26's body |
| 29  | 💀 | Packed cargo | DROP — title and body both struck |
| 30  | ✅ | Subletting/Assignment | Bold *"And Charterers shall countersign all LOIs"* added |
| 31  | ✅ | Liberty | — |
| 32  | ✅ | Exceptions | Bold *"or The Hamburg Rules"* + *"unless The Hamburg Rules compulsorily apply in which case The Hamburg Rules."* added |
| 33  | ✅ | Bills of lading | — |
| 34  | ✅ | War risks | — |
| 35  | ✅ | Both to blame clause | — |
| 36  | ✅ | General average/New Jason Clause | Struck original + bold *"36. General average shall be payable according to the York/Antwerp Rules as amended 1974 AS AMENDED 1990 AND THEREAFTER…"* |
| 37  | ✅ | Clause paramount | Bold *"or The Hamburg Rules"* and *"(3) If there is governing legislation which applies the Hamburg rules…"* added |
| 38  | 💀 | Back loading | DROP — title struck (̶3̶8̶.̶ ̶B̶a̶c̶k̶ ̶l̶o̶a̶d̶i̶n̶g̶) and body struck |
| 39  | 💀 | Bunkers | DROP — title struck |
| 40  | ✅ | Oil pollution prevention | Bold *(d) "not to load on top of such 'collected washing' without specific instructions from Charterers"* added |
| 41  | ✅ | TOVALOP | Struck original + bold *"41. ITOPF Clause Owners warrant that throughout the duration of this Charter the vessel will be: i) owned or demise chartered by a member of the 'International Tanker Owners' Pollution Federation Limited', and ii) entered in the Protection and Indemnity (P&I) Club…"* |
| 42  | ✅ | Lien | — |
| 43  | ✅ | Law and litigation | *a single* struck → *three*; *(Refer Essar Provisions Clause No. 2 ARBITRATION CLAUSE)* added; *1950* → *1996* |
| 44  | ✅ | Construction | — |

**Wholly-struck SHELLVOY: 21, 27, 29, 38, 39 → 5 dropped; 28 is anchor-less replacement → 6 ordinals not in output. Total kept: 38.**

---

## Shell Additional Clauses (pages 18–35), ordinals 1..43, expected 28 kept

| Ord | Status | Title | Notes |
|----:|:------:|:------|:------|
| 1   | ✅ | Indemnity Clause | Long body, ends mid-sentence at *"…cargo on board :"* on PDF page 18, with surviving fragments through page 19 |
| 2   | 💀 | Original Bill of Lading Clause | DROP — title and body wholly struck |
| 3   | ✅ | Insurance Clause | Sub-clauses 1)–4) Oil Pollution / Civil Liability / Hull and Machinery / War Risk — 5) Year 2000 struck out; bold CAPS replacement for War Risk *"OWNERS SHALL EFFECT WAR RISKS INSURANCE…"* survives |
| 4   | ✅ | Early Loading Clause | Bold *"ANY TIME SAVED TO BE SHARED 50/50"* kept |
| 5   | ✅ | Drug and Alcohol Clause | — |
| 6   | ✅ | Charges / Claims Clause | *"additional freight, indemnity claims, insurance"* struck; *"Worldscale charges / dues;"* visible; *ninety (90)* → *120(ONE HUNDRED AND TWENTY)* |
| 7   | ✅ | Worldscale Dues Clause | — |
| 8   | ✅ | ITWF Clause | — |
| 9   | ✅ | Letter of Protest / Deficiencies Clause | — |
| 10  | ✅ | Documentation Clause | *Shell Form 19x / Time sheet(s)* struck out from the bullet list |
| 11  | ✅ | Adherence to Voyage Instruction Clause | — |
| 12  | 💀 | Administration Clause (Refer Essar Rider Clause No. 14) | DROP — title struck (refers to Essar Rider 14); body wholly struck |
| 13  | ✅ | Questionnaire(s) | — |
| 14  | ✅ | Cargo Retention Clause | *"by an independent surveyor, appointed by Charterers and paid jointly by Owners and Charterers)"* struck; bold *AS DETERMINED BY TWO SURVEYORS…INTERTEK* kept |
| 15  | ✅ | Slops Clause | — |
| 16  | ✅ | Clean Ballast Clause | — |
| 17  | ✅ | Closed Loading Clause | — |
| 18  | ✅ | Segregation Clause | Bold *"IF APPLICABLE"* added |
| 19  | ✅ | Hydrogen Sulphide (H2S) Clause | — |
| 20  | 💀 | Vaccum Gasoil (VGO) Waxy Distillate (WD) Cleaning Clause | DROP — title struck and all sub-points (A..I + Non SBT section) struck |
| 21  | 💀 | Part Cargo (Demurrage) Clause | DROP — body wholly struck (title visible but stand-alone heading-only treatment here is inconsistent with other dropped wholly-struck clauses; honest call is to drop) |
| 22  | ✅ | Clearance Clause | Bold *"IF FREE PRATIQUE IS NOT GRANTED WITHIN 6 HOURS…"* + *"HOWEVER THE TIME TO COUNT IN FULL AT LOAD PORTS…"* added |
| 23  | ✅ | Port Regulations Clause | — |
| 24  | ✅ | Pilots Clause | — |
| 25  | ✅ | Excess Berth Occupancy Clause | — |
| 26  | ✅ | Single Point Mooring (SPM) Clause | — |
| 27  | ✅ | Single Buoy Mooring (SBM) Line Clearance Clause | Bold *"OWNERS SHALL REQUIRE RELEVANT LOI FOR SUCH OPERATION AS PER OWNERS P&I CLUB WORDING"* added |
| 28  | ✅ | Speed Clause | — |
| 29  | ✅ | Bunkers / Deviation Clause | — |
| 30  | ✅ | Ship to Ship Transfer Clause | — |
| 31  | 💀 | Additional Load/Discharge Port(s) Clause | DROP — title + body wholly struck |
| 32  | 💀 | United Kingdom Clause | DROP — title + all sub-points struck (Routing, Sullom Voe, Tranmers Service) |
| 33  | 💀 | Rotterdam Port Dues Clause | DROP — title + body wholly struck |
| 34  | 💀 | Canada Clause | DROP — title + body wholly struck |
| 35  | 💀 | United States of America (U.S) Clause | DROP — title + all sub-points struck (Customs, Coastguard, Laws and Regulation) |
| 36  | 💀 | Sidi Kerir Clause | DROP — title + body wholly struck |
| 37  | 💀 | Nigerian Clause | DROP — title + body (a..d) wholly struck |
| 38  | ✅ | India Clause | Bold *"IF DISPUTED MASTER TO ISSUE A LOP AND THIS TO BE SUFFICIENT FOR LAYTIME / DEMURRAGE CALCULATIONS"* added; struck *"a copy of this Charter…"* filtered |
| 39  | 💀 | Singapore Clause | DROP — title + all three sub-points struck |
| 40  | 💀 | Thailand Clause | DROP — title + body wholly struck (A, B, C all struck) |
| 41  | 💀 | Australia Mooring Clause | DROP — title + Great Barrier Reef / Ballast Exchange / Sydney sub-points all struck |
| 42  | 💀 | Japan Clause | DROP — title + all sub-points (Drawing, Supervisor, Okinawa, Safety Pledge Letter, Drifting) struck |
| 43  | ✅ | Address Commission Clause | — |

**Wholly-struck Additional: 2, 12, 20, 21, 31, 32, 33, 34, 35, 36, 37, 39, 40, 41, 42 → 15 dropped. Total kept: 28.**

---

## Essar Rider Clauses (pages 36–39), ordinals 1..22, expected 21 kept

| Ord | Status | Title | Notes |
|----:|:------:|:------|:------|
| 1   | ✅ | INTERNATIONAL REGULATIONS CLAUSE | — |
| 2   | ✅ | ARBITRATION CLAUSE | — |
| 3   | ✅ | TRADING WARRANTIES AND ARAB LEAGUE BYCOTT | (sic — typo in source: "BYCOTT" for "BOYCOTT") |
| 4   | ✅ | SALE | — |
| 5   | ✅ | FREIGHT REMITTANCE | — |
| 6   | 💀 | BROKERAGE | DROP — body wholly struck |
| 7   | ✅ | PRIVACY | — |
| 8   | ✅ | SMALL CLAIMS | — |
| 9   | ✅ | WORLDSCALE HOURS, TERMS AND CONDITIONS | — |
| 10  | ✅ | VESSEL'S DESCRIPTION | — |
| 11  | ✅ | I.S.M. CLAUSE | — |
| 12  | ✅ | ACCIDENTS / BREAKDOWNS | — |
| 13  | ✅ | CONOCO weather clause | — |
| 14  | ✅ | SIGNED CHARTER PARTY | — |
| 15  | ✅ | FREE OF CLAIMS | — |
| 16  | ✅ | (untitled — single line) | *"All voyage instructions and changes to same to be sent by telex/Fax/E mail only."* |
| 17  | ✅ | (untitled — wrapped sentence) | *"If acceptable by Suppliers, otherwise Master to issue Letter of Protest…"* |
| 18  | 🏷 | CLINGAGE – NOT APPLICABLE FOR THIS CHARTER | Heading-only — body fully struck (whole crude/clingage explanation). Output has `text=""`. |
| 19  | ✅ | BIMCO ISPS CLAUSE FOR VOYAGE CHARTERS | — |
| 20  | ✅ | STS TRANSFER CLAUSE | — |
| 21  | ✅ | (untitled — wrapped sentence) | *"Owners confirm that all officers on board hold ocean going vessel certificate of competency. Also confirm that for the forthcoming voyage…"* |
| 22  | ✅ | BILL OF LADING FIGURES | Tokenised as bare `22` + `.BILL OF LADING FIGURES` — anchor detection covers this split form |

**Wholly-struck Essar: 6 → 1 dropped. Total kept: 21.**

---

## Summary

| Section     | Numbered range | Wholly struck (dropped) | Anchor-less replacement | Output count |
|:------------|:---------------|:------------------------|:------------------------|-------------:|
| SHELLVOY 5  | 1..44          | 21, 27, 29, 38, 39 (5)  | 28 (1)                  | **38**       |
| Additional  | 1..43          | 2, 12, 20, 21, 31, 32, 33, 34, 35, 36, 37, 39, 40, 41, 42 (15) | — | **28**       |
| Essar Rider | 1..22          | 6 (1)                   | —                       | **21**       |
| **Total**   |                |                         |                         | **87**       |
