param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Email = "",
    [string]$Password = ""
)

$ErrorActionPreference = "Stop"

function Test-Get {
    param(
        [string]$Path,
        [int[]]$ExpectedStatus
    )

    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl$Path" -UseBasicParsing -TimeoutSec 20
        $statusCode = [int]$response.StatusCode
        $ok = $ExpectedStatus -contains $statusCode
        [pscustomobject]@{
            path = $Path
            status = $statusCode
            ok = $ok
        }
    } catch {
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode.value__
            $ok = $ExpectedStatus -contains $statusCode
            [pscustomobject]@{
                path = $Path
                status = $statusCode
                ok = $ok
            }
        } else {
            throw
        }
    }
}

$results = @()
$results += Test-Get -Path "/health" -ExpectedStatus @(200)
$results += Test-Get -Path "/v1/health" -ExpectedStatus @(200)
$results += Test-Get -Path "/docs" -ExpectedStatus @(200)

$token = $null

if ($Email -and $Password) {
    $body = @{
        email = $Email
        password = $Password
    } | ConvertTo-Json

    try {
        $login = Invoke-WebRequest `
            -Uri "$BaseUrl/auth/login" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body `
            -UseBasicParsing `
            -TimeoutSec 20

        $statusCode = [int]$login.StatusCode
        $ok = $statusCode -eq 200
        $results += [pscustomobject]@{
            path = "/auth/login"
            status = $statusCode
            ok = $ok
        }

        if ($ok) {
            $payload = $login.Content | ConvertFrom-Json
            $token = $payload.token
        }
    } catch {
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode.value__
            $results += [pscustomobject]@{
                path = "/auth/login"
                status = $statusCode
                ok = $false
            }
        } else {
            throw
        }
    }
}

if ($token) {
    try {
        $me = Invoke-WebRequest `
            -Uri "$BaseUrl/auth/me" `
            -Headers @{ Authorization = "Bearer $token" } `
            -UseBasicParsing `
            -TimeoutSec 20
        $results += [pscustomobject]@{
            path = "/auth/me (with token)"
            status = [int]$me.StatusCode
            ok = ([int]$me.StatusCode -eq 200)
        }

        $aprs = Invoke-WebRequest `
            -Uri "$BaseUrl/v1/aprs?skip=0&limit=5" `
            -Headers @{ Authorization = "Bearer $token" } `
            -UseBasicParsing `
            -TimeoutSec 20
        $results += [pscustomobject]@{
            path = "/v1/aprs (with token)"
            status = [int]$aprs.StatusCode
            ok = ([int]$aprs.StatusCode -eq 200)
        }
    } catch {
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode.value__
            $results += [pscustomobject]@{
                path = "/auth/me or /v1/aprs"
                status = $statusCode
                ok = $false
            }
        } else {
            throw
        }
    }
} else {
    $results += Test-Get -Path "/auth/me" -ExpectedStatus @(401)
}

$results | Format-Table -AutoSize

$failed = $results | Where-Object { -not $_.ok }
if ($failed) {
    Write-Error "Smoke test failed."
}

Write-Host "Smoke test passed."
