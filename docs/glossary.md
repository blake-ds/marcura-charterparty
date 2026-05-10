# Glossary

Maritime law and PDF-parsing terms used throughout the docs and code. Markdown has no native definition list, so this page uses HTML `<dl>` — the one place the structure earns its keep.

## Maritime

<dl>

<dt>Charter party (CP)</dt>
<dd>Contract between a ship's owner and the party hiring it. Latin <em>carta partita</em> — "the parted card", a sheet ripped in two so each side held proof. Today: a long, ritualised document with a standard form and bespoke negotiated edits.</dd>

<dt>Voyage charter party</dt>
<dd>The variant in this repo's source PDF. The ship is hired for <em>one specific voyage A→B</em> with a specific cargo; payment is per ton of cargo (freight), not per day. Contrast with <em>time charter</em> (rented by time) and <em>bareboat charter</em> (rent the hull, supply your own crew).</dd>

<dt>Owners</dt>
<dd>The party that owns or disposes of the vessel. In the source PDF: Kakatua Shipping Co. Ltd.</dd>

<dt>Charterers</dt>
<dd>The party hiring the ship to move their cargo. In the source PDF: Red Oil Ltd.</dd>

<dt>Master</dt>
<dd>The ship's captain — the legal authority on board.</dd>

<dt>SHELLVOY 5</dt>
<dd>An industry-standard charter party form drafted by Shell in July 1987, widely used for tanker voyage charters. Part II of the source PDF is the SHELLVOY 5 boilerplate; the bold and struck-through edits show how this specific deal departs from the boilerplate.</dd>

<dt>Strike-through (in a CP)</dt>
<dd>Negotiators take the standard form and physically strike out clauses or phrases they reject. Struck text is <em>not part of the contract</em>. The replacement language sits next to it (commonly bold). This convention is the entire reason the parser must filter strike-through carefully — including struck text would silently change the contract.</dd>

<dt>Freight</dt>
<dd>The price paid by charterers to owners for moving the cargo. In the source PDF: Worldscale 103.00 — i.e. 103% of the published industry-reference rate.</dd>

<dt>Laytime</dt>
<dd>Free time built into the contract for loading and unloading. In the source PDF: 72 hours.</dd>

<dt>Demurrage</dt>
<dd>Penalty paid to owners when laytime is exceeded. In the source PDF: USD 18,000/day.</dd>

<dt>Bill of lading (B/L)</dt>
<dd>Document the master signs acknowledging the cargo onboard; doubles as title to the goods in the international cargo trade. Several Part II clauses regulate how the master must (or must not) issue them.</dd>

</dl>

## Technical

<dl>

<dt>Bounding box (bbox)</dt>
<dd>Four numbers <code>(x0, y0, x1, y1)</code> describing the rectangle a glyph, word, or graphic occupies on the page. PyMuPDF returns a bbox for every word; the strike-through filter intersects word bboxes with strike-rectangle bboxes.</dd>

<dt>Strike rectangle</dt>
<dd>In this PDF, strike-through is rendered as a thin filled rectangle (height &lt; 1pt) drawn over the text — <em>not</em> a PDF annotation, <em>not</em> a font feature. PyMuPDF exposes them through <code>page.get_drawings()</code>.</dd>

<dt>Reasoning effort</dt>
<dd>An Azure / OpenAI model parameter that trades latency and cost for thinking depth. GPT-5.4 accepts <code>minimal | low | medium | high | xhigh</code>; Grok 4.1 accepts <code>low | medium | high</code>; DeepSeek-V4-Flash defaults to <code>medium</code>.</dd>

<dt>Verifier</dt>
<dd>The LLM step in our pipeline. It is <em>not</em> the source of clause text — it only flags suspicious deterministic output and proposes one-line repairs. The split keeps every word in the JSON traceable to a word on the page.</dd>

</dl>
