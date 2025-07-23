import os, json, shutil, zipfile, tempfile
import gradio as gr
from cli_app import LLMClient, Config  # ✅ Sizning LLMClient

# --- Sozlamalar
CHAT_DIR = "chat_data"
META_FILE = os.path.join(CHAT_DIR, "meta.json")

os.makedirs(CHAT_DIR, exist_ok=True)

# --- API key va LLMClient ---
api_key = None
if os.path.exists(Config.ENV_FILE):
    from dotenv import load_dotenv
    load_dotenv(Config.ENV_FILE)
    api_key = os.getenv(Config.API_KEY_NAME)

llm_client = LLMClient(api_key, ui=None) if api_key else None

# ================= JSON Helpers =================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================= Chat Management =================
def load_meta():
    return load_json(META_FILE, {})

def save_meta(meta):
    save_json(META_FILE, meta)

def get_chat_list():
    meta = load_meta()
    return list(meta.keys()) if meta else ["Default Chat"]

def get_chat_description(name):
    meta = load_meta()
    return meta.get(name, {}).get("description", "")

def save_chat_description(name, desc):
    meta = load_meta()
    if name not in meta:
        meta[name] = {}
    meta[name]["description"] = desc
    save_meta(meta)

def chat_file_path(name):
    return os.path.join(CHAT_DIR, f"{name}.json")

def load_chat(name):
    return load_json(chat_file_path(name), [])

def save_chat(name, history):
    save_json(chat_file_path(name), history)

def save_message(chat_name, role, content):
    history = load_chat(chat_name)
    history.append({"role": role, "content": content})
    save_chat(chat_name, history)

def create_chat(name, description=""):
    meta = load_meta()
    if name not in meta:
        meta[name] = {"description": description}
        save_meta(meta)
        save_chat(name, [])

def delete_chat(name):
    meta = load_meta()
    if name in meta:
        meta.pop(name)
        save_meta(meta)
    path = chat_file_path(name)
    if os.path.exists(path):
        os.remove(path)

def rename_chat(old_name, new_name, new_desc=""):
    meta = load_meta()
    if old_name in meta:
        # eski faylni ko‘chiramiz
        old_path = chat_file_path(old_name)
        new_path = chat_file_path(new_name)
        if os.path.exists(old_path):
            shutil.move(old_path, new_path)
        meta[new_name] = {"description": new_desc or meta[old_name].get("description", "")}
        meta.pop(old_name)
        save_meta(meta)

# ================= Streaming javob =================
def stream_message(history, chat_name, user_message):
    if history is None:
        history = []

    # ✅ User xabarini qo‘shamiz
    history.append({"role": "user", "content": user_message})
    save_message(chat_name, "user", user_message)
    yield history

    if not llm_client:
        bot_reply = "❌ API key yo‘q yoki noto‘g‘ri!"
        history.append({"role": "assistant", "content": bot_reply})
        save_message(chat_name, "assistant", bot_reply)
        yield history
        return

    bot_reply = ""
    for token in llm_client.get_streamed_response(user_message):
        bot_reply += token
        if history[-1]["role"] == "assistant":
            history[-1]["content"] = bot_reply
        else:
            history.append({"role": "assistant", "content": bot_reply})
        yield history

    save_message(chat_name, "assistant", bot_reply)

# ================= Export/Import =================
def export_chat(chat_name):
    path = chat_file_path(chat_name)
    if not os.path.exists(path):
        return None
    return path  # Gradio File component bilan qaytariladi

def import_chat(file_obj, new_name):
    if not file_obj:
        return "❌ Fayl yuklanmadi!"
    content = load_json(file_obj.name, [])
    if not new_name:
        new_name = os.path.splitext(os.path.basename(file_obj.name))[0]
    create_chat(new_name, "Imported chat")
    save_chat(new_name, content)
    return f"✅ Chat '{new_name}' import qilindi!"

# ================= Backup/Restore =================
def backup_all_chats():
    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp_zip.name, "w") as zipf:
        # meta.json + barcha chatlar
        for root, _, files in os.walk(CHAT_DIR):
            for file in files:
                fpath = os.path.join(root, file)
                arcname = os.path.relpath(fpath, CHAT_DIR)
                zipf.write(fpath, arcname)
    return tmp_zip.name

def restore_backup(zip_file):
    if not zip_file:
        return "❌ ZIP fayl yuklanmadi!"
    with zipfile.ZipFile(zip_file.name, "r") as zipf:
        zipf.extractall(CHAT_DIR)
    return "✅ Barcha chatlar tiklandi!"

# ================= Search Messages =================
def search_messages(chat_name, query):
    if not query:
        return "🔍 Qidiruv uchun so‘z kiriting!"
    history = load_chat(chat_name)
    matches = [
        f"**{m['role']}**: {m['content']}"
        for m in history if query.lower() in m['content'].lower()
    ]
    if not matches:
        return f"❌ '{query}' topilmadi!"
    return "## Qidiruv natijalari:\n\n" + "\n\n".join(matches)

# ==================== Gradio UI ====================
def launch_webui():
    all_chats = get_chat_list()
    current_chat = all_chats[0]

    with gr.Blocks(title="HacxGPT Multi-Chat") as demo:
        gr.Markdown("## 💬 HacxGPT (Multi-Chat + Streaming + Backup + Search)")

        with gr.Row():
            chat_selector = gr.Dropdown(
                choices=all_chats,
                value=current_chat,
                label="📂 Select Chat"
            )
            desc_box = gr.Textbox(label="Description", value=get_chat_description(current_chat))

        with gr.Row():
            new_chat_name = gr.Textbox(label="➕ New Chat Name")
            new_chat_desc = gr.Textbox(label="Description")
            create_btn = gr.Button("Create")

            rename_box = gr.Textbox(label="✏️ Rename To")
            rename_desc = gr.Textbox(label="New Description")
            rename_btn = gr.Button("Rename")

            delete_btn = gr.Button("🗑️ Delete")

        chatbot = gr.Chatbot(
            label="Chat History",
            type="messages",
            value=load_chat(current_chat)
        )

        msg = gr.Textbox(placeholder="Type message and press ENTER...")
        send = gr.Button("Send")

        with gr.Accordion("📜 Export/Import", open=False):
            export_btn = gr.Button("Export Chat")
            export_file = gr.File(label="Download Chat", interactive=False)
            import_file = gr.File(label="Upload JSON")
            import_name = gr.Textbox(label="New Chat Name")
            import_btn = gr.Button("Import Chat")
            import_status = gr.Markdown("")

        with gr.Accordion("🗜️ Backup / Restore", open=False):
            backup_btn = gr.Button("Backup All Chats (ZIP)")
            backup_file = gr.File(label="Download Backup", interactive=False)
            restore_file = gr.File(label="Upload ZIP Backup")
            restore_btn = gr.Button("Restore Chats")
            restore_status = gr.Markdown("")

        with gr.Accordion("🔍 Search Messages", open=False):
            search_query = gr.Textbox(label="Search in this chat")
            search_btn = gr.Button("Search")
            search_result = gr.Markdown("")

        # --- Chat tanlash ---
        def select_chat(chat_name):
            return (
                load_chat(chat_name),
                get_chat_description(chat_name),
                gr.update(value=chat_name, choices=get_chat_list())
            )

        chat_selector.change(
            select_chat,
            inputs=chat_selector,
            outputs=[chatbot, desc_box, chat_selector]
        )

        # --- Yangi chat yaratish ---
        def create_action(name, desc):
            if not name:
                name = f"Chat {len(get_chat_list())+1}"
            create_chat(name, desc)
            return (
                gr.update(value=name, choices=get_chat_list()),
                load_chat(name),
                get_chat_description(name)
            )

        create_btn.click(
            create_action,
            inputs=[new_chat_name, new_chat_desc],
            outputs=[chat_selector, chatbot, desc_box]
        )

        # --- Rename ---
        def rename_action(old_name, new_name, new_desc):
            rename_chat(old_name, new_name, new_desc)
            return (
                gr.update(value=new_name, choices=get_chat_list()),
                load_chat(new_name),
                get_chat_description(new_name)
            )

        rename_btn.click(
            rename_action,
            inputs=[chat_selector, rename_box, rename_desc],
            outputs=[chat_selector, chatbot, desc_box]
        )

        # --- Delete ---
        def delete_action(name):
            delete_chat(name)
            chats = get_chat_list()
            new_cur = chats[0] if chats else "Default Chat"
            return (
                gr.update(value=new_cur, choices=chats),
                load_chat(new_cur),
                get_chat_description(new_cur)
            )

        delete_btn.click(
            delete_action,
            inputs=chat_selector,
            outputs=[chat_selector, chatbot, desc_box]
        )

        # --- Streaming message ---
        send.click(
            stream_message,
            inputs=[chatbot, chat_selector, msg],
            outputs=chatbot
        )
        msg.submit(
            stream_message,
            inputs=[chatbot, chat_selector, msg],
            outputs=chatbot
        )

        # --- Export ---
        export_btn.click(
            export_chat,
            inputs=chat_selector,
            outputs=export_file
        )

        # --- Import ---
        import_btn.click(
            import_chat,
            inputs=[import_file, import_name],
            outputs=import_status
        )

        # --- Backup ---
        backup_btn.click(
            backup_all_chats,
            outputs=backup_file
        )

        # --- Restore ---
        restore_btn.click(
            restore_backup,
            inputs=restore_file,
            outputs=restore_status
        )

        # --- Search ---
        search_btn.click(
            search_messages,
            inputs=[chat_selector, search_query],
            outputs=search_result
        )

    demo.queue()
    demo.launch(server_name="127.0.0.1", server_port=7860)
