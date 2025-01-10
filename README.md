# CTS Shipping Calculator

A comprehensive shipping price calculator implementing CTS Group's pricing rules, including volume weight, loading meter weight, and stackable/non-stackable shipment calculations.

## Features

### Weight Calculations
- **Volume Weight (Stackable)**: 
  - Formula: `Length × Width × Height × 330 × number_of_collo` (dimensions in meters)
  - Example: 120cm × 80cm × 100cm = 1.2m × 0.8m × 1.0m × 330 = 316.8 kg

- **Loading Meter Weight (Non-stackable)**:
  - Formula: `((Width × Length)/2.4) × number_of_collo × 1750` (dimensions in meters)
  - Example: 120cm × 80cm = ((1.2m × 0.8m)/2.4) × 1750 = 700 kg

### Dimension Rules
- **Maximum Dimensions**:
  - Length: 240 cm
  - Width: 120 cm
  - Height: 220 cm (>120 cm forces non-stackable calculation)
- **Maximum Weight**: 1000 kg per pallet

### Service Levels
- Prio (1BD)
- Road (2-3 BD)
- Eco (4-5 BD)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd shipping_calculator
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Place your pricing Excel file:
```bash
mkdir -p data
cp "CTS flat buy 2024 1.xlsx" data/
```

## Usage

### Streamlit Interface

```bash
streamlit run streamlit_app.py
```
Access the web interface at http://localhost:8501

### FastAPI Backend

```bash
uvicorn main:app --reload
```
Access the API at http://localhost:8000

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Examples

### Calculate Price
```python
import requests

response = requests.post(
    "http://localhost:8000/calculate-price",
    json={
        "country": "DE",
        "zipcode": "40123",
        "num_collo": 1,
        "length": 120,
        "width": 80,
        "height": 100,
        "actual_weight": 75,
        "service_level": "Prio (1BD)"
    }
)
print(response.json())
```

### Get Zone Information
```python
response = requests.get("http://localhost:8000/zones/DE/40123")
print(response.json())
```

### Get Available Service Levels
```python
response = requests.get("http://localhost:8000/service-levels")
print(response.json())
```

## Project Structure
```
shipping_calculator/
│
├── app/
│   ├── __init__.py
│   ├── database.py      # SQLite database operations
│   ├── models.py        # Pydantic data models
│   ├── calculator.py    # Price calculation logic
│   └── data_loader.py   # Excel data loading
│
├── data/
│   └── CTS flat buy 2024 1.xlsx  # Pricing data
│
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py
│   └── test_api.py
│
├── main.py             # FastAPI application
├── streamlit_app.py    # Streamlit interface
├── requirements.txt
└── README.md
```

## Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app tests/
```

## Development

### Code Format
```bash
black .
```

### Linting
```bash
flake8
```

### Type Checking
```bash
mypy .
```

## Excel File Structure

The calculator expects an Excel file with the following sheets:

1. **pricelist**:
   - Weight: Weight range (e.g., "0-50", "51-100")
   - Zone: Zone identifier
   - Rate: Price rate
   - Service level: Service level name
   - Country: Country code
   - Type: Shipment type

2. **zones**:
   - Zone: Zone identifier
   - Value: Zip code prefix
   - Country: Country code

## Error Handling

The calculator handles various scenarios:
- Invalid dimensions
- Unknown zip code prefixes
- Unsupported service levels
- Weight range violations
- Missing price entries