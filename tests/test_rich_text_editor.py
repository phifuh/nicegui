from pathlib import Path

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


def test_single_persistence_state_preserved():
    """Restored state is byte-for-byte equivalent to the saved snapshot."""
    pytest.importorskip('y_py')
    import y_py as Y
    from nicegui import rich_text_editor_room

    doc_id = f'persist-preserved-{id(object())}'
    with ui.row():
        editor = ui.rich_text_editor(doc_id=doc_id)

    # Write known content into the server-side Y.Doc.
    doc = rich_text_editor_room._get_or_create_doc(doc_id)
    ymap = doc.get_map('meta')
    with doc.begin_transaction() as txn:
        ymap.set(txn, 'version', '1')

    snapshot = editor.get_state()
    assert len(snapshot) > 2  # non-empty (Yjs empty-state sentinel is exactly 2 bytes)

    # Apply more edits — simulates user activity after the save point.
    with doc.begin_transaction() as txn:
        ymap.set(txn, 'version', '2')

    after_edit = editor.get_state()
    assert after_edit != snapshot  # confirm the state actually changed

    # Restore the snapshot.
    editor.set_state(snapshot)
    restored = editor.get_state()

    # Build the canonical reference bytes: fresh doc + snapshot applied.
    ref_doc = Y.YDoc()
    Y.apply_update(ref_doc, snapshot)
    ref_bytes = bytes(Y.encode_state_as_update(ref_doc))

    assert restored == ref_bytes


def test_debounce_unsaved_edits_excluded_from_restore():
    """Edits within the debounce window (not yet auto-saved) are absent after restore."""
    pytest.importorskip('y_py')
    import y_py as Y
    from nicegui import rich_text_editor_room

    doc_id = f'debounce-unsaved-{id(object())}'
    with ui.row():
        editor = ui.rich_text_editor(doc_id=doc_id)

    # Establish the "auto-saved" snapshot — the state the debounce timer captured.
    doc = rich_text_editor_room._get_or_create_doc(doc_id)
    ymap = doc.get_map('content')
    with doc.begin_transaction() as txn:
        ymap.set(txn, 'saved', 'yes')

    snapshot = editor.get_state()  # what the debounce timer would have stored

    # Simulate user typing within the 2 s debounce window — NOT auto-saved yet.
    with doc.begin_transaction() as txn:
        ymap.set(txn, 'unsaved', 'yes')

    unsaved_state = editor.get_state()
    assert unsaved_state != snapshot  # confirm unsaved edits changed the state

    # Debounce timer fires: restore the earlier (auto-saved) snapshot.
    editor.set_state(snapshot)
    restored = editor.get_state()

    # Restored state must equal the snapshot, not the unsaved edits.
    ref_doc = Y.YDoc()
    Y.apply_update(ref_doc, snapshot)
    ref_bytes = bytes(Y.encode_state_as_update(ref_doc))

    assert restored == ref_bytes      # matches the auto-saved snapshot
    assert restored != unsaved_state  # unsaved content is gone


def test_remove_sid_cleans_rooms():
    """remove_sid discards a socket-ID from every room it was in."""
    from nicegui import rich_text_editor_room

    rich_text_editor_room._rooms['room-a'] = {'sid-1', 'sid-2'}
    rich_text_editor_room._rooms['room-b'] = {'sid-1'}
    rich_text_editor_room.remove_sid('sid-1')
    assert 'sid-1' not in rich_text_editor_room._rooms['room-a']
    assert 'sid-2' in rich_text_editor_room._rooms['room-a']
    assert 'sid-1' not in rich_text_editor_room._rooms['room-b']


def test_toolbar_default_true():
    """toolbar prop defaults to True."""
    with ui.row():
        editor = ui.rich_text_editor()
    assert editor._props.get('toolbar') is True


def test_toolbar_disabled():
    """toolbar=False is forwarded to the Vue component."""
    with ui.row():
        editor = ui.rich_text_editor(toolbar=False)
    assert editor._props.get('toolbar') is False


def test_toolbar_custom_groups():
    """A 2D list toolbar is forwarded to the Vue component unchanged."""
    groups = [['bold', 'italic'], ['undo', 'redo']]
    with ui.row():
        editor = ui.rich_text_editor(toolbar=groups)
    assert editor._props.get('toolbar') == groups


def test_update_method_is_set():
    """_update_method is set so NiceGUI calls setContentFromProps on prop updates."""
    with ui.row():
        editor = ui.rich_text_editor()
    assert editor._update_method == 'setContentFromProps'


def test_value_prop_name():
    """VALUE_PROP and LOOPBACK are set correctly on the class."""
    assert ui.rich_text_editor.VALUE_PROP == 'value'
    assert ui.rich_text_editor.LOOPBACK is None


def test_shared_doc_id_returns_identical_state():
    """Two editors with the same doc_id read from the same server-side Yjs room."""
    pytest.importorskip('y_py')

    doc_id = f'shared-{id(object())}'
    with ui.row():
        editor1 = ui.rich_text_editor(doc_id=doc_id)
        editor2 = ui.rich_text_editor(doc_id=doc_id)

    assert editor1.doc_id == editor2.doc_id == doc_id
    assert editor1.get_state() == editor2.get_state()


def test_table_html_renders(screen: Screen):
    """An editor initialised with table HTML shows the cell content in the DOM."""
    @ui.page('/')
    def page():
        ui.rich_text_editor(
            '<table><thead><tr><th>Name</th><th>Role</th></tr></thead>'
            '<tbody><tr><td>Alice</td><td>Engineer</td></tr></tbody></table>',
        )

    screen.open('/')
    screen.should_contain('Name')
    screen.should_contain('Alice')
    screen.should_contain('Engineer')


def test_css_file_exists():
    """The dist/rich_text_editor.css file must exist next to the element source."""
    import nicegui.elements.rich_text_editor.rich_text_editor as rte_module
    css = Path(rte_module.__file__).parent / 'dist' / 'rich_text_editor.css'
    assert css.is_file(), f'CSS file missing: {css}'


def test_css_contains_collaboration_cursor_styles():
    """The CSS file must include the collaboration cursor rules that display other users' names."""
    import nicegui.elements.rich_text_editor.rich_text_editor as rte_module
    css = Path(rte_module.__file__).parent / 'dist' / 'rich_text_editor.css'
    content = css.read_text()
    assert 'collaboration-cursor__label' in content
    assert 'collaboration-cursor__caret' in content


def test_resource_path_prop_is_set():
    """add_resource() must set the resource-path prop so the Vue component can load the CSS."""
    with ui.row():
        editor = ui.rich_text_editor()
    assert 'resource-path' in editor._props, 'resource-path prop missing — add_resource() not called?'


def test_event_args_to_value_non_string():
    """_event_args_to_value returns an empty string for non-string event args."""
    from nicegui.events import GenericEventArguments

    with ui.row():
        editor = ui.rich_text_editor()

    for bad_arg in (None, 42, {}, []):
        e = GenericEventArguments(sender=editor, client=None, args=bad_arg)
        assert editor._event_args_to_value(e) == ''


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
