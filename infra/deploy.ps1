param(
    [string]$ResourceGroup = "signaldesk-rg",
    [Parameter(Mandatory = $true)][string]$Location,
    [ValidateSet("F1", "B1")][string]$Sku = "B1"
)

# az prints warnings to stderr; rely on exit codes instead of $ErrorActionPreference = "Stop".
function Assert-Ok([string]$step) {
    if ($LASTEXITCODE -ne 0) { throw "$step failed (exit $LASTEXITCODE)" }
}

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$zip = Join-Path $env:TEMP "signaldesk-backend.zip"

az group create --name $ResourceGroup --location $Location --output none --only-show-errors
Assert-Ok "Resource group"

$outputs = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file (Join-Path $PSScriptRoot "main.bicep") `
    --parameters sku=$Sku `
    --query properties.outputs --output json --only-show-errors | ConvertFrom-Json
Assert-Ok "Bicep deployment"
$appName = $outputs.appName.value

$staging = Join-Path $env:TEMP "signaldesk-staging"
Remove-Item $staging, $zip -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory $staging | Out-Null
Copy-Item (Join-Path $backend "requirements.txt") $staging
Copy-Item (Join-Path $backend "app") $staging -Recurse
Get-ChildItem $staging -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# Compress-Archive on Windows PowerShell writes backslash paths, which Linux App Service can't unpack into folders.
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open($zip, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    Get-ChildItem $staging -Recurse -File | ForEach-Object {
        $entry = $_.FullName.Substring($staging.Length + 1).Replace("\", "/")
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $_.FullName, $entry) | Out-Null
    }
} finally {
    $archive.Dispose()
}

az webapp deploy --resource-group $ResourceGroup --name $appName --src-path $zip --type zip --output none --only-show-errors
Assert-Ok "Code deployment"

Write-Host "Deployed: $($outputs.url.value)"
