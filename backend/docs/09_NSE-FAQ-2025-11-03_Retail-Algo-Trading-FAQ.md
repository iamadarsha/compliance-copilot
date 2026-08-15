---
doc_id: NSE FAQ — Safer participation of Retail investors in Algorithmic trading
title: Frequently Asked Questions (FAQs) - Safer participation of Retail investors in Algorithmic trading
issuer: National Stock Exchange of India Limited (NSE)
date: 2025-11-03
status: current — member-facing FAQ summarizing points already covered across NSE/INVG/69255, NSE/INVG/69289, NSE/INVG/67858, NSE/MSD/67753 and SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/0000013; per its own disclaimer, the underlying circulars are final and binding wherever this FAQ differs from them
source: https://nsearchives.nseindia.com/web/sites/default/files/inline-files/FAQ_Retail%20Algo_03112025_NSE.pdf
retrieved: 2026-08-16
---

# NSE FAQ — Safer participation of Retail investors in Algorithmic trading

**November 3, 2025**

## Subject: Frequently Asked Questions on Safer Participation of Retail Investors in Algorithmic Trading

Disclaimer: this FAQ summarizes queries relating to the topic in a concise manner for members' ease of understanding, is general information only, and NSE accepts no liability for reliance on it. In the event of any difference between this FAQ and the underlying circulars, the circulars shall be construed as final and binding.

1. What are the Empanelment criteria for Algo Provider? The detailed criteria for empanelment of Algo Provider have been mentioned in NSE circular no. NSE/INVG/70309 dated September 19, 2025 — "Corrigendum to 'Safer participation of Retail investors in Algorithmic trading – Detailed Operational Modalities' – Update."

2. As per criteria mentioned in para 4.2 of NSE circular NSE/INVG/70309 dated September 19, 2025, who has to provide the declaration of cyber/adverse technical incident for the previous 3 years? As per the empanelment criteria, the Algo Provider shall provide a self-declaration of any cyber/adverse technical incident for the previous 3 years. This declaration is not required from any auditor and shall be provided by the Algo Provider on their own letterhead.

3. Will a static IP be required for retail customers coming via algo vendors? Client static IP will be required only in case of a Tech Savvy Investor using API for placing orders.

4. Whether a Research Analyst (RA) wishing to deploy any black box algo will first need to become an Algo Provider, and can an Algo Provider host black box algos of multiple third-party RAs? As per SEBI circular SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/0000013 dated February 04, 2025, in case of Black Box Algos, the Algo Provider shall register as a Research Analyst and maintain a detailed research report for each such algo and confirm to the exchanges that such report has been maintained. Thus, any RA wishing to deploy a Black Box Algo shall be required to become an Algo Provider before being able to provide it. Further, as per para 14 of NSE circular NSE/INVG/69255 dated July 22, 2025, all Algos developed by Algo Providers need to be hosted on the Trading Member's server; hence, an Algo Provider hosting black box algos of multiple third-party RAs is not possible.

5. What are the hosting requirements for retail algorithmic trading strategies? As per Exchange Circular NSE/INVG/69255 dated July 22, 2025 (Annexure I, Para 14), all strategies shall be run on the broker's servers, with order messages originating from the broker's server. This is central to ensuring the broker's control over risk management and data confidentiality. However, a Tech Savvy client is required to host the Algo using a static IP at their own end, where the Algo logic resides, instead of hosting it on the Trading Member's cloud server.

6. Is a static IP address mandatory for all individual retail clients using an API? Client static IP is required only in case of a Tech Savvy Investor using API.

7. How should algorithmic orders from Internet Based Trading (IBT) and Securities Trading through Wireless Technology (STWT) platforms be tagged? Retail investors are allowed to trade using Algorithmic Trading through Client Direct API, provided by the broker to clients to send order messages through API and Member frontend for retail algo (Internet or Mobile based applications). In such cases, the tagging shall be: the first 12 digits would be "444444444444" and the 13th digit would be "0", "2", or "4".

8. Is it permissible for clients to place basket orders for unregistered algos through client APIs? As per the framework (Annexure I, Para 2.8 of Exchange Circular NSE/INVG/69255 dated July 22, 2025), all orders received via API from clients are considered Algo orders and require appropriate tagging, including standardised tagging for cases where the OPS is within the threshold of 10 OPS.

9. Is a Tech Savvy client required to participate in the monthly mandatory mock session, as per SEBI guidelines? As the responsibility of outcome (profit/loss) rests with the Tech Savvy client itself, since the algo logic is theirs and RMS is the Trading Member's responsibility, an individual Tech Savvy client is not required to participate in the monthly mock trading sessions. All other entities are required to participate in mandatory mock sessions as per SEBI circular SEBI/HO/MRD1/DSAP/CIR/P/2020/234 dated November 24, 2020 and NSE circular NSE/MSD/67753 dated April 29, 2025.

10. An Algo platform developed by an empanelled Algo vendor is hosted on a Trading Member's infrastructure — whose static IP shall be required in case Retail clients are trading through the Trading Member using such platform? With reference to NSE circular NSE/INVG/67858 dated May 05, 2025, it would be the static IP of the Trading Member's server.

11. Are Market orders and IOC orders allowed through Algo? As per point 8.1.1.12 of NSE circular NSE/MSD/67753 dated April 29, 2025, Algo orders with order type as Market Order are not permitted, and as per point 8.1.2.1 of the same circular, Immediate Or Cancel (IOC) and Market orders shall not be allowed to be placed using algorithmic trading in the Commodity segment.
