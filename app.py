import streamlit as st
import pandas as pd
import datetime
import sqlite3
import io
import base64
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico - JBA", layout="wide")

# --- BANCO DE DADOS PERMANENTE E FIXO (SQLITE) ---
def conectar_banco():
    caminho_banco = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'banco_inventario.db') if '__file__' in locals() else 'banco_inventario.db'
    conn = sqlite3.connect(caminho_banco, check_same_thread=False)
    return conn

def inicializar_banco():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Tabela de usuários/colaboradores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            cpf TEXT UNIQUE,
            email TEXT UNIQUE,
            senha TEXT
        )
    """)
    
    # Tabela de inventários gerais (funcionários)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventarios (
            id TEXT PRIMARY KEY,
            nome TEXT,
            data TEXT,
            status TEXT
        )
    """)
    
    # Tabela de backup persistente para os itens carregados de cada inventário
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_base_inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventario_id TEXT,
            cod_produto TEXT,
            desc_produto TEXT,
            desc_estoque_fisico TEXT,
            unid_medida TEXT,
            qtd_estoque INTEGER,
            id_estoque_fisico TEXT,
            lote TEXT DEFAULT ''
        )
    """)
    
    # Tabela de inventários exclusivos do Supervisor
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventarios_supervisor (
            id TEXT PRIMARY KEY,
            nome TEXT,
            data TEXT,
            status TEXT
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
            fase_contagem TEXT DEFAULT '1a Contagem'
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
            ativo TEXT
        )
    """)
    
    # --- MIGRACAO AUTOMATICA ---
    try:
        cursor.execute("PRAGMA table_info(contagens)")
        colunas_existentes = [coluna[1] for coluna in cursor.fetchall()]
        if 'lote' not in colunas_existentes:
            cursor.execute("ALTER TABLE contagens ADD COLUMN lote TEXT DEFAULT ''")
        if 'fase_contagem' not in colunas_existentes:
            cursor.execute("ALTER TABLE contagens ADD COLUMN fase_contagem TEXT DEFAULT '1a Contagem'")
        conn.commit()
    except Exception as e:
        pass

    # Criar administrador padrão
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO usuarios (nome, cpf, email, senha) 
            VALUES (?, ?, ?, ?)
        """, ("Administrador Tel", "00000000000", "admin@tel.com.br", "123"))
        
    conn.commit()
    conn.close()

inicializar_banco()

# --- CARREGAMENTO SEGURO DOS INVENTÁRIOS ---
conn_init = conectar_banco()
try:
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios ORDER BY data DESC, id DESC", conn_init)
except:
    df_inventarios = pd.DataFrame(columns=['id', 'nome', 'data', 'status'])

try:
    df_inventarios_sup = pd.read_sql_query("SELECT * FROM inventarios_supervisor ORDER BY data DESC, id DESC", conn_init)
except:
    df_inventarios_sup = pd.DataFrame(columns=['id', 'nome', 'data', 'status'])
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

# Estados de paginação independentes
if 'pagina_historico' not in st.session_state:
    st.session_state.pagina_historico = 0
if 'pagina_historico_sup' not in st.session_state:
    st.session_state.pagina_historico_sup = 0

def limpar_documento(doc):
    return str(doc).strip().replace(".", "").replace("-", "").replace("/", "")

# --- RECOVERY URL PARAMETERS ---
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
                    st.success("🎉 Senha atualizada com sucesso! Pode fazer o login na tela principal.")
    st.stop()

# --- TELA DE ACESSO ---
if not st.session_state.logged_in:
    conn = conectar_banco()
    if st.session_state.tela_acesso == "login":
        st.title("🔒 Acesso ao Sistema de Estoque JBA")
        with st.form("login_form"):
            identificador = st.text_input("CPF (somente números) ou E-mail")
            senha = st.text_input("Senha", type="password")
            botao_login = st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True)
            if botao_login:
                id_limpo = identificador.strip()
                doc_limpo = limpar_documento(id_limpo)
                cursor = conn.cursor()
                cursor.execute("SELECT nome FROM usuarios WHERE (email = ? OR cpf = ?) AND senha = ?", (id_limpo, doc_limpo, senha))
                user = cursor.fetchone()
                if user:
                    st.session_state.logged_in = True
                    st.session_state.operador = user[0]
                    st.rerun()
                else:
                    st.error("❌ Credenciais incorretas.")
        c_cad, c_rec = st.columns(2)
        with c_cad:
            if st.button("📝 Criar nova conta", use_container_width=True):
                st.session_state.tela_acesso = "cadastro"
                st.rerun()
        with c_rec:
            if st.button("🔑 Recuperar/Alterar Senha", use_container_width=True):
                st.session_state.tela_acesso = "recuperar"
                st.rerun()
    elif st.session_state.tela_acesso == "cadastro":
        st.title("📝 Cadastro de Colaborador")
        with st.form("cadastro_form"):
            novo_nome = st.text_input("Nome Completo")
            novo_cpf = st.text_input("CPF (Apenas números)")
            novo_email = st.text_input("E-mail")
            nova_senha = st.text_input("Senha", type="password")
            confirma_senha = st.text_input("Confirme a Senha", type="password")
            btn_cad = st.form_submit_button("Finalizar Cadastro", type="primary", use_container_width=True)
            if btn_cad:
                cpf_l = limpar_documento(novo_cpf)
                if not novo_nome or not cpf_l or not novo_email or not nova_senha:
                    st.error("⚠️ Preencha todos os campos!")
                elif nova_senha != confirma_senha:
                    st.error("❌ As senhas não batem!")
                else:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO usuarios (nome, cpf, email, senha) VALUES (?, ?, ?, ?)", (novo_nome.strip(), cpf_l, novo_email.strip(), nova_senha))
                        conn.commit()
                        st.success("✅ Cadastrado com sucesso!")
                        st.session_state.tela_acesso = "login"
                        st.rerun()
                    except:
                        st.error("❌ CPF ou E-mail já existente.")
        if st.button("◀ Voltar"):
            st.session_state.tela_acesso = "login"
            st.rerun()
    elif st.session_state.tela_acesso == "recuperar":
        st.title("🔑 Solicitação de Link de Redefinição")
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
                            <p style="margin:0; color:#b7950b; font-weight:bold; font-size:15px;">📧 Link de Segurança Gerado com Sucesso!</p>
                            <p style="margin:5px 0 15px 0; color:#7d6608; font-size:13px;">Clique no botão vermelho abaixo para abrir a nova janela de redefinição de senha.</p>
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
    
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios ORDER BY data DESC, id DESC", conn)
    df_inventarios_sup = pd.read_sql_query("SELECT * FROM inventarios_supervisor ORDER BY data DESC, id DESC", conn)
    
    st.session_state.operador = st.session_state.get('operador', 'Operador Genérico')
    nome_usuario_logado_limpo = st.session_state.operador.lower()
    eh_supervisor = any(x in nome_usuario_logado_limpo for x in ["yago rodrigues", "administrador", "admin", "supervisor"])
    
    id_inventario_atual_inicial = df_inventarios.iloc[0]['id'].replace('#','') if not df_inventarios.empty else ""

    # SIDEBAR
    with st.sidebar:
        st.write(f"👤 **Operador Ativo:** {st.session_state.operador}")
        
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.rerun()
            
        if st.button("🚪 Sair da Conta", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.operador = ""
            st.session_state.tela_acesso = "login"
            st.rerun()
            
        st.markdown("---")
        with st.expander("➕ Novo Inventário", expanded=df_inventarios.empty):
            with st.form("form_novo", clear_on_submit=True):
                novo_nome = st.text_input("Nome do Inventário")
                if st.form_submit_button("Criar", type="primary") and novo_nome:
                    if not df_inventarios.empty:
                        df_limpo_calc = df_inventarios['id'].str.replace('#', '', regex=False).astype(int)
                        maior_id = df_limpo_calc.max()
                    else:
                        maior_id = 38
                    novo_id = f"#{maior_id + 1}"
                    hoje = datetime.date.today().strftime("%Y-%m-%d")
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO inventarios (id, nome, data, status) VALUES (?, ?, ?, 'Aberto')", (novo_id, novo_nome, hoje))
                    conn.commit()
                    st.rerun()

        st.write("📁 **Selecione o inventário**")
        if df_inventarios.empty:
            st.info("Crie um inventário abaixo.")
            id_inventario_atual = None
            inventario_selected_obj = None
        else:
            lista_inv = [f"{row['id']} – {row['nome']} ({row['status']})" for idx, row in df_inventarios.iterrows()]
            inventario_selected = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
            id_inventario_atual = " – " in inventario_selected and inventario_selected.split(" – ")[0] or None
            inventario_selected_obj = df_inventarios[df_inventarios['id'] == id_inventario_atual].iloc[0]

        # RECONSTRUÇÃO DA BASE DE SALDO PERSISTENTE VINCULADA AO BANCO DE DADOS E À PASTA ATUAL
        if id_inventario_atual:
            id_pasta_limpo_base = id_inventario_atual.replace("#", "")
            df_base_persistida = pd.read_sql_query("SELECT cod_produto, desc_produto, desc_estoque_fisico, unid_medida, qtd_estoque, id_estoque_fisico, lote FROM itens_base_inventario WHERE inventario_id = ?", conn, params=(id_pasta_limpo_base,))
            if not df_base_persistida.empty:
                st.session_state.base_sistema = df_base_persistida.rename(columns={
                    'desc_estoque_fisico': 'descestoquefisico',
                    'id_estoque_fisico': 'idestoquefísico'
                })
            else:
                st.session_state.base_sistema = None

        st.write("📂 **Carregar Base de Dados (Funcionários)**")
        arquivo_excel = st.file_uploader("Suba o arquivo Excel (.xlsx)", type=["xlsx"], label_visibility="collapsed", key="func_excel_loader")
        if arquivo_excel is not None and id_inventario_atual:
            df_upload_temp = pd.read_excel(arquivo_excel)
            colunas_temp = list(df_upload_temp.columns)
            
            def mapear_col(opcoes, default_idx):
                for opcao in opcoes:
                    for col in colunas_temp:
                        if opcao.lower().replace(" ", "").replace(".", "") in col.lower().replace(" ", "").replace(".", ""):
                            return col
                return colunas_temp[default_idx] if default_idx < len(colunas_temp) else colunas_temp[0]

            c_cod_u = mapear_col(['códproduto', 'codproduto', 'codigo', 'cod'], 0)
            c_desc_u = mapear_col(['descproduto', 'descricao', 'desc'], 1)
            c_local_u = mapear_col(['descestoquefisico', 'localizacao', 'local', 'estoquefisico'], 2)
            c_unid_u = mapear_col(['unidmedida', 'unidade', 'un'], 3)
            c_qtd_u = mapear_col(['qtdestoque', 'quantidade', 'saldo', 'qtd'], -1)
            c_id_est_u = mapear_col(['idestoquefísico', 'idestoqfísico', 'idestoque', 'codestoque'], 0)
            
            c_lote_u = None
            for col_l in df_upload_temp.columns:
                if str(col_l).strip().upper() == "LOTE":
                    c_lote_u = col_l
                    break

            cursor_db = conn.cursor()
            cursor_db.execute("DELETE FROM itens_base_inventario WHERE inventario_id = ?", (id_pasta_limpo_base,))
            
            for _, r in df_upload_temp.iterrows():
                lote_item_v = str(r[c_lote_u]).strip() if c_lote_u and pd.notna(r[c_lote_u]) else ""
                cursor_db.execute("""
                    INSERT INTO itens_base_inventario (inventario_id, cod_produto, desc_produto, desc_estoque_fisico, unid_medida, qtd_estoque, id_estoque_fisico, lote)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (id_pasta_limpo_base, str(r[c_cod_u]).strip(), str(r[c_desc_u]), str(r[c_local_u]), str(r[c_unid_u]), int(pd.to_numeric(r[c_qtd_u], errors='coerce') or 0), str(r[c_id_est_u]).strip(), lote_item_v))
            conn.commit()
            st.rerun()

        col_cod, col_desc, col_local, col_unidade, col_qtd, col_id_estoque = "cod_produto", "desc_produto", "descestoquefisico", "unid_medida", "qtd_estoque", "idestoquefísico"

        # TRAVA DE FECHAMENTO ADAPTADA
        if inventario_selected_obj is not None and inventario_selected_obj['status'] in ["Aberto", "2a Contagem"]:
            id_pasta_limpo = id_inventario_atual.replace('#', '')
            pode_fechar = False
            itens_esquecidos_lista = []

            if st.session_state.base_sistema is not None:
                if inventario_selected_obj['status'] == "Aberto":
                    df_c_verif = pd.read_sql_query("SELECT cod_produto FROM contagens WHERE inventario_id = ?", conn, params=(id_pasta_limpo,))
                    lista_contados_set = set(df_c_verif['cod_produto'].astype(str).str.upper().str.strip().tolist())
                    for idx, r_base in st.session_state.base_sistema.iterrows():
                        cod_b = str(r_base['cod_produto']).upper().strip()
                        if cod_b not in lista_contados_set:
                            itens_esquecidos_lista.append(cod_b)
                    if len(itens_esquecidos_lista) == 0:
                        pode_fechar = True
                else:
                    df_recontados = pd.read_sql_query("SELECT cod_produto FROM contagens WHERE inventario_id = ? AND fase_contagem = '2a Contagem' AND qtd_contada > 0", conn, params=(id_pasta_limpo,))
                    set_recontados = set(df_recontados['cod_produto'].astype(str).str.upper().str.strip().tolist())
                    
                    df_alvos_divergentes = pd.read_sql_query("SELECT cod_produto FROM contagens WHERE inventario_id = ? AND fase_contagem = '2a Contagem'", conn, params=(id_pasta_limpo,))
                    set_alvos = set(df_alvos_divergentes['cod_produto'].astype(str).str.upper().str.strip().tolist())
                    
                    itens_faltantes_recontar = set_alvos - set_recontados
                    if len(itens_faltantes_recontar) == 0:
                        pode_fechar = True
                    else:
                        itens_esquecidos_lista = list(itens_faltantes_recontar)

            if pode_fechar:
                if st.button("🔒 Fechar Inventário e Finalizar", use_container_width=True):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE inventarios SET status = 'Fechado' WHERE id = ?", (id_inventario_atual,))
                    conn.commit()
                    st.rerun()
            else:
                st.error(f"❌ Fechamento Bloqueado: Faltam {len(itens_esquecidos_lista)} materiais na lista.")
                if eh_supervisor:
                    st.warning("👤 Yago Rodrigues detectado. Deseja forçar o encerramento?")
                    if st.button("⚠️ Forçar Fechamento Incompleto (ADMIN)", use_container_width=True, type="primary"):
                        cursor = conn.cursor()
                        cursor.execute("UPDATE inventarios SET status = 'Fechado' WHERE id = ?", (id_inventario_atual,))
                        conn.commit()
                        st.rerun()

        # PROGRESSO LATERAL
        total_itens_base, total_contados, total_pendentes, progresso = 0, 0, 0, 0.0
        if st.session_state.base_sistema is not None and id_inventario_atual is not None:
            total_itens_base = len(st.session_state.base_sistema)
            if eh_supervisor:
                df_contagens_atuais_side = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ?", conn, params=(id_inventario_atual.replace('#',''),))
            else:
                df_contagens_atuais_side = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? AND operador = ?", conn, params=(id_inventario_atual.replace('#',''), st.session_state.operador))
                
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

    abas = ["🔍 Contar Item", "📊 Contagem Atual", "🔬 Painel Supervisor", "📈 Acuracidade Estoque", "📁 Histórico Geral", "📄 Base de Estoque", "🏆 Desempenho"]
    aba_contar, aba_atual, aba_supervisor, aba_acuracidade, aba_historico_geral, aba_base, aba_graficos = st.tabs(abas)
    
    # --- ABA 1: CONTAR ITEM (FUNCIONÁRIOS) ---
    with aba_contar:
        if id_inventario_atual is None or st.session_state.base_sistema is None:
            st.warning("⚠️ Carregue a base de saldo e crie um inventário na barra lateral.")
        elif id_inventario_atual and inventario_selected_obj['status'] == "Fechado":
            st.error("🔒 Inventário selecionado está Fechado.")
        else:
            c_busca, c_filtro, c_limpar = st.columns([5, 3, 2])
            with c_busca:
                codigo_input = st.text_input("💻 Código do Produto (etiqueta ou manual)", value="", placeholder="Bipe a etiqueta ou digite...", key=f"bip_{st.session_state.contador_reset}")
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
                id_pasta_limpo = id_inventario_atual.replace("#", "")
                
                # --- TRAVA AMOSTRAGEM: SE FOR 2A CONTAGEM, SÓ DEIXA BIPAR SE ESTIVER NA LISTA DE ERROS ---
                item_autorizado = True
                if inventario_selected_obj['status'] == "2a Contagem":
                    df_permitidos = pd.read_sql_query("SELECT id FROM contagens WHERE inventario_id = ? AND cod_produto = ? AND fase_contagem = '2a Contagem'", conn, params=(id_pasta_limpo, codigo_rastreio))
                    if df_permitidos.empty:
                        item_autorizado = False
                
                if not item_autorizado:
                    st.error("🚫 Bloqueado: Este material está CORRETO no sistema e não foi liberado pelo supervisor para a 2ª Contagem.")
                else:
                    itens_filtrados = st.session_state.base_sistema[st.session_state.base_sistema['cod_produto'].astype(str).str.upper().str.strip() == codigo_rastreio]
                    
                    if not itens_filtrados.empty:
                        lotes_disponiveis = itens_filtrados['lote'].dropna().astype(str).str.strip().unique().tolist()
                        lotes_disponiveis = [l for l in lotes_disponiveis if l != "" and l.lower() != "nan"]

                        col_orig_ativo = None
                        for c_col in itens_filtrados.columns:
                            if str(c_col).strip().upper() in ["ATIVO", "Nº ATIVO", "NUMERO ATIVO", "COD ATIVO"]:
                                col_orig_ativo = c_col
                                break

                        # Escolha do Lote caso existam múltiplos lotes
                        lote_selecionado = ""
                        if lotes_disponiveis:
                            st.warning("⚠️ Múltiplos lotes identificados para este item! Escolha o lote correto abaixo.")
                            lote_selecionado = st.selectbox("👇 SELECIONE O LOTE PARA CONTAGEM:", lotes_disponiveis, key="lote_selector_bip")
                            linhas_filtradas_por_lote = itens_filtrados[itens_filtrados['lote'].astype(str).str.strip() == lote_selecionado]
                        else:
                            linhas_filtradas_por_lote = itens_filtrados

                        # Extração de múltiplos ativos da seleção de lote atual
                        ativos_disponiveis = []
                        if col_orig_ativo:
                            ativos_disponiveis = linhas_filtradas_por_lote[col_orig_ativo].dropna().astype(str).str.strip().unique().tolist()
                            ativos_disponiveis = [a for a in ativos_disponiveis if a != "" and a.lower() != "nan"]

                        # --- FIX: BUSCA ATIVOS CONCLUÍDOS NO INVENTÁRIO ATUAL DE FORMA ROBUSTA ---
                        df_ativos_lancados = pd.read_sql_query("SELECT ativo FROM contagens WHERE inventario_id = ? AND cod_produto = ?", conn, params=(id_pasta_limpo, codigo_rastreio))
                        set_ativos_lancados = set(df_ativos_lancados['ativo'].dropna().astype(str).str.strip().upper().tolist())
                        
                        # Mantém na lista de seleção apenas os ativos que NÃO foram contados ainda nesta pasta
                        ativos_filtrados_restantes = [a for a in ativos_disponiveis if str(a).strip().upper() not in set_ativos_lancados]

                        # Seleção final do Ativo ativo
                        ativo_selecionado = ""
                        if len(ativos_filtrados_restantes) > 1:
                            st.info("🔢 Múltiplos números de ativos identificados para este lote. Selecione o correspondente:")
                            ativo_selecionado = st.selectbox("👇 SELECIONE O ATIVO PARA CONTAGEM:", ativos_filtrados_restantes, key="ativo_selector_bip")
                            item_especifico = linhas_filtradas_por_lote[linhas_filtradas_por_lote[col_orig_ativo].astype(str).str.strip() == ativo_selecionado].iloc[0]
                        elif len(ativos_filtrados_restantes) == 1:
                            ativo_selecionado = ativos_filtrados_restantes[0]
                            item_especifico = linhas_filtradas_por_lote[linhas_filtradas_por_lote[col_orig_ativo].astype(str).str.strip() == ativo_selecionado].iloc[0]
                        else:
                            item_especifico = linhas_filtradas_por_lote.iloc[0]
                            if col_orig_ativo and len(ativos_disponiveis) > 0:
                                st.warning("⚠️ Todos os ativos cadastrados para este produto já foram computados neste inventário!")

                        unid_val = item_especifico['unid_medida'] if 'unid_medida' in itens_filtrados.columns else "UN"
                        desc_val = item_especifico['desc_produto']
                        local_val = item_especifico['descestoquefisico'] if 'descestoquefisico' in itens_filtrados.columns else "Não Informado"
                        id_estoque_val = str(item_especifico['idestoquefísico']).strip() if 'idestoquefísico' in itens_filtrados.columns else ""
                        
                        try:
                            qtd_sys = int(item_especifico['qtd_estoque'])
                        except:
                            qtd_sys = 0
                        
                        b1, b2, b3, b4 = st.columns(4)
                        b1.markdown(f'<div class="bloco-info"><div class="bloco-titulo">CÓD. PRODUTO</div><div class="bloco-valor">{codigo_rastreio}</div></div>', unsafe_allow_html=True)
                        b2.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:0px;"><div class="bloco-titulo">ESTOQUE FÍSICO</div><div class="bloco-valor" style="font-size:22px;">{local_val}</div></div>', unsafe_allow_html=True)
                        b3.markdown(f'<div class="bloco-info"><div class="bloco-titulo">UNID. MEDIDA</div><div class="bloco-valor">{unid_val}</div></div>', unsafe_allow_html=True)
                        b4.markdown(f'<div class="bloco-info"><div class="bloco-titulo">LOTE EM CONTAGEM</div><div class="bloco-valor" style="color:#d35400;">{lote_selecionado if lote_selecionado else "Padrão"}</div></div>', unsafe_allow_html=True)
                        
                        st.markdown(f"**Descrição do Material:** {desc_val}")
                        st.info(f"📋 **Lote Selecionado:** {lote_selecionado if lote_selecionado else 'Não se aplica'} | **Ativo Selecionado:** {ativo_selecionado if ativo_selecionado else 'Padrão / Manual'}")
                        
                        with st.form("confirmar_form", clear_on_submit=True):
                            qtd_fisica = st.number_input("📦 Quantidade contada fisicamente (Obrigatório)", min_value=0, step=1, value=0)
                            
                            if len(ativos_filtrados_restantes) > 1:
                                ativo_final_input = ativo_selecionado
                            else:
                                ativo_final_input = st.text_input("🔢 Número do Ativo (Opcional)", value=ativo_selecionado)
                                
                            observacao = st.text_input("📝 Observação (opcional)")
                            
                            if st.form_submit_button("✓ Confirmar Contagem", type="primary", use_container_width=True):
                                ativo_l = str(ativo_final_input).strip().upper()
                                if qtd_fisica <= 0:
                                    st.error("❌ Erro: Informe uma quantidade maior que 0!")
                                else:
                                    agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    dif_c = qtd_fisica - qtd_sys
                                    cursor = conn.cursor()
                                    
                                    fase_atual_registro = "1a Contagem"
                                    if inventario_selected_obj['status'] == "2a Contagem":
                                        fase_atual_registro = "2a Contagem"
                                        cursor.execute("DELETE FROM contagens WHERE inventario_id = ? AND cod_produto = ? AND lote = ? AND fase_contagem = '2a Contagem'", (id_pasta_limpo, codigo_rastreio, lote_selecionado))

                                    cursor.execute("""
                                        INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, observacao, operador, data_hora, lote, fase_contagem)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (id_pasta_limpo, id_estoque_val, local_val, codigo_rastreio, desc_val, unid_val, qtd_sys, qtd_fisica, dif_c, ativo_l, observacao, st.session_state.operador, agora, lote_selecionado, fase_atual_registro))
                                    conn.commit()
                                    st.session_state.ultimo_item_sucesso = f"✅ Lançamento Efetuado com sucesso para o Lote {lote_selecionado if lote_selecionado else 'Padrão'} ({fase_atual_registro})!"
                                    st.session_state.contador_reset += 1
                                    st.rerun()
                    else:
                        st.error("❌ Código não localizado.")

    # --- ABA 2: CONTAGEM ATUAL ---
    with aba_atual:
        if id_inventario_atual:
            st.subheader(f"Painel Operacional – {id_inventario_atual} ({inventario_selected_obj['nome']})")
            
            modo_visao = "Apenas Minhas Contagens"
            if eh_supervisor:
                modo_visao = st.radio("Filtro de Visualização (Exclusivo Supervisor):", ["Apenas Minhas Contagens", "Ver Tudo (Todos os Operadores Simultâneos)"], horizontal=True)

            if modo_visao == "Apenas Minhas Contagens":
                df_contagens_mutaveis = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? AND operador = ? ORDER BY id DESC", conn, params=(id_inventario_atual.replace('#',''), st.session_state.operador))
            else:
                df_contagens_mutaveis = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? ORDER BY id DESC", conn, params=(id_inventario_atual.replace('#',''),))

            if df_contagens_mutaveis.empty:
                st.info("Nenhum item lançado nessa perspectiva até o momento.")
            else:
                total_auditado = len(df_contagens_mutaveis)
                itens_divergentes = len(df_contagens_mutaveis[df_contagens_mutaveis['diferenca'] != 0])
                st.session_state.soma_contada = int(df_contagens_mutaveis['qtd_contada'].sum())
                soma_sistema = int(df_contagens_mutaveis['qtd_sistema'].sum())
                diferenca_acumulada = int(df_contagens_mutaveis['diferenca'].sum())
                
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">📦 ITENS CONTADOS</div><div class="bloco-valor">{total_auditado}</div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">⚠️ COM DIVERGÊNCIA</div><div class="bloco-valor">{itens_divergentes}</div></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">QUANTIDADE CONTADA</div><div class="bloco-valor">{st.session_state.soma_contada}</div></div>', unsafe_allow_html=True)
                with c4: st.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:0px;"><div class="bloco-titulo">QUANTIDADE SISTEMA</div><div class="bloco-valor">{soma_sistema} <span style="font-size:14px; color:#e74c3c;">(Dif: {diferenca_acumulada})</span></div></div>', unsafe_allow_html=True)
                
                excel_atual = converter_para_excel(df_contagens_mutaveis)
                st.download_button(label="📥 Exportar Lançamentos Filtrados para Excel", data=excel_atual, file_name=f"contagem_{id_inventario_atual}_{st.session_state.operador}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                st.write("")

                colunas_existentes_contagens = list(df_contagens_mutaveis.columns)
                ordem_colunas_print = ['id', 'inventario_id', 'id_estoque', 'desc_estoque', 'cod_produto', 'desc_produto', 'unid_medida', 'qtd_sistema', 'qtd_contada', 'diferenca', 'ativo', 'observacao', 'operador', 'data_hora', 'fase_contagem']
                
                st.dataframe(df_contagens_mutaveis[ordem_colunas_print], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum inventário selecionado.")

    # --- ABA 3: PAINEL SUPERVISOR ---
    with aba_supervisor:
        st.title("🔬 Painel de Gestão e Auditoria do Supervisor")
        
        if not eh_supervisor:
            st.error("🚫 Acesso restrito. Esta tela só pode ser operada pelo Administrador/Supervisor.")
        else:
            st.subheader("🔄 Módulo ADM de Liberação de 2ª Contagem")
            df_todas_contagens_divergentes = pd.read_sql_query("SELECT * FROM contagens WHERE diferenca != 0 AND fase_contagem = '1a Contagem'", conn)
            
            if df_todas_contagens_divergentes.empty:
                st.success("🎉 Nenhuma divergência operacional pendente de tratamento nas primeiras contagens.")
            else:
                ids_inventarios_com_erro = df_todas_contagens_divergentes['inventario_id'].unique().tolist()
                opcoes_pastas_divergentes = []
                for id_pasta in ids_inventarios_com_erro:
                    match_inv = df_inventarios[df_inventarios['id'].str.replace('#', '', regex=False) == str(id_pasta)]
                    nome_pasta = match_inv.iloc[0]['nome'] if not match_inv.empty else "Inventário Operacional"
                    opcoes_pastas_divergentes.append(f"#{id_pasta} – {nome_pasta}")
                
                st.warning(f"⚠️ Identificamos **{len(ids_inventarios_com_erro)}** pasta(s) contendo erros de saldo cometidos pela equipe.")
                pasta_selecionada_erro = st.selectbox("📂 Escolha a pasta do inventário divergente para liberar a recontagem:", opcoes_pastas_divergentes, key="sb_pasta_reabrir_2a")
                id_pasta_limpo = pasta_selecionada_erro.split(" – ")[0].replace("#", "")
                
                df_erros_desta_pasta = df_todas_contagens_divergentes[df_todas_contagens_divergentes['inventario_id'] == id_pasta_limpo]
                
                with st.form("form_liberacao_2a_contagem"):
                    itens_unicos_erro = df_erros_desta_pasta['cod_produto'].unique()
                    opcoes_materiais = []
                    for m_cod in itens_unicos_erro:
                        match_m = df_erros_desta_pasta[df_erros_desta_pasta['cod_produto'] == m_cod].iloc[0]
                        opcoes_materiais.append(f"{m_cod} - {match_m['desc_produto']} (Lote: {match_m['lote'] if match_m['lote'] else 'Padrão'})")
                        
                    material_selecionado_combo = st.selectbox("Escolha o material com erro para autorizar a 2ª Contagem:", opcoes_materiais)
                    cod_material_alvo = material_selecionado_combo.split(" - ")[0]
                    match_linha_contexto = df_erros_desta_pasta[df_erros_desta_pasta['cod_produto'] == cod_material_alvo].iloc[0]
                    
                    st.write(f"**Ação:** Ao clicar no botão vermelho abaixo, este inventário mudará o status para **'2a Contagem'**, liberando a digitação de volta na tela dos almoxarifes.")
                    
                    if st.form_submit_button("🚨 Abrir e Liberar 2ª Contagem para Almoxarife", type="primary", use_container_width=True):
                        cursor = conn.cursor()
                        cursor.execute("UPDATE inventarios SET status = '2a Contagem' WHERE id = ?", (f"#{id_pasta_limpo}",))
                        cursor.execute("UPDATE contagens SET fase_contagem = '2a Contagem', diferenca = 0, qtd_contada = 0 WHERE id = ?", (int(match_linha_contexto['id']),))
                        conn.commit()
                        st.success(f"🎉 Pasta #{id_pasta_limpo} alterada para '2a Contagem'! O material {cod_material_alvo} já está liberado na tela do almoxarife.")
                        st.rerun()

            st.markdown("---")

            # --- SEÇÃO 2: CONTROLE DE QUALIDADE AMOSTRAL ---
            st.subheader("📁 Controle de Auditoria Própria e Amostral do Supervisor")
            
            if df_inventarios_sup.empty:
                st.info("Crie uma pasta de auditoria do supervisor abaixo.")
                id_inv_sup_atual = None
                inv_sup_selecionado_obj = None
            else:
                lista_inv_sup = [f"{r['id']} – {r['nome']} ({r['status']})" for idx, r in df_inventarios_sup.iterrows()]
                inv_sup_selected = st.selectbox("Selecione a sua Pasta de Auditoria Ativa", lista_inv_sup, key="sel_box_sup_propria_v4")
                id_inv_sup_atual = inv_sup_selected.split(" – ")[0]
                inv_sup_selecionado_obj = df_inventarios_sup[df_inventarios_sup['id'] == id_inv_sup_atual].iloc[0]
            
            with st.expander("➕ Nova Pasta de Auditoria do Supervisor"):
                with st.form("form_novo_sup_interno_v4", clear_on_submit=True):
                    nome_sup_inv = st.text_input("Nome da Pasta de Auditoria Amostral")
                    if st.form_submit_button("Criar Pasta Supervisor", type="primary") and nome_sup_inv:
                        if not df_inventarios_sup.empty:
                            df_limpo_sup_calc = df_inventarios_sup['id'].str.replace('SUP-#', '', regex=False).astype(int)
                            maior_id_sup = df_limpo_sup_calc.max()
                        else:
                            maior_id_sup = 0
                        
                        novo_id_sup = f"SUP-#{maior_id_sup + 1}"
                        hoje_sup = datetime.date.today().strftime("%Y-%m-%d")
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO inventarios_supervisor (id, nome, data, status) VALUES (?, ?, ?, 'Aberto')", (novo_id_sup, nome_sup_inv, hoje_sup))
                        conn.commit()
                        st.rerun()
                            
            if inv_sup_selecionado_obj is not None and inv_sup_selecionado_obj['status'] == "Aberto":
                if st.button("🔒 Encerrar e Fechar Pasta de Auditoria Selecionada", use_container_width=True, type="primary"):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE inventarios_supervisor SET status = 'Fechado' WHERE id = ?", (id_inv_sup_atual,))
                    conn.commit()
                    st.rerun()

            st.write("#### 📤 Anexar Estoque / Planilha de Amostragem do Supervisor")
            arquivo_supervisor = st.file_uploader("Suba a planilha Excel com as amostras mapeadas (.xlsx)", type=["xlsx"], key="sup_excel_loader_v4")
            
            if arquivo_supervisor is not None:
                try:
                    df_temp_check = pd.read_excel(arquivo_supervisor)
                    st.session_state.base_supervisor = df_temp_check
                    st.session_state.nome_arquivo_supervisor = arquivo_supervisor.name
                except Exception as e:
                    st.error(f"Erro ao analisar o arquivo anexo: {e}")

            if st.session_state.base_supervisor is not None:
                st.info(f"📂 **Estoque Anexo Ativo do Supervisor:** {st.session_state.nome_arquivo_supervisor}")
                if st.button("🗑️ Remover Planilha Anexada"):
                    st.session_state.base_supervisor = None
                    st.session_state.nome_arquivo_supervisor = ""
                    st.rerun()

            if id_inv_sup_atual and inv_sup_selecionado_obj['status'] == "Aberto" and st.session_state.base_supervisor is not None:
                st.write("#### 💻 Bipar e Contar Item (Lançamento do Supervisor)")
                
                colunas_sup = list(st.session_state.base_supervisor.columns)
                def encontrar_col_sup(opcoes, default_idx):
                    for opcao in opcoes:
                        for col in colunas_sup:
                            if opcao.lower().replace(" ", "").replace(".", "") in col.lower().replace(" ", "").replace(".", ""):
                                return col
                    return colunas_sup[default_idx] if default_idx < len(colunas_sup) else colunas_sup[0]

                col_cod_sup = encontrar_col_sup(['códproduto', 'codproduto', 'codigo', 'cod'], 0)
                col_desc_sup = encontrar_col_sup(['descproduto', 'descricao', 'desc'], 1)
                col_local_sup = encontrar_col_sup(['descestoquefisico', 'localizacao', 'local', 'estoquefisico'], 2)
                col_qtd_sup = encontrar_col_sup(['qtdestoque', 'quantidade', 'saldo', 'qtd'], -1)
                col_id_est_sup = encontrar_col_sup(['idestoquefísico', 'idestoqfísico', 'idestoque', 'codestoque'], 0)

                bip_supervisor = st.text_input("Bipe o código do material da sua amostragem:", value="", key=f"sup_bip_v4_{st.session_state.contador_reset_sup}")
                
                if bip_supervisor:
                    busca_sup = str(bip_supervisor).upper().strip()
                    cod_sup = busca_sup.split(" - ")[-1].strip() if " - " in busca_sup else busca_sup
                    item_sup = st.session_state.base_supervisor[st.session_state.base_supervisor[col_cod_sup].astype(str).str.upper().str.strip() == cod_sup]
                    
                    if not item_sup.empty:
                        desc_sup = item_sup.iloc[0][col_desc_sup]
                        local_sup = item_sup.iloc[0][col_local_sup] if col_local_sup in item_sup.columns else "Não Informado"
                        id_est_sup = str(item_sup.iloc[0][col_id_est_sup]).strip() if col_id_est_sup in item_sup.columns else ""
                        try: qtd_sis_sup = int(pd.to_numeric(item_sup.iloc[0][col_qtd_sup], errors='coerce'))
                        except: qtd_sis_sup = 0
                        
                        col_ativo_sup_real = None
                        for c_at in item_sup.columns:
                            if str(c_at).strip().upper() in ["ATIVO", "Nº ATIVO", "NUMERO ATIVO", "COD ATIVO"]:
                                col_ativo_sup_real = c_at
                                break
                                
                        ativos_sup_encontrados = []
                        if col_ativo_sup_real:
                            ativos_sup_encontrados = item_sup[col_ativo_sup_real].dropna().astype(str).str.strip().unique().tolist()
                        
                        with st.form("form_auditoria_sup_propria", clear_on_submit=True):
                            st.write(f"**Item Selecionado:** {cod_sup} - {desc_sup}")
                            col_f1, col_f2, col_f3 = st.columns(3)
                            with col_f1: qtd_aud_sup = st.number_input("Quantidade Real Encontrada Fisicamente", min_value=0, step=1, value=0)
                            with col_f2: etiq_status = st.selectbox("A etiqueta física está correta?", ["Sim", "Não"])
                            with col_f3: local_status = st.selectbox("O material está na localização correta?", ["Sim", "Não"])
                            
                            if len(ativos_sup_encontrados) > 1:
                                ativo_sup_input = st.selectbox("Selecione o Número do Ativo correspondente:", ativos_sup_encontrados)
                            else:
                                valor_padrao_at = ativos_sup_encontrados[0] if len(ativos_sup_encontrados) == 1 else ""
                                ativo_sup_input = st.text_input("Número do Ativo (Opcional)", value=valor_padrao_at)
                                
                            if st.form_submit_button("💾 Salvar Registro de Auditoria", type="primary", use_container_width=True):
                                ativo_sup_l = ativo_sup_input.strip().upper()
                                dif_sup = qtd_aud_sup - qtd_sis_sup
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO auditorias_supervisor (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, qtd_sistema, qtd_auditada, diferenca, etiqueta_correta, localizacao_correta, supervisor, data_hora, ativo)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (id_inv_sup_atual, id_est_sup, local_sup, cod_sup, desc_sup, qtd_sis_sup, qtd_aud_sup, dif_sup, etiq_status, local_status, st.session_state.operador, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ativo_sup_l))
                                conn.commit()
                                st.session_state.contador_reset_sup += 1
                                st.rerun()
                    else:
                        st.error("❌ Código do material não localizado na sua planilha anexa.")

            if id_inv_sup_atual:
                df_auditorias_atual = pd.read_sql_query("SELECT * FROM auditorias_supervisor WHERE inventario_id = ? ORDER BY id DESC", conn, params=(id_inv_sup_atual,))
                st.write("### 📝 Amostras Coletadas Coletas na Pasta Atual")
                st.dataframe(df_auditorias_atual, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.write("### 🔬 Histórico Geral de Auditorias de Pastas do Supervisor por Período")
            c_dt_sup1, c_dt_sup2 = st.columns(2)
            with c_dt_sup1:
                dt_ini_sup = st.date_input("Data Inicial (Supervisor)", datetime.date.today() - datetime.timedelta(days=90), key="hist_sup_dt_ini")
            with c_dt_sup2:
                dt_fim_sup = st.date_input("Data Final (Supervisor)", datetime.date.today() + datetime.timedelta(days=1), key="hist_sup_dt_fim")
                
            df_inventarios_sup['datetime_parsed'] = pd.to_datetime(df_inventarios_sup['data'], errors='coerce').dt.date
            df_sup_filtrados = df_inventarios_sup[
                (df_inventarios_sup['datetime_parsed'] >= dt_ini_sup) & 
                (df_inventarios_sup['datetime_parsed'] <= dt_fim_sup)
            ]
            
            if not df_sup_filtrados.empty:
                tam_pagina_sup = 15
                total_itens_sup = len(df_sup_filtrados)
                total_paginas_sup = (total_itens_sup - 1) // tam_pagina_sup + 1
                
                if st.session_state.pagina_historico_sup >= total_paginas_sup:
                    st.session_state.pagina_historico_sup = 0
                    
                idx_ini_sup = st.session_state.pagina_historico_sup * tam_pagina_sup
                idx_fim_sup = idx_ini_sup + tam_pagina_sup
                df_pagina_sup_atual = df_sup_filtrados.iloc[idx_ini_sup:idx_fim_sup]
                
                for idx, inv_s in df_pagina_sup_atual.iterrows():
                    df_hist_sup = pd.read_sql_query("SELECT * FROM auditorias_supervisor WHERE inventario_id = ? ORDER BY id DESC", conn, params=(inv_s['id'],))
                    with st.expander(f"📁 {inv_s['id']} – {inv_s['nome']} | {inv_s['data']} | {len(df_hist_sup)} itens auditados"):
                        c_dl, c_del = st.columns([2, 2])
                        with c_dl:
                            if not df_hist_sup.empty:
                                excel_sup_hist = converter_para_excel(df_hist_sup)
                                st.download_button(label="📥 Baixar Pasta em Excel", data=excel_sup_hist, file_name=f"auditoria_{inv_s['id']}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_sup_{inv_s['id']}")
                        with c_del:
                            if eh_supervisor:
                                # --- FIX DUPLICATE KEY: corrigida a sintaxe para extrair a string do ID de forma individual de cada laço ---
                                if st.button("🗑️ Deletar Pasta de Auditoria", key=f"del_folder_sup_{str(inv_s['id'])}", use_container_width=True):
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM inventarios_supervisor WHERE id = ?", (inv_s['id'],))
                                    cursor.execute("DELETE FROM auditorias_supervisor WHERE inventario_id = ?", (inv_s['id'],))
                                    conn.commit()
                                    st.success(f"✅ Pasta {inv_s['id']} excluída com sucesso!")
                                    st.rerun()
                                    
                        if not df_hist_sup.empty:
                            st.dataframe(df_hist_sup, use_container_width=True, hide_index=True)

    # --- ABA 4: ACURACIDADE ESTOQUE ---
    with aba_acuracidade:
        st.title("📈 Acuracidade - Controle Amostral")
        df_todas_auditorias_banco = pd.read_sql_query("SELECT * FROM auditorias_supervisor ORDER BY id DESC", conn)
        
        if df_todas_auditorias_banco.empty:
            st.info("💡 Nenhuma amostragem coletada no banco de dados para computar as acuracidades.")
        else:
            linhas_planilha_acuracidade = []
            for dep_id, grupo in df_todas_auditorias_banco.groupby('id_estoque'):
                certos_qtd = len(grupo[grupo['diferenca'] == 0])
                certos_etiq = len(grupo[grupo['etiqueta_correta'] == "Sim"])
                certos_local = len(grupo[grupo['localizacao_correta'] == "Sim"])
                total_itens_dep = len(grupo)
                
                desc_dep = grupo.iloc[0]['desc_estoque'] if 'desc_estoque' in grupo.columns else "Não Informado"
                data_ultima = grupo.iloc[0]['data_hora'].split(" ")[0] if 'data_hora' in grupo.columns else ""
                
                pct_saldo = (certos_qtd / total_itens_dep) * 100
                pct_etiq = (certos_etiq / total_itens_dep) * 100
                pct_local = (certos_local / total_itens_dep) * 100
                
                bola_saldo = f"🟢 {pct_saldo:.1f}%" if pct_saldo == 100 else f"🔴 {pct_saldo:.1f}%"
                bola_etiq = f"🟢 {pct_etiq:.1f}%" if pct_etiq == 100 else f"🔴 {pct_etiq:.1f}%"
                bola_local = f"🟢 {pct_local:.1f}%" if pct_local == 100 else f"🔴 {pct_local:.1f}%"
                
                linhas_planilha_acuracidade.append({
                    "CÓDIGO ESTOQUE AUDITADO": dep_id,
                    "DESCRIÇÃO DO ESTOQUE": desc_dep,
                    "ACURACIDADE DE SALDO": bola_saldo,
                    "ACURACIDADE ETIQUETAS": bola_etiq,
                    "ACURACIDADE LOCALIZAÇÃO": bola_local,
                    "QUANTOS ITENS CONTABILIZADOS": total_itens_dep,
                    "DATA": data_ultima
                })
            
            df_planilha_final = pd.DataFrame(linhas_planilha_acuracidade)
            st.dataframe(df_planilha_final, use_container_width=True, hide_index=True)
            
            if eh_supervisor:
                with st.expander("⚙️ Painel do Administrador - Deletar Métricas por Código de Estoque"):
                    lista_estoques_audita = list(df_planilha_final["CÓDIGO ESTOQUE AUDITADO"].unique())
                    est_para_deletar = st.selectbox("Escolha o Código do Estoque para expurgar do banco", lista_estoques_audita, key="del_est_acuracidade_box")
                    if st.button("🚨 Confirmar Exclusão do Estoque", type="primary", use_container_width=True):
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM auditorias_supervisor WHERE id_estoque = ?", (est_para_deletar,))
                        conn.commit()
                        st.success(f"✅ Todos os lançamentos do estoque {est_para_deletar} foram deletados!")
                        st.rerun()

            st.write("")
            excel_acuracidade = converter_para_excel(df_planilha_final)
            st.download_button(label="📥 Exportar Planilha de Acuracidade para Excel", data=excel_acuracidade, file_name="acuracidade_depositos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("---")
        
        st.write("### 🔬 Histórico Geral de Auditorias de Pastas do Supervisor por Período")
        c_dt_sup1, c_dt_sup2 = st.columns(2)
        with c_dt_sup1:
            dt_ini_sup = st.date_input("Data Inicial (Supervisor)", datetime.date.today() - datetime.timedelta(days=90), key="acuracidade_sup_dt_ini")
        with c_dt_sup2:
            dt_fim_sup = st.date_input("Data Final (Supervisor)", datetime.date.today() + datetime.timedelta(days=1), key="acuracidade_sup_dt_fim")
            
        df_inventarios_sup['datetime_parsed'] = pd.to_datetime(df_inventarios_sup['data'], errors='coerce').dt.date
        df_sup_filtrados = df_inventarios_sup[
            (df_inventarios_sup['datetime_parsed'] >= dt_ini_sup) & 
            (df_inventarios_sup['datetime_parsed'] <= dt_fim_sup)
        ]
        
        if not df_sup_filtrados.empty:
            tam_pagina_sup = 15
            total_itens_sup = len(df_sup_filtrados)
            total_paginas_sup = (total_itens_sup - 1) // tam_pagina_sup + 1
            
            if st.session_state.pagina_historico_sup >= total_paginas_sup:
                st.session_state.pagina_historico_sup = 0
                
            idx_ini_sup = st.session_state.pagina_historico_sup * tam_pagina_sup
            idx_fim_sup = idx_ini_sup + tam_pagina_sup
            df_pagina_sup_atual = df_sup_filtrados.iloc[idx_ini_sup:idx_fim_sup]
            
            for idx, inv_s in df_pagina_sup_atual.iterrows():
                df_hist_sup = pd.read_sql_query("SELECT * FROM auditorias_supervisor WHERE inventario_id = ? ORDER BY id DESC", conn, params=(inv_s['id'],))
                with st.expander(f"📁 {inv_s['id']} – {inv_s['nome']} | {inv_s['data']} | {len(df_hist_sup)} itens auditados"):
                    c_dl, c_del = st.columns([2, 2])
                    with c_dl:
                        if not df_hist_sup.empty:
                            excel_sup_hist = converter_para_excel(df_hist_sup)
                            st.download_button(label="📥 Baixar Pasta em Excel", data=excel_sup_hist, file_name=f"auditoria_{inv_s['id']}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_sup_{inv_s['id']}")
                    with c_del:
                        if eh_supervisor:
                            if st.button("🗑️ Deletar Pasta de Auditoria", key=f"del_folder_sup_{str(inv_s['id'])}", use_container_width=True):
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM inventarios_supervisor WHERE id = ?", (inv_s['id'],))
                                cursor.execute("DELETE FROM auditorias_supervisor WHERE inventario_id = ?", (inv_s['id'],))
                                conn.commit()
                                st.success(f"✅ Pasta {inv_s['id']} excluída com sucesso!")
                                st.rerun()
                                    
                    if not df_hist_sup.empty:
                        st.dataframe(df_hist_sup, use_container_width=True, hide_index=True)

    # --- ABA 5: HISTÓRICO GERAL ---
    with aba_historico_geral:
        st.title("📁 Arquivo Geral de Movimentações")
        
        st.write("### 📅 Filtrar Pastas por Período de Abertura")
        c_dt1, c_dt2 = st.columns(2)
        with c_dt1:
            data_inicio_filtro = st.date_input("Data Inicial", datetime.date.today() - datetime.timedelta(days=90), key="hist_dt_ini")
        with c_dt2:
            data_fim_filtro = st.date_input("Data Final", datetime.date.today() + datetime.timedelta(days=1), key="hist_dt_fim")
            
        st.markdown("---")
        
        if df_inventarios.empty:
            st.info("Nenhum inventário operacional registrado no banco de dados.")
        else:
            df_inventarios['datetime_parsed'] = pd.to_datetime(df_inventarios['data'], errors='coerce').dt.date
            df_inventarios_filtrados = df_inventarios[
                (df_inventarios['datetime_parsed'] >= data_inicio_filtro) & 
                (df_inventarios['datetime_parsed'] <= data_fim_filtro)
            ]
            
            if df_inventarios_filtrados.empty:
                st.warning("⚠️ Nenhum inventário foi localizado dentro do intervalo de datas selecionado.")
            else:
                tamanho_pagina = 15
                total_itens = len(df_inventarios_filtrados)
                total_paginas = (total_itens - 1) // tamanho_pagina + 1
                
                if st.session_state.pagina_historico >= total_paginas:
                    st.session_state.pagina_historico = 0
                    
                inicio_idx = st.session_state.pagina_historico * tamanho_pagina
                fim_idx = inicio_idx + tamanho_pagina
                
                df_pagina_atual = df_inventarios_filtrados.iloc[inicio_idx:fim_idx]
                st.write(f"Exibindo do **{inicio_idx + 1}º** ao **{min(fim_idx, total_itens)}º** inventário (Total de {total_itens} pastas).")
                
                for idx, inv in df_pagina_atual.iterrows():
                    id_inv_proc = inv['id'].replace('#','')
                    df_hist_inv = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? ORDER BY id DESC", conn, params=(id_inv_proc,))
                    
                    c_exp_g, c_del_g = st.columns([8, 2])
                    with c_exp_g:
                        with st.expander(f"📁 {inv['id']} – {inv['nome']} | Data: {inv['data']} | Status: {inv['status']} ({len(df_hist_inv)} contados)"):
                            if not df_hist_inv.empty:
                                excel_geral_hist = converter_para_excel(df_hist_inv)
                                st.download_button(label="📥 Baixar Lançamentos Feitos em Excel", data=excel_geral_hist, file_name=f"inventario_geral_{inv['id']}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_ger_{inv['id']}")
                                
                                colunas_existentes_hist = list(df_hist_inv.columns)
                                ordem_colunas_print = ['id', 'inventario_id', 'id_estoque', 'desc_estoque', 'cod_produto', 'desc_produto', 'unid_medida', 'qtd_sistema', 'qtd_contada', 'diferenca', 'ativo', 'observacao', 'operador', 'data_hora', 'fase_contagem']
                                    
                                st.write("**📋 Itens Efetivamente Contados:**")
                                st.dataframe(df_hist_inv[ordem_colunas_print], use_container_width=True, hide_index=True)
                                
                            df_base_local_proc = pd.read_sql_query("SELECT cod_produto, desc_produto, desc_estoque_fisico FROM itens_base_inventario WHERE inventario_id = ?", conn, params=(id_inv_proc,))
                            if not df_base_local_proc.empty:
                                set_contados_global = set(df_hist_inv['cod_produto'].astype(str).str.upper().str.strip().tolist())
                                esquecidos_linhas = []
                                for _, row_b in df_base_local_proc.iterrows():
                                    c_atual = str(row_b['cod_produto']).upper().strip()
                                    if c_atual not in set_contados_global:
                                        esquecidos_linhas.append({
                                            "Código Produto": c_atual,
                                            "Descrição Produto": row_b['desc_produto'],
                                            "Localização Prevista": row_b['desc_estoque_fisico']
                                        })
                                
                                st.write("---")
                                st.write(f"**❌ Itens Não Contados: {len(esquecidos_linhas)} itens**")
                                if len(esquecidos_linhas) > 0:
                                    df_esquecidos_print = pd.DataFrame(esquecidos_linhas)
                                    st.dataframe(df_esquecidos_print, use_container_width=True, hide_index=True)
                                else:
                                    st.success("🎯 Inventário Perfeito! 100% mapeado.")
                    with c_del_g:
                        if eh_supervisor:
                            if st.button("🗑️ Deletar Pasta", key=f"del_folder_ger_{inv['id']}", use_container_width=True):
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM inventarios WHERE id = ?", (inv['id'],))
                                cursor.execute("DELETE FROM contagens WHERE inventario_id = ?", (inv['id'].replace('#',''),))
                                cursor.execute("DELETE FROM itens_base_inventario WHERE inventario_id = ?", (inv['id'].replace('#',''),))
                                conn.commit()
                                st.success("Pasta operacional excluída!")
                                st.rerun()
                                
                st.markdown("---")
                col_pag1, col_pag_texto, col_pag2 = st.columns([2, 6, 2])
                with col_pag1:
                    if st.button("◀ Anterior", use_container_width=True, disabled=(st.session_state.pagina_historico == 0)):
                        st.session_state.pagina_historico -= 1
                        st.rerun()
                with col_pag_texto:
                    st.markdown(f"<p style='text-align: center; margin-top: 7px;'>Página <strong>{st.session_state.pagina_historico + 1}</strong> de <strong>{total_paginas}</strong></p>", unsafe_allow_html=True)
                with col_pag2:
                    if st.button("Próximo ▶", use_container_width=True, disabled=(st.session_state.pagina_historico >= total_paginas - 1)):
                        st.session_state.pagina_historico += 1
                        st.rerun()

    # --- ABA 6: BASE DE ESTOQUE ---
    with aba_base:
        if st.session_state.base_sistema is not None:
            st.subheader("📄 Espelho Base de Saldo do Upload")
            
            if id_inventario_atual:
                df_lancados_reais = pd.read_sql_query("SELECT cod_produto, operador FROM contagens WHERE inventario_id = ?", conn, params=(id_inventario_atual.replace('#',''),))
                mapa_contados = dict(zip(df_lancados_reais['cod_produto'].astype(str).str.upper().str.strip(), df_lancados_reais['operador']))
            else:
                mapa_contados = {}
            
            def calcular_status_linha(linha_cod):
                cod_chave = str(linha_cod).upper().strip()
                if cod_chave in mapa_contados:
                    return f"🟩 Contabilizado por ({mapa_contados[cod_chave]})"
                return "🟥 Não Contado"
                
            df_base_visual = st.session_state.base_sistema.copy()
            df_base_visual["Status de Contagem"] = df_base_visual['cod_produto'].apply(calcular_status_linha)
            
            colunas_ordenadas = ["Status de Contagem"] + [col for col in df_base_visual.columns if col != "Status de Contagem"]
            st.dataframe(df_base_visual[colunas_ordenadas], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma base cadastrada na barra lateral.")

    # --- ABA 7: DESEMPENHO ---
    with aba_graficos:
        st.title("🏆 Desempenho e Auditoria de Prazos por Estoque")
        
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
            GROUP BY id_estoque
        """, conn)
        
        mapa_datas = dict(zip(df_ultimas_contagens['id_estoque'].astype(str).str.strip(), df_ultimas_contagens['ultima_data']))
        hoje_dt = datetime.datetime.now()
        linhas_desempenho = []
        criticos_count, auditar_count, bom_count = 0, 0, 0
        
        for est in lista_estoques_fixa:
            get_data_formatada = ""
            est_id = est["id"]
            est_desc = est["desc"]
            ultima_data_str = mapa_datas.get(est_id, None)
            
            if ultima_data_str:
                try:
                    dt_contagem = datetime.datetime.strptime(ultima_data_str, "%Y-%m-%d %H:%M:%S")
                    dias_passados = (hoje_dt - dt_contagem).days
                    get_data_formatada = dt_contagem.strftime("%d/%m/%Y %H:%M")
                except:
                    dias_passados = 999
                    get_data_formatada = "Sem histórico"
            else:
                dias_passados = 999
                get_data_formatada = "Nunca Contado"
                
            if dias_passados <= 7:
                status_final = "🟢 Bom"
                bom_count += 1
            elif dias_passados <= 14:
                status_final = "🟡 Necessário auditar"
                auditar_count += 1
            else:
                status_final = "🔴 Crítico"
                criticos_count += 1
                
            linhas_desempenho.append({
                "Id. Estoque": est_id,
                "Descrição do Estoque Físico": est_desc,
                "Última Contagem Realizada": get_data_formatada,
                "Dias sem Contar": dias_passados if dias_passados != 999 else "—",
                "Status de Criticidade": status_final
            })
            
        df_desempenho_final = pd.DataFrame(linhas_desempenho)
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1: st.markdown(f'<div class="bloco-info" style="border-left: 5px solid #2ecc71;"><div class="bloco-titulo">ESTOQUES EM DIA</div><div class="bloco-valor" style="color: #27ae60;">{bom_count}</div></div>', unsafe_allow_html=True)
        with kpi2: st.markdown(f'<div class="bloco-info" style="border-left: 5px solid #f1c40f;"><div class="bloco-titulo">NECESSÁRIO AUDITAR</div><div class="bloco-valor" style="color: #f39c12;">{auditar_count}</div></div>', unsafe_allow_html=True)
        with kpi3: st.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:10px; border-left: 5px solid #e74c3c;"><div class="bloco-titulo">🔴 CRÍTICO (+2 SEMANAS)</div><div class="bloco-valor" style="color: #c0392b;">{criticos_count}</div></div>', unsafe_allow_html=True)
            
        st.write("")
        st.dataframe(df_desempenho_final, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.write("### 🏆 Ranking de Lançamentos por Operador")
        df_ops = pd.read_sql_query("SELECT operador as Operador, COUNT(id) as [Lançamentos Feitos] FROM contagens GROUP BY operador", conn)
        if not df_ops.empty:
            st.bar_chart(data=df_ops, x='Operador', y='Lançamentos Feitos', color="#d35400")
            
    conn.close()
