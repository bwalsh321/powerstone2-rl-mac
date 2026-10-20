"""gen.py <slot> [extra steps] -- drive.py step string for one sealed lineup (Oct 17 2026), starting from the PLAYER
SELECT menu state at difficulty 8 (see ../README.md step 1). Each COM port: A (HUMAN -> COM), DOWN x2, A (column
default: P1 Falcon, P3 Pete, P4 Accel), then A forward / B backward through the roster; P2: DOWN x2, A (Ryoma), B x3
(Falcon); START -> STAGE SELECT. The caller appends the stage move (UP = Desert, none = Blue sky, RIGHT = Dark castle),
A, wait 200, save."""
import sys
R = ["Falcon","Ayame","Gunrock","Ryoma","Wang-Tang","Galuda","Rouge","Jack","Pete","Julia","Gourmand","Accel","Mel","Pride"]
PLAN = {95:("Jack","Accel","Wang-Tang"), 96:("Mel","Falcon","Ayame"), 97:("Gourmand","Pete","Rouge"),
        98:("Ryoma","Gunrock","Wang-Tang"), 99:("Pride","Galuda","Accel")}
DEF = {"p1":0,"p3":8,"p4":11}
def pick(port, name):
    d = DEF[port]; t = R.index(name)
    btn, n = ("a", t-d) if t >= d else ("b", d-t)
    s = [f"{port}:a:4","wait:15",f"rep:2:{port}:down:3;wait:10",f"{port}:a:4","wait:15"]
    if n: s.append(f"rep:{n}:{port}:{btn}:4;wait:12")
    return s
def select(slot):
    p1,p3,p4 = PLAN[slot]
    s = pick("p1",p1) + pick("p3",p3) + pick("p4",p4)
    s += ["rep:2:p2:down:3;wait:10","p2:a:4","wait:15","rep:3:p2:b:4;wait:12","wait:30",f"shot:s{slot}_select","info:select"]
    s += ["p2:start:4","wait:120",f"shot:s{slot}_stage0"]
    return s
if __name__ == "__main__":
    slot = int(sys.argv[1]); extra = sys.argv[2] if len(sys.argv) > 2 else ""
    print(",".join(select(slot) + ([extra] if extra else [])))
