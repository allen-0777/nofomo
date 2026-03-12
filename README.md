# NoFOMO - Stock Analysis & Portfolio Manager

## Project Structure

- **src/**: Backend (Python/Flask)
  - `api.py`: Main API entry point
  - `portfolio.py`: Portfolio logic & calculations
  - `market_data.py`: Stock price fetching & caching
  - `analyzer.py`: Technical analysis core
  - `utils.py`: File I/O utilities
- **ui/**: Frontend (React + Vite + TypeScript)
- **data/**: Data storage (JSON files)

## Setup & Running

### Backend

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the API:
   ```bash
   python src/api.py
   ```
   Server will run at http://localhost:5000

### Frontend

1. Navigate to ui directory:
   ```bash
   cd ui
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run development server:
   ```bash
   npm run dev
   ```
   Frontend will run at http://localhost:5173

## Features

- **Dashboard**: Real-time portfolio summary.
- **Analysis**: Technical indicators (RSI, MACD, Bollinger Bands).
- **Trade Log**: Record your buy/sell actions.
- **Risk Assessment**: Analyze portfolio concentration and win rate.

## Note

The `ui_backup/` folder contains the previous frontend files.
