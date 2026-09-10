# Reddit post, marked-up draft (Sep 10, 2026)

How to read this: your text is kept as written. `[FIX: ...]` is a factual
correction with the source. `[CUT]` is a line that is now false.
`[SUGGESTED]` blocks are beats you planned but have not written; the facts
in them are verified against `HANDOFF.md` and the receipts, the wording is
a placeholder for your own. No em dashes anywhere.

Verified numbers through leg 15 (Sep 9): held-out lv3 FFA curve
40/42/50/64/78/82/84/86/90/88/90/92/92 (champion 98); lv8 FFA wins per
leg since leg 10: 1, 0, 2, 3, 2, 2 out of 50 (champion 3/20); lineage 26M
PPO steps vs the champion's 31.9M; head-to-head vs champion 29-21 at n=50
(leg 6), then 9-3, 11-1, 11-1, 8-4, 11-1 at n=12 for legs 11 to 15; your
own record vs three lv8 COMs 23-1; BC clone 8 training wins in 4,653
episodes.

---

## Title options

- I trained a Power Stone 2 (Dreamcast) bot from emulator RAM, no pixels, on a laptop. Self-play took it from 40% to 92% on a held-out 4-player FFA.
- Two brothers, one useless CPU player, and 25 years later an RL agent for Power Stone 2 (RAM-based, self-play, no pixels)

---

## Your draft, marked up

A few years back I saw a video about [somebody training an AI to play pokemon red](http://youtube.com/watch?v=DcYLT37ImBY&t=1s). I was absolutely fascinated with this, and even bought an old 16 core Xeon to train it myself. This was really fun, but I did however have a different dream. While I do love pokemon, it sparked another idea. One of my favorite games of all time was Power Stone 2 for dreamcast, and I always wished my 2 brothers and I had a 4th person comparable to our skill level to play with. We spent so many years of my childhood playing a 4 person free for all with a stupid bot that `[typo: "that as" -> "that was"]` essentially useless. That is how this project was born.

I started this back in 2025, but once I realized I needed to hunt for ram values to make this bot actually good, the project hit a wall for over a year. This was until last month. I just had a baby, and needed something to keep my attention late at night while the baby was asleep on me. Doomscrolling sucks so, I finally had dedicated time to do some serious RE and buildout to make this happen. As a father of 3 now, reinforcement learning was a language I understand pretty well at this point.

I have had many challenges. There were no decomps for Powerstone 2, no ram values listed anywhere. No project ready to just test and build on my own. So I got to work. I had to build everything myself, so yes I did use Claude to help me with some of the super tedious stuff that I didnt want to spend time doing (like hunting for RAM values)

`[FIX, disclosure: this undersells it and an ML crowd will check the commit history, which is co-authored. Your own earlier line is stronger and true: "I gave direction while AI agents drove the code, and I understand every result." Say plainly that Claude wrote most of the code under your direction, that you did the reverse engineering calls, the demo recordings and every what-to-run-next decision, and that the repo README has a full "On AI assistance" section. The audits below become your proof that you scrutinized the generated code rather than trusted it.]`

I started on my windows machine, and was able to get the training running on one window on the machine, and it was making some progress. Though not being able to spin up multiple instances was a pain, so I kept scaling to 10 windows which was the threshold my machine could do, but it would only work at 60 fps and not uncapped. I did find a fork of flycast that could run headless on Linux, which I didn't want to build this from a terminal, so I used my macbook instead. Through this, I was able to run 6 instances unlocked on this machine, but at 150+ fps so what the windows machine could do in a day, I could do in a few hours. Huge w. Currently waiting for a 7950x to drop in my linux server and scale.

`[FIX: it is not a flycast fork, it is a libretro harness (sdlarch-rl) that runs the flycast core in-process and headless; you ported it to macOS. Suggest: "I found a libretro harness (sdlarch-rl) that runs the Flycast core headless and in-process, ported it to my M2 MacBook, and ..."]`

`[CUT: "Currently waiting for a 7950x" is no longer true. The DOA chip is a better beat. Suggest: "The plan was to move this to a 7950X Linux box. The eBay chip arrived internally shorted and took the whole build down with it until a full AC drain reset the PSU. So everything below was trained on a laptop, and the Linux migration kit sits in the repo waiting for a working CPU."]`

I had many ups and downs learning about reward tuning, BC, DAgger, and I kept hitting a wall around level 5 com difficulty where no matter what I did, the bot would never get any better. I was even doing self play against prior runs, mixed in with some different characters, com difficulty, etc. I tried mixing in 1v1's so it could master some combat before making it chaotic. Nothing worked.

Then I switch to 6 instances of self play against the recent prior training checkpoints, and after that leg was compelte, 1 FFA low level to use as a gauge to see how the bots learning curve was going vs the previous session. This finally broke my wall. My current 20m step bot is whooping on my previous 35M step bot (8w,4L), and I was able to train it in days, and not weeks. Not one adjustment to rewards or anything. It just seems to work now.

`[FIX, the recipe sentence: the low-level FFA is a held-out evaluation the bot never trains on, not a 7th instance. Suggest: "Then I switched to six instances of pure 1v1 self-play against a pool of frozen past checkpoints, in 2M-step legs that each warm-start from the last. The low-difficulty 4-player FFA is never trained on. It is the held-out test I run after every leg to see whether the self-play skills transfer."]`

`[FIX, numbers: "20m" is 26M as of leg 15; "35M" is 31.9M (say 32M); "(8w,4L)" was one n=12 probe and the latest ones read 11-1, 11-1, 8-4, 11-1. Lead with the held-out curve, it is the result that survives scrutiny: "The held-out FFA win rate went 40, 42, 50, 64, 78, 82, 84, 86, 90, 88, 90, 92, 92 percent over thirteen legs, against the old champion's 98. Head to head in 1v1 the 26M-step bot beats the 32M-step one 29-21 over 50 games, and the quick 12-game probes after recent legs came in 11-1 three times out of four. Same reward table the whole way."]`

`[FIX, "days not weeks": thirteen legs at about 7.5 hours each is roughly four days of laptop compute, spread over two weeks of an unattended relay. Say that; it is more impressive than vague.]`

---

## Beats you planned but have not written yet

`[SUGGESTED, the BC heartbreaker]` Facts: you recorded a sitting vs three lv8 COMs and went 23-1; behavior cloning on that corpus hit 80.6% validation accuracy on your actions; when PPO took over from the clone it won 8 of 4,653 training episodes. The classic diagnosis is covariate shift (the clone drifts into states you never visited and has no idea what to do). The Sep 10 audit added a twist: the recorder had a bug, and the velocity features in every demo corpus were zero in 98% of rows, so the clone was trained on an input it never saw at deployment. Placeholder: "The worst night of the project: I recorded myself going 23-1 against three max-difficulty COMs, cloned it at 80% accuracy on my own button presses, handed it to PPO, and it won 8 games out of 4,653. Covariate shift is the textbook answer. An audit last week found the recorder also had a bug that zeroed out the velocity features, so the clone was learning from a broken view of the game. Both are in the notebook."

`[SUGGESTED, the audit disclosure]` Facts: a Sep 2 review found the opponent-pool sorting bug (recent half of the pool was permanently leg 1's snapshots), snapshot-name collisions and a missing pool entry; fixed, re-ran, the curve held. Sep 9 and 10 reviews found that the pool does not refresh within a leg (docs said it did), the relay script would have advanced even if every eval failed, and the parity gate was checking a stale band. All documented in HANDOFF.md, all the ops ones fixed, the observation-contract ones deliberately deferred so the running experiment is not changed mid-stream. Placeholder: "I had the whole thing audited three times because I did not trust a curve that good. The first audit found a real bug in how opponents were sampled. I fixed it, re-ran, and the curve held. The later ones found the docs overstating a mechanism and the automation being too trusting. The fixes and the things I chose not to fix yet are all in the notebook."

`[SUGGESTED, the lv8 crack]` Facts: nine batteries with zero wins at difficulty 8; stone pickups and transformations per episode were climbing leg over leg before any win appeared; first win at leg 10; since then 1, 0, 2, 3, 2, 2 out of 50. The champion scores 3/20 there. This lineage has zero direct training against difficulty-8 COMs (its pool does contain older checkpoints that were trained against them, so say "direct"). Placeholder: "Max difficulty was a wall for nine straight legs. The behavior stats were climbing the whole time, so I kept going, and at leg 10 it won one. It has won at least one in every leg since. Two to six percent is not mastery. It is a crack in a wall this lineage never trained against directly."

`[SUGGESTED, honest limits, one paragraph, ML readers will respect it]` One training run per recipe, so the curve is one lineage not a mean over seeds. n=50 is plus or minus about 10 points. Head-to-head probes are one-seat (learner always P2). The relay promotes each leg's last checkpoint, which contradicts your own law 6, and you left it alone on purpose during the pre-registered run.

`[SUGGESTED, the closer]` Your brothers, the fourth player, the baby asleep on you while the relay ran. Yours to write.

`[SUGGESTED, links]` Repo: https://github.com/bwalsh321/powerstone2-rl-mac (link only this one; the Windows-era repo is linked from its README as history). Video at the top of the post. HANDOFF.md as "the lab notebook, every failed leg included".

---

## Posting checklist

1. Push the Sep 10 commit (6375739) from the Mac, not through the bridge.
2. Upload the video (leg1_showcase.mp4 is 688 MB; consider a 60 to 90 second cut of the current leg on slot 2 via `watch_play.py --record`).
3. Tighten the savestate unlock paragraph in README step 3 if you can be specific.
4. Post order as planned: r/reinforcementlearning, then r/MachineLearning [P], then r/emulation, r/Fighters, r/dreamcast.
