from turtle import title

from docutils.nodes import description
from nicegui import ui

from . import doc

@doc.demo(ui.rich_text_editor)
def main_demo() -> None:
    ui.rich_text_editor('<p>Hello, <strong>world!</strong></p>').classes('h-full w-full border')


@doc.demo('Collaborative editing', '''
Two or more clients sharing the same ``doc_id`` edit the same document
in real time without any external server.
Open this demo in two browser tabs to see collaboration in action.
''')
def collab_demo() -> None:
    ui.label('Open a second tab and start typing, changes appear instantly.').classes('text-sm text-gray-500')
    ui.rich_text_editor("", doc_id='shared-room').classes('h-full w-full border')


@doc.demo('Named users with colored cursors', '''
Pass a ``user`` dict with a ``name`` and ``color`` to show collaborators'
cursor positions and names inside the editor.
''')
def user_demo() -> None:
    with ui.row():
        name = ui.input("Input your name", value="")
        color = ui.color_input("Select your color")
    ui.button("join room").on_click(lambda: join_room(name.value, color.value))

def join_room(name: str, color):
    print(type(color))
    ui.rich_text_editor("", doc_id='named-room', user={'name': name, 'color': color}).classes('h-full w-full border')


# NOTE The states requires the ``y-py`` package: ``pip install y-py``
@doc.demo('Persistence with get_state / set_state', '''
``get_state()`` returns raw Yjs binary bytes that can be stored in any database
(e.g. MongoDB, Redis, or a file).  ``set_state()`` restores and broadcasts the
state to all connected clients.
''')
def persistence_demo() -> None:
    saved: dict = {}
    editor = ui.rich_text_editor('<p>Editable content</p>', doc_id='persist-demo').classes('h-full w-full border')

    def save():
        saved['data'] = editor.get_state()
        ui.notify('State saved!')

    def restore():
        if 'data' in saved:
            editor.set_state(saved['data'])
            ui.notify('State restored!')
        else:
            ui.notify('Nothing saved yet.', type='warning')

    with ui.row():
        ui.button('Save', on_click=save)
        ui.button('Restore', on_click=restore)


doc.reference(ui.rich_text_editor)
