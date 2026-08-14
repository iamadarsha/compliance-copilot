---
doc_id: NSE/INVG/67858 (Circular Ref. No. 471/2025)
title: Safer participation of retail investors in Algorithmic trading — Implementation Standards
issuer: "National Stock Exchange of India Limited (NSE), Department: Investigation"
date: 2025-05-05
status: current — exchange-level operational standard under SEBI circular 2025/0000013 (doc 01), clause 7(a)
source: https://nsearchives.nseindia.com/content/circulars/INVG67858.pdf
retrieved: 2026-08-14
---

# CIRCULAR — NSE/INVG/67858 (Ref. No. 471/2025)

**May 05, 2025 — National Stock Exchange of India Limited**

To, All Market Participants

## Subject: Safer participation of retail investors in Algorithmic trading

This is with reference to SEBI Circular Ref. no. SEBI/HO/MIRSD/MIRSD-PoD/P/2025/0000013 dated February 04, 2025 (doc 01) and NSE circular Ref. no. NSE/INVG/66524 dated February 05, 2025.

The implementation standards on safer participation of retail investors in Algorithmic trading have been formulated in accordance with para 7(a) of the aforementioned SEBI Circular and are enclosed as Annexure. Market Participants are requested to take note of the above and comply.

For and on behalf of National Stock Exchange of India Limited — Manish Deo, Associate Vice President

## Annexure — Implementation Standards for Safer Participation of Retail Investors in Algorithmic Trading

*(Under Clause 7 of SEBI circular ref. SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/0000013 dated 4-Feb-2025)*

### A. API Access Standards for Clients in Trading

1. Stockbrokers may provide clients with API access to their trading systems. Clients must mandatorily provide the stockbroker with static IP address(es).

2. The client may give one static IP address (primary), or an additional static IP (secondary) for connectivity redundancy.

3. Multiple API keys can be given to the same client (e.g. for different segments or algos). Each key may be mapped to the same primary/secondary static IPs, or have separate ones.

4. Where a client has multiple API keys, the broker will ensure non-registered algos run only through one of the predefined API keys; other keys are for registered algos only.

5. Static IP is mandatory for API access for both client-generated algos and algos generated via empanelled algo provider(s). For client-generated algos the static IP shall be the client's; for algo-provider-generated algos it shall be the vendor's or the client's; for broker-generated algos it shall be the broker's or the client's.

6. Clients may update their mapped static IP no more than once a calendar week, except in extraordinary cases raised with the broker.

7. A static IP can only be mapped to one client at a time, but can be shared between clients belonging to one family as defined in SEBI circular SEBI/HO/MIRSD/MIRSD-PoD1/P/CIR/2024/169 dated 3 December 2024, with written/2FA-validated request.

8. All API sessions shall be compulsorily logged out every day before the start of the next trading day.

9. A Member Client API Enablement Annexure may be specified by Exchanges from time to time.

### B. Standards around APIs without registering algo

1. Clients can use API connectivity only for automated trading systems/algorithms, equipped with necessary RMS checks by brokers.

2. The **Threshold Order Per Second (TOPS)** is initially set at not exceeding 10 orders per second per exchange, adjustable by exchanges after due notice. Below this threshold, the client is not required to register for algorithmic trading.

3. All algo orders via API below the defined TOPS still require registration with the Exchange and receive a generic algo ID.

4. Exchanges may specify restricted order types/contracts/securities for client algos; brokers must ensure APIs don't permit these.

5. If a broker receives orders exceeding the TOPS limit, the broker shall reject/not process the excess orders.

6. Every broker providing API connectivity must be able to effectively monitor/control TOPS limits for non-registration-required algos.

### C. Standards for client-generated registered algos

1. Clients placing orders exceeding 10 OPS must register their algorithm with each Exchange where it will be used; Exchanges will formulate a simplified registration/compliance framework up to a certain threshold.

2. To register, the client provides details to the broker, who forwards them to the exchange(s); the exchange issues a registration ID communicated back via the broker. Orders are tagged with the exchange-provided algorithm ID(s).

### D. Broker-generated algos

1. Brokers may create and offer algorithms to clients; each is registered with the exchange and receives an exchange-specific algorithm ID.

2. Client orders executed through these algorithms must include the appropriate exchange algorithm ID.

3. Any change to a broker-generated algorithm's logic must be reported to the exchange for updated approval.

### E. Algos provided by algo provider

1. All algo providers must be empanelled with exchanges per each exchange's guidelines, and registered with each exchange where their algorithms will trade.

2. Empanelled algo providers register all algos with the exchange; the exchange assigns a unique algo ID, usable across members once registered.

3. Brokers may enter commercial/technical arrangements with algo providers (including fee sharing).

4. Any broker with a commercial, technical, or combined arrangement with an exchange-empanelled algo provider must inform all relevant exchanges, and notify them if the arrangement is terminated.

5. The broker must carry out adequate due diligence on the algo provider and immediately report any violation of securities laws to the relevant Exchange(s).

### F. Threshold Orders Per Second (OPS)

TOPS is initially not exceeding 10 orders per second per exchange/segment, adjustable by exchanges after due notice. Brokers may set their own (lower) client-level threshold, not exceeding the current prescribed TOPS.

### G. Algo ID tagging

Exchanges shall issue tagging mechanisms for registered and registration-free algo orders. All algo orders (below and above threshold) shall be tagged with a unique Exchange-provided identifier to establish audit trail.

### H. Risk Management

Brokers shall comply with requirements for Internet Based Trading (IBT), Securities Trading using Wireless Technology (STWT), Risk Management, and guidelines on Decision Support Tools/Algorithm trading. Reference: NSE consolidated circular NSE/MSD/67753 dated April 29, 2025.

### I. Operational Specifications for algo via IBT / STWT / Client API / Vendor API

In addition to para 8.1 of NSE Circular dated April 29, 2025:

a. Brokers must ensure sound audit trail for all IBT/STWT/Client API/Vendor API orders and trades, with identification of the actual user and user-id. Audit trail data must be retained for at least 5 years.

b. The system must have security features per SEBI cyber security circular SEBI/HO/ITD1/ITD_CSC_EXT/P/CIR/2024/113 dated August 20, 2024, and other SEBI/Exchange directives.

c. Brokers shall be required to have OAuth-based authentication only, or any authentication mechanism allowed/communicated by the Exchange/SEBI from time to time.

d. The system shall have password protection, automatic password expiry after a reasonable duration, re-initialisation on fresh passwords, and two-factor authentication for client access.

e. Brokers must ensure open APIs are not permitted — access only via unique vendor client specific API key and whitelisted static IP for retail users, and unique vendor API key and whitelisted IP for algo providers.

f. Brokers are fully responsible and liable for all orders emanating through their IBT/STWT/Client API/Vendor API systems, and must ensure only eligible clients use the facility.

g. Brokers may implement additional safeguards as they deem fit.

h. All Retail Algorithms, including those provided by empanelled Algo providers, should be hosted on [broker/exchange-specified] servers.

### J. Notes

1. These standards do not apply to trading under Direct Market Access (DMA), which remains governed by relevant provisions.

2. Brokers may charge clients fees/subscription charges for API services, over and above brokerage and any exchange algorithm-registration charges.

3. Stock exchanges have authority to kill any rogue algo(s) impacting the market.
