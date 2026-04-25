import asyncio, websockets, json, threading

clients = set()

async def handler(websocket):
    clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)

def wait_for_enter(loop):
    while True:
        input()
        payload = json.dumps({"type": "sos_alert", "status": "critical"})
        for c in list(clients):
            asyncio.run_coroutine_threadsafe(c.send(payload), loop)

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        loop = asyncio.get_running_loop()
        threading.Thread(target=wait_for_enter, args=(loop,), daemon=True).start()
        await asyncio.Future()

asyncio.run(main())
