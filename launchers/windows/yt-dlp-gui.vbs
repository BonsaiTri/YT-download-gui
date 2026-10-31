' yt-dlp GUI - launcher without a console window.
'
' Double-click this file (or use the shortcut installed by
' install-launcher.bat) to start the GUI using pythonw.exe, so no black
' command prompt appears behind the window.
'
' It finds the project root by walking up from its own folder until it sees
' yt_dlp_gui.py, so the file can live anywhere inside the repository.

Option Explicit

Dim fso, sh, here, root, script, pythonw, cmd, rc

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

' ---- locate the project root (the folder containing yt_dlp_gui.py) --------
here = fso.GetParentFolderName(WScript.ScriptFullName)
root = here
Do While root <> ""
    If fso.FileExists(fso.BuildPath(root, "yt_dlp_gui.py")) Then Exit Do
    If fso.GetParentFolderName(root) = root Then
        root = ""
        Exit Do
    End If
    root = fso.GetParentFolderName(root)
Loop

If root = "" Then
    MsgBox "Could not find yt_dlp_gui.py." & vbCrLf & vbCrLf & _
           "Keep this launcher inside the yt-dlp-gui folder.", _
           vbCritical, "yt-dlp GUI"
    WScript.Quit 1
End If

script = fso.BuildPath(root, "yt_dlp_gui.py")

' ---- find pythonw.exe (same interpreter, no console) ---------------------
pythonw = FindPythonW()
If pythonw = "" Then
    pythonw = FindPythonConsole()
End If

If pythonw = "" Then
    MsgBox "Python 3 was not found." & vbCrLf & vbCrLf & _
           "Install it from https://python.org and tick" & vbCrLf & _
           """Add python.exe to PATH"".", _
           vbCritical, "yt-dlp GUI"
    WScript.Quit 1
End If

' ---- hand over ----------------------------------------------------------
' 0 = hidden window, False = don't wait for it to finish
sh.CurrentDirectory = root
rc = sh.Run(Quote(pythonw) & " " & Quote(script), 0, False)

If rc <> 0 Then
    MsgBox "The GUI could not be started (error " & rc & ")." & vbCrLf & vbCrLf & _
           "Run this to see the error:" & vbCrLf & _
           "    python """ & script & """", _
           vbExclamation, "yt-dlp GUI"
End If


' ------ helpers ----------------------------------------------------------
Function Quote(s)
    Quote = """" & s & """"
End Function

' Ask the shell where pythonw.exe is (respects PATH and app aliases).
Function WhichExe(exeName)
    Dim proc, line
    WhichExe = ""
    On Error Resume Next
    Set proc = sh.Exec("cmd /c where " & exeName & " 2>nul")
    If Err.Number <> 0 Then
        On Error GoTo 0
        Exit Function
    End If
    Do While Not proc.StdOut.AtEndOfStream
        line = Trim(proc.StdOut.ReadLine())
        If line <> "" And fso.FileExists(line) Then
            WhichExe = line
            Exit Do
        End If
    Loop
    On Error GoTo 0
End Function

Function FindPythonW()
    Dim p
    p = WhichExe("pythonw.exe")
    If p <> "" Then
        FindPythonW = p
        Exit Function
    End If
    ' Fall back to pythonw.exe next to a python.exe we can find.
    p = WhichExe("python.exe")
    If p <> "" Then
        p = fso.BuildPath(fso.GetParentFolderName(p), "pythonw.exe")
        If fso.FileExists(p) Then
            FindPythonW = p
            Exit Function
        End If
    End If
    FindPythonW = ""
End Function

Function FindPythonConsole()
    FindPythonConsole = WhichExe("python.exe")
End Function
