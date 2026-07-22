param(
    [string]$AdminUsername = "admin"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$target = Join-Path $repoRoot ".env"
if (Test-Path -LiteralPath $target) {
    throw ".env already exists. Back it up or remove it before generating a new configuration."
}

function New-Secret([int]$bytes = 32) {
    $buffer = New-Object byte[] $bytes
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($buffer)
    }
    finally {
        $generator.Dispose()
    }
    return [Convert]::ToBase64String($buffer).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

$postgresPassword = New-Secret 24
$rabbitPassword = New-Secret 24
$minioPassword = New-Secret 24
$runnerToken = New-Secret 32
$authSecret = New-Secret 48
$adminPassword = New-Secret 18

$content = @"
LLMAPT_ENVIRONMENT=development
LLMAPT_DEBUG=false
LLMAPT_LOG_LEVEL=INFO
LLMAPT_LOG_FORMAT=console
LLMAPT_API_PORT=8000
LLMAPT_WEB_PORT=3000
LLMAPT_WORKER_CONCURRENCY=2

POSTGRES_DB=llmapt
POSTGRES_USER=llmapt
POSTGRES_PASSWORD=$postgresPassword
RABBITMQ_DEFAULT_USER=llmapt
RABBITMQ_DEFAULT_PASS=$rabbitPassword
MINIO_ROOT_USER=llmapt
MINIO_ROOT_PASSWORD=$minioPassword

LLMAPT_DATABASE_URL=postgresql+asyncpg://llmapt:$postgresPassword@postgres:5432/llmapt
LLMAPT_BROKER_URL=amqp://llmapt:$rabbitPassword@rabbitmq:5672//
LLMAPT_REDIS_URL=redis://redis:6379/0
LLMAPT_OBJECT_STORE_ENDPOINT=http://minio:9000
LLMAPT_OBJECT_STORE_BUCKET=llmapt-artifacts

LLMAPT_EXTERNAL_MODEL_CALLS_ENABLED=false
LLMAPT_MODEL_PROVIDER_KEY=external
LLMAPT_MODEL_PROVIDER_NAME=openai-compatible
LLMAPT_MODEL_NAME=
LLMAPT_MODEL_REVISION=
LLMAPT_MODEL_API_ENDPOINT=
LLMAPT_MODEL_API_KEY=
LLMAPT_MODEL_TIMEOUT_SECONDS=60
LLMAPT_RUNNER_URL=http://runner:8080
LLMAPT_RUNNER_TOKEN=$runnerToken
LLMAPT_RUNNER_TIMEOUT_SECONDS=35

LLMAPT_AUTH_SECRET=$authSecret
LLMAPT_BOOTSTRAP_ADMIN_USERNAME=$AdminUsername
LLMAPT_BOOTSTRAP_ADMIN_PASSWORD=$adminPassword
LLMAPT_BOOTSTRAP_ADMIN_DISPLAY_NAME=Local Administrator
LLMAPT_ACCESS_TOKEN_TTL_MINUTES=480
LLMAPT_GUEST_TOKEN_TTL_MINUTES=120
"@

[System.IO.File]::WriteAllText($target, $content, [System.Text.UTF8Encoding]::new($false))
Write-Host "Created $target"
Write-Host "Administrator username: $AdminUsername"
Write-Host "Administrator password is stored in .env (LLMAPT_BOOTSTRAP_ADMIN_PASSWORD)."
Write-Host "Do not commit or share the .env file."
