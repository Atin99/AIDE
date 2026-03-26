param(
  [string]$OutDir = "deploy/hf_space_bundle"
)

$ErrorActionPreference = "Stop"

if (Test-Path $OutDir) {
  Remove-Item -Recurse -Force $OutDir
}

New-Item -ItemType Directory -Force $OutDir | Out-Null

$paths = @(
  "backend",
  "core",
  "engines",
  "explainability",
  "llms",
  "ml",
  "optimisation",
  "physics",
  "rag",
  "requirements.txt",
  "openapi.yaml",
  ".env.example"
)

foreach ($path in $paths) {
  if (Test-Path $path) {
    Copy-Item -Recurse -Force $path (Join-Path $OutDir $path)
  }
}

Copy-Item -Force "deploy/backend.Dockerfile" (Join-Path $OutDir "Dockerfile")
Copy-Item -Force "deploy/hf_space_README.md" (Join-Path $OutDir "README.md")

Write-Output "Created Hugging Face Space bundle at: $OutDir"
