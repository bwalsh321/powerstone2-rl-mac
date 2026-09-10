# Reddit post — draft v2 (Sep 3, plain-reader edition, no em dashes)

**Title:** My brother-in-law gave me one piece of RL advice about my Dreamcast fighting game bot. I spent a week testing it properly. Six experiments later: self-play won, my own gameplay recordings failed, and the max-difficulty wall finally cracked.

Power Stone 2 is a chaotic 4-player arena fighter from 2000: four characters brawl in a destructible arena, power stones (gems) scatter around the stage, and if you collect three you transform into a superpowered form. Last one standing wins. My agent plays it by reading 122 values straight out of the emulator's RAM every few frames (positions, healths, gem locations), zero pixels, trained with PPO on my M2 MacBook. Months of training against the game's built-in AI opponents had produced a 32M-step champion that beat medium difficulty reliably but stalled at level 5 of 8 and never moved again, no matter what I did to the rewards. Then my brother-in-law, an ML engineer who builds game bots professionally, diagnosed it over a family chat: your data is mostly easy wins, just train against max difficulty. Instead of taking his word for it, I tested it. Six training runs, 2M steps each, same starting network, one variable changed per run, identical evals for all of them.

Nearly everything failed, and the failures taught me more than the wins. Feeding max-difficulty battles to the existing champion made it worse at everything (it lost every fight, and it turns out losses contain no information about how to win). A fresh network on that diet won literally 0% of its games for an entire run, twice. The one that hurt: I recorded myself beating three max-difficulty AI opponents 23 games to 1, cloned my play into the starting network at 80% accuracy, and that agent won 8 of its 4,653 training games. My recordings had no examples of recovering from bad spots because I was never in bad spots, so the moment the clone made one mistake it was somewhere my data had never been, and it drowned. That's "covariate shift" in a textbook. It's a lot more visceral when it's your own hands failing to transfer.

What worked was self-play against a growing league of every model the project ever produced, compounded run after run. Each new generation beat its parent about 11 games to 1, and on a held-out test (a stage and opponent lineup it never trains on) its win rate climbed 40, 42, 50, 64, 78, 82, 84, 86 percent across seven runs, closing on the old champion's 98 that took a month to build. Head to head over 50 games it now beats that champion 29 to 21, and it collects more gems and transforms more often per match than the champ does. Full disclosure, because you'd find it in the repo anyway: mid-week I had a fresh AI model audit the project and it caught a sorting bug that had quietly skewed the league toward the old champion's checkpoints, inflating my early head-to-head claims. Fixed it, re-ran everything at proper sample sizes, and the curve held. Best code review I've ever gotten.

Then last night the ending arrived on its own. Nine straight runs had gone 0 for 450 against max difficulty, but underneath, the agent's gem collection and transformations against those opponents climbed three runs in a row, and run 10 scored the first max-difficulty win in the project's history. One win in fifty, from generalization alone, zero max-difficulty training data, on a laptop, with a 7950X in the mail to run all of this 5x faster. Video below, repo with the full lab notebook linked, including the eight "project laws" these experiments paid for. I mostly gave direction while AI agents drove the code, and I understand every result in this post, which honestly might be the part I'm proudest of. Well, that and this: I've been a parent for almost five years, so I've been watching reinforcement learning run in real time since long before I trained one. You can tell by how carefully I tune rewards.

---

## Posting plan
1. r/reinforcementlearning — this version, video at top
2. r/MachineLearning [P] — next day, tightened opener
3. r/emulation (RAM/libretro engineering angle), r/Fighters + r/dreamcast (video-first, 2 paragraphs)
Check each sub's sidebar rules first.

## Pre-post blockers
- Link the MAIN allowlisted repo (powerstone2-rl), not -mac: sync Mac-era scripts/docs into it first (file list on request). Flip powerstone2-rl-mac back to PRIVATE (it carries savestates/VMU files the main repo's policy forbids publishing).
- Update numbers if legs 11+ move them before posting.
