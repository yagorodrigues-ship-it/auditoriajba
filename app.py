import streamlit as st
import pandas as pd
import datetime
import sqlite3
import io
import base64
import os
import re

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
            lote TEXT DEFAULT '',
            ativo TEXT DEFAULT ''
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
    
    # --- GARANTIA ABSOLUTA DE ADMIN PADRÃO ---
    cursor.execute("SELECT * FROM usuarios WHERE email = 'admin@tel.com.br'")
    if cursor.fetchone() is None:
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

def obter_ativos_lancados_com_seguranca(conn, inventario_id, cod_produto, lote=None):
    try:
        if lote:
            df = pd.read_sql_query("SELECT ativo FROM contagens WHERE inventario_id = ? AND cod_produto = ? AND lote = ?", conn, params=(inventario_id, cod_produto, lote))
        else:
            df = pd.read_sql_query("SELECT ativo FROM contagens WHERE inventario_id = ? AND cod_produto = ?", conn, params=(inventario_id, cod_produto))
        
        if not df.empty and 'ativo' in df.columns:
            return set(df['ativo'].dropna().astype(str).str.strip().upper().tolist())
    except:
        pass
    return set()

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
    .bloco-titulo { color: #7f8c8d; font-size: 11px; font-weight: bold; letter-spacing: 0.5px; }
    .bloco-valor { color: #1b4f72; font-size: 24px; font-weight: bold; }
    .card-sistema { background-color: #ebf5fb; padding: 20px; border-radius: 8px; border: 1px solid #d4e6f1; margin-top: 15px; margin-bottom: 25px; }
    .card-lateral { background-color: #1a233a; padding: 12px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #2563eb; }
    .card-lateral-titulo { color: #93c5fd; font-size: 11px; font-weight: bold; }
    .card-lateral-valor { color: white; font-size: 28px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- GERENCIAMENTO DE ESTADO ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'base_sistema' not in st.session_state: st.session_state.base_sistema = None
if 'base_supervisor' not in st.session_state: st.session_state.base_supervisor = None
if 'nome_arquivo_excel' not in st.session_state: st.session_state.nome_arquivo_excel = ""
if 'nome_arquivo_supervisor' not in st.session_state: st.session_state.nome_arquivo_supervisor = ""
if 'operador' not in st.session_state: st.session_state.operador = ""
if 'tela_acesso' not in st.session_state: st.session_state.tela_acesso = "login"
if 'contador_reset' not in st.session_state: st.session_state.contador_reset = 0
if 'contador_reset_sup' not in st.session_state: st.session_state.contador_reset_sup = 0
if 'ultimo_item_sucesso' not in st.session_state: st.session_state.ultimo_item_sucesso = ""
if 'pagina_historico' not in st.session_state: st.session_state.pagina_historico = 0
if 'pagina_historico_sup' not in st.session_state: st.session_state.pagina_historico_sup = 0

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
    conn.close()

# --- TELA LOGADA DO SISTEMA ---
else:
    conn = conectar_banco()
    
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios ORDER BY data DESC, id DESC", conn)
    df_inventarios_sup = pd.read_sql_query("SELECT * FROM inventarios_supervisor ORDER BY data DESC, id DESC", conn)
    
    st.session_state.operador = st.session_state.get('operador', 'Operador Genérico')
    eh_supervisor = any(x in st.session_state.operador.lower() for x in ["yago", "administrador", "admin", "supervisor"])
    
    # SIDEBAR
    with st.sidebar:
        st.write(f"👤 **Operador Ativo:** {st.session_state.operador}")
        if st.button("🔄 Atualizar Dados", use_container_width=True): st.rerun()
        if st.button("🚪 Sair da Conta", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.operador = ""
            st.session_state.tela_acesso = "login"
            st.rerun()
            
        st.markdown("---")
        with st.expander("➕ Novo Inventário"):
            with st.form("form_novo", clear_on_submit=True):
                novo_nome = st.text_input("Nome do Inventário")
                if st.form_submit_button("Criar", type="primary") and novo_nome:
                    maior_id = 0
                    if not df_inventarios.empty:
                        ids_nums = df_inventarios['id'].astype(str).str.extract(r'(\d+)').dropna().astype(int)
                        if not ids_nums.empty:
                            maior_id = ids_nums.max().iloc[0]
                    novo_id = f"#{maior_id + 1}"
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO inventarios (id, nome, data, status) VALUES (?, ?, ?, 'Aberto')", (novo_id, novo_nome, datetime.date.today().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.rerun()

        st.write("📁 **Selecione o inventário**")
        if df_inventarios.empty:
            st.info("Crie um inventário.")
            id_inventario_atual = None
            inventario_selected_obj = None
        else:
            lista_inv = [f"{row['id']} – {row['nome']} ({row['status']})" for idx, row in df_inventarios.iterrows()]
            inventario_selected = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
            
            match_id_num = re.search(r'#(\d+)', inventario_selected)
            id_inventario_atual = match_id_num.group(1) if match_id_num else None
            inventario_selected_obj = df_inventarios[df_inventarios['id'].str.replace('#', '', regex=False) == id_inventario_atual].iloc[0] if id_inventario_atual else None

        if id_inventario_atual:
            id_pasta_limpo_base = id_inventario_atual
            df_base_persistida = pd.read_sql_query("SELECT cod_produto, desc_produto, desc_estoque_fisico, unid_medida, qtd_estoque, id_estoque_fisico, lote, ativo FROM itens_base_inventario WHERE inventario_id = ?", conn, params=(id_pasta_limpo_base,))
            if not df_base_persistida.empty:
                st.session_state.base_sistema = df_base_persistida.rename(columns={'desc_estoque_fisico': 'descestoquefisico', 'id_estoque_fisico': 'idestoquefísico'})
            else:
                st.session_state.base_sistema = None

        st.write("📂 **Carregar Base de Dados (Funcionários)**")
        arquivo_excel = st.file_uploader("Suba o arquivo Excel (.xlsx)", type=["xlsx"], label_visibility="collapsed", key="func_excel_loader")
        if arquivo_excel is not None and id_inventario_atual:
            df_upload_temp = pd.read_excel(arquivo_excel)
            colunas_temp = list(df_upload_temp.columns)
            
            def encontrar_col_nome(opcoes, default_idx):
                for opcao in opcoes:
                    for col in colunas_temp:
                        if opcao.lower().replace(" ", "").replace(".", "") in col.lower().replace(" ", "").replace(".", ""):
                            return col
                return colunas_temp[default_idx] if default_idx < len(colunas_temp) else colunas_temp[0]

            c_cod_u = encontrar_col_nome(['códproduto', 'codproduto', 'codigo', 'cod'], 0)
            c_desc_u = encontrar_col_nome(['descproduto', 'descricao', 'desc'], 1)
            c_local_u = encontrar_col_nome(['descestoquefisico', 'localizacao', 'local', 'estoquefisico'], 2)
            c_unid_u = encontrar_col_nome(['unidmedida', 'unidade', 'un'], 3)
            c_qtd_u = encontrar_col_nome(['qtdestoque', 'quantidade', 'saldo', 'qtd'], -1)
            c_id_est_u = encontrar_col_nome(['idestoquefísico', 'idestoqfísico', 'idestoque', 'codestoque'], 0)
            c_lote_u = encontrar_col_nome(['lote'], 0)
            c_ativo_u = encontrar_col_nome(['ativo', 'nº ativo', 'numero ativo'], 0)

            cursor_db = conn.cursor()
            cursor_db.execute("DELETE FROM itens_base_inventario WHERE inventario_id = ?", (id_pasta_limpo_base,))
            
            for _, r in df_upload_temp.iterrows():
                lote_item_v = str(r[c_lote_u]).strip() if c_lote_u in df_upload_temp.columns and pd.notna(r[c_lote_u]) else ""
                ativo_item_v = str(r[c_ativo_u]).strip() if c_ativo_u in df_upload_temp.columns and pd.notna(r[c_ativo_u]) else ""
                cursor_db.execute("""
                    INSERT INTO itens_base_inventario (inventario_id, cod_produto, desc_produto, desc_estoque_fisico, unid_medida, qtd_estoque, id_estoque_fisico, lote, ativo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (id_pasta_limpo_base, str(r[c_cod_u]).strip(), str(r[c_desc_u]), str(r[c_local_u]), str(r[c_unid_u]), int(pd.to_numeric(r[c_qtd_u], errors='coerce') or 0), str(r[c_id_est_u]).strip(), lote_item_v, ativo_item_v))
            conn.commit()
            st.rerun()

        # PROGRESSO LATERAL
        total_itens_base, total_contados, total_pendentes, progresso = 0, 0, 0, 0.0
        if st.session_state.base_sistema is not None and id_inventario_atual:
            total_itens_base = len(st.session_state.base_sistema)
            df_contagens_atuais_side = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ?", conn, params=(id_inventario_atual,))
            contados_validos_set = set(df_contagens_atuais_side['cod_produto'].astype(str).str.upper().str.strip().tolist()) if not df_contagens_atuais_side.empty else set()
            total_contados = len(df_contagens_atuais_side)
            total_pendentes = max(0, total_itens_base - len(contados_validos_set))
            if total_itens_base > 0: progresso = min(1.0, len(contados_validos_set) / total_itens_base)

        st.markdown("---")
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">📋 ITENS NA BASE</div><div class="card-lateral-valor">{total_itens_base}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">✅ LANÇAMENTOS GERAIS</div><div class="card-lateral-valor">{total_contados}</div></div>', unsafe_allow_html=True)
        st.write("**PROGRESSO GLOBAL**")
        st.progress(progresso)

    abas = ["🔍 Contar Item", "📊 Contagem Atual", "🔬 Painel Supervisor", "📈 Acuracidade Estoque", "📁 Histórico Geral", "📄 Base de Estoque"]
    aba_contar, aba_atual, aba_supervisor, aba_acuracidade, aba_historico_geral, aba_base = st.tabs(abas)
    
    # --- ABA 1: CONTAR ITEM ---
    with aba_contar:
        if id_inventario_atual is None or st.session_state.base_sistema is None:
            st.warning("⚠️ Mapeie o inventário e faça o upload da base na barra lateral para liberar a digitação.")
        elif inventario_selected_obj is not None and inventario_selected_obj['status'] == "Fechado":
            st.error("🔒 Este inventário operacional está Fechado.")
        else:
            c_busca, c_filtro, c_limpar = st.columns([5, 3, 2])
            with c_busca:
                codigo_input = st.text_input("💻 Digite/Bipe o Código do Produto ou o número do Ativo", value="", placeholder="Bipe a etiqueta aqui...", key=f"bip_{st.session_state.contador_reset}")
            with c_filtro: st.selectbox("📍 Estoque Físico", ["Todos"], key=f"f_{st.session_state.contador_reset}")
            with c_limpar:
                st.write("")
                if st.button("🗑️ Limpar", use_container_width=True):
                    st.session_state.contador_reset += 1
                    st.rerun()
                    
            if codigo_input:
                busca_limpa = str(codigo_input).upper().strip()
                codigo_rastreio = busca_limpa.split(" - ")[-1].strip() if " - " in busca_limpa else busca_limpa
                id_pasta_limpo = id_inventario_atual
                
                # Procura por ativo
                df_busca_por_ativo = st.session_state.base_sistema[st.session_state.base_sistema['ativo'].astype(str).str.upper().str.strip() == codigo_rastreio]
                ativo_bipado_direto = None
                if not df_busca_por_ativo.empty:
                    ativo_bipado_direto = codigo_rastreio
                    codigo_rastreio = str(df_busca_por_ativo.iloc[0]['cod_produto']).upper().strip()
                
                itens_filtrados = st.session_state.base_sistema[st.session_state.base_sistema['cod_produto'].astype(str).str.upper().str.strip() == codigo_rastreio]
                
                if not itens_filtrados.empty:
                    lotes_totais = itens_filtrados['lote'].dropna().astype(str).str.strip().unique().tolist()
                    lotes_disponiveis = []
                    for l in lotes_totais:
                        df_ativos_do_lote = itens_filtrados[itens_filtrados['lote'].astype(str).str.strip() == l]
                        
                        # --- FIX BLINDAGEM COMPACTA PYTHON PURO PARA AS LINHAS 411 A 420 ---
                        # Remove a conversão do Pandas .str que causava AttributeError em DataFrames sem colunas de ativos preenchidas
                        col_verif_ativo = next((c for c in df_ativos_do_lote.columns if str(c).strip().lower() in ['ativo', 'nº ativo', 'numero ativo']), None)
                        if col_verif_ativo is not None and col_verif_ativo in df_ativos_do_lote.columns and not df_ativos_do_lote.empty:
                            lista_bruta_ativos = df_ativos_do_lote[col_verif_ativo].dropna().tolist()
                            ativos_lote_set = {str(val).strip().upper() for val in lista_bruta_ativos if str(val).strip() != ""}
                        else:
                            ativos_lote_set = set()
                            
                        assets_lancados_set = obter_ativos_lancados_com_seguranca(conn, id_pasta_limpo, codigo_rastreio, l)
                        if len(ativos_lote_set - assets_lancados_set) > 0 or len(ativos_lote_set) == 0:
                            lotes_disponiveis.append(l)

                    lote_selecionado = ""
                    if ativo_bipado_direto:
                        lote_selecionado = str(df_busca_por_ativo.iloc[0]['lote']).strip()
                        linhas_filtradas_por_lote = itens_filtrados[itens_filtrados['lote'].astype(str).str.strip() == lote_selecionado]
                    elif lotes_disponiveis:
                        lote_selecionado = st.selectbox("👇 SELECIONE O LOTE PARA CONTAGEM:", lotes_disponiveis, key="lote_selector_bip")
                        linhas_filtradas_por_lote = itens_filtrados[itens_filtrados['lote'].astype(str).str.strip() == lote_selecionado]
                    else:
                        linhas_filtradas_por_lote = itens_filtrados

                    col_orig_ativo = next((c for c in itens_filtrados.columns if str(c).strip().upper() in ["ATIVO", "Nº ATIVO", "NUMERO ATIVO"]), None)
                    ativos_do_lote_lista = linhas_filtradas_por_lote[col_orig_ativo].dropna().astype(str).str.strip().unique().tolist() if col_orig_ativo else []
                    set_ativos_lancados = obter_ativos_lancados_com_seguranca(conn, id_pasta_limpo, codigo_rastreio, lote_selecionado)
                    ativos_filtrados_restantes = [a for a in ativos_do_lote_lista if str(a).strip().upper() not in set_ativos_lancados]

                    ativo_selecionado = ""
                    ja_contado_aviso = False

                    if ativo_bipado_direto:
                        if ativo_bipado_direto in set_ativos_lancados: ja_contado_aviso = True
                        else: ativo_selecionado = ativo_bipado_direto
                        item_especifico = df_busca_por_ativo.iloc[0]
                    elif len(ativos_filtrados_restantes) > 1:
                        ativo_selecionado = st.selectbox("👇 SELECIONE O ATIVO PARA CONTAGEM:", ativos_filtrados_restantes, key="ativo_selector_bip")
                        item_especifico = linhas_filtradas_por_lote[linhas_filtradas_por_lote[col_orig_ativo].astype(str).str.strip() == ativo_selecionado].iloc[0]
                    elif len(ativos_filtrados_restantes) == 1:
                        ativo_selecionado = ativos_filtrados_restantes[0]
                        item_especifico = linhas_filtradas_por_lote[linhas_filtradas_por_lote[col_orig_ativo].astype(str).str.strip() == ativo_selecionado].iloc[0]
                    else:
                        item_especifico = linhas_filtradas_por_lote.iloc[0]

                    unid_val = item_especifico['unid_medida'] if 'unid_medida' in itens_filtrados.columns else "UN"
                    desc_val = item_especifico['desc_produto']
                    local_val = item_especifico['descestoquefisico']
                    id_estoque_val = str(item_especifico['idestoquefísico']).strip()
                    qtd_sys = int(item_especifico['qtd_estoque']) if 'qtd_estoque' in item_especifico else 0

                    b1, b2, b3, b4 = st.columns(4)
                    b1.markdown(f'<div class="bloco-info"><div class="bloco-titulo">CÓD. PRODUTO</div><div class="bloco-valor">{codigo_rastreio}</div></div>', unsafe_allow_html=True)
                    b2.markdown(f'<div class="bloco-info"><div class="bloco-titulo">ESTOQUE FÍSICO</div><div class="bloco-valor">{local_val}</div></div>', unsafe_allow_html=True)
                    b3.markdown(f'<div class="bloco-info"><div class="bloco-titulo">UNID. MEDIDA</div><div class="bloco-valor">{unid_val}</div></div>', unsafe_allow_html=True)
                    b4.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:0px;"><div class="bloco-titulo">LOTE EM CONTAGEM</div><div class="bloco-valor" style="color:#d35400;">{lote_selecionado if lote_selecionado else "Padrão"}</div></div>', unsafe_allow_html=True)
                    
                    st.markdown(f"**Descrição do Material:** {desc_val}")
                    
                    if ja_contado_aviso:
                        st.error(f"🚨 Atenção: O Ativo **{ativo_bipado_direto}** já foi bipado anteriormente neste inventário!")
                    else:
                        st.success(f"🎯 Ativo **{ativo_selecionado if ativo_selecionado else 'Padrão'}** e Lote **{lote_selecionado if lote_selecionado else 'Padrão'}** reconhecidos com sucesso via bipagem direta!")
                        
                        with st.form("confirmar_form", clear_on_submit=True):
                            qtd_fisica = st.number_input("📦 Quantidade contada fisicamente (Obrigatório)", min_value=0, step=1, value=1 if ativo_bipado_direto else 0)
                            ativo_final_input = ativo_selecionado if (len(ativos_filtrados_restantes) > 1 or ativo_bipado_direto) else st.text_input("🔢 Número do Ativo (Opcional)", value=ativo_selecionado)
                            observacao = st.text_input("📝 Observação (opcional)")
                            
                            if st.form_submit_button("✓ Confirmar Contagem", type="primary", use_container_width=True):
                                if qtd_fisica <= 0:
                                    st.error("❌ Erro: Informe uma quantidade maior que 0!")
                                else:
                                    cursor = conn.cursor()
                                    fase_atual = "1a Contagem" if inventario_selected_obj['status'] == "Aberto" else "2a Contagem"
                                    if fase_atual == "2a Contagem":
                                        cursor.execute("DELETE FROM contagens WHERE inventario_id = ? AND cod_produto = ? AND lote = ? AND fase_contagem = '2a Contagem'", (id_pasta_limpo, codigo_rastreio, lote_selecionado))
                                    
                                    cursor.execute("""
                                        INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, observacao, operador, data_hora, lote, fase_contagem)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (id_pasta_limpo, id_estoque_val, local_val, codigo_rastreio, desc_val, unid_val, qtd_sys, qtd_fisica, qtd_fisica - qtd_sys, str(ativo_final_input).strip().upper(), observacao, st.session_state.operador, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), lote_selecionado, fase_atual))
                                    conn.commit()
                                    st.session_state.ultimo_item_sucesso = f"📋 Lançamento efetuado com sucesso para o Ativo {ativo_final_input}!"
                                    st.session_state.contador_reset += 1
                                    st.rerun()
                else:
                    st.error("⚠️ Código ou Ativo não localizado na base deste inventário. Verifique se o arquivo correto foi importado para esta pasta.")

    # --- ABA 2: CONTAGEM ATUAL ---
    with aba_atual:
        if id_inventario_atual:
            df_contagens_mutaveis = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? ORDER BY id DESC", conn, params=(id_inventario_atual,))
            if df_contagens_mutaveis.empty:
                st.info("Nenhum item lançado até o momento.")
            else:
                st.dataframe(df_contagens_mutaveis, use_container_width=True, hide_index=True)
        else:
            st.info("Selecione um inventário.")

    # --- ABA 3: PAINEL SUPERVISOR ---
    with aba_supervisor:
        st.title("🔬 Painel de Gestão e Auditoria do Supervisor")
        if not eh_supervisor:
            st.error("🚫 Acesso restrito ao Supervisor.")
        else:
            st.subheader("🔄 Módulo ADM de Liberação de 2ª Contagem")
            df_todas_divergentes = pd.read_sql_query("SELECT * FROM contagens WHERE diferenca != 0 AND fase_contagem = '1a Contagem'", conn)
            
            if df_todas_divergentes.empty:
                st.success("🎉 Nenhuma divergência operacional pendente de tratamento nas primeiras contagens.")
            else:
                ids_com_erro = df_todas_divergentes['inventario_id'].unique().tolist()
                opcoes_pastas = [f"#{id_p}" for id_p in ids_com_erro]
                pasta_selecionada_erro = st.selectbox("📂 Escolha a pasta do inventário divergente:", opcoes_pastas, key="sb_reabrir_2a")
                id_pasta_limpo = pasta_selecionada_erro.replace("#", "")
                
                df_erros_desta_pasta = df_todas_divergentes[df_todas_divergentes['inventario_id'] == id_pasta_limpo]
                opcoes_materiais = [f"{r['cod_produto']} - {r['desc_produto']} (Lote: {r['lote']})" for _, r in df_erros_desta_pasta.iterrows()]
                material_selecionado_combo = st.selectbox("Escolha o material com erro para autorizar a 2ª Contagem:", opcoes_materiais)
                cod_material_alvo = material_selecionado_combo.split(" - ")[0]
                
                if st.button("🚨 Abrir e Liberar 2ª Contagem para Almoxarife", type="primary", use_container_width=True):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE inventarios SET status = '2a Contagem' WHERE id = ?", (f"#{id_pasta_limpo}",))
                    conn.commit()
                    st.success(f"🎉 Pasta #{id_pasta_limpo} alterada para '2a Contagem'!")
                    st.rerun()

    # --- ABA 4: ACURACIDADE ESTOQUE ---
    with aba_acuracidade:
        st.title("📈 Acuracidade - Controle Amostral do Supervisor")
        df_todas_auditorias_banco = pd.read_sql_query("SELECT * FROM auditorias_supervisor ORDER BY id DESC", conn)
        if df_todas_auditorias_banco.empty:
            st.info("💡 Nenhuma amostragem coletada no banco de dados.")
        else:
            st.dataframe(df_todas_auditorias_banco, use_container_width=True, hide_index=True)

    # --- ABA 5: HISTÓRICO GERAL (SISTEMA DE PERSISTÊNCIA VITALÍCIA) ---
    with aba_historico_geral:
        st.title("📁 Arquivo Geral de Movimentações")
        df_pastas_com_contagem = pd.read_sql_query("SELECT DISTINCT inventario_id FROM contagens", conn)
        
        if df_pastas_com_contagem.empty:
            st.info("Nenhum histórico de contagens registrado foi localizado no banco de dados.")
        else:
            lista_pastas_detectadas = []
            for _, r_p in df_pastas_com_contagem.iterrows():
                id_limpo_c = str(r_p['inventario_id']).strip()
                match_meta = df_inventarios[df_inventarios['id'].str.replace('#', '', regex=False) == id_limpo_c]
                lista_pastas_detectadas.append({
                    "id": f"#{id_limpo_c}",
                    "nome": match_meta.iloc[0]['nome'] if not match_meta.empty else f"Pasta de Saldo Geral #{id_limpo_c}",
                    "data": match_meta.iloc[0]['data'] if not match_meta.empty else "Armazenado",
                    "status": match_meta.iloc[0]['status'] if not match_meta.empty else "Histórico Permanente"
                })
            
            df_inventarios_filtrados = pd.DataFrame(lista_pastas_detectadas)
            for idx, inv in df_inventarios_filtrados.iterrows():
                id_inv_proc = inv['id'].replace('#','')
                df_hist_inv = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? ORDER BY id DESC", conn, params=(id_inv_proc,))
                
                c_exp_g, c_del_g = st.columns([8, 2])
                with c_exp_g:
                    with st.expander(f"📁 {inv['id']} – {inv['nome']} | Período: {inv['data']} | Status: {inv['status']} ({len(df_hist_inv)} lançamentos salvos)"):
                        if not df_hist_inv.empty:
                            st.download_button(label="📥 Baixar Excel", data=converter_para_excel(df_hist_inv), file_name=f"inventario_{inv['id']}.xlsx", key=f"dl_ger_{inv['id']}_{idx}")
                            st.dataframe(df_hist_inv, use_container_width=True, hide_index=True)
                with c_del_g:
                    if eh_supervisor:
                        if st.button("🗑️ Deletar Pasta", key=f"del_folder_ger_{inv['id']}_{idx}", use_container_width=True):
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM inventarios WHERE id = ?", (inv['id'],))
                            cursor.execute("DELETE FROM contagens WHERE inventario_id = ?", (id_inv_proc,))
                            cursor.execute("DELETE FROM itens_base_inventario WHERE inventario_id = ?", (id_inv_proc,))
                            conn.commit()
                            st.success("Excluído permanentemente!")
                            st.rerun()

    # --- ABA 6: BASE DE ESTOQUE ---
    with aba_base:
        if st.session_state.base_sistema is not None:
            st.dataframe(st.session_state.base_sistema, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma base cadastrada.")

    conn.close()
