# pyprojection

**Planned.** Output shapes as values: which fields, under which names, computed how.

```python
export = columns["name"]() & columns["salary"](label="Monthly pay") & computed("Yearly pay", salary * 12)
[export(employee) for employee in employees]   # rows for CSV, Excel or JSON
```

See `PHASES.md` for the plan.
