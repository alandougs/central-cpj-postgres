' Inicializador silencioso da Central CPJ 24/7 (sem janela de console)
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strRootDir = objFSO.GetParentFolderName(strScriptDir)

strCommand = "python """ & strScriptDir & "\central-daemon.py"" iniciar --porta 8765"
objShell.CurrentDirectory = strRootDir
objShell.Run strCommand, 0, False
