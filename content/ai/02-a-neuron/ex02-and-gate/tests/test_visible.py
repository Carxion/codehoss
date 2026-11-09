import numpy as np


def test_one_one(run_program):
    v = run_program().vars
    assert v["neuron"](np.array([1, 1]), v["weights"], v["bias"]) > 0.5, (
        "1 AND 1 should be above 0.5"
    )
