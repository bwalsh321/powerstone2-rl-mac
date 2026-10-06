import sys
R = ["Falcon","Ayame","Gunrock","Ryoma","Wang-Tang","Galuda","Rouge","Jack","Pete","Julia","Gourmand","Accel","Mel","Pride"]
PLAN = {60:("Gunrock","Gourmand","Pride"),61:("Accel","Gunrock","Ayame"),62:("Pride","Pete","Gunrock"),
        63:("Gunrock","Accel","Mel"),64:("Gourmand","Galuda","Jack"),65:("Mel","Jack","Gourmand"),
        66:("Falcon","Rouge","Accel"),67:("Wang-Tang","Ayame","Pride"),68:("Galuda","Julia","Pete")}
DEF = {"p1":0,"p3":8,"p4":11}
def pick(port, name):
    d = DEF[port]; t = R.index(name)
    btn, n = ("a", t-d) if t >= d else ("b", d-t)
    s = [f"{port}:a:4","wait:15",f"rep:2:{port}:down:3;wait:10",f"{port}:a:4","wait:15"]
    if n: s.append(f"rep:{n}:{port}:{btn}:4;wait:12")
    return s
def steps(slot, shots=True, save=None):
    p1,p3,p4 = PLAN[slot]
    s = []
    s += pick("p1",p1) + pick("p3",p3) + pick("p4",p4)
    s += ["rep:2:p2:down:3;wait:10","p2:a:4","wait:15","rep:3:p2:b:4;wait:12","wait:30",f"shot:s{slot}_select","info:select"]
    s += ["p2:start:4","wait:120",f"shot:s{slot}_stage0","p2:up:3","wait:20",f"shot:s{slot}_stage","p2:a:4"]
    s += ["wait:200","info:saved"]
    if save: s.append(f"save:{save}")
    s += ["wait:1200",f"shot:s{slot}_fight","info:fight"]
    return ",".join(s)
if __name__ == "__main__":
    slot = int(sys.argv[1]); print(steps(slot, save=sys.argv[2] if len(sys.argv)>2 else None))
