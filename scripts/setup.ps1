param(
    [switch]$Seed,
    [switch]$NoSeed,
    [switch]$Https,
    [switch]$NoHttps,
    [switch]$NoFrontend,
    [switch]$NoModel
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$venvPython = Join-Path $root "venv\Scripts\python.exe"

function Write-Step([string]$message) {
    Write-Host ""
    Write-Host ("==> " + $message) -ForegroundColor Cyan
}

function Fail([string]$message) {
    Write-Host ""
    Write-Host ("ERRO: " + $message) -ForegroundColor Red
    exit 1
}

Write-Host "============================================================" -ForegroundColor Blue
Write-Host "  TRILHA DE TALENTOS - instalacao local (Windows)" -ForegroundColor Blue
Write-Host "============================================================" -ForegroundColor Blue

Write-Step "Verificando Python (3.10 a 3.12)"
$candidates = @(
    @{ Exe = "py"; Prefix = @("-3.12") },
    @{ Exe = "py"; Prefix = @("-3.11") },
    @{ Exe = "py"; Prefix = @("-3.10") },
    @{ Exe = "python"; Prefix = @() }
)
$pythonExe = $null
$pythonPrefix = @()
$pythonVersion = $null
foreach ($candidate in $candidates) {
    $exe = Get-Command $candidate.Exe -ErrorAction SilentlyContinue
    if (-not $exe) { continue }
    try {
        $args = @($candidate.Prefix) + @("-c", "import sys; print(str(sys.version_info.major)+'.'+str(sys.version_info.minor))")
        $version = & $candidate.Exe @args 2>$null
        if ($LASTEXITCODE -eq 0 -and $version) {
            $pythonExe = $candidate.Exe
            $pythonPrefix = $candidate.Prefix
            $pythonVersion = $version.Trim()
            break
        }
    } catch { }
}

if (-not $pythonExe) {
    Fail "Python nao encontrado. Instale Python 3.12 (marque 'Add python.exe to PATH') em https://www.python.org/downloads/windows/"
}
$versionParts = $pythonVersion.Split(".")
$major = [int]$versionParts[0]
$minor = [int]$versionParts[1]
if ($major -ne 3 -or $minor -lt 10 -or $minor -gt 12) {
    Fail "Python $pythonVersion encontrado, mas a faixa suportada e 3.10 a 3.12. Baixe o Python 3.12."
}
Write-Host ("Python " + $pythonVersion + " encontrado (" + $pythonExe + ")") -ForegroundColor Green

Write-Step "Criando/validando venv"
if (-not (Test-Path $venvPython)) {
    $args = @($pythonPrefix) + @("-m", "venv", (Join-Path $root "venv"))
    & $pythonExe @args
    if ($LASTEXITCODE -ne 0) { Fail "Nao foi possivel criar a venv." }
    Write-Host "venv criada." -ForegroundColor Green
} else {
    Write-Host "venv ja existe." -ForegroundColor Green
}

Write-Step "Atualizando pip e instalando requisitos"
& $venvPython -m pip install --upgrade pip --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Fail "Falha ao atualizar o pip." }
& $venvPython -m pip install -r (Join-Path $root "requirements.txt") --disable-pip-version-check
if ($LASTEXITCODE -ne 0) {
    Fail "Falha ao instalar dependencias. Se o erro mencionar compilador C++, instale 'Build Tools for Visual Studio' com 'Desktop development with C++' e rode setup.bat novamente."
}

Write-Step "Validando InsightFace + ONNX Runtime"
& $venvPython -c "import insightface, onnxruntime, cv2, numpy; print('insightface', insightface.__version__); print('onnxruntime', onnxruntime.__version__); print('numpy', numpy.__version__)"
if ($LASTEXITCODE -ne 0) {
    Fail "InsightFace/ONNX Runtime nao importaram. Verifique o Build Tools C++ e rode novamente."
}

Write-Step "Preparando .env e pastas"
& $venvPython (Join-Path $root "scripts\bootstrap_env.py")
if ($LASTEXITCODE -ne 0) { Fail "Falha ao preparar .env." }

if (-not $NoModel) {
    Write-Step "Baixando/verificando modelo buffalo_l"
    & $venvPython (Join-Path $root "scripts\download_model.py")
    if ($LASTEXITCODE -ne 0) { Fail "Falha ao preparar o modelo facial buffalo_l." }
}

Write-Step "Inicializando banco SQLite"
& $venvPython (Join-Path $root "scripts\init_db.py")
if ($LASTEXITCODE -ne 0) { Fail "Falha ao inicializar o banco." }

if (-not $NoFrontend) {
    Write-Step "Compilando frontend React"
    $node = Get-Command node -ErrorAction SilentlyContinue
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $node -or -not $npm) {
        Fail "Node.js/npm nao encontrados. Instale Node.js 20+ em https://nodejs.org/ e rode setup.bat novamente."
    }
    $nodeVersion = (& node --version).TrimStart("v")
    $nodeMajor = [int]($nodeVersion.Split(".")[0])
    if ($nodeMajor -lt 20) { Fail "Node.js 20+ e necessario. Versao encontrada: $nodeVersion" }
    Write-Host ("Node.js " + $nodeVersion + " encontrado.") -ForegroundColor Green
    if (-not (Test-Path (Join-Path $root "node_modules"))) {
        & npm install
        if ($LASTEXITCODE -ne 0) { Fail "Falha no npm install." }
    }
    & npm run build
    if ($LASTEXITCODE -ne 0) { Fail "Falha ao compilar o frontend (npm run build)." }
}

$runSeed = $false
if ($Seed) {
    $runSeed = $true
} elseif (-not $NoSeed) {
    $answer = Read-Host "Deseja rodar o seed com usuarios de teste? [S/n]"
    if ([string]::IsNullOrWhiteSpace($answer) -or $answer -match "^[sSyY]") { $runSeed = $true }
}
if ($runSeed) {
    Write-Step "Rodando seed idempotente"
    & $venvPython (Join-Path $root "scripts\seed.py")
    if ($LASTEXITCODE -ne 0) { Fail "Falha ao rodar o seed." }
}

$makeHttps = $false
if ($Https) {
    $makeHttps = $true
} elseif (-not $NoHttps) {
    $answer = Read-Host "Deseja gerar certificado HTTPS local para usar a camera ao vivo? [s/N]"
    if ($answer -match "^[sSyY]") { $makeHttps = $true }
}
if ($makeHttps) {
    Write-Step "Gerando certificado HTTPS autoassinado"
    & $venvPython (Join-Path $root "scripts\make_cert.py")
    if ($LASTEXITCODE -ne 0) { Fail "Falha ao gerar o certificado HTTPS." }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  INSTALACAO CONCLUIDA" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  1. Inicie o sistema com: start.bat"
Write-Host "  2. Abra no celular o endereco exibido (mesma rede Wi-Fi)."
Write-Host "  3. RH: rh@lins.com.br / LinsRh@2026"
Write-Host "     Lider: lider@lins.com.br / LinsLider@2026"
Write-Host "     Instrutor: instrutor@lins.com.br / LinsInstrutor@2026"
Write-Host "     Funcionario: rafael@lins.com.br / Rafael@2026 (troca obrigatoria)"
Write-Host ""
Write-Host "  Camera ao vivo no celular exige HTTPS: start.bat --https"
Write-Host "  O formulario com camera nativa (capture=user) funciona em HTTP."
Write-Host ""
