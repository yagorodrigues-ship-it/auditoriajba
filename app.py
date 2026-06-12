import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico", layout="wide")

# --- ESTILIZAÇÃO PERSONALIZADA (Identificação com o design do print) ---
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

# --- BANCO DE DADOS EM MEMÓRIA - GARANTIA DE PERSISTÊNCIA ANTIQUEDA ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'base_sistema' not in st.session_state:
    st.session_state.base_sistema = None
if 'nome_arquivo_excel' not in st.session_state:
    st.session_state.nome_arquivo_excel = ""
if 'inventarios' not in st.session_state:
    st.session_state.inventarios = [
        {"id": "#39", "nome": "TEste JBA", "data": "2026-06-12", "status": "Fechado"}
    ]
if 'contagens_por_inventario' not in st.session_state:
    st.session_state.contagens_por_inventario = {"#39": {}}
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 1
if 'operador' not in st.session_state:
    st.session_state.operador = ""
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
                st.session_state.operador = "admin"
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
else:
    
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
        st.write("📁 **Selecione o inventário**")
        
        if not st.session_state.inventarios:
            st.info("Nenhum inventário ativo. Crie um abaixo para iniciar.")
            id_inventario_atual = None
            inventario_selecionado_obj = None
        else:
            lista_inv = [f"{i['id']} – {i['nome']} ({i['status']})" for i in st.session_state.inventarios]
            inventario_selected = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
            id_inventario_atual = inventario_selected.split(" – ")[0]
            inventario_selecionado_obj = next(i for i in st.session_state.inventarios if i['id'] == id_inventario_atual)

        # Criar novo inventário
        with st.expander("➕ Novo Inventário", expanded=not st.session_state.inventarios):
            with st.form("form_novo", clear_on_submit=True):
                novo_nome = st.text_input("Nome do Inventário")
                botao_criar = st.form_submit_button("Criar", type="primary")
                if botao_criar and novo_nome:
                    novo_id = f"#{len(st.session_state.inventarios) + 39}"
                    hoje = datetime.date.today().strftime("%Y-%m-%d")
                    st.session_state.inventarios.insert(0, {"id": novo_id, "nome": novo_nome, "data": hoje, "status": "Aberto"})
                    st.session_state.contagens_por_inventario[novo_id] = {}
                    st.toast(f"Inventário {novo_id} Criado!")
                    st.rerun()

        # Botão Fechar Inventário Atual
        if inventario_selecionado_obj and inventario_selecionado_obj['status'] == "Aberto":
            if st.button("🔒 Fechar inventário atual", use_container_width=True):
                inventario_selecionado_obj['status'] = "Fechado"
                nome_op = st.session_state.operador if st.session_state.operador else "admin"
                df_eq = st.session_state.historico_equipe
                if nome_op in df_eq['Operador'].values:
                    st.session_state.historico_equipe.loc[df_eq['Operador'] == nome_op, 'Inventários Feitos'] += 1
                else:
                    novo_op = pd.DataFrame({'Operador': [nome_op], 'Inventários Feitos': [1]})
                    st.session_state.historico_equipe = pd.concat([st.session_state.historico_equipe, novo_op], ignore_index=True)
                st.toast("Inventário finalizado e fechado com sucesso!")
                st.rerun()

        st.markdown("---")
        st.write("👤 **Operador**")
        st.session_state.operador = st.text_input("Seu nome", value=st.session_state.operador, key="op_input_text", label_visibility="collapsed", placeholder="Seu nome")

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
        st.progress(progresso)
        st.caption(f"{progresso*100:.1f}% concluído")

    # 2. PAINEL PRINCIPAL
    st.title("📦 Painel Geral de Auditoria")
    st.caption("Tel Telecomunicações · Painel de Auditoria Ativa")
    
    aba_contar, aba_atual, aba_historico, aba_base, aba_graficos = st.tabs([
        "🔍 Contar Item", 
        "📊 Contagem Atual", 
        "📁 Histórico de Inventários",
        "📄 Base de Estoque",
        "🏆 Desempenho da Equipe"
    ])
    
    if st.session_state.base_sistema is None:
        st.warning("⚠️ Passo 1 pendente: Faça o upload do arquivo de Saldo na barra lateral para alimentar a base.")
    elif id_inventario_atual is None:
        st.warning("⚠️ Passo 2 pendente: Crie um Novo Inventário na barra lateral para vincular as contagens à base.")
    else:
        contagens_mutaveis = st.session_state.contagens_por_inventario.get(id_inventario_atual, {})
        df_exemplo = st.session_state.base_sistema
        
        colunas_reais = list(df_exemplo.columns)
        
        def encontrar_coluna(opcoes, default_idx):
            for opcao in opcoes:
                for col in colunas_reais:
                    if opcao.lower().replace(" ", "").replace(".", "") in col.lower().replace(" ", "").replace(".", ""):
                        return col
            return colunas_reais[default_idx] if default_idx < len(colunas_reais) else colunas_reais[0]

        col_cod = encontrar_coluna(['códproduto', 'codproduto', 'codigo', 'cod'], 0)
        col_desc = encontrar_coluna(['descproduto', 'descricao', 'desc'], 1)
        col_local = encontrar_coluna(['descestoquefisico', 'localizacao', 'local', 'estoquefisico'], 2)
        col_unidade = encontrar_coluna(['unidmedida', 'unidade', 'un'], 3)
        col_qtd = encontrar_coluna(['qtdestoque', 'quantidade', 'saldo', 'qtd'], -1)
        
        # --- ABA 1: CONTAR ITEM ---
        with aba_contar:
            if inventario_selecionado_obj and inventario_selecionado_obj['status'] == "Fechado":
                st.error("🔒 Este inventário está Fechado. Selecione ou crie um inventário Aberto na barra lateral para realizar novas contagens.")
            else:
                c_busca, c_filtro, c_limpar = st.columns([5, 3, 2])
                with c_busca:
                    codigo_input = st.text_input("💻 Código do Produto (etiqueta ou manual)", placeholder="Bipe ou digite o código aqui...", key="input_bip_chave")
                with c_filtro:
                    st.selectbox("📍 Estoque Físico", ["Todos"], key="sel_est_fisico")
                with c_limpar:
                    st.write("") 
                    if st.button("🗑️ Limpar", use_container_width=True, key="clear_btn"):
                        st.session_state.input_bip_chave = ""
                        st.rerun()
                
                if codigo_input:
                    serie_codigos = df_exemplo[col_cod].astype(str).str.upper().str.strip()
                    item = df_exemplo[serie_codigos == str(codigo_input).upper().strip()]
                    
                    if not item.empty:
                        unid_val = item.iloc[0][col_unidade] if col_unidade in item.columns else "UN"
                        desc_val = item.iloc[0][col_desc]
                        local_val = item.iloc[0][col_local] if col_local in item.columns else "Não Informado"
                        
                        raw_qtd_sis = item.iloc[0][col_qtd]
                        try:
                            qtd_sis = int(pd.to_numeric(raw_qtd_sis, errors='coerce'))
                            if pd.isna(qtd_sis):
                                qtd_sis = 0
                        except:
                            qtd_sis = 0
                        
                        b1, b2, b3, b4 = st.columns(4)
                        with b1:
                            st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">CÓD. PRODUTO</div><div class="bloco-valor">{codigo_input.upper()}</div></div>', unsafe_allow_html=True)
                        with b2:
                            st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">ESTOQUE FÍSICO</div><div class="bloco-valor">{local_val}</div></div>', unsafe_allow_html=True)
                        with b3:
                            st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">UNID. MEDIDA</div><div class="bloco-valor">{unid_val}</div></div>', unsafe_allow_html=True)
                        with b4:
                            st.markdown('<div class="bloco-info"><div class="bloco-titulo">STATUS</div><div class="bloco-valor" style="color:#2ecc71;">● Ativo</div></div>', unsafe_allow_html=True)
                        
                        st.markdown(f"**Descrição:** {desc_val}")
                        st.markdown(f"**Local:** {local_val}")
                        
                        st.markdown(f'<div class="card-sistema"><div class="bloco-titulo">QTD SISTEMA</div><div style="font-size:32px; font-weight:bold; color:#1f2c3f;">{qtd_sis}</div></div>', unsafe_allow_html=True)
                        
                        with st.form("confirmar_contagem_form", clear_on_submit=True):
                            qtd_fisica = st.number_input("📦 Quantidade contada fisicamente", min_value=0, step=1, value=0)
                            observacao = st.text_input("📝 Observação (opcional)", placeholder="Notas adicionais sobre o produto...")
                            btn_confirmar = st.form_submit_button("✅ Confirmar Contagem", type="primary", use_container_width=True)
                            
                            if btn_confirmar:
                                contagens_mutaveis[codigo_input.upper().strip()] = {
                                    "Físico": qtd_fisica,
                                    "Sistema": qtd_sis,
                                    "Descrição": desc_val,
                                    "Observação": observacao
                                }
                                st.session_state.contagens_por_inventario[id_inventario_atual] = contagens_mutaveis
                                st.toast(f"Contagem do item {codigo_input.upper()} adicionada!")
                                st.rerun()
                    else:
                        st.error("Código do produto não localizado na base de dados (Saldo).")

        # --- ABA 2: CONTAGEM ATUAL (RELATÓRIO) ---
        with aba_atual:
            if not contagens_mutaveis:
                st.info("Nenhum item foi auditado neste inventário corrente.")
            else:
                # Botão para Excluir item individual da contagem atual
                st.write("### Itens Auditados e Divergências")
                df_contado = pd.DataFrame.from_dict(contagens_mutaveis, orient='index').reset_index()
                df_contado.columns = ['Cód. Produto', 'Estoque Físico', 'Qtd Estoque', 'Desc. Produto', 'Observação']
                df_contado['Divergência'] = df_contado['Estoque Físico'] - df_contado['Qtd Estoque']
                st.dataframe(df_contado, use_container_width=True)
                
                item_para_remover = st.selectbox("Selecione um código para remover/excluir a contagem (se necessário):", [""] + list(contagens_mutaveis.keys()))
                if item_para_remover and st.button("🗑️ Excluir contagem do item selecionado", type="secondary"):
                    del contagens_mutaveis[item_para_remover]
                    st.session_state.contagens_por_inventario[id_inventario_atual] = contagens_mutaveis
                    st.toast
