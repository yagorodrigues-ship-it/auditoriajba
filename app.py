import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico", layout="wide")

# --- ESTILIZAÇÃO PERSONALIZADA (Identificação com o novo design do print) ---
st.markdown("""
    <style>
    /* Botões laranjas largos de confirmação */
    div.stButton > button:first-child[kind="primary"] {
        background-color: #d35400;
        border-color: #d35400;
        color: white;
        font-weight: bold;
    }
    div.stButton > button:first-child[kind="primary"]:hover {
        background-color: #e67e22;
        border-color: #e67e22;
        color: white;
    }
    /* Customização dos blocos informativos superiores */
    .bloco-info {
        background-color: #ebf5fb;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #d4e6f1;
        text-align: left;
        margin-bottom: 10px;
    }
    .bloco-titulo {
        color: #7f8c8d;
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 0.5px;
    }
    .bloco-valor {
        color: #1b4f72;
        font-size: 24px;
        font-weight: bold;
    }
    /* Card largo para a quantidade do sistema */
    .card-sistema {
        background-color: #ebf5fb;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #d4e6f1;
        margin-top: 15px;
        margin-bottom: 25px;
    }
    /* Cards escuros da barra lateral */
    .card-lateral {
        background-color: #1a233a;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 12px;
        border-left: 4px solid #2563eb;
    }
    .card-lateral-titulo {
        color: #93c5fd;
        font-size: 11px;
        font-weight: bold;
    }
    .card-lateral-valor {
        color: white;
        font-size: 28px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS EM MEMÓRIA DA SESSÃO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'base_sistema' not in st.session_state:
    st.session_state.base_sistema = None
if 'nome_arquivo_excel' not in st.session_state:
    st.session_state.nome_arquivo_excel = ""
if 'inventarios' not in st.session_state:
    # Começa com os exemplos simulados idênticos ao seu print histórico
    st.session_state.inventarios = [
        {"id": "#39", "nome": "TEste JBA", "data": "2026-06-12", "status": "Finalizado", "itens": 0}
    ]
if 'contagens_por_inventario' not in st.session_state:
    st.session_state.contagens_por_inventario = {"#39": {}}
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 1
if 'operador' not in st.session_state:
    st.session_state.operador = "admin"
if 'historico_equipe' not in st.session_state:
    st.session_state.historico_equipe = pd.DataFrame({
        'Operador': ['Junior', 'Tiago', 'Ana', 'Carlos'],
        'Inventários Feitos': [8, 5, 3, 2]
    })

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
    
    # --- CÁLCULO DE IDENTIFICAÇÃO DO INVENTÁRIO SELECIONADO ---
    id_inventario_atual = None
    status_inventario_atual = "Aberto"
    
    # 1. BARRA LATERAL (SIDEBAR)
    with st.sidebar:
        st.write("📂 **Carregar Base de Dados (Saldo)**")
        arquivo_excel = st.file_uploader("Suba o arquivo Excel do sistema (.xlsx)", type=["xlsx"], label_visibility="collapsed")
        if arquivo_excel is not None and st.session_state.base_sistema is None:
            st.session_state.base_sistema = pd.read_excel(arquivo_excel)
            st.session_state.nome_arquivo_excel = arquivo_excel.name
            st.toast("Base de dados (Saldo) carregada com sucesso!")
            st.rerun()
            
        st.markdown("---")
        st.write("📁 **Selecione ou Crie um Inventário**")
        
        if not st.session_state.inventarios:
            st.info("Nenhum inventário ativo. Crie um abaixo para iniciar.")
        else:
            lista_inv = [f"{i['id']} – {i['nome']} ({'🟢 Aberto' if i['status']=='Aberto' else '🔴 Finalizado'})" for i in st.session_state.inventarios]
            inventario_selected = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
            id_inventario_atual = inventario_selected.split(" – ")[0]
            # Descobre o status atual dele
            for inv in st.session_state.inventarios:
                if inv["id"] == id_inventario_atual:
                    status_inventario_atual = inv["status"]

        # Criar novo inventário
        with st.expander("➕ Novo Inventário", expanded=not st.session_state.inventarios):
            with st.form("form_novo", clear_on_submit=True):
                novo_nome = st.text_input("Nome do Inventário")
                botao_criar = st.form_submit_button("Criar", type="primary")
                if botao_criar and novo_nome:
                    novo_id = f"#{len(st.session_state.inventarios) + 39}"
                    hoje = datetime.date.today().strftime("%Y-%m-%d")
                    st.session_state.inventarios.append({"id": novo_id, "nome": novo_nome, "data": hoje, "status": "Aberto", "itens": 0})
                    st.session_state.contagens_por_inventario[novo_id] = {}
                    st.toast(f"Inventário {novo_id} Criado!")
                    st.rerun()

        # Botão para Fechar o Inventário Selecionado Atual
        if id_inventario_atual and status_inventario_atual == "Aberto":
            if st.button("🔒 Fechar inventário atual", use_container_width=True):
                for inv in st.session_state.inventarios:
                    if inv["id"] == id_inventario_atual:
                        inv["status"] = "Finalizado"
                        inv["itens"] = len(st.session_state.contagens_por_inventario.get(id_inventario_atual, {}))
                st.toast(f"Inventário {id_inventario_atual} fechado com sucesso e salvo no histórico!")
                st.rerun()

        st.markdown("---")
        st.write("👤 **Operador**")
        st.session_state.operador = st.text_input("Seu nome", value=st.session_state.operador, key="op_input_text", label_visibility="collapsed")

        # --- CÁLCULO DE MÉTRICAS DINÂMICAS ---
        total_itens_base = 0
        total_contados = 0
        total_pendentes = 0
        progresso = 0.0

        if st.session_state.base_sistema is not None and id_inventario_atual is not None:
            total_itens_base = len(st.session_state.base_sistema)
            contagens_atuais = st.session_state.contagens_por_inventario.get(id_inventario_atual, {})
            total_contados = len(contagens_atuais)
            total_pendentes = max(0, total_itens_base - total_contados)
            if total_itens_base > 0:
                progresso = total_contados / total_itens_base

        st.markdown("---")
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">📋 ITENS NA BASE</div><div class="card-lateral-valor">{total_itens_base}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">✅ CONTADOS</div><div class="card-lateral-valor">{total_contados}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">⏳ PENDENTES</div><div class="card-lateral-valor">{total_pendentes}</div></div>', unsafe_allow_html=True)
        
        st.write("**PROGRESSO DA CONTAGEM**")
        st.
