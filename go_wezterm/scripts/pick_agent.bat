@echo off
choice /c CP /n /m "[C]laude or [P]i: "
if errorlevel 2 (pi) else (claude)