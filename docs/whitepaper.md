# Mutu: Whitepaper (Draft, October 2026)

Mutu is a cryptocurrency designed to revive basement mining: small, quiet, home-run machines earning a fair share of every new coin. Not as charity. As the protocol's own payout rule. This draft describes the design as locked in spec v0.5.2. Items marked (v0.6) are decided, not yet implemented.

## Abstract

Bitcoin proved that strangers can share one ledger without a bank. It also proved something its early miners did not expect. Open mining competition ends in warehouses. Cheap power, bulk hardware, and pooled hashing pushed the individual miner out of the system. The system was supposed to belong to small miners. Mutu keeps Bitcoin's core: proof-of-work, a public ledger, no ruler. Mutu changes the rules that decide who may mine, what a miner may run, and who gets paid. The result is a coin whose mining layer is built for citizens with small machines. Its issuance rewards participation as well as block production. Its rules, once launched, no one can change. Not even the founder.

## 1. The problem

Mining today is an industrial activity. Three forces did it:

1. Uncapped scale. A miner who can run more machines earns more, without limit. Scale compounds.
2. The lottery. Only the block producer is paid. Small miners must join pools to smooth their income. Pools become the system.
3. The halving cliff. Fixed-supply schedules pay early miners most. Late miners least. Then the schedule ends. Fees alone fund security.

Mutu answers each force with a rule. Not a hope. A per-system power cap. A payout split that pays every worker. An issuance curve that rises, plateaus, glides down, and then drips forever.

## 2. Principles

Mutu's design follows Lana Swartz's distinction (2018). Two ideas. Digital metallism: money as scarce metal, mined by whoever can dig hardest. Infrastructural mutualism: money as shared infrastructure, maintained by its users. Mutu is built for the second:

- Everyone who works earns. Participation itself is paid.
- Small is not punished. Payout rules tilt toward smaller systems, on purpose.
- No gatekeepers. No registry, foundation, admin key, or founder privilege. Ever.
- Verifiable by ordinary people. A full node must stay runnable on Pi-class hardware forever.
- The founder exits. After genesis, nobody runs this chain.

## 3. The node system

The unit of the whole design is the node system. Not the machine:

- One node controller. Runs the full node software. Validates. Stores the chain. Builds its own block templates. Integrated in the enclosure. Or a Pi-class companion on the same home network, under the same owner.
- Hash units (Bitaxe-class boards) attached to that controller. In any number.
- One identity key, held in a secure element (see §4).
- One bond of 5 coins (see §6).

The cap applies to the system's total credited work. Not per board. Five boards past the cap earn exactly what one board at the cap earns: the cap. Stacking boards buys redundancy. Not income. A factory is simply many node systems. Each with its own controller, identity, and bond.

Class envelope for hash units: dedicated miners. ≤200W per unit. Home-quiet (≤~40 dB). Open schematics and firmware. Low-hundreds-of-dollars class. Laptops, desktops, GPUs, and industrial ASICs are not hash units.

## 4. Identity: the secure element is the wall, and the meter

Mutu uses SHA-256. An industrial ASIC's work is cryptographically valid. Exclusion cannot come from the puzzle. It comes from whose work the chain will credit at all:

1. Only registered node systems may mine. A block or share not signed by a registered identity key is invalid. Whatever proof-of-work is attached.
2. The identity key lives in a secure element. An ATECC608-class chip, ~$1. Generated inside the element. Non-exportable.
3. No gatekeeper. Secure elements ship from silicon vendors with factory certificate chains. Registration means presenting that chain plus the element's public key on-chain. Trust roots are the silicon vendors. At least three independent vendors, frozen into the genesis block. Not a founder, foundation, or manufacturer whitelist. Anyone with a genuine element can register. Including DIY builders.
4. The element is a rate meter. Shares count only if co-signed by the element. The element enforces a maximum co-signing rate at the epoch cap. Feeding an industrial machine's work through one attested identity gains nothing. The meter will not sign faster than a class device could work.
5. Anonymous attestation. Registration uses DAA-style group attestation. A system proves "genuine metered element from an accepted vendor, and this identity has not registered before" via a one-time nullifier. Without revealing the element's serial number. Miners are not publicly trackable by device. One element cannot mint two identities.
6. Activation queue. A new identity becomes eligible to produce blocks and receive the dividend only after its bond is filled. Two full windows (56 days) of credited work. Clearing a queue capped at +10% of the eligible set per window. Doubling the eligible set takes ≥8 windows (~224 days). Even if one buyer takes every slot. In public, while honest systems keep activating. The queue engages at 1,000 eligible systems. Before that, the seed phase activates on bond + work history alone. Including the founder's system #1. Earnings escrowed until activation.
7. Mandatory per-epoch identity rotation. At each epoch boundary every identity rotates to a fresh key. Bond carried over. Breaking longitudinal linkability of a device's history.
8. Legacy path. Devices without an element (today's Bitaxes) may register a software identity and mine pro-rata. The dividend requires an attested identity.
9. Money keys are not mining keys. The element signs work only. Never spends. Payouts go to a separate wallet address controlled by the operator. A dead or stolen miner never costs its owner their earnings.
10. Compromised-root containment. If fraud proofs from one vendor root pass a protocol threshold, new registrations from that root pause automatically. Existing miners from every root keep mining. The chain never stops.

## 5. The power cap: 80 watts per system

The per-system cap is 80 watts. Enforced as a frozen credited-TH/s schedule. The chain meters TH/s. The watt promise is implemented as a table fixed at genesis from best-purchasable silicon efficiency. Improving ×0.85 per epoch. Never governable:

| Epoch | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Credited cap (TH/s) | 4.57 | 5.38 | 6.33 | 7.44 | 8.76 | 10.30 | 12.12 | 14.26 | 16.78 | 19.74 |

A Bitaxe Gamma (1.2 TH/s, ~20W) is a citizen at 26% of the epoch-0 cap. The cap is denominated in watts. A system's maximum power, heat, and noise are bounded forever. Income ratios between device classes stay constant across epochs. Modelling (see §9) rejected a doubling TH/s cap. It disenfranchised entry devices by epoch 3.

## 6. Issuance: the mesa and the tail

Blocks arrive every 10 minutes. Epochs are 210,000 blocks (~4 years).

| Epoch | Years | Reward/block | Issuance | Cumulative |
|---|---|---|---|---|
| 0 | 0-4 | 8 | 1.68M | 1.68M |
| 1 | 4-8 | 12 | 2.52M | 4.20M |
| 2 | 8-12 | 18 | 3.78M | 7.98M |
| 3 | 12-16 | 26 (peak) | 5.46M | 13.44M |
| 4 | 16-20 | 26 (plateau) | 5.46M | 18.90M |
| 5 | 20-24 | 18 | 3.78M | 22.68M |
| 6 | 24-28 | 12 | 2.52M | 25.20M |
| 7 | 28-32 | 8 | 1.68M | 26.88M |
| 8 | 32-36 | 4 | 0.84M | 27.72M |
| 9 | 36-40 | 2 | 0.42M | 28.14M |
| 10+ | 40- | 1.0 tail, forever | 52,596/yr | inflation ~0.19%/yr at tail start, falling forever |

The schedule rises (small → big, so early miners are not kings). Plateaus. Glides down in steps never worse than Bitcoin's 2:1 halving. Then drips 1 coin per block forever. The tail is Monero-precedented. Funds the dividend and the security floor permanently at a small, shrinking inflation rate. Mutu has no hard cap. Does not claim to be digital gold. The earliest blocks pay the smallest rewards on the curve. Being first is worth the least. The founder's advantage is symbolic. Not economic.

## 7. Payouts: 49 / 28 / 23

Every block subsidy splits the same way in every epoch. After a 2% commons share (§8).

| Slice | Share | Who receives it |
|---|---|---|
| Producer | 49% (+ all fees) | The system whose valid block is accepted |
| Work | 28% | Every system with credited work in the window, pro-rata to capped credited work |
| Sovereign dividend | 23% | Qualifying sovereign systems only, weighted by √(credited work) |

- Producer (49%). Producing the block is the scarce, useful act. Earns the largest single slice. Plus all transaction fees. A system's chance of producing is proportional to its capped credited work.
- Work (28%). Participation itself pays. Any registered system that submits credited work in a window receives this slice. Including systems whose work is delegated to a pool.
- Sovereign dividend (23%). Qualification: attested identity. Bond filled. Activated. Work not delegated that window. Sustained credited work ≥25% of the average system's credited work that window. Split by √(credited work). A small system earns a higher dividend per unit of work than a large one. A large system still receives a larger total. Modelled at epoch 3: a Gamma-class system's dividend rate per TH/s is ~2.3× an at-cap system's. If the qualifying set is ever empty, the slice rolls into the work pool. Issuance is conserved in every window.
- Pools: legal, bounded, dividend-free. A pool may coordinate any number of systems. Delegated work still earns the work slice directly. When delegated work produces a block, the producer slice goes into a protocol-locked payout spendable only pro-rata to contributors. Operator's fee capped at 5%. Delegated work earns no dividend that window. Modelled: at 20% delegation, a delegated Gamma earns ~59% of an identical sovereign Gamma's income with much lower variance. Pooling is a real choice (stability for income). Never the dominant strategy. High delegation is self-penalising. An 80%-pooled world pays members ~3.7× to de-pool.
- Settlement. Window accounts settle one full window after the work window closes. Paid only from blocks deep in the most-work chain. Reorganizations can change unpaid calculations. Never claw back settled income.

Worked scale (epoch 3, 10,000 systems, after commons, at 20% delegation): sovereign Gamma ≈ 63 coins/yr (63-140 across 20-80% delegation). Sovereign Apollo-class ≈ 330 (330-529). Delegated Gamma ≈ 37 with near-zero variance (flat across delegation shares). Per-system income falls as the network grows. The promise is access, a producer's premium, and a dividend tilted toward the small. Not a wage guarantee.

## 8. The commons

2% of each block reward goes to a commons fund. Governed one-identity-one-vote among registered systems. Spendable only on open node software. Independent firmware implementations. Open device designs. Repair documentation. The commons has no power over consensus. It cannot change issuance, caps, payout shares, eligibility, attestation roots, or any balance or bond. Attested devices must run open, auditable firmware.

## 9. Security model

Mutu's security is proof-of-work among registered, metered identities. Stated honestly. Not as pure proof-of-work:

- No external hash. Rented SHA-256, an industrial fleet, or a state cannot produce a valid block without a registered identity and element co-signatures at capped rate.
- Most-work chain selection. Nodes follow the valid chain with the most accumulated work, as Bitcoin does. Separated networks heal on reconnection. The one-window settlement delay ensures payouts come only from deeply buried blocks.
- No flash majority. Rewriting recent history needs a majority of eligible systems. Eligibility cannot be bought quickly (§4). At ~$250 all-in per system, a bare majority at 10,000 systems is ~$1.25M in hardware plus ≥224 days of public buildup.
- Bounded majority power. A majority can censor and reorganize recent blocks. It cannot mint coins, move balances, forge identities, or change any rule. Every full node rejects invalid blocks regardless of producer.
- Recovery fork. Registrations are on-chain and timestamped. An attacking cohort is identifiable as a cohort. If a bought majority acts, honest operators fork from the last pre-attack block. Carrying the eligible set as of a pre-attack snapshot. Deactivating the attacking registrations. The attacker's hardware, bonds, and coins remain on the abandoned chain. The economic network continues on the fork. A successful capture gets forked away. Which is the deterrent.
- No governance capture. No admin keys, upgrade keys, pause functions, or discretionary powers anywhere. Changing the rules requires a voluntary hard fork every operator may refuse.
- Tor-native networking and launch. Nodes can run entirely as Tor onion services. No public IP. No clearnet presence required. Genesis, software, and this paper are published through a v3 onion service. Mirrored by anyone. The founder publishes and operates under Tor from day one, Satoshi-style.
- Residual risk, named. Absolute attack cost is small while the network and the coin's value are small. The safety condition is that participation grows ahead of price (~1,000+ eligible systems per $1 of coin price). A patient attacker who buys a genuine majority of real systems over many months cannot be stopped by any rule here. Only priced, slowed, exposed, and forked away. That is the honest limit of the design. The same limit Bitcoin has, reached by a different road.

## 10. Privacy (v0.5.2 locked; v0.6 decided, not yet implemented)

Locked: Tor-native operation. Anonymous attestation (no serial numbers on-chain). Mandatory per-epoch identity rotation. Money keys separated from mining keys.

(v0.6, decided, not yet implemented): a four-layer transaction privacy package. Dandelion++ relay over Tor (network layer). Silent Payments (recipient unlinkability at zero on-chain cost). Confidential amounts via Pedersen commitments with Bulletproof range proofs (amounts hidden while total issuance stays publicly verifiable). Ring signatures ×16 (sender anonymity). This requires pivoting the transaction layer to UTXO. The mining layer above is unchanged. Issuance and payouts stay transparent by design. Citizens can audit the mint. Public mint, private money. Modelled cost: full privacy ≈ 2,600 bytes per transaction. ~111,000 transactions/day at a 2 MB block cap. ~1 second of verification per block on Pi-class hardware.

## 11. Launch gates

Mainnet launches only when all of these hold:

1. ≥2 independent node implementations.
2. ≥3 attestation vendors shipping, none above ~50% of eligible systems.
3. Eligible-system count ahead of the participation-vs-price safety line.
4. An independent security audit, published.
5. No premine, no founder allocation, no admin keys. Genesis rules frozen in the genesis block. Founder registers system #1 under identical rules and exits.

## 12. Roadmap status (October 2026)

- Spec v0.5.2. Locked. Simulations (payouts, delegation, watt cap, issuance smoothing). Done. Testnet prototype with live chain, mempool transfers, and a Stratum bridge for real Bitaxe hardware. Running. Adversarial test pack 15/15 passing. Remaining before mainnet: peer-to-peer networking. Header validation. Anonymous-attestation group signatures. Second implementation. Vendor diversity. Audit. And v0.6 implementation.

## References

- Nakamoto, S. (2008). *Bitcoin: A Peer-to-Peer Electronic Cash System.*
- Swartz, L. (2018). "What was Bitcoin, what will it be? The techno-economic imaginaries of a new money." *Cultural Studies* 32(4).
- Monero Project. Ring signatures, RingCT, and permanent tail emission.
- Bitcoin BIPs 152 (compact blocks), 157/158 (light-client filters), 352 (Silent Payments).
- Miller, A. et al. (2015). Nonoutsourceable puzzles (on preventing work delegation theft).
