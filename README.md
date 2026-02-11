# streamlitdash_GPT

# MEMBRE DE PROJET 
   HAJAR EL FATHI
   NAJOUA EL MANSOUF

# ❄️ Chat Cortex — Streamlit in Snowflake (sans clé OpenAI)

Application web type **ChatGPT** développée avec **Streamlit in Snowflake** et un LLM via **Snowflake Cortex**.  
Aucune clé OpenAI n’est utilisée : l’appel au modèle se fait directement via Snowflake (`SNOWFLAKE.CORTEX.COMPLETE`).

---

## 🎯 Objectif

Permettre à un utilisateur de discuter avec un **LLM supporté par Snowflake Cortex** directement depuis une application **Streamlit** hébergée dans Snowflake.

Fonctionnalités principales :
- Interface conversationnelle type ChatGPT (`st.chat_input`, `st.chat_message`)
- Choix du modèle Cortex dans la sidebar
- Réglage de la température
- Persistance des conversations en table Snowflake
- Rechargement de conversations existantes

---

## 🧱 Architecture

- **Frontend** : Streamlit in Snowflake
- **Backend LLM** : Snowflake Cortex (`SNOWFLAKE.CORTEX.COMPLETE`)
- **Stockage** : Table Snowflake `DB_LAB.CHAT_APP.CONVERSATIONS`
- **État applicatif** : `st.session_state` (messages + conversation_id)

---

## ✅ Prérequis

Compte Snowflake avec :
- Accès à un **WAREHOUSE**
- Droits de création de **DATABASE** et **SCHEMA**
- Accès à **Streamlit in Snowflake**
- Accès à **Snowflake Cortex**
- activation du cross-region inference pour accéder aux modèles hors région
## 📸 Captures d’écran

### ✅ Test Cortex
![Test Cortex](screens/02_cortex_test.png)

### ✅ Application Streamlit
![Chat Streamlit](sceens/image.png)

![Chat Streamlit](sceens/partie.png)

![Chat Streamlit](sceens/result.png)
![Chat Streamlit](sceens/res1.png)
![Chat Streamlit](sceens/RES3.png)




