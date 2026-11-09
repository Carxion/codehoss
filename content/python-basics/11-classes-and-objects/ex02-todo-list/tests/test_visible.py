def test_add_and_pending():
    from main import TodoList

    todo = TodoList()
    todo.add("shop")
    todo.add("cook")
    assert todo.pending() == ["shop", "cook"], f"pending() gave {todo.pending()}"
