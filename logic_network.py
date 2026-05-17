import json
import os
import socket
import threading
import time
import uuid
import sys
import hashlib
import hmac
import base64
import struct
from copy import deepcopy
from PyQt6.QtCore import QObject, pyqtSignal

from logic_models import Project
from logic_project import ProjectManager, SettingsManager, BalanceCalculator
from config import ATTACHMENTS_DIR, sanitize_filename, safe_path_resolve

# =======================================================================
# PRODUCTION NETWORK SECURITY CONSTRAINTS
# =======================================================================
MAX_MSG_SIZE = 50 * 1024 * 1024        # Maximum 50 MB packet payload
MAX_CLIENTS = 50                       # Max concurrent TCP clients connected to host
MAX_AUTH_ATTEMPTS = 10                 # Max failed attempts before lockout
LOCKOUT_TIME = 30                      # Lockout IP duration in seconds (30s prevents harsh UI block)
PBKDF2_ITERATIONS = 50000              # Standard iterations to thwart fast-hashing yet stay responsive
# =======================================================================

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

def send_msg(sock, data_bytes):
    length = len(data_bytes)
    sock.sendall(struct.pack('>I', length) + data_bytes)

def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet: return None
        data.extend(packet)
    return data

def recv_msg(sock):
    raw_msglen = recvall(sock, 4)
    if not raw_msglen: return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    
    if msglen > MAX_MSG_SIZE:
        print(f"SECURITY ALERT: Dropping connection, message size {msglen} exceeds maximum allowed size.", file=sys.stderr)
        return None
        
    return recvall(sock, msglen)

def hash_password(password: str) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode(), b'BS_App_Secure_Salt_2026', PBKDF2_ITERATIONS).hex()

def get_encryption_key(password: str, salt: bytes) -> bytes:
    if not CRYPTO_AVAILABLE: return b""
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=PBKDF2_ITERATIONS, backend=default_backend())
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

class NetworkSignals(QObject):
    discovered = pyqtSignal(list)
    host_received_action = pyqtSignal(str, str, dict)       # share_key, action_type, action_data
    host_clients_updated = pyqtSignal(str, list)            # share_key, list of client usernames
    client_connected = pyqtSignal(object, list, list)       # project, settlements, settlement_entries
    client_received_update = pyqtSignal(object, list, list)  # project, settlements, settlement_entries
    client_disconnected = pyqtSignal()

class NetworkManager:
    UDP_PORT = 45454

    def __init__(self, signals: NetworkSignals, settings_mgr: SettingsManager):
        self.peer_id = str(uuid.uuid4())
        self.signals = signals  
        self.settings_mgr = settings_mgr  
        
        self.active_shares = {}  
        self.discovered_projects = {}  
        self.auth_attempts = {} 
        
        self.client_socket = None
        self.remote_pwd = ""
        self.remote_salt = b""
        self.connected_share_name = None
        self.connected_host_name = "Unknown Host"
        
        self.running = False
        self.tcp_port = 0
        self.tcp_server = None

    def start(self):
        if self.running: return
        self.running = True
        
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server.bind(('0.0.0.0', 0))
        self.tcp_server.listen(5)
        self.tcp_port = self.tcp_server.getsockname()[1]
        
        threading.Thread(target=self._tcp_server_loop, daemon=True).start()
        threading.Thread(target=self._udp_listener, daemon=True).start()
        threading.Thread(target=self._udp_broadcaster, daemon=True).start()

    def stop(self):
        self.running = False
        self.disconnect_client()
        for share in self.active_shares.values():
            for c in list(share["clients"].keys()):
                try: c.close()
                except: pass
        if self.tcp_server:
            try: self.tcp_server.close()
            except: pass
        self.active_shares.clear()
        self.discovered_projects.clear()

    def _inject_files_for_network(self, project: Project, project_name: str) -> dict:
        data = ProjectManager._to_json([project])[0]
        proj_folder = ATTACHMENTS_DIR / sanitize_filename(project_name)
        for t in data["teammates"]:
            if t.get("avatar"):
                try:
                    path = safe_path_resolve(proj_folder, t["avatar"])
                    if path.exists():
                        with open(path, "rb") as f:
                            t["avatar_b64"] = base64.b64encode(f.read()).decode('utf-8')
                except ValueError: pass
            for e in t["expenses"]:
                for att in e["attachments"]:
                    if "saved_name" in att:
                        try:
                            path = safe_path_resolve(proj_folder, att["saved_name"])
                            if path.exists():
                                with open(path, "rb") as f:
                                    att["file_data"] = base64.b64encode(f.read()).decode('utf-8')
                        except ValueError: pass
        return data

    def _inject_settlement_entry_files(self, entries: list, project_name: str) -> list:
        proj_folder = ATTACHMENTS_DIR / sanitize_filename(project_name)
        result = []
        for entry in entries:
            entry_copy = deepcopy(entry)
            for att in entry_copy.get("attachments", []):
                if "saved_name" in att:
                    try:
                        path = safe_path_resolve(proj_folder, att["saved_name"])
                        if path.exists():
                            with open(path, "rb") as f:
                                att["file_data"] = base64.b64encode(f.read()).decode('utf-8')
                    except ValueError: pass
            result.append(entry_copy)
        return result

    def _extract_files_from_network(self, data: dict, original_project_name: str) -> Project:
        proj_folder = ATTACHMENTS_DIR / sanitize_filename(original_project_name)
        proj_folder.mkdir(parents=True, exist_ok=True)
        
        for t in data.get("teammates", []):
            if "avatar_b64" in t and t.get("avatar"):
                try:
                    path = safe_path_resolve(proj_folder, t["avatar"])
                    with open(path, "wb") as f:
                        f.write(base64.b64decode(t["avatar_b64"]))
                except Exception: pass
                del t["avatar_b64"]
                
            for e in t.get("expenses", []):
                for att in e.get("attachments", []):
                    if "file_data" in att and "saved_name" in att:
                        try:
                            path = safe_path_resolve(proj_folder, att["saved_name"])
                            with open(path, "wb") as f:
                                f.write(base64.b64decode(att["file_data"]))
                        except Exception: pass
                        del att["file_data"]
                        
        return ProjectManager._from_json([data])[0]

    def _extract_settlement_entry_files(self, entries: list, project_name: str) -> list:
        proj_folder = ATTACHMENTS_DIR / sanitize_filename(project_name)
        proj_folder.mkdir(parents=True, exist_ok=True)
        result = []
        for entry in entries:
            for att in entry.get("attachments", []):
                if "file_data" in att and "saved_name" in att:
                    try:
                        path = safe_path_resolve(proj_folder, att["saved_name"])
                        with open(path, "wb") as f:
                            f.write(base64.b64decode(att["file_data"]))
                    except Exception: pass
                    del att["file_data"]
            result.append(entry)
        return result

    def share_project(self, project: Project, custom_name: str, password: str, is_public: bool):
        self.active_shares[project.name] = {
            "custom_name": custom_name,
            "project": project, 
            "visibility": "public" if is_public else "private",
            "password": password,
            "clients": {} # socket -> client username
        }

    def stop_sharing(self, project_name: str):
        if project_name in self.active_shares:
            share = self.active_shares[project_name]
            msg = json.dumps({"type": "disconnect"}).encode()
            for c in list(share["clients"].keys()):
                try: send_msg(c, msg); c.close()
                except: pass
            del self.active_shares[project_name]

    def host_broadcast_update(self, project: Project):
        if project.name not in self.active_shares: return
        share = self.active_shares[project.name]
        
        proj_dict = self._inject_files_for_network(project, project.name)
        settlements = self.settings_mgr.get_settlements(project.name)
        settlement_entries = self._inject_settlement_entry_files(
            self.settings_mgr.get_settlement_entries(project.name), project.name
        )
        
        payload_bytes = json.dumps({
            "type": "update",
            "data": proj_dict,
            "settlements": settlements,
            "settlement_entries": settlement_entries
        }).encode('utf-8')
        
        dead_clients = []
        for c in list(share["clients"].keys()):
            try:
                if share["password"] and CRYPTO_AVAILABLE:
                    salt = os.urandom(16)
                    key = get_encryption_key(share["password"], salt)
                    enc = Fernet(key).encrypt(payload_bytes)
                    resp = json.dumps({"encrypted": True, "salt": base64.b64encode(salt).decode('utf-8'), "payload": base64.b64encode(enc).decode('utf-8')}).encode()
                else:
                    resp = json.dumps({"encrypted": False, "payload": payload_bytes.decode('utf-8')}).encode()
                send_msg(c, resp)
            except Exception as e:
                dead_clients.append(c)
                
        for c in dead_clients:
            if c in share["clients"]:
                del share["clients"][c]
                
        if dead_clients:
            self.signals.host_clients_updated.emit(project.name, list(share["clients"].values()))

    def _tcp_server_loop(self):
        while self.running:
            try:
                client, addr = self.tcp_server.accept()
                
                current_clients = sum(len(s["clients"]) for s in self.active_shares.values())
                if current_clients >= MAX_CLIENTS:
                    client.close()
                    continue
                
                client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                threading.Thread(target=self._handle_host_client, args=(client,), daemon=True).start()
            except Exception:
                time.sleep(1)

    def _handle_host_client(self, client):
        ip = "Unknown"
        share_key_ref = None
        try:
            ip = client.getpeername()[0]
            
            client.settimeout(10.0) 
            data_bytes = recv_msg(client)
            if not data_bytes: return
            req = json.loads(data_bytes.decode('utf-8'))
            
            now = time.time()
            attempts, lockout_expiry = self.auth_attempts.get(ip, (0, 0))
            if now < lockout_expiry:
                send_msg(client, json.dumps({"status": "error", "reason": f"Too many failed attempts. Locked out for {int(lockout_expiry - now)}s."}).encode())
                return

            if req.get("type") == "auth":
                req_name = req.get("name")
                pwd_hash = req.get("pwd_hash", "")
                
                # Rigid fallback for Client Name
                client_username = req.get("client_username", "").strip()
                if not client_username: 
                    client_username = "Unknown Client"
                
                share_key = next((k for k, v in self.active_shares.items() if v["custom_name"].lower() == req_name.lower()), None)
                if not share_key:
                    send_msg(client, json.dumps({"status": "error", "reason": "Project not found or sharing stopped."}).encode())
                    return
                
                share_key_ref = share_key
                share = self.active_shares[share_key]
                real_pwd = share["password"]
                
                if real_pwd:
                    expected_hash = hash_password(real_pwd)
                    if not hmac.compare_digest(expected_hash, pwd_hash):
                        attempts += 1
                        if attempts >= MAX_AUTH_ATTEMPTS:
                            self.auth_attempts[ip] = (attempts, now + LOCKOUT_TIME)
                        else:
                            self.auth_attempts[ip] = (attempts, 0)
                        send_msg(client, json.dumps({"status": "error", "reason": "Invalid password."}).encode())
                        return
                        
                if ip in self.auth_attempts: del self.auth_attempts[ip]
                
                share["clients"][client] = client_username
                self.signals.host_clients_updated.emit(share_key, list(share["clients"].values()))
                
                proj_dict = self._inject_files_for_network(share["project"], share_key)
                settlements = self.settings_mgr.get_settlements(share_key)
                settlement_entries = self._inject_settlement_entry_files(
                    self.settings_mgr.get_settlement_entries(share_key), share_key
                )
                
                # Rigid fallback for Host Name
                host_user = self.settings_mgr.get("username", "").strip()
                if not host_user: 
                    host_user = "Unknown Host"
                
                payload_bytes = json.dumps({
                    "type": "init",
                    "data": proj_dict,
                    "settlements": settlements,
                    "settlement_entries": settlement_entries
                }).encode('utf-8')
                
                if real_pwd and CRYPTO_AVAILABLE:
                    salt = os.urandom(16)
                    key = get_encryption_key(real_pwd, salt)
                    enc = Fernet(key).encrypt(payload_bytes)
                    resp = json.dumps({"status": "ok", "host_name": host_user, "encrypted": True, "salt": base64.b64encode(salt).decode('utf-8'), "payload": base64.b64encode(enc).decode('utf-8')}).encode()
                else:
                    resp = json.dumps({"status": "ok", "host_name": host_user, "encrypted": False, "payload": payload_bytes.decode('utf-8')}).encode()
                send_msg(client, resp)

                client.settimeout(None) 
                
                while self.running and share_key in self.active_shares:
                    msg_bytes = recv_msg(client)
                    if not msg_bytes: break
                    
                    msg_data = json.loads(msg_bytes.decode('utf-8'))
                    if msg_data.get("encrypted"):
                        salt = base64.b64decode(msg_data["salt"])
                        enc = base64.b64decode(msg_data["payload"])
                        key = get_encryption_key(real_pwd, salt)
                        raw_payload = Fernet(key).decrypt(enc)
                    else:
                        raw_payload = msg_data["payload"].encode('utf-8')
                        
                    payload = json.loads(raw_payload.decode('utf-8'))
                    
                    if payload["type"] == "client_action":
                        action_type = payload.get("action_type")
                        action_data = payload.get("action_data", {})
                        
                        proj_folder = ATTACHMENTS_DIR / sanitize_filename(share_key)
                        proj_folder.mkdir(parents=True, exist_ok=True)
                        
                        if action_type in ["add_expense", "update_expense", "insert_expense"]:
                            exp_dict = action_data.get("expense", {})
                            for att in exp_dict.get("attachments", []):
                                if "file_data" in att and "saved_name" in att:
                                    try:
                                        path = safe_path_resolve(proj_folder, att["saved_name"])
                                        with open(path, "wb") as f:
                                            f.write(base64.b64decode(att["file_data"]))
                                    except Exception: pass
                                    del att["file_data"]
                                    
                        elif action_type in ["add_teammate", "update_teammate"]:
                            t_dict = action_data.get("teammate", {})
                            if "avatar_b64" in t_dict and t_dict.get("avatar"):
                                try:
                                    path = safe_path_resolve(proj_folder, t_dict["avatar"])
                                    with open(path, "wb") as f:
                                        f.write(base64.b64decode(t_dict["avatar_b64"]))
                                except Exception: pass
                                del t_dict["avatar_b64"]
                                
                        elif action_type == "update_settlements":
                            action_data["settlement_entries"] = self._extract_settlement_entry_files(
                                action_data.get("settlement_entries", []), share_key
                            )
                            
                        self.signals.host_received_action.emit(share_key, action_type, action_data)

        except Exception as e: pass
        finally:
            if share_key_ref and share_key_ref in self.active_shares:
                share = self.active_shares[share_key_ref]
                if client in share["clients"]:
                    del share["clients"][client]
                    self.signals.host_clients_updated.emit(share_key_ref, list(share["clients"].values()))
            try: client.close()
            except: pass

    def connect_client(self, ip: str, port: int, name: str, password: str, fallback_host_name: str) -> bool:
        self.disconnect_client()
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.client_socket.settimeout(10.0)
        
        try:
            self.client_socket.connect((ip, port))
            self.remote_pwd = password
            self.connected_share_name = name
            
            # Rigid fallback for Client Name outgoing
            client_username = self.settings_mgr.get("username", "").strip()
            if not client_username:
                client_username = "Unknown Client"
            
            req = {"type": "auth", "name": name, "pwd_hash": hash_password(password) if password else "", "client_username": client_username}
            send_msg(self.client_socket, json.dumps(req).encode('utf-8'))
            
            resp_bytes = recv_msg(self.client_socket)
            if not resp_bytes: 
                raise Exception("Connection closed by host (possibly locked out or project was removed).")
                
            resp = json.loads(resp_bytes.decode('utf-8'))
            if resp.get("status") != "ok":
                raise Exception(resp.get("reason", "Connection rejected."))
                
            # Rigid fallback for Host Name incoming
            host_name = resp.get("host_name", "").strip()
            self.connected_host_name = host_name if host_name else fallback_host_name
                
            if resp.get("encrypted"):
                if not CRYPTO_AVAILABLE: raise Exception("Cryptography library missing on this client.")
                self.remote_salt = base64.b64decode(resp["salt"])
                enc = base64.b64decode(resp["payload"])
                key = get_encryption_key(password, self.remote_salt)
                raw_payload = Fernet(key).decrypt(enc)
            else:
                raw_payload = resp["payload"].encode('utf-8')
                
            payload = json.loads(raw_payload.decode('utf-8'))
            if payload["type"] == "init":
                proj = self._extract_files_from_network(payload["data"], payload["data"]["name"])
                
                settlement_entries = payload.get("settlement_entries", [])
                if settlement_entries:
                    settlement_entries = self._extract_settlement_entry_files(
                        settlement_entries, payload["data"]["name"]
                    )
                
                threading.Thread(target=self._client_listener_loop, daemon=True).start()
                self.signals.client_connected.emit(proj, payload.get("settlements", []), settlement_entries)
                return True
        except Exception as e:
            self.disconnect_client()
            raise e
        return False

    def disconnect_client(self):
        if self.client_socket:
            try: self.client_socket.close()
            except: pass
            self.client_socket = None
            self.connected_share_name = None

    def send_client_action(self, project_name: str, action_type: str, action_data: dict):
        if not self.client_socket: return
        try:
            proj_folder = ATTACHMENTS_DIR / sanitize_filename(project_name)
            payload_data = deepcopy(action_data)
            
            if action_type in ["add_expense", "update_expense", "insert_expense"]:
                exp_dict = payload_data.get("expense", {})
                for att in exp_dict.get("attachments", []):
                    if "saved_name" in att:
                        try:
                            path = safe_path_resolve(proj_folder, att["saved_name"])
                            if path.exists():
                                with open(path, "rb") as f:
                                    att["file_data"] = base64.b64encode(f.read()).decode('utf-8')
                        except ValueError: pass
                        
            elif action_type in ["add_teammate", "update_teammate"]:
                t_dict = payload_data.get("teammate", {})
                if t_dict.get("avatar"):
                    try:
                        path = safe_path_resolve(proj_folder, t_dict["avatar"])
                        if path.exists():
                            with open(path, "rb") as f:
                                t_dict["avatar_b64"] = base64.b64encode(f.read()).decode('utf-8')
                    except ValueError: pass
                    
            elif action_type == "update_settlements":
                payload_data["settlement_entries"] = self._inject_settlement_entry_files(
                    payload_data.get("settlement_entries", []), project_name
                )
                
            payload_bytes = json.dumps({
                "type": "client_action",
                "action_type": action_type,
                "action_data": payload_data
            }).encode('utf-8')
            
            if self.remote_pwd and CRYPTO_AVAILABLE:
                salt = os.urandom(16)
                key = get_encryption_key(self.remote_pwd, salt)
                enc = Fernet(key).encrypt(payload_bytes)
                resp = json.dumps({"encrypted": True, "salt": base64.b64encode(salt).decode('utf-8'), "payload": base64.b64encode(enc).decode('utf-8')}).encode()
            else:
                resp = json.dumps({"encrypted": False, "payload": payload_bytes.decode('utf-8')}).encode()
            
            send_msg(self.client_socket, resp)
        except Exception:
            self.disconnect_client()
            self.signals.client_disconnected.emit()

    def _client_listener_loop(self):
        self.client_socket.settimeout(None)
        
        while self.running and self.client_socket:
            try:
                msg_bytes = recv_msg(self.client_socket)
                if not msg_bytes: break
                
                msg_data = json.loads(msg_bytes.decode('utf-8'))
                if msg_data.get("encrypted"):
                    salt = base64.b64decode(msg_data["salt"])
                    enc = base64.b64decode(msg_data["payload"])
                    key = get_encryption_key(self.remote_pwd, salt)
                    raw_payload = Fernet(key).decrypt(enc)
                else:
                    raw_payload = msg_data.get("payload", "").encode('utf-8')
                
                if not raw_payload: 
                    if msg_data.get("type") == "disconnect": break
                    continue
                    
                payload = json.loads(raw_payload.decode('utf-8'))
                
                if payload["type"] == "update":
                    proj = self._extract_files_from_network(payload["data"], payload["data"]["name"])
                    
                    settlement_entries = payload.get("settlement_entries", [])
                    if settlement_entries:
                        settlement_entries = self._extract_settlement_entry_files(
                            settlement_entries, payload["data"]["name"]
                        )
                    
                    self.signals.client_received_update.emit(proj, payload.get("settlements", []), settlement_entries)
                elif payload["type"] == "disconnect":
                    break
                    
            except Exception:
                break
                
        self.disconnect_client()
        self.signals.client_disconnected.emit()

    def _udp_broadcaster(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while self.running:
            host_user = self.settings_mgr.get("username", "").strip()
            if not host_user: host_user = "Unknown Host"
            
            shares_to_broadcast = [
                {"name": data["custom_name"], "auth": bool(data["password"]), "visibility": data["visibility"]} 
                for data in self.active_shares.values()
            ]
            
            try: 
                sock.sendto(json.dumps({
                    "peer_id": self.peer_id, 
                    "host_name": host_user, 
                    "port": self.tcp_port, 
                    "projects": shares_to_broadcast
                }).encode(), ('<broadcast>', self.UDP_PORT))
            except: pass
            time.sleep(5)
        sock.close()

    def _udp_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: sock.bind(('', self.UDP_PORT))
        except OSError: 
            sock.close(); return 
            
        sock.settimeout(2.0)
        while self.running:
            try:
                data, addr = sock.recvfrom(2048)
                payload = json.loads(data.decode('utf-8'))
                sender_peer_id = payload.get("peer_id")
                if sender_peer_id == self.peer_id: continue 
                
                ip, port = addr[0], payload.get("port")
                host_name = payload.get("host_name", "Unknown Host")
                
                keys_to_remove = [k for k, v in self.discovered_projects.items() if v.get("peer_id") == sender_peer_id]
                for k in keys_to_remove:
                    del self.discovered_projects[k]

                for p in payload.get("projects", []):
                    self.discovered_projects[(ip, p["name"])] = {
                        "last_seen": time.time(), 
                        "name": p["name"], 
                        "ip": ip, 
                        "port": port, 
                        "auth": p["auth"], 
                        "visibility": p.get("visibility", "public"), 
                        "host_name": host_name,
                        "peer_id": sender_peer_id
                    }
            except: pass
            
            stale = [k for k, v in self.discovered_projects.items() if time.time() - v["last_seen"] > 15]
            for k in stale: del self.discovered_projects[k]
            
            self.signals.discovered.emit(list(self.discovered_projects.values()))
        sock.close()
