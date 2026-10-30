# DAA Design

Status: approved Oct 30, 2026.

## Purpose

DAA proves a system is a real, distinct miner, without revealing ownership. Prototype uses a fixed demo registry. DAA replaces trust in a hardcoded list with a check every node verifies: a genuine secure element from an approved vendor, an identity key born inside that element and never exported, and an element with no prior registration.

## What DAA proves

Proves genuineness (real chip, approved vendor), key custody (element-held, non-exportable), and uniqueness (one element, one system). Proves nothing about ownership. No name. No link to a person. No link to a payout key. System actions stay public under a pseudonym. Real identity stays private. Identity key signs work only, never spends. Payout key stays an ordinary wallet key, separate from identity. Identity compromise cannot steal funds. Payout compromise cannot fake identity.

## Nullifier

Stable per element. Each element derives one nullifier from a secret plus a fixed basename ("mutu-registration"). Same element registering twice produces the same nullifier. Nodes reject the second registration. Nullifier links a system's own registrations to each other, by design, for double-detection. Nullifier reveals nothing about which chip or who owns it. Mainnet stores seen nullifiers persistently. Prototype stores nullifiers in memory; disk persistence comes with the persistence item.

## Roots

Vendor roots are public keys baked into node software at genesis. Roots cannot be added or removed later without a fork. No admin kill-switch. No admin keys. A compromised root gets forked away, not switched off. Prototype uses test roots. Real roots freeze only after vendor research, since freezing is irreversible without a fork. Vendor selection requires group-based anonymity, not unique device certificates. A vendor offering only serial certificates is unsuitable as a root.

## Roots open question

Chip-vendor roots versus maker-provisioning roots. Chip-vendor roots mean the element manufacturer certifies genuine chips. Maker-independent. Stronger. Maker roots mean the miner maker certifies boards at factory time. Simpler. Weaker link on a rogue maker key. Decision: chip-vendor roots. Open engineering question: whether a low-cost element chip offers DAA-capable attestation in hardware, or whether DAA builds on top of element signatures. Scope assumes a DAA-capable element or an element-backed construction. Assumption named, not solved.

## Identity lifecycle

Key generated inside the element at setup, never exported. Registration is a transaction: system public key plus group signature plus nullifier, gossiped like any transaction and recorded in blocks. All nodes agree on the registry through the chain. Nodes verify the group signature against a frozen root, check the nullifier unseen, then list the system. Work authentication: identity key signs work, nodes verify against the registry before crediting capped work. Legacy non-attested systems keep the spec rule: work slice only, no production, no dividend.

## Prototype scope

Attestation protocol, not hardware. An element interface (generate key, sign, attest) with a software implementation standing in for real chips. Message format, verification, nullifier store, and registry sync get proven before hardware arrives. Same staging as loopback before Tor. Deferred: real chip integration, real vendor roots, revocation-by-fork mechanics, activation (bond escrow plus 56-day queue) as the follow-on scope.

## Approved decisions

- Nullifier stable per element (double-detection, links a system's own registrations).
- Chip-vendor roots over maker roots, test roots for the prototype, real roots frozen only after vendor research.
- Registration as transactions (reuses P2P and chain agreement, no new sync protocol).
- Prototype language: Python, software-simulated elements, hardware later.
