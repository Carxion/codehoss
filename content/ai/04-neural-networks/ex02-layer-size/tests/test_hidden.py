def test_best(run_program):
    v = run_program().vars
    assert v["scores"][2] < v["scores"][64], "A 2-neuron layer should do worse than 64"
    assert v["best_size"] == max(v["scores"], key=v["scores"].get)
