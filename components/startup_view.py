import flet as ft
from utils.network import get_local_ip

on_host_click = None
on_join_click = None


username_input = ft.TextField(
    label="Your Username",
    hint_text="e.g., mas iyan",
    autofocus=True,
    border_radius=20,
    filled=True,
    border_color="transparent",
)
ip_input = ft.TextField(
    label="Peer IP Address",
    hint_text="e.g., 192.168.1.5",
    border_radius=20,
    filled=True,
    border_color="transparent",
)

port_input_host = ft.TextField(
    label="Port",
    value="8765",
    border_radius=20,
    filled=True,
    border_color="transparent",
)
port_input_join = ft.TextField(
    label="Port",
    value="8765",
    border_radius=20,
    filled=True,
    border_color="transparent",
)

port_input = port_input_host 

error_text = ft.Text(color="red", text_align=ft.TextAlign.CENTER)

def StartupView() -> ft.Container:
    """Returns the UI for the startup screen."""

    def on_tab_change(e):
        global port_input
        if e.control.selected_index == 0:  
            port_input = port_input_host
        else: 
            port_input = port_input_join

    host_tab_content = ft.Container(
        content=ft.Column(
            [
                ft.Text(f"Your IP is: {get_local_ip()}", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, size=16),
                ft.Text("Share this IP and Port with your peer.", text_align=ft.TextAlign.CENTER),
                port_input_host,
                ft.FilledButton("Start Hosting", on_click=lambda e: on_host_click(e) if on_host_click else None, width=200, icon=ft.Icons.PODCASTS_ROUNDED)
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.only(top=20)
    )

    join_tab_content = ft.Container(
        content=ft.Column(
            [
                ip_input,
                port_input_join,
                ft.FilledButton("Connect", on_click=lambda e: on_join_click(e) if on_join_click else None, width=200, icon=ft.Icons.SWAP_HORIZ_ROUNDED)
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        padding=ft.padding.only(top=20)
    )

    tabs = ft.Tabs(
        selected_index=0,
        on_change=on_tab_change,
        tabs=[
            ft.Tab(text="Host Chat", content=host_tab_content, icon=ft.Icons.ROUTER_ROUNDED),
            ft.Tab(text="Join Chat", content=join_tab_content, icon=ft.Icons.GROUP_ADD_ROUNDED),
        ],
        expand=True,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("P2P Encrypted Messenger", size=24, weight=ft.FontWeight.BOLD),
                username_input,
                error_text,
                tabs,
            ],
            spacing=15,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=400,
        ),
        alignment=ft.alignment.center,
        expand=True,
        padding=20,
    )
