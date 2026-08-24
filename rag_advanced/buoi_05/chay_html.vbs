Option Explicit
Dim fso, dir, sh, pyw
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = dir & "\.venv\Scripts\pythonw.exe"
Set sh = CreateObject("WScript.Shell")
' Dong moi instance serve_html dang chay tren 8000
sh.Run "powershell -NoProfile -WindowStyle Hidden -Command ""Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }""", 0, True
' Khoi dong serve_html moi, an cua so, tu mo trinh duyet
sh.Run "powershell -NoProfile -WindowStyle Hidden -Command ""Start-Process -FilePath '" & pyw & "' -ArgumentList 'src\serve_html.py' -WorkingDirectory '" & dir & "' -WindowStyle Hidden""", 0, False
