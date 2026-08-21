@ECHO OFF
if exist "wezterm-config.bat" call "wezterm-config.bat"

REM pdir        -> last 1 folder (default)
REM pdir 0      -> full path (drive + path)
REM pdir N      -> last N folders, 1-99
REM              if N > depth, also prefix drive

SET "ARG=%~1"
IF "%ARG%"=="" SET "ARG=1"

IF /I "%ARG%"=="0" GOTO full

SETLOCAL ENABLEDELAYEDEXPANSION

REM Parse requested N (REQ) and clamp 1-99
SET /A REQ=%ARG% 2>nul
IF "!REQ!"=="" SET "REQ=1"
IF !REQ! LSS 1 SET "REQ=1"
IF !REQ! GTR 99 SET "REQ=99"

SET "FULL=%CD%"
SET "DRIVE=!FULL:~0,3!"
SET "REST=!FULL:~3!"

SET "COUNT=0"

:split
IF "!REST!"=="" GOTO split_done
FOR /F "tokens=1* delims=\\" %%A IN ("!REST!") DO (
  SET /A COUNT+=1
  SET "COMP!COUNT!=%%A"
  SET "REST=%%B"
)
GOTO split

:split_done
IF !COUNT! EQU 0 (
  REM Root like D:\
  SET "RESULT=!DRIVE!"
) ELSE (
  REM USE = how many components we *can* show (<= COUNT)
  SET /A USE=REQ
  IF !USE! GTR !COUNT! SET /A USE=COUNT

  SET /A START=COUNT-USE+1
  SET "RESULT="

  FOR /L %%I IN (!START!,1,!COUNT!) DO (
    IF DEFINED RESULT (
      SET "RESULT=!RESULT!\!COMP%%I!"
    ) ELSE (
      SET "RESULT=!COMP%%I!"
    )
  )

  REM If requested more levels than exist, prefix drive
  IF !REQ! GTR !COUNT! (
    SET "RESULT=!DRIVE!!RESULT!"
  )
)

SET "NEWPROMPT=!RESULT!$G"
ENDLOCAL & PROMPT %NEWPROMPT%
GOTO :EOF

:full
PROMPT $P$G
GOTO :EOF