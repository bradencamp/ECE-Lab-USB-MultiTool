cd ..
@echo off
for %%f in ("*.py") do (
	doc\pydoc.py -w %%~nf
	move %%~nf.html doc\%%~nf.html
)
pause
