---
sidebar_position: 0
title: "Index"
---

# QKDN Agent Simulator — Wiki

This wiki documents the **QKDN Agent Simulator**, a backend system that simulates a Quantum Key Distribution Network with a single KMS node, an SDN Agent, and multiple clients. A Personal project used as leanring experience in preparation for an intenship on the topic.

The wiki is structured in two parts: a background section that builds the conceptual foundation from classical cryptography up to QKD, and a system section that documents the simulator's architecture and components in detail.

## Background

Foundational concepts required to understand why QKD exists and what problem it solves.

| Page                                                 | Description                                                                                    |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [1. Cryptography Fast-Track](01-crypto-fasttrack.md) | Encryption, symmetric vs asymmetric, key exchange, Diffie-Hellman, key properties              |
| [2. How Keys Are Distributed Today](02-pki-tls.md)   | PKI, certificate authorities, TLS handshake, the trust model                                   |
| [3. The Quantum Threat](03-quantum-threat.md)        | Quantum computers, Shor's algorithm, Grover's algorithm, harvest now decrypt later, PQC vs QKD |
| [4. What is QKD?](04-qkd.md)                         | Photons, polarization, BB84 protocol, QBER, privacy amplification, limits                      |
| [5. What is a QKDN?](05-qkdn.md)                     | Nodes, key pools, ESKR, ETSI API, SDN control layer                                            |

## System Overview

How the simulator is structured and how its components interact.

|Page|Description|
|---|---|
|[6. System Architecture](06-architecture.md)|The three actors — Mock KMS, SDN Agent, clients — and their boundaries|
|[7. Provisioning a Link — End to End](07-provisioning.md)|Full walkthrough of a provisioning request from client to KMS and back|

## Components

Deep dives into each component of the backend.

| Page                                          | Description                                                                         |
| --------------------------------------------- | ----------------------------------------------------------------------------------- |
| [8. The Mock KMS](08-mock-kms.md)             | ESKR pool, key generation simulation, lock mechanism, endpoints                     |
| [9. The SDN Agent](09-sdn-agent.md)           | Local state, background polling, health tracking, provisioning flow with resilience |
| [10. Resilience Mechanisms](10-resilience.md) | Circuit breaker (two models), exponential backoff, token bucket rate limiter        |
| [11. The Chaos Engine](11-chaos-engine.md)    | Fault injection, probability-based triggering, API, limitations, future directions  |

## Reference

|Page|Description|
|---|---|
|[12. Running the System](12-running.md)|Setup, startup sequence, endpoints reference, example curls, configuration|

---

## Credits

**Author:** Karam El labadie

**Assisted by:** Claude Sonnet (Anthropic)

### How Claude was used

This wiki was built through a structured co-authoring process over a single extended conversation. The goal was for the author to develop and demonstrate genuine understanding of the system, not to generate documentation automatically.

The process worked as follows:

- **The author** provided all source material: the backend codebase, design decisions, and explanations of each component in their own words
- **Claude** asked questions to surface gaps in understanding, suggested structure, fact-checked technical claims, and wrote pages from the author's answers, never from the code alone
- **Pages 1-3** were drafted by the author and refined with Claude's feedback
- **Pages 4-12** were written by Claude from answers the author gave to targeted questions, with the author reviewing and approving each page

The author explicitly chose this approach to ensure the wiki reflected real understanding rather than generated text. Any page the author could not answer questions about was revisited until the understanding was solid.

Design decisions documented in Page 10 (the second circuit breaker model, adaptive backoff, jitter) and Page 11 (chaos engine future directions) originated entirely from the author's own thinking and unpublished design notes.

This transparency note is included because honest attribution of AI assistance matters, both for intellectual integrity and as a model for how AI tools can support learning without replacing it.