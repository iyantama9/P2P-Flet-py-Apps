import flet as ft
from utils.network import get_local_ip

# Callbacks to be set by the main application logic
on_host_click = None
on_join_click = None

# UI Components that need to be accessed from the main app
username_input = ft.TextField(label="Your Username", hint_text="e.g., Andi")
ip_input = ft.TextField(label="Peer IP Address", hint_text="e.g., 192.168.1.5")
port_input = ft.TextField(label="Port", value="8765")

def StartupView() -> ft.Column:
    """Returns the UI for the startup screen."""

    host_tab_content = ft.Column([
        ft.Text(f"Your IP is: {get_local_ip()}", weight="bold"),
        ft.Text("Your peer can connect to you using your IP and Port."),
        port_input, # Re-use the same port input
        ft.ElevatedButton("Start Hosting", on_click=lambda e: on_host_click(e) if on_host_click else None)
    ])

    join_tab_content = ft.Column([
        ip_input,
        port_input, # Re-use the same port input
        ft.ElevatedButton("Connect", on_click=lambda e: on_join_click(e) if on_join_click else None)
    ])

    return ft.Column([
        ft.Text("P2P Encrypted Messenger Setup", size=20),
        username_input,
        ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Host Chat", content=host_tab_content),
                ft.Tab(text="Join Chat", content=join_tab_content),
            ]
        )
    ])
