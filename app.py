import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Estoque", layout="wide")

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
    st.title("Acesso ao Sistema de Estoque")
    with st.form("login_form"):
        usuario = st.text_input("Usuario")
        senha = st.text_input("Senha", type="password")
        botao_login = st.form_submit_button("Entrar")
        if botao_login:
            if usuario == "admin" and senha == "123":
                st.session_state.logged_in = True
                st.session_state.operador = usuario
                st.rerun()
            else:
                st.error("Incorreto.")
else:
    # 1. BARRA LATERAL
    with st.sidebar:
        st.header("Inventario Ativo")
        lista_inv = [f"{i['id']} - {i['nome']}" for i in st.session_state.inventarios]
        inventario_selecionado = st.selectbox("Selecione o inventario", lista_inv)
        
        st.markdown("---")
        
        with st.expander("Novo Inventario", expanded=False):
            with st.form("form_novo", clear_on_submit=True):
                novo_nome = st.text_input("Nome")
                botao_criar = st.form_submit_button("Criar")
                if botao_criar:
                    if novo_nome:
                        novo_id = f"#{len(st.session_state.inventarios) + 37}"
                        st.session_state.inventarios.append({"id": novo_id, "nome": novo_nome, "data": "2026-06-12", "status": "Aberto"})
                        st.rerun()

        st.markdown("---")
        st.write(f"Operador: {st.session_state.operador}")
        
        st.markdown("---")
        arquivo_excel = st.file_uploader("Suba o arquivo (.xlsx)", type=["xlsx"])
        if arquivo_excel is not None:
            st.session_state.base_sistema = pd.read_excel(arquivo_excel)

    # 2. PAINEL PRINCIPAL
    st.title("Contagem de Estoque Fisico")
    aba_contar, aba_relatorio = st.tabs(["Contar Item", "Relatorio"])
    
    # ABA 1: CONTAR ITEM
    with aba_contar:
        if st.session_state.base_sistema is None:
            st.warning("Nenhuma base carregada. Suba o arquivo Excel na barra lateral.")
        else:
            codigo_busca = st.text_input("Codigo do Produto")
            if codigo_busca:
                df_sistema = st.session_state.base_sistema
                produto_encontrado = df_sistema[df_sistema.iloc[:, 0].astype(str).str.upper() == codigo_busca.upper()]
                if not produto_encontrado.empty:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.info(f"COD: {codigo_busca.upper()}")
                    with col2:
                        desc = produto_encontrado.iloc[0, 1] if len(produto_encontrado.columns) > 1 else "Sem Descricao"
                        st.write(f"Descricao: {desc}")
                    with col3:
                        qtd_sis = produto_encontrado.iloc
