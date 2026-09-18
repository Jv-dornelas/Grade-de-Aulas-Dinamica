param([switch]$AceitarLicencaSdk)
$ErrorActionPreference = 'Stop'

if (-not $AceitarLicencaSdk) {
    throw 'Leia https://developer.android.com/studio#terms-and-conditions. Se concordar, execute este script com -AceitarLicencaSdk.'
}

$androidProject = $PSScriptRoot
$projectRoot = Split-Path -Parent $androidProject
$apkOutput = Join-Path $projectRoot 'dist'

docker build --build-arg ACCEPT_ANDROID_SDK_LICENSES=true -t minha-grade-android-builder $androidProject
if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar as ferramentas Android.' }

# As chaves de debug ficam neste volume local, fora do Git. Preserve o volume para
# instalar futuras versões de teste sem desinstalar a anterior.
docker run --rm --mount "type=bind,source=$androidProject,target=/workspace" --mount 'type=volume,source=minha-grade-gradle-cache,target=/home/gradle/.gradle' --mount 'type=volume,source=minha-grade-android-keys,target=/root/.android' minha-grade-android-builder
if ($LASTEXITCODE -ne 0) { throw 'Compilação ou análise Android falhou. Consulte a saída acima.' }

docker run --rm --mount "type=bind,source=$androidProject,target=/workspace,readonly" minha-grade-android-builder /opt/android-sdk/build-tools/35.0.0/apksigner verify --verbose /workspace/app/build/outputs/apk/debug/app-debug.apk
if ($LASTEXITCODE -ne 0) { throw 'Falha na verificação da assinatura do APK.' }

New-Item -ItemType Directory -Path $apkOutput -Force | Out-Null
$apkPath = Join-Path $apkOutput 'MinhaGrade-demo.apk'
Copy-Item -LiteralPath (Join-Path $androidProject 'app/build/outputs/apk/debug/app-debug.apk') -Destination $apkPath
$localDownload = Join-Path $projectRoot 'grade/static/grade/mobile/MinhaGrade-demo.apk'
Copy-Item -LiteralPath $apkPath -Destination $localDownload
Get-FileHash -LiteralPath $apkPath -Algorithm SHA256
Write-Host "APK gerado em: $apkPath"
Write-Host 'Download local pelo Django: /static/grade/mobile/MinhaGrade-demo.apk'
