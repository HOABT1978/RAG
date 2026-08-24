Option Explicit
Dim fso, dir, sh, pyw
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = dir & "\.venv\Scripts\pythonw.exe"
Set sh = CreateObject("WScript.Shell")
' Dong moi instance Streamlit dang chay tren 8502
sh.Run "powershell -NoProfile -WindowStyle Hidden -Command ""Get-NetTCPConnection -LocalPort 8502 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }""", 0, True
' Khoi dong Streamlit moi, an cua so, tu mo trinh duyet
sh.Run "powershell -NoProfile -WindowStyle Hidden -Command ""Start-Process -FilePath '" & pyw & "' -ArgumentList '-m','streamlit','run','app.py','--server.port','8502' -WorkingDirectory '" & dir & "' -WindowStyle Hidden""", 0, False
