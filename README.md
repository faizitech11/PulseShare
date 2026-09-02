PulseShare
PulseShare is a real-time, room-based P2P file sharing and text broadcasting web application for local area networks built with FastAPI and WebSockets.

⚡ PulseShare

> A high-performance, real-time Peer-to-Peer (P2P) file sharing and instant text broadcasting web application built for Local Area Networks (LAN).

PulseShare allows seamless file transfers, live previews, and text sharing across multiple devices (Windows, Android, iOS, macOS) connected to the same Wi-Fi network without requiring external internet access or third-party cloud services.



 ✨ Features

🔒 Room-Based Privacy:** Secure network rooms using custom passwords/pins.  
⚡ Real-Time Device Discovery:** Automated active device listing powered by WebSockets.
📁 Multi-File Uploads:** Drag-and-drop or batch file selection with live transfer progress indicators.
🖼️ Built-In Media Previews:** 
  - Full-resolution responsive image previews (uncropped).
  - In-browser HTML5 video and audio playback.
  - Interactive inline PDF viewing.
  📋 Instant Clipboard / Text Broadcast:** Broadcast URLs, snippets, or messages instantly across all connected room devices.
  🌓 Adaptive Glassmorphism UI:** Modern, responsive UI with single-click theme switching (Vibrant Dark & Light themes).



## 🛠️ Tech Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.8+)
- **Real-Time Communication:** WebSockets (`ConnectionManager`)
- **Frontend:** HTML5, Modern Vanilla JavaScript (ES6+), [Tailwind CSS](https://tailwindcss.com/)
- **Icons & Fonts:** FontAwesome 6, Plus Jakarta Sans
- **ASGI Server:** [Uvicorn](https://www.uvicorn.org/)

---

## 🚀 Quick Start

### 1. Prerequisites

Ensure Python 3.8 or higher is installed on your machine.

### 2. Installation

Clone or download the project files into your workspace, then install the required dependencies:

```bash
pip install fastapi uvicorn
3. Running the Server
Start the application on host 0.0.0.0 so it listens to inbound connections across your local network:

Bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
📱 Connecting Secondary Devices (Mobile / PC)
Find the Host PC's local IP address:

Windows: Run ipconfig in Command Prompt (look for IPv4 Address, e.g., 192.168.10.30).

Linux / macOS: Run hostname -I or ifconfig in Terminal.

Open the web browser on any second device connected to the same Wi-Fi network.

Access the application using your Host PC IP and Port 8000:

HTTP
[http://192.168.10.30:8000](http://192.168.10.30:8000)
Enter your device details, choose/create a Room Password, and start sharing!

📂 Project Structure
Plaintext
.
├── main.py              # FastAPI application server, WebSockets & UI layout
├── shared_downloads/    # Directory where shared files are stored
└── README.md            # Project documentation
🔧 Troubleshooting
Page loading times out on second device?
Ensure Port 8000 is allowed through the Host PC's firewall (e.g., Windows Defender Firewall Inbound Rules).

Devices not discovering each other?
Confirm that all devices are connected to the exact same Wi-Fi router/subnet and have joined using the same Room Password.


<FollowUp label="Would you like me to generate a Dockerfile to containerize PulseShare?" query="Generate a production-ready Dockerfile and docker-compose.yml for this FastAPI PulseShare project."/>
