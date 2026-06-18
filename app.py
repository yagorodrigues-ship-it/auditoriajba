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
    conn = sqlite3.connect('banco_inventario.db', check_same_thread=False)
    return conn

def inicializar_banco():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Tabela de usuários/colaboradores com nível de acesso (cargo)
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
    
    # Tabela dinâmica para os Supervisores cadastrarem seus próprios estoques por unidade
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
    
    # Tabela de inventários do Supervisor
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
    
    # --- MIGRAÇÕES OPERACIONAIS DE ESTRUTURA ---
    tab_alteracoes = {
        "usuarios": ["unidade TEXT DEFAULT 'JURUBATUBA'", "cargo TEXT DEFAULT 'Almoxarife'"],
        "inventarios": ["unidade TEXT DEFAULT 'JURUBATUBA'"],
        "inventarios_supervisor": ["unidade TEXT DEFAULT 'JURUBATUBA'"],
        "contagens": ["lote TEXT DEFAULT ''", "unidade TEXT DEFAULT 'JURUBATUBA'"],
        "auditorias_supervisor": ["unidade TEXT DEFAULT 'JURUBATUBA'"]
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

    # Garantir privilégios Master Iniciais do Yago e Administrador
    try:
        cursor.execute("UPDATE usuarios SET cargo = 'Supervisor' WHERE nome LIKE '%Yago Rodrigues%' OR nome LIKE '%Administrador%'")
        conn.commit()
    except:
        pass

    # Carga Inicial de Estoques Fixos de Jurubatuba se estiver vazio
    cursor.execute("SELECT COUNT(*) FROM cadastros_estoques WHERE unidade = 'JURUBATUBA'")
    if cursor.fetchone()[0] == 0:
        estoques_padrao_jba = [
            ("1077", "JBA - CLASSE D"), ("1078", "JBA - COPA E COZINHA"), ("1080", "JBA - DADOS - CLIENTE"),
            ("1082", "JBA - VIVO VITA - CLIENTE"), ("1084", "JBA - EPI-EPC"), ("1086", "JBA - EQUIPAMENTOS"),
            ("1088", "JBA - FERRAMENTAL"), ("1089", "JBA - KIT FERRAMENTAL CONTRATACOES"), ("1090", "JBA - FERRAMENTAS DE CANTEIRO"),
            ("1102", "1385 - LA JBA - CLIENTE"), ("1104", "JBA - MATERIAL DE ESCRITORIO - SUPRIMENTOS DE INFORMATICA"),
            ("1106", "JBA - MOBILIARIO"), ("1108", "1071 - EXEC SEGREGADO IMPLANTACAO JBA - CLIENTE"),
            ("1113", "1385 - MANUTENCAO JBA - CLIENTE"), ("1118", "JBA - PROPRIO GERAL"), ("1122", "JBA - GRANDES OBRAS IMPLANTACAO"),
            ("1124", "JBA - PROPRIO TIM"), ("1140", "JBA - SPEEDY/FTTX - CLIENTE"), ("1144", "1385 - MANUTENCAO JBA CLIENTE RESERVADO"),
            ("1149", "JBA - UNIFORME"), ("2149", "JBA - SPEEDY/FTTX DEVOLUCAO NOVO COM DEFEITO - CLIENTE"),
            ("2183", "1071 - BOL IMPLANTANCAO JBA - CLIENTE"), ("2185", "JBA - PROPRIO FATURA B PLANTA EXTERNA - BDI"),
            ("2188", "1071 - IMPLANTACAO JBA CLIENTE RESERVADO"), ("2189", "JBA - DEFEITO"), ("2190", "JBA - DEPARTAMENTO T.I"),
            ("2194", "JBA - KITS FERRAMENTAL - DEVOLUCAO"), ("2197", "JBA - EQUIPAMENTOS TI"),
            ("2641", "1259 - IMPLANTACAO JBA - MATERIAL REUTILIZACAO"), ("2643", "1724 - MANUTENCAO JBA - MATERIAL REUTILIZACAO"),
            ("2725", "JBA - RESERVA TIM"), ("2983", "JBA - FORNECEDORES P/ MANUTENCAO - RECARGA"),
            ("3193", "JBA - PROPRIO MATERIAL REAPROVEITAVEL"), ("3395", "LPA - FTTX - CLIENTE"),
            ("3484", "JBA - CELULARES DEFEITO"), ("3546", "JBA - CELULARES")
        ]
        cursor.executemany("INSERT OR IGNORE INTO cadastros_estoques (id, descricao, unidade) VALUES (?, ?, 'JURUBATUBA')", estoques_padrao_jba)
        conn.commit()

    # Criar administrador padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO usuarios (nome, cpf, email, senha, unidade, cargo) 
            VALUES (?, ?, ?, ?, 'JURUBATUBA', 'Supervisor')
        """, ("Administrador Tel", "00000000000", "admin@tel.com.br", "123"))
        
    conn.commit()
    conn.close()

inicializar_banco()

# --- CARREGAMENTO SEGURO DOS INVENTÁRIOS FILTRADOS POR UNIDADE ---
if 'unidade_selecionada' not in st.session_state:
    st.session_state.unidade_selecionada = "JURUBATUBA"
if 'cargo_usuario' not in st.session_state:
    st.session_state.cargo_usuario = "Almoxarife"

conn_init = conectar_banco()
try:
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios WHERE unidade = ? ORDER BY data DESC, id DESC", conn_init, params=(st.session_state.unidade_selecionada,))
except:
    df_inventarios = pd.DataFrame(columns=['id', 'nome', 'data', 'status', 'unidade'])

try:
    df_inventarios_sup = pd.read_sql_query("SELECT * FROM inventarios_supervisor WHERE unidade = ? ORDER BY data DESC, id DESC", conn_init, params=(st.session_state.unidade_selecionada,))
except:
    df_inventarios_sup = pd.DataFrame(columns=['id', 'nome', 'data', 'status', 'unidade'])
conn_init.close()

# --- FUNÇÃO AUXILIAR PARA EXPORTAR EXCEL ---
def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

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
    .bloco-info-link {
        background-color: #fef9e7;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #f9e79f;
        text-align: center;
        margin-top: 15px;
        margin-bottom: 15px;
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

# --- TELA DE ACESSO ---
if not st.session_state.logged_in:
    conn = conectar_banco()
    _, col_login_focada, _ = st.columns([3, 4, 3])
    
    with col_login_focada:
        if st.session_state.tela_acesso == "login":
            st.markdown("<h2 style='text-align: center; border-bottom: none;'>🔒 Acesso ao Sistema</h2>", unsafe_allow_html=True)
            with st.form("login_form"):
                identificador = st.text_input("CPF (somente números) ou E-mail")
                senha = st.text_input("Senha", type="password")
                unidade_login = st.selectbox("📍 Localidade da Auditoria", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"])
                
                botao_login = st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True)
                if botao_login:
                    id_limpo = identificador.strip()
                    doc_limpo = limpar_documento(id_limpo)
                    cursor = conn.cursor()
                    cursor.execute("SELECT nome, unidade, cargo FROM usuarios WHERE (email = ? OR cpf = ?) AND senha = ? AND unidade = ?", (id_limpo, doc_limpo, senha, unidade_login))
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
                if st.button("📝 Criar nova conta", use_container_width=True):
                    st.session_state.tela_acesso = "cadastro"; st.rerun()
            with c_rec:
                if st.button("🔑 Alterar Senha", use_container_width=True):
                    st.session_state.tela_acesso = "recuperar"; st.rerun()
                    
        elif st.session_state.tela_acesso == "cadastro":
            st.markdown("<h2 style='text-align: center; border-bottom: none;'>📝 Cadastro de Colaborador</h2>", unsafe_allow_html=True)
            with st.form("cadastro_form"):
                novo_nome = st.text_input("Nome Completo")
                novo_cpf = st.text_input("CPF (Apenas números)")
                novo_email = st.text_input("E-mail")
                nova_senha = st.text_input("Senha", type="password")
                confirma_senha = st.text_input("Confirme a Senha", type="password")
                unidade_cadastro = st.selectbox("📍 Vincular à Localidade", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"])
                
                btn_cad = st.form_submit_button("Finalizar Cadastro", type="primary", use_container_width=True)
                if btn_cad:
                    cpf_l = limpar_documento(novo_cpf)
                    email_l = novo_email.strip()
                    
                    if not novo_nome or not cpf_l or not email_l or not nova_senha:
                        st.error("⚠️ Preencha todos os campos!")
                    elif nova_senha != confirma_senha:
                        st.error("❌ As senhas não batem!")
                    else:
                        cursor = conn.cursor()
                        cursor.execute("SELECT email, cpf FROM usuarios WHERE cpf = ? OR email = ?", (cpf_l, email_l))
                        usuario_existente = cursor.fetchone()
                        
                        if usuario_existente:
                            st.error("❌ Erro de Cadastro: CPF ou E-mail já ativo!")
                            token_cripto = base64.b64encode(email_l.encode('utf-8')).decode('utf-8')
                            link_direto_cadastro = f"https://auditoriajba.streamlit.app/?recuperar=true&token={token_cripto}"
                            st.markdown(f'<a href="{link_direto_cadastro}" target="_blank"><button style="width:100%; background-color:#e74c3c; color:white; border:none; padding:8px; border-radius:4px; font-weight:bold;">🔗 Gerar Nova Senha Agora</button></a>', unsafe_allow_html=True)
                        else:
                            try:
                                cursor.execute("INSERT INTO usuarios (nome, cpf, email, senha, unidade, cargo) VALUES (?, ?, ?, ?, ?, 'Almoxarife')", (novo_nome.strip(), cpf_l, email_l, nova_senha, unidade_cadastro))
                                conn.commit()
                                st.success("✅ Cadastrado com sucesso!")
                                st.session_state.tela_acesso = "login"; st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro operacional: {e}")
            if st.button("◀ Voltar"):
                st.session_state.tela_acesso = "login"; st.rerun()
    conn.close()

# --- TELA LOGADA DO SISTEMA ---
else:
    conn = conectar_banco()
    
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios WHERE unidade = ? ORDER BY data DESC, id DESC", conn, params=(st.session_state.unidade_selecionada,))
    df_inventarios_sup = pd.read_sql_query("SELECT * FROM inventarios_supervisor WHERE unidade = ? ORDER BY data DESC, id DESC", conn, params=(st.session_state.unidade_selecionada,))
    
    nome_usuario_logado_limpo = st.session_state.operador.lower()
    
    eh_supervisor = st.session_state.cargo_usuario == "Supervisor" or "yago" in nome_usuario_logado_limpo
    eh_yago_master = "yago" in nome_usuario_logado_limpo or "administrador tel" in nome_usuario_logado_limpo
    
    id_inventario_atual_inicial = df_inventarios.iloc[0]['id'].replace('#','') if not df_inventarios.empty else ""
    
    # --- MAPEAMENTO E DEPARA DE COLUNAS ANTECIPADO ---
    col_cod, col_desc, col_local, col_unidade, col_qtd, col_id_estoque = "", "", "", "", "", ""
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
        col_id_estoque = encontrar_coluna(['idestoquefísico', 'idestoqfísico', 'idestoque', 'codestoque'], 0)

    # SIDEBAR
    with st.sidebar:
        if st.button("🔄 Atualizar Dados", type="primary", use_container_width=True):
            st.rerun()
            
        st.subheader(f"🏢 Unidade: {st.session_state.unidade_selecionada}")
        st.write(f"👤 **Operador:** {st.session_state.operador} ({st.session_state.cargo_usuario})")
        if st.button("🚪 Sair da Conta", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.operador = ""
            st.session_state.tela_acesso = "login"
            st.rerun()
            
        st.markdown("---")
        st.write("📂 **Carregar Base de Dados (Funcionários)**")
        arquivo_excel = st.file_uploader("Suba o arquivo Excel (.xlsx)", type=["xlsx"], label_visibility="collapsed", key="func_excel_loader")
        if arquivo_excel is not None and st.session_state.base_sistema is None:
            st.session_state.base_sistema = pd.read_excel(arquivo_excel)
            st.session_state.nome_arquivo_excel = arquivo_excel.name
            st.rerun()
            
        st.markdown("---")
        st.write("📁 **Selecione o inventário**")
        if df_inventarios.empty:
            st.info("Crie um inventário abaixo.")
            id_inventario_atual = None
            inventario_selected_obj = None
        else:
            lista_inv = [f"{row['id']} – {row['nome']} ({row['status']})" for idx, row in df_inventarios.iterrows()]
            inventario_selected = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
            id_inventario_atual = inventario_selected.split(" – ")[0]
            inventario_selected_obj = df_inventarios[df_inventarios['id'] == id_inventario_atual].iloc[0]

        if eh_supervisor:
            with st.expander("➕ Novo Inventário"):
                with st.form("form_novo", clear_on_submit=True):
                    novo_nome = st.text_input("Nome do Inventário")
                    if st.form_submit_button("Criar", type="primary") and novo_nome:
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM inventarios ORDER BY ROWID DESC LIMIT 1")
                        last_row = cursor.fetchone()
                        maior_id = int(last_row[0].replace('#','')) if last_row else 38
                        novo_id = f"#{maior_id + 1}"
                        hoje = datetime.date.today().strftime("%Y-%m-%d")
                        cursor.execute("INSERT INTO inventarios (id, nome, data, status, unidade) VALUES (?, ?, ?, 'Aberto', ?)", (novo_id, novo_nome, hoje, st.session_state.unidade_selecionada))
                        conn.commit()
                        st.rerun()

        # TRAVA 100% CONCLUÍDO FIEL À LOCALIDADE
        if inventario_selected_obj is not None and inventario_selected_obj['status'] == "Aberto":
            itens_esquecidos_lista = []
            if st.session_state.base_sistema is not None:
                df_c_verif = pd.read_sql_query("SELECT cod_produto FROM contagens WHERE inventario_id = ? AND unidade = ?", conn, params=(id_inventario_atual.replace('#',''), st.session_state.unidade_selecionada))
                lista_contados_set = set(df_c_verif['cod_produto'].astype(str).str.upper().str.strip().tolist())
                for idx, r_base in st.session_state.base_sistema.iterrows():
                    cod_b = str(r_base[col_cod]).upper().strip()
                    if cod_b not in lista_contados_set:
                        itens_esquecidos_lista.append(cod_b)

            if len(itens_esquecidos_lista) == 0:
                if st.button("🔒 Fechar Inventário (100%)", use_container_width=True):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE inventarios SET status = 'Fechado' WHERE id = ? AND unidade = ?", (id_inventario_atual, st.session_state.unidade_selecionada))
                    conn.commit()
                    st.rerun()
            else:
                st.error(f"❌ Fechamento Bloqueado: Faltam {len(itens_esquecidos_lista)} materiais na lista.")
                if eh_supervisor:
                    if st.button("⚠️ Forçar Fechamento (ADMIN)", use_container_width=True, type="primary"):
                        cursor = conn.cursor()
                        cursor.execute("UPDATE inventarios SET status = 'Fechado' WHERE id = ? AND unidade = ?", (id_inventario_atual, st.session_state.unidade_selecionada))
                        conn.commit()
                        st.rerun()

        # PROGRESSO LATERAL ISOLADO
        total_itens_base, total_contados, total_pendentes, progresso = 0, 0, 0, 0.0
        if st.session_state.base_sistema is not None and id_inventario_atual is not None:
            total_itens_base = len(st.session_state.base_sistema)
            if eh_supervisor:
                df_contagens_atuais_side = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? AND unidade = ?", conn, params=(id_inventario_atual.replace('#',''), st.session_state.unidade_selecionada))
            else:
                df_contagens_atuais_side = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? AND operador = ? AND unidade = ?", conn, params=(id_inventario_atual.replace('#',''), st.session_state.operador, st.session_state.unidade_selecionada))
                
            contados_validos_set = set(df_contagens_atuais_side['cod_produto'].astype(str).str.upper().str.strip().tolist())
            total_contados = len(df_contagens_atuais_side)
            total_pendentes = max(0, total_itens_base - len(contados_validos_set))
            if total_itens_base > 0:
                progresso = min(1.0, len(contados_validos_set) / total_itens_base)

        st.markdown("---")
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">📋 ITENS NA BASE</div><div class="card-lateral-valor">{total_itens_base}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">✅ SEUS LANÇAMENTOS</div><div class="card-lateral-valor">{total_contados}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">⏳ SUAS PENDÊNCIAS</div><div class="card-lateral-valor">{total_pendentes}</div></div>', unsafe_allow_html=True)
        st.write("**SEU PROGRESSO**")
        st.progress(progresso)

    if st.session_state.ultimo_item_sucesso:
        st.success(st.session_state.ultimo_item_sucesso)
        st.session_state.ultimo_item_sucesso = ""

    # --- DEFINIÇÃO DA NOVA ORDEM EXATA DAS ABAS ---
    todas_as_abas_possiveis = [
        "🔍 Contar Item", 
        "📊 Contagem Atual", 
        "📄 Base de Estoque", 
        "📁 Histórico Geral", 
        "🏆 Desempenho e Prazos", 
        "🔬 Painel Supervisor", 
        "📈 Acuracidade Estoque", 
        "⚙️ Gerenciar Estoques", 
        "👥 Gestão de Usuários"
    ]
    
    # Filtragem estrutural por nível de acesso/cargo
    lista_abas_usuario = ["🔍 Contar Item", "📊 Contagem Atual", "📄 Base de Estoque", "📁 Histórico Geral", "🏆 Desempenho e Prazos"]
    if eh_supervisor:
        lista_abas_usuario += ["🔬 Painel Supervisor", "📈 Acuracidade Estoque", "⚙️ Gerenciar Estoques"]
    if eh_yago_master:
        lista_abas_usuario.append("👥 Gestão de Usuários")
        
    abas_render = st.tabs(lista_abas_usuario)
    
    # ------------------------------------------------------------------------------------------------------
    # 🔍 ABA 1: CONTAR ITEM
    # ------------------------------------------------------------------------------------------------------
    if "🔍 Contar Item" in lista_abas_usuario:
        idx_aba = lista_abas_usuario.index("🔍 Contar Item")
        with abas_render[idx_aba]:
            if id_inventario_atual is None or st.session_state.base_sistema is None:
                st.warning("⚠️ Carregue a base de saldo e crie um inventário na barra lateral.")
            elif inventario_selected_obj['status'] == "Fechado":
                st.error("🔒 Inventário selecionado está Fechado.")
            else:
                c_busca, c_filtro, c_limpar = st.columns([5, 3, 2])
                with c_busca:
                    codigo_input = st.text_input("💻 Código do Produto (etiqueta ou manual)", value="", placeholder="Bipe a etiqueta...", key=f"bip_{st.session_state.contador_reset}")
                with c_filtro:
                    st.selectbox("📍 Estoque Físico", ["Todos"], key=f"f_{st.session_state.contador_reset}")
                with c_limpar:
                    st.write("")
                    if st.button("🗑️ Limpar", use_container_width=True, key="btn_l"):
                        st.session_state.contador_reset += 1; st.rerun()
                        
                if codigo_input:
                    busca_limpa = str(codigo_input).upper().strip()
                    codigo_rastreio = busca_limpa.split(" - ")[-1].strip() if " - " in busca_limpa else busca_limpa
                    
                    item = st.session_state.base_sistema[st.session_state.base_sistema[col_cod].astype(str).str.upper().str.strip() == codigo_rastreio]
                    if not item.empty:
                        unid_val = item.iloc[0][col_unidade] if col_unidade in item.columns else "UN"
                        desc_val = item.iloc[0][col_desc]
                        local_val = item.iloc[0][col_local] if col_local in item.columns else "Não Informado"
                        id_estoque_val = str(item.iloc[0][col_id_estoque]).strip() if col_id_estoque in item.columns else ""
                        
                        try:
                            qtd_sis = int(pd.to_numeric(item.iloc[0][col_qtd], errors='coerce'))
                            if pd.isna(qtd_sis): qtd_sis = 0
                        except: qtd_sis = 0
                        
                        b1, b2, b3, b4 = st.columns(4)
                        b1.markdown(f'<div class="bloco-info"><div class="bloco-titulo">CÓD. PRODUTO</div><div class="bloco-valor">{codigo_rastreio}</div></div>', unsafe_allow_html=True)
                        b2.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:0px;"><div class="bloco-titulo">ESTOQUE FÍSICO</div><div class="bloco-valor" style="font-size:22px;">{local_val}</div></div>', unsafe_allow_html=True)
                        b3.markdown(f'<div class="bloco-info"><div class="bloco-titulo">UNID. MEDIDA</div><div class="bloco-valor">{unid_val}</div></div>', unsafe_allow_html=True)
                        b4.markdown('<div class="bloco-info"><div class="bloco-titulo">STATUS BARRA</div><div class="bloco-valor" style="color:#2ecc71;">● Conectado</div></div>', unsafe_allow_html=True)
                        
                        st.markdown(f"**Descrição:** {desc_val}")
                        
                        with st.form("confirmar_form", clear_on_submit=True):
                            qtd_fisica = st.number_input("📦 Quantidade contada fisicamente (Obrigatório)", min_value=0, step=1, value=0)
                            ativo_input = st.text_input("🔢 Número do Ativo (Opcional)")
                            observacao = st.text_input("📝 Observação (opcional)")
                            
                            if st.form_submit_button("✓ Confirmar Contagem", type="primary", use_container_width=True):
                                ativo_l = ativo_input.strip().upper()
                                if qtd_fisica <= 0:
                                    st.error("❌ Erro: Informe uma quantidade maior que 0!")
                                else:
                                    agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    lote_val = str(item.iloc[0]['lote']) if 'lote' in item.columns else ""
                                    dif_c = qtd_fisica - qtd_sis
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, observacao, operador, data_hora, lote, unidade)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (id_inventario_atual.replace("#",""), id_estoque_val, local_val, codigo_rastreio, desc_val, unid_val, qtd_sis, qtd_fisica, dif_c, ativo_l, observacao, st.session_state.operador, agora, lote_val, st.session_state.unidade_selecionada))
                                    conn.commit()
                                    st.session_state.ultimo_item_sucesso = f"✅ Lançamento Efetuado com sucesso!"
                                    st.session_state.contador_reset += 1; st.rerun()
                    else:
                        st.error("❌ Código não localizado.")

    # ------------------------------------------------------------------------------------------------------
    # 📊 ABA 2: CONTAGEM ATUAL
    # ------------------------------------------------------------------------------------------------------
    if "📊 Contagem Atual" in lista_abas_usuario:
        idx_aba = lista_abas_usuario.index("📊 Contagem Atual")
        with abas_render[idx_aba]:
            if id_inventario_atual:
                st.subheader(f"Painel Operacional – {id_inventario_atual} ({inventario_selected_obj['nome']})")
                modo_visao = "Apenas Minhas Contagens"
                if eh_supervisor:
                    modo_visao = st.radio("Filtro de Visualização:", ["Apenas Minhas Contagens", "Ver Tudo (Todos os Operadores)"], horizontal=True)

                if modo_visao == "Apenas Minhas Contagens":
                    df_contagens_mutaveis = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? AND operador = ? AND unidade = ? ORDER BY id DESC", conn, params=(id_inventario_atual.replace('#',''), st.session_state.operador, st.session_state.unidade_selecionada))
                else:
                    df_contagens_mutaveis = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? AND unidade = ? ORDER BY id DESC", conn, params=(id_inventario_atual.replace('#',''), st.session_state.unidade_selecionada))

                if df_contagens_mutaveis.empty:
                    st.info("Nenhum item lançado.")
                else:
                    total_auditado = len(df_contagens_mutaveis)
                    itens_divergentes = len(df_contagens_mutaveis[df_contagens_mutaveis['diferenca'] != 0])
                    soma_contada = int(df_contagens_mutaveis['qtd_contada'].sum())
                    soma_sistema = int(df_contagens_mutaveis['qtd_sistema'].sum())
                    diferenca_acumulada = int(df_contagens_mutaveis['diferenca'].sum())
                    
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">📦 ITENS CONTADOS</div><div class="bloco-valor">{total_auditado}</div></div>', unsafe_allow_html=True)
                    with c2: st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">⚠️ COM DIVERGÊNCIA</div><div class="bloco-valor">{itens_divergentes}</div></div>', unsafe_allow_html=True)
                    with c3: st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">QUANTIDADE CONTADA</div><div class="bloco-valor">{soma_contada}</div></div>', unsafe_allow_html=True)
                    with c4: st.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:0px;"><div class="bloco-titulo">QUANTIDADE SISTEMA</div><div class="bloco-valor">{soma_sistema} <span style="font-size:14px; color:#e74c3c;">(Dif: {diferenca_acumulada})</span></div></div>', unsafe_allow_html=True)
                    
                    excel_atual = converter_para_excel(df_contagens_mutaveis)
                    st.download_button(label="📥 Exportar Lançamentos", data=excel_atual, file_name="contagem.xlsx")
                    st.dataframe(df_contagens_mutaveis.drop(columns=['unidade'], errors='ignore'), use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum inventário selecionado.")

    # ------------------------------------------------------------------------------------------------------
    # 📄 ABA 3: BASE DE ESTOQUE
    # ------------------------------------------------------------------------------------------------------
    if "📄 Base de Estoque" in lista_abas_usuario:
        idx_aba = lista_abas_usuario.index("📄 Base de Estoque")
        with abas_render[idx_aba]:
            if st.session_state.base_sistema is not None:
                st.subheader("📄 Espelho Base de Saldo")
                st.dataframe(st.session_state.base_sistema, use_container_width=True)
            else:
                st.info("Nenhuma base de dados ativa na sessão atual.")

    # ------------------------------------------------------------------------------------------------------
    # 📁 ABA 4: HISTÓRICO GERAL
    # ------------------------------------------------------------------------------------------------------
    if "📁 Histórico Geral" in lista_abas_usuario:
        idx_aba = lista_abas_usuario.index("📁 Histórico Geral")
        with abas_render[idx_aba]:
            st.title("📁 Arquivo Geral de Movimentações")
            c_dt1, c_dt2 = st.columns(2)
            with c_dt1: data_inicio_filtro = st.date_input("Data Inicial (Opcional)", value=None, key="hist_dt_ini_blank")
            with c_dt2: data_fim_filtro = st.date_input("Data Final (Opcional)", value=None, key="hist_dt_fim_blank")
                
            st.markdown("---")
            df_inventarios['datetime_parsed'] = pd.to_datetime(df_inventarios['data'], errors='coerce').dt.date
            df_filtrados = df_inventarios[df_inventarios['unidade'] == st.session_state.unidade_selecionada]
            
            if data_inicio_filtro: df_filtrados = df_filtrados[df_filtrados['datetime_parsed'] >= data_inicio_filtro]
            if data_fim_filtro: df_filtrados = df_filtrados[df_filtrados['datetime_parsed'] <= data_fim_filtro]
                
            st.write(f"Total de pastas nesta unidade: {len(df_filtrados)}")
            if df_filtrados.empty:
                st.info("Nenhum inventário localizado no filtro selecionado.")
            else:
                tamanho_pagina = 15
                total_itens = len(df_filtrados)
                total_paginas = (total_itens - 1) // tamanho_pagina + 1
                if st.session_state.pagina_historico >= total_paginas: st.session_state.pagina_historico = 0
                    
                df_pagina_atual = df_filtrados.iloc[st.session_state.pagina_historico * tamanho_pagina : (st.session_state.pagina_historico + 1) * tamanho_pagina]
                for idx, inv in df_pagina_atual.iterrows():
                    id_inv_proc = inv['id'].replace('#','')
                    df_hist_inv = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? AND unidade = ? ORDER BY id DESC", conn, params=(id_inv_proc, st.session_state.unidade_selecionada))
                    with st.expander(f"📁 {inv['id']} – {inv['nome']} | Data: {inv['data']} | Status: {inv['status']} ({len(df_hist_inv)} contados)"):
                        if not df_hist_inv.empty:
                            excel_geral_hist = converter_para_excel(df_hist_inv)
                            st.download_button(label="📥 Baixar Pasta em Excel", data=excel_geral_hist, file_name=f"inventario_{inv['id']}.xlsx", key=f"dl_{inv['id']}")
                            st.dataframe(df_hist_inv.drop(columns=['unidade'], errors='ignore'), use_container_width=True, hide_index=True)
                        else:
                            st.info("Nenhuma contagem feita nesta pasta.")
                            
                st.markdown("---")
                col_pag1, col_pag_texto, col_pag2 = st.columns([2, 6, 2])
                with col_pag1:
                    if st.button("◀ Anterior", use_container_width=True, disabled=(st.session_state.pagina_historico == 0)):
                        st.session_state.pagina_historico -= 1; st.rerun()
                with col_pag_texto:
                    st.markdown(f"<p style='text-align: center; margin-top: 7px;'>Página <strong>{st.session_state.pagina_historico + 1}</strong> de <strong>{total_paginas}</strong></p>", unsafe_allow_html=True)
                with col_pag2:
                    if st.button("Próximo ▶", use_container_width=True, disabled=(st.session_state.pagina_historico >= total_paginas - 1)):
                        st.session_state.pagina_historico += 1; st.rerun()

    # ------------------------------------------------------------------------------------------------------
    # 🏆 ABA 5: DESEMPENHO E PRAZOS
    # ------------------------------------------------------------------------------------------------------
    if "🏆 Desempenho e Prazos" in lista_abas_usuario:
        idx_aba = lista_abas_usuario.index("🏆 Desempenho e Prazos")
        with abas_render[idx_aba]:
            st.title("🏆 Validade e Prazos de Auditoria Temporal")
            df_m_est = pd.read_sql_query("SELECT id, descricao FROM cadastros_estoques WHERE unidade = ?", conn, params=(st.session_state.unidade_selecionada,))
            df_lasts = pd.read_sql_query("SELECT id_estoque, MAX(data_hora) as u_data FROM contagens WHERE unidade = ? GROUP BY id_estoque", conn, params=(st.session_state.unidade_selecionada,))
            map_lasts = dict(zip(df_lasts['id_estoque'].astype(str).str.strip(), df_lasts['u_data']))
            
            hoje_dt = datetime.datetime.now()
            dados_prazos = []
            bom_count, auditar_count, criticos_count = 0, 0, 0
            
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
            
            st.write("")
            if dados_prazos: st.dataframe(pd.DataFrame(dados_prazos), use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------------------------------------------
    # 🔬 ABA 6: PAINEL SUPERVISOR (ATUALIZADA)
    # ------------------------------------------------------------------------------------------------------
    if "🔬 Painel Supervisor" in lista_abas_usuario:
        idx_aba = lista_abas_usuario.index("🔬 Painel Supervisor")
        with abas_render[idx_aba]:
            st.title("🔬 Módulo Amostral do Supervisor")
            
            if df_inventarios_sup.empty:
                st.info("Nenhum inventário amostral aberto.")
                id_inv_sup_atual = None
            else:
                lista_inv_sup = [f"{r['id']} – {r['nome']} ({r['status']})" for idx, r in df_inventarios_sup.iterrows()]
                inv_sup_selected = st.selectbox("Selecione a sua Auditoria Amostral", lista_inv_sup, key="sel_box_sup_local_v3")
                id_inv_sup_atual = inv_sup_selected.split(" – ")[0]
                inv_sup_selected_obj = df_inventarios_sup[df_inventarios_sup['id'] == id_inv_sup_atual].iloc[0]
                
                # --- BOTÃO PARA FECHAR INVENTÁRIO DO SUPERVISOR ---
                if inv_sup_selected_obj['status'] == 'Aberto':
                    if st.button("🔒 Fechar Lote Amostral do Supervisor", type="primary"):
                        cursor = conn.cursor()
                        cursor.execute("UPDATE inventarios_supervisor SET status = 'Fechado' WHERE id = ? AND unidade = ?", (id_inv_sup_atual, st.session_state.unidade_selecionada))
                        conn.commit(); st.rerun()

            with st.popover("➕ Novo Inventário Supervisor", use_container_width=True):
                with st.form("form_novo_sup", clear_on_submit=True):
                    nome_sup_inv = st.text_input("Nome da Auditoria Amostral")
                    if st.form_submit_button("Criar Lote", type="primary") and nome_sup_inv:
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM inventarios_supervisor ORDER BY ROWID DESC LIMIT 1")
                        last_sup_row = cursor.fetchone()
                        maior_id_sup = int(last_sup_row[0].replace('SUP-#','')) if last_sup_row else 0
                        novo_id_sup = f"SUP-#{maior_id_sup + 1}"
                        hoje_sup = datetime.date.today().strftime("%Y-%m-%d")
                        cursor.execute("INSERT INTO inventarios_supervisor (id, nome, data, status, unidade) VALUES (?, ?, ?, 'Aberto', ?)", (novo_id_sup, nome_sup_inv, hoje_sup, st.session_state.unidade_selecionada))
                        conn.commit(); st.rerun()
                        
            st.markdown("---")
            
            # --- UPLOAD DE PLANILHA DO ESTOQUE QUE VAMOS CONTAR ---
            st.subheader("📤 Carregar Planilha de Amostragem do Supervisor")
            arquivo_supervisor = st.file_uploader("Suba a planilha Excel para a auditoria amostral (.xlsx)", type=["xlsx"], key="sup_excel_loader_v4")
            
            if arquivo_supervisor is not None:
                try:
                    df_temp_check = pd.read_excel(arquivo_supervisor)
                    colunas_norm = [str(c).strip().lower().replace("º", "").replace("ó", "o") for c in df_temp_check.columns]
                    tem_ativo = any(x in colunas_norm for x in ['ativo', 'n ativo', 'numero ativo', 'cod ativo'])
                    
                    # --- TRAVA DE ATIVO OBRIGATÓRIO NA PLANILHA ---
                    if not tem_ativo:
                        st.error("❌ Erro de Validação: A coluna 'Ativo' é OBRIGATÓRIA e não foi localizada na planilha!")
                        st.session_state.base_supervisor = None
                    elif df_temp_check.iloc[:, [i for i, c in enumerate(colunas_norm) if c in ['ativo', 'n ativo', 'numero ativo', 'cod ativo']][0]].isnull().any():
                        st.error("❌ Erro de Segurança: Existem linhas com o campo 'Ativo' em branco! Corrija antes de prosseguir.")
                        st.session_state.base_supervisor = None
                    else:
                        st.session_state.base_supervisor = df_temp_check
                        st.success("✅ Planilha base validada e carregada com sucesso!")
                except Exception as e:
                    st.error(f"Erro: {e}")
                    
            if id_inv_sup_atual and 'inv_sup_selected_obj' in locals() and inv_sup_selected_obj['status'] == 'Aberto' and st.session_state.base_supervisor is not None:
                st.markdown("### 🔍 Realizar Auditoria Amostral")
                bip_supervisor = st.text_input("💻 Bipar Item para Auditoria", value="", placeholder="Bipe o código do material...")
                
                if bip_supervisor:
                    busca_sup = str(bip_supervisor).upper().strip()
                    # Lógica de depara e gravação forçando o ATIVO OBRIGATÓRIO no formulário
                    st.info(f"Item bipado: {busca_sup}")

    # ------------------------------------------------------------------------------------------------------
    # 📈 ABA 7: ACURACIDADE ESTOQUE
    # ------------------------------------------------------------------------------------------------------
    if "📈 Acuracidade Estoque" in lista_abas_usuario:
        idx_aba = lista_abas_usuario.index("📈 Acuracidade Estoque")
        with abas_render[idx_aba]:
            st.title("📈 Acuracidade Local")
            df_ac = pd.read_sql_query("SELECT * FROM auditorias_supervisor WHERE unidade = ?", conn, params=(st.session_state.unidade_selecionada,))
            st.dataframe(df_ac.drop(columns=['unidade'], errors='ignore'), use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------------------------------------------
    # ⚙️ ABA 8: GERENCIAR ESTOQUES
    # ------------------------------------------------------------------------------------------------------
    if "⚙️ Gerenciar Estoques" in lista_abas_usuario:
        idx_aba = lista_abas_usuario.index("⚙️ Gerenciar Estoques")
        with abas_render[idx_aba]:
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

    # ------------------------------------------------------------------------------------------------------
    # 👥 ABA 9: GESTÃO DE USUÁRIOS
    # ------------------------------------------------------------------------------------------------------
    if "👥 Gestão de Usuários" in lista_abas_usuario:
        idx_aba = lista_abas_usuario.index("👥 Gestão de Usuários")
        with abas_render[idx_aba]:
            st.title("👥 Painel de Controle e Gestão de Usuários")
            df_u = pd.read_sql_query("SELECT id, nome, cpf, email, senha, unidade, cargo FROM usuarios ORDER BY unidade, nome", conn)
            st.dataframe(df_u, use_container_width=True, hide_index=True)
            
            st.write("### 🛠️ Ajustar Permissões")
            with st.form("form_adm_edit"):
                id_a = st.selectbox("Escolha o ID", df_u['id'].tolist(), format_func=lambda x: f"ID {x} - {df_u[df_u['id']==x]['nome'].values[0]} ({df_u[df_u['id']==x]['unidade'].values[0]})")
                r_u = df_u[df_u['id'] == id_a].iloc[0]
                n_nome = st.text_input("Nome", value=r_u['nome'])
                n_senha = st.text_input("Senha", value=r_u['senha'])
                n_unid = st.selectbox("Unidade", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"], index=["JURUBATUBA", "JUNDIAI", "CUBATÃO"].index(r_u['unidade']))
                n_cargo = st.selectbox("💼 Nível de Acesso (Cargo)", ["Almoxarife", "Supervisor"], index=["Almoxarife", "Supervisor"].index(r_u['cargo']))
                
                if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE usuarios SET nome=?, senha=?, unidade=?, cargo=? WHERE id=?", (n_nome.strip(), n_senha.strip(), n_unid, n_cargo, id_a))
                    conn.commit(); st.success("Sucesso!"); st.rerun()
                    
    conn.close()
