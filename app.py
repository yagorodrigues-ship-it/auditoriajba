import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico", layout="wide")

# --- ESTILIZAÇÃO PERSONALIZADA (Identificação Estrita com os Prints) ---
st.markdown("""
    <style>
    /* Botões laranjas largos de confirmação e busca */
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
    /* Blocos informativos azuis claros superiores */
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
    /* Banner de aviso/alerta laranja do relatório */
    .alerta-divergencia {
        background-color: #fef5e7;
        border: 1px solid #f9e79f;
        border-left: 5px solid #f39c12;
        padding: 15px;
        border-radius: 4px;
        margin-top: 10px;
        margin-bottom: 20px;
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
    st.session_state.inventarios = []
if 'contagens_por_inventario' not in st.session_state:
    st.session_state.contagens_por_inventario = {}
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 1
if 'operador' not in st.session_state:
    st.session_state.operador = ""
if 'id_counter' not in st.session_state:
    st.session_state.id_counter = 804
if 'reset_bip' not in st.session_state:
    st.session_state.reset_bip = False
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
                    st.session_state.contagens_por_inventario[novo_id] = []
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
            lista_contagens_atuais = st.session_state.contagens_por_inventario.get(id_inventario_atual, [])
            total_contados = len(lista_contagens_atuais)
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
        lista_contagens_mutaveis = st.session_state.contagens_por_inventario.get(id_inventario_atual, [])
        df_exemplo = st.session_state.base_sistema
        
        # --- DEFINIÇÃO DO MAPA INTELIGENTE DE COLUNAS ---
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
                st.error("🔒 Este inventário está Fechado. Selecione ou crie um inventário Aberto na barra lateral.")
            else:
                c_busca, c_filtro, c_limpar = st.columns([5, 3, 2])
                with c_busca:
                    valor_padrao = ""
                    if st.session_state.reset_bip:
                        st.session_state.reset_bip = False
                        st.rerun()
                        
                    codigo_input = st.text_input("💻 Código do Produto (etiqueta ou manual)", value=valor_padrao, placeholder="Ex: 1234-5678 ou etiqueta — Enter para buscar", key="input_bip_chave")
                with c_filtro:
                    st.selectbox("📍 Estoque Físico", ["Todos"], key="sel_est_fisico")
                with c_limpar:
                    st.write("") 
                    if st.button("🗑️ Limpar", use_container_width=True, key="clear_btn"):
                        st.session_state.reset_bip = True
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
                        
                        # Renderização dos Cards Informativos Superiores
                        b1, b2, b3, b4 = st.columns(4)
                        with b1:
                            st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">CÓD. PRODUTO</div><div class="bloco-valor">{codigo_input.upper()}</div></div>', unsafe_allow_html=True)
                        with b2:
                            st.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:0px;"><div class="bloco-titulo">ESTOQUE FÍSICO</div><div class="bloco-valor" style="font-size:22px;">{local_val}</div></div>', unsafe_allow_html=True)
                        with b3:
                            st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">UNID. MEDIDA</div><div class="bloco-valor">{unid_val}</div></div>', unsafe_allow_html=True)
                        with b4:
                            st.markdown('<div class="bloco-info"><div class="bloco-titulo">STATUS</div><div class="bloco-valor" style="color:#2ecc71;">● Ativo</div></div>', unsafe_allow_html=True)
                        
                        st.markdown(f"**Descrição:** {desc_val}")
                        st.markdown(f"**Local:** {local_val}")
                        
                        st.markdown(f'<div class="card-sistema"><div class="bloco-titulo">QTD SISTEMA</div><div style="font-size:32px; font-weight:bold; color:#1f2c3f;">{qtd_sis}</div></div>', unsafe_allow_html=True)
                        
                        with st.form("confirmar_contagem_form", clear_on_submit=True):
                            qtd_fisica = st.number_input("📦 Quantidade contada fisicamente", min_value=0, step=1, value=0)
                            
                            # Campo obrigatório para inserção do Ativo (Identificador Único)
                            ativo_input = st.text_input("🔢 Número do Ativo / Patrimônio (Obrigatório)", placeholder="Digite o número do ativo único gravado neste item físico...")
                            
                            observacao = st.text_input("📝 Observação (opcional)", placeholder="Notas adicionais sobre o produto...")
                            btn_confirmar = st.form_submit_button("✓ Confirmar Contagem", type="primary", use_container_width=True)
                            
                            if btn_confirmar:
                                if not ativo_input.strip():
                                    st.error("❌ Erro: A inclusão do número de Ativo é obrigatória para este lançamento!")
                                else:
                                    st.session_state.id_counter += 1
                                    agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    
                                    lote_val = ""
                                    if 'lote' in item.columns:
                                        lote_val = str(item.iloc[0]['lote'])
                                    elif 'Lote' in item.columns:
                                        lote_val = str(item.iloc[0]['Lote'])
                                    
                                    # GERAÇÃO DA LINHA DISCRIMINADA EXCLUSIVA (Evita agrupar ou somar linhas iguais)
                                    novo_registro = {
                                        "id": st.session_state.id_counter,
                                        "inventario_id": int(id_inventario_atual.replace("#", "")),
                                        "id_estoque": 1118,
                                        "desc_estoque": local_val,
                                        "cod_produto": codigo_input.upper().strip(),
                                        "desc_produto": desc_val,
                                        "unid_medida": unid_val,
                                        "qtd_sistema": qtd_sis,
                                        "qtd_contada": qtd_fisica,
                                        "diferenca": qtd_fisica - qtd_sis,
                                        "ativo": ativo_input.strip().upper(), 
                                        "observacao": observacao,
                                        "operador": st.session_state.operador if st.session_state.operador else "admin",
                                        "data_hora": agora,
                                        "lote": lote_val
                                    }
                                    
                                    lista_contagens_mutaveis.insert(0, novo_registro)
                                    st.session_state.contagens_por_inventario[id_inventario_atual] = lista_contagens_mutaveis
                                    st.toast(f"Lançamento do Ativo {ativo_input.upper()} computado isoladamente!")
                                    
                                    st.session_state.reset_bip = True
                                    st.rerun()
                    else:
                        st.error("Código do produto não localizado na base de dados (Saldo).")

        # --- ABA 2: CONTAGEM ATUAL (RELATÓRIO DISCRIMINADO) ---
        with aba_atual:
            st.subheader(f"Inventário: {id_inventario_atual} – {inventario_selecionado_obj['nome']} ({inventario_selecionado_obj['data']})")
            
            if not lista_contagens_mutaveis:
                st.info("Nenhum item foi auditado neste inventário corrente.")
            else:
                df_relatorio = pd.DataFrame(lista_contagens_mutaveis)
                
                total_auditado = len(df_relatorio)
                itens_divergentes = len(df_relatorio[df_relatorio['diferenca'] != 0])
                soma_contada = int(df_relatorio['qtd_contada'].sum())
                soma_sistema = int(df_relatorio['qtd_sistema'].sum())
                diferenca_acumulada = int(df_relatorio['diferenca'].sum())
                porcentagem_divergencia = (itens_divergentes / total_auditado) * 100 if total_auditado > 0 else 0
                
                r1, r2, r3, r4 = st.columns(4)
                with r1:
                    st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">📦 ITENS CONTADOS</div><div class="bloco-valor">{total_auditado}</div></div>', unsafe_allow_html=True)
                with r2:
                    st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">⚠️ COM DIVERGÊNCIA</div><div class="bloco-valor">{itens_divergentes}</div></div>', unsafe_allow_html=True)
                with r3:
                    st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">🔢 QTD TOTAL CONTADA</div><div class="bloco-valor">{soma_contada}</div></div>', unsafe_allow_html=True)
                with r4:
                    st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">🗄️ QTD TOTAL SISTEMA</div><div class="bloco-valor">{soma_sistema}</div><div style="font-size:12px; color:#e74c3c; font-weight:bold;">↓ {diferenca_acumulada}</div></div>', unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div class="alerta-divergencia">
                        <strong>⚠️ {itens_divergentes} item(ns) com divergência ({porcentagem_divergencia:.0f}% do total)</strong><br>
                        <span style="color:#7f8c8d; font-size:13px;">Diferença acumulada: {diferenca_acumulada} unidades</span>
                    </div>
                """, unsafe_allow_html=True)
                
                st.write("Filtrar estoque")
                st.selectbox("Filtro", ["Todos"], label_visibility="collapsed", key="filtro_rel_drop")
                
                ordem_colunas_print = [
                    'id', 'inventario_id', 'id_estoque', 'desc_estoque', 'cod_produto', 
                    'desc_produto', 'unid_medida', 'qtd_sistema', 'qtd_contada', 
                    'diferenca', 'ativo', 'observacao', 'operador', 'data_hora', 'lote'
                ]
                st.dataframe(df_relatorio[ordem_colunas_print], use_container_width=True, hide_index=True)
                
                # Exclusão individual usando o ID único gerado por linha (Permite apagar patrimônios específicos sem afetar outros do mesmo código)
                ids_para_remover = [int(x) for x in df_relatorio['id'].tolist()]
                id_para_remover = st.selectbox("Selecione um ID de linha para remover/excluir da contagem (se necessário):", [""] + ids_para_remover)
                if id_para_remover and st.button("🗑️ Excluir linha selecionada", type="secondary"):
                    lista_contagens_mutaveis = [x for x in lista_contagens_mutaveis if x['id'] != int(id_para_remover)]
                    st.session_state.contagens_por_inventario[id_inventario_atual] = lista_contagens_mutaveis
                    st.toast(f"Registro ID {id_para_remover} removido!")
                    st.rerun()

        # --- ABA 3: HISTÓRICO DE INVENTÁRIOS ---
        with aba_historico:
            st.write("### 📁 Histórico de Inventários")
            st.caption("None")
            
            for idx, inv in enumerate(st.session_state.inventarios):
                cor_bola = "🟢" if inv['status'] == "Aberto" else "🔴"
                detalhes_contagem = st.session_state.contagens_por_inventario.get(inv['id'], [])
                qtd_contada_inv = len(detalhes_contagem)
                
                with st.expander(f"{cor_bola} {inv['id']} – {inv['nome']} | {inv['data']} | {qtd_contada_inv} itens"):
                    st.write(f"**Status:** {inv['status']} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Início:** {inv['data']}", unsafe_allow_html=True)
                    
                    if not detalhes_contagem:
                        st.info("Nenhum item contado neste inventário.")
                        if st.button(f"🗑️ Excluir inventário vazio", key=f"del_vazio_{inv['id']}_{idx}"):
                            st.session_state.inventarios.remove(inv)
                            if inv['id'] in st.session_state.contagens_por_inventario:
                                del st.session_state.contagens_por_inventario[inv['id']]
                            st.toast(f"Inventário {inv['id']} removido com sucesso!")
                            st.rerun()
                    else:
                        df_hist_inv = pd.DataFrame(detalhes_contagem)
                        st.dataframe(df_hist_inv, use_container_width=True, hide_index=True)

        # --- ABA 4: BASE DE ESTOQUE ---
        with aba_base:
            df_visualizacao = st.session_state.base_sistema.copy()
            
            filtro_estoque = st.selectbox("Filtrar por Estoque Físico", ["Todos", "Apenas Pendentes", "Apenas Contados"], key="filtro_base_tab")
            pesquisa = st.text_input("🔍 Pesquisar (código ou descrição)", placeholder="Filtre por trechos de dados...", key="pesquisa_base_tab")
            
            codigos_contados_set = {x['cod_produto'] for x in lista_contagens_mutaveis}
            df_visualizacao['Status'] = df_visualizacao[col_cod].apply(
                lambda x: "✅ Contado" if str(x).upper().strip() in codigos_contados_set else "⏳ Pendente"
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
                st.caption(f"{len(df_visualizacao)} itens encontrados | Arquivo: {st.session_state.nome_arquivo_excel}")
            with col_sli:
                itens_por_pagina = st.slider("Itens por página", min_value=10, max_value=100, value=50, step=10, key="slider_pag")
            
            total_linhas = len(df_visualizacao)
            total_paginas = max(1, (total_linhas + itens_por_pagina - 1) // itens_por_pagina)
            
            col_ant, col_pag, col_prox = st.columns([1, 2, 1])
            with col_ant:
                if st.button("◀ Anterior", use_container_width=True, key="btn_ant") and st.session_state.pagina_atual > 1:
                    st.session_state.pagina_atual -= 1
                    st.rerun()
            with col_pag:
                st.markdown(f"<p style='text-align: center; font-weight: bold;'>Página {st.session_state.pagina_atual} de {total_paginas}</p>", unsafe_allow_html=True)
            with col_prox:
                if st.button("Próxima ▶", use_container_width=True, key="btn_prox") and st.session_state.pagina_atual < total_paginas:
                    st.session_state.pagina_atual += 1
                    st.rerun()
            
            inicio = (st.session_state.pagina_atual - 1) * itens_por_pagina
            fim = inicio + itens_por_pagina
            
            st.dataframe(df_visualizacao.iloc[inicio:fim], use_container_width=True)

        # --- ABA 5: DESEMPENHO DA EQUIPE ---
        with aba_graficos:
            st.write("### 🏆 Ranking de Inventários por Operador")
            df_equipe = st.session_state.historico_equipe.copy()
            df_equipe = df_equipe.sort_values(by='Inventários Feitos', ascending=False)
            st.bar_chart(data=df_equipe, x='Operador', y='Inventários Feitos', color="#d35400")
