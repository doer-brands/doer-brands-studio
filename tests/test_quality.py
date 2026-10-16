from rl_studio.quality import check

GOOD = dict(quote="Listening isn't waiting for your turn. It's making room for theirs.",
            practice="Wait two full seconds after they finish before you respond today.",
            question="Who needs you to listen longer?")


def test_good_passes():
    assert check(GOOD, []) == []


def test_attribution_rejected():
    assert check(dict(GOOD, quote="Leadership is influence. - John Smith"), [])


def test_stat_rejected():
    assert check(dict(GOOD, quote="90% of leaders fail at listening to their people today"), [])


def test_duplicate_rejected():
    assert check(GOOD, [GOOD["quote"]])


def test_hype_rejected():
    assert check(dict(GOOD, quote="Embrace the hustle and unlock your potential every day"), [])


from rl_studio.quality import check_verified
V = dict(quote="x y z", author="A B", source_title="Book", source_detail="p. 10, 2nd ed.", pillar="Trust",
         practice="Do the thing today for one person.", question="Who?", verified=True,
         verified_primary_source=True, verified_by="Jason", verified_date="2026-10-16")


def test_verified_ok():
    assert check_verified(V) == []


def test_unverified_blocked():
    assert check_verified(dict(V, verified=False))
    assert check_verified(dict(V, verified_primary_source=False))


def test_aggregator_blocked():
    assert check_verified(dict(V, source_url="https://www.brainyquote.com/quotes/x"))
