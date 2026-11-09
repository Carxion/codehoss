import numpy as np


def test_truth_table(run_program):
    v = run_program().vars
    for x, want in [([0, 0], False), ([0, 1], False), ([1, 0], False), ([1, 1], True)]:
        got = v["neuron"](np.array(x), v["weights"], v["bias"]) > 0.5
        assert got == want, (
            f"For inputs {x} the neuron should be {'above' if want else 'below'} 0.5"
        )
