# PowerShell script to reset and start the local AI environment
# This script follows best practices for PowerShell profile configuration

# Suppress PowerShell update warnings
$global:PROFILE_UPDATE_DISABLED = $true
$global:POWERSHELL_UPDATE_DISABLED = $true

Write-Host "Starting reset and startup process for Local AI environment..." -ForegroundColor Cyan

# Step 1: Stop all existing containers
Write-Host "Stopping all existing containers..." -ForegroundColor Yellow
try {
    docker compose -p localai down --remove-orphans
} catch {
    Write-Host "Warning: Error stopping containers, continuing anyway..." -ForegroundColor Yellow
}

# Step 2: Remove the Docker network if it exists
Write-Host "Removing existing Docker networks..." -ForegroundColor Yellow
$networks = docker network ls --filter "name=localai" --format "{{.ID}}"
foreach ($network in $networks) {
    if ($network) {
        Write-Host "Removing network: $network" -ForegroundColor Gray
        docker network rm $network
    }
}

# Step 3: Prune Docker resources
Write-Host "Pruning Docker resources..." -ForegroundColor Yellow
docker system prune -f

# Step 4: Clone/update Supabase repo
Write-Host "Setting up Supabase repository..." -ForegroundColor Yellow
if (-not (Test-Path "supabase")) {
    Write-Host "Cloning Supabase repository..." -ForegroundColor Gray
    git clone --filter=blob:none --no-checkout https://github.com/supabase/supabase.git
    Push-Location supabase
    git sparse-checkout init --cone
    git sparse-checkout set docker
    git checkout master
    Pop-Location
} else {
    Write-Host "Updating Supabase repository..." -ForegroundColor Gray
    Push-Location supabase
    git pull
    Pop-Location
}

# Step 5: Copy .env file
Write-Host "Copying environment file..." -ForegroundColor Yellow
Copy-Item -Path ".env" -Destination "supabase\docker\.env" -Force

# Step 6: Start Supabase services
Write-Host "Starting Supabase services..." -ForegroundColor Green
docker compose -p localai -f supabase/docker/docker-compose.yml up -d

# Step 7: Wait for Supabase to initialize
Write-Host "Waiting for Supabase to initialize (15 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Step 8: Start local AI services
$containerProfile = "cpu"  # Default profile, can be changed to gpu-nvidia or gpu-amd
Write-Host "Starting local AI services with profile: $containerProfile..." -ForegroundColor Green
docker compose -p localai --profile $containerProfile -f docker-compose.yml up -d

Write-Host "Startup process completed!" -ForegroundColor Cyan
Write-Host "If you encounter any issues, try running 'docker system prune -a' and restart." -ForegroundColor Cyan
