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

# --- TELA PRINCIPAL ---
else:
    conn = conectar_banco()
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios ORDER BY data DESC, id DESC", conn)
    eh_supervisor = any(x in st.session_state.operador.lower() for x in ["administrador", "admin", "supervisor"])
    
    # --- SIDEBAR ---
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
                
                cod_final = str(r[c_cod_u]).strip() if c_cod_u in df_upload_temp.columns else str(r.iloc[0])
                desc_final = str(r[c_desc_u]) if c_desc_u in df_upload_temp.columns else "Sem Descrição"
                local_final = str(r[c_local_u]) if c_local_u in df_upload_temp.columns else "Geral"
                unid_final = str(r[c_unid_u]) if c_unid_u in df_upload_temp.columns else "UN"
                qtd_final = int(pd.to_numeric(r[c_qtd_u], errors='coerce') or 0) if c_qtd_u in df_upload_temp.columns else 0
                id_est_final = str(r[c_id_est_u]).strip() if c_id_est_u in df_upload_temp.columns else "1"

                cursor_db.execute("""
                    INSERT INTO itens_base_inventario (inventario_id, cod_produto, desc_produto, desc_estoque_fisico, unid_medida, qtd_estoque, id_estoque_fisico, lote, ativo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (id_pasta_limpo_base, cod_final, desc_final, local_final, unid_final, qtd_final, id_est_final, lote_item_v, ativo_item_v))
            
            conn.commit()
            st.rerun()

        # PROGRESSO LATERAL
        total_itens_base, total_contados, total_pendentes, progresso = 0, 0, 0, 0.0
        if st.session_state.base_sistema is not None and id_inventario_atual:
            total_itens_base = len(st.session_state.base_sistema)
            df_contagens_atuais_side = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ?", conn, params=(id_inventario_atual,))
            total_contados = len(df_contagens_atuais_side)
            
            # Cálculo de progresso baseado em chaves exclusivas de produto+lote+ativo
            if not df_contagens_atuais_side.empty:
                contados_set = set(df_contagens_atuais_side.apply(lambda r: f"{str(r['cod_produto']).strip().upper()}|{str(r['lote']).strip().upper()}|{str(r['ativo']).strip().upper()}", axis=1))
                base_set = set(st.session_state.base_sistema.apply(lambda r: f"{str(r['cod_produto']).strip().upper()}|{str(r['lote']).strip().upper()}|{str(r['ativo']).strip().upper()}", axis=1))
                total_pendentes = len(base_set - contados_set)
                if len(base_set) > 0:
                    progresso = min(1.0, len(contados_set & base_set) / len(base_set))
            else:
                total_pendentes = total_itens_base

        st.markdown("---")
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">📋 ITENS NA BASE</div><div class="card-lateral-valor">{total_itens_base}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">✅ LANÇAMENTOS GERAIS</div><div class="card-lateral-valor">{total_contados}</div></div>', unsafe_allow_html=True)
        st.write("**PROGRESSO GLOBAL**")
        st.progress(progresso)

    st.markdown("---")
    abas = ["🔍 Contar Item", "📊 Contagem Atual", "🔬 Painel Supervisor", "📁 Histórico Geral", "📄 Base de Estoque"]
    aba_contar, aba_atual, aba_supervisor, aba_historico_geral, aba_base = st.tabs(abas)
    
    # --- ABA 1: CONTAR ITEM (FILTRO AGRESSIVO DE REMOÇÃO APLICADO AQUI) ---
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
                if st.button("🗑️ Limpar Tela", use_container_width=True):
                    st.session_state.contador_reset += 1
                    st.rerun()
                    
            if codigo_input:
                busca_limpa = str(codigo_input).upper().strip()
                id_pasta_limpo = id_inventario_atual
                
                # Buscar contagens que já foram realizadas nesta pasta para exclusão dinâmica
                df_ja_contados = pd.read_sql_query("SELECT lote, ativo, cod_produto FROM contagens WHERE inventario_id = ?", conn, params=(id_pasta_limpo,))
                
                # 1. Tentar encontrar se o valor inserido pertence à coluna de ATIVOS
                df_busca_por_ativo = st.session_state.base_sistema[st.session_state.base_sistema['ativo'].astype(str).str.upper().str.strip() == busca_limpa]
                
                if not df_busca_por_ativo.empty:
                    # Se localizou pelo Ativo, extrai o código correspondente do produto
                    codigo_produto_alvo = str(df_busca_por_ativo.iloc[0]['cod_produto']).upper().strip()
                    itens_filtrados = st.session_state.base_sistema[st.session_state.base_sistema['cod_produto'].astype(str).str.upper().str.strip() == codigo_produto_alvo]
                else:
                    # Caso contrário, trata a entrada diretamente como Código do Produto
                    codigo_produto_alvo = busca_limpa
                    itens_filtrados = st.session_state.base_sistema[st.session_state.base_sistema['cod_produto'].astype(str).str.upper().str.strip() == codigo_produto_alvo]
                
                if not itens_filtrados.empty:
                    # --- FILTRAGEM DINÂMICA DE LOTES E ATIVOS DISPONÍVEIS ---
                    lotes_validos_restantes = []
                    ativos_por_lote_restantes = {}
                    
                    for lote_item in itens_filtrados['lote'].dropna().astype(str).str.strip().unique():
                        linhas_do_lote = itens_filtrados[itens_filtrados['lote'].astype(str).str.strip() == lote_item]
                        ativos_do_lote = linhas_do_lote['ativo'].dropna().astype(str).str.strip().tolist()
                        
                        # Filtra apenas os ativos do lote atual que AINDA NÃO possuem registro na tabela de contagens
                        ativos_filtrados = [
                            a for a in ativos_do_lote 
                            if not (
                                (df_ja_contados['cod_produto'].astype(str).str.strip().str.upper() == codigo_produto_alvo) & 
                                (df_ja_contados['lote'].astype(str).str.strip().str.upper() == lote_item.upper()) & 
                                (df_ja_contados['ativo'].astype(str).str.strip().str.upper() == str(a).strip().upper())
                            ).any()
                        ]
                        
                        # Se houver ativos pendentes ou se o lote não exigir rastreabilidade de ativos específicos
                        if ativos_filtrados or not ativos_do_lote:
                            lotes_validos_restantes.append(lote_item)
                            ativos_por_lote_restantes[lote_item] = ativos_filtrados

                    # --- INTERFACE DE SELEÇÃO DINÂMICA ---
                    if not lotes_validos_restantes:
                        st.success("🎉 Todos os lotes e ativos vinculados a este produto já foram completamente contabilizados!")
                    else:
                        # Se o operador bipou um ativo específico diretamente, autoseleciona o lote dele
                        if not df_busca_por_ativo.empty:
                            lote_padrao = str(df_busca_por_ativo.iloc[0]['lote']).strip()
                            lote_selecionado = lote_padrao if lote_padrao in lotes_validos_restantes else lotes_validos_restantes[0]
                        else:
                            lote_selecionado = st.selectbox("👇 SELECIONE O LOTE PARA CONTAGEM (Apenas pendentes):", lotes_validos_restantes, key="lote_selector_bip")

                        ativos_disponiveis_no_lote = ativos_por_lote_restantes.get(lote_selecionado, [])
                        ativos_disponiveis_no_lote = [a for a in ativos_disponiveis_no_lote if str(a).strip() != ""]

                        ativo_selecionado = ""
                        if not df_busca_por_ativo.empty:
                            ativo_selecionado = busca_limpa
                            # Validação final se o ativo bipado diretamente já foi feito
                            if ativo_selecionado not in ativos_disponiveis_no_lote and len(ativos_disponiveis_no_lote) > 0:
                                st.error(f"🚨 O Ativo {ativo_selecionado} já consta como lançado no banco de dados!")
                                ativo_selecionado = ""
                        elif ativos_disponiveis_no_lote:
                            ativo_selecionado = st.selectbox("👇 SELECIONE O ATIVO PARA CONTAGEM (Apenas pendentes):", ativos_disponiveis_no_lote, key="ativo_selector_bip")

                        # Resgatar metadados da linha selecionada para exibição em tela
                        if ativo_selecionado:
                            item_especifico = itens_filtrados[
                                (itens_filtrados['lote'].astype(str).str.strip() == lote_selecionado) & 
                                (itens_filtrados['ativo'].astype(str).str.strip() == ativo_selecionado)
                            ].iloc[0]
                        else:
                            item_especifico = itens_filtrados[itens_filtrados['lote'].astype(str).str.strip() == lote_selecionado].iloc[0]

                        unid_val = item_especifico['unid_medida'] if 'unid_medida' in item_especifico else "UN"
                        desc_val = item_especifico['desc_produto']
                        local_val = item_especifico['descestoquefisico']
                        id_estoque_val = str(item_especifico['idestoquefísico']).strip()
                        qtd_sys = int(item_especifico['qtd_estoque']) if 'qtd_estoque' in item_especifico else 0

                        b1, b2, b3, b4 = st.columns(4)
                        b1.markdown(f'<div class="bloco-info"><div class="bloco-titulo">CÓD. PRODUTO</div><div class="bloco-valor">{codigo_produto_alvo}</div></div>', unsafe_allow_html=True)
                        b2.markdown(f'<div class="bloco-info"><div class="bloco-titulo">ESTOQUE FÍSICO</div><div class="bloco-valor">{local_val}</div></div>', unsafe_allow_html=True)
                        b3.markdown(f'<div class="bloco-info"><div class="bloco-titulo">UNID. MEDIDA</div><div class="bloco-valor">{unid_val}</div></div>', unsafe_allow_html=True)
                        b4.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:0px;"><div class="bloco-titulo">LOTE EM CONTAGEM</div><div class="bloco-valor" style="color:#d35400;">{lote_selecionado if lote_selecionado else "Padrão"}</div></div>', unsafe_allow_html=True)
                        
                        st.markdown(f"**Descrição do Material:** {desc_val}")
                        
                        with st.form("confirmar_form", clear_on_submit=True):
                            qtd_fisica = st.number_input("📦 Quantidade contada fisicamente (Obrigatório)", min_value=0, step=1, value=1 if not df_busca_por_ativo.empty else 0)
                            ativo_final_input = st.text_input("🔢 Confirmar Número do Ativo", value=ativo_selecionado, disabled=True if ativo_selecionado else False)
                            observacao = st.text_input("📝 Observação (opcional)")
                            
                            if st.form_submit_button("✓ Confirmar Contagem", type="primary", use_container_width=True):
                                if qtd_fisica <= 0:
                                    st.error("❌ Erro: Informe uma quantidade maior que 0!")
                                else:
                                    cursor = conn.cursor()
                                    fase_atual = "1a Contagem" if inventario_selected_obj['status'] == "Aberto" else "2a Contagem"
                                    
                                    cursor.execute("""
                                        INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, observacao, operador, data_hora, lote, fase_contagem)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (id_pasta_limpo, id_estoque_val, local_val, codigo_produto_alvo, desc_val, unid_val, qtd_sys, qtd_fisica, qtd_fisica - qtd_sys, str(ativo_final_input if ativo_final_input else ativo_selecionado).strip().upper(), observacao, st.session_state.operador, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), lote_selecionado, fase_atual))
                                    conn.commit()
                                    
                                    st.session_state.contador_reset += 1
                                    st.rerun()
                else:
                    st.error("⚠️ Código ou Ativo não localizado na base deste inventário.")

    # --- ABA 2: CONTAGEM ATUAL ---
    with aba_atual:
        if id_inventario_atual:
            df_contagens_mutaveis = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? ORDER BY id DESC", conn, params=(id_inventario_atual,))
            if df_contagens_mutaveis.empty:
                st.info("Nenhum item lançado até o momento.")
            else:
                st.dataframe(df_contagens_mutaveis, use_container_width=True, hide_index=True)

    # --- ABA 3: PAINEL SUPERVISOR ---
    with aba_supervisor:
        st.title("🔬 Painel de Gestão e Auditoria do Supervisor")
        if not eh_supervisor:
            st.error("🚫 Acesso restrito ao Supervisor.")
        else:
            df_itens_da_pasta = pd.read_sql_query("SELECT id, cod_produto, desc_produto, lote, ativo, operador, qtd_contada, diferenca, fase_contagem FROM contagens WHERE inventario_id = ?", conn, params=(id_inventario_atual,))
            if df_itens_da_pasta.empty:
                st.info("Nenhuma contagem realizada para auditar.")
            else:
                st.dataframe(df_itens_da_pasta, use_container_width=True, hide_index=True)

    # --- ABA 4: HISTÓRICO GERAL ---
    with aba_historico_geral:
        st.title("📁 Arquivo Geral de Movimentações")
        df_pastas_com_contagem = pd.read_sql_query("SELECT DISTINCT inventario_id FROM contagens", conn)
        if df_pastas_com_contagem.empty:
            st.info("Nenhum histórico registrado encontrado.")
        else:
            for _, r_p in df_pastas_com_contagem.iterrows():
                id_limpo_c = str(r_p['inventario_id'])
                df_hist_inv = pd.read_sql_query("SELECT * FROM contagens WHERE inventario_id = ? ORDER BY id DESC", conn, params=(id_limpo_c,))
                with st.expander(f"📁 Inventário #{id_limpo_c} ({len(df_hist_inv)} lançamentos)"):
                    st.dataframe(df_hist_inv, use_container_width=True, hide_index=True)

    # --- ABA 5: BASE DE ESTOQUE ---
    with aba_base:
        if st.session_state.base_sistema is not None:
            st.dataframe(st.session_state.base_sistema, use_container_width=True, hide_index=True)

    conn.close()
