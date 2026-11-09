from sklearn.metrics import confusion_matrix


def test_counts(run_program):
    v = run_program().vars
    expected = confusion_matrix(v["y_test"], v["predictions"], labels=["ham", "spam"])
    assert (v["cm"] == expected).all(), (
        "Use labels=['ham', 'spam'] so rows and columns are in that order"
    )
    assert v["false_positives"] == expected[0][1]
    assert v["false_negatives"] == expected[1][0]
