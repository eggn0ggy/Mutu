#!/usr/bin/env python3
"""
MUTU TESTNET PROTOTYPE — spec v0.5 mechanics, live in one process.

Implements, end to end:
- Emulated secure elements (Ed25519 keys, testnet vendor-root certificates,
  one-time nullifiers, hardware rate-meter budget) — §4
- Registration, self-funding 5-coin bond from escrowed earnings — §6
- Activation: bond + two full windows of credited work (genesis bootstrap;
  the +10%/window queue engages at 1,000 eligible systems — §4, tested below)
- Per-system credited-work cap (6 TH/s, epoch 0) — §3/§5
- Payouts on the post-commons subsidy: 49% producer / 28% work /
  23% sovereign dividend weighted by sqrt(credited work) — §7
- Delegated (pool) work: producer slice pooled and redistributed pro-rata
  minus a 2% operator fee; NO dividend for delegated systems — §7
- Legacy software identities: work slice only (no production, no dividend) — §4
- One-window settlement delay; wallet transfers with fees to producers — §7
- Issuance conservation check every window.

TESTNET ONLY. Time is compressed (a window is 40 blocks, not 4,032), nodes are
simulated in one process, and the cryptography is prototype-grade. This proves
the mechanics; it is not production consensus code and must never hold value.
"""
import hashlib
import math
import random
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

# ---------------- testnet parameters (spec value -> testnet compression) ----
# Issuance schedule — spec v0.5.1 smoothed hump + tail (§5).
SCHEDULE = [8, 12, 18, 26, 26, 18, 12, 8, 4, 2]   # coins/block, epochs 0-9
TAIL_SUBSIDY = 1.0                                 # forever after epoch 9
# Credited-work cap per system by epoch: the 80W watt cap as a frozen
# TH/s schedule (§5 v0.5); tail era keeps the epoch-9 cap.
CAP_SCHEDULE = [4.57, 5.38, 6.33, 7.44, 8.76, 10.30, 12.12, 14.26, 16.78, 19.74]
CAP = CAP_SCHEDULE[0]     # epoch-0 cap (kept name for the demo's meter check)
# Testnet time compression: a mainnet epoch is 210,000 blocks (~4 yrs);
# on the testnet an epoch is 10 windows so the whole hump plays in minutes.
EPOCH_WINDOWS = 10
CURRENT_CAP = CAP         # set by Chain.run_window as epochs advance


def epoch_of(window):
    # windows are 1-based once running; windows 1-10 are epoch 0, etc.
    return (max(window, 1) - 1) // EPOCH_WINDOWS


def subsidy_of(window):
    e = epoch_of(window)
    return SCHEDULE[e] if e < len(SCHEDULE) else TAIL_SUBSIDY


def cap_of(window):
    e = epoch_of(window)
    return CAP_SCHEDULE[e] if e < len(CAP_SCHEDULE) else CAP_SCHEDULE[-1]
BOND = 5.0                # coins (§6)
COMMONS_FRAC = 0.02       # 2% off the top (§9)
PRODUCER_FRAC = 0.49      # §7 (v0.5.2)
WORK_FRAC = 0.28          # §7 (v0.5.2)
DIV_FRAC = 0.23           # §7 (v0.5.2)
POOL_FEE = 0.02           # modelled operator fee (spec cap: 5%) (§7)
WINDOW_BLOCKS = 40        # mainnet 4,032 — compressed for the demo
QUEUE_THRESHOLD = 1000    # eligible systems before the queue engages (§4)
QUEUE_RATE = 0.10         # +10% of eligible set per window (§4)
SHARES_PER_TH = 10        # meter budget granularity (prototype only)

rng = random.Random(20261022)


def pub_bytes(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def address_of(key):
    return "mutu" + hashlib.sha256(pub_bytes(key)).hexdigest()[:36]


# ---------------- emulated secure element (§4) -------------------------------
def _priv_bytes(key):
    return key.private_bytes(serialization.Encoding.Raw,
                             serialization.PrivateFormat.Raw,
                             serialization.NoEncryption())


class VendorRoot:
    """Testnet stand-in for a silicon vendor's factory certificate root."""
    def __init__(self, name):
        self.name = name
        self._key = Ed25519PrivateKey.generate()

    def issue_cert(self, element_pub, nullifier):
        return self._key.sign(element_pub + nullifier)

    def key_bytes(self):
        return _priv_bytes(self._key)

    @classmethod
    def from_key_bytes(cls, b, name="TestVendor"):
        obj = cls.__new__(cls)
        obj.name = name
        obj._key = Ed25519PrivateKey.from_private_bytes(b)
        return obj


class SecureElement:
    """Software emulation of the §4 secure element: non-exportable identity
    key, vendor certificate, one-time nullifier, and a co-signing rate meter
    that physically cannot sign work faster than the cap."""
    def __init__(self, root: VendorRoot):
        self._key = Ed25519PrivateKey.generate()          # never leaves the element
        self.pub = pub_bytes(self._key)
        self.nullifier = hashlib.sha256(self.pub).digest()  # one element = one identity
        self.cert = root.issue_cert(self.pub, self.nullifier)
        self._meter_budget = 0.0

    def key_bytes(self):
        return _priv_bytes(self._key)

    @classmethod
    def from_key_bytes(cls, root: VendorRoot, b):
        obj = cls.__new__(cls)
        obj._key = Ed25519PrivateKey.from_private_bytes(b)
        obj.pub = pub_bytes(obj._key)
        obj.nullifier = hashlib.sha256(obj.pub).digest()
        obj.cert = root.issue_cert(obj.pub, obj.nullifier)
        obj._meter_budget = 0.0
        return obj

    def reset_meter(self, blocks, cap=None):
        self._meter_budget = (CURRENT_CAP if cap is None else cap) * blocks * SHARES_PER_TH

    def cosign_work(self, th_claim, blocks=1):
        """Co-sign a work claim. The meter refuses claims past the cap budget;
        the chain additionally credits no more than CAP per system."""
        if (not isinstance(th_claim, (int, float)) or isinstance(th_claim, bool)
                or not math.isfinite(th_claim) or th_claim < 0
                or not isinstance(blocks, (int, float)) or isinstance(blocks, bool)
                or not math.isfinite(blocks) or blocks <= 0):
            raise ValueError("invalid work claim")
        cost = th_claim * blocks * SHARES_PER_TH
        if cost > self._meter_budget + 1e-9:
            raise PermissionError("rate meter: co-signing budget exhausted")
        self._meter_budget -= cost
        return self._key.sign(f"work:{th_claim}:{blocks}".encode())


# ---------------- node system (§3) -------------------------------------------
class System:
    def __init__(self, name, device_th, element=None, delegated_to=None):
        self.name = name
        self.device_th = device_th
        self.element = element                  # None = legacy software identity
        self.delegated_to = delegated_to        # pool id or None (sovereign)
        self.wallet = Ed25519PrivateKey.generate()   # money key — separate (§4)
        self.address = address_of(self.wallet)
        self.uptime = rng.uniform(0.85, 0.99)
        self.bond = 0.0
        self.escrow = 0.0
        self.windows_worked = 0
        self.activated = False
        self.earnings = {"producer": 0.0, "work": 0.0, "dividend": 0.0, "pool": 0.0}

    @property
    def attested(self):
        return self.element is not None

    def credited(self):
        return min(self.device_th * self.uptime, CURRENT_CAP)

    def to_dict(self):
        return {"name": self.name, "device_th": self.device_th,
                "delegated_to": self.delegated_to, "uptime": self.uptime,
                "bond": self.bond, "escrow": self.escrow,
                "windows_worked": self.windows_worked, "activated": self.activated,
                "earnings": self.earnings,
                "wallet_key": _priv_bytes(self.wallet).hex(),
                "element_key": self.element.key_bytes().hex() if self.element else None}

    @classmethod
    def from_dict(cls, root, d):
        obj = cls.__new__(cls)
        obj.name = d["name"]
        obj.device_th = d["device_th"]
        obj.delegated_to = d["delegated_to"]
        obj.uptime = d["uptime"]
        obj.bond = d["bond"]
        obj.escrow = d["escrow"]
        obj.windows_worked = d["windows_worked"]
        obj.activated = d["activated"]
        obj.earnings = d["earnings"]
        obj.wallet = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(d["wallet_key"]))
        obj.address = address_of(obj.wallet)
        obj.element = (SecureElement.from_key_bytes(root, bytes.fromhex(d["element_key"]))
                       if d["element_key"] else None)
        return obj


# ---------------- the chain ---------------------------------------------------
class Chain:
    def __init__(self):
        self.height = 0
        self.balances = {}          # address -> coins (spendable)
        self.pending = []           # (release_window, address, amount, kind)
        self.commons = 0.0
        self.total_issued = 0.0
        self.window = 0
        self.systems = []
        self.pool_fees = 0.0
        self.seen_txids = set()     # settled transfer receipts (replay guard)

    def register(self, system):
        assert all(s.element is None or s.element.nullifier != getattr(system.element, "nullifier", None)
                   for s in self.systems), "duplicate nullifier: one element, one identity"
        self.systems.append(system)
        self.balances.setdefault(system.address, 0.0)
        return len(self.systems)  # registration number (founder = 1)

    # -- schedule (§5) -----------------------------------------------------------
    def subsidy(self):
        return subsidy_of(self.window)

    def cap(self):
        return cap_of(self.window)

    # -- one block -------------------------------------------------------------
    def mine_block(self, fee_pot):
        producers = [s for s in self.systems if s.attested]  # legacy cannot produce (§4)
        weights = [s.credited() for s in producers]
        winner = rng.choices(producers, weights=weights)[0]
        self.height += 1
        sub = self.subsidy()
        self.total_issued += sub
        net = sub * (1 - COMMONS_FRAC)
        self.commons += sub * COMMONS_FRAC
        return winner, net * PRODUCER_FRAC

    # -- one window --------------------------------------------------------------
    def run_window(self):
        global CURRENT_CAP
        self.window += 1
        CURRENT_CAP = self.cap()
        for s in self.systems:
            if s.element:
                s.element.reset_meter(WINDOW_BLOCKS, CURRENT_CAP)
        producer_due = {}   # system -> producer coins earned this window
        pool_gross = 0.0
        fee_pot = 0.0
        blocks_won = {}
        for _ in range(WINDOW_BLOCKS):
            winner, producer_coins = self.mine_block(fee_pot)
            blocks_won[winner.name] = blocks_won.get(winner.name, 0) + 1
            if winner.delegated_to:
                pool_gross += producer_coins
            else:
                producer_due[winner] = producer_due.get(winner, 0.0) + producer_coins
        net_window = self.subsidy() * WINDOW_BLOCKS * (1 - COMMONS_FRAC)

        # credited work this window
        work = {s: s.credited() for s in self.systems}
        total_work = sum(work.values())
        avg_work = total_work / len(self.systems)

        earnings = {s: {"producer": 0.0, "work": 0.0, "dividend": 0.0, "pool": 0.0}
                    for s in self.systems}
        for s, amt in producer_due.items():
            earnings[s]["producer"] += amt
        # work slice — everyone who worked, paid directly (§7)
        for s in self.systems:
            earnings[s]["work"] += net_window * WORK_FRAC * work[s] / total_work
        # pool producer redistribution to delegated contributors, minus fee (§7)
        delegated = [s for s in self.systems if s.delegated_to]
        if delegated and pool_gross > 0:
            dwork = sum(work[s] for s in delegated)
            fee = pool_gross * POOL_FEE
            self.pool_fees += fee
            self.pending.append((self.window + 1, "pool-operator", fee, "pool fee"))
            for s in delegated:
                earnings[s]["pool"] += pool_gross * (1 - POOL_FEE) * work[s] / dwork
        # sovereign dividend — attested, activated, bonded, non-delegated,
        # sustained work >= 25% of the average system (§7); sqrt-weighted
        qual = [s for s in self.systems
                if s.attested and s.activated and not s.delegated_to
                and work[s] >= 0.25 * avg_work]
        div_pool_amount = net_window * DIV_FRAC
        if qual:
            wsum = sum(math.sqrt(work[s]) for s in qual)
            for s in qual:
                earnings[s]["dividend"] += div_pool_amount * math.sqrt(work[s]) / wsum
        else:  # fallback: dividend slice rolls into the work slice (§7)
            for s in self.systems:
                earnings[s]["work"] += div_pool_amount * work[s] / total_work

        # route earnings: activated -> settlement queue; pre-activation -> escrow
        for s in self.systems:
            total = sum(earnings[s].values())
            for k, v in earnings[s].items():
                s.earnings[k] += v
            if work[s] > 0:
                s.windows_worked += 1
            if s.attested and not s.activated:
                s.escrow += total
                # bond fills first from escrow (§6)
                move = min(BOND - s.bond, s.escrow)
                s.bond += move
                s.escrow -= move
                if s.bond >= BOND and s.windows_worked >= 2:
                    s.activated = True
                    if s.escrow > 0:  # surplus settles like normal earnings
                        self.pending.append((self.window + 1, s.address, s.escrow, "escrow release"))
                        s.escrow = 0.0
            elif s.attested:
                if total > 0:
                    self.pending.append((self.window + 1, s.address, total, "payout"))
            else:
                if total > 0:  # legacy: work slice settles directly
                    self.pending.append((self.window + 1, s.address, total, "legacy payout"))
        # settle everything due this window
        due = [p for p in self.pending if p[0] <= self.window]
        self.pending = [p for p in self.pending if p[0] > self.window]
        for _, addr, amt, _kind in due:
            self.balances[addr] = self.balances.get(addr, 0.0) + amt
        return blocks_won

    # -- wallet transfer ---------------------------------------------------------
    def transfer(self, sender: System, to_address, amount, fee=0.05, txid=None):
        """Apply a wallet transfer, or return False without touching balances.

        Rejects the malformed cases a hostile mempool file could otherwise
        smuggle in: non-positive or non-finite amounts, negative fees,
        self-sends, and replays of an already-settled receipt."""
        if (not isinstance(amount, (int, float)) or isinstance(amount, bool)
                or not isinstance(fee, (int, float)) or isinstance(fee, bool)
                or not math.isfinite(amount) or not math.isfinite(fee)
                or amount <= 0 or fee < 0
                or not isinstance(to_address, str)
                or to_address == sender.address
                or (txid is not None and txid in self.seen_txids)):
            return False
        if self.balances.get(sender.address, 0.0) < amount + fee:
            return False
        self.balances[sender.address] -= amount + fee
        self.balances[to_address] = self.balances.get(to_address, 0.0) + amount
        self.balances["fee-sink"] = self.balances.get("fee-sink", 0.0) + fee
        if txid is not None:
            self.seen_txids.add(txid)
        return True

    def to_dict(self):
        return {"height": self.height, "window": self.window,
                "balances": self.balances,
                "pending": [list(p) for p in self.pending],
                "commons": self.commons, "total_issued": self.total_issued,
                "pool_fees": self.pool_fees,
                "seen_txids": sorted(self.seen_txids),
                "systems": [s.to_dict() for s in self.systems]}

    @classmethod
    def from_dict(cls, root, d):
        obj = cls.__new__(cls)
        obj.height = d["height"]
        obj.window = d["window"]
        obj.balances = dict(d["balances"])
        obj.pending = [tuple(p) for p in d["pending"]]
        obj.commons = d["commons"]
        obj.total_issued = d["total_issued"]
        obj.pool_fees = d["pool_fees"]
        # Older saves predate the replay guard; default to an empty set.
        obj.seen_txids = set(d.get("seen_txids", []))
        obj.systems = [System.from_dict(root, sd) for sd in d["systems"]]
        return obj

    def check_conservation(self):
        held = (sum(self.balances.values()) + self.commons
                + sum(s.escrow for s in self.systems)
                + sum(s.bond for s in self.systems)
                + sum(p[2] for p in self.pending))
        return abs(held - self.total_issued) < 1e-6, held


# ---------------- activation queue math (§4) ----------------------------------
def activation_schedule(eligible, requests):
    """Return how many of `requests` new systems may activate this window."""
    if eligible < QUEUE_THRESHOLD:
        return requests  # genesis bootstrap: no queue yet
    return min(requests, int(eligible * QUEUE_RATE))


# ---------------- demo ---------------------------------------------------------
def main():
    print("=" * 76)
    print("MUTU TESTNET — genesis")
    print("=" * 76)
    root = VendorRoot("TestVendor")
    chain = Chain()
    founder = System("founder-gamma (SYSTEM #1)", 1.2, SecureElement(root))
    nano = System("nano-4th", 4.0, SecureElement(root))
    apollo = System("apollo-10th", 10.0, SecureElement(root))
    delegated = System("gamma-delegated", 1.2, SecureElement(root), delegated_to="pool-1")
    legacy = System("legacy-bitaxe (software id)", 1.2, element=None)
    dust = System("dust-0.1th (software id)", 0.1, element=None)
    for s in [founder, nano, apollo, delegated, legacy, dust]:
        n = chain.register(s)
        print(f"  registered #{n}: {s.name:34s} payout {s.address}")

    # rate-meter demonstration: an S19's worth of claimed work behind one identity
    rogue = SecureElement(root)
    rogue.reset_meter(1)
    credited = min(104.0, CAP)
    print(f"\n  meter check: S19 claims 104.0 TH/s behind one identity -> "
          f"credited {credited:.1f} TH/s (cap). The S19 adds nothing.")

    print("\n" + "=" * 76)
    print("MINING — 7 windows x 40 blocks (testnet time compression)")
    print("=" * 76)
    for w in range(1, 8):
        won = chain.run_window()
        ok, held = chain.check_conservation()
        act = [s.name.split(" ")[0] for s in chain.systems if s.activated]
        print(f"  window {w}: blocks {won} | activated: {act or 'none yet'} | "
              f"issued {chain.total_issued:,.2f} | conservation {'OK' if ok else 'FAIL'}")
        if w == 4:
            if chain.transfer(founder, nano.address, 5.0):
                print(f"  transfer: founder -> nano 5.00 coins (fee 0.05) OK")
            else:
                print(f"  transfer: founder balance too low — skipped")

    print("\n" + "=" * 76)
    print("FINAL STATE")
    print("=" * 76)
    for s in chain.systems:
        e = s.earnings
        print(f"  {s.name:34s} balance {chain.balances.get(s.address, 0.0):8.2f} | "
              f"producer {e['producer']:7.2f} work {e['work']:6.2f} "
              f"dividend {e['dividend']:6.2f} pool {e['pool']:6.2f} | "
              f"bond {s.bond:.1f} activated {s.activated}")
    print(f"  commons fund: {chain.commons:.2f} | pool operator fees: {chain.pool_fees:.2f} | "
          f"pending settlement: {sum(p[2] for p in chain.pending):.2f}")
    ok, held = chain.check_conservation()
    print(f"  total issued {chain.total_issued:,.2f} | total accounted {held:,.2f} | "
          f"conservation {'OK' if ok else 'FAIL'}")

    print("\n" + "=" * 76)
    print("ACTIVATION QUEUE CHECK (mainnet-scale numbers, §4)")
    print("=" * 76)
    eligible, added, windows = 1000, 0, 0
    while added < 1000:
        step = activation_schedule(eligible + added, 10**9)
        added += step
        windows += 1
    print(f"  from 1,000 eligible systems, doubling the eligible set takes "
          f"{windows} windows at the +10%/window cap (plus bond + 2 windows of work each).")

    assert ok, "conservation failed"
    div_ok = delegated.earnings["dividend"] == 0 and legacy.earnings["dividend"] == 0
    print(f"\n  dividend rules: delegated dividend = 0 -> {'OK' if div_ok else 'FAIL'}; "
          f"founder activated -> {'OK' if founder.activated else 'FAIL'}")
    print("\nTestnet demo complete. No real value exists on this chain.")


if __name__ == "__main__":
    sys.exit(main())
