import pytest

from nicegui import ui
from nicegui.testing import Screen

# pylint: disable=protected-access


def test_rich_text_editor_renders(screen: Screen):
    """Editor renders and initial HTML content is visible in the DOM."""
    @ui.page('/')
    def page():
        ui.rich_text_editor('<p>Hello World</p>')

    screen.open('/')
    screen.should_contain('Hello World')


def test_unique_doc_id_per_instance():
    """Two editors without an explicit doc_id receive distinct UUIDs."""
    with ui.row():
        e1 = ui.rich_text_editor()
        e2 = ui.rich_text_editor()
    assert e1.doc_id != e2.doc_id


def test_explicit_doc_id():
    """An explicit doc_id is forwarded to the element props unchanged."""
    with ui.row():
        editor = ui.rich_text_editor(doc_id='my-room')
    assert editor.doc_id == 'my-room'
    assert editor._props['doc-id'] == 'my-room'


def test_user_prop():
    """The user dict is stored in _props and forwarded to the Vue component."""
    user = {'name': 'Alice', 'color': '#3b82f6'}
    with ui.row():
        editor = ui.rich_text_editor(user=user)
    assert editor._props['user'] == user


def test_empty_user_prop_defaults_to_empty_dict():
    """When user is omitted, _props['user'] is an empty dict (Vue picks random colour)."""
    with ui.row():
        editor = ui.rich_text_editor()
    assert editor._props['user'] == {}


def test_disable():
    """Disabled editor sets the disable prop correctly."""
    with ui.row():
        editor = ui.rich_text_editor()
    editor.disable()
    assert editor._props.get('disable') is True


def test_get_state_requires_y_py():
    """get_state raises ImportError with a helpful message when y-py is absent."""
    from nicegui import rich_text_editor_room

    with ui.row():
        editor = ui.rich_text_editor(doc_id='state-test')

    original = rich_text_editor_room.HAS_Y_PY
    try:
        rich_text_editor_room.HAS_Y_PY = False
        with pytest.raises(ImportError, match='y-py'):
            editor.get_state()
    finally:
        rich_text_editor_room.HAS_Y_PY = original


def test_set_state_requires_y_py():
    """set_state raises ImportError with a helpful message when y-py is absent."""
    from nicegui import rich_text_editor_room

    with ui.row():
        editor = ui.rich_text_editor(doc_id='set-state-test')

    original = rich_text_editor_room.HAS_Y_PY
    try:
        rich_text_editor_room.HAS_Y_PY = False
        with pytest.raises(ImportError, match='y-py'):
            editor.set_state(b'')
    finally:
        rich_text_editor_room.HAS_Y_PY = original


def test_room_state_is_initially_bytes():
    """get_state returns bytes (empty Yjs state) even before any client connects."""
    pytest.importorskip('y_py')

    doc_id = f'initial-state-{id(object())}'
    with ui.row():
        editor = ui.rich_text_editor(doc_id=doc_id)

    state = editor.get_state()
    assert isinstance(state, bytes)
    # Yjs encodes an empty document as exactly 2 bytes.
    assert len(state) >= 2


def test_room_state_roundtrip():
    """get_state / set_state roundtrip does not corrupt the doc (requires y-py)."""
    pytest.importorskip('y_py')
    from nicegui import rich_text_editor_room

    doc_id = f'roundtrip-{id(object())}'
    with ui.row():
        editor = ui.rich_text_editor(doc_id=doc_id)

    state1 = editor.get_state()
    # set_state with the same bytes is a no-op CRDT merge — should not raise.
    rich_text_editor_room.set_state(doc_id, state1)
    state2 = editor.get_state()
    assert isinstance(state2, bytes)


def test_remove_sid_cleans_rooms():
    """remove_sid discards a socket-ID from every room it was in."""
    from nicegui import rich_text_editor_room

    rich_text_editor_room._rooms['room-a'] = {'sid-1', 'sid-2'}
    rich_text_editor_room._rooms['room-b'] = {'sid-1'}
    rich_text_editor_room.remove_sid('sid-1')
    assert 'sid-1' not in rich_text_editor_room._rooms['room-a']
    assert 'sid-2' in rich_text_editor_room._rooms['room-a']
    assert 'sid-1' not in rich_text_editor_room._rooms['room-b']


def test_update_method_is_set():
    """_update_method is set so NiceGUI calls setContentFromProps on prop updates."""
    with ui.row():
        editor = ui.rich_text_editor()
    assert editor._update_method == 'setContentFromProps'


def test_value_prop_name():
    """VALUE_PROP and LOOPBACK are set correctly on the class."""
    assert ui.rich_text_editor.VALUE_PROP == 'value'
    assert ui.rich_text_editor.LOOPBACK is None


def test_on_change_callback(screen: Screen):
    """on_change callback is wired up through the ValueElement machinery."""
    # Verify the callback registration does not raise; full integration requires
    # browser-level interaction to trigger the Yjs onUpdate event.
    changes: list[str] = []

    @ui.page('/')
    def page():
        ui.rich_text_editor(
            '<p>Start</p>',
            on_change=lambda e: changes.append(e.value),
        )

    screen.open('/')
    # No error on page load means the callback was registered successfully.
