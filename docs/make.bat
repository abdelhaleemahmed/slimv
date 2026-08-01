@ECHO OFF
REM slimv documentation build for Windows (cmd / PowerShell) — mirrors the Makefile.
REM Usage:  make.bat html | html-ar | html-all | gettext | update-po | clean

setlocal
set SPHINXBUILD=python -m sphinx
set SOURCEDIR=source
set BUILDDIR=build

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="clean" goto clean
if "%1"=="html" goto html
if "%1"=="html-ar" goto htmlar
if "%1"=="html-all" goto htmlall
if "%1"=="gettext" goto gettext
if "%1"=="update-po" goto updatepo
goto help

:help
echo html       Build English HTML  -^> %BUILDDIR%\html\en
echo html-ar    Build Arabic HTML   -^> %BUILDDIR%\html\ar
echo html-all   Build both languages
echo gettext    Extract translatable strings
echo update-po  Create/refresh Arabic .po files
echo clean      Remove the build directory
goto end

:clean
if exist %BUILDDIR% rmdir /S /Q %BUILDDIR%
goto end

:html
set SPHINX_LANG=en
%SPHINXBUILD% -b html %SOURCEDIR% %BUILDDIR%\html\en
goto end

:htmlar
set SPHINX_LANG=ar
%SPHINXBUILD% -b html -D language=ar %SOURCEDIR% %BUILDDIR%\html\ar
goto end

:htmlall
call "%~f0" html
call "%~f0" html-ar
goto end

:gettext
%SPHINXBUILD% -b gettext %SOURCEDIR% %BUILDDIR%\gettext
goto end

:updatepo
python -m sphinx_intl update -p %BUILDDIR%\gettext -l ar -d %SOURCEDIR%\locale
goto end

:end
endlocal
