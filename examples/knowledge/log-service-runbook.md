# Log Service Restart Runbook

This is an approved procedure for restarting the internal log service on Linux hosts.

## Preconditions

- Confirm you are operating in the correct environment.
- Prefer a non-production host first.
- Verify the service health after the restart.

## Command Sequence

```bash
sudo systemctl restart log-collector
sudo systemctl status log-collector --no-pager
curl -fsS http://localhost:8080/health
```

## Safety Notes

- Run during an approved maintenance window when possible.
- Capture recent logs before restart if the incident is still active.
- Rollback guidance is available in the platform operations handbook.
