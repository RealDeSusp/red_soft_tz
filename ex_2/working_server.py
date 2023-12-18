import asyncio
import aiosqlite
import uuid

# Имя базы данных
DATABASE_NAME = "clients.db"


# Функция для создания нового пользователя
async def create_user(username, client_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT INTO users (username, client_id) VALUES (?, ?)",
            (username, client_id)
        )
        await db.commit()


# Функция для создания нового клиента (виртуальной машины)
async def create_client(client_id, ram_size, cpu_count, hdd_size, hdd_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT INTO clients (client_id, ram_size, cpu_count, hdd_size, hdd_id) VALUES (?, ?, ?, ?, ?)",
            (client_id, ram_size, cpu_count, hdd_size, hdd_id)
        )
        await db.commit()


# Функция для добавления текущего подключения
async def add_current_connection(client_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "INSERT INTO current_connections (client_id) VALUES (?)",
            (client_id,)
        )
        await db.commit()


# Функция для удаления текущего подключения
async def remove_current_connection(client_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            "DELETE FROM current_connections WHERE client_id = ?",
            (client_id,)
        )
        await db.commit()


# Функция для очистки текущих подключений
async def clear_current_connections():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute("DELETE FROM current_connections")
        await db.commit()


# Функция для проверки существования клиента
async def client_exists(client_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM clients WHERE client_id = ?", (client_id,))
        count = await cursor.fetchone()
        await cursor.close()

    return count[0] > 0


# Обработчик удаления виртуальной машины
async def handle_remove_virtual_machine(reader, writer, client_id):
    writer.write(b"Enter client_id to remove the virtual machine: ")
    await writer.drain()
    client_id_to_remove = (await reader.readuntil(b'\n')).decode().strip()

    if client_id == client_id_to_remove:
        writer.write(b"Removing your own virtual machine. Disconnecting...\r\n")
        await writer.drain()
        await remove_current_connection(client_id)
        await remove_virtual_machine(client_id_to_remove)
        writer.close()
    else:
        # Check if the provided client_id exists
        if await client_exists(client_id_to_remove):
            await remove_virtual_machine(client_id_to_remove)
            writer.write(b"Virtual machine removed\r\n")
            await writer.drain()
        else:
            writer.write(b"Error: No virtual machine found with the provided client_id\r\n")
            await writer.drain()


# Функция для удаления виртуальной машины
async def remove_virtual_machine(client_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        # Remove from clients table
        await db.execute("DELETE FROM clients WHERE client_id = ?", (client_id,))
        # Remove from users table
        await db.execute("DELETE FROM users WHERE client_id = ?", (client_id,))
        await db.commit()


# Обработчик обновления информации о клиенте
async def handle_update_client_info(reader, writer):
    writer.write(b"Enter client_id to update client information: ")
    await writer.drain()
    client_id_to_update = (await reader.readuntil(b'\n')).decode().strip()

    writer.write(b"Enter new RAM size: ")
    await writer.drain()
    new_ram_size = (await reader.readuntil(b'\n')).decode().strip()

    writer.write(b"Enter new CPU count: ")
    await writer.drain()
    new_cpu_count = (await reader.readuntil(b'\n')).decode().strip()

    writer.write(b"Enter new HDD size: ")
    await writer.drain()
    new_hdd_size = (await reader.readuntil(b'\n')).decode().strip()

    writer.write(b"Enter new HDD ID: ")
    await writer.drain()
    new_hdd_id = (await reader.readuntil(b'\n')).decode().strip()

    await update_client_info(client_id_to_update, new_ram_size, new_cpu_count, new_hdd_size, new_hdd_id)

    writer.write(b"Client information updated\r\n")
    await writer.drain()


# Функция для получения списка жестких дисков
async def list_hard_disks():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute(
            """
            SELECT u.username, c.hdd_size
            FROM users u
            JOIN clients c ON u.client_id = c.client_id
            """
        )
        hard_disks = await cursor.fetchall()
        await cursor.close()

    return hard_disks


# Обработчик вывода списка жестких дисков
async def handle_list_hard_disks(reader, writer):
    writer.write(b"List of hard disks:\r\n")
    await writer.drain()

    hard_disks = await list_hard_disks()

    for disk in hard_disks:
        disk_info = f"Username: {disk[0]}, HDD Size: {disk[1]}\r\n"
        writer.write(disk_info.encode())
        await writer.drain()

    writer.write(b"End of the list\r\n")
    await writer.drain()


# Функция для получения списка всех подключенных клиентов
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


# Обработчик вывода списка всех подключенных клиентов
async def handle_list_ever_connected_clients(reader, writer):
    writer.write(b"List of ever connected clients:\r\n")
    await writer.drain()

    clients = await list_ever_connected_clients()

    for client in clients:
        client_info = f"Username: {client[0]}, Client ID: {client[1]}, RAM: {client[2]}, CPU: {client[3]}, HDD Size: " \
                      f"{client[4]}, HDD ID: {client[5]}\r\n "
        writer.write(client_info.encode())
        await writer.drain()

    writer.write(b"End of the list\r\n")
    await writer.drain()


# Функция для получения списка текущих подключений
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


# Обработчик вывода списка текущих подключений
async def handle_list_current_connections(reader, writer):
    writer.write(b"List of currently connected clients:\r\n")
    await writer.drain()

    current_connections = await list_current_connections()

    for connection in current_connections:
        connection_info = f"Username: {connection[0]}, Client ID: {connection[1]}, RAM: {connection[2]}, CPU: " \
                          f"{connection[3]}, HDD Size: {connection[4]}, HDD ID: {connection[5]}\r\n"
        writer.write(connection_info.encode())
        await writer.drain()

    writer.write(b"End of the list\r\n")
    await writer.drain()


# Функция для обновления информации о клиенте
async def update_client_info(client_id, ram_size, cpu_count, hdd_size, hdd_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(
            """
            UPDATE clients
            SET ram_size = ?, cpu_count = ?, hdd_size = ?, hdd_id = ?
            WHERE client_id = ?
            """,
            (ram_size, cpu_count, hdd_size, hdd_id, client_id)
        )
        await db.commit()


# Функция для получения общей статистики
async def get_total_stats():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        # Получаем общее количество машин
        cursor = await db.execute("SELECT COUNT(*) FROM clients")
        total_machines = await cursor.fetchone()
        await cursor.close()

        # Получаем общий объем RAM и CPU
        cursor = await db.execute("SELECT SUM(ram_size), SUM(cpu_count) FROM clients")
        total_stats = await cursor.fetchone()
        await cursor.close()

    return total_machines[0], total_stats[0], total_stats[1]


# Обработчик вывода общей статистики
async def handle_total_stats(reader, writer):
    total_machines, total_ram, total_cpu = await get_total_stats()
    stats_message = f"Total machines: {total_machines}, Total RAM: {total_ram}, Total CPU: {total_cpu}\r\n"
    writer.write(stats_message.encode())
    await writer.drain()


# Обработчик основного потока клиента
async def handle_client(reader, writer):
    # Запрашиваем у клиента ввод имени пользователя
    writer.write(b"Enter your username: ")
    await writer.drain()

    # Считываем введенное имя пользователя
    username = (await reader.readuntil(b'\n')).decode().strip()

    # Проверяем, существует ли пользователь в базе данных
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM users WHERE username = ?",
            (username,)
        )
        user_exists = await cursor.fetchone()
        await cursor.close()

    # Если пользователь существует, получаем его идентификатор
    if user_exists[0] > 0:
        async with aiosqlite.connect(DATABASE_NAME) as db:
            cursor = await db.execute(
                "SELECT client_id FROM users WHERE username = ?",
                (username,)
            )
            client_id = await cursor.fetchone()
            await cursor.close()
        client_id = client_id[0]
        # Сообщаем, что пользователь найден, идет подключение к виртуальной машине
        writer.write(b"User found. Connecting to virtual machine...\r\n")
        await writer.drain()
    else:
        # Если пользователь не существует, создаем нового пользователя и его виртуальную машину
        client_id = str(uuid.uuid4())
        await create_user(username, client_id)

        writer.write(b"User not found. Creating virtual machine...\r\n")
        await writer.drain()

        # Запрашиваем у пользователя информацию о виртуальной машине (RAM, CPU, HDD)
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

        # Создаем виртуальную машину для нового пользователя
        await create_client(client_id, ram_size, cpu_count, hdd_size, hdd_id)

        writer.write(b"Client information saved\r\n")
        await writer.drain()

    # Сообщаем об успешной аутентификации
    writer.write(b"Authentication successful\r\n")
    await writer.drain()

    # Добавляем текущее соединение в список активных соединений
    await add_current_connection(client_id)

    while True:
        # Выводим меню команд для пользователя
        writer.write(b"Type 'list_of_users_ever_connected' to see the list of ever connected clients\r\n")
        writer.write(b"Type 'list_of_current_connections' to see the list of currently connected clients\r\n")
        writer.write(b"Type 'list_of_hard_disks' to see the list of hard disks\r\n")
        writer.write(b"Type 'remove_virtual_machine' to remove a virtual machine\r\n")
        writer.write(b"Type 'update_client_info' to update client information\r\n")
        writer.write(b"Type 'list_total_stats' to see the total statistics\r\n")
        writer.write(b"Type 'exit' to exit\r\n")
        await writer.drain()

        # Считываем команду пользователя
        command = (await reader.readuntil(b'\n')).decode().strip()

        # Обработка команд
        if command.lower() == 'list_of_users_ever_connected':
            await handle_list_ever_connected_clients(reader, writer)
        elif command.lower() == 'list_of_current_connections':
            await handle_list_current_connections(reader, writer)
        elif command.lower() == 'list_of_hard_disks':
            await handle_list_hard_disks(reader, writer)
        elif command.lower() == 'remove_virtual_machine':
            await handle_remove_virtual_machine(reader, writer, client_id)
        elif command.lower() == 'update_client_info':
            await handle_update_client_info(reader, writer, client_id)
        elif command.lower() == 'list_total_stats':
            await handle_total_stats(reader, writer)
        # Выход из цикла и сервера при вводе команды 'exit'
        elif command.lower() == 'exit':
            # Удаляем текущее соединение из списка активных соединений
            await remove_current_connection(client_id)
            writer.write(b"Disconnecting...\r\n")
            await writer.drain()
            writer.close()
            break
        else:
            # Отправляем сообщение об ошибке при вводе неизвестной команды
            writer.write(b"Error: Unknown command\r\n")
            await writer.drain()


# Основная асинхронная функция
async def main():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        # Создаем таблицы, если они не существуют
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

    # Очищаем текущие подключения перед запуском сервера
    await clear_current_connections()

    # Запускаем сервер на указанном адресе и порте
    server = await asyncio.start_server(
        handle_client, '127.0.0.1', 8888)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()

# Запуск основной асинхронной функции
if __name__ == "__main__":
    asyncio.run(main())
