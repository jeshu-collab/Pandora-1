import asyncio
import websockets
import json
from datetime import datetime

# Keep track of all connected nodes (Dashboards and Cameras)
connected_clients = set()

async def handler(websocket):
    # Register the new client
    connected_clients.add(websocket)
    print(f"[+] NEW CONNECTION. TOTAL ACTIVE NODES: {len(connected_clients)}")
    
    try:
        async for message in websocket:
            data = json.loads(message)
            stamp = datetime.now().strftime("%H:%M:%S")

            # --- SMART ROUTING LOGIC ---
            
            # ROUTE 1: Threat Alert from the Camera
            if "alert_type" in data:
                print(f"[{stamp}] 🚨 DISPATCH | {data['alert_type'].upper()} | {data['building']}")
            
            # ROUTE 2: Hot-Swap Command from the Dashboard
            elif "command" in data:
                print(f"[{stamp}] ⚙️ COMMAND ROUTED | {data['command']} -> {data.get('type', 'UNKNOWN').upper()}")
            
            # --- BROADCAST ENGINE ---
            # Forward the message to all OTHER connected clients
            for client in connected_clients:
                if client != websocket:
                    try:
                        await client.send(message)
                    except websockets.exceptions.ConnectionClosed:
                        pass

    except websockets.exceptions.ConnectionClosedError:
        pass
    finally:
        # Unregister client when they disconnect or close the browser
        connected_clients.remove(websocket)
        print(f"[-] NODE DISCONNECTED. TOTAL ACTIVE: {len(connected_clients)}")

async def main():
    print("🟢 PANDORA CENTRAL COMMAND ONLINE [PORT 8765]")
    print("📡 Listening for bidirectional traffic on 0.0.0.0...")
    
    # max_size=10**7 allows large Base64 images to pass through safely
    async with websockets.serve(handler, "0.0.0.0", 8765, max_size=10**7):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())