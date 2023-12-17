import asyncio
import aiosqlite

DATABASE_NAME = "clients.db"


async def authenticate(reader, writer):
    writer.write(b"Enter your username: ")
    await writer.drain()

    username = (await reader.readuntil(b'\n')).decode().strip()

    # Check if the username already exists in the database
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute("SELECT * FROM clients WHERE user_name=?", (username,))
        existing_user = await cursor.fetchone()

    if existing_user:
        writer.write(b"User already exists. Authentication successful\n")
        await writer.drain()
        return True
    else:
        # Perform logic to create a new user or any other authentication logic
        writer.write(b"New user created. Authentication successful\n")
        await writer.drain()

        # Add the new user to the database
        async with aiosqlite.connect(DATABASE_NAME) as db:
            await db.execute(
                "INSERT INTO clients (user_name) VALUES (?)",
                (username,)
            )
            await db.commit()

        return True


async def handle_client(reader, writer):
    authenticated = await authenticate(reader, writer)

    if not authenticated:
        writer.close()
        return

    username = authenticated.username

    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute("SELECT * FROM clients WHERE user_name=?", (username,))
        existing_user = await cursor.fetchone()
    # Check if the user already exists
    user_info = await get_user_info(authenticated)

    if user_info:
        writer.write(b"User already exists. Authentication successful\n")
        await writer.drain()
    else:
        # If the user does not exist, create a new user
        writer.write(b"New user created. Authentication successful\n")
        await writer.drain()

        # Read client information
        writer.write(b"Enter your ID: ")
        await writer.drain()
        client_id = (await reader.readuntil(b'\n')).decode().strip()

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

        # Store client information in the database
        async with aiosqlite.connect(DATABASE_NAME) as db:
            await db.execute(
                """
                INSERT INTO clients (user_name, client_id, ram_size, cpu_count, hdd_size, hdd_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (authenticated, client_id, ram_size, cpu_count, hdd_size, hdd_id)
            )
            await db.commit()

        writer.write(b"Client information saved\n")
        await writer.drain()


async def main():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                user_name TEXT PRIMARY KEY,
                client_id TEXT,
                ram_size TEXT,
                cpu_count TEXT,
                hdd_size TEXT,
                hdd_id TEXT
            )
            """
        )
        await db.commit()

    server = await asyncio.start_server(
        handle_client, '127.0.0.1', 8888)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

asyncio.run(main())
