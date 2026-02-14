"""Minimal demo app for the collaborative rich-text editor.

Run locally:   python demo.py
Deploy:        push to GitHub, then connect the repo on render.com
               (render.yaml in the repo root is picked up automatically).
"""
import os

from nicegui import ui

SHARED_DOC_ID = 'demo-room'


@ui.page('/')
def index() -> None:
    with ui.column().classes('w-full max-w-4xl mx-auto p-6 h-screen gap-3'):
        with ui.row().classes('items-baseline gap-3'):
            ui.label('Collaborative Rich Text Editor').classes('text-2xl font-bold')
            ui.badge('Live', color='green')
        ui.label(
            'Built with NiceGUI · Tiptap · Yjs. '
            'Open this page in multiple browser tabs to edit the same document in real time.'
        ).classes('text-sm opacity-60')
        ui.rich_text_editor('', doc_id=SHARED_DOC_ID).classes('w-full border rounded flex-1')


ui.run(
    host='0.0.0.0',
    port=int(os.environ.get('PORT', 8080)),
    title='RTE Demo',
    reload=False,
    storage_secret=os.environ.get('STORAGE_SECRET', 'change-me-in-production'),
)
