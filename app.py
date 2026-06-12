import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico", layout="wide")

# --- ESTILIZAÇÃO PERSONALIZADA (Idêntica aos Prints) ---
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
    /* Barra de pesquisa com foco em laranja */
    .stTextInput input:focus {
        border-color: #e65100 !important;
        box-shadow: 0 0 0 1px #e65100 !important;
    }
    /* Cards escuros da barra lateral */
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
if 'base_sistema' not in st.session_state:
    st.session_state.base_sistema = None
if 'inventarios' not in st.session_state:
    st.session_state.inventarios = []
if 'contagens_por_inventario' not in st.session_state:
    # Estrutura para separar as contagens de cada inventário criado
    st.session_state.contagens_por_inventario = {}
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 1
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
    
    # 1. BARRA LATERAL (SIDEBAR)
    with st.sidebar:
        st.write("📂 **Carregar Base de Dados (Saldo)**")
        arquivo_excel = st.file_uploader("Suba o arquivo Excel do sistema (.xlsx)", type=["xlsx"], label_visibility="collapsed")
        if arquivo_excel is not None and st.session_state.base_sistema is None:
            st.session_state.base_sistema = pd.read_excel(arquivo_excel)
            st.toast("Base de dados (Saldo) carregada com sucesso!")
            st.rerun()
            
        st.markdown("---")
        st.write("📁 **Selecione ou Crie um Inventário**")
        
        if not st.session_state.inventarios:
            st.info("Nenhum inventário ativo. Crie um abaixo para iniciar.")
            id_inventario_atual = None
        else:
            lista_inv = [f"{i['id']} – {i['nome']}" for i in st.session_state.inventarios]
            inventario_selecionado = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
            id_inventario_atual = inventario_selecionado.split(" – ")[0]

        # Criar novo inventário
        with st.expander("➕ Novo Inventário", expanded=not st.session_state.inventarios):
            with st.form("form_novo", clear_on_submit=True):
                novo_nome = st.text_input("Nome do Inventário")
                botao_criar = st.form_submit_button("Criar", type="primary")
                if botao_criar and novo_nome:
                    novo_id = f"#{len(st.session_state.inventarios) + 39}"
                    hoje = datetime.date.today().strftime("%Y-%m-%d")
                    st.session_state.inventarios.append({"id": novo_id, "nome": novo_nome, "data": hoje})
                    # Inicializa o pote de contagem vazio para este novo inventário
                    st.session_state.contagens_por_inventario[novo_id] = {}
                    st.toast(f"Inventário {novo_id} Criado!")
                    st.rerun()

        st.markdown("---")
        st.write("👤 **Operador**")
        nome_operador = st.text_input("Seu nome", value=st.session_state.operador, key="op_input", label_visibility="collapsed")

        # --- LÓGICA DE MÉTRICAS DINÂMICAS VINCULADAS AO INVENTÁRIO ATUAL ---
        total_itens_base = 0
        total_contados = 0
        total_pendentes = 0
        progresso = 0.0

        # Se houver uma base carregada E um inventário ativo selecionado
        if st.session_state.base_sistema is not None and id_inventario_atual is not None:
            total_itens_base = len(st.session_state.base_sistema)
            # Puxa apenas as contagens realizadas DENTRO deste inventário específico
            contagens_atuais = st.session_state.contagens_por_inventario.get(id_inventario_atual, {})
            total_contados = len(contagens_atuais)
            total_pendentes = max(0, total_itens_base - total_contados)
            if total_itens_base > 0:
                progresso = total_contados / total_itens_base

        st.markdown("---")
        st.markdown(f'<div class="card-lateral"><div class="card-titulo">📋 ITENS NA BASE</div><div class="card-valor">{total_itens_base}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-titulo">✅ CONTADOS</div><div class="card-valor">{total_contados}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-titulo">⏳ PENDENTES</div><div class="card-valor">{total_pendentes}</div></div>', unsafe_allow_html=True)
        
        st.write("**PROGRESSO DA CONTAGEM**")
        st.progress(progresso)
        st.caption(f"{progresso*100:.1f}% concluído")

    # 2. PAINEL PRINCIPAL
    st.title("📋 Painel de Controle de Estoque")
    st.caption("Tel Telecomunicações · Painel de Auditoria Ativa")
    
    # Abas estruturadas
    aba_contar, aba_atual, aba_base, aba_graficos = st.tabs([
        "🔍 Contar Item", 
        "📊 Contagem Atual", 
        "📄 Base de Estoque",
        "🏆 Desempenho da Equipe"
    ])
    
    # VERIFICAÇÃO SE FLUXO INICIAL FOI SEGUIDO
    if st.session_state.base_sistema is None:
        st.warning("⚠️ Passo 1 pendente: Faça o upload do arquivo de Saldo na barra lateral para alimentar a base.")
    elif id_inventario_atual is None:
        st.warning("⚠️ Passo 2 pendente: Crie um Novo Inventário na barra lateral para vincular as contagens à base.")
    else:
        # Puxa o dicionário de contagens do inventário ativo selecionado
        contagens_mutaveis = st.session_state.contagens_por_inventario[id_inventario_atual]
        
        # --- ABA 1: CONTAR ITEM ---
        with aba_contar:
            st.write("### Registrar Contagem Física")
            cod_bipado = st.text_input("Digite ou Bipe o Código do Produto para Buscar na Base", key="bip")
            
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
                        st.metric("Quantidade no Sistema (Saldo)", int(qtd_sis))
                    
                    st.markdown("---")
                    qtd_fisica = st.number_input("Digite a Quantidade Física Encontrada", min_value=0, step=1)
                    if st.button("Incluir Item Contado", type="primary"):
                        # Salva a contagem isolada dentro do respectivo inventário ativo
                        contagens_mutaveis[cod_bipado.upper()] = {
                            "Físico": qtd_fisica,
                            "Sistema": int(qtd_sis),
                            "Descrição": item.iloc[0][desc_col]
                        }
                        st.success(f"Item {cod_bipado.upper()} adicionado às contagens!")
                        st.rerun()
                else:
                    st.error("Código não localizado no Saldo importado.")

        # --- ABA 2: CONTAGEM ATUAL (RELATÓRIO DE DIVERGÊNCIAS) ---
        with aba_atual:
            if not contagens_mutaveis:
                st.info("Nenhum item foi auditado neste inventário corrente.")
            else:
                df_contado = pd.DataFrame.from_dict(contagens_mutaveis, orient='index').reset_index()
                df_contado.columns = ['Cód. Produto', 'Estoque Físico', 'Qtd Estoque', 'Desc. Produto']
                df_contado['Divergência'] = df_contado['Estoque Físico'] - df_contado['Qtd Estoque']
                
                st.write("### Itens Auditados e Divergências Calculadas")
                st.dataframe(df_contado, use_container_width=True)

        # --- ABA 3: BASE DE ESTOQUE ---
        with aba_base:
            df_visualizacao = st.session_state.base_sistema.copy()
            
            filtro_estoque = st.selectbox("Filtrar por Estoque Físico", ["Todos", "Apenas Pendentes", "Apenas Contados"])
            pesquisa = st.text_input("🔍 Pesquisar (código ou descrição)", placeholder="Filtre rapidamente a lista...")
            
            col_cod = 'Cód. Produto' if 'Cód. Produto' in df_visualizacao.columns else df_visualizacao.columns[0]
            col_desc = 'Desc. Produto' if 'Desc. Produto' in df_visualizacao.columns else df_visualizacao.columns[1]
            
            # O status de Pendente/Contado avalia diretamente o inventário selecionado
            df_visualizacao['Status'] = df_visualizacao[col_cod].apply(
                lambda x: "✅ Contado" if str(x).upper() in contagens_mutaveis else "⏳ Pendente"
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
            
            cols = ['Status'] + [c for c in df_visualizacao.columns if c != 'Status']
            df_visualizacao = df_visualizacao[cols]
            
            st.markdown("---")
            col_inf, col_sli = st.columns([2, 2])
            with col_inf:
                st.caption(f"{len(df_visualizacao)} itens listados na base de dados ativa.")
            with col_sli:
                itens_por_pagina = st.slider("Itens por página", min_value=10, max_value=100, value=50, step=10)
            
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
