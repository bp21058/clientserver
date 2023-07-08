import asyncio
import websockets

async def send_message():
    async with websockets.connect('ws://localhost:8765') as websocket:
        while True:
            print("1: Login, 2: Sign up, 3: Deback, 4: Quit")
            message = input("Enter a command (or 'exit' to quit): ")
            if message == 'exit':
                break
            elif message == '1':
                print("Login")
                username = input("Enter username: ")
                password = input("Enter password: ")
                
                message = "SELECT COUNT(*) FROM Classroom WHERE username ='" + username + "';"
                await websocket.send(message)
                response = await websocket.recv()
                
                if response == "[(1,)]":
                    message = "SELECT password FROM Classroom WHERE username ='" + username + "';"
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
                username = input("Enter username: ")
                password = input("Enter password: ")

                message = "SELECT COUNT(*) FROM Classroom WHERE username ='" + username + "';"
                await websocket.send(message)
                response = await websocket.recv()

                if response == "[(0,)]":
                    message = "SELECT COUNT(*) FROM Classroom;"
                    await websocket.send(message)
                    response = await websocket.recv()
                    # print(response[2])
                
                    message = "INSERT INTO Classroom VALUES ( " + str(int(response[2])+1) + ", 5261, '" + username + "', '" + password + "');"
                    await websocket.send(message)
                    response = await websocket.recv()
                    print("Sign up Success!")
                else:
                    print("This username is already used. Please try again.")

            elif message == '3':
                print("Deback")
                message = "SELECT * FROM Classroom;"
                await websocket.send(message)
                response = await websocket.recv()
                print(response)

            elif message == '4':
                print("Quit")
                break
            
            else:
                print("Invalid command. Please try again.")

asyncio.get_event_loop().run_until_complete(send_message())
