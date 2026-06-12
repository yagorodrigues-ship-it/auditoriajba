import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico", layout="wide")

# --- ESTILIZAÇÃO PERSONALIZADA (Botão Laranja) ---
st.markdown("""
    <style>
    div.stButton > button:first-child[kind="primary"] {
        background-color: #e65100;
        border-color: #e65100;
        color: white;
    }
    div.stButton > button:first-child[kind="primary"]:hover {
        background-color: #ef6c00;
        border-color: #ef6c00;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIMULAÇÃO DE BANCO DE DADOS EM MEMÓRIA ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'inventarios' not in st.session_state:
    st.session_state.inventarios = [{"id": "#37", "nome": "teste", "data": "2026-06-12", "status": "Aberto"}]
if 'base_sistema' not in st.session_state:
    st.session_state.base_sistema = None
if 'contagens' not in st.session_state:
    st.session_state.contagens = {}

# --- TELA DE LOGIN ---
if not st.session_state.logged_in:
    st.title("🔒 Acesso ao Sistema de Estoque")
    
    with st.form("login_form"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        botao_login = st.form_submit_button("Entrar", type="primary")
        
        if botao_login:
            if usuario == "admin" and senha == "123":
                st.session_state.logged_in = True
                st.session_state.operador = usuario
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
else:
    # --- SE USUÁRIO LOGADO, MOSTRA O SISTEMA ---
    
    # 1. BARRA LATERAL (SIDEBAR)
    with st.sidebar:
        st.header("📁 Inventário Ativo")
        
        lista_inv = [f"{i['id']} – {i['nome']} ({i['data']})" for i in st.session_state.inventarios]
        inventario_selecionado = st.selectbox("Selecione o inventário", lista_inv)
        
        st.markdown("---")
        
        # Criar novo inventário (CORRIGIDO COM FORMULÁRIO COMPLETO)
        with st.expander("➕ Novo Inventário", expanded=False):
            with st.form("form_novo_inventario", clear_on_submit=True):
                novo_nome = st.text_input("Nome")
                nova_desc = st.text_input("Descrição (opcional)")
                botao_criar = st.form_submit_button("Criar", type="primary", use_container_width=True)
                
                if botao_criar:
                    if novo_nome:
                        proximo_numero = len(st.session_state.inventarios) + 37
                        novo_id = f"#{proximo_numero}"
                        hoje = datetime.date.today().strftime("%Y-%m-%d")
                        
                        st.session_state.inventarios.append({
                            "id": novo_id, 
                            "nome": novo_nome, 
                            "data": hoje, 
                            "status": "Aberto"
                        })
                        st.toast(f"✅ Inventário
