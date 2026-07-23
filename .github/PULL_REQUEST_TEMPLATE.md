## Summary

Describe what changed and why.

## User impact

- [ ] Existing workflows remain compatible.
- [ ] Any behavior change is documented.

## Security and data impact

- [ ] Authorization and project scoping were reviewed.
- [ ] User input is bounded and rendered safely.
- [ ] No credentials, tokens or local database files were added.

## Validation

List the commands you ran:

```text
python security_tests.py
python advanced_tests.py
python security_advanced_tests.py
python endpoint_quality_tests.py
python server.py --check
```

## Checklist

- [ ] Tests added or updated for the change.
- [ ] Documentation updated where needed.
- [ ] The diff is limited to the intended scope.
