---
doc_id: NSE/INVG/69255 (Circular Ref. No. 495/2025)
title: Safer participation of Retail investors in Algorithmic trading – Detailed Operational Modalities
issuer: "National Stock Exchange of India Limited (NSE), Department: Investigation"
date: 2025-07-22
status: current — implementation date August 1, 2025; corrigendum issued via NSE/INVG/69289 dated July 24, 2025 (doc 08) revises the order-tagging tables in Section 2
source: https://nsearchives.nseindia.com/content/circulars/INVG69255.zip
retrieved: 2026-08-16
---

# CIRCULAR — NSE/INVG/69255 (Ref. No. 495/2025)

**July 22, 2025**

To, All Market Participants

## Subject: Safer participation of Retail investors in Algorithmic trading – Detailed Operational Modalities

This is with reference to SEBI Circular Ref. no. SEBI/HO/MIRSD/MIRSD-PoD/P/2025/0000013 dated February 04, 2025 and NSE circular Ref. no. NSE/INVG/66524 dated February 05, 2025 regarding safer participation of retail investors in Algorithmic trading. The Exchange, vide circular number NSE/INVG/67858 dated May 05, 2025, issued the implementation standards in accordance with para 7(a) of the aforementioned SEBI Circular. As required in the above-mentioned SEBI circular, the detailed operational modalities for participation of Retail investors in Algorithmic trading along with the documentation required are provided in Annexure I. The implementation date of the above framework is 1st August 2025.

## Annexure — Detailed operational modalities for empanelment of Algo Providers and registration of Retail Algo

### I. Background

1. SEBI, vide circular no. SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/0000013 dated February 4, 2025, issued a circular "Safer participation of retail investors in Algorithmic trading." Exchange vide circular NSE/INVG/67858 dated May 05, 2025 has issued "Implementation Standards for safer participation of retail investors in Algorithmic trading." "Algo orders" are orders generated using automated execution logic. Any Algo Provider providing the facility to place algo orders with Brokers through API shall be required to be empanelled with Exchanges in a manner as stipulated by Exchanges.

### II. Chronology and turnaround time for registration of an algo

2. The chronology to be followed for registration of an algo is: empanelment of the vendor (already-empanelled vendors and in-house Trading Members do not need to re-empanel); registration of the algo product; and application and registration of the algo strategy through a Trading Member and grant of an Algo ID by the Exchange.

3. Turnaround Time (TAT): for empanelment of an "Algo Provider" with the Exchange, the proposed TAT is T+30 working days from receipt of a complete application. For processing an application for registration of an algo from an Algo Provider, empanelled vendor, or Trading Member, TAT is T+10 working days, except Execution algos, which get a faster TAT of T+7 working days. TAT is the maximum timeline within which Exchange officials shall communicate a registered/rejected status with reasons to the applicant, and may be reviewed later based on experience gained.

### III. Empanelment process of Algo providers

4. The Algo Provider shall make an application to the Exchange for empanelment as per specified format and shall execute an undertaking in favour of the Exchange, including submission of an empanelment undertaking, meeting the empanelment criteria, submission of the empanelment application, and 2 years of securities market experience for the Proprietor/Directors (any 1)/Partners (any 1). Upon satisfactory processing, the Algo Provider is registered and allotted a unique Vendor code; a circular is issued announcing the empanelment, and the Algo Provider list is updated on the Exchange website. The empanelled Algo Provider enters into an independent commercial arrangement with members; the Exchange is not liable for any payment due to the Algo Provider, and any breach of the empanelment terms entitles the Exchange to terminate the empanelment immediately.

### IV. Product registration and change management

5. As part of product registration, the Exchange processes User Interface registration (product name, front-end writeup including password policy, version, segments, URL of the portal, RMS writeup, and an auditor certificate) and registration of the Algo product itself, which is categorized as Whitebox (logic disclosed and replicable, i.e. Execution Algos) or Blackbox (logic not known to the user and not replicable). Any change in the logic governing an algo, any change in OMS/RMS resulting in a code change, addition of segment or version change, an Exchange-mandated change, implementation of a new SEBI circular, or a change in login/password policy or API requires a change request; no modification is allowed for registered Blackbox algos, which require fresh registration for any logic change.

### V. Operational specifications and roles of brokers

6. Trading members providing API/Algo Provider facility for routing client orders shall not be allowed to cross trades of their clients with each other; all orders must be offered to the market for matching. All API orders shall be routed to the exchange trading system through the member's trading system, which shall be located in India. The trading member should ensure sound audit trail for all API/Algo Provider orders and trades, with data available for at least 5 years, and must not permit clients to place orders for order types or securities restricted by the Exchange or SEBI.

7. The API/Algo Provider system shall have sufficient security features including password protection for the user ID, automatic expiry of passwords at the end of a reasonable duration, and re-initialisation of access on entering fresh passwords. The system shall authenticate client access through two-factor authentication. Trading members shall ensure open APIs are not permitted, and access is provided only through a unique client-specific API key and static IP whitelisted by the broker to ensure identification and traceability of the end user.

8. The broker shall be fully responsible and liable for all orders emanating through their API/Algo Provider systems, and it is the broker's responsibility to ensure only clients meeting the eligibility criteria are permitted to use the facility. Brokers shall be solely responsible for handling investor grievances related to algo trading and for monitoring APIs for prohibited activities, and shall perform due diligence before onboarding an empanelled algo provider/vendor. Algo providers and brokers may share subscription charges and brokerage collected from clients, provided prominent and complete disclosures of all charges are made to the client and no conflict of interest results.

### VI. Risk Management

9. The following pre-trade risk controls are compulsory at the individual order level: Price Check (orders shall not breach the exchange's price bands/dummy filters), Quantity Check (orders shall not breach the order quantity limit defined by the Exchange, applicable to spread orders too), Order Value Check (orders shall not exceed the Exchange-specified value limit), Trade Price Protection Check (orders shall not breach the bad trade price for the security), Market Price check (a pre-set percentage of LTP), Automated Execution check (the algo shall account for all executed, unexecuted, and unconfirmed orders before releasing further orders), Net Position check, RBI Violation checks, and MWPL (Market Wide Position Limit) violation check. The system shall also have provision to restrict Algo order placement in Mini and Micro contracts as defined by the Exchange for the Commodity Segment.

### VII. Testing, confidentiality, and data flow

10. All registered retail algos are required to participate in mock/simulation testing on a monthly basis. Trading Members can avail the Simulated Environment detailed in NSE consolidated circular NSE/MSD/67731 dated April 28, 2025.

11. Retail algo strategies may be developed by the Trading Member, Algo Provider, Vendor, or a tech-savvy client. Algos are categorized as Execution/White box Algos (logic disclosed and replicable) or Black box Algos (logic not known to the user and not replicable); for Black box Algos, the Algo Provider shall register as a Research Analyst and maintain a detailed research report for each such algo, and re-register with a fresh research report for any logic change. Where an algo is developed by a tech-savvy client, the entire responsibility of the strategy logic and RMS requirements rests with that client. In all cases, a detailed agreement covering confidentiality clauses, non-disclosure agreements, and encrypted submissions must be entered into between the concerned parties (Broker, Vendor, tech-savvy client) wherever applicable.

12. Data flow between the algo provider, broker and the Exchange: the Trading Member is responsible for orders placed through any algo. NSE circular NSE/INVG/67858 dated May 05, 2025 (Annexure Para I(h)) states that all strategies shall be run on the broker's servers, with order messages originating from the broker's server. The broker is responsible for ensuring client data does not flow beyond their servers, and for compliance with SEBI's outsourcing guidelines.

13. All provisions of system audit, cyber security, VAPT (Vulnerability Assessment and Penetration Testing) and inspection-related requirements applicable to algos generally shall also apply to Retail algos.
