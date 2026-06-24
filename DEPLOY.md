# Deployment Guide: Minelytics Fleet Management System

## Overview
This project includes a Flask backend API and Vue.js frontend for a fleet management system called Minelytics. This guide covers deployment options for both local development and production environments.

## Prerequisites
- GitHub account (for source code and frontend hosting)
- Render account (for backend deployment)
- Flask knowledge (optional)

## Deployment Options

### Option 1: Local Development (Quick Setup)
1. **Clone or extract the repository**
```bash
cd your-folder
cp backend/app.py backend/requirements.txt frontend/ /your/project/location/
```

2. **Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate    # Windows
```

3. **Install dependencies**
```bash
pip install -r backend/requirements.txt
```

4. **Initialize SQLite database**
```bash
# Navigate to the backend directory
cd backend
# Run the initialization script (if you have one)
python -c "import sqlite3; from backend.app import init_sqlite; init_sqlite()"
```

5. **Run the application**
```bash
# Navigate to the backend directory
cd backend
# Start the Flask application
flask run --port 5000
```

**Access:**
- Frontend: `http://localhost:3000` (or whatever port your static files are served from)
- API: `http://localhost:5000/api/dashboard/metrics`

### Option 2: Production Deployment (Recommended for Portfolios)

#### 2.1 Create GitHub Repository
1. Go to [GitHub](https://github.com) and create a new repository
2. Clone it locally
3. Push all files from this project

#### 2.2 Prepare Deployment Files
The project already includes the necessary files:

- **`.gitignore`**: Ignores Python cache, environment files, and database files
- **`backend/Procfile`**: Defines the web process for Render
- **`backend/render.yaml`**: Render configuration for deploying to production

#### 2.3 Deploy with Render
1. Go to [Render](https://render.com) and sign in
2. Click "New +" → "Web Service"
3. Configure as follows:
   - **Name**: `minelytics-api`
   - **GitHub Repository**: Select your repository
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: `backend`
   - **Environment**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120`
   - **Health Check**: `/api/dashboard/metrics`
   - **Environment Variables**: 
     - `USE_SQLITE=true`
     - `PYTHON_VERSION=3.11.0`

#### 2.4 Deploy Static Frontend (GitHub Pages)
1. In your GitHub repository, navigate to "Settings" → "Pages"
2. Under "Source", select "GitHub Actions"
3. Commit a simple workflow file `.github/workflows/deploy.yml`:
```yaml
name: Deploy Pages

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
      - name: Install dependencies
        run: |
          cd frontend
          npm install
      - name: Build frontend
        run: |
          cd frontend
          npm run build
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./frontend/dist
```

## Features

### 1. Dashboard
Shows fleet metrics in real-time:
- Total fleet units
- Operating, Idle, and Breakdown units
- Physical Availability (PA) and Use of Availability (UA) percentages

### 2. Fleet Management
Allows administrators to:
- Add new fleet units
- Update unit status (Operating, Idle, Breakdown)
- Delete units

### 3. History Log
Tracks the history of fleet unit status changes:
- Shows the machine code, model, and status
- Displays start and end times
- Calculates duration of each status change

### 4. Login
Provides secure access to the system:
- Validates username and password
- Uses role-based access control (RBAC)
- Redirects to the dashboard after successful login

## API Endpoints

### `/api/login` (POST)
Authenticates users and generates a token

### `/api/dashboard/metrics` (GET)
Returns current fleet metrics

### `/api/fleet` (GET, POST)
Manages fleet units
- GET: Returns all fleet units
- POST: Adds a new fleet unit

### `/api/fleet/<id_alat>/status` (PUT)
Updates the status of a specific fleet unit

### `/api/fleet/<id_alat>` (DELETE)
Deletes a fleet unit

### `/api/history` (GET)
Returns the history of fleet unit status changes

## Notes

### SQLite vs MySQL
The application now uses SQLite by default for simplicity. This means:
- The database is stored locally with the application
- Data is easier to back up and restore
- No separate database server is required

### Authentication
Authentication is simulated using a local SQLite database. In a production environment, consider implementing:
- HTTPS for secure communication
- Rate limiting to prevent brute force attacks
- Login attempts tracking and account lockout

### Development vs Production
When deploying to production:
- Ensure environment variables are properly set
- Use a CDN for static assets
- Implement proper error handling and logging
- Monitor API usage and set up alerts

## License
This project is licensed under the MIT License - see the LICENSE file for more information.

## Contributing
Pull requests are welcome. Please ensure your changes include appropriate tests and documentation.

## Acknowledgements
This project was built using:
- Flask (Python web framework)
- Vue.js (JavaScript framework)
- Tailwind CSS (utility-first CSS framework)
- SQLite (local database)
- Chart.js (data visualization)

For more information, please refer to the project's documentation files.