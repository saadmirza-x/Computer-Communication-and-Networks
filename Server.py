"""
===============================================================================
Course      : Computer Communication Networks (CCN)
Project     : Semester Project
File        : server.py

Team Members:
- [Saad Mirza]        - [2023498]
- [Mian Moiz ud din]  - [2023315]
- [Hassan Khalid]     - [2023435]

Description :
This file provides the concurrent server architecture utilizing TCP sockets and
threading to manage multiple client connections. It maintains an active user 
registry and correctly routes incoming broadcast and private messages.
===============================================================================
"""
import socket
import threading
import json
import struct
import sys

# --- Network Helper Functions ---
def send_message(sock, msg_dict):
    """Serializes a dictionary to JSON, prepends a 4-byte length header, and sends it."""
    try:
        payload = json.dumps(msg_dict).encode('utf-8')
        header = struct.pack('!I', len(payload)) # 4-byte unsigned integer (network byte order)
        sock.sendall(header + payload)
    except Exception as e:
        print(f"Error sending message: {e}")

def recvall(sock, n):
    """Helper function to exactly read n bytes from a socket."""
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def recv_message(sock):
    """Reads the 4-byte header, then reads the exact payload length and decodes JSON."""
    header = recvall(sock, 4)
    if not header:
        return None
    msg_len = struct.unpack('!I', header)[0]
    payload = recvall(sock, msg_len)
    if not payload:
        return None
    return json.loads(payload.decode('utf-8'))

# --- Server Class ---
class IMServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.clients = {} # Maps username -> socket object
        self.lock = threading.Lock() # Thread lock for modifying the clients dictionary
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))

    def broadcast_user_list(self):
        """Sends the current list of active users to everyone."""
        with self.lock:
            user_list = list(self.clients.keys())
            msg = {"type": "USER_LIST", "users": user_list}
            for user, sock in self.clients.items():
                send_message(sock, msg)

    def handle_client(self, conn, addr):
        print(f"[NEW CONNECTION] {addr} connected.")
        username = None
        
        try:
            # 1. Registration Phase
            reg_msg = recv_message(conn)
            if reg_msg and reg_msg.get('type') == 'REGISTER':
                requested_name = reg_msg.get('username')
                with self.lock:
                    if requested_name in self.clients or not requested_name:
                        send_message(conn, {"type": "ERROR", "message": "Username taken or invalid."})
                        conn.close()
                        return
                    else:
                        username = requested_name
                        self.clients[username] = conn
                        send_message(conn, {"type": "REGISTER_SUCCESS"})
                
                print(f"[REGISTERED] {username} joined from {addr}")
                self.broadcast_user_list()
            else:
                conn.close()
                return

            # 2. Message Routing Loop
            while True:
                msg = recv_message(conn)
                if not msg:
                    break # Client disconnected

                msg_type = msg.get('type')
                
                if msg_type == 'BROADCAST':
                    # Send to everyone
                    formatted_msg = {
                        "type": "BROADCAST",
                        "sender": username,
                        "text": msg.get('text'),
                        "timestamp": msg.get('timestamp')
                    }
                    with self.lock:
                        for user, sock in self.clients.items():
                            send_message(sock, formatted_msg)

                elif msg_type == 'UNICAST':
                    # Send to a specific user and the sender (for local display)
                    target = msg.get('target')
                    formatted_msg = {
                        "type": "UNICAST",
                        "sender": username,
                        "target": target,
                        "text": msg.get('text'),
                        "timestamp": msg.get('timestamp')
                    }
                    with self.lock:
                        if target in self.clients:
                            send_message(self.clients[target], formatted_msg)
                            send_message(conn, formatted_msg) # Send back to sender for confirmation
                        else:
                            send_message(conn, {"type": "ERROR", "message": f"User {target} not found."})

        except ConnectionResetError:
            pass # Standard disconnect
        except Exception as e:
            print(f"[ERROR] {addr}: {e}")
        finally:
            # 3. Cleanup on disconnect
            if username:
                with self.lock:
                    if username in self.clients:
                        del self.clients[username]
                print(f"[DISCONNECTED] {username} left.")
                self.broadcast_user_list()
            conn.close()

    def start(self):
        self.server_socket.listen()
        print(f"[LISTENING] Server is listening on {self.host}:{self.port}")
        try:
            while True:
                conn, addr = self.server_socket.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("\n[SHUTDOWN] Server shutting down.")
            self.server_socket.close()
            sys.exit(0)

if __name__ == "__main__":
    server = IMServer()
    server.start()