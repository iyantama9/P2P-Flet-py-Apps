import flet as ft

on_send_message_click = None
on_typing_change = None

messages = ft.ListView(
    expand=True,
    auto_scroll=True,
    spacing=10,
    padding=10,
)

new_message = ft.TextField(
    hint_text="Type a message...",
    expand=True,
    filled=True,
    border_color=ft.Colors.TRANSPARENT,
    border_radius=20,
    on_change=lambda e: on_typing_change(e.data) if on_typing_change else None,
)

status_text = ft.Text(
    weight=ft.FontWeight.BOLD,
    text_align=ft.TextAlign.CENTER,
)

typing_indicator = ft.Text(
    value="",
    italic=True,
    size=12,
    color=ft.Colors.GREY_600,
    text_align=ft.TextAlign.RIGHT
)


def ChatView() -> ft.Container:
    send_button = ft.IconButton(
        icon=ft.Icons.SEND_ROUNDED,
        tooltip="Send",
        disabled=True,
        on_click=lambda e: on_send_message_click(e) if on_send_message_click else None,
    )

    ChatView.send_button = send_button

    chat_box = ft.Container(
        content=messages,
        padding=15,
        bgcolor=ft.Colors.TRANSPARENT,
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=10,
        expand=True,  
    )

    return ft.Container(
        padding=20,
        visible=False, 
        content=ft.Column(
            spacing=12,
            expand=True,
            controls=[
                ft.Row([status_text], alignment=ft.MainAxisAlignment.CENTER),

                chat_box,

                typing_indicator,

                ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        new_message,
                        send_button,
                    ],
                ),
            ],
        ),
    )
