---
doc_id: NSE/INVG/69289 (Circular Ref. No. 496/2025)
title: Corrigendum to "Safer participation of Retail investors in Algorithmic trading – Detailed Operational Modalities" - Update
issuer: "National Stock Exchange of India Limited (NSE), Department: Investigation"
date: 2025-07-24
status: current — amends Section 2 (NNF ID identification tables) of NSE/INVG/69255 dated July 22, 2025 (doc 07); all other content of that circular remains unchanged
source: https://nsearchives.nseindia.com/content/circulars/INVG69289.pdf
retrieved: 2026-08-16
---

# CIRCULAR — NSE/INVG/69289 (Ref. No. 496/2025)

**July 24, 2025**

## Subject: Corrigendum to "Safer participation of Retail investors in Algorithmic trading – Detailed Operational Modalities" - Update

This is with reference to Exchange circular NSE/INVG/69255 dated July 22, 2025, in respect of "Safer participation of Retail investors in Algorithmic trading – Detailed Operational Modalities." It is hereby notified that with respect to Section 2 on 'Revised Framework for identification' as detailed out in para nos. 2.1 and 2.2, the tables mentioned shall stand revised as under.

### I. Revised identification for the first 12 digits of the NNF ID

Provisions with respect to the NNF ID as defined in Exchange circular NSE/MSD/67753 dated April 29, 2025 are revised as under to incorporate identification of Algo orders from Client Direct API:

- **CTCL** (operated only by a Dealer of the TM, or the TM's Direct system, for square-off orders): Algo allowed — Yes. NNF ID: 12-digit [Pin code (6 digit), Branch Code (3 digit), Terminal ID (3 digit)]. 13th digit can be "0", "1", "2", "3", "4", "5", "6", "7" or "8", which determines ALGO or NON-ALGO.
- **IBT** (Internet Based Trading — front end of the TM capturing only manual order entry): Algo allowed — No. NNF ID: 111111111111. 13th digit can be "1", "3", "6", "7" or "8" and should always be NON-ALGO.
- **STWT** (Securities Trading through Wireless Technology — front end of the TM capturing only manual order entry): Algo allowed — No. NNF ID: 333333333333. 13th digit can be "1", "3", "6", "7" or "8" and should always be NON-ALGO.
- **DMA** (Direct Market Access — only for specific categories of clients specified by the Exchange from time to time): Algo allowed — Yes. NNF ID: 222222222222. 13th digit can be "0", "1", "2", "3", "4", "5", "6", "7" or "8", which determines ALGO or NON-ALGO.
- **Client Direct API** (facility provided by the TM to clients to send order messages through API, other than the above options): Algo allowed — Yes. NNF ID: 444444444444. 13th digit should always be ALGO, i.e. "0", "2" or "4".

### II. Revised identification for the 13th digit of the NNF ID

- **"0" — Algorithmic Order**: allowed NNF ID (12 digit) is the Pin/Branch/Terminal code, OR 222222222222, OR 444444444444.
- **"1" — Non-Algorithmic Order**: allowed NNF ID is the Pin/Branch/Terminal code, OR 111111111111, OR 222222222222, OR 333333333333.
- **"2" — Algorithmic Order using SOR** (Smart Order Routing): allowed NNF ID is the Pin/Branch/Terminal code, OR 222222222222, OR 444444444444.
- **"3" — Non-Algorithmic Order using SOR**: allowed NNF ID is the Pin/Branch/Terminal code, OR 111111111111, OR 222222222222, OR 333333333333.
- **"4" — Inter Exchange Algorithmic Orders**: allowed NNF ID is the Pin/Branch/Terminal code, OR 222222222222, OR 444444444444.
- **"5" — RMS Square off orders**: allowed NNF ID is the Pin/Branch/Terminal code only.
- **"6" — After market Orders**: allowed NNF ID is the Pin/Branch/Terminal code, OR 111111111111, OR 222222222222, OR 333333333333.
- **"7" — Basket orders**: allowed NNF ID is the Pin/Branch/Terminal code, OR 111111111111, OR 222222222222, OR 333333333333.
- **"8" — Batch upload**: allowed NNF ID is the Pin/Branch/Terminal code, OR 111111111111, OR 222222222222, OR 333333333333.

### III. Scope of this corrigendum

All other contents mentioned in the Exchange circular NSE/INVG/69255 dated July 22, 2025 remain unchanged. Queries may be addressed to invg@nse.co.in.
