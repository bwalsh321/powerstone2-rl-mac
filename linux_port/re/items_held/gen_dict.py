"""Build the code -> (name, category, range, thrown_on_use, init_counter, counter_kind)
dictionary from the game's own item table (item_table.json, decode_table.py) plus a
small set of hand overrides (marked). Writes items_dict.py (ready to paste)."""
import json
T = json.load(open("item_table.json"))
FOOD = {"Apple", "Short Cake", "Meat", "Rice Ball", "Banana", "Hamburger", "Roast Chicken",
        "Roast Pork", "Wedding Cake", "Cheese"}
MOUNT = {"Skateboard", "Inline Skate", "Scooter", "Angel Wing", "Devil Wing"}
CREATURE = {"Fire Dragon", "Ice Dragon", "Thunder Dragon", "Panther", "Kitten"}
SHIELD = {"Power Shield", "Deluxe Shield", "Medusa"}
EXPLOSIVE = {"Small Bomb", "Medium Bomb", "Large Bomb", "Fire-Bottle", "Fire Cracker", "Stick Bomb",
             "Hand Grenade", "Beehive"}
# ranged items that only reach a short distance (stream / cone / sound)
RANGED_SHORT = {"Flame Thrower", "Soap Bubble Gun", "Adhesive Spray", "Trumpet", "Loudspeaker", "Typhoon"}
# deployed traps (placed/thrown, then sit on the floor)
TRAP = {"Leg Trap", "Pitfall Hoop", "Thumbtack", "Bamboo Shoot"}
# codes seen held live in probe3 logs with initial counter == table counter (an4_behavior_out.txt)
LIVE = {0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0A,0x0B,0x0C,0x0D,0x0E,0x0F,0x13,0x19,0x1D,
        0x21,0x24,0x2B,0x30,0x33,0x35,0x39,0x3B,0x43,0x44,0x46,0x6A}
TAIL = '''# codes seen held live (initial counter matched the game table) -- the rest are named
# from the game's own name table via code = item_no + 1 (proven by the 30 live matches)
LIVE_CONFIRMED = {%s}

# Stage objects share the type byte space above the items. On DESERT (all three training
# savestates) only 0xC3 and 0xC8 are holdable. Codes 0xC4.. are reused per stage.
STAGE_CODES = {
    0xC1: ("power stone", "not holdable via F+0x54"),
    0xC2: ("treasure chest", "not holdable"),
    0xC3: ("desert barrel cactus (stage prop)", "throwable, counter 10 unused"),
    0xC8: ("desert tall saguaro (stage prop)", "uproot/carry/throw, counter 10 unused"),
    0xC4: ("stage-specific: boat-stage turret (fn 0x0C0E455E, counter 30 per use, holder state 18) / airship object (fn 0x0C0D1BAE)", "GUESS"),
    0xC5: ("stage-specific throwable (fn 0x0C0DF0CA)", "GUESS"),
    0xCC: ("stage-specific (fn 0x0C0E5522, counter 600)", "GUESS"),
}

# ---------------------------------------------------------------- readers
OBJ_TYPE = 0x420     # u8 type code (this dict's key)
OBJ_STATE = 0x421    # u8: 0 pop-out, 2 resting, 5 held, 6 dropped/tossed, 7 held+in use, 8 thrown in flight, 10/11 dying
OBJ_COUNTER = 0x424  # u16 remaining shots / frames / fuse (see counter_kind)
OBJ_HOLDER_MASK = 0x426  # u8 1<<seat of the current holder (LIKELY)


def held_record(ram, f_anchor_guest):
    """ram = 16 MiB SYSTEM_RAM numpy view; f_anchor_guest = ps2_addr.GEMS[k][1].
    Returns record offset into ram (F+0x54 pointer - 4) or None."""
    o = (f_anchor_guest & 0xFFFFFF) + 0x54
    p = int(ram[o]) | int(ram[o+1]) << 8 | int(ram[o+2]) << 16 | int(ram[o+3]) << 24
    return ((p - 4) & 0xFFFFFF) if p else None


def held_item(ram, f_anchor_guest):
    """-> (code, name, category, range_class, thrown_on_use, counter, counter_frac) or None."""
    r = held_record(ram, f_anchor_guest)
    if r is None:
        return None
    code = int(ram[r + OBJ_TYPE])
    ctr = int(ram[r + OBJ_COUNTER]) | int(ram[r + OBJ_COUNTER + 1]) << 8
    if code in ITEMS:
        n, cat, rng, thrown, init, kind = ITEMS[code]
        frac = min(1.0, ctr / init) if kind in ("shots", "frames", "fuse_frames") and init else 1.0
        return code, n, cat, rng, thrown, ctr, frac
    if code >= 0xC1:
        return code, STAGE_CODES.get(code, ("stage object", ""))[0], "stage_prop", "throw", True, ctr, 1.0
    return code, "?", "unknown", "none", False, ctr, 1.0
''' % ", ".join(f"0x{c:02X}" for c in sorted(LIVE))
out = {}
for r in T[:119]:          # rows 119/120 do not decode cleanly (code_chk mismatch)
    n = r["name"]
    thrown = bool(r["b00"] == 1) or n in TRAP or n == "Leg Trap"
    if n in FOOD: cat, rng = "food", "none"
    elif n in MOUNT: cat, rng = "mount", "none"
    elif n in CREATURE: cat, rng = "creature", "mid"
    elif n in SHIELD: cat, rng = "shield", "melee"
    elif n in EXPLOSIVE: cat, rng = "explosive", "throw"
    elif n in TRAP: cat, rng = "trap", "throw"
    elif r["b00"] == 1: cat, rng = "throwable", "throw"
    elif r["b04"] in (2, 4, 18) or (r["b03"] == 2 and r["counter"] == 10 and r["b01"] == 0 and r["f08"] == 0
                                    and n not in ("Typhoon",)):
        cat, rng = "wearable", "none"
    elif r["b03"] == 1:
        cat = "melee"; rng = "melee_long" if (abs(r["f10"]) >= 70 or r["b01"] == 1) else "melee_short"
    elif r["b03"] == 2:
        cat = "ranged"; rng = "ranged_short" if n in RANGED_SHORT else "ranged_long"
    else:
        cat, rng = "other", "none"
    if cat in ("melee", "shield", "mount", "creature") or n in ("Flame Thrower", "Soap Bubble Gun"):
        kind = "frames"          # counts down 1/frame (held, or while firing for streams)
    elif cat == "ranged": kind = "shots"
    elif cat == "explosive" and r["counter"] == 420: kind = "fuse_frames"
    elif cat == "food": kind = "heal?"
    else: kind = "unused(10)"
    out[r["code"]] = (n, cat, rng, thrown, r["counter"], kind)
with open("items_dict.py", "w") as f:
    f.write('"""Power Stone 2 held-item dictionary (generated by gen_dict.py from the game\'s own\n'
            'item table @0x0C273900 + name table @0x0C29DDD0). Key = item CODE byte read at\n'
            '(F+0x54 pointer) - 4 + 0x420 (low byte). code = item_no + 1. Codes >= 0xC1 are\n'
            'stage objects (see STAGE_CODES)."""\n\n')
    f.write("# code: (name, category, range_class, thrown_on_use, initial_counter, counter_kind)\nITEMS = {\n")
    for c, v in out.items():
        f.write(f"    0x{c:02X}: {v!r},\n")
    f.write("}\n\n")
    f.write(TAIL)
print(len(out), "items")
import collections
print(collections.Counter(v[1] for v in out.values()))
for c, v in out.items(): print(f"{c:#04x} {v}")
