import pytest


def test_complete():
    from main import TodoList

    todo = TodoList()
    for task in ["shop", "cook", "eat"]:
        todo.add(task)
    todo.complete("cook")
    assert todo.pending() == ["shop", "eat"]
    assert todo.done_count() == 1


def test_complete_unknown_task():
    from main import TodoList

    with pytest.raises(ValueError):
        TodoList().complete("fly")
