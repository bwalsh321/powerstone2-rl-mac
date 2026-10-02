#!/bin/bash
# Oct 1 2026: Mac-side lv8mix n=1000 reference on leg 103's zip (10 shards x 100, slots 90-94), for the Linux parity comparison.
cd "/Users/Apple/Downloads/macbook_migration/linux_port"
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PYTHONUNBUFFERED=1 PS2_OBS_V2=1 PS2_OBS_V3=1
M=powerstone_v6_leg103_league.zip
pids=()
for i in 0 1 2 3 4 5 6 7 8 9; do
  ( sleep $((i*6)); /Users/Apple/ps2rl/bin/python eval_parity.py --core "/Users/Apple/Library/Application Support/RetroArch/cores/flycast_libretro.dylib" --game "../Power Stone 2 (USA).chd" --slots 90,91,92,93,94 --model "$M" --episodes 100 --instance $i > receipts/parity/mac_leg103_lv8mix_s${i}_out.txt 2>&1 ) &
  pids+=($!)
done
wait "${pids[@]}"
/Users/Apple/ps2rl/bin/python merge_receipts.py slot --model "$M" --slot 90 --slots 90,91,92,93,94 --per-shard 100 --out receipts/parity/mac_leg103_lv8mix_n1000_out.txt receipts/parity/mac_leg103_lv8mix_s*_out.txt
echo MAC_PARITY_DONE > receipts/parity/mac_leg103_lv8mix_done.txt
