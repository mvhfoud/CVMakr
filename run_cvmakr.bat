@echo off
:: Set environment variables
set "DRIVE_FOLDER_ID=1j0McbhmRarOzZkZYKEj9igGdh-SgOWGF"
set "DRIVE_FOLDER_NAME=Resumes_CDI"
set "SHEET_ID=1UovwuNHj9EyPyLcG1SZi-0u3xB3jZagE45OyaYun7g0"
set "CLIENT_SECRETS_FILE=client_secret_236671734134-vrce2q6p4895haqvupssujhff5cmeq1l.apps.googleusercontent.com.json"

:: Run Streamlit app
streamlit run main_cloud.py

pause
