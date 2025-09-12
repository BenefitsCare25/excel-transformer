@echo off
echo Starting Excel Template Transformer...
echo.

echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo Starting Flask backend server...
start "Backend Server" cmd /k "cd backend && python app.py"

echo.
echo Installing Node.js dependencies...
cd frontend
call npm install

echo.
echo Starting React frontend server...
start "Frontend Server" cmd /k "npm start"

echo.
echo Both servers are starting...
echo Backend: http://localhost:5000
echo Frontend: http://localhost:3000
echo.
pause