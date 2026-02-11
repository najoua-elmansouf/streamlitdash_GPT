import streamlit as st
import uuid
from snowflake.snowpark.context import get_active_session

st.set_page_config(page_title="Chat Cortex", page_icon="", layout="centered")

DB_TABLE = "DB_LAB.CHAT_APP.CONVERSATIONS"
SYSTEM_MESSAGE = {"role": "system", "content": "Tu es un assistant utile et clair. Réponds en français."}

MODEL_OPTIONS = [
    "mistral-large",
    "mixtral-8x7b",
    "llama3-8b",
    "llama3-70b",
    "snowflake-arctic",
]

# -----------------------------
# DB helpers
# -----------------------------
def save_message_to_db(conversation_id: str, role: str, content: str) -> None:
    session = get_active_session()
    safe_conv = conversation_id.replace("'", "''")
    safe_role = role.replace("'", "''")
    safe_content = content.replace("'", "''")

    sql = f"""
    INSERT INTO {DB_TABLE} (conversation_id, timestamp, role, content)
    VALUES ('{safe_conv}', CURRENT_TIMESTAMP(), '{safe_role}', '{safe_content}');
    """
    session.sql(sql).collect()

def load_conversation_from_db(conversation_id: str):
    session = get_active_session()
    safe_conv = conversation_id.replace("'", "''")

    sql = f"""
    SELECT role, content
    FROM {DB_TABLE}
    WHERE conversation_id = '{safe_conv}'
    ORDER BY timestamp;
    """
    df = session.sql(sql).to_pandas()

    messages = [SYSTEM_MESSAGE]
    for _, row in df.iterrows():
        role = str(row["ROLE"]).lower()
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": str(row["CONTENT"])})
    return messages

def list_conversations():
    """
    Liste les conversations existantes.
    'title' = première question user (si existe).
    """
    session = get_active_session()

    sql = f"""
    WITH first_user AS (
      SELECT
        conversation_id,
        content AS first_question,
        ROW_NUMBER() OVER (PARTITION BY conversation_id ORDER BY timestamp) AS rn
      FROM {DB_TABLE}
      WHERE role = 'user'
    ),
    started AS (
      SELECT conversation_id, MIN(timestamp) AS started_at
      FROM {DB_TABLE}
      GROUP BY conversation_id
    )
    SELECT
      s.conversation_id,
      s.started_at,
      COALESCE(f.first_question, '[Sans question]') AS title
    FROM started s
    LEFT JOIN first_user f
      ON s.conversation_id = f.conversation_id AND f.rn = 1
    ORDER BY s.started_at DESC;
    """

    df = session.sql(sql).to_pandas()

    convs = []
    for _, row in df.iterrows():
        convs.append({
            "conversation_id": str(row["CONVERSATION_ID"]),
            "title": str(row["TITLE"]).strip()
        })
    return convs

# -----------------------------
# Prompt (system + historique)
# -----------------------------
def build_prompt_from_history(messages, max_turns: int = 12) -> str:
    system_txt = SYSTEM_MESSAGE["content"]
    convo = []

    for m in messages:
        if m["role"] == "system":
            system_txt = m["content"]
        elif m["role"] in ("user", "assistant"):
            convo.append(m)

    convo = convo[-max_turns:]

    lines = []
    lines.append("INSTRUCTION SYSTEME:")
    lines.append(system_txt.strip())
    lines.append("")
    lines.append("HISTORIQUE:")
    for m in convo:
        role = "Utilisateur" if m["role"] == "user" else "Assistant"
        lines.append(f"{role}: {m['content'].strip()}")
    lines.append("")
    lines.append("CONSIGNE: Réponds uniquement avec la prochaine réponse de l'Assistant.")
    lines.append("Assistant:")
    return "\n".join(lines)

# -----------------------------
# Cortex call (Snowflake) + fallback
# -----------------------------
def call_cortex_complete(model: str, prompt: str, temp: float) -> str:
    session = get_active_session()
    safe_prompt = prompt.replace("$$", "\\$\\$")

    sql_with_opts = f"""
    SELECT SNOWFLAKE.CORTEX.COMPLETE(
        '{model}',
        $${safe_prompt}$$,
        PARSE_JSON('{{"temperature": {temp}}}')
    ) AS RESPONSE;
    """

    prompt_with_temp = f"[Température demandée: {temp}]\n" + safe_prompt
    sql_no_opts = f"""
    SELECT SNOWFLAKE.CORTEX.COMPLETE(
        '{model}',
        $${prompt_with_temp}$$
    ) AS RESPONSE;
    """

    try:
        df = session.sql(sql_with_opts).to_pandas()
        return str(df.loc[0, "RESPONSE"])
    except Exception as e:
        msg = str(e)
        if ("COMPLETE$V6" in msg) or ("Invalid argument types" in msg) or ("needs to be a string literal" in msg):
            df = session.sql(sql_no_opts).to_pandas()
            return str(df.loc[0, "RESPONSE"])
        raise

# -----------------------------
# Session state init
# -----------------------------
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = [SYSTEM_MESSAGE]

# -----------------------------
# Sidebar UI
# -----------------------------
st.sidebar.title("⚙️ Paramètres")
selected_model = st.sidebar.selectbox("Modèle Cortex", MODEL_OPTIONS, index=0)
temperature = st.sidebar.slider("Température", 0.0, 1.5, 0.7, 0.1)

st.sidebar.divider()
st.sidebar.subheader(" Conversations")

convs = list_conversations()

#  Dropdown = uniquement la question (title), raccourcie
labels = []
id_by_label = {}
for c in convs:
    title = c["title"].strip()
    if len(title) > 40:
        title = title[:40] + "…"

    labels.append(title)
    id_by_label[title] = c["conversation_id"]

# Choix par défaut : conversation courante si elle existe, sinon la plus récente
default_index = 0
if labels:
    for i, lab in enumerate(labels):
        if id_by_label[lab] == st.session_state.conversation_id:
            default_index = i
            break

selected_label = st.sidebar.selectbox(
    "Choisir une conversation",
    options=labels if labels else ["(Aucune conversation sauvegardée)"],
    index=default_index if labels else 0
)

# Charger la conversation sélectionnée
if labels:
    selected_cid = id_by_label[selected_label]
    if selected_cid != st.session_state.conversation_id:
        st.session_state.conversation_id = selected_cid
        st.session_state.messages = load_conversation_from_db(selected_cid)
        st.rerun()

if st.sidebar.button(" Nouveau Chat"):
    st.session_state.conversation_id = str(uuid.uuid4())
    st.session_state.messages = [SYSTEM_MESSAGE]
    st.rerun()

# (Optionnel) afficher l'ID en petit pour debug
st.sidebar.caption(f"ID courant : {st.session_state.conversation_id}")

# -----------------------------
# Main UI
# -----------------------------
st.title(" Welcome to your chat ..")

for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_text = st.chat_input("Écris ton message...")

if user_text:
    # user
    st.session_state.messages.append({"role": "user", "content": user_text})
    save_message_to_db(st.session_state.conversation_id, "user", user_text)

    with st.chat_message("user"):
        st.markdown(user_text)

    # cortex
    full_prompt = build_prompt_from_history(st.session_state.messages, max_turns=12)

    with st.chat_message("assistant"):
        with st.spinner("Cortex réfléchit..."):
            try:
                answer = call_cortex_complete(selected_model, full_prompt, temperature)
            except Exception as e:
                answer = f"❌ Erreur Cortex : {e}"
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    save_message_to_db(st.session_state.conversation_id, "assistant", answer)
