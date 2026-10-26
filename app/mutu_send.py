"""
MUTU TESTNET — SEND COINS (testnet v0.2 tool)

Send coins between wallets on the testnet chain, signed by the sender's
wallet key. Two modes:
- Live chain STOPPED: the transfer is applied to the saved chain directly.
- Live chain RUNNING: the signed transfer is queued in the mempool
  (data/txpool) and the live chain verifies + settles it on its next
  window — the same wallet -> mempool -> chain path a real network uses.

Fee model matches the spec prototype: flat 0.05 coins, routed to the
producer fee sink in the accounting (conservation is preserved).
"""
import hashlib
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mutu_testnet import VendorRoot, Chain  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE, "data", "chain_state.json")
HEARTBEAT = os.path.join(BASE, "data", "heartbeat.txt")
TXPOOL_DIR = os.path.join(BASE, "data", "txpool")
FEE = 0.05


def live_running():
    try:
        with open(HEARTBEAT) as f:
            return time.time() - float(f.read().strip()) < 20
    except (OSError, ValueError):
        return False


def main():
    if not os.path.exists(STATE_FILE):
        print("No saved chain found. Run START_LIVE first and let it save.")
        return
    with open(STATE_FILE) as f:
        payload = json.load(f)
    root = VendorRoot.from_key_bytes(bytes.fromhex(payload["root_key"]))
    chain = Chain.from_dict(root, payload["chain"])

    systems = list(chain.systems)
    print("Wallets on the chain:")
    for i, s in enumerate(systems, 1):
        bal = chain.balances.get(s.address, 0.0)
        print(f"  {i}. {s.name:28} balance {bal:10.2f}   {s.address}")
    print(f"  (height {chain.height}, window {chain.window}, "
          f"issued {chain.total_issued:.2f})")

    try:
        src_i = int(input("\nSend FROM which wallet number? ").strip())
        sender = systems[src_i - 1]
    except (ValueError, IndexError):
        print("Not a valid wallet number. Nothing sent.")
        return

    to_addr = input("Send TO which address? (paste a mutu... address, "
                    "or a wallet number) ").strip()
    if to_addr.isdigit() and 1 <= int(to_addr) <= len(systems):
        to_addr = systems[int(to_addr) - 1].address
    if not to_addr.startswith("mutu"):
        print("That doesn't look like a Mutu address. Nothing sent.")
        return
    if to_addr == sender.address:
        print("That is the sender's own wallet. Nothing sent.")
        return

    try:
        amount = float(input("How many coins? ").strip())
    except ValueError:
        print("Not a number. Nothing sent.")
        return
    if amount <= 0:
        print("Amount must be positive. Nothing sent.")
        return

    # Sign the transfer with the sender's WALLET key (money key, not the
    # identity element — spec section 4: the element can never spend).
    nonce = uuid.uuid4().hex[:12]
    msg = f"mutu-tx|{sender.address}|{to_addr}|{amount:.2f}|{nonce}".encode()
    sig = sender.wallet.sign(msg)
    txid = hashlib.sha256(sig + msg).hexdigest()[:16]

    # If the live chain is running, DON'T touch its state file (it would
    # overwrite this file on its next save). Queue the signed transfer in the
    # mempool instead — the live chain verifies and settles it next window.
    if live_running():
        if chain.balances.get(sender.address, 0.0) < amount + FEE:
            print(f"Insufficient balance (need amount + {FEE} fee). "
                  "Nothing sent.")
            return
        os.makedirs(TXPOOL_DIR, exist_ok=True)
        tx = {"txid": txid, "from": sender.address, "to": to_addr,
              "amount": amount, "fee": FEE, "nonce": nonce,
              "sig": sig.hex()}
        with open(os.path.join(TXPOOL_DIR, txid + ".json"), "w") as f:
            json.dump(tx, f)
        print(f"\nQUEUED in mempool: {amount:.2f} coins from {sender.name} "
              f"to {to_addr}")
        print(f"receipt #{txid} — the live chain settles it within a "
              "window (~seconds). Watch the explorer's Transfers table.")
        return

    if not chain.transfer(sender, to_addr, amount, fee=FEE, txid=txid):
        print(f"Insufficient balance (need amount + {FEE} fee). Nothing sent.")
        return

    payload["chain"] = chain.to_dict()
    payload.setdefault("tx_log", []).append(
        {"txid": txid, "from": sender.address, "to": to_addr,
         "amount": amount, "fee": FEE, "height": chain.height,
         "nonce": nonce, "sig": sig.hex()})
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f)
    os.replace(tmp, STATE_FILE)

    print(f"\nSENT: {amount:.2f} coins from {sender.name} to {to_addr}")
    print(f"fee {FEE:.2f} | tx receipt #{txid}")
    print(f"sender's new balance: {chain.balances[sender.address]:.2f}")
    print("Restart START_LIVE: the explorer balances will show the move.")


if __name__ == "__main__":
    main()
