"""
Pure logic for grouping VIP users by their optional label, so /vips can
display them clustered together (e.g. all "College Group" VIPs under
one heading) instead of a flat list. Separate from notifier/state.py
because it's a display-shaping concern, not state management.
"""

UNLABELED = "Unlabeled"


def group_vips_by_label(vips: dict) -> dict:
    """
    vips: {user_id: {"label": str|None, ...}}
    Returns: {label: [user_id, ...]} sorted by label name, with
    unlabeled VIPs grouped last under UNLABELED. User IDs within each
    group are sorted ascending.
    """
    groups = {}
    for user_id, info in vips.items():
        label = info.get("label") or UNLABELED
        groups.setdefault(label, []).append(user_id)

    for ids in groups.values():
        ids.sort()

    labeled = sorted(k for k in groups if k != UNLABELED)
    ordered_keys = labeled + ([UNLABELED] if UNLABELED in groups else [])
    return {k: groups[k] for k in ordered_keys}
