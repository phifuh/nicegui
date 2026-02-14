"""Collaborative rich-text editor element backed by Tiptap + Yjs."""
from __future__ import annotations

import uuid

# ruff: noqa: TID252
from ... import rich_text_editor_room
from ...elements.mixins.disableable_element import DisableableElement
from ...elements.mixins.value_element import ValueElement
from ...events import GenericEventArguments, Handler, ValueChangeEventArguments


class RichTextEditor(ValueElement, DisableableElement, component='rich_text_editor.js',
                     esm={'nicegui-rich-text-editor': 'dist'}, default_classes='nicegui-rich-text-editor'):
    """Collaborative rich-text editor backed by Tiptap + Yjs.

    Multiple browser clients sharing the same ``doc_id`` edit the same document
    in real time using CRDT conflict-free merging.  The NiceGUI Python server
    relays Yjs update and awareness messages; no external synchronisation server
    is required.

    :param value: initial HTML content (default: empty string)
    :param doc_id: collaborative room identifier; all clients using the same
        ``doc_id`` share one Yjs document.  A unique UUID is auto-generated
        when omitted, giving a per-element private document.
    :param user: cursor identity shown to collaborators,
        e.g. ``{'name': 'Alice', 'color': '#3b82f6'}``.
        Defaults to an anonymous user with a random colour.
    :param on_change: callback invoked with a ``ValueChangeEventArguments`` whenever the HTML
        content changes.

    Default Editor:
    """

    VALUE_PROP = 'value'
    LOOPBACK = None  # Yjs (in the Vue component) owns document state; no server echo needed.

    def __init__(self, value: str = '', *, doc_id: str | None = None, user: dict[str, str] | None = None,
                 on_change: Handler[ValueChangeEventArguments] | None = None) -> None:
        """Init the RichTextEditor."""
        self._doc_id = doc_id if doc_id is not None else str(uuid.uuid4())
        super().__init__(value=value, on_value_change=None)
        if on_change is not None:
            self.on_value_change(on_change)
        self._props['doc-id'] = self._doc_id
        self._props['user'] = user or {}
        self._update_method = 'setContentFromProps'

    def _event_args_to_value(self, e: GenericEventArguments) -> str:
        """Carry the HTML string emitted by Tiptap's onUpdate hook.

        Returns:
            Emptz string or the event arguments

        """
        args = e.args
        return args if isinstance(args, str) else ''

    @property
    def doc_id(self) -> str:
        """The collaborative room identifier (read-only after construction)."""
        return self._doc_id

    def get_state(self) -> bytes:
        """Return the raw Yjs binary state of this document.

        The bytes represent a full Yjs state vector update that can be stored
        in any persistence layer (e.g. MongoDB ``Binary``, Redis, filesystem)
        and later restored with ``set_state()``.

        Works correctly even when no clients are currently connected to the room.

        :raises ImportError: if ``y-py`` is not installed
            (``pip install y-py``).

        Returns:
            All data as bytes

        """
        return rich_text_editor_room.get_state(self._doc_id)

    def set_state(self, data: bytes) -> None:
        """Restore a previously persisted Yjs binary state.

        The update is CRDT-merged into the in-memory document and immediately
        broadcast to all clients that are currently in the room.

        :param data: raw Yjs state bytes as returned by ``get_state()``.
        :raises ImportError: if ``y-py`` is not installed
            (``pip install y-py``).
        """
        rich_text_editor_room.set_state(self._doc_id, data)
