def test_map():
    from main import count_islands

    grid = [
        "##..#",
        "#...#",
        "..#..",
        ".....",
        "##.##",
    ]
    assert count_islands(grid) == 5
