#!/bin/bash

# Start the Python backend
cd /app/backend
python app.py &

# Start the Vue.js frontend
cd /app/frontend
npm run preview &

# Keep the container running
wait
