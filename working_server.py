import asyncio
import aiosqlite
import uuid

DATABASE_NAME = "clients.db"


async def create_user(username, client_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT INTO users (username, client_id) VALUES (?, ?)",
            (username, client_id)
        )
        await db.commit()


async def create_client(client_id, ram_size, cpu_count, hdd_size, hdd_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT INTO clients (client_id, ram_size, cpu_count, hdd_size, hdd_id) VALUES (?, ?, ?, ?, ?)",
            (client_id, ram_size, cpu_count, hdd_size, hdd_id)
        )
        await db.commit()


async def add_current_connection(client_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT INTO current_connections (client_id) VALUES (?)",
            (client_id,)
        )
        await db.commit()


async def remove_current_connection(client_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "DELETE FROM current_connections WHERE client_id = ?",
            (client_id,)
        )
        await db.commit()


async def clear_current_connections():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute("DELETE FROM current_connections")
        await db.commit()


async def handle_client(reader, writer):
    writer.write(b"Enter your username: ")
    await writer.drain()

    username = (await reader.readuntil(b'\n')).decode().strip()

    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM users WHERE username = ?",
            (username,)
        )
        user_exists = await cursor.fetchone()
        await cursor.close()

    if user_exists[0] > 0:
        async with aiosqlite.connect(DATABASE_NAME) as db:
            cursor = await db.execute(
                "SELECT client_id FROM users WHERE username = ?",
                (username,)
            )
            client_id = await cursor.fetchone()
            await cursor.close()
        client_id = client_id[0]
        writer.write(b"User found. Connecting to virtual machine...\r\n")
        await writer.drain()
    else:
        client_id = str(uuid.uuid4())
        await create_user(username, client_id)

        writer.write(b"User not found. Creating virtual machine...\r\n")
        await writer.drain()

        writer.write(b"Enter RAM size: ")
        await writer.drain()
        ram_size = (await reader.readuntil(b'\n')).decode().strip()

        writer.write(b"Enter CPU count: ")
        await writer.drain()
        cpu_count = (await reader.readuntil(b'\n')).decode().strip()

        writer.write(b"Enter HDD size: ")
        await writer.drain()
        hdd_size = (await reader.readuntil(b'\n')).decode().strip()

        writer.write(b"Enter HDD ID: ")
        await writer.drain()
        hdd_id = (await reader.readuntil(b'\n')).decode().strip()

        await create_client(client_id, ram_size, cpu_count, hdd_size, hdd_id)

        writer.write(b"Client information saved\r\n")
        await writer.drain()

    writer.write(b"Authentication successful\r\n")
    await writer.drain()

    # Add the current connection to the database
    await add_current_connection(client_id)

    while True:
        writer.write(b"Type 'list_of_users_ever_connected' to see the list of ever connected clients\r\n")
        writer.write(b"Type 'list_of_current_connections' to see the list of currently connected clients\r\n")
        writer.write(b"Type 'exit' to exit\r\n")
        await writer.drain()

        command = (await reader.readuntil(b'\n')).decode().strip()

        if command.lower() == 'list_of_users_ever_connected':
            await handle_list_ever_connected_clients(reader, writer)
        elif command.lower() == 'list_of_current_connections':
            await handle_list_current_connections(reader, writer)
        elif command.lower() == 'exit':
            await remove_current_connection(client_id)
            writer.write(b"Disconnecting...\r\n")
            await writer.drain()
            writer.close()
            break


async def list_ever_connected_clients():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute(
            """
            SELECT u.username, c.client_id, c.ram_size, c.cpu_count, c.hdd_size, c.hdd_id
            FROM users u
            LEFT JOIN clients c ON u.client_id = c.client_id
            """
        )
        clients = await cursor.fetchall()
        await cursor.close()

    return clients


async def handle_list_ever_connected_clients(reader, writer):
    writer.write(b"List of ever connected clients:\r\n")
    await writer.drain()

    clients = await list_ever_connected_clients()

    for client in clients:
        client_info = f"Username: {client[0]}, Client ID: {client[1]}, RAM: {client[2]}, CPU: {client[3]}, HDD Size: {client[4]}, HDD ID: {client[5]}\r\n"
        writer.write(client_info.encode())
        await writer.drain()

    writer.write(b"End of the list\r\n")
    await writer.drain()


async def list_current_connections():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute(
            """
            SELECT u.username, c.client_id, c.ram_size, c.cpu_count, c.hdd_size, c.hdd_id
            FROM users u
            JOIN clients c ON u.client_id = c.client_id
            JOIN current_connections cc ON u.client_id = cc.client_id
            """
        )
        current_connections = await cursor.fetchall()
        await cursor.close()

    return current_connections


async def handle_list_current_connections(reader, writer):
    writer.write(b"List of currently connected clients:\r\n")
    await writer.drain()

    current_connections = await list_current_connections()

    for connection in current_connections:
        connection_info = f"Username: {connection[0]}, Client ID: {connection[1]}, RAM: {connection[2]}, CPU: {connection[3]}, HDD Size: {connection[4]}, HDD ID: {connection[5]}\r\n"
        writer.write(connection_info.encode())
        await writer.drain()

    writer.write(b"End of the list\r\n")
    await writer.drain()


async def main():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                client_id TEXT UNIQUE
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                client_id TEXT PRIMARY KEY,
                ram_size TEXT,
                cpu_count TEXT,
                hdd_size TEXT,
                hdd_id TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS current_connections (
                client_id TEXT PRIMARY KEY
            )
            """
        )
        await db.commit()

    # Clear current connections before starting the server
    await clear_current_connections()

    server = await asyncio.start_server(
        handle_client, '127.0.0.1', 8888)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


asyncio.run(main())
