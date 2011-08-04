rd /s /q build 2>nul
call d:\Python31\Scripts\cxfreeze.bat encx264.py --target-dir build
md build\pyd
move build\*.pyd build\pyd
rd /s /q tmp
md tmp
copy encx264.py tmp
cd tmp
echo. > imports.py
for %%f in (..\impls\*.py) do copy /b imports.py + "%%f" imports.py
call d:\Python31\Scripts\cxfreeze.bat encx264.py --target-dir build --include-modules imports
copy /y build\encx264.exe ..\build
cd ..
rd /s /q tmp
md build\impls
copy impls build\impls
copy encx264_targets.py.sample build
del build\impls\*.pyc
rd /s /q build\impls\__pycache__ 2> nul
pause