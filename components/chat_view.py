import flet as ft

# Callback to be set by the main application logic
on_send_message_click = None
on_typing_change = None # New callback

# UI Components that need to be accessed from the main app
messages = ft.Column(auto_scroll=True, expand=True)
new_message = ft.TextField(
    hint_text="Type a message...", 
    expand=True,
    # Call the new callback whenever the content changes
    on_change=lambda e: on_typing_change(e.data) if on_typing_change else None
)
status_text = ft.Text()
# New UI element to show the typing status of the peer
typing_indicator = ft.Text(value="", italic=True, size=12)

def ChatView() -> ft.Column:
    """Returns the UI for the main chat view."""
    
    send_button = ft.IconButton(
        icon=ft.icons.SEND, 
        on_click=lambda e: on_send_message_click(e) if on_send_message_click else None, 
        disabled=True # Initially disabled
    )
    
    ChatView.send_button = send_button

    return ft.Column([
        status_text,
        ft.Container(
            content=messages, 
            border=ft.border.all(1, "grey"), 
            border_radius=5, 
            padding=10, 
            expand=True
        ),
        typing_indicator, # Add the indicator to the layout
        ft.Row([new_message, send_button])
    ], expand=True, visible=False) # Initially hidden
