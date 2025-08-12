#!/usr/bin/env python3
"""
Terraform Provider RPC Server (Demo)
Implements basic gRPC server for Terraform provider protocol v5
"""

import socket
import sys
import time
import threading

def find_free_port():
    """Find a free port to listen on"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def run_mock_server(port):
    """Run a mock server that accepts connections"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', port))
        s.listen(1)
        
        # Keep server running
        while True:
            try:
                conn, addr = s.accept()
                with conn:
                    # Send a basic response
                    conn.recv(1024)  # Read request
                    conn.sendall(b"Provider server running (PSPF Demo)\n")
            except KeyboardInterrupt:
                break
            except:
                pass

def main():
    """Start the provider server"""
    port = find_free_port()
    
    # Print the handshake line Terraform expects
    print(f"1|5|tcp|127.0.0.1:{port}|grpc|")
    sys.stdout.flush()
    
    # Start server in background
    server_thread = threading.Thread(target=run_mock_server, args=(port,))
    server_thread.daemon = True
    server_thread.start()
    
    # Keep running until interrupted
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()