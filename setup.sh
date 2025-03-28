#!/bin/bash

set -e  # Stop on error

echo "Setting up virtual environment..."
python3 -m venv ./api/venv
source ./api/venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r ./api/requirements.txt

echo "Installing Node dependencies..."
npm install

echo "Building React frontend..."
npm run build

echo "Copying build files to Flask..."
# Adjust for build or dist based on your React setup (Vite = dist, CRA = build)
BUILD_DIR="build"
STATIC_DIR="./api"
TEMPLATES_DIR="./api/templates"

mkdir -p $STATIC_DIR $TEMPLATES_DIR
cp -r $BUILD_DIR/* $STATIC_DIR/
cp $BUILD_DIR/index.html $TEMPLATES_DIR/

echo "Setting up PostgreSQL tables..."
python3 ./api/server.py  # Ensure this runs `create_tables()` safely

echo "Starting Flask server with Gunicorn..."
gunicorn server:app --bind 0.0.0.0:5000 --workers 4
