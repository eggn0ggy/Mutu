# Join Mutu: The Small Miner's Guide

*No coding needed. No warehouse needed. A small miner, a home internet connection, and an evening.*

## What to buy

- **A Bitaxe-class miner.** A small, quiet, dedicated mining box, roughly $60-400. The reference example is the Bitaxe Gamma at about $77 (unit + stand + power supply). Any maker or DIY build in the class works. There is no official box. There never will be.
- **A node controller.** Either a box with the full node built in (Apollo-style), or a small Pi-class computer on the same home network as the miner. The controller runs the node software. The miner does the hashing. Together, one *node system*.
- **Power.** About $2-4 a month at typical home electricity prices for a ~20-35W setup. Sounds like a whisper fan. Not a server room.

Not needed: a laptop sacrificed to mining (laptops are out by design), an industrial machine, or any coins to start.

## Setup, in plain steps

1. **Unbox and plug in.** Miner on Wi-Fi, controller on the same network, both powered.
2. **Install the node software** from the project's public release. See the anonymity guide for why publication is pseudonymous. The software is open. The founder is unnamed. That is normal here.
3. **Register the system.** The miner's security chip presents its factory certificate on-chain. No office approves anything. Registration is a transaction, not an application. The payout address is the operator's own wallet key. The chip can never spend the coins.
4. **Start working.** From day one the system earns the work slice, held in escrow while the deposit fills.
5. **Fill the deposit without buying coins.** The protocol holds back the first earnings until 5 coins are saved up as the bond. At early-network scale that takes roughly 6 weeks. Nobody needs coins to start.
6. **Wait out activation.** After 56 days of credited work plus a turn in the activation queue, the system becomes eligible for block production and the dividend. From then on, the system earns all three slices.
7. **Watch it work.** The node software shows balances, work, and dividend. The public explorer shows the whole network's fairness, verifiable from the operator's own machine.

## What a system earns

- **Every round:** a share of the 28% work slice, proportional to capped work. Steady, visible, from day one (escrowed until activation).
- **Sometimes:** the 49% producer slice when the system finds a block, plus that block's fees. The jackpot.
- **Every round, once activated and solo:** a share of the 23% dividend, tilted toward small systems. A Gamma-class system earns about 2.3× the dividend rate of a maxed-out system.
- **Modelled scale (epoch 3, 10,000 systems, at 20% delegation):** a sovereign Gamma earns roughly 63 coins a year (63-140 across 20-80% delegation). That is the design's promise. Access and a fair tilt. Not a wage guarantee. Income falls per system as the network grows. That is true of every coin. Mutu doesn't hide it.

## What NOT to do

- **No laptop or desktop mining.** Not supported. Not rewarded. It cooks a daily machine. Dedicated boxes only.
- **No industrial ASICs pointed at it.** Without a registered security chip, the work is ignored. With one chip, the chip's speed limit caps it. Either way it gains nothing.
- **No buying 50 boards for 50 dividends.** The cap is per *system*, not per board. Boards past the cap earn nothing extra. They buy redundancy, not income. Fifty systems means fifty controllers, fifty chips, fifty bonds.
- **No joining a pool for the dividend.** Pools pay the work slice and share producer wins. Pooled work earns no dividend that round. Pool for steadier income. Stay solo for the dividend.
- **Do not lose the wallet key.** The miner's chip can't spend, so a dead miner never costs the earnings. A lost wallet key loses the coins themselves. Back up the seed phrase like cash. Because it is.

## FAQ

**Coding knowledge needed?** No. Setup is plugging things in and following a guide.
**Loud or hot?** No. ~20-35W, a whisper fan, less heat than a game console at idle.
**Quitting?** Yes. Exit cleanly and the 5-coin bond comes back.
**Old Bitaxe without a security chip?** Yes. Software identities mine pro-rata. The dividend needs an attested chip. The installed base has years to turn over before that matters.
**Who to complain to if something breaks?** No one is in charge. That is the design. The community, the open code, and the commons-funded documentation are the support system. That sounds scary. It is also the reason no one can switch the rules off.
**When to join?** At mainnet launch, after the gates in `launch-checklist.md` are met. The testnet is open for practice before that.
