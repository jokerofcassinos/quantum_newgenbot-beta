@echo off
echo ============================================
echo Forex Quantum Bot - C++ Build Script
echo ============================================
echo.

set MSYS2_PATH=D:\msys64
set BUILD_DIR=%MSYS2_PATH%\usr\bin

echo Checking MSYS2 installation...
if not exist "%MSYS2_PATH%\msys2_shell.cmd" (
    echo ERROR: MSYS2 not found at %MSYS2_PATH%
    echo Please install MSYS2 from https://www.msys2.org/
    pause
    exit /b 1
)

echo MSYS2 found at %MSYS2_PATH%
echo.

cd /d %~dp0

echo Creating build directory...
if not exist build mkdir build
cd build

echo.
echo ============================================
echo Starting build process...
echo ============================================
echo.

"%MSYS2_PATH%\msys2_shell.cmd" -mingw64 -defterm -here -no-start -c "
    echo Installing required packages...
    pacman -S --needed --noconfirm mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-make mingw-w64-x86_64-openmp
    
    echo.
    echo Configuring CMake...
    cmake -G 'MinGW Makefiles' -DCMAKE_BUILD_TYPE=Release ..
    
    echo.
    echo Compiling...
    mingw32-make -j%NUMBER_OF_PROCESSORS%
    
    echo.
    echo ============================================
    echo Running tests...
    echo ============================================
    echo.
    test_quantum_systems
    
    echo.
    echo ============================================
    echo Build complete!
    echo ============================================
    pause
"

echo.
echo Build script finished.
pause
