import unittest
from io import StringIO
import asyncio
import aiosqlite

from working_server import (
    create_user, create_client, add_current_connection, remove_current_connection,
    clear_current_connections, client_exists, remove_virtual_machine,
    update_client_info, list_ever_connected_clients, list_current_connections,
    get_total_stats, handle_remove_virtual_machine, handle_update_client_info,
    handle_list_ever_connected_clients, handle_list_current_connections,
    handle_total_stats, handle_list_hard_disks
)


class TestYourCode(unittest.TestCase):

    def setUp(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Создаем асинхронное подключение
        self.db_connection = loop.run_until_complete(aiosqlite.connect(":memory:"))
        self.db_cursor = loop.run_until_complete(self.db_connection.cursor())
        self.stdout = StringIO()

    def tearDown(self):
        asyncio.run(self.db_cursor.close())
        asyncio.run(self.db_connection.close())

    async def run_command(self, command, input_data=None):
        reader = asyncio.StreamReader()
        reader_protocol = asyncio.StreamReaderProtocol(reader)
        reader_transport, _ = await asyncio.connect_read_pipe(lambda: reader_protocol, asyncio.StreamWriter)

        writer = asyncio.StreamWriter(self.stdout, None, None, None)
        writer_transport = asyncio.BufferedWriter(writer)

        if input_data:
            writer.write(input_data.encode())

        await command(reader, writer)

        writer_transport.close()
        await writer_transport.wait_closed()

        return self.stdout.getvalue()

    async def test_create_user(self):
        await create_user("test_user", "test_id")
        self.assertTrue(await client_exists("test_id"))

    async def test_create_client(self):
        await create_client("test_id", "2GB", "2", "500GB", "hdd_001")
        self.assertTrue(await client_exists("test_id"))

    async def test_add_remove_current_connection(self):
        await add_current_connection("test_id")
        self.assertTrue(await client_exists("test_id"))
        await remove_current_connection("test_id")
        self.assertFalse(await client_exists("test_id"))

    async def test_clear_current_connections(self):
        await add_current_connection("test_id")
        await clear_current_connections()
        self.assertFalse(await client_exists("test_id"))

    async def test_remove_virtual_machine(self):
        await create_user("test_user", "test_id")
        await create_client("test_id", "2GB", "2", "500GB", "hdd_001")
        await add_current_connection("test_id")
        await remove_virtual_machine("test_id")
        self.assertFalse(await client_exists("test_id"))

    async def test_update_client_info(self):
        await create_client("test_id", "2GB", "2", "500GB", "hdd_001")
        await update_client_info("test_id", "4GB", "4", "1TB", "hdd_002")
        client_info = await list_ever_connected_clients()
        self.assertEqual(client_info[0][2], "4GB")
        self.assertEqual(client_info[0][3], "4")
        self.assertEqual(client_info[0][4], "1TB")
        self.assertEqual(client_info[0][5], "hdd_002")

    async def test_list_ever_connected_clients(self):
        await create_user("test_user", "test_id")
        await create_client("test_id", "2GB", "2", "500GB", "hdd_001")
        await add_current_connection("test_id")
        result = await self.run_command(handle_list_ever_connected_clients)
        self.assertIn("Username: test_user", result)
        self.assertIn("Client ID: test_id", result)

    async def test_list_current_connections(self):
        await create_user("test_user", "test_id")
        await create_client("test_id", "2GB", "2", "500GB", "hdd_001")
        await add_current_connection("test_id")
        result = await self.run_command(handle_list_current_connections)
        self.assertIn("Username: test_user", result)
        self.assertIn("Client ID: test_id", result)

    async def test_total_stats(self):
        await create_client("test_id", "2GB", "2", "500GB", "hdd_001")
        await add_current_connection("test_id")
        result = await self.run_command(handle_total_stats)
        self.assertIn("Total machines: 1", result)
        self.assertIn("Total RAM: 2GB", result)
        self.assertIn("Total CPU: 2", result)

    async def test_handle_remove_virtual_machine(self):
        await create_user("test_user", "test_id")
        await create_client("test_id", "2GB", "2", "500GB", "hdd_001")
        await add_current_connection("test_id")
        result = await self.run_command(handle_remove_virtual_machine, "test_id\n")
        self.assertIn("Removing your own virtual machine. Disconnecting...", result)

    async def test_handle_update_client_info(self):
        await create_client("test_id", "2GB", "2", "500GB", "hdd_001")
        result = await self.run_command(handle_update_client_info, "test_id\n4GB\n4\n1TB\nhdd_002\n")
        self.assertIn("Client information updated", result)

    async def test_handle_list_ever_connected_clients(self):
        await create_user("test_user", "test_id")
        await create_client("test_id", "2GB", "2", "500GB", "hdd_001")
        await add_current_connection("test_id")
        result = await self.run_command(handle_list_ever_connected_clients)
        self.assertIn("Username: test_user", result)
        self.assertIn("Client ID: test_id", result)

    async def test_handle_list_current_connections(self):
        await create_user("test_user", "test_id")
        await create_client("test_id", "2GB", "2", "500GB", "hdd_001")
        await add_current_connection("test_id")
        result = await self.run_command(handle_list_current_connections)
        self.assertIn("Username: test_user", result)
        self.assertIn("Client ID: test_id", result)

    async def test_handle_total_stats(self):
        await create_client("test_id", "2GB", "2", "500GB", "hdd_001")
        await add_current_connection("test_id")
        result = await self.run_command(handle_total_stats)
        self.assertIn("Total machines: 1", result)
        self.assertIn("Total RAM: 2GB", result)
        self.assertIn("Total CPU: 2", result)

    async def test_handle_list_hard_disks(self):
        await create_user("test_user", "test_id")
        await create_client("test_id", "2GB", "2", "500GB", "hdd_001")
        await add_current_connection("test_id")
        result = await self.run_command(handle_list_hard_disks)
        self.assertIn("Username: test_user", result)
        self.assertIn("HDD Size: 500GB", result)


if __name__ == '__main__':
    unittest.main()
