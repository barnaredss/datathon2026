$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$out = Join-Path $dir "preview"
New-Item -ItemType Directory -Force $out | Out-Null
$app = New-Object -ComObject PowerPoint.Application
$pres = $app.Presentations.Open((Join-Path $dir "presentacion.pptx"), -1, 0, 0)
$pres.Export($out, "PNG", 1280, 720)
$pres.Close()
$app.Quit()
