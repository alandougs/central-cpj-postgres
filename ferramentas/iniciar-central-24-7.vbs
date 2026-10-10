' Inicializador silencioso da Central CPJ 24/7 (sem janela de console)
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strRootDir = objFSO.GetParentFolderName(strScriptDir)

strPython = strRootDir & "\.venv\Scripts\python.exe"
If Not objFSO.FileExists(strPython) Then strPython = "python"
Set objEnv = objShell.Environment("PROCESS")
If objFSO.FileExists(strPython) Then objEnv("PATH") = objFSO.GetParentFolderName(strPython) & ";" & objEnv("PATH")
objEnv("CPJ_WORKSPACE") = strRootDir
objEnv("CPJ_WORKSPACES") = ""
strCommand = """" & strPython & """ """ & strScriptDir & "\central-daemon.py"" iniciar --porta 8765"
objShell.CurrentDirectory = strRootDir
objShell.Run strCommand, 0, False
