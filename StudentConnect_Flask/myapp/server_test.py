import asyncio
import websockets
import sqlite3

async def handle_message(websocket, path):
    async for message in websocket:
        print(f"Received message: {message}")

        if message == "INSERT INTO Class_info (subject, username, password, email) VALUES (?, ?, ?, ?)":
            username = await websocket.recv()
            password = await websocket.recv()
            email = await websocket.recv()
            conn = sqlite3.connect('test_db.db')
            cursor = conn.cursor()
            query = "INSERT INTO Class_info (subject, username, password, email) VALUES (?, ?, ?, ?)"
            values = ("5261", username, password, email)
            cursor.execute(query, values)
            conn.commit()
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            response = str(result)
        else:
            result = execute_query(message)
            response = str(result)
        
        await websocket.send(response)

def execute_query(query):
    conn = sqlite3.connect('test_db.db')
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    conn.close()
    return result

start_server = websockets.serve(handle_message, 'localhost', 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()

