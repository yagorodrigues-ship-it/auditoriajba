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
    
    # Tabela de usuários/colaboradores com coluna de UNIDADE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            cpf TEXT UNIQUE,
            email TEXT UNIQUE,
            senha TEXT,
            unidade TEXT DEFAULT 'JURUBATUBA'
        )
    """)
    
    # Tabela de inventários gerais com coluna de UNIDADE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventarios (
            id TEXT PRIMARY KEY,
            nome TEXT,
            data TEXT,
            status TEXT,
            unidade TEXT DEFAULT 'JURUBATUBA'
        )
    """)
    
    # Tabela de inventários do Supervisor com coluna de UNIDADE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventarios_supervisor (
            id TEXT PRIMARY KEY,
            nome TEXT,
            data TEXT,
            status TEXT,
            unidade TEXT DEFAULT 'JURUBATUBA'
        )
    """)
    
    # Tabela de contagens dos funcionários com coluna de UNIDADE
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

    # Tabela de Auditorias do Supervisor com coluna de UNIDADE
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
        "usuarios": ["unidade TEXT DEFAULT 'JURUBATUBA'"],
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

    # Criar administrador padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO usuarios (nome, cpf, email, senha, unidade) 
            VALUES (?, ?, ?, ?, ?)
        """, ("Administrador Tel", "00000000000", "admin@tel.com.br", "123", "JURUBATUBA"))
        
    conn.commit()
    conn.close()

inicializar_banco()

# --- CARREGAMENTO SEGURO DOS INVENTÁRIOS FILTRADOS POR UNIDADE ---
if 'unidade_selecionada' not in st.session_state:
    st.session_state.unidade_selecionada = "JURUBATUBA"

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
    .pasta-secao {
        background-color: #f4f6f7;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2980b9;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- GERENCIAMENTO DE ESTADO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'base_sistema' not in st.session_state:
    st.session_state.base_sistema = None
if 'base_supervisor' not in st.session_state:
    st.session_state.base_supervisor = None
if 'nome_arquivo_excel' not in st.session_state:
    st.session_state.nome_arquivo_excel = ""
if 'nome_arquivo_supervisor' not in st.session_state:
    st.session_state.nome_arquivo_supervisor = ""
if 'operador' not in st.session_state:
    st.session_state.operador = ""
if 'tela_acesso' not in st.session_state:
    st.session_state.tela_acesso = "login"

if 'contador_reset' not in st.session_state:
    st.session_state.contador_reset = 0
if 'contador_reset_sup' not in st.session_state:
    st.session_state.contador_reset_sup = 0
if 'ultimo_item_sucesso' not in st.session_state:
    st.session_state.ultimo_item_sucesso = ""

if 'pagina_historico' not in st.session_state:
    st.session_state.pagina_historico = 0
if 'pagina_historico_sup' not in st.session_state:
    st.session_state.pagina_historico_sup = 0

def limpar_documento(doc):
    return str(doc).strip().replace(".", "").replace("-", "").replace("/", "")

# --- CAPTURA DE PARÂMETROS DE URL ---
query_params = st.query_params

if "recuperar" in query_params and "token" in query_params:
    st.title("🔑 Redefinição de Senha Seguro JBA")
    try:
        email_token = base64.b64decode(query_params["token"]).decode('utf-8')
    except:
        email_token = ""

    if not email_token:
        st.error("❌ Link inválido ou corrompido.")
    else:
        st.info(f"Alterando a senha da conta vinculada ao e-mail: **{email_token}**")
        _, col_senha_center, _ = st.columns([2, 4, 2])
        with col_senha_center:
            with st.form("form_nova_senha_janela"):
                nova_senha_f = st.text_input("Digite a Nova Senha", type="password")
                confirma_senha_f = st.text_input("Confirme a Nova Senha", type="password")
                
                if st.form_submit_button("Confirmar e Atualizar Senha", type="primary", use_container_width=True):
                    if not nova_senha_f:
                        st.error("⚠️ Digite uma senha válida.")
                    elif nova_senha_f != confirma_senha_f:
                        st.error("❌ As senhas digitadas não conferem.")
                    else:
                        conn = conectar_banco()
                        cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET senha = ? WHERE email = ?", (nova_senha_f, email_token))
                        conn.commit()
                        conn.close()
                        st.success("🎉 Senha updated com sucesso! Pode fazer o login na tela principal.")
    st.stop()

# --- TELA DE ACESSO CENTRALIZADA E COMPACTA ---
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
                    cursor.execute("SELECT nome, unidade FROM usuarios WHERE (email = ? OR cpf = ?) AND senha = ? AND unidade = ?", (id_limpo, doc_limpo, senha, unidade_login))
                    user = cursor.fetchone()
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.operador = user[0]
                        st.session_state.unidade_selecionada = user[1]
                        st.rerun()
                    else:
                        st.error("❌ Credenciais incorretas ou não cadastradas nesta unidade!")
                        
            c_cad, c_rec = st.columns(2)
            with c_cad:
                if st.button("📝 Criar nova conta", use_container_width=True):
                    st.session_state.tela_acesso = "cadastro"
                    st.rerun()
            with c_rec:
                if st.button("🔑 Alterar Senha", use_container_width=True):
                    st.session_state.tela_acesso = "recuperar"
                    st.rerun()
                    
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
                            st.error("❌ Erro de Cadastro: Este CPF ou E-mail já possui conta ativa no sistema!")
                            token_cripto = base64.b64encode(email_l.encode('utf-8')).decode('utf-8')
                            link_direto_cadastro = f"https://auditoriajba.streamlit.app/?recuperar=true&token={token_cripto}"
                            
                            st.markdown(f"""
                                <div class="bloco-info-link" style="margin-top: 5px;">
                                    <p style="margin:0; color:#c0392b; font-weight:bold; font-size:14px;">🔄 Deseja alterar a senha desta conta existente?</p>
                                    <a href="{link_direto_cadastro}" target="_blank" style="text-decoration:none;">
                                        <button style="background-color:#e74c3c; color:white; border:none; padding:8px 15px; border-radius:4px; font-weight:bold; cursor:pointer; width:100%;">
                                            🔗 Gerar Nova Senha Agora
                                        </button>
                                    </a>
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            try:
                                cursor.execute("INSERT INTO usuarios (nome, cpf, email, senha, unidade) VALUES (?, ?, ?, ?, ?)", (novo_nome.strip(), cpf_l, email_l, nova_senha, unity_cadastro := unity_cadastro if 'unity_cadastro' in locals() else unidade_cadastro))
                                conn.commit()
                                st.success("✅ Cadastrado com sucesso!")
                                st.session_state.tela_acesso = "login"
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro operacional: {e}")
                                
            if st.button("◀ Voltar"):
                st.session_state.tela_acesso = "login"
                st.rerun()
                
        elif st.session_state.tela_acesso == "recuperar":
            st.markdown("<h2 style='text-align: center; border-bottom: none;'>🔑 Recuperação de Senha</h2>", unsafe_allow_html=True)
            with st.form("rec_form"):
                validador = st.text_input("Informe o seu E-mail cadastrado")
                btn_rec = st.form_submit_button("Gerar Link de Alteração de Senha", type="primary", use_container_width=True)
                
                if btn_rec:
                    v_limpo = validador.strip()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, email FROM usuarios WHERE email = ?", (v_limpo,))
                    row = cursor.fetchone()
                    
                    if row:
                        token_cripto = base64.b64encode(row[1].encode('utf-8')).decode('utf-8')
                        link_final = f"https://auditoriajba.streamlit.app/?recuperar=true&token={token_cripto}"
                        
                        st.markdown(f"""
                            <div class="bloco-info-link">
                                <p style="margin:0; color:#b7950b; font-weight:bold; font-size:15px;">📧 Link Gerado!</p>
                                <a href="{link_final}" target="_blank" style="text-decoration:none;">
                                    <button style="background-color:#e74c3c; color:white; border:none; padding:10px 20px; border-radius:4px; font-weight:bold; cursor:pointer; width:100%;">
                                        🔗 Abrir Janela de Nova Senha
                                    </button>
                                </a>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("❌ E-mail não localizado no banco de dados.")
                        
            if st.button("◀ Voltar para Tela de Login"):
                st.session_state.tela_acesso = "login"
                st.rerun()
    conn.close()

# --- TELA LOGADA DO SISTEMA ---
else:
    conn = conectar_banco()
    
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios WHERE unidade = ? ORDER BY data DESC, id DESC", conn, params=(st.session_state.unidade_selecionada,))
    df_inventarios_sup = pd.read_sql_query("SELECT * FROM inventarios_supervisor WHERE unidade = ? ORDER BY data DESC, id DESC", conn, params=(st.session_state.unidade_selecionada,))
    
    nome_usuario_logado_limpo = st.session_state.operador.lower()
    
    # --- CRITÉRIO REVISADO DE SUPERVISÃO POR PALAVRA-CHAVE OU USUÁRIO MASTER ---
    eh_supervisor = "supervisor" in nome_usuario_logado_limpo or "admin" in nome_usuario_logado_limpo or "yago rodrigues" in nome_usuario_logado_limpo
    eh_yago_master = "yago rodrigues" in nome_usuario_logado_limpo or "administrador tel" in nome_usuario_logado_limpo
    
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
        st.subheader(f"🏢 Unidade: {st.session_state.unidade_selecionada}")
        st.write(f"👤 **Operador:** {st.session_state.operador}")
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

        with st.expander("➕ Novo Inventário", expanded=df_inventarios.empty):
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

    # Determinar abas disponíveis
    lista_abas = ["🔍 Contar Item", "📊 Contagem Atual", "🔬 Painel Supervisor", "📈 Acuracidade Estoque", "📁 Histórico Geral", "📄 Base de Estoque", "🏆 Desempenho e Prazos"]
    
    # Exclusividade da aba de gestão apenas para você (Acesso Master Soberano)
    if eh_yago_master:
        lista_abas.append("⚙️ Gestão de Usuários")
        
    abas_render = st.tabs(lista_abas)
    
    # --- ABA 1: CONTAR ITEM ---
    with abas_render[0]:
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
                    st.session_state.contador_reset += 1
                    st.rerun()
                    
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
                                st.session_state.contador_reset += 1
                                st.rerun()
                else:
                    st.error("❌ Código não localizado.")

    # --- ABA 2: CONTAGEM ATUAL ---
    with abas_render[1]:
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

    # --- ABA 3: PAINEL SUPERVISOR ---
    with abas_render[2]:
        st.title("🔬 Controle de Qualidade Amostral do Supervisor")
        if not eh_supervisor:
            st.error("🚫 Acesso restrito aos supervisores.")
        else:
            st.subheader("📁 Controle de Inventários do Supervisor")
            if df_inventarios_sup.empty:
                st.info("Nenhum inventário aberto.")
                id_inv_sup_atual = None
                inv_sup_selecionado_obj = None
            else:
                lista_inv_sup = [f"{r['id']} – {r['nome']} ({r['status']})" for idx, r in df_inventarios_sup.iterrows()]
                inv_sup_selected = st.selectbox("Selecione a sua Auditoria Amostral", lista_inv_sup, key="sel_box_sup_local_v3")
                id_inv_sup_atual = inv_sup_selected.split(" – ")[0]
                inv_sup_selecionado_obj = df_inventarios_sup[df_inventarios_sup['id'] == id_inv_sup_atual].iloc[0]
            
            with st.popover("➕ Novo Inventário Supervisor", use_container_width=True):
                with st.form("form_novo_sup", clear_on_submit=True):
                    nome_sup_inv = st.text_input("Nome da Auditoria Amostral")
                    if st.form_submit_button("Criar", type="primary") and nome_sup_inv:
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM inventarios_supervisor ORDER BY ROWID DESC LIMIT 1")
                        last_sup_row = cursor.fetchone()
                        maior_id_sup = int(last_sup_row[0].replace('SUP-#','')) if last_sup_row else 0
                        
                        novo_id_sup = f"SUP-#{maior_id_sup + 1}"
                        hoje_sup = datetime.date.today().strftime("%Y-%m-%d")
                        cursor.execute("INSERT INTO inventarios_supervisor (id, nome, data, status, unidade) VALUES (?, ?, ?, 'Aberto', ?)", (novo_id_sup, nome_sup_inv, hoje_sup, st.session_state.unidade_selecionada))
                        conn.commit()
                        st.rerun()
                            
            if inv_sup_selecionado_obj is not None and inv_sup_selecionado_obj['status'] == "Aberto":
                if st.button("🔒 Fechar Amostragem", type="primary"):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE inventarios_supervisor SET status = 'Fechado' WHERE id = ? AND unidade = ?", (id_inv_sup_atual, st.session_state.unidade_selecionada))
                    conn.commit()
                    st.rerun()

            st.markdown("---")
            st.subheader("📤 Upload da Planilha de Amostragem do Supervisor")
            arquivo_supervisor = st.file_uploader("Suba a planilha Excel (.xlsx)", type=["xlsx"], key="sup_excel_loader")
            
            if arquivo_supervisor is not None:
                try:
                    df_temp_check = pd.read_excel(arquivo_supervisor)
                    colunas_norm = [str(c).strip().lower().replace("º", "").replace("ó", "o") for c in df_temp_check.columns]
                    tem_ativo = any(x in colunas_norm for x in ['ativo', 'n ativo', 'numero ativo', 'cod ativo'])
                    if not tem_ativo:
                        st.error("❌ Erro: Coluna 'Ativo' obrigatória ausente!")
                    elif df_temp_check.iloc[:, [i for i, c in enumerate(colunas_norm) if c in ['ativo', 'n ativo', 'numero ativo', 'cod ativo']][0]].isnull().any():
                        st.error("⚠️ Erro: Existem ativos em branco.")
                    else:
                        st.session_state.base_supervisor = df_temp_check
                except Exception as e:
                    st.error(f"Erro: {e}")

            df_auditorias_atual = pd.read_sql_query("SELECT * FROM auditorias_supervisor WHERE inventario_id = ? AND unidade = ?", conn, params=(id_inv_sup_atual, st.session_state.unidade_selecionada)) if id_inv_sup_atual else pd.DataFrame()
            st.write("### Relatório Amostral")
            st.dataframe(df_auditorias_atual.drop(columns=['unidade'], errors='ignore'), use_container_width=True)

    # --- ABA 4: ACURACIDADE ESTOQUE ---
    with abas_render[3]:
        st.title("📈 Acuracidade - Controle Amostral")
        df_todas_auditorias_banco = pd.read_sql_query("SELECT * FROM auditorias_supervisor WHERE unidade = ?", conn, params=(st.session_state.unidade_selecionada,))
        st.dataframe(df_todas_auditorias_banco, use_container_width=True)

    # --- ABA 5: HISTÓRICO GERAL ---
    with abas_render[4]:
        st.title("📁 Arquivo Geral de Movimentações")
        c_dt1, c_dt2 = st.columns(2)
        with c_dt1: data_inicio_filtro = st.date_input("Data Inicial", datetime.date.today() - datetime.timedelta(days=90))
        with c_dt2: data_fim_filtro = st.date_input("Data Final", datetime.date.today() + datetime.timedelta(days=1))
        
        df_inventarios['datetime_parsed'] = pd.to_datetime(df_inventarios['data'], errors='coerce').dt.date
        df_filtrados = df_inventarios[(df_inventarios['datetime_parsed'] >= data_inicio_filtro) & (df_inventarios['datetime_parsed'] <= data_fim_filtro) & (df_inventarios['unidade'] == st.session_state.unidade_selecionada)]
        st.write(f"Total de pastas nesta unidade: {len(df_filtrados)}")

    # --- ABA 6: BASE DE ESTOQUE ---
    with abas_render[5]:
        if st.session_state.base_sistema is not None:
            st.subheader("📄 Espelho Base de Saldo")
            st.dataframe(st.session_state.base_sistema, use_container_width=True)

    # --- ABA 7: DESEMPENHO E PRAZOS ---
    with abas_render[6]:
        st.title("🏆 Desempenho e Prazos por Estoque")
        
        lista_estoques_fixa = [
            {"id": "1077", "desc": "JBA - CLASSE D"}, {"id": "1078", "desc": "JBA - COPA E COZINHA"},
            {"id": "1080", "desc": "JBA - DADOS - CLIENTE"}, {"id": "1082", "desc": "JBA - VIVO VITA - CLIENTE"},
            {"id": "1084", "desc": "JBA - EPI-EPC"}, {"id": "1086", "desc": "JBA - EQUIPAMENTOS"},
            {"id": "1088", "desc": "JBA - FERRAMENTAL"}, {"id": "1089", "desc": "JBA - KIT FERRAMENTAL CONTRATACOES"},
            {"id": "1090", "desc": "JBA - FERRAMENTAS DE CANTEIRO"}, {"id": "1102", "desc": "1385 - LA JBA - CLIENTE"},
            {"id": "1104", "desc": "JBA - MATERIAL DE ESCRITORIO - SUPRIMENTOS DE INFORMATICA"}, {"id": "1106", "desc": "JBA - MOBILIARIO"},
            {"id": "1108", "desc": "1071 - EXEC SEGREGADO IMPLANTACAO JBA - CLIENTE"}, {"id": "1113", "desc": "1385 - MANUTENCAO JBA - CLIENTE"},
            {"id": "1118", "desc": "JBA - PROPRIO GERAL"}, {"id": "1122", "desc": "JBA - GRANDES OBRAS IMPLANTACAO"},
            {"id": "1124", "desc": "JBA - PROPRIO TIM"}, {"id": "1140", "desc": "JBA - SPEEDY/FTTX - CLIENTE"},
            {"id": "1144", "desc": "1385 - MANUTENCAO JBA CLIENTE RESERVADO"}, {"id": "1149", "desc": "JBA - UNIFORME"},
            {"id": "2149", "desc": "JBA - SPEEDY/FTTX DEVOLUCAO NOVO COM DEFEITO - CLIENTE"}, {"id": "2183", "desc": "1071 - BOL IMPLANTANCAO JBA - CLIENTE"},
            {"id": "2185", "desc": "JBA - PROPRIO FATURA B PLANTA EXTERNA - BDI"}, {"id": "2188", "desc": "1071 - IMPLANTACAO JBA CLIENTE RESERVADO"},
            {"id": "2189", "desc": "JBA - DEFEITO"}, {"id": "2190", "desc": "JBA - DEPARTAMENTO T.I"},
            {"id": "2194", "desc": "JBA - KITS FERRAMENTAL - DEVOLUCAO"}, {"id": "2197", "desc": "JBA - EQUIPAMENTOS TI"},
            {"id": "2641", "desc": "1259 - IMPLANTACAO JBA - MATERIAL REUTILIZACAO"}, {"id": "2643", "desc": "1724 - MANUTENCAO JBA - MATERIAL REUTILIZACAO"},
            {"id": "2725", "desc": "JBA - RESERVA TIM"}, {"id": "2983", "desc": "JBA - FORNECEDORES P/ MANUTENCAO - RECARGA"},
            {"id": "3193", "desc": "JBA - PROPRIO MATERIAL REAPROVEITAVEL"}, {"id": "3395", "desc": "LPA - FTTX - CLIENTE"},
            {"id": "3484", "desc": "JBA - CELULARES DEFEITO"}, {"id": "3546", "desc": "JBA - CELULARES"}
        ]
        
        df_ultimas_contagens = pd.read_sql_query("""
            SELECT id_estoque, MAX(data_hora) as ultima_data 
            FROM contagens 
            WHERE unidade = ? 
            GROUP BY id_estoque
        """, conn, params=(st.session_state.unidade_selecionada,))
        
        mapa_datas = dict(zip(df_ultimas_contagens['id_estoque'].astype(str).str.strip(), df_ultimas_contagens['ultima_data']))
        hoje_dt = datetime.datetime.now()
        linhas_planilha_desempenho = []
        bom_count, auditar_count, criticos_count = 0, 0, 0
        
        for est in lista_estoques_fixa:
            est_id = est["id"]
            est_desc = est["desc"]
            ultima_data_str = mapa_datas.get(est_id, None)
            
            if ultima_data_str:
                try:
                    dt_contagem = datetime.datetime.strptime(ultima_data_str, "%Y-%m-%d %H:%M:%S")
                    dias_passados = (hoje_dt - dt_contagem).days
                    data_formatada = dt_contagem.strftime("%d/%m/%Y %H:%M")
                except:
                    dias_passados = 999
                    data_formatada = "Sem Histórico Válido"
            else:
                dias_passados = 999
                data_formatada = "Nunca Contabilizado"
                
            if dias_passados <= 7:
                status_final = "🟢 Bom"
                bom_count += 1
            elif dias_passados <= 14:
                status_final = "🟡 Precisa contar"
                auditar_count += 1
            else:
                status_final = "🔴 Crítico"
                criticos_count += 1
                
            linhas_planilha_desempenho.append({
                "Id. Estoque Físico": est_id,
                "Descrição do Estoque Físico": est_desc,
                "Última Contagem Lançada": data_formatada,
                "Dias sem Contabilizar": dias_passados if dias_passados != 999 else "—",
                "Status": status_final
            })
            
        df_desempenho_final = pd.DataFrame(linhas_planilha_desempenho)
        k1, k2, k3 = st.columns(3)
        with k1: st.markdown(f'<div class="bloco-info" style="border-left: 5px solid #2ecc71;"><div class="bloco-titulo">🟢 EM DIA (BOM)</div><div class="bloco-valor" style="color: #27ae60;">{bom_count}</div></div>', unsafe_allow_html=True)
        with k2: st.markdown(f'<div class="bloco-info" style="border-left: 5px solid #f1c40f;"><div class="bloco-titulo">🟡 PRECISA CONTAR</div><div class="bloco-valor" style="color: #f39c12;">{auditar_count}</div></div>', unsafe_allow_html=True)
        with k3: st.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:10px; border-left: 5px solid #e74c3c;"><div class="bloco-titulo">🔴 CRÍTICO (+2 SEMANAS)</div><div class="bloco-valor" style="color: #c0392b;">{criticos_count}</div></div>', unsafe_allow_html=True)
            
        st.write("")
        st.markdown("### 📊 Planilha Temporal Automatizada de Inventários")
        st.dataframe(df_desempenho_final, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.write("### 🏆 Lançamentos Totais por Operador")
        df_ops = pd.read_sql_query("SELECT operador as Operador, COUNT(id) as [Lançamentos Feitos] FROM contagens WHERE unidade = ? GROUP BY operador", conn, params=(st.session_state.unidade_selecionada,))
        if not df_ops.empty:
            st.bar_chart(data=df_ops, x='Operador', y='Lançamentos Feitos', color="#d35400")

    # --- ABA EXCLUSIVA PERMISSÃO MASTER SOBERANO: GESTÃO DE LOGINS (REVISADA) ---
    if eh_yago_master:
        with abas_render[7]:
            st.title("⚙️ Painel de Controle e Gestão de Usuários")
            df_usuarios_all = pd.read_sql_query("SELECT id, nome, cpf, email, senha, unidade FROM usuarios ORDER BY unidade, nome", conn)
            st.dataframe(df_usuarios_all, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.write("### 🛠️ Alterar Dados e Permissões")
            with st.form("form_edit_user"):
                usuario_alvo_id = st.selectbox("Escolha o usuário para alterar", df_usuarios_all['id'].tolist(), format_func=lambda x: f"ID {x} - {df_usuarios_all[df_usuarios_all['id']==x]['nome'].values[0]} ({df_usuarios_all[df_usuarios_all['id']==x]['unidade'].values[0]})")
                u_row = df_usuarios_all[df_usuarios_all['id'] == usuario_alvo_id].iloc[0]
                novo_nome_user = st.text_input("Nome Completo", value=u_row['nome'])
                nova_senha_user = st.text_input("Nova Senha de Acesso", value=u_row['senha'])
                nova_unid_user = st.selectbox("Mudar Unidade / Localidade", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"], index=["JURUBATUBA", "JUNDIAI", "CUBATÃO"].index(u_row['unidade']))
                
                if st.form_submit_button("💾 Salvar Alterações Definitivas", type="primary"):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE usuarios SET nome = ?, senha = ?, unidade = ? WHERE id = ?", (novo_nome_user.strip(), nova_senha_user.strip(), nova_unid_user, usuario_alvo_id))
                    conn.commit()
                    st.success("✅ Usuário atualizado com sucesso no banco de dados!")
                    st.rerun()
                    
    conn.close()
