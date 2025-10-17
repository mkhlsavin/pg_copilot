@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\user\pg_copilot\rag_cpgql"
call C:\Users\user\anaconda3\Scripts\activate.bat llama.cpp
python demo_real_rag.py > results\demo_output.txt 2>&1
