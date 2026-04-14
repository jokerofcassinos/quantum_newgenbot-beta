"""
Debug Socket Test - Teste simplificado para debugar comunicação TCP

Este script cria um servidor socket mínimo e mostra exatamente o que acontece
quando o MT5 conecta.
"""

import socket
import threading
import time
import sys

def handle_client(client_socket, addr):
    """Handle single client connection"""
    print(f"\n[SERVER] Client connected from {addr}")
    
    try:
        # Receive handshake
        print("[SERVER] Waiting for handshake...")
        data = client_socket.recv(4096).decode('utf-8')
        print(f"[SERVER] Received: {data}")
        
        # Send ack
        ack = "HANDSHAKE_OK|Python|v1.0\n"
        print(f"[SERVER] Sending ack: {ack.strip()}")
        client_socket.send(ack.encode('utf-8'))
        print("[SERVER] Ack sent")
        
        # Keep connection alive and show all received data
        print("[SERVER] Listening for data...")
        while True:
            try:
                data = client_socket.recv(4096).decode('utf-8')
                if data:
                    print(f"[SERVER] Received ({len(data)} bytes): {data[:100]}...")
                else:
                    print("[SERVER] Client disconnected (empty data)")
                    break
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[SERVER] Error receiving: {e}")
                break
        
    except Exception as e:
        print(f"[SERVER] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[SERVER] Closing client connection")
        client_socket.close()

def main():
    print("="*60)
    print("SOCKET DEBUG SERVER")
    print("="*60)
    
    host = '127.0.0.1'
    port = 5555
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    
    try:
        server.bind((host, port))
        server.listen(1)
        server.settimeout(1.0)
        print(f"[SERVER] Listening on {host}:{port}")
        print(f"[SERVER] Waiting for MT5 to connect...")
        print(f"[SERVER] Press Ctrl+C to stop\n")
        
        client_count = 0
        while True:
            try:
                client, addr = server.accept()
                client_count += 1
                print(f"\n{'='*60}")
                print(f"CONNECTION #{client_count}")
                print(f"{'='*60}")
                
                client.settimeout(0.1)
                
                # Handle in thread
                t = threading.Thread(target=handle_client, args=(client, addr))
                t.daemon = True
                t.start()
                
            except socket.timeout:
                continue
                
    except KeyboardInterrupt:
        print("\n\n[SERVER] Stopping...")
    finally:
        server.close()
        print("[SERVER] Server closed")

if __name__ == "__main__":
    main()
