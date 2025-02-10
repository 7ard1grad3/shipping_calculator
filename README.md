# Shipping Calculator

## Project Overview
The Shipping Calculator is a web-based application built with Streamlit and FastAPI that helps users calculate shipping costs based on package dimensions, weight, and destination. The application provides an intuitive interface for logistics professionals and businesses to get accurate shipping cost estimates.

## Features
- Calculate shipping costs based on:
  - Package dimensions (length, width, height)
  - Number of packages (collo)
  - Actual weight
  - Destination country and zipcode
  - Service level
- Supports multiple weight calculation methods:
  - Volume weight (stackable items)
  - Loading meter weight (non-stackable items)
  - Actual weight
- Automatic weight type determination based on package height
- User authentication system
- Interactive data visualization with Plotly
- Configuration management for shipping parameters
- Database storage for pricing data and configurations

## Technical Stack
- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Database**: SQLite
- **Data Processing**: Pandas
- **Visualization**: Plotly
- **Data Format Support**: Excel (via openpyxl)

## Project Structure
```
shipping_calculator/
├── app/                    # Main application package
│   ├── calculator.py       # Core shipping calculation logic
│   └── database.py        # Database operations
├── data/                  # Data storage
├── tests/                 # Test files
├── app.py                 # Main Streamlit application
├── configurations.py      # Configuration settings
├── main.py               # FastAPI server
└── requirements.txt       # Project dependencies
```

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy .env.example to .env and configure your environment variables

## Usage

1. Start the application:
   ```bash
   streamlit run app.py
   ```
2. Access the web interface through your browser (typically at `http://localhost:8501`)
3. Log in to the system
4. Enter package details:
   - Number of packages
   - Dimensions (length, width, height)
   - Actual weight
   - Destination country and zipcode
   - Service level
5. Get instant shipping cost calculations

## Configuration

The application uses several configurable parameters:
- `DEFAULT_WEIGHT_TYPE`: Default method for weight calculation
- `NNR_PREMIUM_FEES`: Premium fees for NNR service
- `UNILOG_PREMIUM_FEES`: Premium fees for Unilog service
- `FUEL_SURCHARGE`: Current fuel surcharge percentage

These can be modified through the application's configuration interface or directly in the database.

## Core Components

### ShippingCalculator
The main calculation engine that:
- Calculates volume weight for stackable items
- Calculates loading meter weight for non-stackable items
- Determines the chargeable weight based on package characteristics
- Computes final shipping prices based on destination and service level

### PricingData
Manages the pricing data and configurations:
- Loads pricing data from Excel files
- Stores and retrieves data from SQLite database
- Handles configuration management

## Security
- User authentication required for access
- Environment variables for sensitive configurations
- Input validation for all calculations

This project provides a robust solution for shipping cost calculations, suitable for logistics companies and businesses that need accurate shipping cost estimates. The modular design allows for easy maintenance and future extensions of functionality.