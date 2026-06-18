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

    # Tabela de Auditorias do Supervisor (Acuracidade)
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
        "auditorias_supervisor": ["unidade TEXT DEFAULT 'JURUBATUBA'", "ativo TEXT"]
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

    # Administradores padrão
    try:
        cursor.execute("UPDATE usuarios SET cargo = 'Supervisor' WHERE nome LIKE '%Yago%' OR nome LIKE '%Administrador%'")
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
if 'ultimo_item_sucesso' not in st.session_state: st.session_state.ultimo_item_sucesso = ""

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
            with c_rec:
                if st.button("🔑 Alterar Senha", use_container_width=True):
                    st.session_state.tela_acesso = "recuperar"; st.rerun()
                    
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
                    if novo_nome and cpf_l and novo_email and nova_senha:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO usuarios (nome, cpf, email, senha, unidade, cargo) VALUES (?, ?, ?, ?, ?, 'Almoxarife')", (novo_nome.strip(), cpf_l, novo_email.strip(), nova_senha, unidade_cadastro))
                            conn.commit()
                            st.success("✅ Cadastrado!")
                            st.session_state.tela_acesso = "login"; st.rerun()
                        except: st.error("❌ CPF ou E-mail já cadastrado!")
            if st.button("◀ Voltar"):
                st.session_state.tela_acesso = "login"; st.rerun()
    conn.close()

# --- INSTÂNCIA LOGADA ---
else:
    conn = conectar_banco()
    
    # Validações de nível de acesso
    nome_u = st.session_state.operador.lower()
    eh_supervisor = st.session_state.cargo_usuario == "Supervisor" or "yago" in nome_u
    eh_yago_master = "yago" in nome_u or "administrador" in nome_u
    
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios WHERE unidade = ? ORDER BY id DESC", conn, params=(st.session_state.unidade_selecionada,))
    df_inventarios_sup = pd.read_sql_query("SELECT * FROM inventarios_supervisor WHERE unidade = ? ORDER BY id DESC", conn, params=(st.session_state.unidade_selecionada,))

    # Mapeamento dinâmico de colunas
    def obter_coluna(df, opcoes):
        if df is not None:
            for op in opcoes:
                for c in df.columns:
                    if op.lower().replace(" ", "") in str(c).lower().replace(" ", "").replace(".", ""):
                        return c
        return None

    # INTERFACE LATERAL (SIDEBAR)
    with st.sidebar:
        st.subheader(f"🏢 {st.session_state.unidade_selecionada}")
        st.write(f"👤 {st.session_state.operador} ({st.session_state.cargo_usuario})")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logged_in = False; st.rerun()
            
        st.markdown("---")
        st.write("📂 **Base Geral (Funcionários)**")
        ar_excel = st.file_uploader("Suba o arquivo Excel Geral", type=["xlsx"], label_visibility="collapsed")
        if ar_excel:
            st.session_state.base_sistema = pd.read_excel(ar_excel)
            
        st.markdown("---")
        if df_inventarios.empty:
            id_inventario_atual = None
            inventario_selected_obj = None
        else:
            lista_inv = [f"{r['id']} – {r['nome']} ({r['status']})" for idx, r in df_inventarios.iterrows()]
            inv_sel = st.selectbox("Selecione o Inventário", lista_inv)
            id_inventario_atual = inv_sel.split(" – ")[0]
            inventario_selected_obj = df_inventarios[df_inventarios['id'] == id_inventario_atual].iloc[0]

        if eh_supervisor:
            with st.expander("➕ Novo Pasta de Inventário"):
                with st.form("form_novo_inv", clear_on_submit=True):
                    n_inv = st.text_input("Nome")
                    if st.form_submit_button("Criar") and n_inv:
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM inventarios ORDER BY ROWID DESC LIMIT 1")
                        last = cursor.fetchone()
                        nxt = int(last[0].replace('#','')) + 1 if last else 1
                        cursor.execute("INSERT INTO inventarios (id, nome, data, status, unidade) VALUES (?, ?, ?, 'Aberto', ?)", (f"#{nxt}", n_inv, datetime.date.today().strftime("%Y-%m-%d"), st.session_state.unidade_selecionada))
                        conn.commit(); st.rerun()

    # --- DEFINIÇÃO E RENDERIZAÇÃO DAS ABAS NA ORDEM EXATA ---
    ordem_abas = ["🔍 Contar Item", "📊 Contagem Atual", "📄 Base de Estoque", "📁 Histórico Geral", "🏆 Desempenho e Prazos"]
    if eh_supervisor:
        ordem_abas += ["🔬 Painel Supervisor", "📈 Acuracidade Estoque", "⚙️ Gerenciar Estoques"]
    if eh_yago_master:
        ordem_abas.append("👥 Gestão de Usuários")
        
    abas_gui = st.tabs(ordem_abas)

    # ------------------------------------------------------------------------------------------------------
    # 🔍 ABA: CONTAR ITEM
    # ------------------------------------------------------------------------------------------------------
    if "🔍 Contar Item" in ordem_abas:
        with abas_gui[ordem_abas.index("🔍 Contar Item")]:
            if id_inventario_atual is None or st.session_state.base_sistema is None:
                st.warning("⚠️ Selecione a base e o inventário na barra lateral.")
            elif inventario_selected_obj['status'] == "Fechado":
                st.error("🔒 Inventário Fechado.")
            else:
                c_cod = obter_coluna(st.session_state.base_sistema, ['códproduto', 'codproduto', 'codigo', 'cod'])
                c_desc = obter_coluna(st.session_state.base_sistema, ['descproduto', 'descricao'])
                c_un = obter_coluna(st.session_state.base_sistema, ['unidmedida', 'unidade', 'un'])
                c_est = obter_coluna(st.session_state.base_sistema, ['idestoquefísico', 'idestoque'])
                c_qtd = obter_coluna(st.session_state.base_sistema, ['qtdestoque', 'quantidade', 'saldo'])
                c_loc = obter_coluna(st.session_state.base_sistema, ['descestoquefisico', 'localizacao'])

                bip_prod = st.text_input("💻 Bipar Código do Produto", key=f"bip_op_{st.session_state.contador_reset}")
                if bip_prod:
                    prod_l = str(bip_prod).strip().upper()
                    it = st.session_state.base_sistema[st.session_state.base_sistema[c_cod].astype(str).str.upper().str.strip() == prod_l]
                    if not it.empty:
                        row = it.iloc[0]
                        st.markdown(f"### 📦 {row[c_desc]} ({row[c_un]})")
                        with st.form("f_salva_contagem", clear_on_submit=True):
                            q_cont = st.number_input("Quantidade Física", min_value=0, step=1)
                            n_ativ = st.text_input("Ativo / Placa (Obrigatório se houver)")
                            obs = st.text_input("Observação")
                            if st.form_submit_button("Confirmar Lançamento", type="primary"):
                                cursor = conn.cursor()
                                q_sis = int(row[c_qtd]) if pd.notna(row[c_qtd]) else 0
                                cursor.execute("""
                                    INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, observacao, operador, data_hora, unidade)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (id_inventario_atual.replace('#',''), str(row[c_est]), str(row[c_loc]), prod_l, str(row[c_desc]), str(row[c_un]), q_sis, q_cont, q_cont - q_sis, n_ativ.strip().upper(), obs, st.session_state.operador, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.unidade_selecionada))
                                conn.commit()
                                st.success("Contagem salva!")
                                st.session_state.contador_reset += 1; st.rerun()
                    else:
                        st.error("Produto não localizado na base.")

    # ------------------------------------------------------------------------------------------------------
    # 📊 ABA: CONTAGEM ATUAL
    # ------------------------------------------------------------------------------------------------------
    if "📊 Contagem Atual" in ordem_abas:
        with abas_gui[ordem_abas.index("📊 Contagem Atual")]:
            if id_inventario_atual:
                df_c = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? AND unidade = ?", conn, params=(id_inventario_atual.replace('#',''), st.session_state.unidade_selecionada))
                st.dataframe(df_c, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum inventário selecionado.")

    # ------------------------------------------------------------------------------------------------------
    # 📄 ABA: BASE DE ESTOQUE
    # ------------------------------------------------------------------------------------------------------
    if "📄 Base de Estoque" in ordem_abas:
        with abas_gui[ordem_abas.index("📄 Base de Estoque")]:
            if st.session_state.base_sistema is not None:
                st.dataframe(st.session_state.base_sistema, use_container_width=True)

    # ------------------------------------------------------------------------------------------------------
    # 📁 ABA: HISTÓRICO GERAL
    # ------------------------------------------------------------------------------------------------------
    if "📁 Histórico Geral" in ordem_abas:
        with abas_gui[ordem_abas.index("📁 Histórico Geral")]:
            df_h = pd.read_sql_query("SELECT * FROM inventarios WHERE unidade = ?", conn, params=(st.session_state.unidade_selecionada,))
            st.dataframe(df_h, use_container_width=True)

    # ------------------------------------------------------------------------------------------------------
    # 🏆 ABA: DESEMPENHO E PRAZOS
    # ------------------------------------------------------------------------------------------------------
    if "🏆 Desempenho e Prazos" in ordem_abas:
        with abas_gui[ordem_abas.index("🏆 Desempenho e Prazos")]:
            st.info("Painel de monitoramento temporal de acuracidade por setor e prazos de recontagem.")

    # ------------------------------------------------------------------------------------------------------
    # 🔬 ABA: PAINEL SUPERVISOR (ATUALIZADA)
    # ------------------------------------------------------------------------------------------------------
    if "🔬 Painel Supervisor" in ordem_abas:
        with abas_gui[ordem_abas.index("🔬 Painel Supervisor")]:
            st.title("🔬 Módulo Amostral e Auditoria do Supervisor")
            
            # 1. Gerenciamento de Pastas Amostrais
            if df_inventarios_sup.empty:
                st.warning("⚠️ Crie uma auditoria amostral abaixo para iniciar.")
                id_inv_sup_atual = None
            else:
                lista_sup = [f"{r['id']} – {r['nome']} ({r['status']})" for idx, r in df_inventarios_sup.iterrows()]
                inv_sup_sel = st.selectbox("Selecione a Auditoria Amostral Ativa", lista_sup)
                id_inv_sup_atual = inv_sup_sel.split(" – ")[0]
                obj_sup_atual = df_inventarios_sup[df_inventarios_sup['id'] == id_inv_sup_atual].iloc[0]
                
                # Botão para Fechamento do Inventário Amostral
                if obj_sup_atual['status'] == 'Aberto':
                    if st.button("🔒 Fechar esta Auditoria Amostral", type="primary"):
                        cursor = conn.cursor()
                        cursor.execute("UPDATE inventarios_supervisor SET status = 'Fechado' WHERE id = ? AND unidade = ?", (id_inv_sup_atual, st.session_state.unidade_selecionada))
                        conn.commit()
                        st.success("Auditoria fechada!")
                        st.rerun()

            with st.expander("➕ Nova Pasta de Auditoria Amostral"):
                with st.form("f_new_sup", clear_on_submit=True):
                    n_sup = st.text_input("Nome do Lote Amostral")
                    if st.form_submit_button("Criar") and n_sup:
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM inventarios_supervisor ORDER BY ROWID DESC LIMIT 1")
                        l_sup = cursor.fetchone()
                        n_id = int(l_sup[0].replace('SUP-#','')) + 1 if l_sup else 1
                        cursor.execute("INSERT INTO inventarios_supervisor (id, nome, data, status, unidade) VALUES (?, ?, ?, 'Aberto', ?)", (f"SUP-#{n_id}", n_sup, datetime.date.today().strftime("%Y-%m-%d"), st.session_state.unidade_selecionada))
                        conn.commit(); st.rerun()
            
            st.markdown("---")
            
            # 2. Upload da Planilha Base que será Contada
            st.subheader("📤 Carregar Base Específica para Amostragem")
            ar_sup = st.file_uploader("Suba a planilha Excel da amostragem", type=["xlsx"], key="sup_excel_file")
            if ar_sup:
                st.session_state.base_supervisor = pd.read_excel(ar_sup)
                st.success("Planilha de amostragem carregada!")

            # 3. Campo de Bipagem e Lançamento de Auditoria
            if id_inv_sup_atual and 'obj_sup_atual' in locals() and obj_sup_atual['status'] == 'Aberto' and st.session_state.base_supervisor is not None:
                st.markdown("### 💻 Bipagem de Amostragem")
                
                # Identificação das colunas da planilha do supervisor
                df_s = st.session_state.base_supervisor
                cs_cod = obter_coluna(df_s, ['códproduto', 'codproduto', 'codigo', 'cod'])
                cs_desc = obter_coluna(df_s, ['descproduto', 'descricao'])
                cs_est = obter_coluna(df_s, ['idestoquefísico', 'idestoque'])
                cs_loc = obter_coluna(df_s, ['descestoquefisico', 'localizacao'])
                cs_qtd = obter_coluna(df_s, ['qtdestoque', 'quantidade', 'saldo'])
                cs_atv = obter_coluna(df_s, ['ativo', 'n ativo', 'numero ativo'])
                
                bip_sup = st.text_input("Bipar Produto (Etiqueta/Código)", key="bip_supervisor_input")
                if bip_sup:
                    bl = str(bip_sup).strip().upper()
                    it_sup = df_s[df_s[cs_cod].astype(str).str.upper().str.strip() == bl]
                    
                    if not it_sup.empty:
                        r_sup = it_sup.iloc[0]
                        st.markdown(f"**Item Localizado:** {r_sup[cs_desc]}")
                        
                        # Definição e obrigatoriedade do Ativo
                        val_ativo_sistema = str(r_sup[cs_atv]).strip() if cs_atv and pd.notna(r_sup[cs_atv]) else ""
                        tem_ativo_obrigatorio = val_ativo_sistema != "" and val_ativo_sistema.lower() != "nan"
                        
                        if tem_ativo_obrigatorio:
                            st.warning(f"⚠️ **Este item possui o Ativo [{val_ativo_sistema}] vinculado no sistema. O preenchimento é obrigatório!**")

                        with st.form("form_auditoria_salvar", clear_on_submit=True):
                            q_aud = st.number_input("Quantidade Auditada (Física)", min_value=0, step=1)
                            
                            # Condicional do Ativo Informado
                            if tem_ativo_obrigatorio:
                                label_atv = "Número do Ativo / Placa (OBRIGATÓRIO)"
                                f_ativo = st.text_input(label_atv)
                            else:
                                label_atv = "Número do Ativo / Placa (Opcional)"
                                f_ativo = st.text_input(label_atv)
                                
                            # Conferência visual para alimentar Acuracidade
                            conf_etiqueta = st.radio("🏷️ A etiqueta de identificação está correta no local?", ["Sim", "Não"], horizontal=True)
                            conf_localizacao = st.radio("📍 A localização física está correta conforme sistema?", ["Sim", "Não"], horizontal=True)
                            
                            if st.form_submit_button("✓ Salvar na Acuracidade", type="primary"):
                                if tem_ativo_obrigatorio and not f_ativo.strip():
                                    st.error("❌ Erro: O campo Ativo é obrigatório para este produto!")
                                else:
                                    q_s_val = int(r_sup[cs_qtd]) if pd.notna(r_sup[cs_qtd]) else 0
                                    est_id_val = str(r_sup[cs_est]) if cs_est else "0"
                                    loc_desc_val = str(r_sup[cs_loc]) if cs_loc else "Geral"
                                    
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        INSERT INTO auditorias_supervisor (
                                            inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, 
                                            qtd_sistema, qtd_auditada, diferenca, etiqueta_correta, localizacao_correta, 
                                            supervisor, data_hora, ativo, unidade
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (
                                        id_inv_sup_atual, est_id_val, loc_desc_val, bl, str(r_sup[cs_desc]),
                                        q_s_val, q_aud, q_aud - q_s_val, conf_etiqueta, conf_localizacao,
                                        st.session_state.operador, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        f_ativo.strip().upper(), st.session_state.unidade_selecionada
                                    ))
                                    conn.commit()
                                    st.success("📊 Auditoria de acuracidade processada com sucesso!")
                                    st.rerun()
                    else:
                        st.error("❌ Código do produto não encontrado na planilha de amostragem.")

    # ------------------------------------------------------------------------------------------------------
    # 📈 ABA: ACURACIDADE ESTOQUE
    # ------------------------------------------------------------------------------------------------------
    if "📈 Acuracidade Estoque" in ordem_abas:
        with abas_gui[ordem_abas.index("📈 Acuracidade Estoque")]:
            st.title("📈 Relatório de Acuracidade de Estoque")
            df_ac = pd.read_sql_query("SELECT * FROM auditorias_supervisor WHERE unidade = ? ORDER BY id DESC", conn, params=(st.session_state.unidade_selecionada,))
            if df_ac.empty:
                st.info("Nenhuma auditoria realizada ainda.")
            else:
                # KPIs de Performance baseados nas respostas do supervisor
                total_aud = len(df_ac)
                etiquetas_ok = len(df_ac[df_ac['etiqueta_correta'] == 'Sim'])
                loc_ok = len(df_ac[df_ac['localizacao_correta'] == 'Sim'])
                
                pct_etiqueta = (etiquetas_ok / total_aud) * 100 if total_aud > 0 else 100
                pct_loc = (loc_ok / total_aud) * 100 if total_aud > 0 else 100
                
                kpi_ac1, kpi_ac2, kpi_ac3 = st.columns(3)
                with kpi_ac1: st.metric("Total de Itens Auditados", total_aud)
                with kpi_ac2: st.metric("Acuracidade de Etiquetagem", f"{pct_etiqueta:.1f}%")
                with kpi_ac3: st.metric("Acuracidade de Localização", f"{pct_loc:.1f}%")
                
                st.markdown("---")
                st.dataframe(df_ac.drop(columns=['unidade'], errors='ignore'), use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------------------------------------------
    # ⚙️ ABA: GERENCIAR ESTOQUES
    # ------------------------------------------------------------------------------------------------------
    if "⚙️ Gerenciar Estoques" in ordem_abas:
        with abas_gui[ordem_abas.index("⚙️ Gerenciar Estoques")]:
            st.title("⚙️ Gerenciar Setores e Estoques")
            df_meus_est = pd.read_sql_query("SELECT id as 'ID', descricao as 'Descrição' FROM cadastros_estoques WHERE unidade = ? ORDER BY id", conn, params=(st.session_state.unidade_selecionada,))
            st.dataframe(df_meus_est, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------------------------------------------
    # 👥 ABA: GESTÃO DE USUÁRIOS
    # ------------------------------------------------------------------------------------------------------
    if "👥 Gestão de Usuários" in ordem_abas:
        with abas_gui[ordem_abas.index("👥 Gestão de Usuários")]:
            st.title("👥 Controle de Acesso")
            df_u = pd.read_sql_query("SELECT id, nome, cpf, email, unidade, cargo FROM usuarios", conn)
            st.dataframe(df_u, use_container_width=True, hide_index=True)
                    
    conn.close()
