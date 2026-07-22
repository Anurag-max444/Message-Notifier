from notifier.vip_labels import group_vips_by_label, UNLABELED


def vip(label=None):
    return {"muted_until": 0, "cooldown_seconds": None, "label": label}


class TestGroupVipsByLabel:
    def test_single_labeled_group(self):
        vips = {1: vip("College Group"), 2: vip("College Group")}
        result = group_vips_by_label(vips)
        assert result == {"College Group": [1, 2]}

    def test_multiple_labels_sorted_alphabetically(self):
        vips = {1: vip("Work"), 2: vip("Family")}
        result = group_vips_by_label(vips)
        assert list(result.keys()) == ["Family", "Work"]

    def test_unlabeled_vips_grouped_last(self):
        vips = {1: vip("Family"), 2: vip(None)}
        result = group_vips_by_label(vips)
        assert list(result.keys()) == ["Family", UNLABELED]
        assert result[UNLABELED] == [2]

    def test_user_ids_within_group_are_sorted(self):
        vips = {5: vip("Team"), 1: vip("Team"), 3: vip("Team")}
        result = group_vips_by_label(vips)
        assert result["Team"] == [1, 3, 5]

    def test_empty_vips_returns_empty_dict(self):
        assert group_vips_by_label({}) == {}

    def test_all_unlabeled(self):
        vips = {1: vip(), 2: vip()}
        result = group_vips_by_label(vips)
        assert result == {UNLABELED: [1, 2]}
