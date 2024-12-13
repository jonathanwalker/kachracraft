<template>
    <div class="model-generator">
        <div class="main-content">
            <!-- Chat Section -->
            <div class="chat-section">
                <h1>KachraCraft</h1>
                <div class="chat-box">
                    <div v-for="(message, index) in messages" :key="index"
                        :class="['message', message.user ? 'user' : 'ai']">
                        <p v-html="message.text"></p>
                    </div>
                </div>

                <div class="input-container">
                    <textarea v-model="input" placeholder="Type your prompt for a 3D model..." :disabled="isLoading"
                        rows="3" @keydown.enter="handleEnter"></textarea>

                    <button type="submit" :disabled="isLoading" class="send-button" v-show="input.trim().length > 0"
                        @click="sendMessage">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                            stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="22" y1="2" x2="11" y2="13"></line>
                            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                        </svg>
                    </button>
                </div>
            </div>

            <!-- STL Viewer Section -->
            <div class="stl-viewer">
                <div class="model-navigation">
                    <button @click="navigatePrevious" :disabled="!canNavigatePrevious" class="nav-button">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                            stroke-linecap="round" stroke-linejoin="round">
                            <line x1="19" y1="12" x2="5" y2="12"></line>
                            <polyline points="12 19 5 12 12 5"></polyline>
                        </svg>
                        Previous
                    </button>

                    <button @click="regenerateModel" :disabled="!canRegenerate" class="regenerate-button">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                            stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="1 4 1 10 7 10"></polyline>
                            <path d="M3.51 15a9 9 0 102.13-9.36L1 10"></path>
                        </svg>
                        Regenerate
                    </button>

                    <button @click="navigateNext" :disabled="!canNavigateNext" class="nav-button">
                        Next
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                            stroke-linecap="round" stroke-linejoin="round">
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                            <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                    </button>
                </div>

                <div id="stl-container">
                    <div v-if="isLoading" class="loading-overlay">
                        <div class="loading-spinner"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import {
    ref,
    shallowRef,
    onMounted,
    onBeforeUnmount,
    getCurrentInstance,
} from "vue";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls";
import axios from "axios";

export default {
    name: "ModelGenerator",
    data() {
        return {
            input: "",
            messages: [
                {
                    text: `Welcome! Discover AI-generated models optimized for 3D printing. Use the mouse to interact with the 3D model:
            - Rotate: Left-click and drag
            - Zoom: Scroll wheel or pinch
            - Pan: Ctrl + Left-click and drag`,
                    user: false,
                    isInitial: true
                },
            ],

            stlFile: null,
            isLoading: false,
            defaultModelUrl: "https://static-assets.securityrunners.io/kachra.stl",
            modelHistory: [],
            currentModelIndex: -1,
            lastPrompt: "",
        };
    },
    computed: {
        canNavigatePrevious() {
            return this.currentModelIndex > 0;
        },
        canNavigateNext() {
            return this.currentModelIndex < this.modelHistory.length - 1;
        },
        canRegenerate() {
            return this.lastPrompt !== "" && !this.isLoading;
        },
    },
    setup() {
        const scene = shallowRef(null);
        const camera = shallowRef(null);
        const renderer = shallowRef(null);
        let controls = null;

        const modelGroup = new THREE.Group();
        const isUserInteracting = ref(false);

        const initScene = () => {
            scene.value = new THREE.Scene();
            scene.value.background = new THREE.Color(0x121212);

            scene.value.add(modelGroup);

            const container = document.getElementById("stl-container");
            const width = container.clientWidth;
            const height = container.clientHeight;

            camera.value = new THREE.PerspectiveCamera(45, width / height, 1, 1000);
            camera.value.position.set(0, 0, 100);

            renderer.value = new THREE.WebGLRenderer({ antialias: true });
            renderer.value.setSize(width, height);
            container.appendChild(renderer.value.domElement);
            renderer.value.domElement.style.width = "100%";
            renderer.value.domElement.style.height = "100%";

            controls = new OrbitControls(camera.value, renderer.value.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;

            controls.addEventListener("start", () => {
                isUserInteracting.value = true;
            });

            controls.addEventListener("end", () => {
                isUserInteracting.value = false;
            });

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
            scene.value.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
            directionalLight.position.set(0, 1, 1);
            scene.value.add(directionalLight);

            window.addEventListener("resize", onWindowResize);
        };

        const onWindowResize = () => {
            const container = document.getElementById("stl-container");
            const width = container.clientWidth;
            const height = container.clientHeight;

            camera.value.aspect = width / height;
            camera.value.updateProjectionMatrix();
            renderer.value.setSize(width, height);
        };

        const loadSTL = (stlUrl) => {
            if (!scene.value || !camera.value || !renderer.value) return;
            const loader = new STLLoader();
            loader.load(
                stlUrl,
                (geometry) => {
                    while (modelGroup.children.length > 0) {
                        modelGroup.remove(modelGroup.children[0]);
                    }

                    const material = new THREE.MeshPhongMaterial({ color: 0x1e88e5 });
                    const mesh = new THREE.Mesh(geometry, material);
                    modelGroup.add(mesh);

                    geometry.center();
                    geometry.computeBoundingBox();

                    const box = new THREE.Box3().setFromObject(mesh);
                    const size = box.getSize(new THREE.Vector3()).length();
                    const center = box.getCenter(new THREE.Vector3());

                    controls.target.copy(center);
                    camera.value.near = size / 100;
                    camera.value.far = size * 100;
                    camera.value.updateProjectionMatrix();

                    camera.value.position.copy(center);
                    camera.value.position.z += size * 2;
                    camera.value.lookAt(center);
                    controls.update();
                },
                undefined,
                (error) => {
                    console.error("Error loading STL:", error);
                }
            );
        };

        const animate = () => {
            requestAnimationFrame(animate);
            if (!isUserInteracting.value) {
                modelGroup.rotation.y += 0.005;
            }
            controls.update();
            renderer.value.render(scene.value, camera.value);
        };

        onMounted(() => {
            initScene();
            animate();
            if (getCurrentInstance().proxy.defaultModelUrl) {
                loadSTL(getCurrentInstance().proxy.defaultModelUrl);
            }
        });

        onBeforeUnmount(() => {
            if (renderer.value) {
                renderer.value.dispose();
            }
            if (controls) {
                controls.dispose();
            }
            window.removeEventListener("resize", onWindowResize);
        });

        return { loadSTL };
    },
    methods: {
        async generateModel(messages) {
            this.isLoading = true;
            try {
                const API_BASE_URL = "http://localhost:5000";
                const response = await axios.post(`${API_BASE_URL}/generate-model`, { messages });

                if (response.data.stl_url) {
                    const modelUrl = API_BASE_URL + response.data.stl_url;
                    this.modelHistory.push({ url: modelUrl, prompt: this.lastPrompt });
                    this.currentModelIndex = this.modelHistory.length - 1;
                    this.stlFile = modelUrl;

                    let messageText = response.data.description
                        ? `${response.data.description}<br><br>`
                        : "";
                    messageText += `<a href="${modelUrl}" download="generated-model.stl">Download STL File</a>`;

                    this.messages.push({ text: messageText, user: false });
                    this.loadSTL(modelUrl);
                } else if (response.data.error) {
                    throw new Error(response.data.error);
                }
            } catch (error) {
                console.error("Error generating model:", error);
                const errorMessage = error.response?.data?.error || error.message || "Failed to generate model";
                this.messages.push({
                    text: `
            <div class="error-card">
                <div class="error-content">
                    <div class="error-title">Generation Failed</div>
                    <div class="error-details">${errorMessage}</div>
                </div>
            </div>`,
                    user: false,
                });
            } finally {
                this.isLoading = false;
            }
        },
        async sendMessage() {
            if (!this.input.trim()) return;

            this.messages.push({ text: this.input, user: true });
            this.lastPrompt = this.input;
            this.input = "";

            this.$nextTick(() => {
                const chatBox = document.querySelector(".chat-box");
                if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
            });

            // Now simply call generateModel() with the entire message history
            await this.generateModel(this.messages.filter(msg => !msg.isInitial));
        },
        async regenerateModel() {
            if (this.lastPrompt && !this.isLoading) {
                // Use the full messages array, not just the lastPrompt string
                await this.generateModel(this.messages.filter(msg => !msg.isInitial));
            }
        },
        navigatePrevious() {
            if (this.canNavigatePrevious) {
                this.currentModelIndex--;
                const model = this.modelHistory[this.currentModelIndex];
                this.stlFile = model.url;
                this.loadSTL(this.stlFile);
            }
        },
        navigateNext() {
            if (this.canNavigateNext) {
                this.currentModelIndex++;
                const model = this.modelHistory[this.currentModelIndex];
                this.stlFile = model.url;
                this.loadSTL(this.stlFile);
            }
        },
        handleEnter(e) {
            if (e.shiftKey) {
                // Allow default behavior, which inserts a newline
                return;
            }

            // If no shift key, prevent default and send the message
            e.preventDefault();
            this.sendMessage();
        },
    },
    watch: {
        messages: {
            handler() {
                this.$nextTick(() => {
                    const chatBox = document.querySelector(".chat-box");
                    if (chatBox) {
                        chatBox.scrollTop = chatBox.scrollHeight;
                    }
                });
            },
            deep: true,
        },
    },
};
</script>

<style scoped>
:root {
    --color-background: #121212;
    --color-background-soft: #1e1e1e;
    --color-background-mute: #2a2a2a;
    --color-border: #333;
    --color-text: #fafafa;
    --color-primary: #f57c00;
    --color-secondary: #64b5f6;
    --color-heading: #f57c00;
    --font-family: "Roboto", sans-serif;
}

.model-generator {
    display: flex;
    flex-direction: column;
    height: 100%;
    background-color: var(--color-background);
    font-family: var(--font-family);
    overflow: hidden;
}

.main-content {
    display: flex;
    flex: 1;
    height: 100%;
    width: 100%;
}

/* Chat Section */
.chat-section {
    flex: 0 0 30%;
    min-width: 30%;
    max-width: 30%;
    background-color: var(--color-background-soft);
    border-right: 1px solid var(--color-border);
    display: flex;
    flex-direction: column;
    padding: 20px;
    color: var(--color-text);
    box-sizing: border-box;
}

.chat-section h1 {
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--color-heading);
    text-align: center;
    margin-bottom: 20px;
    letter-spacing: 1px;
    text-transform: uppercase;
    background: linear-gradient(to right,
            rgba(255, 87, 34, 0.2),
            rgba(255, 87, 34, 0));
    padding: 10px;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3), 0 4px 8px rgba(0, 0, 0, 0.2);
}

.chat-box {
    flex: 1;
    overflow-y: auto;
    margin-bottom: 20px;
    display: flex;
    flex-direction: column;
    padding-right: 5px;
    scrollbar-width: thin;
    scrollbar-color: var(--color-border) transparent;
}

.chat-box::-webkit-scrollbar {
    width: 6px;
}

.chat-box::-webkit-scrollbar-track {
    background: transparent;
}

.chat-box::-webkit-scrollbar-thumb {
    background: var(--color-border);
    border-radius: 3px;
}

.message {
    max-width: 80%;
    margin: 10px 0;
    padding: 12px 16px;
    border-radius: 18px;
    word-wrap: break-word;
    transition: all 0.3s ease-in-out;
    display: inline-block;
    line-height: 1.4;
    font-size: 0.95rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25);
}

.message p {
    margin: 0;
    font-weight: 500;
    color: #fff;
    white-space: pre-wrap;
}

.message a {
    color: var(--color-primary);
    text-decoration: none;
    font-weight: 600;
}

.message a:hover {
    text-decoration: underline;
}

.user {
    align-self: flex-end;
    background: linear-gradient(135deg, #f57c00 0%, #ef6c00 100%);
    color: #fff;
    border-bottom-right-radius: 0;
}

.ai {
    align-self: flex-start;
    background: linear-gradient(135deg, #3949ab 0%, var(--color-secondary) 100%);
    color: #fff;
    border-bottom-left-radius: 0;
}

/* STL Viewer Section */
.stl-viewer {
    flex: 1;
    padding: 20px;
    display: flex;
    flex-direction: column;
    color: var(--color-text);
    position: relative;
    box-sizing: border-box;
    background-color: var(--color-background);
}

#stl-container {
    flex: 1;
    background-color: var(--color-background-mute);
    position: relative;
    border-radius: 8px;
    overflow: hidden;
}

#stl-container canvas {
    position: absolute;
    top: 0;
    left: 0;
}

.loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(18, 18, 18, 0.8);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1;
    backdrop-filter: blur(4px);
    border-radius: 8px;
}

.loading-spinner {
    border: 4px solid var(--color-border);
    border-top: 4px solid var(--color-primary);
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

/* Navigation */
.model-navigation {
    display: flex;
    gap: 10px;
    justify-content: center;
    margin-bottom: 15px;
}

.nav-button,
.regenerate-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    color: #fff;
    font-size: 0.9rem;
    font-weight: 600;
    padding: 0 12px;
    height: 40px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: transform 0.2s ease, background-color 0.2s ease;
}

.nav-button {
    background: var(--color-secondary);
}

.regenerate-button {
    background: var(--color-primary);
}

.nav-button:hover,
.regenerate-button:hover {
    transform: scale(1.05);
    background: #e64a19;
    /* a slightly darker shade for hover */
}

.nav-button:disabled,
.regenerate-button:disabled {
    background-color: var(--color-border);
    opacity: 0.5;
    cursor: not-allowed;
}

.nav-button svg,
.regenerate-button svg {
    width: 18px;
    height: 18px;
    stroke: currentColor;
}

/* Error message styling */
.error-card {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    background: linear-gradient(to right,
            rgba(30, 30, 30, 0.95),
            rgba(44, 44, 44, 0.95));
    border-left: 4px solid #ff5722;
    border-radius: 8px;
    padding: 16px;
    margin: 8px 0;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

.error-title {
    font-size: 0.9rem;
    font-weight: 600;
    color: #ff5722;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
}

.error-details {
    font-size: 0.85rem;
    color: rgba(255, 255, 255, 0.9);
    line-height: 1.5;
    word-break: break-word;
}

/* Textarea & Send Button */
.input-container {
    position: relative;
    margin-top: 20px;
    width: 100%;
}

textarea {
    width: 100%;
    padding: 15px 50px 15px 15px;
    border: 1px solid var(--color-border);
    border-radius: 15px;
    background-color: var(--color-background-mute);
    color: var(--color-text);
    font-size: 0.95rem;
    resize: none;
    min-height: 80px;
    font-family: inherit;
    box-sizing: border-box;
    transition: border-color 0.3s;
}

textarea::placeholder {
    color: #aaa;
}

textarea:focus {
    border-color: var(--color-primary);
    outline: none;
}

.send-button {
    position: absolute;
    top: 12px;
    right: 12px;
    width: 32px;
    height: 32px;
    padding: 0;
    border: none;
    border-radius: 8px;
    background: var(--color-primary);
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.2s ease, background-color 0.2s ease;
}

.send-button:hover {
    transform: scale(1.1);
    background: #e64a19;
}

.send-button:disabled {
    background-color: #555;
    cursor: not-allowed;
    transform: none;
}

.send-button svg {
    width: 18px;
    height: 18px;
    transform: translateX(-2px);
    /* Adjust the value as needed */
}
</style>
