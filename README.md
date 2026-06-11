# Multi-Threaded TCP Instant Messaging System

A concurrent, low-latency client-server Instant Messaging (IM) system built from scratch using raw TCP sockets and Python's standard library. This project implements custom application-layer framing to handle stream boundary issues and decouples network I/O from the user interface using a thread-safe execution model.

## 🚀 Core Features

* **Raw Socket Architecture:** Operates directly over the TCP transport layer without relying on high-level network frameworks or third-party wrappers.
* **High Concurrency Backbone:** Multi-threaded server capable of handling persistent client connections, user registrations, and dynamic socket mapping simultaneously.
* **Custom Application Protocol:** Resolves the classic TCP partial-read and packet fragmentation issues using a strict length-prefixed framing format.
* **Flexible Routing:** Supports both targeted private messages (`UNICAST`) and room-wide group communication (`BROADCAST`).
* **Asynchronous, Thread-Safe GUI:** Event-driven Tkinter desktop client featuring an isolated background worker thread for non-blocking network polling.

---

## 🛠️ Technical Architecture & Protocol

### 1. Framing & Wire Protocol
Because TCP is a stream-oriented protocol, data boundaries are not preserved. To prevent message bleeding and truncation, this system implements an explicit application-layer frame constraint:

+---------------------------+-----------------------------------+
|  Header: 4-Byte Integer   |       Payload: JSON String        |
|    (Network Byte Order)   |          (UTF-8 Encoded)          |
+---------------------------+-----------------------------------+
|  Specifies Payload Size   | Contains Type, Sender, Text, etc. |
+---------------------------+-----------------------------------+


* **Serialization:** System payloads are packed into dictionaries, serialized to JSON strings, and encoded via `utf-8`.
* **Length Prefixing:** A 4-byte big-endian unsigned integer header (`!I`) is computed using Python's `struct` module to prefix the payload, declaring its exact byte size.
* **Stream Reconstruction:** The receiving socket performs a deterministic two-stage read sequence—first fetching exactly 4 bytes to resolve the frame size, and then looping execution until that precise allocation of payload bytes is extracted from the network buffer.

### 2. Concurrency Model
* **`server.py`:** The main execution loop listens on a target port. Upon invoking `.accept()`, the incoming client socket descriptor is immediately assigned to an isolated worker thread running `handle_client`. Shared state variables (like the active username-to-socket registry) are strictly wrapped in threading primitives (`threading.Lock`) to eliminate race conditions during registration and abrupt disconnects.
* **`client.py`:** To maintain responsiveness, the GUI loop executes on the main thread while socket operations execute inside a separate daemon thread. Communication across this thread boundary is completely decoupled via a thread-safe `queue.Queue`. The GUI periodically polls the queue using a non-blocking `.after()` clock event to process and render new messages.

---

## 📂 Repository Structure

```text
├── server.py     # Concurrent server architecture, protocol parsing, & packet routing
└── client.py     # Desktop application interface, socket polling thread, & frame processing
💻 Installation & Prerequisites
The system is built entirely on the Python Standard Library. No external dependencies or virtual environments are required.  


Operating System: Cross-platform deployment setup.

Runtime Environment: Python 3.8 or higher.

Required Core Libraries: socket, threading, json, struct, tkinter, queue.  


🚦 Execution Guide
1. Spin Up the Server
Initialize the centralized routing hub first. By default, the server binds to local interfaces.

Bash
python server.py
2. Launch Client Node 1
Open a new terminal instance and execute the client wrapper interface:

Bash
python client.py

Enter a unique username and connect.

3. Launch Client Nodes 2 & 3
Repeat the process in separate terminal contexts to test multi-party concurrent communication:

Bash
python client.py

💬 Message Interface Contracts
Internally, data payloads conform to structured JSON contracts mapped over the network streams:  

Unicast Message Frame Example
JSON
{
  "type": "UNICAST",
  "sender": "Saad",
  "target": "Hassan",
  "text": "Check the frame boundaries on the server logs.",
  "timestamp": "20:51:04"
}
Broadcast Message Frame Example
JSON
{
  "type": "BROADCAST",
  "sender": "Moiz",
  "text": "The message routing layer is fully synchronized.",
  "timestamp": "20:51:30"
}
👥 Contributors
Saad Mirza - (Student ID: 2023498)

Mian Moiz ud din - (Student ID: 2023315)

Hassan Khalid - (Student ID: 2023435)
