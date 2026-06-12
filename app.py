import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico", layout="wide")

# --- ESTILIZAÇÃO PERSONALIZADA (Identificação Visual com os Prints) ---
st.markdown("""
    <style>
    /* Botões primários laranjas */
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
    /* Estilização da barra de pesquisa com borda laranja ao focar */
    .stTextInput input:focus {
        border-color: #e65100 !important;
        box-shadow: 0 0 0 1px #e65100 !important;
    }
    /* Cards customizados para a barra lateral */
    .card-lateral {
        background-color: #1a233a;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 12px;
        border-left: 4px solid #2563eb;
    }
    .card-titulo {
        color: #93c5fd;
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 1px;
        margin-bottom: 2px;
    }
    .card-valor {
        color: white;
        font-size: 28px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- BANCO DE DADOS EM MEMÓRIA DA SESSÃO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'inventarios' not in st.session_state:
    st.session_state.inventarios = [{"id": "#39", "nome": "TEste JBA", "data": "2026-06-12", "status": "Aberto"}]
if 'base_sistema' not in st.session_state:
    st.session_state.base_sistema = None
if 'contagens' not in st.session_state:
    st.session_state.contagens = {}
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 1
if 'historico_equipe' not in st.session_state:
    # Dados para o gráfico de desempenho da equipe
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
    # --- CÁLCULO DE MÉTRICAS DA BARRA LATERAL ---
    total_itens_base = 0
    total_contados = 0
    total_pendentes = 0
    progresso = 0.0

    if st.session_state.base_sistema is not None:
        total_itens_base = len(st.session_state.base_sistema)
        total_contados = len(st.session_state.contagens)
        total_pendentes = max(0, total_itens_base - total_contados)
        if total_itens_base > 0:
            progresso = total_contados / total_itens_base

    # 1. BARRA LATERAL (SIDEBAR)
    with st.sidebar:
        st.write("📁 **Selecione o inventário**")
        lista_inv = [f"{i['id']} – {i['nome']} ({i['data']})" for i in st.session_state.inventarios]
        inventario_selecionado = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
        
        with st.expander("➕ Novo Inventário", expanded=False):
            with st.form("form_novo", clear_on_submit=True):
                novo_nome = st.text_input("Nome")
                botao_criar = st.form_submit_button("Criar", type="primary")
                if botao_criar:
                    if novo_nome:
                        novo_id = f"#{len(st.session_state.inventarios) + 39}"
                        hoje = datetime.date.today().strftime("%Y-%m-%d")
                        st.session_state.inventarios.append({"id": novo_id, "nome": novo_nome, "data": hoje, "status": "Aberto"})
                        st.rerun()

        if st.button("🔒 Fechar inventário atual", use_container_width=True):
            st.sidebar.warning("Inventário finalizado.")

        st.markdown("---")
        st.write("👤 **Operador**")
        nome_operador = st.text_input("Seu nome", value=st.session_state.operador, key="op_input", label_visibility="collapsed")
        
        # INDICADORES LATERAIS ESTILIZADOS COMO NOS PRINTS
        st.markdown("---")
        st.markdown(f'<div class="card-lateral"><div class="card-titulo">📋 ITENS NA BASE</div><div class="card-valor">{total_itens_base}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-titulo">✅ CONTADOS</div><div class="card-valor">{total_contados}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-titulo">⏳ PENDENTES</div><div class="card-valor">{total_pendentes}</div></div>', unsafe_allow_html=True)
        
        st.write("**PROGRESSO DA CONTAGEM**")
        st.progress(progresso)
        st.caption(f"{progresso*100:.1f}% concluído")

        st.markdown("---")
        with st.expander("📁 Carregar / Atualizar Estoque", expanded=False):
            arquivo_excel = st.file_uploader("Suba o arquivo (.xlsx)", type=["xlsx"])
            if arquivo_excel is not None:
                st.session_state.base_sistema = pd.read_excel(arquivo_excel)
                st.toast("Base importada com sucesso!")
                st.rerun()

    # 2. PAINEL PRINCIPAL
    st.title("📋 Painel de Controle de Estoque")
    st.caption("Tel Telecomunicações · Painel de Auditoria Ativa")
    
    aba_contar, aba_atual, aba_base, aba_graficos = st.tabs([
        "🔍 Contar Item", 
        "📊 Contagem Atual", 
        "📄 Base de Estoque",
        "🏆 Desempenho da Equipe"
    ])
    
    # --- ABA 1: CONTAR ITEM ---
    with aba_contar:
        if st.session_state.base_sistema is None:
            st.warning("⚠️ Nenhuma base carregada. Faça o upload do Excel na barra lateral para começar.")
        else:
            st.write("### Registrar Contagem Física")
            cod_bipado = st.text_input("Digite ou Bipe o Código do Produto", key="bip")
            
            if cod_bipado:
                df = st.session_state.base_sistema
                col_cod = 'Cód. Produto' if 'Cód. Produto' in df.columns else df.columns[0]
                item = df[df[col_cod].astype(str).str.upper() == cod_bipado.upper()]
                
                if not item.empty:
                    col_col1, col_col2 = st.columns(2)
                    with col_col1:
                        desc_col = 'Desc. Produto' if 'Desc. Produto' in df.columns else df.columns[1]
                        st.info(f"**Produto:** {item.iloc[0][desc_col]}")
                    with col_col2:
                        qtd_col = 'Qtd Estoque' if 'Qtd Estoque' in df.columns else df.columns[4]
                        qtd_sis = item.iloc[0][qtd_col]
                        st.metric("Quantidade no Sistema", int(qtd_sis))
                    
                    qtd_fisica = st.number_input("Digite a Quantidade Física Encontrada", min_value=0, step=1)
                    if st.button("Incluir Item Contado", type="primary"):
                        st.session_state.contagens[cod_bipado.upper()] = {
                            "Físico": qtd_fisica,
                            "Sistema": int(qtd_sis),
                            "Descrição": item.iloc[0][desc_col]
                        }
                        st.success("Item contabilizado!")
                        st.rerun()
                else:
                    st.error("Código não encontrado na base de dados.")

    # --- ABA 2: CONTAGEM ATUAL ---
    with aba_atual:
        if not st.session_state.contagens:
            st.info("Nenhum item foi contado ainda neste inventário.")
        else:
            df_contado = pd.DataFrame.from_dict(st.session_state.contagens, orient='index').reset_index()
            df_contado.columns = ['Cód. Produto', 'Estoque Físico', 'Qtd Estoque', 'Desc. Produto']
            df_contado['Divergência'] = df_contado['Estoque Físico'] - df_contado['Qtd Estoque']
            
            st.write("### Itens Diferenciados")
            st.dataframe(df_contado, use_container_width=True)

    # --- ABA 3: BASE DE ESTOQUE ---
    with aba_base:
        if st.session_state.base_sistema is None:
            st.info("Aguardando upload da planilha de estoque na barra lateral.")
        else:
            df_visualizacao = st.session_state.base_sistema.copy()
            
            # Filtro dropdown superior
            filtro_estoque = st.selectbox("Filtrar por Estoque Físico", ["Todos", "Apenas Pendentes", "Apenas Contados"])
            
            # Barra de pesquisa
            pesquisa = st.text_input("🔍 Pesquisar (código ou descrição)", placeholder="Digite um termo para filtrar...")
            
            col_cod = 'Cód. Produto' if 'Cód. Produto' in df_visualizacao.columns else df_visualizacao.columns[0]
            col_desc = 'Desc. Produto' if 'Desc. Produto' in df_visualizacao.columns else df_visualizacao.columns[1]
            
            df_visualizacao['Status'] = df_visualizacao[col_cod].apply(
                lambda x: "✅ Contado" if str(x).upper() in st.session_state.contagens else "⏳ Pendente"
            )
            
            if filtro_estoque == "Apenas Pendentes":
                df_visualizacao = df_visualizacao[df_visualizacao['Status'] == "⏳ Pendente"]
            elif filtro_estoque == "Apenas Contados":
                df_visualizacao = df_visualizacao[df_visualizacao['Status'] == "✅ Contado"]
                
            if pesquisa:
                df_visualizacao = df_visualizacao[
                    df_visualizacao[col_cod].astype(str).str.contains(pesquisa, case=False) | 
                    df_visualizacao[col_desc].astype(str).str.contains(pesquisa, case=False)
                ]
            
            # Reposiciona o status na primeira coluna
            cols = ['Status'] + [c for c in df_visualizacao.columns if c != 'Status']
            df_visualizacao = df_visualizacao[cols]
            
            st.markdown("---")
            col_inf, col_sli = st.columns([2, 2])
            with col_inf:
                st.caption(f"{len(df_visualizacao)} itens encontrados | Arquivo ativo")
            with col_sli:
                itens_por_pagina = st.slider("Itens por página", min_value=10, max_value=100, value=50, step=10)
            
            # Paginação estruturada
            total_linhas = len(df_visualizacao)
            total_paginas = max(1, (total_linhas + itens_por_pagina - 1) // itens_por_pagina)
            
            col_ant, col_pag, col_prox = st.columns([1, 2, 1])
            with col_ant:
                if st.button("◀ Anterior", use_container_width=True) and st.session_state.pagina_atual > 1:
                    st.session_state.pagina_atual -= 1
                    st.rerun()
            with col_pag:
                st.markdown(f"<p style='text-align: center; font-weight: bold;'>Página {st.session_state.pagina_atual} de {total_paginas}</p>", unsafe_allow_html=True)
            with col_prox:
                if st.button("Próxima ▶", use_container_width=True) and st.session_state.pagina_atual < total_paginas:
                    st.session_state.pagina_atual += 1
                    st.rerun()
            
            inicio = (st.session_state.pagina_atual - 1) * itens_por_pagina
            fim = inicio + itens_por_pagina
            
            st.dataframe(df_visualizacao.iloc[inicio:fim], use_container_width=True)

    # --- ABA 4: GRÁFICO DA EQUIPE ---
    with aba_graficos:
        st.write("### 🏆 Ranking de Inventários por Operador")
        df_equipe = st.session_state.historico_equipe.copy()
        if total_contados > 0:
            if nome_operador in df_equipe['Operador'].values:
                df_equipe.loc[df_equipe['Operador'] == nome_operador, 'Inventários Feitos'] += 1
            else:
                novo_op = pd.DataFrame({'Operador': [nome_operador], 'Inventários Feitos': [1]})
                df_equipe = pd.concat([df_equipe, novo_op], ignore_index=True)
        df_equipe = df_equipe.sort_values(by='Inventários Feitos', ascending=False)
        st.bar_chart(data=df_equipe, x='Operador', y='Inventários Feitos', color="#e65100")
