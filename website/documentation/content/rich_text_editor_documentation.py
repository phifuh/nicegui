from nicegui import ui

from . import doc

@doc.demo(ui.rich_text_editor)
def main_demo() -> None:
    ui.rich_text_editor('<p>Hello, <strong>world!</strong></p>').classes('h-full w-full border')


@doc.demo('Custom toolbar', '''
Pass a list of lists to ``toolbar`` to control which buttons appear and how
they are grouped (each inner list becomes a button group with a separator).
Use ``toolbar=False`` to hide the toolbar entirely.
''')
def toolbar_demo() -> None:
    ui.rich_text_editor('<p>Minimal toolbar</p>', toolbar=[
        ['bold', 'italic', 'underline'],
        ['bullet_list', 'ordered_list'],
        ['undo', 'redo'],
    ]).classes('h-full w-full border')


@doc.demo('Available toolbar buttons', '''
Every button has a string ID that you use when building a custom toolbar.
The editor below shows all of them at once.

**Inline formatting** — ``bold``, ``italic``, ``underline``, ``strike``, ``code``

**Headings** — ``heading`` (dropdown: Normal / H1 / H2 / H3), or individual buttons ``h1``, ``h2``, ``h3``

**Lists** — ``bullet_list``, ``ordered_list``

**Blocks** — ``blockquote``, ``code_block``, ``table``, ``hr``

**History** — ``undo``, ``redo``
''')
def all_buttons_demo() -> None:
    ui.rich_text_editor('<p>Try every button above.</p>', toolbar=[
        ['bold', 'italic', 'underline', 'strike', 'code'],
        ['heading', 'h1', 'h2', 'h3'],
        ['bullet_list', 'ordered_list'],
        ['blockquote', 'code_block'],
        ['table', 'hr'],
        ['undo', 'redo'],
    ]).classes('h-full w-full border')


@doc.demo('Tables', '''
The editor supports multi-column tables with a header row out of the box.
Use the ``table`` toolbar button to insert a new 3×3 table, or supply
initial HTML with a ``<table>`` element.
Clicking inside a table reveals an *Edit table* dropdown for adding or
removing rows and columns, or deleting the whole table.
Tab / Shift-Tab navigates between cells; cell content supports all inline
formatting (bold, italic, etc.).
''')
def table_demo() -> None:
    ui.rich_text_editor(
        '<table>'
        '<thead><tr><th>Name</th><th>Role</th><th>Status</th></tr></thead>'
        '<tbody>'
        '<tr><td>Alice</td><td>Engineer</td><td>Active</td></tr>'
        '<tr><td>Bob</td><td>Designer</td><td>On leave</td></tr>'
        '</tbody>'
        '</table>',
        toolbar=[['bold', 'italic'], ['table'], ['undo', 'redo']], 
        doc_id='shared-table'
    ).classes('h-full w-full border')


@doc.demo('Collaborative editing', '''
Two or more clients sharing the same ``doc_id`` edit the same document
in real time without any external server.
Open this demo in two browser tabs to see collaboration in action.
''')
def collab_demo() -> None:
    ui.label('Open a second tab and start typing, changes appear instantly.').classes('text-sm text-gray-500')
    ui.rich_text_editor("", doc_id='shared-room', ).classes('h-full w-full border')


@doc.demo('Named users with colored cursors', '''
Pass a ``user`` dict with a ``name`` and ``color`` to show collaborators\'
cursor positions and names inside the editor.
''')
def user_demo() -> None:
    def join_room(name: str, color: str) -> None:
        ui.rich_text_editor("", doc_id='named-room', user={'name': name, 'color': color}).classes('h-full w-full border')

    with ui.row():
        name = ui.input("Input your name", value="")
        color = ui.color_input("Select your color")
    ui.button("join room").on_click(lambda: join_room(name.value, color.value))


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
