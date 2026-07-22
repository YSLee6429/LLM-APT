[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$WebUrl = "http://localhost:3000"
)

$ErrorActionPreference = "Stop"

function Assert-Equal {
    param(
        [Parameter(Mandatory = $true)]$Actual,
        [Parameter(Mandatory = $true)]$Expected,
        [Parameter(Mandatory = $true)][string]$Message
    )
    if ($Actual -ne $Expected) {
        throw "${Message}: expected $Expected, got $Actual"
    }
}

Write-Host "[1/5] Checking API liveness"
$live = Invoke-RestMethod -Uri "$BaseUrl/health/live" -Method Get
Assert-Equal -Actual $live.status -Expected "ok" -Message "API liveness check failed"

Write-Host "[2/5] Checking API readiness"
$ready = Invoke-RestMethod -Uri "$BaseUrl/health/ready" -Method Get
Assert-Equal -Actual $ready.status -Expected "ready" -Message "API readiness check failed"

Write-Host "[3/5] Creating a short-lived guest session"
$guest = Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/guest" -Method Post
Assert-Equal -Actual $guest.user.role -Expected "guest" -Message "Unexpected guest role"
$headers = @{ Authorization = "Bearer $($guest.access_token)" }
$me = Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/me" -Headers $headers -Method Get
Assert-Equal -Actual $me.role -Expected "guest" -Message "Guest token verification failed"

Write-Host "[4/5] Verifying that guests cannot call model providers"
$denied = $false
try {
    Invoke-RestMethod `
        -Uri "$BaseUrl/api/v1/providers/generate" `
        -Headers $headers `
        -Method Post `
        -ContentType "application/json" `
        -Body '{"provider_key":"mock","prompt":"smoke test","language":"cpp"}' | Out-Null
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 403) {
        $denied = $true
    } else {
        throw
    }
}
Assert-Equal -Actual $denied -Expected $true -Message "Guest provider boundary failed"

Write-Host "[5/5] Checking the Web entry point"
$web = Invoke-WebRequest -Uri $WebUrl -Method Get -UseBasicParsing
Assert-Equal -Actual $web.StatusCode -Expected 200 -Message "Web entry-point check failed"

Write-Host "LLM-APT smoke test passed: API ready, guest session valid, restricted route denied, Web reachable." -ForegroundColor Green
