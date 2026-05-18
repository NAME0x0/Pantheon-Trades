# Pantheon Trades — Arc Testnet witness seeder.
#
# Writes a handful of realistic Proof-of-Restraint witnesses (council
# declined trades) and VisitorWitness records (visitor demo runs) to
# Arc Testnet so the public dashboard at /dashboard renders a populated
# feed for showcase / traction screenshots.
#
# Idempotent: every entry has a unique signalHash / visitHash, so
# re-running adds new rows without conflicting with existing ones.
#
# Required env: PRIVATE_KEY (deployer / restraint-role holder). The
# deployer of ProofOfRestraint has the role automatically — see
# contracts/script/DeployRestraint.s.sol.

param(
    [int] $RestraintCount = 4,
    [int] $VisitorCount   = 3
)

$ErrorActionPreference = 'Stop'

$rpc       = 'https://rpc.testnet.arc.network'
$arcscan   = 'https://testnet.arcscan.app'
$porAddr   = '0x4b35CE4Bf71B976205f60Fda1EBAb82eD4D34895'
$vwAddr    = '0xF35B1fa5A6026C61C187881eA17d77F97Cd1AFA7'
$castExe   = "$env:USERPROFILE\.foundry\bin\cast.exe"

# Pull PRIVATE_KEY from .env at the repo root.
$envFile = Join-Path $PSScriptRoot '..\.env'
$pk = (Select-String -Path $envFile -Pattern '^PRIVATE_KEY=' | Select-Object -First 1).Line -replace '^PRIVATE_KEY=',''
if (-not $pk) { throw "PRIVATE_KEY not found in .env" }

function New-Bytes32Hex {
    $bytes = [byte[]]::new(32)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return '0x' + ([BitConverter]::ToString($bytes).Replace('-','').ToLower())
}

function Invoke-Cast {
    param([string] $To, [string] $Sig, [string[]] $CallArgs)
    $allArgs = @('send', $To, $Sig) + $CallArgs + @(
        '--rpc-url', $rpc,
        '--private-key', $pk,
        '--json'
    )
    # cast send mixes its progress lines into stderr; merge both streams,
    # then strip out anything that isn't the JSON body. We look for the
    # first '{' and the matching last '}' so JSON parses cleanly.
    $out = (& $castExe @allArgs 2>&1 | Out-String)
    if ([string]::IsNullOrWhiteSpace($out)) {
        throw "cast send returned empty output for $Sig"
    }
    $start = $out.IndexOf('{')
    $end   = $out.LastIndexOf('}')
    if ($start -lt 0 -or $end -le $start) {
        throw "cast send did not return JSON for $Sig`n$out"
    }
    return $out.Substring($start, $end - $start + 1)
}

# ── Restraint scenarios — realistic veto reason codes that match
#    services/areopagus/src/areopagus/court.py + RestraintCard labels.
$restraints = @(
    @{
        marketId   = '0xa6f9e34d-eth-3500-2026-q2'
        reasonCode = 'EDGE'
        note       = 'directional edge 1.8pp below 5pp constitutional floor; refused.'
    },
    @{
        marketId   = '0x4d8e21b3-fed-rate-cut-may-2026'
        reasonCode = 'STALENESS'
        note       = 'oracle quote 412s old; spread > 50bp. trade refused.'
    },
    @{
        marketId   = '0x9c5be71a-superbowl-lxiii-chiefs'
        reasonCode = 'LIQUIDITY'
        note       = '24h volume 11,400 USDC against 50,000 floor (Article IV §1).'
    },
    @{
        marketId   = '0x71e4082c-us-election-2028-incumbent'
        reasonCode = 'CATEGORY_EXPOSURE'
        note       = 'politics cluster at 3.9% NAV; adding would breach 4% cap.'
    },
    @{
        marketId   = '0xd2b91f63-btc-200k-eoy-2027'
        reasonCode = 'ZEUS_VETO'
        note       = 'Zeus: macro-cluster correlation 0.78 > 0.65 constitutional ceiling.'
    },
    @{
        marketId   = '0xfa3782e9-recession-h2-2026'
        reasonCode = 'SOLON_VETO'
        note       = 'Solon: Themis flagged thesis lacking source citation per Article VII.'
    }
)

# ── Visitor scenarios — labels match what /demo's WitnessButton sends.
$visitors = @(
    'btc-120k-approve',
    'btc-120k-restraint',
    'election-2028-approve',
    'nfl-superbowl-restraint',
    'coingecko-paper-trade',
    'backtest-200-markets'
)

Write-Host "→ Seeding $RestraintCount Proof-of-Restraint witnesses on Arc..."
$porTxs = @()
for ($i = 0; $i -lt $RestraintCount; $i++) {
    $r = $restraints[$i % $restraints.Count]
    $h = New-Bytes32Hex
    Write-Host ("  [{0}/{1}] {2,-18} {3}" -f ($i+1), $RestraintCount, $r.reasonCode, $r.marketId)
    $raw = Invoke-Cast -To $porAddr -Sig 'declineTrade(bytes32,string,string,string)' -CallArgs @($h, $r.marketId, $r.reasonCode, $r.note)
    $json = $raw | ConvertFrom-Json
    $porTxs += [pscustomobject]@{
        tx         = $json.transactionHash
        block      = [Convert]::ToInt64($json.blockNumber, 16)
        reasonCode = $r.reasonCode
    }
    Start-Sleep -Milliseconds 400  # small spacing — avoid mempool ordering races
}

Write-Host "→ Seeding $VisitorCount VisitorWitness records on Arc..."
$vwTxs = @()
for ($i = 0; $i -lt $VisitorCount; $i++) {
    $scenario = $visitors[$i % $visitors.Count]
    $h = New-Bytes32Hex
    Write-Host ("  [{0}/{1}] {2}" -f ($i+1), $VisitorCount, $scenario)
    $raw = Invoke-Cast -To $vwAddr -Sig 'witness(bytes32,string)' -CallArgs @($h, $scenario)
    $json = $raw | ConvertFrom-Json
    $vwTxs += [pscustomobject]@{
        tx       = $json.transactionHash
        block    = [Convert]::ToInt64($json.blockNumber, 16)
        scenario = $scenario
    }
    Start-Sleep -Milliseconds 400
}

Write-Host "`n=== Restraints written ==="
$porTxs | Format-Table -AutoSize @{n='reason'; e={$_.reasonCode}}, @{n='block'; e={$_.block}}, @{n='arcscan'; e={"$arcscan/tx/$($_.tx)"}}

Write-Host "`n=== Visitor witnesses written ==="
$vwTxs | Format-Table -AutoSize @{n='scenario'; e={$_.scenario}}, @{n='block'; e={$_.block}}, @{n='arcscan'; e={"$arcscan/tx/$($_.tx)"}}

Write-Host "`nDashboard will reflect both feeds on its next 30s revalidate."
