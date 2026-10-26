#!/usr/bin/env python3
"""
MUTU TESTNET — adversarial test pack.

Run with RUN_TESTS.bat (Windows) or:  python app/mutu_tests.py

The pack tries to rob, corrupt, desync, and outsmart a SCRATCH copy of the
testnet. It never opens, writes, or deletes the real saved chain in
data/chain_state.json: core tests run in memory, and every filesystem test
stages a throwaway copy of the app under the OS temp folder.

Covered: schedule math across every epoch boundary incl. the tail,
conservation during a 115-window soak, settlement delay, bond/activation,
transfer validation, mempool forgery / fee tampering / replay / double
spend, rate-meter and credited-cap limits, dividend rules (split-identity
premium, delegated and legacy exclusion, qualification threshold), pool
redistribution, activation-queue math, save/load round-trip, corrupt-save
handling, and an abrupt-kill/restart of the live chain.

Exit code 0 = every test passed. The report is written to
output/test_report.txt.
"""
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)
REPORT_FILE = os.path.join(ROOT_DIR, "output", "test_report.txt")
sys.path.insert(0, APP_DIR)

import mutu_testnet as mt  # noqa: E402

RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    mark = "PASS" if ok else "FAIL"
    line = f"[{mark}] {name}" + (f" — {detail}" if detail else "")
    print(line, flush=True)


def check(name, condition, detail=""):
    record(name, bool(condition), detail)
    return bool(condition)


def approx(a, b, tol=1e-6):
    return abs(float(a) - float(b)) <= tol


def run(name, fn):
    try:
        fn()
    except Exception:
        detail = traceback.format_exc(limit=3).strip().splitlines()[-1]
        record(name, False, f"exception: {detail}")


def make_system(name, th, root, delegated_to=None, legacy=False,
                uptime=1.0, activated=False):
    element = None if legacy else mt.SecureElement(root)
    s = mt.System(name, th, element, delegated_to=delegated_to)
    s.uptime = uptime
    if activated:
        s.activated = True
        s.bond = mt.BOND
    return s


def make_chain(systems):
    chain = mt.Chain()
    for s in systems:
        chain.register(s)
    return chain


# --------------------------------------------------------------------------
# Schedule + soak
# --------------------------------------------------------------------------

def test_schedule_table():
    cases = [
        # window, epoch, subsidy, cap
        (1, 0, 8, 4.57), (10, 0, 8, 4.57),
        (11, 1, 12, 5.38), (20, 1, 12, 5.38),
        (21, 2, 18, 6.33), (30, 2, 18, 6.33),
        (31, 3, 26, 7.44), (40, 3, 26, 7.44),
        (41, 4, 26, 8.76), (50, 4, 26, 8.76),
        (51, 5, 18, 10.30), (61, 6, 12, 12.12),
        (71, 7, 8, 14.26), (81, 8, 4, 16.78),
        (91, 9, 2, 19.74), (100, 9, 2, 19.74),
        (101, 10, 1.0, 19.74), (500, 49, 1.0, 19.74),
    ]
    bad = []
    for window, epoch, subsidy, cap in cases:
        if mt.epoch_of(window) != epoch:
            bad.append(f"w{window} epoch")
        if not approx(mt.subsidy_of(window), subsidy):
            bad.append(f"w{window} subsidy")
        if not approx(mt.cap_of(window), cap):
            bad.append(f"w{window} cap")
    # No issuance step anywhere may be worse than a halving, incl. the tail.
    steps = [mt.SCHEDULE[i + 1] / mt.SCHEDULE[i] for i in range(len(mt.SCHEDULE) - 1)]
    steps.append(mt.TAIL_SUBSIDY / mt.SCHEDULE[-1])
    if min(steps) < 0.5 - 1e-12:
        bad.append("a step worse than 2:1 exists")
    total = sum(mt.SCHEDULE) * 210_000
    if not approx(total, 28_140_000, tol=1e-6):
        bad.append(f"40-year total {total}")
    check("Schedule table: epochs, subsidies, caps, tail, 2:1 step limit",
          not bad, "; ".join(bad) if bad else
          "28.14M over epochs 0-9, then 1.0/block forever, cap frozen at 19.74")


def test_soak_conservation():
    root = mt.VendorRoot("SoakVendor")
    chain = make_chain([
        make_system("sovereign", 1.2, root, uptime=0.97),
        make_system("delegated", 4.0, root, delegated_to="pool-1", uptime=0.93),
        make_system("legacy", 1.2, root, legacy=True, uptime=0.89),
    ])
    expected_issued = 0.0
    failures = []
    for w in range(1, 116):
        expected_issued += mt.subsidy_of(w) * mt.WINDOW_BLOCKS
        chain.run_window()
        ok, held = chain.check_conservation()
        if chain.height != w * mt.WINDOW_BLOCKS:
            failures.append(f"w{w} height {chain.height}")
        if not approx(chain.total_issued, expected_issued, tol=1e-5):
            failures.append(f"w{w} issued {chain.total_issued} != {expected_issued}")
        if not ok:
            failures.append(f"w{w} conservation held={held}")
        if not approx(chain.commons, chain.total_issued * mt.COMMONS_FRAC, tol=1e-5):
            failures.append(f"w{w} commons {chain.commons}")
        if not approx(mt.CURRENT_CAP, mt.cap_of(w)):
            failures.append(f"w{w} cap {mt.CURRENT_CAP} != {mt.cap_of(w)}")
        if failures:
            break
    check("Soak: 115 windows across the whole mesa + tail, exact issuance",
          not failures, failures[0] if failures else
          f"issued {chain.total_issued:,.2f}, height {chain.height}, conservation OK every window")


# --------------------------------------------------------------------------
# Settlement, bond, activation
# --------------------------------------------------------------------------

def test_settlement_delay():
    root = mt.VendorRoot("SettleVendor")
    solo = make_system("solo", 1.2, root, activated=True)
    chain = make_chain([solo])
    chain.run_window()
    earned_w1 = sum(solo.earnings.values())
    pending_w1 = sum(p[2] for p in chain.pending)
    bal_w1 = chain.balances.get(solo.address, 0.0)
    chain.run_window()
    bal_w2 = chain.balances.get(solo.address, 0.0)
    ok = (approx(bal_w1, 0.0) and approx(pending_w1, earned_w1)
          and approx(bal_w2, earned_w1))
    check("Settlement delay: earnings land exactly one window late",
          ok, f"w1 balance {bal_w1:.2f} / pending {pending_w1:.2f}; w2 balance {bal_w2:.2f}")


def test_bond_and_activation():
    root = mt.VendorRoot("BondVendor")
    solo = make_system("newcomer", 1.2, root, activated=False)
    chain = make_chain([solo])
    chain.run_window()
    w1 = (solo.bond, solo.windows_worked, solo.activated,
          chain.balances.get(solo.address, 0.0))
    chain.run_window()
    earned_by_w2 = sum(solo.earnings.values())
    w2 = (solo.activated, chain.balances.get(solo.address, 0.0))
    chain.run_window()
    bal_w3 = chain.balances.get(solo.address, 0.0)
    expected_release = earned_by_w2 - mt.BOND
    ok = (approx(w1[0], mt.BOND) and w1[1] == 1 and not w1[2] and approx(w1[3], 0.0)
          and w2[0] and approx(w2[1], 0.0)
          and approx(bal_w3, expected_release, tol=1e-5))
    check("Bond + activation: 5 coins self-funded, 2 windows of work, then escrow releases",
          ok, f"after w1 bond {w1[0]:.1f}; activated at w2; w3 balance {bal_w3:.2f}")


def test_activation_queue():
    ok = (mt.activation_schedule(999, 500) == 500
          and mt.activation_schedule(1000, 10 ** 9) == 100
          and mt.activation_schedule(1500, 10 ** 9) == 150)
    eligible, added, windows = 1000, 0, 0
    while added < 1000:
        added += mt.activation_schedule(eligible + added, 10 ** 9)
        windows += 1
    check("Activation queue: off below 1,000 eligible, +10%/window above it",
          ok and windows == 8, f"doubling the eligible set takes {windows} windows")


# --------------------------------------------------------------------------
# Transfers (core validation)
# --------------------------------------------------------------------------

def test_transfer_validation():
    root = mt.VendorRoot("TxVendor")
    a = make_system("alice", 1.2, root)
    b = make_system("bob", 1.2, root)
    chain = make_chain([a, b])
    chain.balances[a.address] = 20.0
    chain.total_issued = 20.0

    valid = chain.transfer(a, b.address, 5.0)
    state1 = (chain.balances[a.address], chain.balances[b.address],
              chain.balances.get("fee-sink", 0.0))
    snapshot = dict(chain.balances)
    attacks = [
        ("zero amount", lambda: chain.transfer(a, b.address, 0.0)),
        ("negative amount", lambda: chain.transfer(a, b.address, -100.0)),
        ("self-send", lambda: chain.transfer(a, a.address, 1.0)),
        ("NaN amount", lambda: chain.transfer(a, b.address, float("nan"))),
        ("infinite amount", lambda: chain.transfer(a, b.address, float("inf"))),
        ("negative fee", lambda: chain.transfer(a, b.address, 1.0, fee=-1000.0)),
        ("overdraw", lambda: chain.transfer(a, b.address, 10_000.0)),
    ]
    blocked = [name for name, fn in attacks if fn() is False]
    unchanged = all(approx(chain.balances.get(k, 0.0), v) for k, v in snapshot.items())
    replay = chain.transfer(a, b.address, 1.0, txid="receipt-1")
    replay2 = chain.transfer(a, b.address, 1.0, txid="receipt-1")
    ok = (valid and approx(state1[0], 14.95) and approx(state1[1], 5.0)
          and approx(state1[2], 0.05) and len(blocked) == len(attacks)
          and unchanged and replay and not replay2)
    check("Transfer validation: bad amounts/fees/self-sends/replays change nothing",
          ok, f"valid send settled; blocked: {', '.join(blocked)}")


# --------------------------------------------------------------------------
# Identity, meter, dividend, pools
# --------------------------------------------------------------------------

def test_meter_and_cap():
    mt.CURRENT_CAP = mt.CAP_SCHEDULE[0]
    root = mt.VendorRoot("MeterVendor")
    element = mt.SecureElement(root)
    element.reset_meter(1)
    over_budget = False
    try:
        element.cosign_work(104.0, blocks=1)
    except PermissionError:
        over_budget = True
    negative = False
    element2 = mt.SecureElement(root)
    element2.reset_meter(1)
    try:
        element2.cosign_work(-50.0, blocks=1)
    except ValueError:
        negative = True
    s19 = make_system("s19-in-a-trenchcoat", 104.0, root, uptime=1.0)
    credited = s19.credited()
    check("Rate meter + credited cap: an S19 behind one identity is just 4.57 TH/s",
          over_budget and negative and approx(credited, mt.CAP_SCHEDULE[0]),
          f"104 TH/s claim refused by meter; credited {credited:.2f} TH/s")


def test_duplicate_identity():
    root = mt.VendorRoot("DupVendor")
    shared = mt.SecureElement(root)
    chain = mt.Chain()
    chain.register(mt.System("identity-a", 1.2, shared))
    rejected = False
    try:
        chain.register(mt.System("identity-b", 1.2, shared))
    except AssertionError:
        rejected = True
    check("One secure element = one identity (duplicate nullifier rejected)",
          rejected and len(chain.systems) == 1)


def test_dividend_split_premium():
    pool = mt.SCHEDULE[0] * mt.WINDOW_BLOCKS * (1 - mt.COMMONS_FRAC) * mt.DIV_FRAC
    root_a = mt.VendorRoot("SplitA")
    target_a = make_system("target-4th", 4.0, root_a, activated=True)
    common_a = make_system("common-4th", 4.0, root_a, activated=True)
    make_chain([target_a, common_a]).run_window()
    div_single = target_a.earnings["dividend"]

    root_b = mt.VendorRoot("SplitB")
    t1 = make_system("split-2th-a", 2.0, root_b, activated=True)
    t2 = make_system("split-2th-b", 2.0, root_b, activated=True)
    common_b = make_system("common-4th", 4.0, root_b, activated=True)
    make_chain([t1, t2, common_b]).run_window()
    div_split = t1.earnings["dividend"] + t2.earnings["dividend"]

    ratio = div_split / div_single if div_single else float("inf")
    expected_single = pool * 0.5
    ok = (approx(div_single, expected_single, tol=1e-5)
          and 1.0 < ratio < math.sqrt(2))
    check("Dividend: splitting one 4 TH/s box into two identities pays a bounded premium",
          ok, f"single {div_single:.2f} vs split {div_split:.2f} (x{ratio:.3f}, cap is sqrt(2)=1.414)")


def test_dividend_exclusions():
    root = mt.VendorRoot("ExclVendor")
    sovereign = make_system("sovereign", 4.0, root, activated=True)
    delegated = make_system("delegated", 4.0, root, delegated_to="pool-1",
                            activated=True)
    dust = make_system("dust", 0.1, root, activated=True)
    chain = make_chain([sovereign, delegated, dust])
    chain.run_window()
    legacy_root = mt.VendorRoot("LegacyVendor")
    attested = make_system("attested", 4.0, legacy_root, activated=True)
    legacy = make_system("legacy", 4.0, legacy_root, legacy=True)
    make_chain([attested, legacy]).run_window()
    ok = (delegated.earnings["dividend"] == 0 and delegated.earnings["work"] > 0
          and dust.earnings["dividend"] == 0
          and sovereign.earnings["dividend"] > 0
          and legacy.earnings["dividend"] == 0
          and legacy.earnings["producer"] == 0
          and legacy.earnings["work"] > 0)
    check("Dividend exclusions: delegated, sub-threshold, and legacy systems earn none",
          ok, "delegated/legacy still earn the work slice; only sovereign qualifying systems divide the 23%")


def test_pool_redistribution():
    root = mt.VendorRoot("PoolVendor")
    delegated = make_system("only-delegated", 1.2, root, delegated_to="pool-1",
                            activated=True)
    legacy = make_system("legacy-filler", 1.2, root, legacy=True)
    chain = make_chain([delegated, legacy])
    chain.run_window()
    gross = (mt.SCHEDULE[0] * mt.WINDOW_BLOCKS
             * (1 - mt.COMMONS_FRAC) * mt.PRODUCER_FRAC)
    expected_pool = gross * (1 - mt.POOL_FEE)
    expected_fee = gross * mt.POOL_FEE
    ok = (approx(delegated.earnings["pool"], expected_pool, tol=1e-5)
          and approx(chain.pool_fees, expected_fee, tol=1e-5)
          and mt.POOL_FEE <= 0.05
          and delegated.earnings["dividend"] == 0)
    check("Pools: producer slice redistributed pro-rata, operator fee inside the 5% cap",
          ok, f"pool paid {delegated.earnings['pool']:.2f} of {gross:.2f} gross; fee {chain.pool_fees:.2f} (2% modelled)")


# --------------------------------------------------------------------------
# Filesystem tests — staged copies only, never the real chain
# --------------------------------------------------------------------------

def stage_app(tmp):
    app = os.path.join(tmp, "app")
    os.makedirs(app)
    for fn in ("mutu_testnet.py", "mutu_live.py"):
        shutil.copy2(os.path.join(APP_DIR, fn), os.path.join(app, fn))
    return app


def run_snippet(app, code, timeout=60):
    env = dict(os.environ, PYTHONPATH=app)
    proc = subprocess.run([sys.executable, "-c", code], cwd=app, env=env,
                          capture_output=True, text=True, timeout=timeout)
    return proc


def snippet_result(proc):
    for line in proc.stdout.splitlines()[::-1]:
        if line.startswith("RESULT="):
            return json.loads(line[len("RESULT="):])
    raise RuntimeError(f"no RESULT line; rc={proc.returncode}; "
                       f"stdout tail={proc.stdout[-300:]!r}; "
                       f"stderr tail={proc.stderr[-300:]!r}")


def test_save_load_roundtrip():
    with tempfile.TemporaryDirectory(prefix="mutu-test-save-") as tmp:
        app = stage_app(tmp)
        code = r'''
import json, mutu_live
root, chain, recent = mutu_live.genesis()
for _ in range(3):
    chain.run_window()
mutu_live.save_state(root, chain, recent, [])
loaded = mutu_live.load_state()
assert loaded is not None
root2, chain2, recent2, txlog2 = loaded
ok, held = chain2.check_conservation()
# A half-written .tmp from a crashed save must be ignored.
with open(mutu_live.STATE_FILE + ".tmp", "w") as f:
    f.write("{\"partial\": ")
loaded2 = mutu_live.load_state()
result = {
    "height": chain2.height, "window": chain2.window,
    "issued": chain2.total_issued,
    "balances": chain2.balances,
    "addresses": [s.address for s in chain2.systems],
    "orig_addresses": [s.address for s in chain.systems],
    "pending": sum(p[2] for p in chain2.pending),
    "orig_pending": sum(p[2] for p in chain.pending),
    "conservation": ok,
    "tmp_ignored": loaded2 is not None and loaded2[1].height == chain.height,
}
print("RESULT=" + json.dumps(result))
'''
        proc = run_snippet(app, code)
        r = snippet_result(proc)
        ok = (r["height"] == 120 and r["window"] == 3 and r["conservation"]
              and r["addresses"] == r["orig_addresses"]
              and approx(r["pending"], r["orig_pending"])
              and r["tmp_ignored"])
        check("Persistence: save/load round-trip is exact; partial .tmp ignored",
              ok, f"resumed at height {r['height']}, issued {r['issued']:.2f}, addresses stable")


def test_corrupt_save_fails_safe():
    with tempfile.TemporaryDirectory(prefix="mutu-test-corrupt-") as tmp:
        app = stage_app(tmp)
        data = os.path.join(tmp, "data")
        os.makedirs(data)
        state = os.path.join(data, "chain_state.json")
        garbage = b'{"root_key": "abcd", "chain": {"height": 12'
        with open(state, "wb") as f:
            f.write(garbage)
        proc = run_snippet(app, "import mutu_live; mutu_live.load_state()")
        with open(state, "rb") as f:
            after = f.read()
        check("Chaos: a corrupt save is rejected and left untouched (no invented chain)",
              proc.returncode != 0 and after == garbage,
              f"loader exit code {proc.returncode}; file unchanged")


MEMPOOL_SNIPPET = r'''
import hashlib, json, os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import mutu_testnet as mt
import mutu_live

root, chain, recent = mutu_live.genesis()
sender, r1, r2 = chain.systems[0], chain.systems[1], chain.systems[2]
os.makedirs(mutu_live.TXPOOL_DIR, exist_ok=True)
tx_log = []

def make_tx(to, amount, nonce, frm=None, key=None):
    frm = frm or sender.address
    key = key or sender.wallet
    msg = f"mutu-tx|{frm}|{to}|{amount:.2f}|{nonce}".encode()
    sig = key.sign(msg)
    return {"txid": hashlib.sha256(sig + msg).hexdigest()[:16],
            "from": frm, "to": to, "amount": amount, "fee": 0.05,
            "nonce": nonce, "sig": sig.hex()}

def drop(name, tx):
    with open(os.path.join(mutu_live.TXPOOL_DIR, name), "w") as f:
        json.dump(tx, f)

def rejected_count():
    return sum(1 for fn in os.listdir(mutu_live.TXPOOL_DIR)
               if fn.endswith(".rejected"))

# Batch 1: one honest transfer + broken file + edited amount + fee tamper.
chain.balances[sender.address] = 100.0
drop("01_valid.json", make_tx(r1.address, 3.0, "n-valid"))
with open(os.path.join(mutu_live.TXPOOL_DIR, "00_broken.json"), "w") as f:
    f.write("{not json")
forged = make_tx(r1.address, 4.0, "n-forged")
forged["amount"] = 4.01                      # edited after signing
drop("02_forged.json", forged)
fee_tx = make_tx(r1.address, 2.0, "n-fee")
fee_tx["fee"] = -500.0                       # fee is not signed; must be enforced
drop("03_fee.json", fee_tx)
mutu_live.process_txpool(chain, tx_log)
after_valid = chain.balances[sender.address]
rejected_1 = rejected_count()

# Batch 2: double spend — two signed 10-coin sends against a 12-coin balance.
chain.balances[sender.address] = 12.0
before_recips = chain.balances.get(r1.address, 0.0) + chain.balances.get(r2.address, 0.0)
drop("01_double_a.json", make_tx(r1.address, 10.0, "n-double-a"))
drop("02_double_b.json", make_tx(r2.address, 10.0, "n-double-b"))
mutu_live.process_txpool(chain, tx_log)
after_double = chain.balances[sender.address]
recip_gain = (chain.balances.get(r1.address, 0.0)
              + chain.balances.get(r2.address, 0.0)) - before_recips
rejected_2 = rejected_count()

# Batch 3: replay — the same signed transfer filed twice under two names.
chain.balances[sender.address] = 10.0
replay = make_tx(r1.address, 1.0, "n-replay")
drop("01_replay_a.json", replay)
drop("02_replay_b.json", replay)
mutu_live.process_txpool(chain, tx_log)
after_replay = chain.balances[sender.address]
rejected_3 = rejected_count()

# Batch 4: zero / negative / self / unknown-sender transfers, all signed.
chain.balances[sender.address] = 20.0
drop("01_zero.json", make_tx(r1.address, 0.0, "n-zero"))
drop("02_negative.json", make_tx(r1.address, -5.0, "n-negative"))
drop("03_self.json", make_tx(sender.address, 1.0, "n-self"))
ext_key = Ed25519PrivateKey.generate()
ext_addr = mt.address_of(ext_key)
drop("04_unknown.json", make_tx(r1.address, 1.0, "n-unknown",
                                frm=ext_addr, key=ext_key))
mutu_live.process_txpool(chain, tx_log)
after_invalid = chain.balances[sender.address]
rejected_4 = rejected_count()

result = {
    "after_valid": after_valid, "rejected_1": rejected_1,
    "after_double": after_double, "recip_gain": recip_gain,
    "rejected_2": rejected_2,
    "after_replay": after_replay, "rejected_3": rejected_3,
    "after_invalid": after_invalid, "rejected_4": rejected_4,
    "settled": len(tx_log),
    "fee_sink": chain.balances.get("fee-sink", 0.0),
}
print("RESULT=" + json.dumps(result))
'''


def test_mempool_attacks():
    with tempfile.TemporaryDirectory(prefix="mutu-test-mempool-") as tmp:
        app = stage_app(tmp)
        proc = run_snippet(app, MEMPOOL_SNIPPET)
        r = snippet_result(proc)
        ok = (approx(r["after_valid"], 96.95) and r["rejected_1"] == 3
              and approx(r["after_double"], 1.95) and approx(r["recip_gain"], 10.0)
              and r["rejected_2"] == 4
              and approx(r["after_replay"], 8.95) and r["rejected_3"] == 5
              and approx(r["after_invalid"], 20.0) and r["rejected_4"] == 9
              and r["settled"] == 3 and approx(r["fee_sink"], 0.15))
        check("Mempool: forgery, fee tamper, double-spend, replay, 0/negative/self/unknown all stopped",
              ok, f"3 honest transfers settled; 9 hostile files rejected; fee sink {r['fee_sink']:.2f}")


def test_live_kill_and_resume():
    with tempfile.TemporaryDirectory(prefix="mutu-test-live-") as tmp:
        app = stage_app(tmp)
        state = os.path.join(tmp, "data", "chain_state.json")
        log_path = os.path.join(tmp, "live.log")
        snapshot = None
        with open(log_path, "wb") as log:
            proc = subprocess.Popen(
                [sys.executable, "-u", os.path.join(app, "mutu_live.py")],
                cwd=app, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.time() + 30
                while time.time() < deadline:
                    if os.path.exists(state):
                        try:
                            with open(state) as f:
                                data = json.load(f)
                            if data["chain"]["height"] >= 40:
                                snapshot = data["chain"]
                                break
                        except (OSError, ValueError, KeyError):
                            pass
                    if proc.poll() is not None:
                        break
                    time.sleep(0.25)
            finally:
                if proc.poll() is None:
                    proc.kill()          # abrupt kill — no clean shutdown
                proc.wait(timeout=15)
        if snapshot is None:
            check("Chaos: live chain survives an abrupt kill and resumes", False,
                  "live chain never reached height 40")
            return
        code = r'''
import json, mutu_live
loaded = mutu_live.load_state()
assert loaded is not None
root, chain, recent, txlog = loaded
ok, held = chain.check_conservation()
print("RESULT=" + json.dumps({
    "height": chain.height, "window": chain.window,
    "issued": chain.total_issued, "conservation": ok,
    "founder": chain.systems[0].address}))
'''
        proc2 = run_snippet(app, code)
        r = snippet_result(proc2)
        founder_saved = snapshot["systems"][0]["name"]
        ok = (r["height"] == snapshot["height"] and r["conservation"]
              and approx(r["issued"], snapshot["total_issued"]))
        check("Chaos: live chain survives an abrupt kill and resumes",
              ok, f"killed mid-run; resumed at height {r['height']} "
                  f"(saved {snapshot['height']}), conservation OK")


# --------------------------------------------------------------------------

def main():
    print("=" * 76)
    print("MUTU TESTNET — ADVERSARIAL TEST PACK")
    print("Scratch chains only. The saved chain in data/ is never touched.")
    print("=" * 76)
    run("Schedule table", test_schedule_table)
    run("Soak + conservation", test_soak_conservation)
    run("Settlement delay", test_settlement_delay)
    run("Bond + activation", test_bond_and_activation)
    run("Activation queue", test_activation_queue)
    run("Transfer validation", test_transfer_validation)
    run("Rate meter + cap", test_meter_and_cap)
    run("Duplicate identity", test_duplicate_identity)
    run("Dividend split premium", test_dividend_split_premium)
    run("Dividend exclusions", test_dividend_exclusions)
    run("Pool redistribution", test_pool_redistribution)
    run("Save/load round-trip", test_save_load_roundtrip)
    run("Corrupt save", test_corrupt_save_fails_safe)
    run("Mempool attacks", test_mempool_attacks)
    run("Live kill + resume", test_live_kill_and_resume)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print("=" * 76)
    print(f"RESULT: {passed}/{total} tests passed")
    print("=" * 76)
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        f.write("MUTU TESTNET — ADVERSARIAL TEST PACK REPORT\n")
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} local time\n\n")
        for name, ok, detail in RESULTS:
            f.write(f"[{'PASS' if ok else 'FAIL'}] {name}")
            if detail:
                f.write(f" — {detail}")
            f.write("\n")
        f.write(f"\nRESULT: {passed}/{total} tests passed\n")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
