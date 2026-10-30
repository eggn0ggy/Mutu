# P2P Design

Status: approved Oct 30, 2026.

## Purpose

P2P is transport, not consensus. Without P2P, the chain lives on one machine. With P2P, multiple machines run one chain: nodes find each other over Tor, share blocks and transactions, follow the most-work valid chain. Consensus rules stay: mesa issuance, payouts, cap, settlement delay.

## Transport

Tor only. No clearnet. Every full node runs a Tor onion service. No public IP needed. Works behind CGNAT, where clearnet inbound fails. Prototype: node uses local Tor (Expert Bundle or Tor Browser) via SOCKS, static torrc hidden service. Later: node manages onion key via Tor control port, no manual torrc editing.

## Peer discovery

Seeds plus gossip. No DNS. New nodes start from hardcoded seed onion addresses (founding nodes plus community nodes, baked into software, operator-overridable). After that, nodes gossip peer addresses, Bitcoin-style. No DNS seeds. No DHT.

## What moves

Headers first, then full blocks, then transactions. Messages: handshake, headers sync, block fetch, transaction relay, peer gossip, ping/pong. Full blocks only, no compact-block tricks. A 2 MB cap and 10-minute blocks mean about 3 KB/s per peer. 8 peers mean about 27 KB/s.

## Chain selection and sync

Most-accumulated-work. Nodes track header chains, follow the most-work valid chain. Headers-first sync: download headers, validate proof-of-work and structure, download full blocks for the best chain, validate fully, extend. Orphans stored briefly, parents requested. Reorg: switch to a more-work chain. No hard finality. Settlement delay (one window) protects payouts from shallow reorgs. Initial sync from genesis. No checkpoints. Chain is small early, so genesis sync is cheap. Assume-valid and headers-first optimizations deferred.

## Validation

Validation gates everything. A node never relays or builds on an unvalidated block. Header checks: proof-of-work and structure. Full block checks: transactions valid, conservation, 49/28/23 split plus 2% commons, cap compliance, issuance schedule. Invalid blocks get dropped. Senders of invalid blocks get banned. Rate limits apply per peer. Tor slowness adds a natural rate limit.

## Transactions and mempool

Any full node relays valid transactions: signature, fee, no double-spend. Prototype fee: flat 0.05 (testnet fee). Mainnet fee policy stays open. Mempool has a size cap with lowest-fee eviction. Spam cannot eat memory.

## Roles

Two roles, kept separate. Full node (relay): permissionless. Anyone runs one. No attestation. No rewards. More relays make the network harder to eclipse or censor. Mining system: full node plus attested identity, bond, activation, hash units. Mining requires attestation. Relaying does not.

## Sybil and eclipse

A fake army of relay nodes earns nothing and cannot vote. Chain selection is most-work, not most-nodes. Eclipse alone cannot fake work: fooling a node requires a heavier valid chain, which costs real hashrate, not fake onions. Outbound peer diversity plus anchored peers across restarts add a second layer.

## Prototype scope

Two nodes syncing over Tor. Headers plus blocks plus transactions plus gossip. Full validation on peer blocks. Stratum bridge grown into controller: Gamma shares become real chain work, not counted shares. Deferred: real DAA (still emulated), control-port onion keys, compact blocks, light clients (wallets query a trusted full node initially).

## Approved decisions

- Default peers: 8 outbound, 32 inbound.
- Seed nodes: system #1 plus early volunteers, onion addresses baked in.
- Relay-only nodes: permissionless.
- Prototype language: Python. Second implementation in another language comes later, by another team, for the two-implementations gate.
