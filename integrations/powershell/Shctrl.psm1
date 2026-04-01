$script:ShctrlPendingRequestId = $null
$script:ShctrlPendingRawCommand = $null
$script:ShctrlPendingAnnotatedCommand = $null
$script:ShctrlInsertedAtMs = $null

function Invoke-Shctrl {
    [CmdletBinding()]
    param(
        [string]$Intent
    )

    if (-not ("Microsoft.PowerShell.PSConsoleReadLine" -as [type])) {
        Import-Module PSReadLine -ErrorAction Stop
    }

    $line = ""
    $cursor = 0
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

    if ([string]::IsNullOrWhiteSpace($Intent)) {
        if (-not [string]::IsNullOrWhiteSpace($line)) {
            $Intent = $line
        }
        else {
            $Intent = Read-Host "shctrl intent"
        }
    }

    $payload = & shctrl suggest $Intent --shell powershell --cwd ((Get-Location).Path) --existing-buffer $line --json
    if (-not $payload) {
        return
    }

    $parsed = $payload | ConvertFrom-Json
    $script:ShctrlPendingRequestId = [string]$parsed.request_id
    $script:ShctrlPendingRawCommand = [string]$parsed.command
    $script:ShctrlPendingAnnotatedCommand = [string]$parsed.annotated_command
    $script:ShctrlInsertedAtMs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()

    [Microsoft.PowerShell.PSConsoleReadLine]::Replace(0, $line.Length, $script:ShctrlPendingAnnotatedCommand)
    [Microsoft.PowerShell.PSConsoleReadLine]::EndOfLine()
}

function Invoke-ShctrlAcceptLine {
    [CmdletBinding()]
    param()

    $line = ""
    $cursor = 0
    [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)

    if ($script:ShctrlPendingRequestId) {
        $latency = $null
        if ($script:ShctrlInsertedAtMs) {
            $latency = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() - $script:ShctrlInsertedAtMs
        }

        $edited = $line -ne $script:ShctrlPendingAnnotatedCommand
        $args = @(
            "log-execution",
            "--request-id", $script:ShctrlPendingRequestId,
            "--final-command", $line
        )
        if ($edited) {
            $args += "--edited"
        }
        if ($null -ne $latency) {
            $args += @("--execution-latency-ms", "$latency")
        }

        & shctrl @args | Out-Null
        $script:ShctrlPendingRequestId = $null
        $script:ShctrlPendingRawCommand = $null
        $script:ShctrlPendingAnnotatedCommand = $null
        $script:ShctrlInsertedAtMs = $null
    }

    [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()
}

function Register-Shctrl {
    [CmdletBinding()]
    param(
        [string]$Chord = "Ctrl+g"
    )

    if (-not ("Microsoft.PowerShell.PSConsoleReadLine" -as [type])) {
        Import-Module PSReadLine -ErrorAction Stop
    }

    Set-PSReadLineKeyHandler -Chord $Chord -BriefDescription "shctrl" -ScriptBlock {
        Invoke-Shctrl
    }

    Set-PSReadLineKeyHandler -Key Enter -BriefDescription "AcceptLineWithShctrlTelemetry" -ScriptBlock {
        Invoke-ShctrlAcceptLine
    }
}

Export-ModuleMember -Function Invoke-Shctrl, Register-Shctrl
