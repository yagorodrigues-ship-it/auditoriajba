import streamlit as st
import pandas as pd
import datetime
import sqlite3
import io
import base64

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico - JBA", layout="wide")

# --- BANCO DE DADOS PERMANENTE (SQLITE) ---
def conectar_banco():
    return sqlite3.connect('banco_inventario.db', check_same_thread=False)

def limpar_documento(doc):
    return ''.join(filter(str.isdigit, str(doc)))

def inicializar_banco():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Tabela de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            cpf TEXT UNIQUE,
            email TEXT UNIQUE,
            senha TEXT,
            unidade TEXT DEFAULT 'JURUBATUBA',
            cargo TEXT DEFAULT 'Almoxarife'
        )
    """)
    
    # Tabela de estoques por unidade
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cadastros_estoques (
            id TEXT,
            descricao TEXT,
            unidade TEXT,
            PRIMARY KEY (id, unidade)
        )
    """)
    
    # Tabela de inventários gerais
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventarios (
            id TEXT PRIMARY KEY,
            nome TEXT,
            data TEXT,
            status TEXT,
            unidade TEXT DEFAULT 'JURUBATUBA'
        )
    """)
    
    # Tabela de inventários do Supervisor (Amostral)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventarios_supervisor (
            id TEXT PRIMARY KEY,
            nome TEXT,
            data TEXT,
            status TEXT,
            unidade TEXT DEFAULT 'JURUBATUBA'
        )
    """)
    
    # Tabela de contagens dos funcionários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventario_id TEXT,
            id_estoque TEXT,
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
            lote TEXT,
            unidade TEXT DEFAULT 'JURUBATUBA'
        )
    """)

    # Tabela de Auditorias do Supervisor
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS auditorias_supervisor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventario_id TEXT,
            id_estoque TEXT,
            desc_estoque TEXT,
            cod_produto TEXT,
            desc_produto TEXT,
            qtd_sistema INTEGER,
            qtd_auditada INTEGER,
            diferenca INTEGER,
            etiqueta_correta TEXT,
            localizacao_correta TEXT,
            supervisor TEXT,
            data_hora TEXT,
            recontagem_3 TEXT DEFAULT 'Não',
            ativo TEXT,
            unidade TEXT DEFAULT 'JURUBATUBA'
        )
    """)
    
    # Migrações e Ajustes de Colunas
    tab_alteracoes = {
        "usuarios": ["unidade TEXT DEFAULT 'JURUBATUBA'", "cargo TEXT DEFAULT 'Almoxarife'"],
        "inventarios": ["unidade TEXT DEFAULT 'JURUBATUBA'"],
        "inventarios_supervisor": ["unidade TEXT DEFAULT 'JURUBATUBA'"],
        "contagens": ["lote TEXT DEFAULT ''", "unidade TEXT DEFAULT 'JURUBATUBA'"],
        "auditorias_supervisor": ["unidade TEXT DEFAULT 'JURUBATUBA'", "ativo TEXT", "recontagem_3 TEXT DEFAULT 'Não'"]
    }
    
    for tabela, colunas in tab_alteracoes.items():
        try:
            cursor.execute(f"PRAGMA table_info({tabela})")
            cols_existentes = [c[1] for c in cursor.fetchall()]
            for col_def in colunas:
                nome_col = col_def.split()[0]
                if nome_col not in cols_existentes:
                    cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {col_def}")
                    conn.commit()
        except:
            pass

    conn.close()

inicializar_banco()

# --- ESTADOS DA SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'operador' not in st.session_state: st.session_state.operador = ""
if 'tela_acesso' not in st.session_state: st.session_state.tela_acesso = "login"
if 'base_sistema' not in st.session_state: st.session_state.base_sistema = None
if 'base_supervisor' not in st.session_state: st.session_state.base_supervisor = None
if 'contador_reset' not in st.session_state: st.session_state.contador_reset = 0
if 'pagina_historico' not in st.session_state: st.session_state.pagina_historico = 0
if 'pagina_acuracidade_sup' not in st.session_state: st.session_state.pagina_acuracidade_sup = 0

# --- ESTILIZAÇÃO INTERFACE ---
st.markdown("""
    <style>
    div.stButton > button:first-child[kind="primary"] {
        background-color: #d35400; border-color: #d35400; color: white; font-weight: bold;
    }
    div.stButton > button:first-child[kind="primary"]:hover {
        background-color: #e67e22; border-color: #e67e22;
    }
    .bloco-info {
        background-color: #ebf5fb; padding: 15px; border-radius: 8px; border: 1px solid #d4e6f1; margin-bottom: 10px;
    }
    .bloco-titulo { color: #7f8c8d; font-size: 11px; font-weight: bold; letter-spacing: 0.5px; }
    .bloco-valor { color: #1b4f72; font-size: 24px; font-weight: bold; }
    .card-sistema { background-color: #ebf5fb; padding: 20px; border-radius: 8px; border: 1px solid #d4e6f1; margin-bottom: 25px; }
    </style>
""", unsafe_allow_html=True)

# --- TELA DE ACESSO ---
if not st.session_state.logged_in:
    conn = conectar_banco()
    _, col_login, _ = st.columns([3, 4, 3])
    
    with col_login:
        if st.session_state.tela_acesso == "login":
            st.markdown("<h2 style='text-align: center;'>🔒 Acesso ao Sistema</h2>", unsafe_allow_html=True)
            with st.form("login_form"):
                identificador = st.text_input("CPF ou E-mail")
                senha = st.text_input("Senha", type="password")
                unidade_login = st.selectbox("📍 Localidade", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"])
                
                if st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True):
                    id_l = identificador.strip()
                    doc_l = limpar_documento(id_l)
                    cursor = conn.cursor()
                    cursor.execute("SELECT nome, unidade, cargo FROM usuarios WHERE (email = ? OR cpf = ?) AND senha = ? AND unidade = ?", (id_l, doc_l, senha, unidade_login))
                    user = cursor.fetchone()
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.operador = user[0]
                        st.session_state.unidade_selecionada = user[1]
                        st.session_state.cargo_usuario = user[2]
                        st.rerun()
                    else:
                        st.error("❌ Credenciais incorretas ou não cadastradas nesta unidade!")
            
            c_cad, c_rec = st.columns(2)
            with c_cad:
                if st.button("📝 Criar conta", use_container_width=True):
                    st.session_state.tela_acesso = "cadastro"; st.rerun()
                    
        elif st.session_state.tela_acesso == "cadastro":
            st.markdown("<h2 style='text-align: center;'>📝 Cadastro de Colaborador</h2>", unsafe_allow_html=True)
            with st.form("cadastro_form"):
                novo_nome = st.text_input("Nome Completo")
                novo_cpf = st.text_input("CPF (Apenas números)")
                novo_email = st.text_input("E-mail")
                nova_senha = st.text_input("Senha", type="password")
                unidade_cadastro = st.selectbox("📍 Unidade", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"])
                
                if st.form_submit_button("Finalizar Cadastro", type="primary", use_container_width=True):
                    cpf_l = limpar_documento(novo_cpf)
                    email_l = novo_email.strip()
                    if novo_nome and cpf_l and email_l and nova_senha:
                        cursor = conn.cursor()
                        cursor.execute("SELECT email, cpf FROM usuarios WHERE cpf = ? OR email = ?", (cpf_l, email_l))
                        usuario_existente = cursor.fetchone()
                        if usuario_existente:
                            st.error("❌ Erro de Cadastro: Este CPF ou E-mail já possui conta activa!")
                        else:
                            try:
                                cursor.execute("INSERT INTO usuarios (nome, cpf, email, senha, unidade, cargo) VALUES (?, ?, ?, ?, ?, 'Almoxarife')", (novo_nome.strip(), cpf_l, email_l, nova_senha, unidade_cadastro))
                                conn.commit()
                                st.success("✅ Cadastrado!")
                                st.session_state.tela_acesso = "login"; st.rerun()
                            except Exception as e: st.error(f"❌ Erro operacional: {e}")
            if st.button("◀ Voltar"):
                st.session_state.tela_acesso = "login"; st.rerun()
    conn.close()

# --- INSTÂNCIA LOGADA ---
else:
    conn = conectar_banco()
    
    nome_u = st.session_state.operador.lower()
    eh_supervisor = st.session_state.cargo_usuario == "Supervisor" or "yago" in nome_u
    eh_yago_master = "yago" in nome_u or "administrador" in nome_u
    
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios WHERE unidade = ? ORDER BY id DESC", conn, params=(st.session_state.unidade_selecionada,))
    df_inventarios_sup = pd.read_sql_query("SELECT * FROM inventarios_supervisor WHERE unidade = ? ORDER BY id DESC", conn, params=(st.session_state.unidade_selecionada,))

    def encontrar_coluna(df, o_list, def_i):
        if df is not None:
            for op in o_list:
                for c in df.columns:
                    if op.lower().replace(" ", "") in str(c).lower().replace(" ", "").replace(".", ""):
                        return c
            return list(df.columns)[def_i] if def_i < len(df.columns) else ""
        return ""

    # --- MAPEAMENTO DE COLUNAS DA BASE ---
    c_cod, c_desc, c_un, c_est, c_qtd, c_loc, c_atv_b = "", "", "", "", "", "", ""
    if st.session_state.base_sistema is not None:
        c_cod = encontrar_coluna(st.session_state.base_sistema, ['códproduto', 'codproduto', 'codigo', 'cod'], 0)
        c_desc = encontrar_coluna(st.session_state.base_sistema, ['descproduto', 'descricao'], 1)
        c_un = encontrar_coluna(st.session_state.base_sistema, ['unidmedida', 'unidade', 'un'], 3)
        c_est = encontrar_coluna(st.session_state.base_sistema, ['idestoquefísico', 'idestoque'], 0)
        c_qtd = encontrar_coluna(st.session_state.base_sistema, ['qtdestoque', 'quantidade', 'saldo'], -1)
        c_loc = encontrar_coluna(st.session_state.base_sistema, ['descestoquefisico', 'localizacao'], 2)
        c_atv_b = encontrar_coluna(st.session_state.base_sistema, ['ativo', 'patrimonio', 'n ativo'], -1)

    # INTERFACE LATERAL (SIDEBAR)
    with st.sidebar:
        if st.button("🔄 Atualizar Dados", type="primary", use_container_width=True): st.rerun()
        st.subheader(f"🏢 {st.session_state.unidade_selecionada}")
        st.write(f"👤 {st.session_state.operador} ({st.session_state.cargo_usuario})")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logged_in = False; st.rerun()
            
        st.markdown("---")
        st.write("📂 **Base Geral**")
        ar_excel = st.file_uploader("Upload Excel Geral", type=["xlsx"], label_visibility="collapsed")
        if ar_excel:
            st.session_state.base_sistema = pd.read_excel(ar_excel)
            
        st.markdown("---")
        st.write("📁 **Selecione o Inventário**")
        if df_inventarios.empty or 'id' not in df_inventarios.columns:
            id_inventario_atual = None
            inventario_selected_obj = None
        else:
            lista_inv = [f"{r['id']} – {r['nome']} ({r['status']})" for idx, r in df_inventarios.iterrows()]
            inv_sel = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
            id_inventario_atual = inv_sel.split(" – ")[0]
            inventario_selected_obj = df_inventarios[df_inventarios['id'] == id_inventario_atual].iloc[0]

        # --- SEÇÃO DINÂMICA DE PROGRESSO ATUALIZADA (EXIBE PARA SUPERVISOR E ALMOXARIFE) ---
        if id_inventario_atual and st.session_state.base_sistema is not None:
            df_c_side = pd.read_sql_query("SELECT cod_produto FROM contagens WHERE inventario_id = ? AND unidade = ?", conn, params=(id_inventario_atual.replace('#',''), st.session_state.unidade_selecionada))
            total_itens_base = len(st.session_state.base_sistema)
            itens_contados_unicos = df_c_side['cod_produto'].unique() if not df_c_side.empty else []
            total_contados = len(itens_contados_unicos)
            total_faltantes = max(0, total_itens_base - total_contados)
            
            # ATUALIZAÇÃO DA DESCRIÇÃO PEDIDA
            st.markdown("**📊 Progresso do Inventário Atual**")
            st.caption(f"📋 Mapeados: **{total_itens_base}**")
            st.caption(f"✅ Contados: **{total_contados}**")
            if total_faltantes > 0:
                st.caption(f"⏳ Pendentes: <span style='color:#e74c3c;font-weight:bold;'>{total_faltantes}</span>", unsafe_allow_html=True)
            else:
                st.caption("🎉 Status: <span style='color:#2ecc71;font-weight:bold;'>100% Concluído</span>", unsafe_allow_html=True)

        st.markdown("---")
        st.write("⚙️ **Criar Inventário**")
        with st.expander("➕ Abrir Nova Contagem"):
            with st.form("form_novo_inv", clear_on_submit=True):
                n_inv = st.text_input("Nome do Inventário Geral")
                if st.form_submit_button("Criar Lote") and n_inv:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM inventarios")
                    todos_ids = cursor.fetchall()
                    
                    maior_id = 0
                    for row in todos_ids:
                        try:
                            num = int(row[0].replace('#',''))
                            if num > maior_id:
                                maior_id = num
                        except ValueError:
                            pass
                    
                    nxt = maior_id + 1
                    cursor.execute("INSERT INTO inventarios (id, nome, data, status, unidade) VALUES (?, ?, ?, 'Aberto', ?)", (f"#{nxt}", n_inv, datetime.date.today().strftime("%Y-%m-%d"), st.session_state.unidade_selecionada))
                    conn.commit(); st.rerun()

    # --- DEFINIÇÃO E RENDERIZAÇÃO DAS ABAS NA ORDEM EXATA ---
    ordem_abas = ["🔍 Contar Item", "📊 Contagem Atual e Progresso", "📄 Base de Estoque", "📁 Histórico Geral", "🏆 Desempenho e Prazos", "📈 Acuracidade Estoque"]
    
    if eh_supervisor:
        ordem_abas += ["🔬 Painel Supervisor", "⚙️ Gerenciar Estoques"]
    if eh_yago_master:
        ordem_abas.append("👥 Gestão de Usuários")
        
    abas_gui = st.tabs(ordem_abas)

    # 🔍 ABA 1: CONTAR ITEM
    with abas_gui[0]:
        if id_inventario_atual is None:
            st.warning("⚠️ **Bloqueado:** Nenhum lote de inventário selecionado ou ativo. Use a barra lateral para criar ou selecionar um lote.")
        elif st.session_state.base_sistema is None:
            st.warning("⚠️ Carregue a Base Geral no menu lateral para iniciar as bipagens.")
        elif inventario_selected_obj is not None and inventario_selected_obj['status'] == "Fechado":
            st.error("🔒 Este lote de inventário foi finalizado e fechado.")
        else:
            st.subheader(f"📝 Lançamento de Contagem Ativa – Lote {id_inventario_atual}")
            bip_prod = st.text_input("💻 Bipar Código do Produto", key=f"bip_op_{st.session_state.contador_reset}")
            if bip_prod:
                prod_l = str(bip_prod).strip().upper()
                it = st.session_state.base_sistema[st.session_state.base_sistema[c_cod].astype(str).str.upper().str.strip() == prod_l]
                if not it.empty:
                    row = it.iloc[0]
                    st.markdown(f"### 📦 {row[c_desc]} ({row[c_un]})")
                    
                    tem_ativo_na_base = False
                    if c_atv_b in it.columns:
                        val_at = str(row[c_atv_b]).strip()
                        if val_at and val_at.lower() != "nan" and val_at != "": tem_ativo_na_base = True

                    with st.form("f_salva_contagem", clear_on_submit=True):
                        q_cont = st.number_input("Quantidade Física Encontrada", min_value=0, step=1, value=1)
                        if tem_ativo_na_base:
                            n_ativ = st.text_input("🔢 Número do Ativo (OBRIGATÓRIO)")
                        else:
                            n_ativ = st.text_input("🔢 Número do Ativo (Opcional)")
                        obs = st.text_input("Observação")
                        
                        if st.form_submit_button("Confirmar Lançamento", type="primary"):
                            if tem_ativo_na_base and not n_ativ.strip():
                                st.error("❌ Erro: O campo Ativo é obrigatório para este produto!")
                            else:
                                cursor = conn.cursor()
                                q_sis = int(row[c_qtd]) if pd.notna(row[c_qtd]) else 0
                                cursor.execute("""
                                    INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, observacao, operador, data_hora, unidade)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (id_inventario_atual.replace('#',''), str(row[c_est]), str(row[c_loc]), prod_l, str(row[c_desc]), str(row[c_un]), q_sis, q_cont, q_cont - q_sis, n_ativ.strip().upper(), obs, st.session_state.operador, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.unidade_selecionada))
                                conn.commit()
                                st.success("Contagem salva com sucesso!")
                                st.session_state.contador_reset += 1; st.rerun()
                else: st.error("Material/Produto não localizado na base de dados carregada.")

    # 📊 ABA 2: CONTAGEM ATUAL E PROGRESSO
    with abas_gui[1]:
        if id_inventario_atual:
            st.subheader(f"📊 Progresso em Tempo Real - Lote {id_inventario_atual}")
            df_c = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? AND unidade = ?", conn, params=(id_inventario_atual.replace('#',''), st.session_state.unidade_selecionada))
            
            if st.session_state.base_sistema is not None:
                total_itens_base = len(st.session_state.base_sistema)
                itens_contados_unicos = df_c['cod_produto'].unique() if not df_c.empty else []
                total_contados = len(itens_contados_unicos)
                total_faltantes = max(0, total_itens_base - total_contados)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("📋 Total de Itens Mapeados", total_itens_base)
                m2.metric("✅ Itens Já Contabilizados", total_contados)
                m3.metric("⏳ Itens Pendentes (Falta Contar)", total_faltantes)
                
                codigos_base = st.session_state.base_sistema[c_cod].astype(str).str.upper().str.strip().tolist()
                codigos_contados = [str(x).upper().strip() for x in itens_contados_unicos]
                codigos_faltantes = [c for c in codigos_base if c not in codigos_contados]
                
                st.markdown("---")
                if total_faltantes > 0:
                    st.error(f"⚠️ **Atenção:** Ainda restam {total_faltantes} itens sem nenhuma contagem realizada.")
                    df_faltantes_exibir = st.session_state.base_sistema[st.session_state.base_sistema[c_cod].astype(str).str.upper().str.strip().isin(codigos_faltantes)]
                    st.write("### 📋 Lista de Itens Faltantes para Concluir:")
                    st.dataframe(df_faltantes_exibir[[c_cod, c_desc, c_loc]], use_container_width=True, hide_index=True)
                else:
                    st.success("🎉 **Excelente!** 100% dos itens da planilha base foram contabilizados.")
                st.markdown("---")

                # REGRA DE FECHAMENTO
                if inventario_selected_obj is not None and inventario_selected_obj['status'] == 'Aberto':
                    if total_faltantes > 0:
                        if eh_supervisor:
                            st.warning("⚠️ **Aviso de Supervisor:** O inventário está incompleto, mas você possui permissão de nível hierárquico para forçar o fechamento.")
                            if st.button("🔒 Forçar Encerramento do Lote (Supervisor)", type="primary", use_container_width=True):
                                cursor = conn.cursor()
                                cursor.execute("UPDATE inventarios SET status = 'Fechado' WHERE id = ? AND unidade = ?", (id_inventario_atual, st.session_state.unidade_selecionada))
                                conn.commit(); st.success("Lote encerrado com pendências pelo Supervisor!"); st.rerun()
                        else:
                            st.button("🔒 Encerrar Lote Geral (Incompleto)", disabled=True, use_container_width=True)
                            st.caption("🔴 **Acesso Restrito:** Este lote possui pendências. Apenas o **Supervisor** tem autorização para encerrar inventários incompletos.")
                    else:
                        if st.button("🔒 Encerrar e Fechar Lote Geral (100% Concluído)", type="primary", use_container_width=True):
                            cursor = conn.cursor()
                            cursor.execute("UPDATE inventarios SET status = 'Fechado' WHERE id = ? AND unidade = ?", (id_inventario_atual, st.session_state.unidade_selecionada))
                            conn.commit(); st.success("Lote concluído e fechado com sucesso!"); st.rerun()
            
            st.write("### 📑 Histórico de Lançamentos Registrados")
            st.dataframe(df_c.drop(columns=['unidade'], errors='ignore'), use_container_width=True, hide_index=True)
        else: st.info("Nenhum inventário selecionado.")

    # 📄 ABA 3: BASE DE ESTOQUE
    with abas_gui[2]:
        if st.session_state.base_sistema is not None: st.dataframe(st.session_state.base_sistema, use_container_width=True)
        else: st.info("Nenhuma base carregada.")

    # 📁 ABA 4: HISTÓRICO GERAL
    with abas_gui[3]:
        st.title("📁 Arquivo Geral de Movimentações")
        c_dt1, c_dt2 = st.columns(2)
        with c_dt1: data_inicio_filtro = st.date_input("Data Inicial (Opcional)", value=None, key="blank_dt_ini")
        with c_dt2: data_fim_filtro = st.date_input("Data Final (Opcional)", value=None, key="blank_dt_fim")
        
        if not df_inventarios.empty and 'data' in df_inventarios.columns:
            df_inventarios['datetime_parsed'] = pd.to_datetime(df_inventarios['data'], errors='coerce').dt.date
            df_filtrados = df_inventarios[df_inventarios['unidade'] == st.session_state.unidade_selecionada]
            if data_inicio_filtro: df_filtrados = df_filtrados[df_filtrados['datetime_parsed'] >= data_inicio_filtro]
            if data_fim_filtro: df_filtrados = df_filtrados[df_filtrados['datetime_parsed'] <= data_fim_filtro]
                
            st.write(f"Total de pastas nesta unidade: {len(df_filtrados)}")
            if not df_filtrados.empty:
                tamanho_pagina = 15
                total_paginas = (len(df_filtrados) - 1) // tamanho_pagina + 1
                if st.session_state.pagina_historico >= total_paginas:
                    st.session_state.pagina_historico = 0
                    
                df_pag = df_filtrados.iloc[st.session_state.pagina_historico*tamanho_pagina : (st.session_state.pagina_historico+1)*tamanho_pagina]
                for idx, inv in df_pag.iterrows():
                    id_p = inv['id'].replace('#','')
                    df_det = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? AND unidade = ?", conn, params=(id_p, st.session_state.unidade_selecionada))
                    with st.expander(f"📁 {inv['id']} – {inv['nome']} | Data: {inv['data']} ({len(df_det)} contados)"):
                        st.dataframe(df_det.drop(columns=['unidade'], errors='ignore'), use_container_width=True, hide_index=True)
                
                st.write("")
                cp1, cp2, cp3 = st.columns([2, 6, 2])
                with cp1:
                    if st.button("◀ Anterior", disabled=(st.session_state.pagina_historico==0), key="btn_ant_hist"): st.session_state.pagina_historico-=1; st.rerun()
                with cp2: st.markdown(f"<p style='text-align:center;'>Página {st.session_state.pagina_historico+1} de {total_paginas}</p>", unsafe_allow_html=True)
                with cp3:
                    if st.button("Próximo ▶", disabled=(st.session_state.pagina_historico>=total_paginas-1), key="btn_prox_hist"): st.session_state.pagina_historico+=1; st.rerun()
        else:
            st.info("Nenhum histórico registrado até o momento.")

    # 🏆 ABA 5: DESEMPENHO E PRAZOS
    with abas_gui[4]:
        st.title("🏆 Validade e Prazos de Auditoria Temporal")
        df_m_est = pd.read_sql_query("SELECT id, descricao FROM cadastros_estoques WHERE unidade = ?", conn, params=(st.session_state.unidade_selecionada,))
        df_lasts = pd.read_sql_query("SELECT id_estoque, MAX(data_hora) as u_data FROM contagens WHERE warmth=1 AND unidade = ? GROUP BY id_estoque", conn, params=(st.session_state.unidade_selecionada,)) if 'warmth' in pd.read_sql_query("PRAGMA table_info(contagens)", conn)['name'].tolist() else pd.read_sql_query("SELECT id_estoque, MAX(data_hora) as u_data FROM contagens WHERE unidade = ? GROUP BY id_estoque", conn, params=(st.session_state.unidade_selecionada,))
        map_lasts = dict(zip(df_lasts['id_estoque'].astype(str).str.strip(), df_lasts['u_data']))
        
        hoje_dt = datetime.datetime.now()
        dados_prazos, bom_count, auditar_count, criticos_count = [], 0, 0, 0
        for _, re in df_m_est.iterrows():
            ide = str(re['id']).strip()
            udstr = map_lasts.get(ide, None)
            if udstr:
                try:
                    dtc = datetime.datetime.strptime(udstr, "%Y-%m-%d %H:%M:%S")
                    dias = (hoje_dt - dtc).days
                    exib = dtc.strftime("%d/%m/%Y %H:%M")
                except: dias = 999; exib = "Erro"
            else: dias = 999; exib = "Nunca Contado"
            
            status_f = "🟢 Bom" if dias <= 7 else "🟡 Precisa contar" if dias <= 14 else "🔴 Crítico"
            if dias <= 7: bom_count += 1
            elif dias <= 14: auditar_count += 1
            else: criticos_count += 1
            dados_prazos.append({"Id. Estoque": ide, "Descrição": re['descricao'], "Última Contagem": exib, "Dias sem Contar": dias if dias != 999 else "—", "Status": status_f})
        
        k1, k2, k3 = st.columns(3)
        with k1: st.markdown(f'<div class="bloco-info" style="border-left: 5px solid #2ecc71;"><div class="bloco-titulo">🟢 EM DIA (BOM)</div><div class="bloco-valor" style="color: #27ae60;">{bom_count}</div></div>', unsafe_allow_html=True)
        with k2: st.markdown(f'<div class="bloco-info" style="border-left: 5px solid #f1c40f;"><div class="bloco-titulo">🟡 PRECISA CONTAR</div><div class="bloco-valor" style="color: #f39c12;">{auditar_count}</div></div>', unsafe_allow_html=True)
        with k3: st.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:10px; border-left: 5px solid #e74c3c;"><div class="bloco-titulo">🔴 CRÍTICO (+2 SEMANAS)</div><div class="bloco-valor" style="color: #c0392b;">{criticos_count}</div></div>', unsafe_allow_html=True)
        if dados_prazos: st.dataframe(pd.DataFrame(dados_prazos), use_container_width=True, hide_index=True)

    # 📈 ABA 6: ACURACIDADE ESTOQUE
    with abas_gui[5]:
        st.title("📈 Painel Gerencial de Acuracidade Local por Estoque")
        
        df_ac = pd.read_sql_query("SELECT * FROM auditorias_supervisor WHERE unidade = ?", conn, params=(st.session_state.unidade_selecionada,))
        
        if df_ac.empty:
            st.info("💡 Nenhuma amostragem de acuracidade coletada no banco de dados para esta unidade.")
        else:
            linhas_acuracidade_gerencial = []
            
            def formatar_acuracidade_visual(porcentagem):
                if porcentagem == 100.0:
                    return f"<span style='color:green; font-weight:bold;'>🟢 {porcentagem:.1f}%</span>"
                elif porcentagem >= 95.0:
                    return f"<span style='color:#d4ac0d; font-weight:bold;'>🟡 {porcentagem:.1f}%</span>"
                else:
                    return f"<span style='color:red; font-weight:bold;'>🔴 {porcentagem:.1f}%</span>"
            
            for dep_id, grupo in df_ac.groupby('id_estoque'):
                total_itens_dep = len(grupo)
                certos_qtd = len(grupo[grupo['diferenca'] == 0])
                certos_etiq = len(grupo[grupo['etiqueta_correta'] == "Sim"])
                certos_local = len(grupo[grupo['localizacao_correta'] == "Sim"])
                
                desc_dep = grupo.iloc[0]['desc_estoque'] if 'desc_estoque' in grupo.columns else "Não Informado"
                
                pct_saldo = (certos_qtd / total_itens_dep) * 100
                pct_etiq = (certos_etiq / total_itens_dep) * 100
                pct_local = (certos_local / total_itens_dep) * 100
                
                linhas_acuracidade_gerencial.append({
                    "CÓDIGO ESTOQUE": str(dep_id),
                    "DESCRIÇÃO DO ESTOQUE": desc_dep,
                    "QUANTIDADE ITENS": total_itens_dep,
                    "ACURACIDADE SALDO": formatar_acuracidade_visual(pct_saldo),
                    "ACURACIDADE ETIQUETA": formatar_acuracidade_visual(pct_etiq),
                    "ACURACIDADE LOCALIZAÇÃO": formatar_acuracidade_visual(pct_local)
                })
            
            df_gerencial_final = pd.DataFrame(linhas_acuracidade_gerencial)
            st.write(df_gerencial_final.to_html(escape=False, index=False), unsafe_allow_html=True)
            
        st.markdown("---")
        
        st.subheader("🔍 Filtrar Pastas por Período")
        f_col1, f_col2 = st.columns(2)
        with f_col1: dt_ini_ac = st.date_input("Filtrar Data Inicial", value=None, key="dt_ini_ac")
        with f_col2: dt_fim_ac = st.date_input("Filtrar Data Final", value=None, key="dt_fim_ac")
        
        st.markdown("---")
        st.subheader("📁 Histórico de Pastas Contabilizadas (Supervisor)")
        
        if not df_inventarios_sup.empty and 'data' in df_inventarios_sup.columns:
            df_inventarios_sup['dt_parsed'] = pd.to_datetime(df_inventarios_sup['data'], errors='coerce').dt.date
            df_pastas_filtradas = df_inventarios_sup.copy()
            if dt_ini_ac: df_pastas_filtradas = df_pastas_filtradas[df_pastas_filtradas['dt_parsed'] >= dt_ini_ac]
            if dt_fim_ac: df_pastas_filtradas = df_pastas_filtradas[df_pastas_filtradas['dt_parsed'] <= dt_fim_ac]

            if not df_pastas_filtradas.empty:
                tamanho_pag_sup = 10
                total_pag_sup = (len(df_pastas_filtradas) - 1) // tamanho_pag_sup + 1
                
                if st.session_state.pagina_acuracidade_sup >= total_pag_sup:
                    st.session_state.pagina_acuracidade_sup = 0
                    
                df_pastas_paginadas = df_pastas_filtradas.iloc[
                    st.session_state.pagina_acuracidade_sup * tamanho_pag_sup : (st.session_state.pagina_acuracidade_sup + 1) * tamanho_pag_sup
                ]
                
                for idx, pasta_sup in df_pastas_paginadas.iterrows():
                    df_itens_da_pasta = pd.read_sql_query(
                        "SELECT id_estoque as 'Cód. Estoque', desc_estoque as 'Localização', cod_produto as 'Código', desc_produto as 'Descrição', qtd_sistema as 'Qtd. Sist', qtd_auditada as 'Qtd. Auditada', diferenca as 'Diferença', etiqueta_correta as 'Etiqueta Ok', localizacao_correta as 'Local Ok', supervisor as 'Auditado Por', data_hora as 'Data/Hora' FROM auditorias_supervisor WHERE inventario_id = ? ORDER BY id DESC", 
                        conn, 
                        params=(pasta_sup['id'],)
                    )
                    
                    with st.expander(f"📁 Pasta: {pasta_sup['id']} – {pasta_sup['nome']} ({pasta_sup['status']}) | {len(df_itens_da_pasta)} itens auditados"):
                        if not df_itens_da_pasta.empty:
                            st.dataframe(df_itens_da_pasta, use_container_width=True, hide_index=True)
                        else:
                            st.info("Nenhum item contabilizado nesta pasta amostral ainda.")
                
                st.write("")
                cs1, cs2, cs3 = st.columns([2, 6, 2])
                with cs1:
                    if st.button("◀ Anterior", disabled=(st.session_state.pagina_acuracidade_sup == 0), key="btn_ant_ac_sup"):
                        st.session_state.pagina_acuracidade_sup -= 1; st.rerun()
                with cs2:
                    st.markdown(f"<p style='text-align:center;'>Exibindo página {st.session_state.pagina_acuracidade_sup + 1} de {total_pag_sup}</p>", unsafe_allow_html=True)
                with cs3:
                    if st.button("Próximo ▶", disabled=(st.session_state.pagina_acuracidade_sup >= total_pag_sup - 1), key="btn_prox_ac_sup"):
                        st.session_state.pagina_acuracidade_sup += 1; st.rerun()
            else:
                st.info("Nenhuma pasta localizada para os critérios de filtragem atuais.")
        else:
            st.info("Nenhum inventário de supervisor cadastrado.")

    # RECURSOS EXCLUSIVOS DO SUPERVISOR
    if eh_supervisor:
        # 🔬 ABA 7: PAINEL SUPERVISOR
        with abas_gui[6]:
            st.title("🔬 Módulo Amostral do Supervisor")
            if df_inventarios_sup.empty:
                st.warning("Nenhum inventário amostral aberto.")
                id_inv_sup_atual = None
            else:
                lista_inv_sup = [f"{r['id']} – {r['nome']} ({r['status']})" for idx, r in df_inventarios_sup.iterrows()]
                inv_sup_selected = st.selectbox("Selecione a sua Auditoria Amostral", lista_inv_sup)
                id_inv_sup_atual = inv_sup_selected.split(" – ")[0]
                inv_sup_selected_obj = df_inventarios_sup[df_inventarios_sup['id'] == id_inv_sup_atual].iloc[0]
                
                if inv_sup_selected_obj['status'] == 'Aberto':
                    if st.button("🔒 Fechar Lote Amostral do Supervisor", type="primary", use_container_width=True):
                        cursor = conn.cursor()
                        cursor.execute("UPDATE inventarios_supervisor SET status = 'Fechado' WHERE id = ? AND unidade = ?", (id_inv_sup_atual, st.session_state.unidade_selecionada))
                        conn.commit(); st.rerun()

            with st.popover("➕ Novo Inventário Supervisor", use_container_width=True):
                with st.form("form_novo_sup", clear_on_submit=True):
                    nome_sup_inv = st.text_input("Nome da Auditoria Amostral")
                    if st.form_submit_button("Criar Lote", type="primary") and nome_sup_inv:
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM inventarios_supervisor")
                        todos_ids_sup = cursor.fetchall()
                        
                        maior_id_sup = 0
                        for row in todos_ids_sup:
                            try:
                                num = int(row[0].replace('SUP-#',''))
                                if num > maior_id_sup:
                                    maior_id_sup = num
                            except ValueError:
                                pass
                                
                        novo_id_sup = f"SUP-#{maior_id_sup + 1}"
                        cursor.execute("INSERT INTO inventarios_supervisor (id, nome, data, status, unidade) VALUES (?, ?, ?, 'Aberto', ?)", (novo_id_sup, nome_sup_inv, datetime.date.today().strftime("%Y-%m-%d"), st.session_state.unidade_selecionada))
                        conn.commit(); st.rerun()

            st.markdown("---")
            st.subheader("📤 Carregar Planilha de Amostragem do Supervisor")
            arquivo_supervisor = st.file_uploader("Suba a planilha Excel (.xlsx)", type=["xlsx"], key="sup_excel_loader")
            
            if arquivo_supervisor is not None:
                try:
                    df_temp_check = pd.read_excel(arquivo_supervisor)
                    st.session_state.base_supervisor = df_temp_check
                    st.success("✅ Planilha de amostragem pré-carregada com sucesso!")
                except Exception as e: st.error(f"Erro: {e}")

            if id_inv_sup_atual and 'inv_sup_selected_obj' in locals() and inv_sup_selected_obj['status'] == 'Aberto' and st.session_state.base_supervisor is not None:
                st.markdown("---")
                st.subheader("💻 Executar Auditoria do Item")
                df_s = st.session_state.base_supervisor
                
                col_cod_sup = encontrar_coluna(df_s, ['códproduto', 'codproduto', 'codigo', 'cod'], 0)
                col_desc_sup = encontrar_coluna(df_s, ['descproduto', 'descricao', 'desc'], 1)
                col_local_sup = encontrar_coluna(df_s, ['descestoquefisico', 'localizacao', 'local', 'estoquefisico'], 2)
                col_qtd_sup = encontrar_coluna(df_s, ['qtdestoque', 'quantidade', 'saldo', 'qtd'], -1)
                col_id_est_sup = encontrar_coluna(df_s, ['idestoquefísico', 'idestoqfísico', 'idestoque', 'codestoque'], 0)
                col_atv_sup = encontrar_coluna(df_s, ['ativo', 'patrimonio', 'n ativo', 'numero ativo'], -1)

                bip_sup_item = st.text_input("💻 Bipar Produto para Auditoria Amostral", key="bip_sup_action")
                if bip_sup_item:
                    sup_bl = str(bip_sup_item).strip().upper()
                    match_sup = df_s[df_s[col_cod_sup].astype(str).str.upper().str.strip() == sup_bl]
                    
                    if not match_sup.empty:
                        row_sup = match_sup.iloc[0]
                        st.info(f"📋 **Item:** {sup_bl} - {row_sup[col_desc_sup]} | **Saldo Sistema:** {row_sup[col_qtd_sup]}")
                        
                        tem_ativo_na_planilha_sup = False
                        if col_atv_sup in match_sup.columns:
                            v_at_s = str(row_sup[col_atv_sup]).strip()
                            if v_at_s and v_at_s.lower() != "nan" and v_at_s != "": tem_ativo_na_planilha_sup = True
                        
                        with st.form("form_auditoria_action", clear_on_submit=True):
                            qtd_aud_sup = st.number_input("Quantidade Física Encontrada", min_value=0, step=1)
                            
                            if tem_ativo_na_planilha_sup:
                                f_ativo_sup = st.text_input("🔢 Número do Ativo (OBRIGATÓRIO PARA ESTE ITEM)")
                            else:
                                f_ativo_sup = st.text_input("🔢 Número do Ativo (Opcional)")
                                
                            etiq_check = st.selectbox("A etiqueta de identificação está correta?", ["Sim", "Não"])
                            loc_check = st.selectbox("O material está na localização física correta?", ["Sim", "Não"])
                            
                            if st.form_submit_button("💾 Salvar na Acuracidade", type="primary"):
                                if tem_ativo_na_planilha_sup and not f_ativo_sup.strip():
                                    st.error("❌ Erro: O preenchimento do Ativo é obrigatório para este material!")
                                else:
                                    q_s_v = int(row_sup[col_qtd_sup]) if pd.notna(row_sup[col_qtd_sup]) else 0
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        INSERT INTO auditorias_supervisor (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, qtd_sistema, qtd_auditada, diferenca, etiqueta_correta, localizacao_correta, supervisor, data_hora, ativo, unidade)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (id_inv_sup_atual, str(row_sup[col_id_est_sup]), str(row_sup[col_local_sup]), sup_bl, str(row_sup[col_desc_sup]), q_s_v, qtd_aud_sup, qtd_aud_sup - q_s_v, etiq_check, loc_check, st.session_state.operador, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f_ativo_sup.strip().upper(), st.session_state.unidade_selecionada))
                                    conn.commit()
                                    st.success("✅ Lançamento enviado para a Acuracidade!")
                                    st.rerun()
                    else: st.error("❌ Produto não localizado na planilha de amostragem.")

            df_auditorias_atual = pd.read_sql_query("SELECT * FROM auditorias_supervisor WHERE inventario_id = ? AND unidade = ?", conn, params=(id_inv_sup_atual, st.session_state.unidade_selecionada)) if id_inv_sup_atual else pd.DataFrame()
            st.write("### Itens Auditados neste Lote Amostral")
            st.dataframe(df_auditorias_atual.drop(columns=['unidade'], errors='ignore'), use_container_width=True, hide_index=True)

        # ⚙️ ABA 8: GERENCIAR ESTOQUES
        with abas_gui[7]:
            st.title("⚙️ Gerenciamento de Estoques Físicos (Unidade)")
            c_est1, c_est2 = st.columns([1, 2])
            with c_est1:
                st.write("### ➕ Adicionar Estoque")
                with st.form("add_est_form", clear_on_submit=True):
                    id_n = st.text_input("ID do Estoque (Ex: 1077)")
                    desc_n = st.text_input("Descrição do Estoque")
                    if st.form_submit_button("Cadastrar", type="primary") and id_n and desc_n:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO cadastros_estoques (id, descricao, unidade) VALUES (?, ?, ?)", (id_n.strip(), desc_n.strip(), st.session_state.unidade_selecionada))
                            conn.commit(); st.success("Cadastrado!"); st.rerun()
                        except: st.error("Erro ou Duplicidade.")
            with c_est2:
                st.write("### 📋 Estoques Configurados")
                df_meus_est = pd.read_sql_query("SELECT id as 'ID', descricao as 'Descrição' FROM cadastros_estoques WHERE unidade = ? ORDER BY id", conn, params=(st.session_state.unidade_selecionada,))
                st.dataframe(df_meus_est, use_container_width=True, hide_index=True)
                if not df_meus_est.empty:
                    est_del = st.selectbox("Remover ID", df_meus_est['ID'].tolist())
                    if st.button("🗑️ Excluir Estoque"):
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM cadastros_estoques WHERE id = ? AND unidade = ?", (est_del, st.session_state.unidade_selecionada))
                        conn.commit(); st.rerun()

    # 👥 ABA 9: GESTÃO DE USUÁRIOS
    if eh_yago_master:
        with abas_gui[-1]:
            st.title("👥 Painel de Controle e Gestão de Usuários")
            df_u = pd.read_sql_query("SELECT id, nome, cpf, email, senha, unidade, cargo FROM usuarios ORDER BY unidade, nome", conn)
            st.dataframe(df_u, use_container_width=True, hide_index=True)
            with st.form("form_adm_edit"):
                id_a = st.selectbox("Escolha o ID para Alterar", df_u['id'].tolist(), format_func=lambda x: f"ID {x} - {df_u[df_u['id']==x]['nome'].values[0]} ({df_u[df_u['id']==x]['unidade'].values[0]})")
                r_u = df_u[df_u['id'] == id_a].iloc[0]
                n_nome = st.text_input("Nome", value=r_u['nome'])
                n_senha = st.text_input("Senha", value=r_u['senha'])
                n_unid = st.selectbox("Unidade", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"], index=["JURUBATUBA", "JUNDIAI", "CUBATÃO"].index(r_u['unidade']))
                n_cargo = st.selectbox("💼 Cargo (Nível de Acesso)", ["Almoxarife", "Supervisor"], index=["Almoxarife", "Supervisor"].index(r_u['cargo']))
                if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE usuarios SET nome=?, senha=?, unidade=?, cargo=? WHERE id=?", (n_nome.strip(), n_senha.strip(), n_unid, n_cargo, id_a))
                    conn.commit(); st.success("Usuário Atualizado!"); st.rerun()
                    
    conn.close()
