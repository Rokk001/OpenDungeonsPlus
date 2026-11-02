# AI levels

The keeper AI has five levels: Easy, Medium, Normal, Hard and Hell. All use the same rules and information available to a human keeper.

## Level values

| Parameter | Unit | Easy | Medium | Normal | Hard | Hell |
|---|---|---:|---:|---:|---:|
| Rho | cycles per minute | 12 | 15 | 20 | 25.433 | 30 |
| Pi | probability | 0.4 | 0.55 | 0.75 | 0.909 | 0.99 |
| ScanPeriod | seconds | 120 | 80 | 45 | 24.834 | 10 |
| ClickShare | share | 0.3 | 0.42 | 0.6 | 0.806 | 1.0 |
| MistakeMultiplier | factor | 4.555556 | 3.444444 | 2.333333 | 1.944444 | 0.555556 |
| EstimateNoise | ln units | 0.206 | 0.164 | 0.132 | 0.106 | 0.049 |
| TacticTemperature | ln units | 2.0 | 0.7 | 0.45 | 0.4 | 0.35 |
| AttackAdvantage | ln units | -1.2 | -1.15 | -1.1 | -1.05 | -1.0 |
| FocusFire | probability | 0.62 | 0.698 | 0.758 | 0.807 | 0.914 |
| RetreatThreshold | ratio | 0.603 | 0.661 | 0.706 | 0.743 | 0.823 |
| TunnelDetour | factor | 0.215 | 0.176 | 0.146 | 0.122 | 0.068 |
| TacticPriorAllin | share (the five sum to 1.00) | 0.34 | 0.33 | 0.32 | 0.31 | 0.3 |
| TacticPriorSingle | share (the five sum to 1.00) | 0.58 | 0.465 | 0.35 | 0.23 | 0.12 |
| TacticPriorSplit | share (the five sum to 1.00) | 0.04 | 0.12 | 0.2 | 0.25 | 0.3 |
| TacticPriorRaid | share (the five sum to 1.00) | 0.01 | 0.015 | 0.02 | 0.025 | 0.03 |
| TacticPriorCounter | share (the five sum to 1.00) | 0.03 | 0.07 | 0.11 | 0.185 | 0.25 |
| EnemyManaEstimate | mode | own | own | own | own | observed |

## Mistakes

For a row multiplier of 1, the mistake probabilities are:

| Class | Easy | Medium | Normal | Hard | Hell |
|---|---:|---:|---:|---:|---:|
| routine | 0.091 | 0.069 | 0.047 | 0.039 | 0.011 |
| rule | 0.410 | 0.310 | 0.210 | 0.175 | 0.050 |
| complex | 0.729 | 0.551 | 0.373 | 0.311 | 0.089 |
| unfamiliar | 0.850 | 0.850 | 0.607 | 0.506 | 0.144 |
| rare | 0.850 | 0.850 | 0.850 | 0.850 | 0.306 |

A decision's probability is its class base rate times its row multiplier and level multiplier, clipped to 0.004–0.85. The class base rates are 0.02 (routine), 0.09 (rule), 0.16 (complex), 0.26 (unfamiliar) and 0.55 (rare). Table values are rounded to three decimal places. Hard limits and legality checks have no mistake roll. E20 and H04 are coordinator rows without simulated effect; their effect on win rates was not simulated.

## Campaign unlock

Hell is available in the campaign after finishing the campaign on Hard. It is always available in skirmish.

## Reactions

Let S be ScanPeriod. Action latency is a lognormal draw with mean 0.72 seconds and standard deviation 0.217 seconds.

| Kind | Delay |
|---|---|
| alert | With probability Pi, an exponential draw with mean 60 / Rho seconds; otherwise an exponential draw with mean S. Add action latency. |
| symptom | An exponential draw with mean S, multiplied by 0.5 × (2 − Pi), plus action latency. |
| periodic | The next look follows after max(5 seconds, an exponential draw with mean S × the topic's look factor). No action latency is added to this interval. |
| internal | No reaction delay; actions still consume their configured action cost. |
| hard limit | No delay or mistake roll. |

Fixed-period looks scale by S / 60: a 600-second look has mean 10 × S. Each event draws one delay per seat, shared by all rows it triggers. Actions use a rolling click budget of 202.5 × ClickShare per minute, a minimum click gap of 0.296 seconds and the configured action times; the hand performs one action at a time.

## War

The AI estimates enemy strength from known sightings, plans an attack from its available fighters and chooses among all-in, single, split, raid, counter and waiting using level-dependent priors and scores. It explores until it knows an enemy tile and uses only information its seat has seen. Easy through Hard estimate enemy mana from their own mana; Hell estimates it from elapsed game time and enemy spells it observed.

Planning starts after 600 seconds plus a uniform draw from 0 to 120 seconds. An assault needs a known open tunnel, at least three ready fighters, an available Call to War and a legal drop tile; assaults rest for 45 seconds afterward. Fighters are sorted by current HP × raw damage per second. Group power is the sum of current HP multiplied by the sum of raw damage per second. The advantage estimate also accounts for known doors, traps, spells and heart healing.

An assault picks up and drops creatures on its own claimed ground, then uses a Call to War banner for each group target; the banner can also pull idle fighters at home. During combat it considers retreat using RetreatThreshold and selects spell targets and banner positions using FocusFire; it cannot order melee targets. Spells obey the same targeting, prices, cooldowns and limits as for a human keeper.

## Not built

No keeper command: D11 equipping and selling items; E14 Sunthorn; G03 choosing conversion or skeleton; H01 selling loot.

Built in part, with these actions not built: A01 worker share; A02 claiming; A04 and D01 paying wages; B11 selling loot and stocking the table; B12 guard duty; B13 moving potion bags; D09 carrying gift boxes; F12 reloading; G01 capture and carrying; H02 filling potion slots; J03 selecting melee targets.
