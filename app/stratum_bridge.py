#!/usr/bin/env python3
"""
MUTU TESTNET — Stratum bridge (v0.1).

Lets a REAL Bitaxe-class miner hash on the testnet. The miner talks ordinary
Stratum V1 (the same protocol it uses for Bitcoin) to this bridge running on
the node controller; the bridge counts accepted shares per payout address and
writes them to stratum_shares.json, where the testnet node reads credited work.

Point the miner at:  stratum+tcp://<controller LAN IP>:3333
Username:           a Mutu payout address (any address starting with 'mutu' works on testnet)
Password:           x

HONEST LIMITS (testnet): jobs are Bitcoin-format headers and shares are
counted, not yet validated against Mutu block rules — header/work validation
is abstract in the v0.1 prototype. This proves the hardware path end to end:
ASIC hashes -> bridge credits work -> node pays the address.
"""
import json
import os
import socketserver
import sys
import threading
import time

HOST, PORT = "0.0.0.0", 3333
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
SHARE_FILE = os.path.join(OUTPUT_DIR, "stratum_shares.json")
DIFFICULTY = 256
_lock = threading.Lock()
shares = {}


def save_shares():
    with _lock:
        with open(SHARE_FILE, "w") as f:
            json.dump(shares, f, indent=2)


def fake_job(job_id):
    # Bitcoin-format job with testnet parameters. coinb1/coinb2 are stubs in v0.1.
    return {
        "id": None,
        "method": "mining.notify",
        "params": [
            job_id,                                    # job id
            "00" * 32,                                 # prevhash
            "01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff",
            "ffffffff0100f2052a01000000434104ffff",    # coinb2 stub
            [],                                        # merkle branch
            "20000000",                                # version
            "207fffff",                                # nbits (easy testnet target)
            format(int(time.time()), "08x"),           # ntime
            True,                                      # clean jobs
        ],
    }


class Handler(socketserver.StreamRequestHandler):
    def send(self, obj):
        self.wfile.write((json.dumps(obj) + "\n").encode())

    def handle(self):
        address = "unknown"
        job_counter = [0]
        print(f"[bridge] miner connected from {self.client_address[0]}")
        for raw in self.rfile:
            try:
                msg = json.loads(raw.decode())
            except Exception:
                continue
            method = msg.get("method", "")
            mid = msg.get("id")
            if method == "mining.subscribe":
                self.send({"id": mid, "result": [
                    [["mining.set_difficulty", "1"], ["mining.notify", "1"]],
                    "12345678", 4], "error": None})
                self.send({"id": None, "method": "mining.set_difficulty",
                           "params": [DIFFICULTY]})
                job_counter[0] += 1
                self.send(fake_job(f"job{job_counter[0]}"))
            elif method == "mining.authorize":
                address = (msg.get("params") or ["unknown"])[0]
                self.send({"id": mid, "result": True, "error": None})
                print(f"[bridge] authorized miner address: {address}")
            elif method == "mining.submit":
                with _lock:
                    shares[address] = shares.get(address, 0) + 1
                    total = shares[address]
                save_shares()
                self.send({"id": mid, "result": True, "error": None})
                print(f"[bridge] share accepted from {address} (total {total}) — "
                      f"credited work recorded in {SHARE_FILE}")
                job_counter[0] += 1
                self.send(fake_job(f"job{job_counter[0]}"))
            elif method == "mining.configure":
                self.send({"id": mid, "result": {}, "error": None})
            elif method == "mining.suggest_difficulty":
                self.send({"id": mid, "result": True, "error": None})
            else:
                self.send({"id": mid, "result": None, "error": None})
        print(f"[bridge] miner {address} disconnected")


if __name__ == "__main__":
    print(f"Mutu testnet Stratum bridge listening on port {PORT}")
    print("Point a Bitaxe at this computer's LAN IP, port 3333 (see LAUNCH_GUIDE.md).")
    print("Ctrl+C to stop.")
    with socketserver.ThreadingTCPServer((HOST, PORT), Handler) as server:
        server.allow_reuse_address = True
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            sys.exit(0)
