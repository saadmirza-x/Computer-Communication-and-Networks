"""
===============================================================================
Course      : Computer Communication Networks (CCN)
Project     : Semester Project
File        : client.py

Team Members:
- [Saad Mirza]       - [2023498]
- [Mian Moiz ud din] - [2023315]
- [Hassan Khalid]    - [2023435]

Description :
This file implements the client-side graphical interface and network logic 
using Tkinter and TCP sockets. It manages user registration, background message
polling, and handles both broadcast and unicast communication.
===============================================================================
"""
import socket
import threading
import json
import struct
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import queue
import time
from datetime import datetime

# --- Network Helper Functions ---
def send_message(sock, msg_dict):
    try:
        payload = json.dumps(msg_dict).encode('utf-8')
        header = struct.pack('!I', len(payload))
        sock.sendall(header + payload)
    except Exception as e:
        print(f"Send error: {e}")

def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def recv_message(sock):
    header = recvall(sock, 4)
    if not header: return None
    msg_len = struct.unpack('!I', header)[0]
    payload = recvall(sock, msg_len)
    if not payload: return None
    return json.loads(payload.decode('utf-8'))

# --- Client Application ---
class IMClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Instant Messenger")
        self.root.geometry("400x500")
        
        self.sock = None
        self.username = ""
        self.gui_queue = queue.Queue() # Thread-safe queue for UI updates
        
        self.build_login_screen()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- GUI Construction ---
    def build_login_screen(self):
        self.login_frame = tk.Frame(self.root, pady=50)
        self.login_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(self.login_frame, text="Username:").pack(pady=5)
        self.entry_username = tk.Entry(self.login_frame)
        self.entry_username.pack(pady=5)

        tk.Label(self.login_frame, text="Server IP:").pack(pady=5)
        self.entry_ip = tk.Entry(self.login_frame)
        self.entry_ip.insert(0, "127.0.0.1")
        self.entry_ip.pack(pady=5)

        tk.Button(self.login_frame, text="Connect", command=self.connect_to_server).pack(pady=20)

    def build_chat_screen(self):
        self.login_frame.destroy()
        self.chat_frame = tk.Frame(self.root)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Chat History Area
        self.chat_area = scrolledtext.ScrolledText(self.chat_frame, wrap=tk.WORD, state='disabled')
        self.chat_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Bottom Input Area
        self.bottom_frame = tk.Frame(self.chat_frame)
        self.bottom_frame.pack(fill=tk.X)

        # Dropdown to select broadcast or unicast
        self.target_var = tk.StringVar(value="All (Broadcast)")
        self.target_menu = ttk.Combobox(self.bottom_frame, textvariable=self.target_var, state="readonly", width=15)
        self.target_menu.pack(side=tk.LEFT, padx=(0, 5))

        # Message Input
        self.entry_msg = tk.Entry(self.bottom_frame)
        self.entry_msg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.entry_msg.bind("<Return>", lambda event: self.send_chat_message())

        # Send Button
        tk.Button(self.bottom_frame, text="Send", command=self.send_chat_message).pack(side=tk.RIGHT)

        # Start checking the queue for incoming messages
        self.root.after(100, self.process_queue)

    # --- Network Operations ---
    def connect_to_server(self):
        self.username = self.entry_username.get().strip()
        ip = self.entry_ip.get().strip()
        
        if not self.username or not ip:
            messagebox.showerror("Error", "Please fill in all fields")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((ip, 5000))
            
            # Send Registration
            send_message(self.sock, {"type": "REGISTER", "username": self.username})
            response = recv_message(self.sock)
            
            if response and response.get("type") == "REGISTER_SUCCESS":
                self.build_chat_screen()
                self.display_system_message("Connected to server.")
                
                # Start background thread to listen for incoming messages
                listen_thread = threading.Thread(target=self.receive_loop)
                listen_thread.daemon = True
                listen_thread.start()
            else:
                err = response.get("message", "Registration failed") if response else "No response"
                messagebox.showerror("Error", err)
                self.sock.close()

        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect: {e}")

    def receive_loop(self):
        """Runs in a background thread, constantly listening to the server."""
        while True:
            try:
                msg = recv_message(self.sock)
                if not msg:
                    break
                self.gui_queue.put(msg) # Safely hand off to GUI thread
            except Exception:
                break
        self.gui_queue.put({"type": "SYSTEM", "text": "Disconnected from server."})

    def send_chat_message(self):
        text = self.entry_msg.get().strip()
        if not text: return
        
        target = self.target_var.get()
        timestamp = datetime.now().strftime("%H:%M")

        if target == "All (Broadcast)":
            msg = {"type": "BROADCAST", "text": text, "timestamp": timestamp}
        else:
            msg = {"type": "UNICAST", "target": target, "text": text, "timestamp": timestamp}

        send_message(self.sock, msg)
        self.entry_msg.delete(0, tk.END)

    # --- GUI Updates ---
    def process_queue(self):
        """Runs on the main GUI thread, updating the UI safely."""
        while not self.gui_queue.empty():
            msg = self.gui_queue.get()
            msg_type = msg.get('type')

            if msg_type == 'USER_LIST':
                users = msg.get('users', [])
                if self.username in users:
                    users.remove(self.username) # Don't DM yourself
                self.target_menu['values'] = ["All (Broadcast)"] + users
                if self.target_var.get() not in self.target_menu['values']:
                    self.target_var.set("All (Broadcast)")

            elif msg_type == 'BROADCAST':
                display_text = f"[{msg['timestamp']}] {msg['sender']} (All): {msg['text']}"
                self.display_message(display_text)

            elif msg_type == 'UNICAST':
                if msg['sender'] == self.username:
                    display_text = f"[{msg['timestamp']}] You -> {msg['target']}: {msg['text']}"
                else:
                    display_text = f"[{msg['timestamp']}] {msg['sender']} (Private): {msg['text']}"
                self.display_message(display_text)

            elif msg_type == 'SYSTEM':
                self.display_system_message(msg['text'])
                
            elif msg_type == 'ERROR':
                messagebox.showwarning("Server Error", msg['message'])

        self.root.after(100, self.process_queue) # Re-check every 100ms

    def display_message(self, text):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, text + "\n")
        self.chat_area.see(tk.END)
        self.chat_area.config(state='disabled')

    def display_system_message(self, text):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, f"--- {text} ---\n")
        self.chat_area.see(tk.END)
        self.chat_area.config(state='disabled')

    def on_closing(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = IMClient(root)
    root.mainloop()