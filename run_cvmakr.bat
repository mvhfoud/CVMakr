@echo off
:: Set environment variables
set "DRIVE_FOLDER_ID=replace"
set "DRIVE_FOLDER_NAME=replace"
set "SHEET_ID=replace"
set "CLIENT_SECRETS_FILE=replace"

:: Run Streamlit app
streamlit run main_cloud.py

pause
