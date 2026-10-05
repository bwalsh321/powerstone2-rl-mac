"""Summarize holds_*.json: per item code -> name guess (code-0x501 into the
game's own name table), counts, initial counter, counter trajectories."""
import json, glob, sys, collections
NAMES = json.load(open("item_names.json"))
def nm(code):
    i = (code & 0xFF) - 1
    return NAMES[i] if 0 <= i < len(NAMES) else f"<non-item {code & 0xff:#x}>"
fs = sys.argv[1:] or sorted(glob.glob("ev/holds_*.json"))
by = collections.defaultdict(list); cen = collections.Counter()
for f in fs:
    d = json.load(open(f))
    for h in d["holds"]:
        by[h["info"]["code"] & 0xFF].append((d["tag"], h))
    for c, fn, n in d["census"]:
        cen[(c & 0xFF, c >> 8, fn)] += n
for code in sorted(by):
    L = by[code]
    print(f"\n=== code {code:#04x} -> {nm(code)}  holds={len(L)} fns={sorted(set(hex(h['info']['fn']) for _, h in L))}")
    for tag, h in L[:6]:
        cl = h["ctr_log"]
        post = h["post"][:6]
        print(f"  {tag} P{h['p']+1} o={h['o']:#x} f={h['start']}-{h['end']} ctr0={h['info']['ctr']} b427={h['info']['b427']} w428={h['info']['w428']:#x} "
              f"ctr_changes={len(cl)-1} ctr_log={cl[:8]}{'...' if len(cl)>8 else ''} end={h.get('end_info',{}).get('ctr')}")
        if post: print("     post(dt,x,y,z,code,hdr,fn):", post)
print("\ncensus (code, fn): n")
for (c, st, fn), n in sorted(cen.items()):
    print(f"  code={c:#04x} state={st:#x} {nm(c):20s} fn={fn:#x} n={n}")
