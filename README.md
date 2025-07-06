
# Terminal Server

The Terminal Server project is a lightweight Telnet proxy designed to multiplex a single Telnet session across multiple clients. It addresses a common limitation in network environments where a remote device (such as a router, switch, or virtual appliance) allows only one active Telnet connection at a time. In such scenarios, if a single user occupies the Telnet session, other users are blocked from access. This hinders collaborative workflows, real-time monitoring, and shared debugging efforts.

The Terminal Server solves this problem by acting as an intermediary between the remote Telnet server and multiple local clients. It connects to the target Telnet server once and then allows multiple users to attach to that single session via a local port. Each connected user sees the same terminal output in real time, and their input is sent back to the remote device. This enables:

- **Collaborative Access**: Multiple engineers can share a session for live troubleshooting or demonstrations.

- **Session Replication**: All interactions with the Telnet server are mirrored to connected clients, useful for observation and training.

- **Debugging and Monitoring**: Automated systems or humans can attach to monitor ongoing operations without interfering with the primary session.

- **Access Control**: The local proxy interface can restrict or log user access, enabling basic auditing.

The solution is built with standard Python libraries like `socket`, `select`, and `threading`, making it easy to deploy and extend. It dynamically allocates a local port for clients and handles Telnet negotiation commands to ensure compatibility with common Telnet clients.

## Getting Started

Typical usage involves launching the proxy to connect to a remote Telnet server and then connecting locally.

This connects to a remote Telnet server at `1.2.3.4:1234` and assigns a random available local port for client access.

    python3 terminal_server.py -r 1.2.3.4 -p 1234

After starting, it will display something like:

    >>>>>>>>> connect with: telnet localhost 47631 <<<<<<<<<

Users can then connect via:

    telnet localhost 47631

You can explicitly binds the local proxy server to a port, so clients always know where to connect.

    python3 terminal_server.py -r 1.2.3.4 -p 1234 -l 4679

## Demo

In this demo, the terminal_server connects to a remote Telnet server, creating a shared terminal session. Two different users connect to the local terminal server using Telnet. Any command entered by one user and its output is mirrored across all connected terminals, enabling real-time collaboration, monitoring, and debugging.

[demo.mp4](https://github.com/user-attachments/assets/ec6ff95b-94d5-42eb-b19f-09a14ea5cc18)
