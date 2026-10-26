# Mutu Testnet Prototype v0.1

A runnable implementation of the Mutu spec v0.5.2 mechanics. Start with **LAUNCH_GUIDE.md** — it is written for a non-coder and is fully copy-paste.

Layout:
- Root: `START_TESTNET.bat` / `START_LIVE.bat` / `START_BRIDGE.bat` / `SEND_COINS.bat` / `RUN_TESTS.bat`, `LAUNCH_GUIDE.md`, `LICENSE`, this README.
- `app/` — the code: `mutu_testnet.py` (chain + demo network: emulated secure elements, registration/bond/activation, capped credited work, 49/28/23 payouts with settlement delay, delegated-pool accounting, legacy identities, conservation checks, activation-queue math), `mutu_live.py` (live mode + explorer generation), `mutu_send.py` (signed wallet transfers, direct or via the mempool), `mutu_tests.py` (adversarial test pack), `stratum_bridge.py` (Stratum V1 server on port 3333 for a real Bitaxe; shares counted per payout address).
- **Adversarial test pack:** `RUN_TESTS.bat` attacks a scratch copy of the testnet — schedule/conservation soak, transfer and mempool forgery, double-spend and replay, dividend/identity attacks, corrupt saves, and an abrupt kill/restart of the live chain. It never touches the saved chain in `data/`; the report lands in `output/test_report.txt`.
- `output/` — generated at runtime: `explorer.html` (self-refreshing block explorer), `stratum_shares.json`.
- `data/` — **persistence**: `chain_state.json` holds the full chain state and all system keys, atomically rewritten after every window. Live mode resumes from it (verified Oct 22, 2026: run to height 120, stop, relaunch → RESUMED at 120 with identical SYSTEM #1 address, continued to 200). `START_FRESH.bat` deletes the save (with a warning) for a new genesis.

Run the demo directly (after `python -m pip install cryptography`):

```
cd app
python mutu_testnet.py
```

Verified Oct 22, 2026: demo completes with conservation OK in all 7 windows, activation at window 2, delegated dividend = 0, S19 meter check credited at cap; bridge tested with a scripted Stratum client (subscribe/authorize/submit accepted, share recorded).

Known prototype limits: single-process simulated peers (no network layer yet), Bitcoin-format stratum jobs with stub coinbase (shares counted, not header-validated), fresh keys each run (no persistence), float accounting. All are v0.2+ work, ahead of the roadmap's independent audit.

Scope note: prototype implements v0.5.2 mining/payout mechanics; v0.6 production decisions recorded in the proposal, not implemented in the prototype.
