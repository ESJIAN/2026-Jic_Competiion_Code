#!/bin/bash

# Check if requirements.txt exists
if [ ! -f "/app/jic_competiion/requirements.txt" ]; then
    echo "requirements.txt not found in /app/jic_competiion/"
    exit 1
fi

# Create a virtual environment
echo "Creating virtual environment..."
python3 -m venv /app/jic_competiion/venv

# Activate the virtual environment
echo "Activating virtual environment..."
source /app/jic_competiion/venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies from requirements.txt
echo "Installing dependencies..."
pip install -r /app/jic_competiion/requirements.txt

echo "Environment initialization complete."