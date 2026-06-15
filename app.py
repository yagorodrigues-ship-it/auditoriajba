import streamlit as st
import pandas as pd
import datetime
import sqlite3
import io

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
            data_hora TEXT
        )
    """)
    
    conn.commit()
    conn.close()

inicializar_banco()

# --- CARREGAMENTO SEGURO DOS INVENTÁRIOS (PREVINE NAMEERROR) ---
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

def limpar_documento(doc):
    return str(doc).strip().replace(".", "").replace("-", "").replace("/", "")

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
        st.title("🔑 Redefinição de Senha")
        with st.form("rec_form"):
            validador = st.text_input("Informe seu E-mail ou CPF cadastrado")
            nova_senha_rec = st.text_input("Nova Senha", type="password")
            btn_rec = st.form_submit_button("Alterar Senha", type="primary", use_container_width=True)
            if btn_rec:
                v_limpo = validador.strip()
                v_doc = limpar_documento(v_limpo)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM usuarios WHERE email = ? OR cpf = ?", (v_limpo, v_doc))
                row = cursor.fetchone()
                if row and nova_senha_rec:
                    cursor.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (nova_senha_rec, row[0]))
                    conn.commit()
                    st.success("✅ Senha alterada!")
                    st.session_state.tela_acesso = "login"
                    st.rerun()
                else:
                    st.error("❌ Identificador inválido.")
        if st.button("◀ Voltar"):
            st.session_state.tela_acesso = "login"
            st.rerun()
    conn.close()

# --- TELA LOGADA DO SISTEMA ---
else:
    conn = conectar_banco()
    
    # Atualiza os dataframes em tempo real após o login
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios ORDER BY data DESC, id DESC", conn)
    df_inventarios_sup = pd.read_sql_query("SELECT * FROM inventarios_supervisor ORDER BY data DESC, id DESC", conn)
    
    nome_usuario_logado_limpo = st.session_state.operador.lower()
    eh_supervisor = any(x in nome_usuario_logado_limpo for x in ["yago rodrigues", "administrador", "admin", "supervisor"])
    
    id_inventario_atual_inicial = df_inventarios.iloc[0]['id'].replace('#','') if not df_inventarios.empty else ""
    
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
            inventario_selecionado_obj = None
        else:
            lista_inv = [f"{row['id']} – {row['nome']} ({row['status']})" for idx, row in df_inventarios.iterrows()]
            inventario_selected = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
            id_inventario_atual = inventario_selected.split(" – ")[0]
            inventario_selecionado_obj = df_inventarios[df_inventarios['id'] == id_inventario_atual].iloc[0]

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

        if inventario_selecionado_obj is not None and inventario_selecionado_obj['status'] == "Aberto":
            if st.button("🔒 Fechar inventário atual", use_container_width=True):
                cursor = conn.cursor()
                cursor.execute("UPDATE inventarios SET status = 'Fechado' WHERE id = ?", (id_inventario_atual,))
                conn.commit()
                st.rerun()

        # --- MAPEAMENTO DE COLUNAS ---
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

        # --- PROGRESSO LATERAL (FILTRADO POR OPERADOR PARA NÃO CONFUNDIR) ---
        total_itens_base, total_contados, total_pendentes, progresso = 0, 0, 0, 0.0
        if st.session_state.base_sistema is not None and id_inventario_atual is not None:
            total_itens_base = len(st.session_state.base_sistema)
            
            # Mudança crucial: a barra lateral do funcionário só conta o progresso DELE
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

    # ABAS DO PAINEL PRINCIPAL
    abas = ["🔍 Contar Item", "📊 Contagem Atual", "🔬 Painel Supervisor", "📈 Acuracidade Estoque", "📁 Histórico Geral", "📄 Base de Estoque", "🏆 Desempenho"]
    aba_contar, aba_atual, aba_supervisor, aba_acuracidade, aba_historico_geral, aba_base, aba_graficos = st.tabs(abas)
    
    # --- ABA 1: CONTAR ITEM (FUNCIONÁRIOS) ---
    with aba_contar:
        if id_inventario_atual is None or st.session_state.base_sistema is None:
            st.warning("⚠️ Carregue a base de saldo e crie um inventário na barra lateral.")
        elif inventario_selecionado_obj['status'] == "Fechado":
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
                                    INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, observacao, operador, data_hora, lote)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (id_inventario_atual.replace("#",""), id_estoque_val, local_val, codigo_rastreio, desc_val, unid_val, qtd_sis, qtd_fisica, dif_c, ativo_l, observacao, st.session_state.operador, agora, lote_val))
                                conn.commit()
                                st.session_state.ultimo_item_sucesso = f"✅ Lançamento Efetuado com sucesso!"
                                st.session_state.contador_reset += 1
                                st.rerun()
                else:
                    st.error("❌ Código não localizado.")

    # --- ABA 2: CONTAGEM ATUAL (ISOLADA POR OPERADOR CONCORRENTE) ---
    with aba_atual:
        if id_inventario_atual:
            st.subheader(f"Painel Operacional – {id_inventario_atual} ({inventario_selecionado_obj['nome']})")
            
            # BLINDAGEM ANTI-CONCORRÊNCIA: 
            # Funcionários enxergam estritamente o seu login. O Supervisor pode optar por ver o global.
            modo_visao = "Apenas Minhas Contagens"
            if eh_supervisor:
                modo_visao = st.radio("Filtro de Visualização (Exclusivo Supervisor):", ["Apenas Minhas Contagens", "Ver Tudo (Todos os Operadores Simultâneos)"], horizontal=True)

            if modo_visao == "Apenas Minhas Contagens":
                df_contagens_mutaveis = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? AND operador = ? ORDER BY id DESC", conn, params=(id_inventario_atual.replace('#',''), st.session_state.operador))
            else:
                df_contagens_mutaveis = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? ORDER BY id DESC", conn, params=(id_inventario_atual.replace('#',''),))

            if df_contagens_mutaveis.empty:
                st.info("Nenhum item foi lançado por você neste inventário corrente ainda.")
            else:
                total_auditado = len(df_contagens_mutaveis)
                itens_divergentes = len(df_contagens_mutaveis[df_contagens_mutaveis['diferenca'] != 0])
                soma_contada = int(df_contagens_mutaveis['qtd_contada'].sum())
                soma_sistema = int(df_contagens_mutaveis['qtd_sistema'].sum())
                diferenca_acumulada = int(df_contagens_mutaveis['diferenca'].sum())
                porcentagem_divergencia = (itens_divergentes / total_auditado) * 100 if total_auditado > 0 else 0
                
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">📦 ITENS CONTADOS</div><div class="bloco-valor">{total_auditado}</div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">⚠️ COM DIVERGÊNCIA</div><div class="bloco-valor">{itens_divergentes}</div></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">🔢 QTD TOTAL CONTADA</div><div class="bloco-valor">{soma_contada}</div></div>', unsafe_allow_html=True)
                with c4: st.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:0px;"><div class="bloco-titulo">🗄️ QTD TOTAL SISTEMA</div><div class="bloco-valor">{soma_sistema} <span style="font-size:14px; color:#e74c3c;">(Dif: {diferenca_acumulada})</span></div></div>', unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div class="alerta-divergencia">
                        <strong>⚠️ {itens_divergentes} item(ns) apresentando divergência nesta visão ({porcentagem_divergencia:.0f}%)</strong>
                    </div>
                """, unsafe_allow_html=True)
                
                excel_atual = converter_para_excel(df_contagens_mutaveis)
                st.download_button(label="📥 Exportar Lançamentos Filtrados para Excel", data=excel_atual, file_name=f"contagem_{id_inventario_atual}_{st.session_state.operador}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                st.write("")

                ordem_colunas_print = ['id', 'inventario_id', 'id_estoque', 'desc_estoque', 'cod_produto', 'desc_produto', 'unid_medida', 'qtd_sistema', 'qtd_contada', 'diferenca', 'ativo', 'observacao', 'operador', 'data_hora']
                st.dataframe(df_contagens_mutaveis[ordem_colunas_print], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum inventário selecionado.")

    # --- ABA 3: PAINEL SUPERVISOR ---
    with aba_supervisor:
        st.title("🔬 Controle de Qualidade Amostral do Supervisor")
        
        if not eh_supervisor:
            st.error("🚫 Acesso restrito. Esta tela só pode ser operada pelo Administrador/Supervisor (Acesso Liberado para Yago Rodrigues).")
        else:
            st.subheader("📁 Controle de Inventários do Supervisor")
            col_sel, col_btn = st.columns([7, 3])
            
            with col_sel:
                if df_inventarios_sup.empty:
                    st.info("Nenhum inventário de amostragem aberto. Crie um ao lado.")
                    id_inv_sup_atual = None
                    inv_sup_selecionado_obj = None
                else:
                    lista_inv_sup = [f"{r['id']} – {r['nome']} ({r['status']})" for idx, r in df_inventarios_sup.iterrows()]
                    inv_sup_selected = st.selectbox("Selecione a sua Auditoria Amostral", lista_inv_sup, key="sel_box_sup_local")
                    id_inv_sup_atual = inv_sup_selected.split(" – ")[0]
                    inv_sup_selecionado_obj = df_inventarios_sup[df_inventarios_sup['id'] == id_inv_sup_atual].iloc[0]
            
            with col_btn:
                with st.popover("➕ Novo Inventário Supervisor", use_container_width=True):
                    with st.form("form_novo_sup_interno", clear_on_submit=True):
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

            if id_inv_sup_atual:
                df_auditorias_atual = pd.read_sql_query("SELECT * FROM auditorias_supervisor WHERE inventario_id = ? ORDER BY id DESC", conn, params=(id_inv_sup_atual,))
                
                if inv_sup_selecionado_obj['status'] == "Aberto":
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

                    if st.session_state.base_supervisor is None:
                        st.warning("⚠️ Faça o upload da planilha de amostragem abaixo para liberar a bipagem.")
                    else:
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
                                        
                                    if st.form_submit_button("💾 Salvar Auditoria", type="primary", use_container_width=True):
                                        dif_sup = qtd_aud_sup - qtd_sis_sup
                                        cursor = conn.cursor()
                                        cursor.execute("""
                                            INSERT INTO auditorias_supervisor (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, qtd_sistema, qtd_auditada, diferenca, etiqueta_correta, localizacao_correta, supervisor, data_hora)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        """, (id_inv_sup_atual, id_est_sup, local_sup, cod_sup, desc_sup, qtd_sis_sup, qtd_aud_sup, dif_sup, etiq_status, local_status, st.session_state.operador, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                        conn.commit()
                                        st.session_state.contador_reset_sup += 1
                                        st.rerun()

                    if not df_auditorias_atual.empty:
                        st.write("### 📝 Amostras Coletadas Correntes")
                        st.dataframe(df_auditorias_atual, use_container_width=True, hide_index=True)
                else:
                    st.markdown(f"""
                        <div class="pasta-secao" style="border-left-color: #27ae60; background-color: #e8f8f5;">
                            <h4 style="margin: 0; color: #1e8449;">🔓 Relatório de Fechamento Amostral Ativo (Código: {id_inv_sup_atual})</h4>
                            <p style="margin: 5px 0 0 0; font-size: 13px; color: #234d20;">Exibindo o balanço de auditoria consolidado e as divergências encontradas pelo Supervisor.</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if df_auditorias_atual.empty:
                        st.info("Nenhuma amostragem registrada nesta pasta encerrada.")
                    else:
                        df_sup_divergencias = df_auditorias_atual[df_auditorias_atual['diferenca'] != 0]
                        st.write(f"### 📋 Todas as Amostras Auditadas ({len(df_auditorias_atual)} itens)")
                        st.dataframe(df_auditorias_atual, use_container_width=True, hide_index=True)
                        st.write(f"### ⚠️ Filtro de Divergências Encontradas pelo Supervisor ({len(df_sup_divergencias)} erros)")
                        if df_sup_divergencias.empty:
                            st.success("🎉 Nenhuma divergência de saldo foi encontrada nas amostras desse estoque!")
                        else:
                            st.dataframe(df_sup_divergencias, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("📤 Upload da Planilha de Amostragem do Supervisor")
            arquivo_supervisor = st.file_uploader("Suba a planilha Excel para a amostragem do supervisor (.xlsx)", type=["xlsx"], key="sup_unified_excel_loader_final")
            if arquivo_supervisor is not None and st.session_state.base_supervisor is None:
                st.session_state.base_supervisor = pd.read_excel(arquivo_supervisor)
                st.session_state.nome_arquivo_supervisor = arquivo_supervisor.name
                st.rerun()
            if st.session_state.base_supervisor is not None:
                st.info(f"📂 **Base Ativa do Supervisor:** {st.session_state.nome_arquivo_supervisor}")
                if st.button("🗑️ Remover Planilha"):
                    st.session_state.base_supervisor = None
                    st.session_state.nome_arquivo_supervisor = ""
                    st.rerun()

    # --- ABA 4: ACURACIDADE ESTOQUE ---
    with aba_acuracidade:
        st.title("📈 Acuracidade - Controle Amostral")
        
        st.write("### 📊 Pasta de Acuracidade de Amostragens (Métricas por Depósito)")
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
            for idx, inv_s in df_inventarios_sup.iterrows():
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

    # --- ABA 5: HISTÓRICO GERAL ---
    with aba_historico_geral:
        st.title("📁 Arquivo Geral de Movimentações")
        st.write("Abaixo consta a listagem completa de contagens e lançamentos realizados pelas equipes operacionais em campo:")
        
        if df_inventarios.empty:
            st.info("Nenhum inventário operacional registrado no banco de dados.")
        else:
            for idx, inv in df_inventarios.iterrows():
                df_hist_inv = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? ORDER BY id DESC", conn, params=(inv['id'].replace('#',''),))
                
                c_exp_g, c_del_g = st.columns([8, 2])
                with c_exp_g:
                    with st.expander(f"📁 {inv['id']} – {inv['nome']} | Data Inicial: {inv['data']} | Status: {inv['status']} ({len(df_hist_inv)} itens lançados)"):
                        if not df_hist_inv.empty:
                            excel_geral_hist = converter_para_excel(df_hist_inv)
                            st.download_button(label="📥 Baixar Lançamentos em Excel", data=excel_geral_hist, file_name=f"inventario_geral_{inv['id']}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_ger_{inv['id']}")
                            ordem_colunas_print = ['id', 'inventario_id', 'id_estoque', 'desc_estoque', 'cod_produto', 'desc_produto', 'unid_medida', 'qtd_sistema', 'qtd_contada', 'diferenca', 'ativo', 'observacao', 'operador', 'data_hora']
                            st.dataframe(df_hist_inv[ordem_colunas_print], use_container_width=True, hide_index=True)
                with c_del_g:
                    if eh_supervisor:
                        if st.button("🗑️ Deletar Pasta", key=f"del_folder_ger_{inv['id']}", use_container_width=True):
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM inventarios WHERE id = ?", (inv['id'],))
                            cursor.execute("DELETE FROM contagens WHERE inventario_id = ?", (inv['id'].replace('#',''),))
                            conn.commit()
                            st.success("Pasta operacional excluída!")
                            st.rerun()

    # --- ABA 6: BASE DE ESTOQUE ---
    with aba_base:
        if st.session_state.base_sistema is not None:
            st.dataframe(st.session_state.base_sistema, use_container_width=True)
        else:
            st.info("Nenhuma base carregada.")

    # --- ABA 7: DESEMPENHO ---
    with aba_graficos:
        st.write("### 🏆 Ranking de Lançamentos por Operador")
        df_ops = pd.read_sql_query("SELECT operador as Operador, COUNT(id) as [Lançamentos Feitos] FROM contagens GROUP BY operador", conn)
        if not df_ops.empty:
            st.bar_chart(data=df_ops, x='Operador', y='Lançamentos Feitos', color="#d35400")
            
    conn.close()
