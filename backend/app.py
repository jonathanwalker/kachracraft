from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
import os
import boto3
import time
import re
import subprocess
import sys
import tempfile
import shutil
import uuid
import atexit
from typing import Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Create formatter for HTTP requests
class RequestFormatter(logging.Formatter):
    def format(self, record):
        record.url = request.url if request else "No request"
        record.remote_addr = request.remote_addr if request else "No remote addr"
        return super().format(record)

# Add HTTP request handler
handler = logging.StreamHandler()
handler.setFormatter(RequestFormatter(
    '%(asctime)s - %(levelname)s - %(remote_addr)s - %(url)s - %(message)s'
))
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addHandler(handler)

app = Flask(__name__)
CORS(app)

# Configuration
STATIC_DIR = os.path.join(os.getcwd(), 'static')
TEMP_DIR = os.path.join(os.getcwd(), 'temp_files')

# Ensure directories exist
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

@dataclass
class ModelConfig:
    region: str = 'us-west-2'
    model_id: str = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
    max_tokens: int = 2000
    temperature: float = 1.0
    top_p: float = 0.999

class ModelPrompt:
    BASE_REQUIREMENTS = """
You are a Python code generator for 3D modeling using 'solidpython'. Your task is to output executable Python code for 3D model creation. Follow these requirements:

1. **Imports**:
   - Import `*` from `solid`.
   - Import `*` from `solid.utils`.
   - Import standard Python modules `subprocess` and `os`.
   - Import other common modules if needed: `random`, `math` (for cos, sin, radians).

2. **Code Requirements**:
   - The generated code must define a variable `model` containing the 3D object.
   - Use proper syntax for importing functions like `cube`.
   - Use Python syntax ONLY - do not include OpenSCAD syntax like '$fn'.
   - For setting the number of segments in spheres/cylinders, use the segments parameter:
     - Example: sphere(r=10, segments=50)
     - Example: cylinder(r=5, h=10, segments=50)
   - Save the SCAD file using `scad_render` and convert it to an STL file using OpenSCAD via `subprocess`.
   - For transformations, always use function wrapping syntax:
     - CORRECT: translate([x, y, z])(object)
     - WRONG: object.translate([x,y,z])
     - CORRECT: rotate([x, y, z])(object)
     - WRONG: object.rotate([x,y,z])
     - CORRECT: scale([x, y, z])(object)
     - WRONG: object.scale([x,y,z])
   - For combining objects, use:
     - union()([obj1, obj2])
     - difference()([obj1, obj2])
     - intersection()([obj1, obj2])

3. **Output Specifications**:
   - The code should output a SCAD file (`model.scad`) and an STL file (`model.stl`).
   - Only generate one STL file.
   - After generating the STL file, delete the SCAD file using `os.remove`.

4. **Code Format**:
   - Only output Python code.
   - Avoid any invalid syntax, additional content, or markdown formatting.
   - Ensure the code is directly executable without errors.
   - DO NOT include OpenSCAD syntax (like $fn) - use Python parameters instead.

5. **Modeling Limits**:
   - No greater than 270mm x 200mm x 200mm.
   - Make sure all parts are touching each other.
   - Make sure spheres/cylinders have 50 segments.
   - No floating parts.
   - At least one side has to be flat on the bed.
   - All transformations must use function wrapping, not method chaining
   - Properly combine objects using union(), difference(), or intersection()

Example correct code structure:
```python
from solid import *
from solid.utils import *
import subprocess
import os

# Create your model here
model = sphere(r=10, segments=50)  # Note: using segments parameter, not $fn

# Save SCAD file
scad_file = 'model.scad'
stl_file = 'model.stl'

with open(scad_file, 'w') as f:
    f.write(scad_render(model))

# Convert to STL
subprocess.run(['openscad', '-o', stl_file, scad_file], check=True)

# Cleanup SCAD file
os.remove(scad_file)
```
"""

    @classmethod
    def generate_prompt(cls, task: str) -> str:
        return f"{cls.BASE_REQUIREMENTS}\n\n**Your Task**:\n{task}"

class ModelGenerator:
    def __init__(self, config: ModelConfig):
        self.config = config
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=config.region)
    
    def generate_response(self, prompt: str, conversation: list) -> Tuple[str, str]:
        conversation = [
            {
                "role": "user",
                "content": [
                    {"text": f"""
First, create the 3D model code according to the requirements. 
Then, provide a brief, friendly description of what you created in 1-2 sentences.
Separate your response into two parts:
CODE:
[your code here]
DESCRIPTION:
[your description here]
Task: {prompt.strip()}
                    """}
                ],
            }
        ]

        try:
            response = self.bedrock_client.converse(
                modelId=self.config.model_id,
                messages=conversation,  # full conversation
                inferenceConfig={
                    "maxTokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                    "topP": self.config.top_p,
                },
            )
            full_response = response["output"]["message"]["content"][0]["text"].strip()
            # print full_response
            print(full_response)
            
            # Split response into code and description
            code_match = re.search(r"CODE:(.*?)DESCRIPTION:", full_response, re.DOTALL)
            desc_match = re.search(r"DESCRIPTION:(.*?)$", full_response, re.DOTALL)
            
            code = code_match.group(1).strip() if code_match else full_response
            description = desc_match.group(1).strip() if desc_match else ""
            
            return code, description
        except Exception as e:
            raise RuntimeError(f"Model invocation failed: {e}")

class FileManager:
    @staticmethod
    @contextmanager
    def temporary_directory():
        """Create a temporary directory that's automatically cleaned up."""
        temp_dir = tempfile.mkdtemp(dir=TEMP_DIR)
        try:
            yield temp_dir
        finally:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Error cleaning up temporary directory {temp_dir}: {e}")

    @staticmethod
    def generate_unique_filename(prefix: str = "", suffix: str = "") -> str:
        """Generate a unique filename using UUID."""
        return f"{prefix}{uuid.uuid4().hex}{suffix}"

    @staticmethod
    def cleanup_old_files(directory: str, max_age_hours: int = 24):
        """Clean up files older than specified hours."""
        current_time = time.time()
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > max_age_hours * 3600:  # Convert hours to seconds
                    try:
                        os.remove(filepath)
                    except Exception as e:
                        print(f"Error removing old file {filepath}: {e}")

class CodeProcessor:
    @staticmethod
    def extract_code(response_text: str) -> Optional[str]:
        patterns = [
            r"```python(.*?)```",
            r"```(.*?)```"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return response_text.strip()

    @staticmethod
    def generate_stl(code_str: str) -> Tuple[bool, str, Optional[str]]:
        """Generate STL file from Python code and return status, error message, and file path."""
        with FileManager.temporary_directory() as temp_dir:
            try:
                # Generate unique filenames
                base_filename = FileManager.generate_unique_filename()
                py_file = os.path.join(temp_dir, f"{base_filename}.py")
                scad_file = os.path.join(temp_dir, f"{base_filename}.scad")
                stl_file = os.path.join(temp_dir, f"{base_filename}.stl")
                
                # Update file paths in code
                modified_code = code_str.replace("'model.scad'", f"'{scad_file}'")
                modified_code = modified_code.replace('"model.scad"', f'"{scad_file}"')
                modified_code = modified_code.replace("'model.stl'", f"'{stl_file}'")
                modified_code = modified_code.replace('"model.stl"', f'"{stl_file}"')

                # Write and execute the Python script
                with open(py_file, 'w') as f:
                    f.write(modified_code)

                subprocess.run([sys.executable, py_file], check=True, cwd=temp_dir)

                if not os.path.exists(stl_file):
                    return False, "STL file was not created", None

                # Move successful STL to static directory
                final_stl_name = FileManager.generate_unique_filename(suffix=".stl")
                final_stl_path = os.path.join(STATIC_DIR, final_stl_name)
                shutil.move(stl_file, final_stl_path)

                return True, "", final_stl_name

            except subprocess.CalledProcessError as e:
                return False, f"Error executing Python script: {str(e)}", None
            except Exception as e:
                return False, f"Error during STL generation: {str(e)}", None

@app.route('/generate-model', methods=['POST'])
def generate_model():
    data = request.json
    messages = data.get('messages', [])

    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    # Construct the conversation in the format the model expects:
    conversation = []
    for msg in messages:
        role = "user" if msg.get("user", False) else "assistant"
        conversation.append({
            "role": role,
            "content": [{"text": msg.get("text", "")}]
        })

    # Now call the model with the full conversation history
    try:
        config = ModelConfig()
        generator = ModelGenerator(config)
        processor = CodeProcessor()

        # Instead of generate_prompt(prompt), you can now pass a prompt derived from the last user message
        # or use all messages for context. The prompt for generation might be the last user's input:
        last_user_message = next((m["text"] for m in reversed(messages) if m["user"]), "")
        code, description = generator.generate_response(ModelPrompt.generate_prompt(last_user_message), conversation=conversation)
        
        processed_code = processor.extract_code(code)
        if not processed_code:
            return jsonify({"error": "No valid code generated"}), 500

        success, error_message, stl_filename = processor.generate_stl(processed_code)
        if not success:
            return jsonify({"error": error_message}), 500

        return jsonify({
            "stl_url": f"/static/{stl_filename}",
            "description": description
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# @app.route('/static/<path:filename>')
# def serve_static(filename):
#     return send_from_directory(STATIC_DIR, filename)

@app.route('/')
def serve_frontend():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    try:
        return send_from_directory('static', path)
    except Exception as e:
        print(f"Error serving {path}: {str(e)}")
        return str(e), 404

def cleanup_temp_files():
    """Cleanup function to be called on application shutdown."""
    FileManager.cleanup_old_files(TEMP_DIR)
    print("Temporary files cleaned up")

# Register cleanup function
atexit.register(cleanup_temp_files)

if __name__ == '__main__':
    # Initial cleanup of old files
    FileManager.cleanup_old_files(TEMP_DIR)
    FileManager.cleanup_old_files(STATIC_DIR, max_age_hours=168)  # 1 week for static files
    
    # Print debug info
    static_dir = os.path.join(os.getcwd(), 'static')
    print(f"Starting server. Static directory: {static_dir}")
    print("Static directory structure:")
    for root, dirs, files in os.walk(static_dir):
        level = root.replace(static_dir, '').count(os.sep)
        indent = ' ' * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print(f"{subindent}{f}")
    
    # Run Flask on all interfaces
    app.run(host='0.0.0.0', debug=True, port=5000)
