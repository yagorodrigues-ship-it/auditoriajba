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
            lote TEXT
        )
    """)

    # Tabela de Auditorias do Supervisor (E 3ª Contagem)
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
        st.write(f"👤 **Operador Ativo:** {st.session_state.operador}")
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
            id_inventario_atual = " – " in inventario_selected and inventario_selected.split(" – ")[0] or None
            inventario_selected_obj = df_inventarios[df_inventarios['id'] == id_inventario_atual].iloc[0]

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

        # TRAVA 100% CONCLUÍDO
        if inventario_selected_obj is not None and inventario_selected_obj['status'] == "Aberto":
            itens_esquecidos_lista = []
            if st.session_state.base_sistema is not None:
                df_c_verif = pd.read_sql_query("SELECT cod_produto FROM contagens WHERE inventario_id = ?", conn, params=(id_inventario_atual.replace('#',''),))
                lista_contados_set = set(df_c_verif['cod_produto'].astype(str).str.upper().str.strip().tolist())
                
                for idx, r_base in st.session_state.base_sistema.iterrows():
                    cod_b = str(r_base[col_cod]).upper().strip()
                    if cod_b not in lista_contados_set:
                        itens_esquecidos_lista.append(cod_b)

            if len(itens_esquecidos_lista) == 0:
                if st.button("🔒 Fechar Inventário (100% Concluído)", use_container_width=True):
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
                
                # Filtra todos os itens condizentes com o código mapeado da planilha de saldo
                itens_filtrados = st.session_state.base_sistema[st.session_state.base_sistema[col_cod].astype(str).str.upper().str.strip() == codigo_rastreio]
                
                if not itens_filtrados.empty:
                    # LOCALIZAÇÃO FLEXÍVEL DA COLUNA DE LOTE (Ignora espaços invisíveis ou maiúsculas/minúsculas)
                    col_lote_real = None
                    for c in st.session_state.base_sistema.columns:
                        if str(c).strip().upper() == "LOTE":
                            col_lote_real = c
                            break
                    
                    lotes_disponiveis = []
                    if col_lote_real:
                        lotes_disponiveis = itens_filtrados[col_lote_real].dropna().astype(str).str.strip().unique().tolist()
                        lotes_disponiveis = [l for l in lotes_disponiveis if l != "" and l.lower() != "nan"]

                    # Interface para escolha de Lote reposicionada abaixo da descrição do produto
                    lote_selecionado = ""
                    if lotes_disponiveis:
                        st.warning("⚠️ Múltiplos lotes identificados para este item! Escolha o lote correto abaixo.")
                        lote_selecionado = st.selectbox("👇 SELECIONE O LOTE PARA CONTAGEM:", lotes_disponiveis, key="lote_selector_bip")
                        # Filtra todas as correspondências daquele lote específico
                        linhas_com_lote = itens_filtrados[itens_filtrados[col_lote_real].astype(str).str.strip() == lote_selecionado]
                        item_especifico = linhas_com_lote.iloc[0]
                    else:
                        item_especifico = itens_filtrados.iloc[0]
                        linhas_com_lote = itens_filtrados

                    # LOCALIZAÇÃO FLEXÍVEL DA COLUNA DE ATIVO
                    col_ativo_real = None
                    for c in st.session_state.base_sistema.columns:
                        if str(c).strip().upper() in ["ATIVO", "Nº ATIVO", "NUMERO ATIVO", "COD ATIVO"]:
                            col_ativo_real = c
                            break
                    
                    ativos_disponiveis = []
                    if col_ativo_real:
                        ativos_disponiveis = linhas_com_lote[col_ativo_real].dropna().astype(str).str.strip().unique().tolist()
                        ativos_disponiveis = [a for a in ativos_disponiveis if a != "" and a.lower() != "nan"]

                    unid_val = item_especifico[col_unidade] if col_unidade in st.session_state.base_sistema.columns else "UN"
                    desc_val = item_especifico[col_desc]
                    local_val = item_especifico[col_local] if col_local in st.session_state.base_sistema.columns else "Não Informado"
                    id_estoque_val = str(item_especifico[col_id_estoque]).strip() if col_id_estoque in st.session_state.base_sistema.columns else ""
                    
                    try:
                        # Se selecionou um lote/ativo específico, pega o saldo daquela combinação
                        qtd_sis = int(pd.to_numeric(item_especifico[col_qtd], errors='coerce'))
                        if pd.isna(qtd_sis): qtd_sis = 0
                    except: qtd_sis = 0
                    
                    b1, b2, b3, b4 = st.columns(4)
                    b1.markdown(f'<div class="bloco-info"><div class="bloco-titulo">CÓD. PRODUTO</div><div class="bloco-valor">{codigo_rastreio}</div></div>', unsafe_allow_html=True)
                    b2.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:0px;"><div class="bloco-titulo">ESTOQUE FÍSICO</div><div class="bloco-valor" style="font-size:22px;">{local_val}</div></div>', unsafe_allow_html=True)
                    b3.markdown(f'<div class="bloco-info"><div class="bloco-titulo">UNID. MEDIDA</div><div class="bloco-valor">{unid_val}</div></div>', unsafe_allow_html=True)
                    b4.markdown(f'<div class="bloco-info"><div class="bloco-titulo">LOTE EM CONTAGEM</div><div class="bloco-valor" style="color:#d35400;">{lote_selecionado if lote_selecionado else "Padrão"}</div></div>', unsafe_allow_html=True)
                    
                    st.markdown(f"**Descrição do Material:** {desc_val}")
                    st.info(f"📋 **Lote Vinculado à Contagem Corrente:** {lote_selecionado if lote_selecionado else 'Não se aplica / Lote Único'}")
                    
                    with st.form("confirmar_form", clear_on_submit=True):
                        qtd_fisica = st.number_input("📦 Quantidade contada fisicamente (Obrigatório)", min_value=0, step=1, value=0)
                        
                        # Se houver múltiplos ativos na planilha para esse item, vira Selectbox. Caso contrário, input livre.
                        if len(ativos_disponiveis) > 1:
                            ativo_input = st.selectbox("🔢 Selecione o Número do Ativo correspondente:", ativos_disponiveis)
                        else:
                            valor_padrao_ativo = ativos_disponiveis[0] if len(ativos_disponiveis) == 1 else ""
                            ativo_input = st.text_input("🔢 Número do Ativo (Opcional)", value=valor_padrao_ativo)
                            
                        observacao = st.text_input("📝 Observação (opcional)")
                        
                        if st.form_submit_button("✓ Confirmar Contagem", type="primary", use_container_width=True):
                            ativo_l = str(ativo_input).strip().upper()
                            if qtd_fisica <= 0:
                                st.error("❌ Erro: Informe uma quantidade maior que 0!")
                            else:
                                agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                dif_c = qtd_fisica - qtd_sis
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, observacao, operador, data_hora, lote)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (id_inventario_atual.replace("#","") if id_inventario_atual else "", id_estoque_val, local_val, codigo_rastreio, desc_val, unid_val, qtd_sis, qtd_fisica, dif_c, ativo_l, observacao, st.session_state.operador, agora, lote_selecionado))
                                conn.commit()
                                st.session_state.ultimo_item_sucesso = f"✅ Lançamento Efetuado com sucesso para o Lote {lote_selecionado if lote_selecion0 else 'Padrão'}!"
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
                soma_contada = int(df_contagens_mutaveis['qtd_contada'].sum())
                soma_sistema = int(df_contagens_mutaveis['qtd_sistema'].sum())
                diferenca_acumulada = int(df_contagens_mutaveis['diferenca'].sum())
                
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">📦 ITENS CONTADOS</div><div class="bloco-valor">{total_auditado}</div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">⚠️ COM DIVERGÊNCIA</div><div class="bloco-valor">{itens_divergentes}</div></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">QUANTIDADE CONTADA</div><div class="bloco-valor">{soma_contada}</div></div>', unsafe_allow_html=True)
                with c4: st.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:0px;"><div class="bloco-titulo">QUANTIDADE SISTEMA</div><div class="bloco-valor">{soma_sistema} <span style="font-size:14px; color:#e74c3c;">(Dif: {diferenca_acumulada})</span></div></div>', unsafe_allow_html=True)
                
                excel_atual = converter_para_excel(df_contagens_mutaveis)
                st.download_button(label="📥 Exportar Lançamentos Filtrados para Excel", data=excel_atual, file_name=f"contagem_{id_inventario_atual}_{st.session_state.operador}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                st.write("")

                colunas_existentes_contagens = list(df_contagens_mutaveis.columns)
                ordem_colunas_print = ['id', 'inventario_id', 'id_estoque', 'desc_estoque', 'cod_produto', 'desc_produto', 'unid_medida', 'qtd_sistema', 'qtd_contada', 'diferenca', 'ativo', 'observacao', 'operador', 'data_hora']
                if 'lote' in colunas_existentes_contagens:
                    ordem_colunas_print.append('lote')
                
                st.dataframe(df_contagens_mutaveis[ordem_colunas_print], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum inventário selecionado.")

    # --- ABA 3: PAINEL SUPERVISOR ---
    with aba_supervisor:
        st.title("🔬 Controle de Qualidade Amostral do Supervisor")
        
        if not eh_supervisor:
            st.error("🚫 Acesso restrito. Esta tela só pode ser operada pelo Administrador/Supervisor.")
        else:
            st.subheader("📁 Controle de Inventários do Supervisor")
            
            if df_inventarios_sup.empty:
                st.info("Nenhum inventário de amostragem aberto. Crie um ao lado.")
                id_inv_sup_atual = None
                inv_sup_selecionado_obj = None
                index_default_combo = 0
            else:
                lista_inv_sup = [f"{r['id']} – {r['nome']} ({r['status']})" for idx, r in df_inventarios_sup.iterrows()]
                index_default_combo = 0
                for idx_c, txt_c in enumerate(lista_inv_sup):
                    if "(Aberto)" in txt_c:
                        index_default_combo = idx_c
                        break
                        
                inv_sup_selected = st.selectbox("Selecione a sua Auditoria Amostral", lista_inv_sup, index=index_default_combo, key="sel_box_sup_local_v3")
                id_inv_sup_atual = inv_sup_selected.split(" – ")[0]
                inv_sup_selecionado_obj = df_inventarios_sup[df_inventarios_sup['id'] == id_inv_sup_atual].iloc[0]
            
            col_vazio, col_btn_pop = st.columns([7, 3])
            with col_btn_pop:
                with st.popover("➕ Novo Inventário Supervisor", use_container_width=True):
                    with st.form("form_novo_sup_interno_v3", clear_on_submit=True):
                        nome_sup_inv = st.text_input("Nome da Auditoria Amostral")
                        if st.form_submit_button("Confirmar Criação", type="primary") and nome_sup_inv:
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
                if st.button("🔒 Fechar Inventário Supervisor", use_container_width=True, type="primary", key="btn_close_sup_interno"):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE inventarios_supervisor SET status = 'Fechado' WHERE id = ?", (id_inv_sup_atual,))
                    conn.commit()
                    st.rerun()

            st.markdown("---")

            st.subheader("📤 Upload da Planilha de Amostragem do Supervisor")
            arquivo_supervisor = st.file_uploader("Suba a planilha Excel para a amostragem do supervisor (.xlsx)", type=["xlsx"], key="sup_unified_excel_loader_v3")
            
            if arquivo_supervisor is not None:
                try:
                    df_temp_check = pd.read_excel(arquivo_supervisor)
                    colunas_norm = [str(c).strip().lower().replace("º", "").replace("ó", "o") for c in df_temp_check.columns]
                    tem_ativo = any(x in colunas_norm for x in ['ativo', 'n ativo', 'numero ativo', 'cod ativo'])
                    
                    if not tem_ativo:
                        st.error("❌ Erro: Coluna 'Ativo' não encontrada na planilha!")
                        st.session_state.base_supervisor = None
                    elif df_temp_check.iloc[:, [i for i, c in enumerate(colunas_norm) if c in ['ativo', 'n ativo', 'numero ativo', 'cod ativo']][0]].isnull().any():
                        st.error("⚠️ Erro: Coluna 'Ativo' possui valores em branco na planilha.")
                        st.session_state.base_supervisor = None
                    else:
                        if st.session_state.base_supervisor is None:
                            st.session_state.base_supervisor = df_temp_check
                            st.session_state.nome_arquivo_supervisor = arquivo_supervisor.name
                            st.rerun()
                except Exception as e:
                    st.error(f"Erro ao analisar arquivo: {e}")

            if st.session_state.base_supervisor is not None:
                st.info(f"📂 **Base Ativa do Supervisor:** {st.session_state.nome_arquivo_supervisor}")
                if st.button("🗑️ Remover Planilha"):
                    st.session_state.base_supervisor = None
                    st.session_state.nome_arquivo_supervisor = ""
                    st.rerun()

            st.markdown("---")

            if id_inv_sup_atual:
                df_auditorias_atual = pd.read_sql_query("SELECT * FROM auditorias_supervisor WHERE inventario_id = ? ORDER BY id DESC", conn, params=(id_inv_sup_atual,))
                
                if inv_sup_selecionado_obj['status'] == "Aberto":
                    if st.session_state.base_supervisor is not None:
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

                        bip_supervisor = st.text_input("💻 Bipar item para Amostragem (Supervisor)", value="", placeholder="Bipe o item da sua planilha...", key=f"sup_bip_{st.session_state.contador_reset_sup}")
                        
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
                                
                                with st.form("form_auditoria_sup_interno", clear_on_submit=True):
                                    st.write(f"**Item Selecionado:** {cod_sup} - {desc_sup}")
                                    col_f1, col_f2, col_f3 = st.columns(3)
                                    with col_f1: qtd_aud_sup = st.number_input("Quantidade Real Encontrada", min_value=0, step=1, value=0)
                                    with col_f2: etiq_status = st.selectbox("A etiqueta física está correta?", ["Sim", "Não"])
                                    with col_f3: local_status = st.selectbox("O material está na localização correta?", ["Sim", "Não"])
                                    
                                    ativo_sup_input = st.text_input("🔢 Número do Ativo (Obrigatório)")
                                        
                                    if st.form_submit_button("💾 Salvar Auditoria", type="primary", use_container_width=True):
                                        ativo_sup_l = ativo_sup_input.strip().upper()
                                        if not ativo_sup_l:
                                            st.error("❌ Erro: O Número do Ativo é obrigatório!")
                                        else:
                                            dif_sup = qtd_aud_sup - qtd_sis_sup
                                            cursor = conn.cursor()
                                            cursor.execute("""
                                                INSERT INTO auditorias_supervisor (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, qtd_sistema, qtd_auditada, diferenca, etiqueta_correta, localizacao_correta, supervisor, data_hora, ativo)
                                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                            """, (id_inv_sup_atual, id_est_sup, local_sup, cod_sup, desc_sup, qtd_sis_sup, qtd_aud_sup, dif_sup, etiq_status, local_status, st.session_state.operador, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ativo_sup_l))
                                            conn.commit()
                                            st.session_state.contador_reset_sup += 1
                                            st.rerun()

                    # 3ª Contagem
                    st.write("### 🔄 Auditoria de Divergências (Módulo ADM de 3ª Contagem)")
                    df_geral_funcionarios_analise = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ?", conn, params=(id_inventario_atual.replace('#',''),))
                    
                    if not df_geral_funcionarios_analise.empty:
                        df_itens_com_erro = df_geral_funcionarios_analise[df_geral_funcionarios_analise['diferenca'] != 0]
                        if not df_itens_com_erro.empty:
                            st.warning(f"⚠️ Identificamos {len(df_itens_com_erro)} materiais divergentes na contagem da equipe. Deseja abrir uma 3ª contagem?")
                            
                            with st.form("form_3contagem_adm"):
                                material_recontar = st.selectbox("Escolha o material divergente para recontar", df_itens_com_erro['cod_produto'].unique())
                                q_real_3 = st.number_input("Quantidade Real Constatada (3ª Contagem ADM)", min_value=0, step=1)
                                etiq_3 = st.selectbox("Etiqueta Correta?", ["Sim", "Não"], key="etiq3")
                                local_3 = st.selectbox("Localização Correta?", ["Sim", "Não"], key="local3")
                                ativo_3_input = st.text_input("🔢 Número do Ativo (Obrigatório)")
                                
                                if st.form_submit_button("🔄 Gravar 3ª Contagem Definitiva", type="primary"):
                                    ativo_3_l = ativo_3_input.strip().upper()
                                    if not ativo_3_l:
                                        st.error("❌ Erro: O preenchimento do Número do Ativo é obrigatório!")
                                    else:
                                        match_linha = df_itens_com_erro[df_itens_com_erro['cod_produto'] == material_recontar].iloc[0]
                                        dif_3 = q_real_3 - int(match_linha['qtd_sistema'])
                                        
                                        cursor = conn.cursor()
                                        cursor.execute("""
                                            INSERT INTO auditorias_supervisor (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, qtd_sistema, qtd_auditada, diferenca, etiqueta_correta, localizacao_correta, supervisor, data_hora, recontagem_3, ativo)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Sim', ?)
                                        """, (id_inv_sup_atual, match_linha['id_estoque'] if 'id_estoque' in match_linha else "N/I", match_linha['desc_estoque'], material_recontar, match_linha['desc_produto'], int(match_linha['qtd_sistema']), q_real_3, dif_3, etiq_3, local_3, st.session_state.operador, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ativo_3_l))
                                        conn.commit()
                                        st.success("✅ 3ª Contagem gravada com sucesso!")
                                        st.rerun()
                        else:
                            st.success("🎉 Nenhuma divergência operacional encontrada.")

                    st.markdown("---")
                    
                    st.write("### 🔐 Relatório de Fechamento Amostral Ativo")
                    if not df_auditorias_atual.empty:
                        total_sup = len(df_auditorias_atual)
                        certos_qtd = len(df_auditorias_atual[df_auditorias_atual['diferenca'] == 0])
                        certos_etiq = len(df_auditorias_atual[df_auditorias_atual['etiqueta_correta'] == "Sim"])
                        certos_local = len(df_auditorias_atual[df_auditorias_atual['localizacao_correta'] == "Sim"])
                        
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("🎯 SALDO CORRETO", f"{(certos_qtd / total_sup)*100:.1f}%")
                        m2.metric("🏷️ ETIQUETAS OK", f"{(certos_etiq / total_sup)*100:.1f}%")
                        m3.metric("📍 LOCALIZAÇÃO OK", f"{(certos_local / total_sup)*100:.1f}%")
                        m4.metric("📋 AMOSTRAS BIPIADAS", f"{total_sup} itens")
                        
                        st.write("### 📝 Amostras Coletadas Correntes")
                        st.dataframe(df_auditorias_atual, use_container_width=True, hide_index=True)
                else:
                    st.markdown(f"""
                        <div class="pasta-secao" style="border-left-color: #27ae60; background-color: #e8f8f5;">
                            <h4 style="margin: 0; color: #1e8449;">🔓 Relatório de Fechamento Amostral Ativo (Código: {id_inv_sup_atual})</h4>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if df_auditorias_atual.empty:
                        st.info("Nenhuma amostragem registrada nesta pasta encerrada.")
                    else:
                        st.dataframe(df_auditorias_atual, use_container_width=True, hide_index=True)

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
        
        st.write("### 🔬 Histórico de Auditorias Exclusivas do Supervisor")
        
        if df_inventarios_sup.empty:
            st.info("Nenhum histórico amostral arquivado.")
        else:
            st.write("#### 📅 Filtrar Pastas do Supervisor por Período de Abertura")
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
            
            if df_sup_filtrados.empty:
                st.warning("⚠️ Nenhum histórico do supervisor foi localizado neste intervalo de datas.")
            else:
                tam_pagina_sup = 15
                total_itens_sup = len(df_sup_filtrados)
                total_paginas_sup = (total_itens_sup - 1) // tam_pagina_sup + 1
                
                if st.session_state.pagina_historico_sup >= total_paginas_sup:
                    st.session_state.pagina_historico_sup = 0
                    
                idx_ini_sup = st.session_state.pagina_historico_sup * tam_pagina_sup
                idx_fim_sup = idx_ini_sup + tam_pagina_sup
                
                df_pagina_sup_atual = df_sup_filtrados.iloc[idx_ini_sup:idx_fim_sup]
                
                st.write(f"Exibindo do **{idx_ini_sup + 1}º** ao **{min(idx_fim_sup, total_itens_sup)}º** inventário amostral (Total de {total_itens_sup} pastas do supervisor).")
                
                for idx, inv_s in df_pagina_sup_atual.iterrows():
                    df_hist_sup = pd.read_sql_query("SELECT * FROM auditorias_supervisor WHERE inventario_id = ? ORDER BY id DESC", conn, params=(inv_s['id'],))
                    
                    c_exp, c_del = st.columns([8, 2])
                    with c_exp:
                        with st.expander(f"📁 {inv_s['id']} – {inv_s['nome']} | {inv_s['data']} | {len(df_hist_sup)} itens auditados"):
                            if not df_hist_sup.empty:
                                excel_sup_hist = converter_para_excel(df_hist_sup)
                                st.download_button(label="📥 Baixar Pasta em Excel", data=excel_sup_hist, file_name=f"auditoria_{inv_s['id']}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_sup_{inv_s['id']}")
                                st.dataframe(df_hist_sup, use_container_width=True, hide_index=True)
                    with c_del:
                        if eh_supervisor:
                            if st.button("🗑️ Deletar Pasta", key=f"del_folder_sup_{inv_s['id']}", use_container_width=True):
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM inventarios_supervisor WHERE id = ?", (inv_s['id'],))
                                cursor.execute("DELETE FROM auditorias_supervisor WHERE inventario_id = ?", (inv_s['id'],))
                                conn.commit()
                                st.success("Pasta deletada!")
                                st.rerun()
                                
                st.markdown("---")
                col_p_sup1, col_p_sup_txt, col_p_sup2 = st.columns([2, 6, 2])
                with col_p_sup1:
                    if st.button("◀ Anterior (Supervisor)", use_container_width=True, disabled=(st.session_state.pagina_historico_sup == 0)):
                        st.session_state.pagina_historico_sup -= 1
                        st.rerun()
                with col_p_sup_txt:
                    st.markdown(f"<p style='text-align: center; margin-top: 7px;'>Página <strong>{st.session_state.pagina_historico_sup + 1}</strong> de <strong>{total_paginas_sup}</strong></p>", unsafe_allow_html=True)
                with col_p_sup2:
                    if st.button("Próximo (Supervisor) ▶", use_container_width=True, disabled=(st.session_state.pagina_historico_sup >= total_paginas_sup - 1)):
                        st.session_state.pagina_historico_sup += 1
                        st.rerun()

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
                                ordem_colunas_print = ['id', 'inventario_id', 'id_estoque', 'desc_estoque', 'cod_produto', 'desc_produto', 'unid_medida', 'qtd_sistema', 'qtd_contada', 'diferenca', 'ativo', 'observacao', 'operador', 'data_hora']
                                if 'lote' in colunas_existentes_hist:
                                    ordem_colunas_print.append('lote')
                                    
                                st.write("**📋 Itens Efetivamente Contados:**")
                                st.dataframe(df_hist_inv[ordem_colunas_print], use_container_width=True, hide_index=True)
                                
                            if st.session_state.base_sistema is not None:
                                set_contados_global = set(df_hist_inv['cod_produto'].astype(str).str.upper().str.strip().tolist())
                                esquecidos_linhas = []
                                for _, row_b in st.session_state.base_sistema.iterrows():
                                    c_atual = str(row_b[col_cod]).upper().strip()
                                    if c_atual not in set_contados_global:
                                        esquecidos_linhas.append({
                                            "Código Produto": c_atual,
                                            "Descrição Produto": row_b[col_desc],
                                            "Localização Prevista": row_b[col_local] if col_local in row_b else "N/I"
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
            df_base_visual["Status de Contagem"] = df_base_visual[col_cod].apply(calcular_status_linha)
            
            colunas_ordenadas = ["Status de Contagem"] + [col for col in df_base_visual.columns if col != "Status de Contagem"]
            st.dataframe(df_base_visual[colunas_ordenadas], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma base carregada na barra lateral.")

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
                    data_formatada = "Sem histórico"
            else:
                dias_passados = 999
                data_formatada = "Nunca Contado"
                
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
                "Última Contagem Realizada": data_formatada,
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
