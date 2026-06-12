import streamlit as st
import pandas as pd
import datetime
import sqlite3
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico", layout="wide")

# --- BANCO DE DADOS PERMANENTE (SQLITE) ---
def conectar_banco():
    conn = sqlite3.connect('banco_inventario.db', check_same_thread=False)
    return conn

def inicializar_banco():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventarios (
            id TEXT PRIMARY KEY,
            nome TEXT,
            data TEXT,
            status TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventario_id TEXT,
            id_estoque INTEGER,
            desc_estoque TEXT,
            cod_produto TEXT,
            desc_produto TEXT,
            unid_medida TEXT,
            qtd_sistema INTEGER,
            qtd_contada INTEGER,
            diferenca INTEGER,
            ativo TEXT,
            observacao TEXT,
            operador TEXT,
            data_hora TEXT,
            lote TEXT
        )
    """)
    conn.commit()
    conn.close()

inicializar_banco()

# --- ESTILIZAÇÃO PERSONALIZADA ---
st.markdown("""
    <style>
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
    .card-sistema {
        background-color: #ebf5fb;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #d4e6f1;
        margin-top: 15px;
        margin-bottom: 25px;
    }
    .alerta-divergencia {
        background-color: #fef5e7;
        border: 1px solid #f9e79f;
        border-left: 5px solid #f39c12;
        padding: 15px;
        border-radius: 4px;
        margin-top: 10px;
        margin-bottom: 20px;
    }
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

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'base_sistema' not in st.session_state:
    st.session_state.base_sistema = None
if 'nome_arquivo_excel' not in st.session_state:
    st.session_state.nome_arquivo_excel = ""
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 1
if 'operador' not in st.session_state:
    st.session_state.operador = ""
if 'reset_bip' not in st.session_state:
    st.session_state.reset_bip = False

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
    conn = conectar_banco()
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios ORDER BY data DESC, id DESC", conn)
    
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
        
        if df_inventarios.empty:
            st.info("Nenhum inventário ativo. Crie um abaixo para iniciar.")
            id_inventario_atual = None
            inventario_selecionado_obj = None
        else:
            lista_inv = [f"{row['id']} – {row['nome']} ({row['status']})" for idx, row in df_inventarios.iterrows()]
            inventario_selected = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
            id_inventario_atual = inventario_selected.split(" – ")[0]
            inventario_selecionado_obj = df_inventarios[df_inventarios['id'] == id_inventario_atual].iloc[0]

        # Criar novo inventário
        with st.expander("➕ Novo Inventário", expanded=df_inventarios.empty):
            with st.form("form_novo", clear_on_submit=True):
                novo_nome = st.text_input("Nome do Inventário")
                botao_criar = st.form_submit_button("Criar", type="primary")
                if botao_criar and novo_nome:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM inventarios")
                    count = cursor.fetchone()[0]
                    novo_id = f"#{count + 39}"
                    hoje = datetime.date.today().strftime("%Y-%m-%d")
                    cursor.execute("INSERT INTO inventarios (id, nome, data, status) VALUES (?, ?, ?, ?)", 
                                   (novo_id, novo_nome, hoje, "Aberto"))
                    conn.commit()
                    st.toast(f"Inventário {novo_id} criado!")
                    st.rerun()

        if inventario_selecionado_obj is not None and inventario_selecionado_obj['status'] == "Aberto":
            if st.button("🔒 Fechar inventário atual", use_container_width=True):
                cursor = conn.cursor()
                cursor.execute("UPDATE inventarios SET status = 'Fechado' WHERE id = ?", (id_inventario_atual,))
                conn.commit()
                st.toast("Inventário finalizado e fechado com sucesso!")
                st.rerun()

        st.markdown("---")
        st.write("👤 **Operador**")
        st.session_state.operador = st.text_input("Seu nome", value=st.session_state.operador, key="op_input_text", label_visibility="collapsed", placeholder="Seu nome")

        # --- MAPEAMENTO INTELIGENTE DE COLUNAS ---
        col_cod, col_desc, col_local, col_unidade, col_qtd, col_ativo_base = "", "", "", "", "", ""
        if st.session_state.base_sistema is not None:
            colunas_reais = list(st.session_state.base_sistema.columns)
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
            col_ativo_base = encontrar_coluna(['ativo', 'patrimonio', 'numativo', 'id_estoque'], -1)

        # --- CÁLCULO DE PROGRESSO DINÂMICO E SEGURO ---
        total_itens_base = 0
        total_contados = 0
        total_pendentes = 0
        progresso = 0.0

        if st.session_state.base_sistema is not None and id_inventario_atual is not None:
            total_itens_base = len(st.session_state.base_sistema)
            df_contagens_atuais = pd.read_sql_query(f"SELECT * FROM contagens WHERE inventario_id = '{id_inventario_atual.replace('#','')}'", conn)
            
            contados_validos_set = set()
            for idx, c_row in df_contagens_atuais.iterrows():
                match_base = st.session_state.base_sistema[
                    st.session_state.base_sistema[col_cod].astype(str).str.upper().str.strip() == str(c_row['cod_produto']).upper().strip()
                ]
                if not match_base.empty:
                    # Varre todas as ocorrências possíveis daquele código no saldo para cruzar ativos corretos
                    ativos_validos_da_base = [str(x).upper().strip() for x in match_base[col_ativo_base].tolist() if col_ativo_base in match_base.columns]
                    
                    # Filtra apenas registros com ativos reais (ignora flags genéricas)
                    ativos_validos_da_base = [x for x in ativos_validos_da_base if x not in ["NAN", "SIM", "", "0", "0.0"]]
                    
                    if ativos_validos_da_base:
                        if str(c_row['ativo']).upper().strip() in ativos_validos_da_base:
                            contados_validos_set.add(str(c_row['cod_produto']).upper().strip())
                    else:
                        contados_validos_set.add(str(c_row['cod_produto']).upper().strip())
            
            total_contados = len(df_contagens_atuais)
            total_pendentes = max(0, total_itens_base - len(contados_validos_set))
            if total_itens_base > 0:
                progresso = min(1.0, len(contados_validos_set) / total_itens_base)

        st.markdown("---")
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">📋 ITENS NA BASE</div><div class="card-lateral-valor">{total_itens_base}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">✅ LANÇAMENTOS FEITOS</div><div class="card-lateral-valor">{total_contados}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">⏳ PENDENTES REAIS</div><div class="card-lateral-valor">{total_pendentes}</div></div>', unsafe_allow_html=True)
        
        st.write("**PROGRESSO DA CONTAGEM (ATIVOS CORRETOS)**")
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
        df_contagens_mutaveis = pd.read_sql_query(f"SELECT * FROM contagens WHERE inventario_id = '{id_inventario_atual.replace('#','')}' ORDER BY id DESC", conn)
        df_exemplo = st.session_state.base_sistema
        
        # --- ABA 1: CONTAR ITEM ---
        with aba_contar:
            if inventario_selecionado_obj is not None and inventario_selecionado_obj['status'] == "Fechado":
                st.error("🔒 Este inventário está Fechado. Selecione ou crie um inventário Aberto na barra lateral.")
            else:
                c_busca, c_filtro, c_limpar = st.columns([5, 3, 2])
                with c_busca:
                    if st.session_state.reset_bip:
                        st.session_state.reset_bip = False
                        st.rerun()
                    codigo_input = st.text_input("💻 Código do Produto (etiqueta ou manual)", placeholder="Ex: TEAT0139Z — Enter para buscar", key="input_bip_chave")
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
                            if pd.isna(qtd_sis): qtd_sis = 0
                        except:
                            qtd_sis = 0
                        
                        # Lista todos os ativos válidos desse mesmo código na base
                        ativos_da_base_lista = [str(x).upper().strip() for x in item[col_ativo_base].tolist() if col_ativo_base in item.columns]
                        ativos_da_base_lista = [x for x in list(set(ativos_da_base_lista)) if x not in ["NAN", "SIM", "", "0", "0.0"]]

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
                        
                        if ativos_da_base_lista:
                            st.info(f"📋 **Nota de Sistema:** Este item possui ativos mapeados no saldo. Ativos válidos: {', '.join(ativos_da_base_lista)}")
                        else:
                            st.caption("ℹ️ **Nota:** Linhas de ativo zeradas ou ausentes para este item no Excel (Campo Opcional).")
                        
                        st.markdown(f'<div class="card-sistema"><div class="bloco-titulo">QTD SISTEMA</div><div style="font-size:32px; font-weight:bold; color:#1f2c3f;">{qtd_sis}</div></div>', unsafe_allow_html=True)
                        
                        with st.form("confirmar_contagem_form", clear_on_submit=True):
                            qtd_fisica = st.number_input("📦 Quantidade contada fisicamente", min_value=0, step=1, value=1)
                            
                            rotulo_ativo = "🔢 Número do Ativo / Patrimônio (Obrigatório)" if ativos_da_base_lista else "🔢 Número do Ativo / Patrimônio (Opcional - Linha Zerada)"
                            ativo_input = st.text_input(rotulo_ativo, placeholder="Insira o número de identificação do ativo...")
                            
                            observacao = st.text_input("📝 Observação (opcional)")
                            btn_confirmar = st.form_submit_button("✓ Confirmar Contagem", type="primary", use_container_width=True)
                            
                            if btn_confirmar:
                                ativo_digitado_limpo = ativo_input.strip().upper()
                                
                                if高度_da_base_lista = ativos_da_base_lista # alias
                                if ativos_da_base_lista and not ativo_digitado_limpo:
                                    st.error("❌ Erro: O preenchimento do número de Ativo é obrigatório para este item!")
                                else:
                                    agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    lote_val = str(item.iloc[0]['lote']) if 'lote' in item.columns else ""
                                    
                                    # --- CORREÇÃO CIRÚRGICA DE VALIDAÇÃO ISOLADA ---
                                    qtd_sistema_calculada = qtd_sis
                                    
                                    if高度_da_base_lista: # se o item exige controle estrito por ativos
                                        if ativo_digitado_limpo in高度_da_base_lista:
                                            # Se o patrimônio bate perfeitamente, valida contra a linha correspondente dele
                                            linha_especifica = item[item[col_ativo_base].astype(str).str.upper().str.strip() == ativo_digitado_limpo]
                                            try:
                                                qtd_sistema_calculada = int(pd.to_numeric(linha_especifica.iloc[0][col_qtd], errors='coerce'))
                                            except:
                                                qtd_sistema_calculada = 1
                                        else:
                                            # CORREÇÃO DO PROBLEMA DO USUÁRIO: Se o ativo for inválido/errado de propósito, 
                                            # ele gera 0 no sistema de forma ISOLADA para aquela linha, gerando divergência só nele!
                                            qtd_sistema_calculada = 0
                                            
                                    dif_calculada = qtd_fisica - qtd_sistema_calculada
                                    
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, observacao, operador, data_hora, lote)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (id_inventario_atual.replace("#",""), 1118, local_val, codigo_input.upper().strip(), desc_val, unid_val, qtd_sistema_calculada, qtd_fisica, dif_calculada, ativo_digitado_limpo, observacao, st.session_state.operador, agora, lote_val))
                                    conn.commit()
                                    
                                    st.toast(f"Lançamento processado e armazenado de forma isolada!")
                                    st.session_state.reset_bip = True
                                    st.rerun()
                    else:
                        st.error("Código do produto não localizado na base de dados (Saldo).")

        # --- ABA 2: CONTAGEM ATUAL ---
        with aba_atual:
            st.subheader(f"Inventário: {id_inventario_atual} – {inventario_selecionado_obj['nome']} ({inventario_selecionado_obj['data']})")
            
            if df_contagens_mutaveis.empty:
                st.info("Nenhum item foi auditado neste inventário corrente.")
            else:
                total_auditado = len(df_contagens_mutaveis)
                itens_divergentes = len(df_contagens_mutaveis[df_contagens_mutaveis['diferenca'] != 0])
                soma_contada = int(df_contagens_mutaveis['qtd_contada'].sum())
                soma_sistema = int(df_contagens_mutaveis['qtd_sistema'].sum())
                diferenca_acumulada = int(df_contagens_mutaveis['diferenca'].sum())
                porcentagem_divergencia = (itens_divergentes / total_auditado) * 100
                
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("📦 ITENS CONTADOS", total_auditado)
                r2.metric("⚠️ COM DIVERGÊNCIA", itens_divergentes)
                r3.metric("🔢 QTD TOTAL CONTADA", soma_contada)
                r4.metric("🗄️ QTD TOTAL SISTEMA", f"{soma_sistema} (Diferença: {diferenca_acumulada})")
                
                st.markdown(f'<div class="alerta-divergencia"><strong>⚠️ {itens_divergentes} item(ns) apresentando divergência ou inconformidade de Ativo/Quantidade ({porcentagem_divergencia:.0f}%)</strong></div>', unsafe_allow_html=True)
                
                ordem_colunas_print = ['id', 'inventario_id', 'id_estoque', 'desc_estoque', 'cod_produto', 'desc_produto', 'unid_medida', 'qtd_sistema', 'qtd_contada', 'diferenca', 'ativo', 'observacao', 'operador', 'data_hora', 'lote']
                st.dataframe(df_contagens_mutaveis[ordem_colunas_print], use_container_width=True, hide_index=True)
                
                if inventario_selecionado_obj['status'] == "Aberto":
                    id_para_remover = st.selectbox("Selecione o ID da linha para excluir contagem:", [""] + df_contagens_mutaveis['id'].tolist())
                    if id_para_remover and st.button("🗑️ Excluir linha selecionada"):
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM contagens WHERE id = ?", (id_para_remover,))
                        conn.commit()
                        st.toast("Linha excluída com sucesso!")
                        st.rerun()

        # --- ABA 3: HISTÓRICO DE INVENTÁRIOS ---
        with aba_historico:
            st.write("### 📁 Histórico de Inventários Arquivados")
            for idx, inv in df_inventarios.iterrows():
                cor_bola = "🟢" if inv['status'] == "Aberto" else "🔴"
                df_hist_inv = pd.read_sql_query(f"SELECT * FROM contagens WHERE inventario_id = '{inv['id'].replace('#','')}' ORDER BY id DESC", conn)
                qtd_contada_inv = len(df_hist_inv)
                
                with st.expander(f"{cor_bola} {inv['id']} – {inv['nome']} | {inv['data']} | {qtd_contada_inv} itens"):
                    st.write(f"**Status:** {inv['status']} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Início:** {inv['data']}")
                    
                    if df_hist_inv.empty:
                        st.info("Nenhum item contado neste inventário.")
                        # TRAVA DE SEGURANÇA: Só o admin (criador) pode apagar inventários vazios
                        if st.session_state.operador == "admin":
                            if st.button("🗑️ Excluir inventário vazio", key=f"del_vazio_{inv['id']}_{idx}"):
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM inventarios WHERE id = ?", (inv['id'],))
                                conn.commit()
                                st.toast("Inventário vazio excluído do histórico!")
                                st.rerun()
                    else:
                        ordem_colunas_print = ['id', 'inventario_id', 'id_estoque', 'desc_estoque', 'cod_produto', 'desc_produto', 'unid_medida', 'qtd_sistema', 'qtd_contada', 'diferenca', 'ativo', 'observacao', 'operador', 'data_hora', 'lote']
                        st.dataframe(df_hist_inv[ordem_colunas_print], use_container_width=True, hide_index=True)
                        
                        c_dl, c_del_full = st.columns([4, 2])
                        with c_dl:
                            buffer = io.BytesIO()
                            df_hist_inv[ordem_colunas_print].to_excel(buffer, index=False, engine='openpyxl')
                            st.download_button(
                                label="📥 Exportar este Inventário para Excel (.xlsx)",
                                data=buffer.getvalue(),
                                file_name=f"Inventario_{inv['id']}_{inv['nome']}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"dl_excel_{inv['id']}"
                            )
                        with c_del_full:
                            # SOLICITAÇÃO ATENDIDA: Só permite exclusão se o usuário logado for o criador ('admin')
                            if st.session_state.operador == "admin":
                                if st.button("❌ Excluir Inventário Arquivado", key=f"del_full_{inv['id']}_{idx}", use_container_width=True):
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM inventarios WHERE id = ?", (inv['id'],))
                                    cursor.execute("DELETE FROM contagens WHERE inventario_id = ?", (inv['id'].replace('#',''),))
                                    conn.commit()
                                    st.toast(f"Inventário {inv['id']} excluído permanentemente pelo administrador.")
                                    st.rerun()

        # --- ABA 4: BASE DE ESTOQUE ---
        with aba_base:
            df_visualizacao = st.session_state.base_sistema.copy()
            filtro_estoque = st.selectbox("Filtrar por Estoque Físico", ["Todos", "Apenas Pendentes", "Apenas Contados"], key="filtro_base_tab")
            pesquisa = st.text_input("🔍 Pesquisar (código ou descrição)", placeholder="Filtre por trechos de dados...", key="pesquisa_base_tab")
            
            codigos_contados_set = set()
            if not df_contagens_mutaveis.empty:
                for idx, r_cont in df_contagens_mutaveis.iterrows():
                    match_base = df_visualizacao[df_visualizacao[col_cod].astype(str).str.upper().str.strip() == str(r_cont['cod_produto']).upper().strip()]
                    if not match_base.empty:
                        at_esp = [str(x).upper().strip() for x in match_base[col_ativo_base].tolist() if col_ativo_base in match_base.columns]
                        at_esp = [x for x in at_esp if x not in ["NAN", "SIM", "", "0", "0.0"]]
                        if at_esp:
                            if str(r_cont['ativo']).upper().strip() in at_esp:
                                codigos_contados_set.add(str(r_cont['cod_produto']).upper().strip())
                        else:
                            codigos_contados_set.add(str(r_cont['cod_produto']).upper().strip())

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
            df_ops = pd.read_sql_query("SELECT operador as Operador, COUNT(DISTINCT inventario_id) as [Inventários Feitos] FROM contagens WHERE operador IS NOT NULL AND operador != '' GROUP BY operador", conn)
            if df_ops.empty:
                st.info("Aguardando lançamentos para processar dados de operadores.")
            else:
                df_ops = df_ops.sort_values(by='Inventários Feitos', ascending=False)
                st.bar_chart(data=df_ops, x='Operador', y='Inventários Feitos', color="#d35400")
                
    conn.close()
