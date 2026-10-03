"""action_space.py — the JOINT action set (Oct 3 2026, 9950X; Blake: "this is why its movement is goofy").

The legacy set is 10 single inputs (up/down/left/right, A jump, B action, X attack, Y discard, L/R Power Fusion):
one input per decision, no diagonals, no move-while-attacking, no "do nothing". The joint set is
  direction (9: none, up, down, left, right, up-left, up-right, down-left, down-right)
  x button  (7: none, A, B, X, Y, L, R)                                    = 63 actions,
index = dir * 7 + btn. Every legacy action has an exact joint equivalent (LEGACY_TO_JOINT) and keeps its exact
legacy execution (direction-only presses overlap the next decision by 4 frames; buttons and triggers run
ACTION_FRAMES). A combo presses every part in ONE mask (L/R are mask bits in the harness) for ACTION_FRAMES;
pure movement, diagonals included, uses the direction hold. (none, none) releases everything.

The observation's last-action block stays 10 slots wide: a joint action is written MULTI-HOT over the legacy
slots (direction bits on slots 0-3, the button on its legacy slot), so legacy actions encode exactly as before.
"""
DC_B, DC_A = 0x2, 0x4
DC_UP, DC_DOWN, DC_LEFT, DC_RIGHT = 0x10, 0x20, 0x40, 0x80
DC_Y, DC_X = 0x200, 0x400
AXIS_L, AXIS_R = 5, 6

LEGACY_N = 10
DIRS = [("none", 0), ("up", DC_UP), ("down", DC_DOWN), ("left", DC_LEFT), ("right", DC_RIGHT),
        ("up-left", DC_UP | DC_LEFT), ("up-right", DC_UP | DC_RIGHT),
        ("down-left", DC_DOWN | DC_LEFT), ("down-right", DC_DOWN | DC_RIGHT)]
# (name, dc_mask, axis_id or None, legacy slot or None)
BTNS = [("none", 0, None, None), ("A", DC_A, None, 4), ("B", DC_B, None, 5), ("X", DC_X, None, 6),
        ("Y", DC_Y, None, 7), ("L", 0, AXIS_L, 8), ("R", 0, AXIS_R, 9)]
JOINT_N = len(DIRS) * len(BTNS)                         # 63
DIR_SLOTS = {DC_UP: 0, DC_DOWN: 1, DC_LEFT: 2, DC_RIGHT: 3}

# legacy action k -> joint index (exact equivalent)
LEGACY_TO_JOINT = {0: 1 * 7 + 0, 1: 2 * 7 + 0, 2: 3 * 7 + 0, 3: 4 * 7 + 0,
                   4: 0 * 7 + 1, 5: 0 * 7 + 2, 6: 0 * 7 + 3, 7: 0 * 7 + 4, 8: 0 * 7 + 5, 9: 0 * 7 + 6}
JOINT_TO_LEGACY = {j: k for k, j in LEGACY_TO_JOINT.items()}


def split(j):
    return divmod(int(j), len(BTNS))                    # (dir index, button index)


def name(j):
    d, b = split(j)
    return f"{DIRS[d][0]}+{BTNS[b][0]}"


def last_action_slots(action, n_actions):
    """Legacy-slot indices to set in the 10-wide last-action block (one-hot for legacy, multi-hot for joint)."""
    a = int(action)
    if n_actions == LEGACY_N:
        return [a]
    d, b = split(a)
    dmask = DIRS[d][1]
    slots = [s for bit, s in DIR_SLOTS.items() if dmask & bit]
    if BTNS[b][3] is not None:
        slots.append(BTNS[b][3])
    return slots


def execution(action, n_actions, action_frames):
    """(dc_mask, axis_id or None, hold_frames) for one decision.
    Legacy actions (and their joint equivalents) reproduce the legacy env exactly."""
    a = int(action)
    if n_actions != LEGACY_N:
        if a in JOINT_TO_LEGACY:
            a, n_actions = JOINT_TO_LEGACY[a], LEGACY_N
        else:
            d, b = split(a)
            dmask = DIRS[d][1]
            _, bmask, axis, _ = BTNS[b]
            if b == 0:                                       # pure movement (diagonals): direction hold
                return dmask, None, action_frames + 4 if dmask else action_frames
            return dmask | bmask, axis, action_frames
    # legacy semantics
    if a < 4:
        return [DC_UP, DC_DOWN, DC_LEFT, DC_RIGHT][a], None, action_frames + 4
    if a < 8:
        return [DC_A, DC_B, DC_X, DC_Y][a - 4], None, action_frames
    return 0, [AXIS_L, AXIS_R][a - 8], action_frames
