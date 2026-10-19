# Builds the frontend locally (npm run build) and uploads frontend/dist to the
# EC2 instance's Nginx web root. Run from anywhere on your PC:
#
#   .\deploy\deploy-frontend.ps1 -HostName <ec2-public-ip> -KeyPath C:\path\to\key.pem
param(
    [Parameter(Mandatory = $true)][string]$HostName,
    [Parameter(Mandatory = $true)][string]$KeyPath,
    [string]$User = 'ubuntu',
    [string]$WebRoot = '/var/www/chat-exporter'
)

$ErrorActionPreference = 'Stop'
$frontend = Resolve-Path (Join-Path $PSScriptRoot '..\frontend')
$target = "$User@$HostName"
$staging = '/tmp/chat-exporter-dist'

Push-Location $frontend
try {
    if (-not (Test-Path 'node_modules')) {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
    }

    # Uses .env.production, so the build calls /api on its own origin.
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'npm run build failed' }
}
finally {
    Pop-Location
}

ssh -i $KeyPath $target "rm -rf $staging"
if ($LASTEXITCODE -ne 0) { throw 'ssh failed - check -HostName, -KeyPath and the security group (port 22)' }

scp -i $KeyPath -r (Join-Path $frontend 'dist') "${target}:$staging"
if ($LASTEXITCODE -ne 0) { throw 'scp upload failed' }

ssh -i $KeyPath $target "rm -rf $WebRoot/* && cp -r $staging/. $WebRoot/ && rm -rf $staging"
if ($LASTEXITCODE -ne 0) { throw "copying into $WebRoot failed - did deploy/setup-server.sh run?" }

Write-Host "Frontend deployed: http://$HostName"
