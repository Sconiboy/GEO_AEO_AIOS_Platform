# Customer Interface Prototype: Evidence Pattern Map

## Design Direction

The prototype uses a **premium editorial operations** aesthetic rather than a conventional metrics dashboard. It combines a restrained paper field, dark evidence-operations rail, serif decision headlines, monospaced provenance metadata, and deliberately limited accent colors. The visual hierarchy keeps the buyer question and the evidence decision dominant; source details and system state support that decision rather than competing with it.

## Implemented Interaction Flow

The standalone prototype at `demo/evidence-pattern-map-operator.html` demonstrates the real bounded 7-OH source-map case. It includes a conversational operator pane, source-role filters, live external source links, a customer-readable work order, a human decision gate, and a guided input that makes no unsourced finding.

The tested interactions are:

| Interaction | Result |
| --- | --- |
| Source-role filter | Shows only the legal-news or attorney-intake sources selected by the user. |
| Operator input | Stores a draft-note acknowledgement in the interface without pretending to answer from unverified evidence. |
| Work-order button | Confirms that the proposed work order is routed for review rather than published automatically. |
| External source links | Open the exact URLs preserved from the observed answer capture. |

## Next Implementation Layer

The prototype should become the application shell after the following data-backed features are connected: workspace authentication; buyer-question intake; capture paste/upload with immutable transcript reference; source review and evidence storage; work-order approval state; and a report view. The visual model is already designed for these objects.
