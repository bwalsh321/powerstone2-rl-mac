# Audit: levers pulled, levers missed (Oct 17 2026, leg 194)

Blake asked: we broke 70%; what did we miss, and what was tried that might make sense now?

## Current settings

| Setting | Value |
|---|---|
| Learning rate | 2.5e-5 (was 1e-4 until leg 169) |
| Entropy coef | 0.01, fixed since the start |
| Batch | 256 |
| Epochs | 10, target_kl 0.03 |
| gamma / GAE | 0.999 / 0.95 |
| Gradient clip | 0.5, shared by policy and critic |
| Network | MLP 512x2, LSTM 128 |
| Frame stack | 2 |
| Hunters | 50% |

Opponent pool: 50% from the last 10 snapshots (about 1 leg), 50% uniform over every snapshot from leg 113 to now
(741 files).

## Missed or never revisited (ranked by expected value)
1. **Opponent pool is half "ancient".** Half the self-play opponents are drawn uniformly from legs 113-194. Leg 113
   was a ~37% bot, and most of that history is now far weaker than the learner.
   - Standard practice: OpenAI Five played 80% latest / 20% past; AlphaStar used prioritized (PFSP) sampling. Our
     code already has `pfsp` (PS2_POOL_SAMPLING), never turned on.
   - A recent-only pool already helped once (legs 139+).
   - Fix: move legs before ~170 to pool_league_archive/ (a move, not a delete), or switch on pfsp.
2. **The entropy bonus has never been annealed.** Fixed at 0.01 for 190 legs. Standard is to lower it as play
   improves.
   - The sampled vs top-move gap is ~7 points (68 vs 75), and much of it is randomness the bonus pays for.
   - Lower 0.01 -> 0.005 and expect sampled to rise toward top-move.
   - Needs one small script change: PS2_ENT_COEF exists in the trainer but the relay doesn't pass it through.
3. **The learning rate keeps paying off: keep stepping it.** 1e-4 -> 5e-5 = +7; 5e-5 -> 2.5e-5 = +4. Next is
   1.25e-5 at the next plateau.
4. **One sealed test set for 60+ legs of decisions.** Every keep/revert has been judged on the same 5 held-out
   lineups (90-94). Picking by one test set slowly overfits to it. Before claiming 80%, build a second sealed set
   (new lineups, other stages), graded rarely. It is in the old queue and was never built.

## Tried before: worth retrying now?
- **Split gradient clip (reverted with the leg 149 bundle).** The critic's gradient was ~30x the policy's, so the
  shared clip shrank policy steps a lot. Splitting them makes policy steps bigger, which is the opposite of what just
  worked (smaller steps). Low priority; only if a later plateau resists the lr steps.
- **Reward cleanup (leg 143, -11).** The stone cap was the likely culprit. Still not worth a slot.
- **DAgger / imitation:** no. **Practice start points:** no effect before; skip.
- **Bigger batch (1024):** worse before, at lr 1e-4. Plausible again at low lr, but low priority.
- **Hunters 50%:** keep. The hunted grade is now 19-22 (was ~12).
- **LSTM 256:** built and tested; legs ~7 h. Lower expected value per hour than items 1-3.

## Revised order (vacation plan and after)
1. Ride the current setup until the plateau.
2. **Pool: recent-only**, by archiving legs <170 (no code; reversible by moving them back). 3-leg read.
3. Learning rate 1.25e-5 at the next plateau.
4. Entropy 0.01 -> 0.005, once the pass-through flag is merged (Blake runs the merge command).
5. Build the second sealed test set in parallel (agent; no training impact).
6. LSTM 256 last.

Sources:
- [OpenAI Five paper](https://arxiv.org/pdf/1912.06680): 80/20 latest/past, quality-scored past opponents.
- [Unity ML-Agents self-play docs](https://plastichub.unity.cn/unity-tech-cn/ml-agents/src/commit/0ff591bc-5a84-42c6-aacf-d6b8debeef35...docs/Training-Self-Play.md):
  play_against_latest_model_ratio.
- [Unity ML-Agents PPO best practices](https://plastichub.unity.cn/unity-tech-cn/ml-agents/raw/branch/tag-0.2.1...docs/best-practices-ppo.md):
  entropy should fall as reward rises.
