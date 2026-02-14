import * as RTE from 'nicegui-rich-text-editor';

export default {
  template: `<div></div>`,
  props: {
    value: String,
    docId: String,
    user: Object,
    disable: Boolean,
    id: String,
  },
  data() {
    return {
      // Allows methods called by the server before mount to await the editor.
      editorPromise: new Promise((resolve) => {
        this.resolveEditor = resolve;
      }),
    };
  },
  watch: {
    disable(newVal) {
      if (this.editor) this.editor.setEditable(!newVal);
    },
  },
  methods: {
    // Called by NiceGUI via _update_method when Python sets .value.
    setContentFromProps() {
      if (!this.editor) return;
      if (this.editor.getHTML() === this.value) return;
      this._applyingServerContent = true;
      this.editor.commands.setContent(this.value || '', false);
      this._applyingServerContent = false;
    },
    getHTML() {
      return this.editor ? this.editor.getHTML() : '';
    },
  },
  async mounted() {
    // Flag used to suppress echoing server-applied content back to the server.
    this._applyingServerContent = false;

    // --- Yjs document and awareness ---
    this.ydoc = new RTE.Y.Doc();
    this.awareness = new RTE.Awareness(this.ydoc);

    // --- Outbound: doc updates → server ---
    // window.socket is set inside the root Vue app's mounted() hook, which runs
    // AFTER child component mounted() hooks in Vue 3. We access window.socket
    // lazily inside callbacks so it is always resolved at call time.
    this.ydoc.on('update', (update, origin) => {
      // 'server' origin means we applied an inbound relay — do not echo it back.
      if (origin === 'server') return;
      if (!window.socket) return;
      window.socket.emit('yjs_update', {
        client_id: window.clientId,
        doc_id: this.docId,
        update: Array.from(update),
      });
    });

    // --- Outbound: awareness (cursor positions) → server ---
    this.awareness.on('update', ({ added, updated, removed }) => {
      if (!window.socket) return;
      const changed = [...added, ...updated, ...removed];
      const encoded = RTE.encodeAwarenessUpdate(this.awareness, changed);
      window.socket.emit('yjs_awareness', {
        client_id: window.clientId,
        doc_id: this.docId,
        awareness: Array.from(encoded),
      });
    });

    // --- Inbound handlers (named references for later .off() cleanup) ---
    this._onYjsUpdate = (data) => {
      if (data.doc_id !== this.docId) return;
      RTE.Y.applyUpdate(this.ydoc, new Uint8Array(data.update), 'server');
    };
    this._onYjsAwareness = (data) => {
      if (data.doc_id !== this.docId) return;
      RTE.applyAwarenessUpdate(this.awareness, new Uint8Array(data.awareness), 'server');
    };
    this._onYjsInit = (data) => {
      if (data.doc_id !== this.docId) return;
      RTE.Y.applyUpdate(this.ydoc, new Uint8Array(data.update), 'server');
    };

    // Register inbound listeners once the socket is ready.
    // We poll with nextTick until window.socket is available (set by root Vue mounted()).
    const registerSocketListeners = async () => {
      while (!window.socket) {
        await new Promise((resolve) => setTimeout(resolve, 10));
      }
      window.socket.on('yjs_update', this._onYjsUpdate);
      window.socket.on('yjs_awareness', this._onYjsAwareness);
      window.socket.on('yjs_init', this._onYjsInit);
      // Join the room — server replies with yjs_init if the doc has existing state.
      window.socket.emit('yjs_join', { client_id: window.clientId, doc_id: this.docId });
    };
    registerSocketListeners();

    // --- User identity for collaboration cursors ---
    const userInfo =
      this.user && this.user.name
        ? this.user
        : {
            name: 'Anonymous',
            color:
              '#' +
              Math.floor(Math.random() * 0xffffff)
                .toString(16)
                .padStart(6, '0'),
          };

    // --- Create Tiptap editor ---
    this.editor = new RTE.Editor({
      element: this.$el,
      editable: !this.disable,
      extensions: [
        // history: false is mandatory — Yjs/y-prosemirror provides its own undo stack.
        RTE.StarterKit.configure({ history: false }),
        RTE.Collaboration.configure({ document: this.ydoc }),
        // CollaborationCursor only requires provider.awareness — our Awareness object satisfies this.
        RTE.CollaborationCursor.configure({
          provider: { awareness: this.awareness },
          user: userInfo,
        }),
        RTE.Image,
        RTE.Table.configure({ resizable: true }),
        RTE.TableRow,
        RTE.TableCell,
        RTE.TableHeader,
      ],
      onUpdate: ({ editor }) => {
        if (!this._applyingServerContent) {
          this.$emit('update:value', editor.getHTML());
        }
      },
    });

    // Apply any initial HTML value passed from Python.
    if (this.value) this.setContentFromProps();

    this.resolveEditor(this.editor);
  },
  beforeUnmount() {
    // Sync final HTML back to the server element state (mirrors codemirror.js pattern).
    const element = mounted_app.elements[this.$props.id.slice(1)];
    if (element) element.props.value = this.getHTML();

    if (window.socket) {
      window.socket.emit('yjs_leave', { client_id: window.clientId, doc_id: this.docId });
      window.socket.off('yjs_update', this._onYjsUpdate);
      window.socket.off('yjs_awareness', this._onYjsAwareness);
      window.socket.off('yjs_init', this._onYjsInit);
    }

    if (this.awareness) this.awareness.destroy();
    if (this.editor) this.editor.destroy();
  },
};
