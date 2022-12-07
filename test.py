logs = [-1, -2, 4, 5, 6, 8, 9]
entries = [4, 5]

start_idx = 2

logs_start = logs[:start_idx]
logs_middle = logs[start_idx : start_idx + len(entries)]
logs_end = logs[start_idx + len(entries):]

is_conflict = False
for i in range(0, len(logs_middle)):
    if logs_middle[i] != entries[i]:
        is_conflict = True
        break

if is_conflict:
    logs = logs_start + entries
else:
    logs = logs_start + entries + logs_end

print(logs)