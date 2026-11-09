from dojo_checks import first_axes


def test_line_chart(run_program):
    run_program()
    ax = first_axes()
    assert ax["lines"] >= 1, "Draw a line chart with plt.plot"
    assert ax["title"] == "Monthly revenue", f"The title is {ax['title']!r}"
