A few years back I saw a video about [somebody training an AI to play Pokemon Red](https://www.youtube.com/watch?v=DcYLT37ImBY). I was fascinated and even bought an old 16 core Xeon to train it myself. But I had a different dream. One of my favorite games of all time is Power Stone 2 for Dreamcast, and my two brothers and I always wished we had a 4th player at our skill level. We spent years of my childhood playing 4 person free for alls with a stock bot that was essentially useless. That is how this project was born.

I started in 2025, and once I realized I needed to hunt down RAM values to make the bot any good, it hit a wall for over a year. No decomp, no memory map anywhere, nothing to build on. Then last month I had a baby and needed something to do late at night with him asleep on me. Doomscrolling sucks, so I finally did the RE. As a father of 3, reinforcement learning is a language I understand pretty well at this point.

Full disclosure: I gave direction and made every call, but Claude wrote most of the code. I understand every result in the repo and I had the whole thing audited three separate times because I did not trust a curve this good. More on that below.

It started on my Windows machine, one emulator window, then ten, capped at 60 fps. Then I found a libretro harness (sdlarch-rl) that runs Flycast headless and in-process, ported it to my M2 MacBook, and got 6 instances at 150+ fps. What Windows did in a day the laptop does in a few hours. The 7950X Linux box I planned to scale on arrived from eBay internally shorted, so everything below was trained on a laptop.

I hit a wall around COM difficulty 5 for a long time. Reward tuning, behavior cloning from my own play, mixing in harder COMs, mixing in 1v1s, nothing moved it. The worst one: I recorded myself going 23-1 against three max difficulty COMs, cloned it, handed it to PPO, and it won 8 games out of 4,653.

What finally broke it was the simplest recipe in the repo. Six instances of pure 1v1 self-play against a pool of frozen past checkpoints, in 2M step legs that each warm start from the last. A low difficulty 4 player FFA that the bot never trains on is the test after every leg. That held-out win rate went 40, 42, 50, 64, 78, 82, 84, 86, 90, 88, 90, 92, 92 percent over thirteen legs, against 98 for my old 32M step champion. Head to head in 1v1 the new 26M step bot beats the old one 29-21 over 50 games, and the quick 12 game probes after recent legs read 11-1 three times out of four. Max difficulty was 0 wins for nine straight legs, then it won one at leg 10 and has won at least one every leg since. Not one reward change the whole way. About four days of laptop compute spread over two weeks of an unattended relay.

The audits found real bugs (an opponent sampling bug, docs claiming a mechanism the code did not have, a relay script that would have kept going if every eval failed). Fixed, re-ran, the curve held. All of it, every failed leg included, is in the lab notebook in the repo.

Repo: https://github.com/bwalsh321/powerstone2-rl-mac

Still no 4th player for game night. Getting closer.
