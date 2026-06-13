import streamlit as st
import pandas as pd
import datetime
import sqlite3
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico", layout="wide")

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
    
    # Tabela de inventários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventarios (
            id TEXT PRIMARY KEY,
            nome TEXT,
            data TEXT,
            status TEXT
        )
    """)
    
    # Tabela de contagens
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
    
    # Criar administrador padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO usuarios (nome, cpf, email, senha) 
            VALUES (?, ?, ?, ?)
        """, ("Administrador Tel", "00000000000", "admin@tel.com.br", "123"))
        
    conn.commit()
    conn.close()

inicializar_banco()

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
    </style>
""", unsafe_allow_html=True)

# --- GERENCIAMENTO DE ESTADO ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'base_sistema' not in st.session_state:
    st.session_state.base_sistema = None
if 'nome_arquivo_excel' not in st.session_state:
    st.session_state.nome_arquivo_excel = ""
if 'pagina_atual' not in st.session_state:
    st.session_state.pagina_atual = 1
if 'operador' not in st.session_state:
    st.session_state.operador = ""
if 'tela_acesso' not in st.session_state:
    st.session_state.tela_acesso = "login"

if 'contador_reset' not in st.session_state:
    st.session_state.contador_reset = 0
if 'ultimo_item_sucesso' not in st.session_state:
    st.session_state.ultimo_item_sucesso = ""

def limpar_documento(doc):
    return str(doc).strip().replace(".", "").replace("-", "").replace("/", "")

# --- TELA DE ACESSO (LOGIN / CADASTRO / RECUPERAÇÃO) ---
if not st.session_state.logged_in:
    conn = conectar_banco()
    
    if st.session_state.tela_acesso == "login":
        st.title("🔒 Acesso ao Sistema de Estoque")
        with st.form("login_form"):
            identificador = st.text_input("CPF (somente números) ou E-mail")
            senha = st.text_input("Senha", type="password")
            botao_login = st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True)
            
            if botao_login:
                id_limpo = identificador.strip()
                doc_limpo = limpar_documento(id_limpo)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT nome FROM usuarios 
                    WHERE (email = ? OR cpf = ?) AND senha = ?
                """, (id_limpo, doc_limpo, senha))
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
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios ORDER BY data DESC, id DESC", conn)
    
    # SIDEBAR
    with st.sidebar:
        st.write(f"👤 **Operador:** {st.session_state.operador}")
        if st.button("🚪 Sair da Conta", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.operador = ""
            st.session_state.tela_acesso = "login"
            st.rerun()
            
        st.markdown("---")
        st.write("📂 **Carregar Base de Dados (Saldo)**")
        arquivo_excel = st.file_uploader("Suba o arquivo Excel (.xlsx)", type=["xlsx"], label_visibility="collapsed")
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
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM inventarios")
                    novo_id = f"#{cursor.fetchone()[0] + 39}"
                    hoje = datetime.date.today().strftime("%Y-%m-%d")
                    cursor.execute("INSERT INTO inventarios (id, nome, data, status) VALUES (?, ?, ?, ?)", (novo_id, novo_nome, hoje, "Aberto"))
                    conn.commit()
                    st.rerun()

        if inventario_selecionado_obj is not None and inventario_selecionado_obj['status'] == "Aberto":
            if st.button("🔒 Fechar inventário atual", use_container_width=True):
                cursor = conn.cursor()
                cursor.execute("UPDATE inventarios SET status = 'Fechado' WHERE id = ?", (id_inventario_atual,))
                conn.commit()
                st.rerun()

        # --- MAPEAMENTO DE COLUNAS ---
        col_cod, col_desc, col_local, col_unidade, col_qtd, col_ativo_base, col_id_estoque = "", "", "", "", "", "", ""
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
            col_id_estoque = encontrar_coluna(['idestoquefísico', 'idestoque', 'codestoque'], 0)
            
            col_ativo_base = "Não Encontrado"
            for col in colunas_reais:
                if col.strip().lower() == "ativo":
                    col_ativo_base = col
                    break
            if col_ativo_base == "Não Encontrado":
                col_ativo_base = encontrar_coluna(['ativo', 'patrimonio', 'numativo'], -1)

        # --- PROGRESSO LATERAL ---
        total_itens_base = 0
        total_contados = 0
        total_pendentes = 0
        progresso = 0.0

        if st.session_state.base_sistema is not None and id_inventario_atual is not None:
            total_itens_base = len(st.session_state.base_sistema)
            df_contagens_atuais = pd.read_sql_query(f"SELECT * FROM contagens WHERE inventario_id = '{id_inventario_atual.replace('#','')}'", conn)
            
            contados_validos_set = set()
            for idx, c_row in df_contagens_atuais.iterrows():
                match_base = st.session_state.base_sistema[st.session_state.base_sistema[col_cod].astype(str).str.upper().str.strip() == str(c_row['cod_produto']).upper().strip()]
                if not match_base.empty:
                    at_esp = [str(x).upper().strip() for x in match_base[col_ativo_base].tolist() if col_ativo_base in match_base.columns]
                    at_esp = [x for x in at_esp if x not in ["NAN", "SIM", "", "0", "0.0"]]
                    if at_esp:
                        if str(c_row['ativo']).upper().strip() in at_esp:
                            contados_validos_set.add(str(c_row['cod_produto']).upper().strip())
                    else:
                        contados_validos_set.add(str(c_row['cod_produto']).upper().strip())
            
            total_contados = len(df_contagens_atuais)
            total_pendentes = max(0, total_itens_base - len(contados_validos_set))
            if total_itens_base > 0:
                progresso = min(1.0, len(contados_validos_set) / total_itens_base)

        st.markdown("---")
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">📋 ITENS NA BASE</div><div class="card-lateral-valor">{total_itens_base}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">✅ LANÇAMENTOS FEITOS</div><div class="card-lateral-valor">{total_contados}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-lateral"><div class="card-lateral-titulo">⏳ PENDENTES REAIS</div><div class="card-lateral-valor">{total_pendentes}</div></div>', unsafe_allow_html=True)
        st.write("**PROGRESSO DA CONTAGEM**")
        st.progress(progresso)

    if st.session_state.ultimo_item_sucesso:
        st.success(st.session_state.ultimo_item_sucesso)
        st.session_state.ultimo_item_sucesso = ""

    # ABAS DO PAINEL PRINCIPAL
    df_contagens_mutaveis = pd.read_sql_query(f"SELECT * FROM contagens WHERE inventario_id = '{id_inventario_atual.replace('#','')}' ORDER BY id DESC", conn) if id_inventario_atual else pd.DataFrame()
    
    aba_contar, aba_atual, aba_historico, aba_base, aba_graficos = st.tabs([
        "🔍 Contar Item", "📊 Contagem Atual", "📁 Histórico de Inventários", "📄 Base de Estoque", "🏆 Desempenho"
    ])
    
    # --- ABA 1: CONTAR ITEM ---
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
                
                item = df_exemplo[df_exemplo[col_cod].astype(str).str.upper().str.strip() == codigo_rastreio]
                if not item.empty:
                    unid_val = item.iloc[0][col_unidade] if col_unidade in item.columns else "UN"
                    desc_val = item.iloc[0][col_desc]
                    local_val = item.iloc[0][col_local] if col_local in item.columns else "Não Informado"
                    id_estoque_val = str(item.iloc[0][col_id_estoque]).strip() if col_id_estoque in item.columns else ""
                    
                    try:
                        qtd_sis = int(pd.to_numeric(item.iloc[0][col_qtd], errors='coerce'))
                        if pd.isna(qtd_sis): qtd_sis = 0
                    except: qtd_sis = 0
                    
                    ativos_da_base_lista = [str(x).upper().strip() for x in item[col_ativo_base].tolist() if col_ativo_base in item.columns]
                    ativos_da_base_lista = [x for x in list(set(ativos_da_base_lista)) if x not in ["NAN", "SIM", "", "0", "0.0"]]
                    
                    b1, b2, b3, b4 = st.columns(4)
                    b1.markdown(f'<div class="bloco-info"><div class="bloco-titulo">CÓD. PRODUTO</div><div class="bloco-valor">{codigo_rastreio}</div></div>', unsafe_allow_html=True)
                    b2.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:0px;"><div class="bloco-titulo">ESTOQUE FÍSICO</div><div class="bloco-valor" style="font-size:22px;">{local_val}</div></div>', unsafe_allow_html=True)
                    b3.markdown(f'<div class="bloco-info"><div class="bloco-titulo">UNID. MEDIDA</div><div class="bloco-valor">{unid_val}</div></div>', unsafe_allow_html=True)
                    b4.markdown('<div class="bloco-info"><div class="bloco-titulo">STATUS BARRA</div><div class="bloco-valor" style="color:#2ecc71;">● Conectado</div></div>', unsafe_allow_html=True)
                    
                    st.markdown(f"**Descrição:** {desc_val}")
                    if ativos_da_base_lista:
                        st.info(f"📋 **Nota de Sistema:** Este item possui ativos mapeados no saldo da coluna '{col_ativo_base}'. Ativos válidos: {', '.join(ativos_da_base_lista)}")
                    
                    st.markdown(f'<div class="card-sistema"><div class="bloco-titulo">QTD SISTEMA</div><div style="font-size:32px; font-weight:bold; color:#1f2c3f;">{qtd_sis}</div></div>', unsafe_allow_html=True)
                    
                    with st.form("confirmar_form", clear_on_submit=True):
                        qtd_fisica = st.number_input("📦 Quantidade contada fisicamente (Obrigatório)", min_value=0, step=1, value=0)
                        rotulo_ativo = "🔢 Número do Ativo (Obrigatório)" if ativos_da_base_lista else "🔢 Número do Ativo (Opcional)"
                        ativo_input = st.text_input(rotulo_ativo)
                        observacao = st.text_input("📝 Observação (opcional)")
                        
                        if st.form_submit_button("✓ Confirmar Contagem", type="primary", use_container_width=True):
                            ativo_l = ativo_input.strip().upper()
                            if qtd_fisica <= 0:
                                st.error("❌ Erro: Informe uma quantidade maior que 0!")
                            elif ativos_da_base_lista and not ativo_l:
                                st.error("❌ Erro: O número do Ativo é obrigatório!")
                            else:
                                agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                lote_val = str(item.iloc[0]['lote']) if 'lote' in item.columns else ""
                                
                                qtd_sistema_calculada = qtd_sis
                                if ativos_da_base_lista:
                                    if ativo_l in ativos_da_base_lista:
                                        linha_especifica = item[item[col_ativo_base].astype(str).str.upper().str.strip() == ativo_l]
                                        try: qtd_sistema_calculada = int(pd.to_numeric(linha_especifica.iloc[0][col_qtd], errors='coerce'))
                                        except: qtd_sistema_calculada = 1
                                    else:
                                        qtd_sistema_calculada = 0
                                        
                                dif_c = qtd_fisica - qtd_sistema_calculada
                                cursor = conn.cursor()
                                cursor.execute("""
                                    INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, observacao, operador, data_hora, lote)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (id_inventario_atual.replace("#",""), id_estoque_val, local_val, codigo_rastreio, desc_val, unid_val, qtd_sistema_calculada, qtd_fisica, dif_c, ativo_l, observacao, st.session_state.operador, agora, lote_val))
                                conn.commit()
                                
                                st.session_state.ultimo_item_sucesso = f"✅ Lançamento Efetuado: O item '{codigo_rastreio}' foi adicionado!"
                                st.session_state.contador_reset += 1
                                st.rerun()
                else:
                    st.error("❌ Código não localizado.")

    # --- ABA 2: CONTAGEM ATUAL (RETORNADO OS 4 CARDS E BANNER DE PROGRESSO DE ACORDO COM O SEU PEDIDO) ---
    with aba_atual:
        if id_inventario_atual:
            st.subheader(f"Inventário: {id_inventario_atual} – {inventario_selecionado_obj['nome']} ({inventario_selecionado_obj['data']})")
            
            if df_contagens_mutaveis.empty:
                st.info("Nenhum item foi auditado neste inventário corrente.")
            else:
                # Cálculos dinâmicos para o topo da tela
                total_auditado = len(df_contagens_mutaveis)
                itens_divergentes = len(df_contagens_mutaveis[df_contagens_mutaveis['diferenca'] != 0])
                soma_contada = int(df_contagens_mutaveis['qtd_contada'].sum())
                soma_sistema = int(df_contagens_mutaveis['qtd_sistema'].sum())
                diferenca_acumulada = int(df_contagens_mutaveis['diferenca'].sum())
                porcentagem_divergencia = (itens_divergentes / total_auditado) * 100 if total_auditado > 0 else 0
                
                # Renderização fiel dos 4 blocos informativos no topo da aba
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">📦 ITENS CONTADOS</div><div class="bloco-valor">{total_auditado}</div></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">⚠️ COM DIVERGÊNCIA</div><div class="bloco-valor">{itens_divergentes}</div></div>', unsafe_allow_html=True)
                with c3:
                    st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">🔢 QTD TOTAL CONTADA</div><div class="bloco-valor">{soma_contada}</div></div>', unsafe_allow_html=True)
                with c4:
                    st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">🗄️ QTD TOTAL SISTEMA</div><div class="bloco-valor">{soma_sistema} <span style="font-size:14px; color:#e74c3c;">(↓ {abs(diferenca_acumulada)})</span></div></div>', unsafe_allow_html=True)
                
                # Banner de aviso laranja idêntico ao solicitado
                st.markdown(f"""
                    <div class="alerta-divergencia">
                        <strong>⚠️ {itens_divergentes} item(ns) apresentando divergência ou inconformidade de Ativo/Quantidade ({porcentagem_divergencia:.0f}%)</strong>
                    </div>
                """, unsafe_allow_html=True)
                
                # Tabela de dados estruturada
                ordem_colunas_print = ['id', 'inventario_id', 'id_estoque', 'desc_estoque', 'cod_produto', 'desc_produto', 'unid_medida', 'qtd_sistema', 'qtd_contada', 'diferenca', 'ativo', 'observacao', 'operador', 'data_hora']
                st.dataframe(df_contagens_mutaveis[ordem_colunas_print], use_container_width=True, hide_index=True)
                
                if inventario_selecionado_obj['status'] == "Aberto":
                    id_para_remover = st.selectbox("Selecione o ID da linha para excluir contagem:", [""] + df_contagens_mutaveis['id'].tolist(), key="del_sel_atual")
                    if id_para_remover and st.button("🗑️ Excluir linha selecionada"):
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM contagens WHERE id = ?", (id_para_remover,))
                        conn.commit()
                        st.toast("Linha removida!")
                        st.rerun()
        else:
            st.info("Nenhum inventário selecionado.")

    # --- ABA 3: HISTÓRICO DE INVENTÁRIOS ---
    with aba_historico:
        st.write("### 📁 Histórico de Inventários Arquivados")
        for idx, inv in df_inventarios.iterrows():
            df_hist_inv = pd.read_sql_query(f"SELECT * FROM contagens WHERE inventario_id = '{inv['id'].replace('#','')}' ORDER BY id DESC", conn)
            with st.expander(f"📁 {inv['id']} – {inv['nome']} | {inv['data']} | {len(df_hist_inv)} itens"):
                if not df_hist_inv.empty:
                    ordem_colunas_print = ['id', 'inventario_id', 'id_estoque', 'desc_estoque', 'cod_produto', 'desc_produto', 'unid_medida', 'qtd_sistema', 'qtd_contada', 'diferenca', 'ativo', 'observacao', 'operador', 'data_hora']
                    st.dataframe(df_hist_inv[ordem_colunas_print], use_container_width=True, hide_index=True)
                    
                    c_dl, c_del = st.columns([4, 2])
                    with c_dl:
                        buffer = io.BytesIO()
                        df_hist_inv[ordem_colunas_print].to_excel(buffer, index=False, engine='openpyxl')
                        st.download_button(label="📥 Exportar para Excel (.xlsx)", data=buffer.getvalue(), file_name=f"Inventario_{inv['id']}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_{inv['id']}")
                    with c_del:
                        if st.session_state.operador == "admin" or st.session_state.operador == "Administrador Tel":
                            if st.button("❌ Excluir Definitivamente", key=f"del_inv_{inv['id']}", use_container_width=True):
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM inventarios WHERE id = ?", (inv['id'],))
                                cursor.execute("DELETE FROM contagens WHERE inventario_id = ?", (inv['id'].replace('#',''),))
                                conn.commit()
                                st.rerun()

    # --- ABA 4: BASE DE ESTOQUE ---
    with aba_base:
        if st.session_state.base_sistema is not None:
            st.dataframe(st.session_state.base_sistema, use_container_width=True)
        else:
            st.info("Nenhuma base carregada.")

    # --- ABA 5: DESEMPENHO ---
    with aba_graficos:
        st.write("### 🏆 Ranking de Lançamentos por Operador")
        df_ops = pd.read_sql_query("SELECT operador as Operador, COUNT(id) as [Lançamentos Feitos] FROM contagens GROUP BY operador", conn)
        if not df_ops.empty:
            st.bar_chart(data=df_ops, x='Operador', y='Lançamentos Feitos', color="#d35400")
            
    conn.close()
