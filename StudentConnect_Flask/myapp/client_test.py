import asyncio
import websockets
import time

async def send_message():
    async with websockets.connect('ws://localhost:8765') as websocket:
        while True:
            print("1: Login, 2: Sign up, 3: Deback, 4: Quit")
            message = input("Enter a command: ")
            if message == 'exit':
                break
            elif message == '1':
                print("Login")
                username = input("Enter username: ")
                password = input("Enter password: ")
                
                message = "SELECT COUNT(*) FROM Class_info WHERE username ='" + username + "';"
                await websocket.send(message)
                response = await websocket.recv()
                
                if response == "[(1,)]":
                    message = "SELECT password FROM Class_info WHERE username ='" + username + "';"
                    await websocket.send(message)
                    response = await websocket.recv()
                    if response == "[('" + password + "',)]":
                        print("Login Success!")
                    else:
                        print("Password is incorrect. Please try again.")
                else:
                    print("Login Failed. You need to sign up.")

            elif message == '2':
                print("Sign up")
                username = str(input("Enter username: "))
                password = str(input("Enter password: "))
                email = str(input("Enter email: "))
                
                message = "SELECT COUNT(*) FROM Class_info WHERE username ='" + username + "';"
                await websocket.send(message)
                response = await websocket.recv()
                
                if response == "[(0,)]":
                    query = "INSERT INTO Class_info (subject, username, password, email) VALUES (?, ?, ?, ?)"
                    await websocket.send(query)
                    time.sleep(1)
                    await websocket.send(username)
                    time.sleep(1)
                    await websocket.send(password)
                    time.sleep(1)
                    await websocket.send(email)

                    response = await websocket.recv()
                    print(response)
                else:
                    print("Username is already used. Please try again.") 
            elif message == '3':
                print("Deback")
                message = "SELECT * FROM Class_info;"
                await websocket.send(message)
                response = await websocket.recv()
                print(response)

            elif message == '4':
                print("Quit")
                break
            
            else:
                print("Invalid command. Please try again.")

asyncio.get_event_loop().run_until_complete(send_message())
