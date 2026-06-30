# ============================================================
#  Démarrage du serveur d'inférence Ollama — exposé sur le LAN
#  Équipe INFRA / TechCorp Challenge
# ============================================================
#  Lancer dans PowerShell :  .\start_server.ps1
# ============================================================

$ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"

# 1) Arrêter l'instance locale par défaut (écoute seulement 127.0.0.1)
Write-Host "Arret de l'instance Ollama existante..." -ForegroundColor Yellow
Get-Process ollama* -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 2) Exposer l'API sur toutes les interfaces (accessible depuis le LAN)
$env:OLLAMA_HOST = "0.0.0.0:11434"
# Autoriser les origines web (CORS) pour l'interface de l'equipe DEV WEB
$env:OLLAMA_ORIGINS = "*"

$ip = (Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null -and $_.NetAdapter.Status -eq 'Up' } | Select-Object -First 1).IPv4Address.IPAddress

Write-Host "Demarrage du serveur Ollama..." -ForegroundColor Green
Write-Host "  Local  : http://localhost:11434" -ForegroundColor Cyan
Write-Host "  LAN    : http://$ip`:11434   <-- a communiquer a l'equipe DEV WEB" -ForegroundColor Cyan
Write-Host "  Modele : phi35-financial" -ForegroundColor Cyan
Write-Host ""

# 3) Ouvrir le port dans le pare-feu Windows (necessite admin ; ignore si deja fait)
New-NetFirewallRule -DisplayName "Ollama 11434" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue | Out-Null

# 4) Lancer le serveur (bloquant)
& $ollama serve
