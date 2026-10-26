# Mutu Testnet — Launch Guide (no coding needed)

This package is a **test version** of the coin, running on a local computer. It runs the real rules from the spec (registration, bond, activation, the cap, the 49/28/23 payouts, pool rules, settlement) with pretend coins and compressed time. **Nothing here is worth money.** When it works here, the same rules are what a real launch would run.

Everything below is copy-paste. If a step fails, check **Troubleshooting** at the bottom before changing anything.

---

## Step 1 — Install Python (one time, ~5 minutes)

1. Go to **python.org** → **Downloads** → download the Windows installer.
2. Run it. On the first screen, **tick the box "Add python.exe to PATH"** at the bottom. This step matters — skip it and nothing below works.
3. Click **Install Now**. Close the installer when it finishes.
4. Open **PowerShell** (Start menu → type `powershell` → Enter) and paste this, then press Enter:

```
py --version
```

Expected output: something like `Python 3.12.x`. If so, Python is ready.

## Step 2 — Get the testnet folder

1. Download the testnet zip file and unzip it (right-click → Extract All) onto the Desktop. Result: a folder called `testnet`.
2. Contents (only the first two are used directly):
   - **The three `START_*.bat` files** — the launchers. Double-click these.
   - **`LAUNCH_GUIDE.md`** — this guide.
   - **`app`** — the code. No need to open anything in here.
   - **`output`** — files the chain creates while it runs (the explorer page, share counts).
   - **`data`** — the saved chain. This file *is* the blockchain; delete only to start over.
3. That's it — no other setup.

## Step 3 — Launch the testnet

**Double-click `START_TESTNET.bat`.**

The first launch takes about a minute (it builds its own environment and installs one package — it needs internet for this part only). After that, launches take seconds.

Command-line alternative: open PowerShell, and paste these one at a time:

```
cd Desktop\testnet\app
python -m pip install cryptography
python mutu_testnet.py
```

## Step 4 — What the output shows

The testnet boots a tiny six-miner network and mines 7 "windows" of blocks (time is compressed: a window here is 40 blocks instead of 4,032):

- **Registration list** — miner #1 is `founder-gamma (SYSTEM #1)`. The address next to it is its payout wallet.
- **Meter check** — an S19 trying to hide behind one identity gets credited 6 TH/s. The cap holds.
- **Window lines** — who produced each window's blocks. Around window 2 miners become **activated** (their 5-coin bond filled from their own earnings, plus two windows of work — exactly the spec rules).
- **Final state** — every miner's balance and *where the money came from* (producer / work / dividend / pool). Notice: the delegated miner's **dividend is 0**, the legacy Bitaxe earns only the work slice, and the dust miner earns almost nothing.
- **Conservation OK** — every coin issued is accounted for, to the coin, every window.

To stop it: it stops by itself when the demo finishes. To run it again, double-click the .bat again. (Addresses are freshly generated each run on this prototype.)

## Step 4b — Watch the chain live (block explorer)

The demo above runs once and ends. To *watch* a running chain:

1. Double-click **`START_LIVE.bat`** (or, in PowerShell inside the `testnet\app` folder, paste `python mutu_live.py`).

2. Open the **`output`** folder and double-click **`explorer.html`** — it opens in a browser and refreshes itself every 2 seconds. Blocks landing, window settlements, bonds filling, activations flipping to ACTIVATED, and balances moving are all visible live.
3. Stop with **Ctrl+C** in the PowerShell window. **The chain is saved** (in the `data` folder) after every window — start START_LIVE again any time and it resumes at the exact height, balances, and addresses where it stopped. The SYSTEM #1 payout address is now **permanent**.
4. To deliberately start over from block zero: use **`START_FRESH.bat`** (it warns first and deletes the saved chain). There is no undo.

## Step 5 — Point a real Bitaxe at it (when the Gamma arrives)

A Bitaxe needs no new hardware or new firmware to mine Mutu. **An ASIC only does SHA-256 math — the AxeOS settings decide whose work it's doing.** Switching chains is a settings change, takes two minutes, and is fully reversible.

1. Plug in the Gamma and join it to the Wi-Fi (the Gamma screen shows its IP address, like `192.168.1.47`).
2. On the computer, find the IP address: open PowerShell, paste `ipconfig`, and look for **IPv4 Address** (usually `192.168.1.x`). Write it down.
3. Double-click **`START_BRIDGE.bat`**. If Windows Firewall asks, click **Allow** (private network). Leave this window open.
4. In a browser, go to the Gamma's IP address — that's its **AxeOS dashboard**. Open **Settings** and set:
   - **Stratum URL:** the computer's IP from step 2 (numbers only, e.g. `192.168.1.20`)
   - **Stratum Port:** `3333`
   - **Stratum User:** the Mutu payout address (the one printed next to SYSTEM #1 — on this prototype, any address starting with `mutu` works)
   - **Stratum Password:** `x`
5. Save / restart the miner from the dashboard. Within a minute **"share accepted"** lines appear in the bridge window — the physical rig is now hashing for the testnet, and its shares are counted as credited work.
6. **To switch it back to Bitcoin:** in the same AxeOS settings, set Stratum URL to `solo.ckpool.org`, port `3333`, user to a Bitcoin address. Done — nothing about the device ever changed. AxeOS also has a **fallback pool** slot: Mutu can be set as primary and Bitcoin solo as fallback, and the Gamma fails over automatically.

## What this testnet is — and is not

- ✅ The payout, bond, activation, cap, dividend, pool, and settlement rules from spec v0.5.2, running live.
- ✅ A real hardware path: a physical Bitaxe can hash on it through the bridge.
- ❌ Not the production software: miners are simulated inside one program, the cryptography is prototype-grade, and there's no internet peer-to-peer layer yet. That's the next build phase, and the reason the roadmap still says **independent audit before any mainnet**.

## Troubleshooting

- **`py` is not recognized** — Python wasn't added to PATH. Re-run the Python installer, choose **Modify**, and make sure the PATH option is on — or uninstall/reinstall and tick the box this time.
- **The .bat window closes instantly** — open PowerShell, `cd` into the folder (Step 3 commands), and run it there so the error is visible.
- **Bitaxe connects but no shares appear** — check the Gamma and the computer are on the **same Wi-Fi network**, the bridge window is still open, and the firewall prompt was allowed.
- **Port 3333 is already in use** — another mining program is using it. Close it, or change the port in `app/stratum_bridge.py`.
