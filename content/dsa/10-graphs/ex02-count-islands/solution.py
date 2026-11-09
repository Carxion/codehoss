def count_islands(grid):
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    seen = set()
    islands = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != "#" or (r, c) in seen:
                continue
            islands += 1
            seen.add((r, c))
            stack = [(r, c)]
            while stack:
                y, x = stack.pop()
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < rows and 0 <= nx < cols and grid[ny][nx] == "#" and (ny, nx) not in seen:
                        seen.add((ny, nx))
                        stack.append((ny, nx))
    return islands
