#!/usr/bin/env python3

# Author: Mani Amoozadeh
# Email: mani.amoozadeh2@gmail.com

import sys
import socket
import queue
import select
import threading
import logging
import argparse

log = logging.getLogger(__name__)

# telnet commands
IAC = bytes([255])
DONT = bytes([254])
DO = bytes([253])
WONT = bytes([252])
WILL = bytes([251])
LINEMODE = bytes([34])
SGA = bytes([3])
ECHO = bytes([1])


class TelnetProxyServer:

    def __init__(self, remote_ip_, remote_port_, local_port_=None, local_ip="0.0.0.0"):

        if not local_port_:
            local_port_ = self.get_open_port_local()

        self.remote_ip = remote_ip_
        self.remote_port = int(remote_port_)
        self.local_port = int(local_port_)
        self.local_ip = local_ip

        self.server_socket = None
        self.remote_socket = None
        self.client_queue = queue.Queue()
        self.keep_running = True
        self.client_sockets = []


    def get_terminal_server_address(self):

        return (self.local_ip, self.local_port)


    def start_server(self, max_clients=5):

        log.info("\nStarting Terminal Server...")

        status_, output_ = self.connect_to_telnet_server()
        if not status_:
            return False, output_

        receiver_thread = threading.Thread(target=self.receive_from_telnet)
        sender_thread = threading.Thread(target=self.send_to_telnet)
        receiver_thread.start()
        sender_thread.start()

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.local_ip, self.local_port))
        except Exception as E:
            return False, str(E)

        try:
            self.server_socket.listen(max_clients)
        except Exception as E:
            return False, str(E)

        self.init_telnet()

        return True, None


    def stop_server(self):

        log.debug("Shutting down the terminal server...")

        self.keep_running = False
        self.client_queue.put(None)

        for client in self.client_sockets:
            client.close()

        self.server_socket.close()
        self.remote_socket.close()

        log.debug("All sockets were closed.")


    def listen_for_clients(self, daemon=False):

        client_thread = threading.Thread(target=self.listen_for_clients_run)
        client_thread.start()

        log.info("Listening to clients...")
        client_thread.join(3)

        if not daemon:
            client_thread.join()


    def listen_for_clients_run(self):

        timeout = 5

        while self.keep_running:

            # wait for the socket to be ready for reading (accepting connections)
            ready_to_read, _, _ = select.select([self.server_socket], [], [], timeout)

            if not ready_to_read:
                continue

            client_sock, addr = self.server_socket.accept()
            log.debug("Accepted connection from %s", addr)
            self.client_sockets.append(client_sock)
            client_thread = threading.Thread(target=self.handle_client, args=(client_sock,))
            client_thread.start()


    def connect_to_telnet_server(self, timeout=10):

        self.remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        log.info("Connecting to %s %s", self.remote_ip, self.remote_port)

        try:
            self.remote_socket.settimeout(timeout)
            addr = (self.remote_ip, self.remote_port)
            self.remote_socket.connect(addr)
            self.remote_socket.settimeout(None)
        except Exception as E:
            return False, str(E)

        log.info("Connected to the remote telnet.")

        return True, None


    def receive_from_telnet(self):

        timeout = 5

        while self.keep_running:

            try:

                # check if the socket is ready for reading
                ready_to_read, _, _ = select.select([self.remote_socket], [], [], timeout)
                if not ready_to_read:
                    continue

                data = self.remote_socket.recv(4096)
                if not data:
                    break

                self.broadcast_to_clients(data)

            except Exception as e:
                log.error("receive_from_telnet: error receiving data from Telnet server: %s", e)
                break


    def send_to_telnet(self):

        while self.keep_running:

            data = self.client_queue.get()
            if not data:
                continue

            try:
                self.remote_socket.send(data)
            except Exception as e:
                log.error("send_to_telnet: failed to send data to Telnet server: %s", e)
                self.keep_running = False


    def init_telnet(self):

        return

        data = "terminal width 0 \n"
        self.remote_socket.send(data.encode())

        data = "terminal length 0 \n"
        self.remote_socket.send(data.encode())


    def handle_client(self, client_socket):

        greeting_message = f"""
            You are connected to {self.remote_ip}:{self.local_port}
        """

        client_socket.sendall(greeting_message.encode())

        # switch mode to character
        client_socket.send(IAC + WILL + ECHO)
        client_socket.send(IAC + WILL + SGA)
        client_socket.send(IAC + WONT + LINEMODE)

        timeout = 5

        while self.keep_running:

            try:

                ready_to_read, _, _ = select.select([client_socket], [], [], timeout)
                if not ready_to_read:
                    continue

                data = client_socket.recv(1)
                if not data:
                    break

                if data == b'\x00':
                    continue

                self.client_queue.put(data)

            except:
                break

        log.debug("Client disconnected")
        client_socket.close()
        self.client_sockets.remove(client_socket)


    def broadcast_to_clients(self, data):

        for client in self.client_sockets:
            try:
                client.send(data)
            except socket.error as e:
                log.error("Failed to send data to a client: %s", e)
                client.close()
                self.client_sockets.remove(client)


    def get_open_port_local(self):
        '''
            get an available ephemeral port on 'local' host
        '''

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        s.listen(1)
        port_ = s.getsockname()[1]
        s.close()
        return port_


class TS_Parser(argparse.ArgumentParser):

    def error(self, message):
        sys.stderr.write(f'error: {message}\n')
        self.print_help()
        sys.exit(2)


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    main_parser = TS_Parser(
        description="Terminal server utility.",
        epilog="""Example usage:
        terminal_server.py -r 1.2.3.4 -p 1234
        terminal_server.py -r 1.2.3.4 -p 1234 -l 4679
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    main_parser.add_argument('-r', '--remote_ip', help='Telnet remote IP', required=True)
    main_parser.add_argument('-p', '--remote_port', help='Telnet remote port', default=23)
    main_parser.add_argument('-l', '--local_port', help='Telnet local port')
    main_parser.add_argument('--debug', help='turn on debugging', action="store_true")

    args = main_parser.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)

    proxy = TelnetProxyServer(args.remote_ip,
                              args.remote_port,
                              args.local_port)

    status, output = proxy.start_server()
    if not status:
        log.error(output)
        sys.exit(2)

    _, port = proxy.get_terminal_server_address()

    log.info(">>>>>>>>> connect with: telnet localhost %s <<<<<<<<<", port)

    try:
        # this is blocking
        proxy.listen_for_clients()
    except KeyboardInterrupt:
        log.info("\nShutting down the telnet terminal server...")
        proxy.stop_server()
        sys.exit(2)
