# Create the directory if it doesn't exist
$configDir = "$env:USERPROFILE\.zedtv"
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    Write-Host "Created directory: $configDir"
}

# Create the configuration content
$configContent = @"
{
  "default_country": "RO",
  "geo_detection": true,
  "playlist_last_path": ""
}
"@

# Write to the config file
$configFile = Join-Path -Path $configDir -ChildPath "config.json"
Set-Content -Path $configFile -Value $configContent

# Verify and display results
if (Test-Path $configFile) {
    Write-Host "Config file created successfully at: $configFile"
    Write-Host "File contents:"
    Get-Content -Path $configFile
} else {
    Write-Host "Failed to create the config file!"
}
