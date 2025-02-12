FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create data directory
RUN mkdir -p data

# Create Streamlit config directory and file
RUN mkdir -p .streamlit && \
    echo '[server]\n\
    enableCORS = false\n\
    enableXsrfProtection = false\n\
    ' > .streamlit/config.toml

# Expose ports for FastAPI and Streamlit
EXPOSE 8000 8501

# Create a script to run both services
RUN echo '#!/bin/bash\n\
uvicorn main:app --host 0.0.0.0 --port 8000 & \n\
streamlit run --server.address 0.0.0.0 --server.port 8501 app.py\n\
wait' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
