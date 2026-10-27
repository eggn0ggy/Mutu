# Mutu Testnet Prototype v0.1

A runnable version of the Mutu spec v0.5.2 rules. Pretend coins. Nothing here is worth money.

Start with LAUNCH_GUIDE.md. Written for someone who doesn't code. Copy-paste the whole way.

## What's here

- Root: the launchers. START_TESTNET.bat, START_LIVE.bat, START_BRIDGE.bat, SEND_COINS.bat, RUN_TESTS.bat, START_FRESH.bat. Plus LAUNCH_GUIDE.md, LICENSE, and this file.
- app/ is the actual code. mutu_testnet.py runs the chain and the demo network: emulated secure elements, registration, bond, activation, capped credited work, 49/28/23 payouts with a settlement delay, delegated-pool accounting, legacy identities, conservation checks, activation-queue math. mutu_live.py runs live mode and builds the explorer. mutu_send.py sends signed transfers, direct or through the mempool. mutu_tests.py is the attack pack. stratum_bridge.py is a Stratum V1 server on port 3333 for a real Bitaxe. Shares get counted per payout address.
- The attack pack: RUN_TESTS.bat goes after a throwaway copy of the testnet. Schedule soak. Conservation checks. Transfer validation. Mempool forgery. Double-spends. Replays. Dividend and identity exclusions. Corrupt saves. Killing and restarting the live chain mid-run. Never touches the real saved chain in data/. The report lands in output/test_report.txt.
- output/ is made at runtime. explorer.html is the block explorer, refreshes itself. stratum_shares.json is the share log.
- data/ is the save. chain_state.json holds the whole chain state plus all system keys, rewritten atomically after every window. Live mode picks up where it stopped. Checked Oct 22, 2026: ran to height 120, stopped, relaunched. Picked up at 120 with the same SYSTEM #1 address, kept going to 200. START_FRESH.bat wipes the save (with a warning) for a fresh start.
- docs/ holds the reading. whitepaper.md makes the plain-language case. spec-v0.5.2.md is the full rulebook. citizens-guide.md is the small miner's guide.

## Run it

First:

python -m pip install cryptography

Then:

cd app
python mutu_testnet.py

## Checked Oct 22, 2026

Demo finishes with conservation OK in all 7 windows. Activation at window 2. Delegated dividend = 0. S19 meter check credited at cap. Bridge tested against a scripted Stratum client. Subscribe, authorize, submit all accepted. Share recorded.

## What it can't do yet

One process, fake peers. No network layer yet. Stratum jobs are Bitcoin-format with a stub coinbase, so shares get counted but headers aren't validated yet. Fresh keys every run. No persistence across demo runs. Float accounting, not integer units. All of that is v0.2+ work, before any independent audit.

## Scope

This prototype runs the v0.5.2 mining and payout rules. The v0.6 production calls live in the proposal. Not built here yet.
