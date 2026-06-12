import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico", layout="wide")

# --- ESTILIZAÇÃO PERSONALIZADA (Botão Laranja e Alinhamento) ---
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

# --- BANCO DE DADOS EM MEMÓRIA DA SESSÃO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'inventarios' not in st.session_state:
    st.session_state.inventarios = [] # Começa vazio conforme o print demonstrativo
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
    # --- INTERFACE PRINCIPAL DO SISTEMA ---
    
    # 1. BARRA LATERAL (SIDEBAR)
    with st.sidebar:
        st.write("📁 **Inventário Ativo**")
        
        if not st.session_state.inventarios:
            st.caption("None")
            st.info("Nenhum inventário aberto. Crie um abaixo ↓")
            lista_inv = ["Nenhum disponível"]
            inventario_selecionado = st.selectbox("Selecione o inventário", lista_inv, disabled=True)
        else:
            st.caption("Inventário selecionado:")
            lista_inv = [f"{i['id']} – {i['nome']} ({i['data']})" for i in st.session_state.inventarios]
            inventario_selecionado = st.selectbox("Selecione o inventário", lista_inv)
        
        # Formulário protegido para criar novo inventário
        with st.expander("➕ Novo Inventário", expanded=False):
            with st.form("form_novo", clear_on_submit=True):
                novo_nome = st.text_input("Nome")
                botao_criar = st.form_submit_button("Criar", type="primary")
                if botao_criar:
                    if novo_nome:
                        novo_id = f"#{len(st.session_state.inventarios) + 37}"
                        hoje = datetime.date.today().strftime("%Y-%m-%d")
                        st.session_state.inventarios.append({"id": novo_id, "nome": novo_nome, "data": hoje, "status": "Aberto"})
                        st.rerun()
                    else:
                        st.error("Digite um nome.")

        st.markdown("---")
        st.write("👤 **Operador**")
        nome_operador = st.text_input("Seu nome", value=st.session_state.operador)
        
        st.markdown("---")
        with st.expander("📁 Carregar / Atualizar Estoque", expanded=False):
            arquivo_excel = st.file_uploader("Suba o arquivo (.xlsx)", type=["xlsx"])
            if arquivo_excel is not None:
                st.session_state.base_sistema = pd.read_excel(arquivo_excel)
                st.toast("Base carregada com sucesso!")
                
        if st.button("🔄 Recarregar estoque", use_container_width=True):
            st.rerun()

        st.markdown("---")
        st.info("☁️ Banco: **Supabase** (nuvem)")

    # 2. PAINEL PRINCIPAL
    st.title("📦 Contagem de Estoque Físico")
    st.caption("Tel Telecomunicações · Contagem de Estoque Físico")
    
    if not st.session_state.inventarios:
        st.warning("⚠️ Nenhum inventário ativo. Crie ou selecione um na barra lateral.")
    
    # Abas estruturadas conforme as pastas solicitadas
    aba_contar, aba_atual, aba_historico, aba_base = st.tabs([
        "🔍 Contar Item", 
        "📊 Contagem Atual", 
        "📁 Histórico de Inventários", 
        "📄 Base de Estoque"
    ])
    
    # COMPORTAMENTO SE NÃO HOUVER INVENTÁRIO ATIVO
    if not st.session_state.inventarios:
        mensagem_padrao = "Selecione ou crie um inventário na barra lateral para começar."
        with aba_contar: st.info(mensagem_padrao)
        with aba_atual: st.info(mensagem_padrao)
        with aba_historico: st.info("Nenhum histórico disponível.")
        with aba_base: st.info("Nenhuma base associada.")
    else:
        # --- SE TIVER INVENTÁRIO SELECIONADO, LIBERA AS FUNÇÕES ---
        
        # ABA 1: CONTAR ITEM
        with aba_contar:
            if st.session_state.base_sistema is None:
                st.warning("⚠️ Nenhuma base de estoque carregada. Faça o upload do seu arquivo Excel na barra lateral (📁 Carregar / Atualizar Estoque).")
            else:
                st.write("### Código do Produto (etiqueta ou manual)")
                codigo_busca = st.text_input("Ex: 1234-5678 ou etiqueta 912TEIM0192Z — Enter para buscar", placeholder="Digite o código aqui...")
                
                if codigo_busca:
                    df_sistema = st.session_state.base_sistema
                    produto_encontrado = df_sistema[df_sistema.iloc[:, 0].astype(str).str.upper() == codigo_busca.upper()]
                    
                    if not produto_encontrado.empty:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.info(f"**CÓD. PRODUTO**\n### {codigo_busca.upper()}")
                        with col2:
                            desc = produto_encontrado.iloc[0, 1] if len(produto_encontrado.columns) > 1 else "Sem Descrição"
                            local = produto_encontrado.iloc[0, 3] if len(produto_encontrado.columns) > 3 else "Não Informado"
                            st.write(f"**Descrição:** {desc}")
                            st.write(f"**Local:** {local}")
                        with col3:
                            qtd_sis = produto_encontrado.iloc[0, 4] if len(produto_encontrado.columns) > 4 else 0
                            st.metric(label="QTD SISTEMA", value=int(qtd_sis))
                        
                        st.markdown("---")
                        qtd_fisica = st.number_input("Estoque Físico Encontrado", min_value=0, value=0, step=1)
                        
                        if st.button("💾 Salvar Contagem", type="primary"):
                            st.session_state.contagens[codigo_busca.upper()] = {
                                "quantidade_contada": qtd_fisica,
                                "quantidade_sistema": int(qtd_sis),
                                "descricao": desc
                            }
                            st.success(f"Contagem do item {codigo_busca.upper()} salva!")
                    else:
                        st.error("Produto não encontrado na base de dados.")

        # ABA 2: CONTAGEM ATUAL (RELATÓRIO DE DIVERGÊNCIAS)
        with aba_atual:
            if not st.session_state.contagens:
                st.info("Nenhum item foi contado neste inventário ainda.")
            else:
                st.write("### Relatório de Divergências em Tempo Real")
                df_relatorio = pd.DataFrame.from_dict(st.session_state.contagens, orient='index').reset_index()
                df_relatorio.columns = ['Código', 'Físico', 'Sistema', 'Descrição']
                
                df_relatorio['Divergência'] = df_relatorio['Físico'] - df_relatorio['Sistema']
                itens_com_divergencia = df_relatorio[df_relatorio['Divergência'] != 0]
                
                # Cards de Resumo Estilizados
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📦 ITENS CONTADOS", len(df_relatorio))
                c2.metric("⚠️ COM DIVERGÊNCIA", len(itens_com_divergencia))
                c3.metric("🔢 QTD TOTAL CONTADA", int(df_relatorio['Físico'].sum()))
                c4.metric("💻 QTD TOTAL SISTEMA", int(df_relatorio['Sistema'].sum()))
                
                porcentagem_erro = (len(itens_com_divergencia) / len(df_relatorio)) * 100
                st.warning(f"⚠️ {len(itens_com_divergencia)} itens com divergência ({porcentagem_erro:.1f}% do total contado)")
                
                st.markdown("---")
                st.dataframe(df_relatorio, use_container_width=True)

        # ABA 3: HISTÓRICO DE INVENTÁRIOS
        with aba_historico:
            st.write("### Histórico de Inventários Registrados")
            df_hist = pd.DataFrame(st.session_state.inventarios)
            st.dataframe(df_hist, use_container_width=True)

        # ABA 4: BASE DE ESTOQUE
        with aba_base:
            st.write("### Dados Originais do Sistema Importado")
            if st.session_state.base_sistema is not None:
                st.dataframe(st.session_state.base_sistema, use_container_width=True)
            else:
                st.warning("Nenhuma planilha Excel ativa no sistema.")
