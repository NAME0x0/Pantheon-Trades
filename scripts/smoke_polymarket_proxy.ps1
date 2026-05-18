# Pantheon Trades — Polymarket proxy smoke test.
#
# Confirms the Vercel edge proxy at apps/web/app/api/polymarket-proxy/
# correctly forwards Polymarket Gamma + CLOB requests from a geo-blocked
# host, returning real upstream JSON instead of the standard
# "Polymarket is not available in your region" HTML.
#
# Usage (after deploying apps/web to Vercel):
#
#   pwsh scripts/smoke_polymarket_proxy.ps1
#
# Defaults to the production Vercel URL; override via -BaseUrl.

param(
    [string] $BaseUrl  = 'https://pantheon-trades-web.vercel.app',
    [string] $ProxyToken = ''
)

$ErrorActionPreference = 'Stop'

$gamma = "$BaseUrl/api/polymarket-proxy/gamma/markets?limit=3&active=true&closed=false&order=volume24hr&ascending=false"
$clob  = "$BaseUrl/api/polymarket-proxy/clob/markets?limit=1"

$headers = @{ 'Accept' = 'application/json' }
if ($ProxyToken) { $headers['X-Pantheon-Proxy-Token'] = $ProxyToken }

function Probe {
    param([string] $Name, [string] $Url)
    Write-Host "→ $Name → $Url"
    try {
        $resp = Invoke-WebRequest -Uri $Url -Headers $headers -TimeoutSec 20
        Write-Host "  status: $($resp.StatusCode)" -ForegroundColor Green
        $ct = $resp.Headers['Content-Type']
        Write-Host "  content-type: $ct"
        $body = $resp.Content
        if ($ct -like '*application/json*') {
            $parsed = $body | ConvertFrom-Json
            if ($parsed -is [System.Array]) {
                Write-Host "  array length: $($parsed.Count)"
                if ($parsed.Count -gt 0) {
                    $first = $parsed[0]
                    if ($first.question) { Write-Host "  first question: $($first.question)" }
                    if ($first.condition_id) { Write-Host "  first condition_id: $($first.condition_id)" }
                }
            } else {
                $keys = ($parsed.PSObject.Properties | Select-Object -First 8 -ExpandProperty Name) -join ', '
                Write-Host "  keys: $keys"
            }
            return $true
        }
        if ($body -match 'not available in your region|geographic|forbidden') {
            Write-Host "  FAIL — upstream returned geo-block payload through proxy" -ForegroundColor Red
            return $false
        }
        Write-Host "  WARN — non-JSON response, first 200 chars:" -ForegroundColor Yellow
        Write-Host "  $($body.Substring(0, [Math]::Min(200, $body.Length)))"
        return $false
    } catch {
        Write-Host "  ERROR: $_" -ForegroundColor Red
        return $false
    }
}

$gOk = Probe -Name 'Gamma · markets (top 3 by volume)' -Url $gamma
Write-Host ''
$cOk = Probe -Name 'CLOB · markets (limit 1)' -Url $clob

Write-Host ''
if ($gOk -and $cOk) {
    Write-Host '✓ Polymarket proxy is live — Gamma + CLOB both reachable from this host.' -ForegroundColor Green
    exit 0
} else {
    Write-Host '✗ Proxy smoke test failed. Check Vercel deploy logs + UPSTREAM_MAP routing.' -ForegroundColor Red
    exit 1
}
