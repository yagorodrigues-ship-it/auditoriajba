import streamlit as st
import pandas as pd
import datetime
import sqlite3
import io
import re
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico - JBA", layout="wide")

# --- BANCO DE DADOS PERMANENTE (SQLITE) ---
def conectar_banco():
    caminho_banco = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'banco_inventario.db') if '__file__' in locals() else 'banco_inventario.db'
    conn = sqlite3.connect(caminho_banco, check_same_thread=False)
    return conn

def inicializar_banco():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            cpf TEXT UNIQUE,
            email TEXT UNIQUE,
            senha TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventarios (
            id TEXT PRIMARY KEY,
            nome TEXT,
            data TEXT,
            status TEXT
        )
    """)
    
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

    cursor.execute("SELECT * FROM usuarios WHERE email = 'admin@tel.com.br'")
    if cursor.fetchone() is None:
        cursor.execute("""
            INSERT INTO usuarios (nome, cpf, email, senha) 
            VALUES (?, ?, ?, ?)
        """, ("Administrador Tel", "00000000000", "admin@tel.com.br", "123"))
        
    conn.commit()
    conn.close()

inicializar_banco()

# --- LISTA FIXA DE ESTOQUES JBA ---
ESTOQUES_JBA = [
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

def converter_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    return output.getvalue()

# --- ESTILIZAÇÃO ---
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
    .card-lateral { background-color: #1a233a; padding: 12px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #2563eb; }
    .card-lateral-titulo { color: #93c5fd; font-size: 11px; font-weight: bold; }
    .card-lateral-valor { color: white; font-size: 28px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'base_sistema' not in st.session_state: st.session_state.base_sistema = None
if 'operador' not in st.session_state: st.session_state.operador = ""
if 'tela_acesso' not in st.session_state: st.session_state.tela_acesso = "login"
if 'contador_reset' not in st.session_state: st.session_state.contador_reset = 0

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
            if st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True):
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

# --- PAINEL PRINCIPAL ---
else:
    conn = conectar_banco()
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios ORDER BY data DESC, id DESC", conn)
    eh_supervisor = any(x in st.session_state.operador.lower() for x in ["administrador", "admin", "supervisor", "tel"])
    
    # --- BARRA LATERAL ---
    with st.sidebar:
        st.write(f"👤 **Operador Ativo:** {st.session_state.operador}")
        c_side_u1, c_side_u2 = st.columns(2)
        with c_side_u1:
            if st.button("🔄 Atualizar", use_container_width=True): st.rerun()
        with c_side_u2:
            if st.button("🚪 Sair", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.operador = ""
                st.session_state.tela_acesso = "login"
                st.rerun()
            
        st.markdown("---")
        with st.expander("➕ Criar Novo Inventário"):
            with st.form("form_novo", clear_on_submit=True):
                novo_nome = st.text_input("Nome do Inventário")
                if st.form_submit_button("Criar Pasta", type="primary") and novo_nome:
                    maior_id = 0
                    if not df_inventarios.empty:
                        ids_nums = df_inventarios['id'].astype(str).str.extract(r'(\d+)').dropna().astype(int)
                        if not ids_nums.empty: maior_id = ids_nums.max().iloc[0]
                    novo_id = f"#{maior_id + 1}"
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO inventarios (id, nome, data, status) VALUES (?, ?, ?, 'Aberto')", (novo_id, novo_nome, datetime.date.today().strftime("%Y-%m-%d")))
                    conn.commit()
                    st.rerun()

        st.write("📁 **Selecione o Inventário Ativo**")
        if df_inventarios.empty:
            st.info("Nenhum inventário aberto.")
            id_inventario_atual = None
            inventario_selected_obj = None
        else:
            lista_inv = [f"{row['id']} – {row['nome']} ({row['status']})" for idx, row in df_inventarios.iterrows()]
            inventario_selected = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
            
            match_id_num = re.search(r'#(\d+)', inventario_selected)
            id_inventario_atual = match_id_num.group(1) if match_id_num else None
            inventario_selected_obj = df_inventarios[df_inventarios['id'].str.replace('#', '', regex=False) == id_inventario_atual].iloc[0] if id_inventario_atual else None

        if id_inventario_atual:
            id_limpo_sql = id_inventario_atual.replace("#", "").strip()
            df_base_persistida = pd.read_sql_query("SELECT cod_produto, desc_produto, desc_estoque_fisico, unid_medida, qtd_estoque, id_estoque_fisico, lote, ativo FROM itens_base_inventario WHERE inventario_id = ?", conn, params=(id_limpo_sql,))
            if not df_base_persistida.empty:
                st.session_state.base_sistema = df_base_persistida.rename(columns={'desc_estoque_fisico': 'descestoquefisico', 'id_estoque_fisico': 'idestoquefísico'})
            else:
                st.session_state.base_sistema = None

        st.write("📂 **Carregar Planilha Base**")
        arquivo_excel = st.file_uploader("Suba o arquivo (.xlsx)", type=["xlsx"], label_visibility="collapsed")
        if arquivo_excel is not None and id_inventario_atual:
            df_upload_temp = pd.read_excel(arquivo_excel)
            id_limpo_gravar = id_inventario_atual.replace("#", "").strip()
            
            cursor_db = conn.cursor()
            cursor_db.execute("DELETE FROM itens_base_inventario WHERE inventario_id = ?", (id_limpo_gravar,))
            
            def resgatar_coluna(termos, index_padrao, proibir=None):
                for t in termos:
                    for col in df_upload_temp.columns:
                        col_str = str(col).lower().replace(" ", "").replace(".", "").replace("_", "")
                        if t.lower() in col_str:
                            if proibir and any(p.lower() in col_str for p in proibir):
                                continue
                            return col
                if index_padrao < len(df_upload_temp.columns):
                    return df_upload_temp.columns[index_padrao]
                return None

            c_cod = resgatar_coluna(['codproduto', 'códproduto', 'material', 'codigo', 'código', 'sap', 'item'], 0)
            c_desc = resgatar_coluna(['descproduto', 'descricao', 'descrição', 'texto', 'nome'], 1)
            c_local = resgatar_coluna(['descestoquefisico', 'localizacao', 'localização', 'estoque', 'depósito', 'deposito'], 2)
            c_unid = resgatar_coluna(['unidmedida', 'unidade', 'unid', 'umb', 'un'], 3)
            c_qtd = resgatar_coluna(['qtdestoque', 'quantidade', 'saldo', 'atual', 'total'], -1)
            c_id_est = resgatar_coluna(['idestoquefísico', 'idestoque', 'codestoque', 'centro'], 0)
            c_lote = resgatar_coluna(['lote', 'batch'], 0)
            c_ativo = resgatar_coluna(['ativo', 'patrimonio', 'asset'], 0, proibir=['id', 'cod', 'codigo', 'código'])

            for _, r in df_upload_temp.iterrows():
                cod_final = str(r[c_cod]).strip().upper() if c_cod and pd.notna(r[c_cod]) else ""
                if not cod_final or cod_final.lower() == 'nan': 
                    continue
                
                desc_final = str(r[c_desc]).strip() if c_desc and pd.notna(r[c_desc]) else "Sem Descrição"
                local_final = str(r[c_local]).strip() if c_local and pd.notna(r[c_local]) else "Geral"
                unid_final = str(r[c_unid]).strip() if c_unid and pd.notna(r[c_unid]) else "UN"
                qtd_final = int(pd.to_numeric(r[c_qtd], errors='coerce') or 0) if c_qtd and pd.notna(r[c_qtd]) else 0
                id_est_final = str(r[c_id_est]).strip() if c_id_est and pd.notna(r[c_id_est]) else "1"
                lote_item_v = str(r[c_lote]).strip() if c_lote and pd.notna(r[c_lote]) else ""
                
                ativo_item_v = ""
                if c_ativo and pd.notna(r[c_ativo]):
                    bruto_ativo = str(r[c_ativo]).strip()
                    if bruto_ativo and bruto_ativo.lower() != 'nan' and bruto_ativo != '0' and bruto_ativo != '1864380':
                        ativo_item_v = bruto_ativo

                cursor_db.execute("""
                    INSERT INTO itens_base_inventario (inventario_id, cod_produto, desc_produto, desc_estoque_fisico, unid_medida, qtd_estoque, id_estoque_fisico, lote, ativo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (id_limpo_gravar, cod_final, desc_final, local_final, unid_final, qtd_final, id_est_final, lote_item_v, ativo_item_v))
            
            conn.commit()
            st.rerun()

        # METRICAS LATERAIS
        total_itens_base, total_contados, total_pendentes, progresso = 0, 0, 0, 0.0
        pode_fechar_sozinho = False
        if id_inventario_atual:
            id_limpo_calc = id_inventario_atual.replace("#", "").strip()
            df_itens_b = pd.read_sql_query("SELECT * FROM itens_base_inventario WHERE inventario_id = ?", conn, params=(id_limpo_calc,))
            total_itens_base = len(df_itens_b)
            
            df_contagens_atuais_side = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ?", conn, params=(id_limpo_calc,))
            total_contados = len(df_contagens_atuais_side)
            
            if total_itens_base > 0 and not df_contagens_atuais_side.empty:
                contados_set = set(df_contagens_atuais_side.apply(lambda r: f"{str(r['cod_produto']).strip().upper()}|{str(r['lote']).strip().upper()}|{str(r['ativo']).strip().upper()}", axis=1))
                base_set = set(df_itens_b.apply(lambda r: f"{str(r['cod_produto']).strip().upper()}|{str(r['lote']).strip().upper()}|{str(r['ativo']).strip().upper()}", axis=1))
                total_pendentes = len(base_set - contados_set)
                progresso = min(1.0, len(contados_set & base_set) / len(base_set))
            else:
                total_pendentes = total_itens_base
            if total_pendentes == 0 and total_itens_base > 0: pode_fechar_sozinho = True

        st.markdown("---")
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">📋 ITENS NA BASE</div><div class="card-lateral-valor">{total_itens_base}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">✅ LANÇAMENTOS GERAIS</div><div class="card-lateral-valor">{total_contados}</div></div>', unsafe_allow_html=True)
        st.write(f"**PENDÊNCIAS RESTANTES:** {total_pendentes}")
        st.progress(progresso)

        if inventario_selected_obj is not None and inventario_selected_obj['status'] in ["Aberto", "2a Contagem", "2ª Contagem"]:
            st.markdown("---")
            if pode_fechar_sozinho:
                if st.button("🔒 Fechar Inventário e Finalizar", use_container_width=True, type="primary"):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE inventarios SET status = 'Fechado' WHERE id = ?", (f"#{id_inventario_atual}",))
                    conn.commit()
                    st.success("✅ Inventário encerrado com sucesso!")
                    st.rerun()
            else:
                st.error(f"❌ Bloqueado: Faltam {total_pendentes} itens.")
                if eh_supervisor:
                    if st.button("🚨 Confirmar Fechamento (ADMIN)", use_container_width=True, type="primary"):
                        cursor = conn.cursor()
                        cursor.execute("UPDATE inventarios SET status = 'Fechado' WHERE id = ? OR id = ?", (id_inventario_atual, f"#{id_inventario_atual}"))
                        conn.commit()
                        st.success("✅ Forçado com sucesso!")
                        st.rerun()

    st.markdown("---")
    aba_contar, aba_atual, aba_supervisor, aba_historico, aba_status_estoques, aba_base_estoque = st.tabs(["🔍 Contar Item", "📊 Contagem AtuaL", "🔬 Painel Supervisor", "📁 Histórico Geral", "📊 Status dos Estoques", "📄 Base de Estoque"])
    
    # --- ABA 1: CONTAR ITEM ---
    with aba_contar:
        if id_inventario_atual is None or st.session_state.base_sistema is None or total_itens_base == 0:
            st.warning("⚠️ Mapeie o inventário e faça o upload da base na barra lateral para liberar a digitação.")
        elif inventario_selected_obj is not None and inventario_selected_obj['status'] == "Fechado":
            st.error("🔒 Este inventário operacional está Fechado.")
        else:
            c_busca, c_limpar = st.columns([8, 2])
            with c_busca:
                codigo_input = st.text_input("💻 Digite/Bipe o Código do Produto ou o número do Ativo", value="", placeholder="Bipe aqui...", key=f"bip_{st.session_state.contador_reset}")
            with c_limpar:
                st.write("")
                if st.button("🗑 ... Limpar Tela", use_container_width=True):
                    st.session_state.contador_reset += 1
                    st.rerun()
                    
            if codigo_input:
                busca_limpa = str(codigo_input).upper().strip()
                codigo_produto_alvo = busca_limpa.split(" - ")[-1].strip() if " - " in busca_limpa else busca_limpa
                id_pasta_limpo = id_inventario_atual.replace("#", "").strip()
                
                df_ja_contados = pd.read_sql_query("SELECT lote, ativo, cod_produto FROM contagens WHERE inventario_id = ?", conn, params=(id_pasta_limpo,))
                df_busca_por_ativo = st.session_state.base_sistema[st.session_state.base_sistema['ativo'].astype(str).str.upper().str.strip() == codigo_produto_alvo]
                
                if not df_busca_por_ativo.empty:
                    codigo_produto_alvo = str(df_busca_por_ativo.iloc[0]['cod_produto']).upper().strip()

                itens_filtrados = st.session_state.base_sistema[st.session_state.base_sistema['cod_produto'].astype(str).str.upper().str.strip() == codigo_produto_alvo]
                
                if not itens_filtrados.empty:
                    def checar_ativo_real(val):
                        s = str(val).strip()
                        if not s or s.lower() in ['nan', '0', '', '-', 'n/a', 'sem ativo', '1864380']:
                            return False
                        return bool(re.match(r'^\d+$', s))

                    possui_ativo_na_base = any(checar_ativo_real(x) for x in itens_filtrados['ativo'].unique())
                    
                    lotes_validos_restantes = []
                    ativos_por_lote_restantes = {}
                    
                    for lote_item in itens_filtrados['lote'].dropna().astype(str).str.strip().unique():
                        linhas_do_lote = itens_filtrados[itens_filtrados['lote'].astype(str).str.strip() == lote_item]
                        ativos_do_lote = [a for a in linhas_do_lote['ativo'].dropna().astype(str).str.strip().tolist() if checar_ativo_real(a)]
                        
                        if not possui_ativo_na_base:
                            if not ((df_ja_contados['cod_produto'].astype(str).str.strip().str.upper() == codigo_produto_alvo) & 
                                    (df_ja_contados['lote'].astype(str).str.strip().str.upper() == lote_item.upper())).any():
                                lotes_validos_restantes.append(lote_item)
                        else:
                            ativos_filtrados = [
                                a for a in ativos_do_lote 
                                if not (
                                    (df_ja_contados['cod_produto'].astype(str).str.strip().str.upper() == codigo_produto_alvo) & 
                                    (df_ja_contados['lote'].astype(str).str.strip().str.upper() == lote_item.upper()) & 
                                    (df_ja_contados['ativo'].astype(str).str.strip().str.upper() == str(a).strip().upper())
                                ).any()
                            ]
                            if len(ativos_filtrados) > 0:
                                lotes_validos_restantes.append(lote_item)
                                ativos_por_lote_restantes[lote_item] = ativos_filtrados

                    if not lotes_validos_restantes:
                        st.success("🎉 Todos os lotes e ativos deste produto já foram completamente contabilizados!")
                    else:
                        lote_selecionado = st.selectbox("👇 SELECIONE O LOTE PARA CONTAGEM (Apenas pendentes):", lotes_validos_restantes, key="lote_selector_bip")

                        ativos_disponiveis_no_lote = ativos_por_lote_restantes.get(lote_selecionado, [])
                        ativo_selecionado = ""
                        
                        if possui_ativo_na_base and ativos_disponiveis_no_lote:
                            ativo_selecionado = st.selectbox("👇 SELECIONE O ATIVO PARA CONTAGEM (Apenas pendentes):", ativos_disponiveis_no_lote, key="ativo_selector_bip")

                        item_especifico = itens_filtrados[itens_filtrados['lote'].astype(str).str.strip() == lote_selecionado].iloc[0]

                        unid_val = item_especifico['unid_medida'] if 'unid_medida' in item_especifico else "UN"
                        desc_val = item_especifico['desc_produto']
                        local_val = item_especifico['descestoquefisico']
                        id_estoque_val = str(item_especifico['idestoquefísico']).strip()
                        qtd_sys = int(item_especifico['qtd_estoque']) if 'qtd_estoque' in item_especifico else 0

                        b1, b2, b3 = st.columns(3)
                        b1.markdown(f'<div class="bloco-info"><div class="bloco-titulo">CÓD. PRODUTO</div><div class="bloco-valor">{codigo_produto_alvo}</div></div>', unsafe_allow_html=True)
                        b2.markdown(f'<div class="bloco-info"><div class="bloco-titulo">ESTOQUE FÍSICO</div><div class="bloco-valor">{local_val}</div></div>', unsafe_allow_html=True)
                        b3.markdown(f'<div class="bloco-info"><div class="bloco-titulo">LOTE EM CONTAGEM</div><div class="bloco-valor" style="color:#d35400;">{lote_selecionado if lote_selecionado else "Padrão"}</div></div>', unsafe_allow_html=True)
                        
                        st.markdown(f"**Descrição do Material:** {desc_val}")
                        
                        with st.form("confirmar_contagem_form"):
                            qtd_fisica = st.number_input("📦 Quantidade contada fisicamente (Obrigatório)", min_value=1, step=1, value=1)
                            observacao = st.text_input("📝 Observação (opcional)")
                            
                            if st.form_submit_button("✓ Confirmar Lançamento", type="primary", use_container_width=True):
                                cursor = conn.cursor()
                                fase_atual = "1a Contagem" if inventario_selected_obj['status'] == "Aberto" else "2a Contagem"
                                
                                cursor.execute("""
                                    INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, observacao, operador, data_hora, lote, fase_contagem)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (id_pasta_limpo, id_estoque_val, local_val, codigo_produto_alvo, desc_val, unid_val, qtd_sys, qtd_fisica, qtd_fisica - qtd_sys, str(ativo_selecionado).strip().upper(), observacao, st.session_state.operador, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), lote_selecionado, fase_atual))
                                conn.commit()
                                
                                st.session_state.contador_reset += 1
                                st.rerun()
                else:
                    st.error("⚠️ Código ou Ativo não localizado na base deste inventário.")

    # --- ABA 2: CONTAGEM ATUAL ---
    with aba_atual:
        if id_inventario_atual:
            id_limpo_a = id_inventario_atual.replace("#", "").strip()
            df_contagens_mutaveis = pd.read_sql_query("SELECT id, lote, ativo, cod_produto, desc_produto, qtd_contada, operador, data_hora FROM contagens WHERE inventario_id = ? ORDER BY id DESC", conn, params=(id_limpo_a,))
            if df_contagens_mutaveis.empty:
                st.info("Nenhum item lançado até o momento.")
            else:
                st.dataframe(df_contagens_mutaveis, use_container_width=True, hide_index=True)

    # --- ABA 3: PAINEL SUPERVISOR ---
    with aba_supervisor:
        if not eh_supervisor:
            st.error("🚫 Painel exclusivo para o Supervisor.")
        else:
            st.subheader("📊 Lançamentos da Pasta Ativa")
            id_limpo_s = id_inventario_atual.replace("#", "").strip() if id_inventario_atual else ""
            df_painel_adm = pd.read_sql_query("SELECT id, inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, lote, ativo, operador, qtd_sistema, qtd_contada, diferenca, fase_contagem, data_hora, observacao FROM contagens WHERE inventario_id = ?", conn, params=(id_limpo_s,))
            
            if not df_painel_adm.empty:
                st.dataframe(df_painel_adm, use_container_width=True, hide_index=True)
                st.download_button(label="📥 Exportar Lançamentos para Excel", data=converter_para_excel(df_painel_adm), file_name=f"Inventario_Pasta_{id_limpo_s}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                
                st.markdown("---")
                st.subheader("🔄 Corrigir e Liberar Item para Recontagem")
                with st.form("form_correcao_supervisor"):
                    lista_itens_reabrir = [f"{r['id']} - {r['cod_produto']} | {r['desc_produto']} (Lote: {r['lote']})" for _, r in df_painel_adm.iterrows()]
                    item_selecionado_recontar = st.selectbox("Escolha o lançamento incorreto para anular e mandar para a 2ª Contagem:", lista_itens_reabrir)
                    id_linha_contagem = item_selecionado_recontar.split(" - ")[0]
                    
                    if st.form_submit_button("🚨 Zerar e Liberar para 2ª Contagem", type="primary", use_container_width=True):
                        cursor = conn.cursor()
                        cursor.execute("UPDATE inventarios SET status = '2ª Contagem' WHERE id = ? OR id = ?", (id_inventario_atual, f"#{id_inventario_atual}"))
                        cursor.execute("UPDATE contagens SET fase_contagem = '2a Contagem', qtd_contada = 0, diferenca = (0 - qtd_sistema) WHERE id = ?", (id_linha_contagem,))
                        conn.commit()
                        st.success("✅ Item liberado para correção na Aba 1!")
                        st.rerun()
            else:
                st.info("Nenhum lançamento registrado nesta pasta.")

    # --- ABA 4: HISTÓRICO GERAL ---
    with aba_historico:
        st.title("📁 Arquivo Geral de Movimentações")
        df_pastas = pd.read_sql_query("SELECT DISTINCT inventario_id FROM contagens", conn)
        if df_pastas.empty:
            st.info("Nenhum histórico registrado encontrado.")
        else:
            for _, r in df_pastas.iterrows():
                id_p = str(r['inventario_id'])
                df_p = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ?", conn, params=(id_p,))
                
                c_exp, c_del = st.columns([8, 2])
                with c_exp:
                    with st.expander(f"📁 Pasta Operacional #{id_p} ({len(df_p)} lançamentos salvos)"):
                        st.dataframe(df_p, use_container_width=True, hide_index=True)
                        st.download_button(label="📥 Baixar Planilha em Excel", data=converter_para_excel(df_p), file_name=f"Backup_Pasta_{id_p}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"btn_{id_p}")
                with c_del:
                    if eh_supervisor:
                        if st.button("🗑️ Deletar Pasta", key=f"del_{id_p}", use_container_width=True):
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM inventarios WHERE id = ? OR id = ?", (id_p, f"#{id_p}"))
                            cursor.execute("DELETE FROM contagens WHERE inventario_id = ?", (id_p,))
                            cursor.execute("DELETE FROM itens_base_inventario WHERE inventario_id = ?", (id_p,))
                            conn.commit()
                            st.success("Deletado!")
                            st.rerun()

    # --- ABA 5: STATUS E PRAZOS DOS ESTOQUES JBA ---
    with aba_status_estoques:
        st.title("📊 Painel de Controle e Auditoria de Prazos")
        df_ultimas = pd.read_sql_query("SELECT id_estoque, max(data_hora) as ultima_data FROM contagens GROUP BY id_estoque", conn)
        dict_ultimas = dict(zip(df_ultimas['id_estoque'].astype(str), df_ultimas['ultima_data']))
        hoje_dt = datetime.datetime.now()
        
        dados_status = []
        for est in ESTOQUES_JBA:
            id_est = est["id"]
            ultima_v = dict_ultimas.get(id_est, None)
            if ultima_v:
                try:
                    dt_objeto = datetime.datetime.strptime(str(ultima_v)[:19], "%Y-%m-%d %H:%M:%S")
                    dias_passados = (hoje_dt - dt_objeto).days
                    texto_ultima = dt_objeto.strftime("%d/%m/%Y %H:%M")
                except: dias_passados, texto_ultima = 999, "Sem registros"
            else: dias_passados, texto_ultima = 999, "Nunca Contado pelo Sistema"
            
            if dias_passados <= 5: status_texto = "🟢 Bom (Atualizado)"
            elif dias_passados <= 14: status_texto = "🟡 Atenção (Aviso: +1 semana)"
            else: status_texto = "🔴 CRÍTICO (Necessita contar urgente: +2 semanas)"
            
            dados_status.append({"Id. Estoque": id_est, "Descrição do Estoque Físico": est["desc"], "Última Contagem Realizada": texto_ultima, "Dias desde a Última Contagem": dias_passados if dias_passados != 999 else "N/A", "Status de Criticidade": status_texto})
            
        df_painel_final = pd.DataFrame(dados_status)
        filtro_status = st.multiselect("Filtrar por Status", ["🟢 Bom (Atualizado)", "🟡 Atenção (Aviso: +1 semana)", "🔴 CRÍTICO (Necessita contar urgente: +2 semanas)"], default=["🟢 Bom (Atualizado)", "🟡 Atenção (Aviso: +1 semana)", "🔴 CRÍTICO (Necessita contar urgente: +2 semanas)"])
        st.dataframe(df_painel_final[df_painel_final["Status de Criticidade"].isin(filtro_status)], use_container_width=True, hide_index=True)

    # --- ABA 6: PLANILHA DA BASE DE ESTOQUE (CRUZAMENTO EM TEMPO REAL) ---
    with aba_base_estoque:
        st.title("📄 Base de Dados Importada do Inventário")
        if st.session_state.base_sistema is not None:
            id_limpo_b = id_inventario_atual.replace("#", "").strip() if id_inventario_atual else ""
            
            # Resgata lançamentos efetuados nesta pasta para cruzar dados
            df_contados_db = pd.read_sql_query("SELECT cod_produto, lote, ativo, qtd_contada FROM contagens WHERE inventario_id = ?", conn, params=(id_limpo_b,))
            
            # Clona a base para aplicar as colunas extras de auditoria visual
            df_exibicao_base = st.session_state.base_sistema.copy()
            
            if not df_contados_db.empty:
                # Agrupa a quantidade total bipada por chave única de material
                grouped_contas = df_contados_db.groupby(['cod_produto', 'lote', 'ativo'])['qtd_contada'].sum().reset_index()
                
                # Mescla as contagens para exibir na listagem
                df_exibicao_base = df_exibicao_base.merge(
                    grouped_contas, 
                    on=['cod_produto', 'lote', 'ativo'], 
                    how='left'
                )
                df_exibicao_base['qtd_contada'] = df_exibicao_base['qtd_contada'].fillna(0).astype(int)
                df_exibicao_base['Contabilizado'] = df_exibicao_base['qtd_contada'].apply(lambda x: '🟢 Sim' if x > 0 else '❌ Não')
                df_exibicao_base = df_exibicao_base.rename(columns={'qtd_contada': 'qtd_lancada'})
            else:
                df_exibicao_base['qtd_lancada'] = 0
                df_exibicao_base['Contabilizado'] = '❌ Não'
                
            st.dataframe(df_exibicao_base, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma planilha base foi importada para esta pasta operacional até o momento.")

    conn.close()
