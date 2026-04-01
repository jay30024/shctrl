# Windows Service Verification

Approved procedure for restarting the Windows event forwarding collector and verifying health.

## Procedure

```powershell
Restart-Service -Name Wecsvc
Get-Service -Name Wecsvc
Test-NetConnection -ComputerName localhost -Port 5985
```

## Safety Notes

- Use an elevated PowerShell prompt when required.
- Verify the host is part of the intended maintenance scope.
