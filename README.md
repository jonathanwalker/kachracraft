# KachraCraft 🗑️ - AI-Powered 3D Model Generator

KachraCraft is an innovative web application that harnesses the power of AI to generate 3D models, ready for 3D printing. Featuring a Vue.js frontend for user interaction and visualization, alongside a Flask backend that integrates AWS Bedrock and OpenSCAD, KachraCraft delivers a seamless 3D modeling experience.

---

## Features

- 🤖 **AI-Powered 3D Modeling**: Uses AWS Bedrock for intelligent model generation.
- 🎨 **Real-Time 3D Visualization**: Interactive previews powered by Three.js.
- 💬 **Chat-Based Interface**: Generate models through conversational commands.
- 🔄 **Regeneration & History**: Navigate and refine your model generation history.
- ⚡ **3D Print Optimization**: Automated checks to ensure print readiness.
- 💾 **Direct STL Downloads**: Save your models effortlessly.

## Tech Stack

### Frontend
- **Vue.js 3** with Composition API for a modern UI.
- **Three.js** for immersive 3D visualization.
- **Axios** for seamless API communication.

### Backend
- **Flask** with Python 3.9 for robust API services.
- **AWS Bedrock** for AI-driven model generation.
- **SolidPython** for dynamic 3D modeling.
- **OpenSCAD** for STL conversion and validation.

## Prerequisites

To run KachraCraft, ensure you have the following:

- **Python** 3.9+
- **Node.js** 18+
- **OpenSCAD** installed
- An **AWS account** with Bedrock access
- **AWS SSO** configured with necessary permissions

## Quick Start with Docker

Simplify your setup with Docker:

1. Build and run the container:
   ```bash
   docker build -t kachracraft .
   docker run -p 5000:5000 \
     -v ~/.aws:/root/.aws:ro \
     -e AWS_PROFILE=your-profile-name \
     kachracraft
   ```

2. Open your browser and visit `http://localhost:5000`.

## Development Setup

Follow these steps to run the project locally:

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/kachracraft.git
cd kachracraft
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

### 4. Run Locally

#### Start the Backend Server
```bash
cd backend
python app.py
```

#### Start the Frontend Development Server
```bash
cd frontend
npm run dev
```

#### Access the App
Visit `http://localhost:5173` in your browser.

## Project Structure

```
kachracraft/
├── backend/
│   ├── app.py           # Flask application
│   ├── requirements.txt # Python dependencies
│   └── static/          # Generated STL files
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   └── components/
│   ├── package.json
│   └── vite.config.js
└── Dockerfile          # Multi-stage build
```

## Model Generation Constraints

To ensure 3D print compatibility, the following constraints apply:

- **Maximum Dimensions**: 270mm x 200mm x 200mm.
- **Connectivity**: All parts must be connected (no floating components).
- **Flat Surface**: At least one flat surface for bed adhesion.
- **Segment Resolution**: Minimum of 50 segments for curved surfaces.
- **STL Handling**: Automatic generation and cleanup of STL files.

## Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository.
2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add your feature description"
   ```
4. Push to your branch:
   ```bash
   git push origin feature/your-feature-name
   ```
5. Open a Pull Request.

## Acknowledgments

- **Anthropic's Claude**: For AI-driven insights and guidance.
- **Three.js Community**: For exceptional 3D visualization tools.
- **OpenSCAD**: For robust STL generation capabilities.
