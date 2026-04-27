import asyncio
import websockets
import json
from datetime import datetime

clients = set()

async def handler(ws):
    clients.add(ws)
    try:
        async for msg in ws:
            data = json.loads(msg)
            stamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{stamp}] DISPATCH | {data['alert_type'].upper()} | {data['building']} - {data['room']}")
            websockets.broadcast(clients, msg)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.remove(ws)

async def main():
    print("🟢 PANDORA CENTRAL COMMAND ONLINE [PORT 8765]")
    async with websockets.serve(handler, "localhost", 8765, max_size=10**7):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())