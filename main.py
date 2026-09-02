import os
import shutil
from typing import Dict, List
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

UPLOAD_DIR = "shared_downloads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Static directory mount for full image & file previews
app.mount("/shared_downloads", StaticFiles(directory=UPLOAD_DIR), name="downloads")

class ConnectionManager:
    def __init__(self):
        self.active_rooms: Dict[str, List[Dict]] = {}

    async def connect(self, websocket: WebSocket, room: str, device_name: str, device_type: str, device_pin: str):
        await websocket.accept()
        if room not in self.active_rooms:
            self.active_rooms[room] = []
        
        device_info = {
            "ws": websocket,
            "name": device_name,
            "type": device_type,
            "pin": device_pin
        }
        self.active_rooms[room].append(device_info)
        await self.broadcast_devices(room)

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.active_rooms:
            self.active_rooms[room] = [d for d in self.active_rooms[room] if d["ws"] != websocket]
            if not self.active_rooms[room]:
                del self.active_rooms[room]

    async def broadcast_devices(self, room: str):
        if room in self.active_rooms:
            device_list = [{
                "name": d["name"],
                "type": d["type"],
                "pin": d["pin"]
            } for d in self.active_rooms[room]]
            
            dead_sockets = []
            for conn in self.active_rooms[room]:
                try:
                    await conn["ws"].send_json({"type": "device_list", "devices": device_list})
                except Exception:
                    dead_sockets.append(conn["ws"])
            
            for ws in dead_sockets:
                self.disconnect(ws, room)

    async def broadcast_file_event(self, room: str, filename: str, sender: str):
        if room in self.active_rooms:
            dead_sockets = []
            for conn in self.active_rooms[room]:
                if conn["name"] != sender:
                    try:
                        await conn["ws"].send_json({
                            "type": "new_file",
                            "filename": filename,
                            "sender": sender
                        })
                    except Exception:
                        dead_sockets.append(conn["ws"])
            
            for ws in dead_sockets:
                self.disconnect(ws, room)

    async def broadcast_text_message(self, room: str, text: str, sender: str):
        if room in self.active_rooms:
            dead_sockets = []
            for conn in self.active_rooms[room]:
                if conn["name"] != sender:
                    try:
                        await conn["ws"].send_json({
                            "type": "new_text",
                            "text": text,
                            "sender": sender
                        })
                    except Exception:
                        dead_sockets.append(conn["ws"])
            
            for ws in dead_sockets:
                self.disconnect(ws, room)

manager = ConnectionManager()

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    room: str = Form(...),
    sender: str = Form(...)
):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    await manager.broadcast_file_event(room, file.filename, sender)
    return {"status": "success"}

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    return FileResponse(path=file_path, filename=filename)

@app.websocket("/ws/{room}/{device_name}/{device_type}/{device_pin}")
async def websocket_endpoint(websocket: WebSocket, room: str, device_name: str, device_type: str, device_pin: str):
    await manager.connect(websocket, room, device_name, device_type, device_pin)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("TEXT_SHARE:"):
                text_content = data[11:]
                await manager.broadcast_text_message(room, text_content, device_name)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        await manager.broadcast_devices(room)
    except Exception:
        manager.disconnect(websocket, room)
        await manager.broadcast_devices(room)

@app.get("/")
async def get_ui():
    return HTMLResponse(html_content)

html_content = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PulseShare • Multi-Color Glass UI</title>
    
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%236366f1'><path d='M13 2L3 14h9l-1 8 10-12h-9l1-8z'/></svg>">

    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Plus Jakarta Sans', 'sans-serif'],
                    }
                }
            }
        }
    </script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">

    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; }

        html.dark body { 
            background: radial-gradient(circle at top left, #1e1b4b 0%, #0f172a 40%, #030712 100%);
            color: #f8fafc; 
        }
        html.dark .glass-card { 
            background: rgba(30, 41, 59, 0.6); 
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1); 
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        html.dark .glass-input { 
            background: rgba(15, 23, 42, 0.7); 
            border: 1px solid rgba(255, 255, 255, 0.15); 
            color: #f8fafc; 
        }

        html.light body { 
            background: linear-gradient(135deg, #e0e7ff 0%, #f3e8ff 50%, #fce7f3 100%);
            color: #0f172a; 
        }
        html.light .glass-card { 
            background: rgba(255, 255, 255, 0.85); 
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.6); 
            box-shadow: 0 15px 35px rgba(99, 102, 241, 0.12);
        }
        html.light .glass-input { 
            background: rgba(255, 255, 255, 0.9); 
            border: 1px solid rgba(203, 213, 225, 0.8); 
            color: #0f172a; 
        }

        .gradient-text {
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .gradient-btn {
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        }
        .gradient-btn:hover {
            background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%);
        }

        @keyframes floatSlow {
            0%, 100% { transform: translateY(0px) scale(1); }
            50% { transform: translateY(-12px) scale(1.08); }
        }
        @keyframes floatFast {
            0%, 100% { transform: translateY(0px) scale(1); }
            50% { transform: translateY(14px) scale(0.92); }
        }
        .animate-ball-1 { animation: floatSlow 6s ease-in-out infinite; }
        .animate-ball-2 { animation: floatFast 8s ease-in-out infinite; }
        .animate-ball-3 { animation: floatSlow 7s ease-in-out infinite reverse; }

        .custom-scrollbar::-webkit-scrollbar {
            width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
            background: rgba(168, 85, 247, 0.4);
            border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: rgba(168, 85, 247, 0.7);
        }
    </style>
</head>
<body class="min-h-screen flex flex-col md:flex-row overflow-y-auto md:overflow-hidden transition-colors duration-500">

<div id="login-modal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xl p-4 overflow-y-auto">
    <div class="glass-card rounded-3xl p-8 max-w-md w-full text-center relative overflow-hidden my-auto">
        <div class="absolute -top-12 -right-12 w-40 h-40 bg-purple-500/30 rounded-full blur-2xl"></div>
        <div class="absolute -bottom-12 -left-12 w-40 h-40 bg-indigo-500/30 rounded-full blur-2xl"></div>
        
        <div class="w-16 h-16 gradient-btn rounded-2xl flex items-center justify-center text-white text-3xl mx-auto mb-4 shadow-xl shadow-indigo-500/30 transform hover:rotate-12 transition">
            <i class="fa-solid fa-bolt"></i>
        </div>
        <h2 class="text-3xl font-black mb-1 gradient-text">PulseShare</h2>
        <p class="text-xs font-semibold text-purple-400 mb-6 tracking-wide">LAN PEER-TO-PEER NETWORK</p>
        
        <div class="space-y-3 relative z-10">
            <input type="text" id="dev-name" placeholder="Device Name (e.g. Neon Phoenix)" class="w-full glass-input rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500">
            <select id="dev-type" class="w-full glass-input rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500">
                <option value="Samsung">Android • Samsung</option>
                <option value="Xiaomi">Android • Xiaomi</option>
                <option value="Windows">Windows • PC</option>
                <option value="iPhone">iOS • iPhone</option>
            </select>
            <input type="text" id="dev-pin" placeholder="PIN Tag (e.g. #99)" class="w-full glass-input rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500">
            <input type="password" id="room-pass" placeholder="Network Group Password" class="w-full glass-input rounded-xl px-4 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500">
        </div>

        <button onclick="joinNetwork()" class="w-full mt-6 gradient-btn text-white font-extrabold py-4 rounded-xl shadow-lg shadow-purple-500/30 hover:scale-[1.02] active:scale-[0.98] transition">
            Connect Device
        </button>
    </div>
</div>

<div id="toast-popup" class="fixed bottom-6 right-6 z-50 glass-card border-l-4 border-purple-500 px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-3 transform translate-y-32 opacity-0 transition-all duration-300">
    <i class="fa-solid fa-circle-check text-purple-400 text-xl" id="toast-icon"></i>
    <span id="toast-msg" class="text-sm font-semibold">Message Notification</span>
</div>

<aside class="w-full md:w-64 glass-card border-b md:border-b-0 md:border-r p-6 flex md:flex-col justify-between items-center z-40 shrink-0">
    <div class="w-full">
        <div class="flex items-center gap-3 mb-6 md:mb-10">
            <div class="w-10 h-10 gradient-btn rounded-xl flex items-center justify-center text-white text-xl shadow-lg shadow-indigo-500/30">
                <i class="fa-solid fa-bolt"></i>
            </div>
            <span class="text-2xl font-black tracking-tight gradient-text">PulseShare</span>
        </div>

        <nav class="flex md:flex-col gap-2 md:gap-3 w-full">
            <button onclick="switchTab('send')" id="nav-send" class="nav-btn active flex items-center justify-center md:justify-start gap-2 md:gap-4 px-3 md:px-4 py-2.5 md:py-3.5 rounded-2xl gradient-btn text-white font-bold text-xs md:text-sm w-full shadow-md shadow-indigo-500/20 transition">
                <i class="fa-solid fa-paper-plane"></i> <span>Send</span>
            </button>
            <button onclick="switchTab('receive')" id="nav-receive" class="nav-btn flex items-center justify-center md:justify-start gap-2 md:gap-4 px-3 md:px-4 py-2.5 md:py-3.5 rounded-2xl opacity-70 hover:opacity-100 hover:bg-purple-500/10 font-bold text-xs md:text-sm w-full transition">
                <i class="fa-solid fa-download"></i> <span>Received</span>
            </button>
            <button onclick="switchTab('settings')" id="nav-settings" class="nav-btn flex items-center justify-center md:justify-start gap-2 md:gap-4 px-3 md:px-4 py-2.5 md:py-3.5 rounded-2xl opacity-70 hover:opacity-100 hover:bg-purple-500/10 font-bold text-xs md:text-sm w-full transition">
                <i class="fa-solid fa-sliders"></i> <span>Settings</span>
            </button>
        </nav>
    </div>

    <div class="hidden md:flex items-center gap-3 w-full p-3.5 glass-input rounded-2xl border border-purple-500/20 mt-6">
        <div class="w-9 h-9 rounded-xl gradient-btn text-white flex items-center justify-center text-sm font-bold shadow-md">
            <i class="fa-solid fa-mobile-screen"></i>
        </div>
        <div class="truncate text-left">
            <div id="badge-dev-name" class="text-xs font-extrabold truncate">Not Connected</div>
            <div id="badge-room-name" class="text-[10px] text-purple-400 font-semibold truncate">Room: -</div>
        </div>
    </div>
</aside>

<main class="flex-1 overflow-y-auto p-4 md:p-10 max-w-5xl mx-auto w-full md:h-screen min-h-0">

    <section id="send-page" class="tab-page pb-16">
        
        <div id="drop-zone" class="relative overflow-hidden glass-card border-2 border-dashed border-purple-500/40 rounded-3xl p-6 md:p-8 mb-6 md:mb-8 text-center transition-all hover:border-pink-500">
            
            <div class="absolute inset-0 pointer-events-none overflow-hidden">
                <div class="animate-ball-1 absolute -top-8 -left-8 w-32 h-32 bg-indigo-500/30 rounded-full blur-xl"></div>
                <div class="animate-ball-2 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-40 h-40 bg-purple-500/20 rounded-full blur-2xl"></div>
                <div class="animate-ball-3 absolute -bottom-10 -right-10 w-36 h-36 bg-pink-500/30 rounded-full blur-xl"></div>
            </div>

            <div class="relative z-10">
                <div class="flex flex-col sm:flex-row items-center justify-between gap-2 mb-4">
                    <h3 class="text-base md:text-lg font-bold flex items-center gap-2">
                        <i class="fa-solid fa-cloud-arrow-up text-purple-400"></i> Drop Files Here
                    </h3>
                    <span id="selection-stats" class="text-xs font-bold glass-input px-3.5 py-1.5 rounded-xl text-purple-400">Files: 0 • Size: 0 MB</span>
                </div>

                <div id="file-previews" class="flex flex-wrap justify-center gap-3 my-6 min-h-[60px] md:min-h-[80px] items-center">
                    <p class="text-xs md:text-sm opacity-60 font-medium">Drag & drop files or click Add Files button.</p>
                </div>

                <div class="flex justify-center gap-3">
                    <input type="file" id="file-input" multiple class="hidden" onchange="handleFilesSelected(this.files)">
                    <button onclick="clearFiles()" class="px-4 md:px-5 py-2.5 rounded-xl glass-input opacity-70 hover:opacity-100 hover:text-red-400 text-xs font-bold transition">
                        Clear
                    </button>
                    <button onclick="document.getElementById('file-input').click()" class="px-5 md:px-6 py-2.5 rounded-xl gradient-btn text-white font-extrabold text-xs shadow-lg shadow-purple-500/30 transition flex items-center gap-2 hover:scale-105">
                        <i class="fa-solid fa-plus"></i> Add Files
                    </button>
                </div>
            </div>
        </div>

        <div id="progress-box" class="hidden mb-6 md:mb-8 glass-card p-5 rounded-2xl">
            <div class="flex justify-between text-xs font-bold mb-2">
                <span class="text-purple-400">Sending Files...</span>
                <span id="progress-percent" class="text-pink-500">0%</span>
            </div>
            <div class="w-full h-2.5 glass-input rounded-full overflow-hidden">
                <div id="progress-fill" class="h-full gradient-btn w-0 transition-all duration-150"></div>
            </div>
        </div>

        <div class="glass-card rounded-3xl p-5 md:p-6 mb-6 md:mb-8">
            <div class="flex items-center justify-between mb-3">
                <span class="text-xs md:text-sm font-bold flex items-center gap-2">
                    <i class="fa-solid fa-paste text-pink-400"></i> Instant Clipboard / Links
                </span>
                <button onclick="sendSharedText()" class="px-4 py-1.5 rounded-xl gradient-btn text-white text-xs font-bold shadow-md hover:scale-105 transition">
                    Broadcast
                </button>
            </div>
            <textarea id="text-share-input" rows="2" placeholder="Paste links, text, or snippets to broadcast..." class="w-full glass-input rounded-xl p-3 text-xs md:text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"></textarea>
        </div>

        <div>
            <div class="flex items-center justify-between mb-4">
                <h4 class="text-xs font-extrabold uppercase tracking-widest text-purple-400 flex items-center gap-2">
                    <i class="fa-solid fa-wifi"></i> Nearby Connected Devices
                </h4>
                <button onclick="showToast('Scanning network...')" class="w-8 h-8 rounded-xl glass-input opacity-70 hover:opacity-100 flex items-center justify-center text-xs transition">
                    <i class="fa-solid fa-rotate-right"></i>
                </button>
            </div>

            <div id="devices-list" class="flex flex-col gap-3 min-h-[120px] max-h-[350px] overflow-y-auto pr-1 custom-scrollbar">
                <p class="text-center opacity-50 text-xs md:text-sm py-8">Searching for devices in network...</p>
            </div>
        </div>

    </section>

    <section id="receive-page" class="tab-page hidden pb-16">
        <h2 class="text-xl md:text-2xl font-black mb-6 gradient-text">Received Files</h2>
        <div id="received-files-list" class="space-y-4 max-h-[500px] overflow-y-auto pr-1 custom-scrollbar">
            <p class="opacity-50 text-xs md:text-sm">No files or links received yet.</p>
        </div>
    </section>

    <section id="settings-page" class="tab-page hidden space-y-4 pb-16">
        <h2 class="text-xl md:text-2xl font-black mb-6 gradient-text">Settings</h2>
        
        <div class="glass-card p-5 md:p-6 rounded-2xl flex items-center justify-between">
            <div>
                <h4 class="font-bold text-xs md:text-sm">Theme Appearance</h4>
                <p class="text-[10px] md:text-xs opacity-60">Switch between Vibrant Dark and Light themes</p>
            </div>
            <button onclick="toggleTheme()" class="px-4 md:px-5 py-2.5 rounded-xl gradient-btn text-white text-xs font-bold shadow-md hover:scale-105 transition">
                <i class="fa-solid fa-circle-half-stroke mr-1"></i> Switch Theme
            </button>
        </div>
    </section>

</main>

<script>
let ws;
let currentRoom = "";
let currentName = "";
let selectedFiles = [];

function showToast(msg, isSuccess = true) {
    const toast = document.getElementById("toast-popup");
    document.getElementById("toast-msg").innerText = msg;
    toast.classList.remove("translate-y-32", "opacity-0");
    setTimeout(() => toast.classList.add("translate-y-32", "opacity-0"), 3500);
}

function toggleTheme() {
    const htmlElem = document.documentElement;
    if (htmlElem.classList.contains('dark')) {
        htmlElem.classList.remove('dark');
        htmlElem.classList.add('light');
        showToast("Switched to Colorful Light Theme!");
    } else {
        htmlElem.classList.remove('light');
        htmlElem.classList.add('dark');
        showToast("Switched to Vibrant Dark Theme!");
    }
}

/* Drag & Drop Handlers */
const dropZone = document.getElementById('drop-zone');
['dragenter', 'dragover'].forEach(name => dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.add('border-pink-500'); }));
['dragleave', 'drop'].forEach(name => dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.remove('border-pink-500'); }));
dropZone.addEventListener('drop', (e) => handleFilesSelected(e.dataTransfer.files));

function handleFilesSelected(files) {
    selectedFiles = Array.from(files);
    let totalSize = selectedFiles.reduce((acc, f) => acc + f.size, 0);
    document.getElementById("selection-stats").innerText = `Files: ${selectedFiles.length} • Size: ${(totalSize / (1024*1024)).toFixed(1)} MB`;

    const previews = document.getElementById("file-previews");
    previews.innerHTML = "";
    
    selectedFiles.forEach(f => {
        const badge = document.createElement("div");
        badge.className = "glass-input rounded-xl px-4 py-2 flex items-center gap-2 text-xs font-bold text-purple-400 shadow-sm border border-purple-500/20";
        badge.innerHTML = `<i class="fa-solid fa-file"></i> <span>${f.name.substring(0,16)}</span>`;
        previews.appendChild(badge);
    });
}

function clearFiles() {
    selectedFiles = [];
    document.getElementById("file-input").value = "";
    document.getElementById("selection-stats").innerText = "Files: 0 • Size: 0 MB";
    document.getElementById("file-previews").innerHTML = `<p class="text-xs md:text-sm opacity-60 font-medium">Drag & drop files or click Add Files button.</p>`;
}

function joinNetwork() {
    currentName = document.getElementById("dev-name").value || "Neon Phoenix";
    const devType = document.getElementById("dev-type").value;
    const devPin = document.getElementById("dev-pin").value || "#99";
    currentRoom = document.getElementById("room-pass").value;

    if (!currentRoom) return showToast("Enter Network Password!", false);

    const host = window.location.host;
    ws = new WebSocket(`ws://${host}/ws/${currentRoom}/${encodeURIComponent(currentName)}/${encodeURIComponent(devType)}/${encodeURIComponent(devPin)}`);

    ws.onopen = () => {
        setInterval(() => ws.readyState === WebSocket.OPEN && ws.send("ping"), 10000);
    };

    ws.onmessage = (e) => {
        if (e.data === "pong") return;
        const data = JSON.parse(e.data);
        if (data.type === "device_list") renderDevices(data.devices);
        else if (data.type === "new_file") addReceivedFile(data.filename, data.sender);
        else if (data.type === "new_text") addReceivedText(data.text, data.sender);
    };

    document.getElementById("login-modal").style.display = "none";
    document.getElementById("badge-dev-name").innerText = currentName;
    document.getElementById("badge-room-name").innerText = `Room: ${currentRoom}`;
    showToast(`Connected to Room: ${currentRoom}`);
}

function renderDevices(devices) {
    const list = document.getElementById("devices-list");
    list.innerHTML = "";

    devices.forEach(d => {
        if (d.name === currentName) return;
        const card = document.createElement("div");
        card.className = "glass-card rounded-2xl p-3.5 md:p-4 flex items-center justify-between hover:border-purple-500 transition shrink-0 w-full";

        card.innerHTML = `
            <div class="flex items-center gap-3 md:gap-4 truncate">
                <div class="w-10 h-10 md:w-12 md:h-12 rounded-2xl gradient-btn text-white flex items-center justify-center text-lg md:text-xl font-bold shadow-md shrink-0">
                    <i class="fa-solid fa-mobile-screen"></i>
                </div>
                <div class="truncate">
                    <h5 class="font-bold text-xs md:text-sm truncate">${d.name}</h5>
                    <div class="flex gap-1.5 md:gap-2 mt-1">
                        <span class="text-[9px] md:text-[10px] font-extrabold glass-input text-purple-400 px-2 py-0.5 rounded-lg border border-purple-500/20">${d.pin}</span>
                        <span class="text-[9px] md:text-[10px] font-extrabold glass-input text-pink-400 px-2 py-0.5 rounded-lg border border-pink-500/20">${d.type}</span>
                    </div>
                </div>
            </div>
            <button onclick="sendFilesToDevice('${d.name}')" class="px-4 md:px-5 py-2 md:py-2.5 rounded-xl gradient-btn text-white font-extrabold text-xs shadow-md shadow-purple-500/20 hover:scale-105 transition flex items-center gap-1.5 md:gap-2 shrink-0">
                <i class="fa-solid fa-paper-plane"></i> Send
            </button>
        `;
        list.appendChild(card);
    });

    if (list.children.length === 0) {
        list.innerHTML = `<p class="text-center opacity-50 text-xs md:text-sm py-8">No other devices online in this room.</p>`;
    }
}

function sendFilesToDevice(target) {
    if (selectedFiles.length === 0) return showToast("Select files first!", false);

    const pBox = document.getElementById("progress-box");
    const pFill = document.getElementById("progress-fill");
    const pText = document.getElementById("progress-percent");
    pBox.classList.remove("hidden");

    selectedFiles.forEach(file => {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("room", currentRoom);
        formData.append("sender", currentName);

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload", true);
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                pFill.style.width = percent + "%";
                pText.innerText = percent + "%";
            }
        };
        xhr.onload = () => {
            showToast(`Sent file to ${target}!`);
            setTimeout(() => pBox.classList.add("hidden"), 1000);
            clearFiles();
        };
        xhr.send(formData);
    });
}

function sendSharedText() {
    const val = document.getElementById("text-share-input").value.trim();
    if (!val) return showToast("Enter text to broadcast!", false);
    ws.send("TEXT_SHARE:" + val);
    showToast("Text shared!");
    document.getElementById("text-share-input").value = "";
}

function addReceivedFile(filename, sender) {
    const container = document.getElementById("received-files-list");
    if (container.innerHTML.includes("No files or links")) container.innerHTML = "";

    const fileUrl = `/download/${encodeURIComponent(filename)}`;
    const staticUrl = `/shared_downloads/${encodeURIComponent(filename)}`;
    const ext = filename.split('.').pop().toLowerCase();
    
    let previewHTML = '';
    const imgExts = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'];
    const videoExts = ['mp4', 'webm', 'ogg', 'mov'];
    const audioExts = ['mp3', 'wav', 'ogg', 'm4a'];

    if (imgExts.includes(ext)) {
        // Full Image view fix: max-h-[400px], object-contain and click-to-open full resolution
        previewHTML = `
            <div class="mt-3 rounded-2xl overflow-hidden border border-purple-500/20 bg-black/40 p-1">
                <a href="${staticUrl}" target="_blank" title="Click to open full size">
                    <img src="${staticUrl}" alt="${filename}" class="w-full h-auto max-h-[400px] object-contain rounded-xl hover:scale-[1.01] transition-transform duration-200" />
                </a>
            </div>`;
    } else if (videoExts.includes(ext)) {
        previewHTML = `
            <div class="mt-3 rounded-2xl overflow-hidden border border-purple-500/20 bg-black/40">
                <video controls class="w-full h-auto max-h-[350px] rounded-xl">
                    <source src="${staticUrl}">
                    Your browser does not support video.
                </video>
            </div>`;
    } else if (audioExts.includes(ext)) {
        previewHTML = `
            <div class="mt-3">
                <audio controls class="w-full rounded-xl">
                    <source src="${staticUrl}">
                    Your browser does not support audio.
                </audio>
            </div>`;
    } else if (ext === 'pdf') {
        previewHTML = `
            <div class="mt-3 rounded-2xl overflow-hidden border border-purple-500/20 h-64">
                <iframe src="${staticUrl}" class="w-full h-full"></iframe>
            </div>`;
    }

    const card = document.createElement("div");
    card.className = "glass-card p-4 md:p-5 rounded-2xl flex flex-col gap-2";
    card.innerHTML = `
        <div class="flex items-center justify-between w-full">
            <div class="truncate mr-2">
                <h5 class="font-bold text-xs md:text-sm truncate">${filename}</h5>
                <p class="text-[10px] md:text-xs opacity-60 mt-0.5">From: ${sender}</p>
            </div>
            <a href="${fileUrl}" download class="px-4 py-2 rounded-xl gradient-btn text-white font-bold text-xs shadow-md hover:scale-105 transition shrink-0">
                <i class="fa-solid fa-download mr-1"></i> Download
            </a>
        </div>
        ${previewHTML}
    `;
    container.appendChild(card);
    showToast(`Received file from ${sender}`);
}

function addReceivedText(text, sender) {
    const container = document.getElementById("received-files-list");
    if (container.innerHTML.includes("No files or links")) container.innerHTML = "";

    const card = document.createElement("div");
    card.className = "glass-card p-4 md:p-5 rounded-2xl";
    card.innerHTML = `
        <div class="flex justify-between items-center mb-2">
            <span class="text-xs font-bold text-purple-400">Broadcast Text from ${sender}</span>
            <button onclick="navigator.clipboard.writeText(\`${text}\`); showToast('Copied!')" class="text-xs font-bold glass-input px-3 py-1 rounded-lg">Copy</button>
        </div>
        <p class="text-xs md:text-sm glass-input p-3 rounded-xl border border-purple-500/20 break-all">${text}</p>
    `;
    container.appendChild(card);
    showToast(`New broadcast text received`);
}

function switchTab(tab) {
    document.querySelectorAll('.tab-page').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.nav-btn').forEach(el => {
        el.classList.remove('active', 'gradient-btn', 'text-white', 'shadow-md');
        el.classList.add('opacity-70');
    });
    
    document.getElementById(`${tab}-page`).classList.remove('hidden');
    const activeBtn = document.getElementById(`nav-${tab}`);
    activeBtn.classList.add('active', 'gradient-btn', 'text-white', 'shadow-md');
    activeBtn.classList.remove('opacity-70');
}
</script>
</body>
</html>
"""