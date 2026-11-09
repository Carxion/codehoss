from dojo_checks import first_axes


def test_bar_chart(run_program):
    run_program()
    ax = first_axes()
    assert ax["bars"] > 0, "Draw a bar chart with plt.bar"
