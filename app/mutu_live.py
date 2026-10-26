#!/usr/bin/env python3
"""
MUTU TESTNET — live mode + block explorer + PERSISTENCE (v0.2).

Runs the chain continuously and keeps an `explorer.html` page updated in the
`output` folder. After every window, the full chain state AND all keys are
saved to `data/chain_state.json`. Stop it (Ctrl+C), start it again tomorrow,
next month — it resumes at the exact height, balances, and addresses where
it left off. SYSTEM #1 now has ONE permanent payout address.

To start over from genesis instead: use START_FRESH.bat (it deletes the save).
"""
import hashlib
import html
import json
import math
import os
import re
import time

from mutu_testnet import Chain, SecureElement, System, VendorRoot, epoch_of

BASE = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE, "..", "output")
DATA_DIR = os.path.join(BASE, "..", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
EXPLORER_FILE = os.path.join(OUTPUT_DIR, "explorer.html")
STATE_FILE = os.path.join(DATA_DIR, "chain_state.json")


def save_state(root, chain, recent, tx_log=None):
    payload = {"root_key": root.key_bytes().hex(),
               "chain": chain.to_dict(),
               "recent": recent[-50:],
               "tx_log": (tx_log or [])[-50:]}
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f)
    # Atomic replace, with retries: on Windows the save file can be briefly
    # locked (OneDrive sync, antivirus, an editor with it open). A locked
    # file must never kill the chain — skip this save and try next window;
    # the previous good save stays intact either way.
    import time
    for attempt in range(6):
        try:
            os.replace(tmp, STATE_FILE)
            try:
                import time as _t
                with open(os.path.join(DATA_DIR, "heartbeat.txt"), "w") as f:
                    f.write(str(_t.time()))
            except OSError:
                pass
            return
        except PermissionError:
            time.sleep(0.5)
    print("  (save skipped: chain_state.json is busy/open elsewhere — "
          "previous save intact, will retry next window)")
    try:
        import time as _t
        with open(os.path.join(DATA_DIR, "heartbeat.txt"), "w") as f:
            f.write(str(_t.time()))
    except OSError:
        pass


def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE) as f:
        payload = json.load(f)
    root = VendorRoot.from_key_bytes(bytes.fromhex(payload["root_key"]))
    chain = Chain.from_dict(root, payload["chain"])
    return root, chain, payload.get("recent", []), payload.get("tx_log", [])


def genesis():
    root = VendorRoot("TestVendor")
    chain = Chain()
    systems = [
        System("founder-gamma (SYSTEM #1)", 1.2, SecureElement(root)),
        System("nano-4th", 4.0, SecureElement(root)),
        System("apollo-10th", 10.0, SecureElement(root)),
        System("gamma-delegated", 1.2, SecureElement(root), delegated_to="pool-1"),
        System("legacy-bitaxe (software id)", 1.2, element=None),
        System("dust-0.1th (software id)", 0.1, element=None),
    ]
    for s in systems:
        chain.register(s)
    return root, chain, []


def write_explorer(chain, recent_blocks, tx_log=None):
    rows = ""
    for s in chain.systems:
        e = s.earnings
        rows += (f"<tr><td>{html.escape(s.name)}</td>"
                 f"<td>{html.escape(s.address)}</td>"
                 f"<td class='num'>{chain.balances.get(s.address, 0.0):,.2f}</td>"
                 f"<td class='num'>{e['producer']:,.2f}</td>"
                 f"<td class='num'>{e['work']:,.2f}</td>"
                 f"<td class='num'>{e['dividend']:,.2f}</td>"
                 f"<td class='num'>{e['pool']:,.2f}</td>"
                 f"<td>{s.bond:.1f} / 5.0</td>"
                 f"<td>{'ACTIVATED' if s.activated else 'pending'}</td></tr>")
    blocks = ""
    for entry in recent_blocks[-15:][::-1]:
        height, producer = entry[0], entry[1]
        sub = entry[2] if len(entry) > 2 else chain.subsidy()
        blocks += f"<tr><td>#{height}</td><td>{html.escape(producer)}</td><td>{sub:g} coins</td></tr>"
    names = {s.address: s.name for s in chain.systems}
    txs = ""
    for tx in (tx_log or [])[-15:][::-1]:
        frm = names.get(tx["from"], tx["from"][:18] + "...")
        to = names.get(tx["to"], tx["to"][:18] + "...")
        txs += (f"<tr><td>#{tx['txid']}</td><td>{html.escape(frm)}</td>"
                f"<td>{html.escape(to)}</td>"
                f"<td class='num'>{tx['amount']:,.2f}</td>"
                f"<td class='num'>{tx['fee']:.2f}</td>"
                f"<td>at height {tx['height']}</td></tr>")
    tx_section = ""
    if txs:
        tx_section = (f"<h2>Transfers</h2><table><tr><th>Receipt</th><th>From</th>"
                      f"<th>To</th><th>Amount</th><th>Fee</th><th>When</th></tr>{txs}</table>")
    ok, held = chain.check_conservation()
    page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta http-equiv="refresh" content="2">
<title>Mutu Testnet Explorer</title>
<style>
body {{ background:#0b1020; color:#e8ecf4; font-family:Georgia,serif; margin:32px; }}
h1 {{ color:#f5a623; letter-spacing:2px; }} h2 {{ color:#7fb2f0; margin-top:28px; }}
table {{ border-collapse:collapse; width:100%; margin-top:8px; }}
td, th {{ border-bottom:1px solid #26304d; padding:6px 8px; text-align:left; font-size:14px; }}
td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.stat {{ display:inline-block; margin-right:28px; font-size:18px; }}
.stat b {{ color:#f5a623; }}
</style></head><body>
<h1>MUTU — TESTNET EXPLORER</h1>
<div>
<span class="stat">Height <b>{chain.height}</b></span>
<span class="stat">Window <b>{chain.window}</b></span>
<span class="stat">Epoch <b>{epoch_of(chain.window)}</b></span>
<span class="stat">Subsidy <b>{chain.subsidy():g}/block</b></span>
<span class="stat">Issued <b>{chain.total_issued:,.2f}</b></span>
<span class="stat">Commons <b>{chain.commons:,.2f}</b></span>
<span class="stat">Conservation <b>{'OK' if ok else 'FAIL'}</b></span>
</div>
<h2>Systems</h2>
<table><tr><th>System</th><th>Payout address</th><th>Balance</th><th>Producer</th>
<th>Work</th><th>Dividend</th><th>Pool</th><th>Bond</th><th>Status</th></tr>{rows}</table>
<h2>Latest blocks</h2>
<table><tr><th>Block</th><th>Produced by</th><th>Subsidy</th></tr>{blocks}</table>
{tx_section}
<p style="color:#8fa1c7">Testnet — pretend coins, no value. Page refreshes itself. Chain state is saved after every window.</p>
</body></html>"""
    with open(EXPLORER_FILE, "w") as f:
        f.write(page)
    # Fossil guard: early builds left an explorer.html in the testnet root
    # that never updates — replace it with a redirect to the real one.
    try:
        stub = os.path.join(BASE, "..", "explorer.html")
        with open(stub, "w") as f:
            f.write('<!DOCTYPE html><meta http-equiv="refresh" '
                    'content="0; url=output/explorer.html">'
                    '<p>Moved — the live explorer is in the '
                    '<a href="output/explorer.html">output folder</a>.</p>')
    except OSError:
        pass


TXPOOL_DIR = os.path.join(DATA_DIR, "txpool")
TX_FEE = 0.05
_ADDRESS_RE = re.compile(r"^mutu[0-9a-f]{36}$")


def _validate_tx(chain, tx):
    """Return the sender System for a well-formed, honestly-signed queued
    transfer; raise ValueError otherwise. The fee is NOT taken from the
    file (it is not covered by the signature): the flat protocol fee is
    enforced here, and the receipt id is recomputed, never trusted."""
    if not isinstance(tx, dict):
        raise ValueError("transfer is not a JSON object")
    amount = tx.get("amount")
    if (not isinstance(amount, (int, float)) or isinstance(amount, bool)
            or not math.isfinite(amount) or amount <= 0):
        raise ValueError("amount must be a positive, finite number")
    if abs(float(tx.get("fee", TX_FEE)) - TX_FEE) > 1e-12:
        raise ValueError("fee does not match the flat protocol fee")
    frm, to = tx.get("from"), tx.get("to")
    if not isinstance(frm, str) or not _ADDRESS_RE.match(frm):
        raise ValueError("bad sender address")
    if not isinstance(to, str) or not _ADDRESS_RE.match(to):
        raise ValueError("bad recipient address")
    if frm == to:
        raise ValueError("self-send")
    sender = next((s for s in chain.systems if s.address == frm), None)
    if sender is None:
        raise ValueError("unknown sender")
    nonce = tx.get("nonce")
    if not isinstance(nonce, str) or not nonce:
        raise ValueError("missing nonce")
    msg = f"mutu-tx|{frm}|{to}|{amount:.2f}|{nonce}".encode()
    try:
        sig = bytes.fromhex(tx["sig"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("bad signature encoding")
    # The receipt id must be the hash of signature + message, as SEND_COINS
    # computes it; a file that invents its own id is not the signed transfer.
    if tx.get("txid") != hashlib.sha256(sig + msg).hexdigest()[:16]:
        raise ValueError("receipt id does not match the signature")
    if tx["txid"] in chain.seen_txids:
        raise ValueError("replay of an already-settled transfer")
    sender.wallet.public_key().verify(sig, msg)  # raises if forged/edited
    return sender


def process_txpool(chain, tx_log):
    """Settle queued transfers (dropped in data/txpool by SEND_COINS while
    the live chain runs — the wallet->mempool->chain path, as on mainnet).
    Each file is a wallet-signed transfer; verified, applied, logged."""
    if not os.path.isdir(TXPOOL_DIR):
        return
    for fn in sorted(os.listdir(TXPOOL_DIR)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(TXPOOL_DIR, fn)
        try:
            with open(path) as f:
                tx = json.load(f)
            sender = _validate_tx(chain, tx)
            if not chain.transfer(sender, tx["to"], tx["amount"],
                                  fee=TX_FEE, txid=tx["txid"]):
                raise ValueError("insufficient balance at settle time")
            tx_log.append({"txid": tx["txid"], "from": tx["from"],
                           "to": tx["to"], "amount": tx["amount"],
                           "fee": TX_FEE,
                           "height": chain.height})
            os.remove(path)
            print(f"  mempool: settled {tx['amount']:.2f} coins "
                  f"{sender.name} -> {tx['to'][:18]}... (#{tx['txid']})",
                  flush=True)
        except Exception as e:
            try:
                os.replace(path, path + ".rejected")
            except OSError:
                pass
            print(f"  mempool: rejected {fn}: {e}", flush=True)


def main():
    loaded = load_state()
    tx_log = []
    if loaded:
        root, chain, recent, tx_log = loaded
        founder = chain.systems[0]
        print(f"RESUMED saved chain at height {chain.height}, window {chain.window}.")
        print(f"SYSTEM #1 payout address (permanent): {founder.address}")
    else:
        root, chain, recent = genesis()
        tx_log = []
        founder = chain.systems[0]
        print("GENESIS — new chain created.")
        print(f"SYSTEM #1 payout address (permanent): {founder.address}")
        save_state(root, chain, recent, tx_log)

    original_mine = chain.mine_block

    def recording_mine(fee_pot):
        winner, coins = original_mine(fee_pot)
        recent.append([chain.height, winner.name, chain.subsidy()])
        print(f"  block #{chain.height} produced by {winner.name}", flush=True)
        return winner, coins

    chain.mine_block = recording_mine
    write_explorer(chain, recent, tx_log)
    print("Mutu testnet LIVE. Open the 'output' folder and double-click explorer.html to watch.")
    print("Ctrl+C to stop — the chain is saved and resumes where it left off.")
    try:
        while True:
            chain.run_window()
            process_txpool(chain, tx_log)
            save_state(root, chain, recent, tx_log)
            write_explorer(chain, recent, tx_log)
            print(f"  -- window {chain.window} settled | height {chain.height} "
                  f"| issued {chain.total_issued:,.2f} | saved --", flush=True)
            time.sleep(5)
    except KeyboardInterrupt:
        save_state(root, chain, recent, tx_log)
        print(f"\nStopped and saved at height {chain.height}. Run START_LIVE again to resume.")


if __name__ == "__main__":
    main()
