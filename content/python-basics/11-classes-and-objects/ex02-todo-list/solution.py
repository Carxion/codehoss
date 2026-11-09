class TodoList:
    def __init__(self):
        self.tasks = []
        self.done = set()

    def add(self, task):
        self.tasks.append(task)

    def complete(self, task):
        if task not in self.tasks:
            raise ValueError(f"No task called {task!r}")
        self.done.add(task)

    def pending(self):
        return [task for task in self.tasks if task not in self.done]

    def done_count(self):
        return len(self.done)
