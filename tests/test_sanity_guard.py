from build.sanity_guard import is_pull_valid


def test_empty_roster_fails():
    assert is_pull_valid([], previous_store_count=18) is False


def test_empty_roster_with_no_prior_history_fails():
    assert is_pull_valid([], previous_store_count=None) is False


def test_stable_roster_passes():
    roster = [{"store_name": f"s{i}"} for i in range(17)]
    assert is_pull_valid(roster, previous_store_count=18) is True


def test_roster_growing_passes():
    roster = [{"store_name": f"s{i}"} for i in range(20)]
    assert is_pull_valid(roster, previous_store_count=18) is True


def test_first_ever_run_with_no_prior_count_passes():
    roster = [{"store_name": f"s{i}"} for i in range(18)]
    assert is_pull_valid(roster, previous_store_count=None) is True


def test_roster_dropping_by_more_than_half_fails():
    roster = [{"store_name": f"s{i}"} for i in range(8)]
    assert is_pull_valid(roster, previous_store_count=18) is False
