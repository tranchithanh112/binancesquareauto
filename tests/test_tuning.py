from src import tuning


def test_load_weights_defaults_when_missing(tmp_path):
    w = tuning.load_weights(tmp_path / "nope.json")
    assert w == tuning.DEFAULT_WEIGHTS


def test_engagement_score_weights_interactions():
    low = {"avg_views": 100, "avg_likes": 0, "avg_comments": 0, "avg_reactions": 0}
    high = {"avg_views": 100, "avg_likes": 2, "avg_comments": 1, "avg_reactions": 2}
    assert tuning.engagement_score(high) > tuning.engagement_score(low)


def test_auto_tune_shifts_toward_winner(tmp_path):
    path = tmp_path / "tuning.json"
    by_type = [
        {"post_type": "signal", "avg_views": 200, "avg_likes": 3,
         "avg_comments": 1, "avg_reactions": 3},
        {"post_type": "news_ta", "avg_views": 50, "avg_likes": 0,
         "avg_comments": 0, "avg_reactions": 0},
    ]
    res = tuning.auto_tune(by_type, path=path)
    assert res["changed"] is True
    assert res["weights"]["signal"] > res["old"]["signal"]
    assert res["weights"]["news_ta"] < res["old"]["news_ta"]
    w = tuning.load_weights(path)
    assert abs(sum(w.values()) - 100) < 1.0


def test_auto_tune_no_stats(tmp_path):
    res = tuning.auto_tune([], path=tmp_path / "t.json")
    assert res["changed"] is False


def test_auto_tune_records_trend(tmp_path):
    path = tmp_path / "tuning.json"
    by_type = [{"post_type": "signal", "avg_views": 100, "avg_likes": 1,
                "avg_comments": 0, "avg_reactions": 1},
               {"post_type": "poll", "avg_views": 80, "avg_likes": 0,
                "avg_comments": 0, "avg_reactions": 0}]
    r1 = tuning.auto_tune(by_type, path=path)
    assert r1["prev_avg_score"] is None
    by_type2 = [{"post_type": "signal", "avg_views": 200, "avg_likes": 3,
                 "avg_comments": 2, "avg_reactions": 3},
                {"post_type": "poll", "avg_views": 150, "avg_likes": 1,
                 "avg_comments": 0, "avg_reactions": 1}]
    r2 = tuning.auto_tune(by_type2, path=path)
    assert r2["prev_avg_score"] is not None
    assert r2["improving"] is True