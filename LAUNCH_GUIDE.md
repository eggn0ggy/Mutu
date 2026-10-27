# Mutu Testnet: Launch Guide (no coding needed)

This package is a test version of the coin. Runs on a local computer. Runs the real rules from the spec: registration, bond, activation, the cap, the 49/28/23 payouts, pool rules, settlement. Pretend coins. Compressed time. Nothing here is worth money. When it works here, the same rules are what a real launch would run.

Everything below is copy-paste. If a step fails, check Troubleshooting at the bottom before changing anything.

---

## Step 1: Install Python (one time, ~5 minutes)

1. Go to python.org → Downloads → download the Windows installer.
2. Run it. On the first screen, tick the box "Add python.exe to PATH" at the bottom. This step matters. Skip it and nothing below works.
3. Click Install Now. Close the installer when it finishes.
4. Open PowerShell. Start menu → type powershell → Enter. Paste this, then press Enter:

```
python --version
```

Expected output: something like Python 3.12.x. If so, Python is ready.

## Step 2: Get the testnet folder

1. Download the testnet zip file. Unzip it (right-click → Extract All) onto the Desktop. Result: a folder called testnet.
2. Contents (only the first two are used directly):
   - The four START_*.bat files. The launchers. Double-click these.
   - LAUNCH_GUIDE.md. This guide.
   - app. The code. No need to open anything in here.
   - output. Files the chain creates while it runs (the explorer page, share counts).
   - data. The saved chain. This file is the blockchain. Delete only to start over.
3. That's it. No other setup.

## Step 3: Launch the testnet

Double-click START_TESTNET.bat.

The first launch takes about a minute. It builds its own environment and installs one package. It needs internet for this part only. After that, launches take seconds.

Command-line alternative. Open PowerShell. Paste these one at a time:

```
cd Desktop\testnet\app
python -m pip install cryptography
python mutu_testnet.py
```

## Step 4: What the output shows

The testnet boots a tiny six-miner network. Mines 7 "windows" of blocks. Time is compressed: a window here is 40 blocks instead of 4,032.

- Registration list. Miner #1 is founder-gamma (SYSTEM #1). The address next to it is its payout wallet.
- Meter check. An S19 trying to hide behind one identity gets credited 4.57 TH/s. The cap holds.
- Window lines. Who produced each window's blocks. Around window 2 miners become activated. Their 5-coin bond filled from their own earnings, plus two windows of work. Exactly the spec rules.
- Final state. Every miner's balance. And where the money came from (producer, work, dividend, pool). Notice: the delegated miner's dividend is 0. The legacy Bitaxe earns only the work slice. The dust miner earns almost nothing.
- Conservation OK. Every coin issued is accounted for, to the coin, every window.

To stop it: it stops by itself when the demo finishes. To run it again, double-click the .bat again. Addresses are freshly generated each run on this prototype.

## Step 4b: Watch the chain live (block explorer)

The demo above runs once and ends. To watch a running chain:

1. Double-click START_LIVE.bat. Or, in PowerShell inside the testnet\app folder, paste python mutu_live.py.

2. Open the output folder. Double-click explorer.html. It opens in a browser. Refreshes itself every 2 seconds. Blocks landing. Window settlements. Bonds filling. Activations flipping to ACTIVATED. Balances moving. All visible live.
3. Stop with Ctrl+C in the PowerShell window. The chain is saved (in the data folder) after every window. Start START_LIVE again any time. It resumes at the exact height, balances, and addresses where it stopped. The SYSTEM #1 payout address is now permanent.
4. To deliberately start over from block zero: use START_FRESH.bat. It warns first and deletes the saved chain. There is no undo.

## Step 5: Point a real Bitaxe at it (when the Gamma arrives)

A Bitaxe needs no new hardware or new firmware to mine Mutu. An ASIC only does SHA-256 math. The AxeOS settings decide whose work it's doing. Switching chains is a settings change. Takes two minutes. Fully reversible.

1. Plug in the Gamma. Join it to the Wi-Fi. The Gamma screen shows its IP address, like 192.168.1.47.
2. On the computer, find the IP address. Open PowerShell. Paste ipconfig. Look for IPv4 Address (usually 192.168.1.x). Write it down.
3. Double-click START_BRIDGE.bat. If Windows Firewall asks, click Allow (private network). Leave this window open.
4. In a browser, go to the Gamma's IP address. That's its AxeOS dashboard. Open Settings and set:
   - Stratum URL: the computer's IP from step 2 (numbers only, e.g. 192.168.1.20)
   - Stratum Port: 3333
   - Stratum User: the Mutu payout address (the one printed next to SYSTEM #1. On this prototype, any address starting with mutu works)
   - Stratum Password: x
5. Save and restart the miner from the dashboard. Within a minute "share accepted" lines appear in the bridge window. The physical rig is now hashing for the testnet. Its shares are counted as credited work.
6. To switch it back to Bitcoin: in the same AxeOS settings, set Stratum URL to solo.ckpool.org, port 3333, user to a Bitcoin address. Done. Nothing about the device ever changed. AxeOS also has a fallback pool slot: Mutu can be set as primary and Bitcoin solo as fallback. The Gamma fails over automatically.

## What this testnet is, and is not

- ✅ The payout, bond, activation, cap, dividend, pool, and settlement rules from spec v0.5.2, running live.
- ✅ A real hardware path: a physical Bitaxe can hash on it through the bridge.
- ❌ Not the production software. Miners are simulated inside one program. The cryptography is prototype-grade. No internet peer-to-peer layer yet. That's the next build phase. That is why the roadmap still says independent audit before any mainnet.

## Troubleshooting

- python is not recognized. Python wasn't added to PATH. Re-run the Python installer, choose Modify, and make sure the PATH option is on. Or uninstall and reinstall and tick the box this time.
- The .bat window closes instantly. Open PowerShell and cd into the folder (Step 3 commands). Run it there so the error is visible.
- Bitaxe connects but no shares appear. Check the Gamma and the computer are on the same Wi-Fi network. Check the bridge window is still open. Check the firewall prompt was allowed.
- Port 3333 is already in use. Another mining program is using it. Close it, or change the port in app/stratum_bridge.py.
