"""lineup.py OUT_PREFIX C1 C2 C3 C4  -> prints drive.py steps that, from work/cc_slot3.state
(slot3 paused -> CHANGE CHARACTER; columns preset Pride/Falcon/Ryoma/Accel, P2 HUMAN),
make all four seats COM with the given characters, pick Desert, and save <prefix>_intro/_live states."""
import sys
CYC = ["Ryoma", "Wang-Tang", "Galuda", "Rouge", "Jack", "Pete", "Julia", "Gourmand", "Accel",
       "Mel", "Pride", "RANDOM", "Falcon", "Ayame", "Gunrock"]
START = ["Pride", "Falcon", "Ryoma", "Accel"]
out, chars = sys.argv[1], sys.argv[2:6]
st = ["p2:a:4", "wait:12", "rep:2:p1:down:3;wait:10"]
for col, (a, b) in enumerate(zip(START, chars)):
    if col:
        st += ["p1:right:3", "wait:10"]
    d = (CYC.index(b) - CYC.index(a)) % 15
    if d:
        st.append(f"rep:{d}:p1:a:4;wait:12" if d <= 7 else f"rep:{15-d}:p1:b:4;wait:12")
st += ["wait:20", "shot:%s_cfg" % out.split('/')[-1], "p1:start:4", "wait:60", "rep:2:p1:down:3;wait:15", "p1:a:4", "wait:400",
       f"save:{out}_intro.state", "wait:1500", "shot:%s_live" % out.split('/')[-1], f"save:{out}_live.state"]
print(",".join(st))
