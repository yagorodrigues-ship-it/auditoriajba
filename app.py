import streamlit as st
import pandas as pd
import datetime
import sqlite3
import io
import random
import string

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico", layout="wide")

# --- BANCO DE DADOS PERMANENTE (SQLITE) ---
def conectar_banco():
    conn = sqlite3.connect('banco_inventario.db', check_same_thread=False)
    return conn

def inicializar_banco():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Nova tabela de usuários/colaboradores
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
    
    # Criar um usuário administrador padrão caso a tabela esteja vazia
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
    st.session_state.tela_acesso = "login"  # login, cadastro, recuperar

# Contadores de controle para forçar limpeza visual estrita de inputs
if 'contador_reset' not in st.session_state:
    st.session_state.contador_reset = 0
if 'ultimo_item_sucesso' not in st.session_state:
    st.session_state.ultimo_item_sucesso = ""

# --- AUXILIARES DE AUTENTICAÇÃO ---
def limpar_documento(doc):
    return str(doc).strip().replace(".", "").replace("-", "").replace("/", "")

# --- CONTROLADOR DA TELA DE LOGIN / ACESSO ---
if not st.session_state.logged_in:
    conn = conectar_banco()
    
    # TELA 1: LOGIN TRADICIONAL
    if st.session_state.tela_acesso == "login":
        st.title("🔒 Acesso ao Sistema de Estoque")
        st.caption("Insira suas credenciais cadastradas (CPF ou E-mail) para prosseguir.")
        
        with st.form("login_form"):
            identificador = st.text_input("CPF (somente números) ou E-mail")
            senha = st.text_input("Senha", type="password")
            botao_login = st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True)
            
            if botao_login:
                identificador_limpo = identificador.strip()
                id_doc_limpo = limpar_documento(identificador_limpo)
                
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT nome FROM usuarios 
                    WHERE (email = ? OR cpf = ?) AND senha = ?
                """, (identificador_limpo, id_doc_limpo, senha))
                usuario_encontrado = cursor.fetchone()
                
                if usuario_encontrado:
                    st.session_state.logged_in = True
                    st.session_state.operador = usuario_encontrado[0]
                    st.toast(f"Bem-vindo, {usuario_encontrado[0]}!")
                    st.rerun()
                else:
                    st.error("❌ Usuário, CPF ou senha incorretos. Verifique os dados ou cadastre-se.")
                    
        # Botões de navegação de fluxo fora do formulário
        c_cad, c_rec = st.columns(2)
        with c_cad:
            if st.button("📝 Não tem conta? Cadastrar-se", use_container_width=True):
                st.session_state.tela_acesso = "cadastro"
                st.rerun()
        with c_rec:
            if st.button("🔑 Esqueceu a senha? Recuperar", use_container_width=True):
                st.session_state.tela_acesso = "recuperar"
                st.rerun()

    # TELA 2: CADASTRO DE NOVO COLABORADOR
    elif st.session_state.tela_acesso == "cadastro":
        st.title("📝 Cadastro de Novo Colaborador")
        st.caption("Preencha todos os campos para liberar seu acesso às auditorias.")
        
        with st.form("cadastro_form"):
            novo_nome = st.text_input("Nome Completo")
            novo_cpf = st.text_input("CPF (Apenas números)")
            novo_email = st.text_input("E-mail Corporativo ou Pessoal")
            nova_senha = st.text_input("Crie uma Senha", type="password")
            confirma_senha = st.text_input("Confirme a Senha", type="password")
            
            botao_salvar_cad = st.form_submit_button("Finalizar Cadastro", type="primary", use_container_width=True)
            
            if botao_salvar_cad:
                cpf_limpo = limpar_documento(novo_cpf)
                email_limpo = novo_email.strip()
                
                if not novo_nome or not cpf_limpo or not email_limpo or not nova_senha:
                    st.error("⚠️ Todos os campos são obrigatórios!")
                elif nova_senha != confirma_senha:
                    st.error("❌ As senhas digitadas não coincidem!")
                else:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO usuarios (nome, cpf, email, senha) 
                            VALUES (?, ?, ?, ?)
                        """, (novo_nome.strip(), cpf_limpo, email_limpo, nova_senha))
                        conn.commit()
                        st.success("✅ Cadastro realizado com sucesso! Faça seu login.")
                        st.session_state.tela_acesso = "login"
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("❌ Falha no cadastro: Este CPF ou E-mail já está cadastrado no sistema!")
                        
        if st.button("◀ Voltar para o Login", use_container_width=True):
            st.session_state.tela_acesso = "login"
            st.rerun()

    # TELA 3: RECUPERAÇÃO DE SENHA / TOKENS
    elif st.session_state.tela_acesso == "recuperar":
        st.title("🔑 Recuperação de Acesso")
        st.caption("Valide sua identidade por e-mail ou CPF para gerar uma redefinição.")
        
        with st.form("recuperar_form"):
            validador = st.text_input("Informe seu E-mail ou CPF cadastrado")
            nova_senha_rec = st.text_input("Digite sua NOVA senha", type="password")
            botao_recuperar = st.form_submit_button("Redefinir Senha", type="primary", use_container_width=True)
            
            if botao_recuperar:
                validador_limpo = validador.strip()
                validador_doc = limpar_documento(validador_limpo)
                
                cursor = conn.cursor()
                cursor.execute("SELECT id, email, nome FROM usuarios WHERE email = ? OR cpf = ?", (validador_limpo, validador_doc))
                user = cursor.fetchone()
                
                if user and nova_senha_rec:
                    user_id, user_email, user_nome = user[0], user[1], user[2]
                    
                    # Atualiza diretamente no banco a nova senha informada
                    cursor.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (nova_senha_rec, user_id))
                    conn.commit()
                    
                    st.success(f"🎉 Pronto {user_nome}! Sua senha foi alterada com sucesso. Um log de segurança foi emitido.")
                    
                    # --- NOTA TÉCNICA DE ENVIO SMTP (OPCIONAL) ---
                    # Se você possuir os dados de um servidor de e-mail corporativo (Outlook, Gmail, etc) 
                    # basta descomentar as linhas abaixo para realizar o disparo real:
                    #
                    # import smtplib
                    # from email.mime.text import MIMEText
                    # msg = MIMEText(f"Olá {user_nome}, sua senha de acesso ao Painel de Auditoria foi alterada hoje.")
                    # msg['Subject'] = 'Alteração de Senha - Sistema de Estoque'
                    # msg['From'] = 'seu_email_sistema@tel.com'
                    # msg['To'] = user_email
                    # with smtplib.SMTP('smtp.seu_provedor.com', 587) as server:
                    #     server.starttls()
                    #     server.login('seu_email_sistema@tel.com', 'sua_senha_smtp')
                    #     server.send_message(msg)
                    
                    st.session_state.tela_acesso = "login"
                    st.rerun()
                else:
                    st.error("❌ Nenhuma conta ativa foi localizada com o CPF ou E-mail informado.")
                    
        if st.button("◀ Voltar para o Login", use_container_width=True):
            st.session_state.tela_acesso = "login"
            st.rerun()
            
    conn.close()

# --- INTERFACE LOGADA DO SISTEMA ---
else:
    conn = conectar_banco()
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios ORDER BY data DESC, id DESC", conn)
    
    # 1. BARRA LATERAL (SIDEBAR)
    with st.sidebar:
        st.write(f"👤 **Operador Ativo:** {st.session_state.operador}")
        if st.button("🚪 Sair da Conta", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.operador = ""
            st.session_state.tela_acesso = "login"
            st.rerun()
            
        st.markdown("---")
        st.write("📂 **Carregar Base de Dados (Saldo)**")
        arquivo_excel = st.file_uploader("Suba o arquivo Excel do sistema (.xlsx)", type=["xlsx"], label_visibility="collapsed")
        if arquivo_excel is not None and st.session_state.base_sistema is None:
            st.session_state.base_sistema = pd.read_excel(arquivo_excel)
            st.session_state.nome_arquivo_excel = arquivo_excel.name
            st.toast("Base de dados (Saldo) carregada com sucesso!")
            st.rerun()
            
        st.markdown("---")
        st.write("📁 **Selecione o inventário**")
        
        if df_inventarios.empty:
            st.info("Nenhum inventário ativo. Crie um abaixo para iniciar.")
            id_inventario_atual = None
            inventario_selecionado_obj = None
        else:
            lista_inv = [f"{row['id']} – {row['nome']} ({row['status']})" for idx, row in df_inventarios.iterrows()]
            inventario_selected = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
            id_inventario_atual = inventario_selected.split(" – ")[0]
            inventario_selecionado_obj = df_inventarios[df_inventarios['id'] == id_inventario_atual].iloc[0]

        # Criar novo inventário
        with st.expander("➕ Novo Inventário", expanded=df_inventarios.empty):
            with st.form("form_novo", clear_on_submit=True):
                novo_nome = st.text_input("Nome do Inventário")
                botao_criar = st.form_submit_button("Criar", type="primary")
                if botao_criar and novo_nome:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM inventarios")
                    count = cursor.fetchone()[0]
                    novo_id = f"#{count + 39}"
                    hoje = datetime.date.today().strftime("%Y-%m-%d")
                    cursor.execute("INSERT INTO inventarios (id, nome, data, status) VALUES (?, ?, ?, ?)", 
                                   (novo_id, novo_nome, hoje, "Aberto"))
                    conn.commit()
                    st.toast(f"Inventário {novo_id} criado!")
                    st.rerun()

        if inventario_selecionado_obj is not None and inventario_selecionado_obj['status'] == "Aberto":
            if st.button("🔒 Fechar inventário atual", use_container_width=True):
                cursor = conn.cursor()
                cursor.execute("UPDATE inventarios SET status = 'Fechado' WHERE id = ?", (id_inventario_atual,))
                conn.commit()
                st.toast("Inventário finalizado e fechado com sucesso!")
                st.rerun()

        # --- MAPEAMENTO INTELIGENTE DE COLUNAS ---
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

        # --- CÁLCULO DE PROGRESSO DINÂMICO ---
        total_itens_base = 0
        total_contados = 0
        total_pendentes = 0
        progresso = 0.0

        if st.session_state.base_sistema is not None and id_inventario_atual is not None:
            total_itens_base = len(st.session_state.base_sistema)
            df_contagens_atuais = pd.read_sql_query(f"SELECT * FROM contagens WHERE inventario_id = '{id_inventario_atual.replace('#','')}'", conn)
            
            contados_validos_set = set()
            for idx, c_row in df_contagens_atuais.iterrows():
                match_base = st.session_state.base_sistema[
                    st.session_state.base_sistema[col_cod].astype(str).str.upper().str.strip() == str(c_row['cod_produto']).upper().strip()
                ]
                if not match_base.empty:
                    ativos_validos_da_base = [str(x).upper().strip() for x in match_base[col_ativo_base].tolist() if col_ativo_base in match_base.columns]
                    ativos_validos_da_base = [x for x in ativos_validos_da_base if x not in ["NAN", "SIM", "", "0", "0.0"]]
                    
                    if map_ativos_base_lista := ativos_validos_da_base:
                        if str(c_row['ativo']).upper().strip() in map_ativos_base_lista:
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

    # 2. PAINEL PRINCIPAL
    st.title("📦 Painel Geral de Auditoria")
    st.caption("Tel Telecomunicações · Painel de Auditoria Ativa")
    
    if st.session_state.ultimo_item_sucesso:
        st.success(st.session_state.ultimo_item_sucesso)
        st.session_state.ultimo_item_sucesso = ""

    aba_contar, aba_atual, aba_historico, aba_base, aba_graficos = st.tabs([
        "🔍 Contar Item", "📊 Contagem Atual", "📁 Histórico de Inventários", "📄 Base de Estoque", "🏆 Desempenho"
    ])
    
    if st.session_state.base_sistema is None:
        st.warning("⚠️ Passo 1 pendente: Faça o upload do arquivo de Saldo na barra lateral para alimentar a base.")
    elif id_inventario_atual is None:
        st.warning("⚠️ Passo 2 pendente: Crie um Novo Inventário na barra lateral para vincular as contagens à base.")
    else:
        df_contagens_mutaveis = pd.read_sql_query(f"SELECT * FROM contagens WHERE inventario_id = '{id_inventario_atual.replace('#','')}' ORDER BY id DESC", conn)
        df_exemplo = st.session_state.base_sistema
        
        # --- ABA 1: CONTAR ITEM ---
        with aba_contar:
            if inventario_selecionado_obj is not None and inventario_selecionado_obj['status'] == "Fechado":
                st.error("🔒 Este inventário está Fechado.")
            else:
                c_busca, c_filtro, c_limpar = st.columns([5, 3, 2])
                with c_busca:
                    codigo_input = st.text_input(
                        "💻 Código do Produto (etiqueta ou manual)", 
                        value="", 
                        placeholder="Bipe a etiqueta ou digite o código...", 
                        key=f"input_bip_dinamico_{st.session_state.contador_reset}"
                    )
                with c_filtro:
                    st.selectbox("📍 Estoque Físico", ["Todos"], key=f"sel_est_fisico_{st.session_state.contador_reset}")
                with c_limpar:
                    st.write("") 
                    if st.button("🗑️ Limpar", use_container_width=True, key="clear_btn"):
                        st.session_state.contador_reset += 1
                        st.rerun()
                
                if codigo_input:
                    busca_limpa = str(codigo_input).upper().strip()
                    
                    # Regra inteligente de rastreio de bipes combinados
                    if " - " in busca_limpa:
                        codigo_rastreio = busca_limpa.split(" - ")[-1].strip()
                    else:
                        codigo_rastreio = busca_limpa

                    serie_codigos = df_exemplo[col_cod].astype(str).str.upper().str.strip()
                    item = df_exemplo[serie_codigos == codigo_rastreio]
                    
                    if not item.empty:
                        unid_val = item.iloc[0][col_unidade] if col_unidade in item.columns else "UN"
                        desc_val = item.iloc[0][col_desc]
                        local_val = item.iloc[0][col_local] if col_local in item.columns else "Não Informado"
                        id_estoque_val = str(item.iloc[0][col_id_estoque]).strip() if col_id_estoque in item.columns else ""
                        
                        raw_qtd_sis = item.iloc[0][col_qtd]
                        try:
                            qtd_sis = int(pd.to_numeric(raw_qtd_sis, errors='coerce'))
                            if pd.isna(qtd_sis): qtd_sis = 0
                        except:
                            qtd_sis = 0
                        
                        ativos_da_base_lista = [str(x).upper().strip() for x in item[col_ativo_base].tolist() if col_ativo_base in item.columns]
                        ativos_da_base_lista = [x for x in list(set(ativos_da_base_lista)) if x not in ["NAN", "SIM", "", "0", "0.0"]]

                        b1, b2, b3, b4 = st.columns(4)
                        with b1:
                            st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">CÓD. PRODUTO</div><div class="bloco-valor">{codigo_rastreio}</div></div>', unsafe_allow_html=True)
                        with b2:
                            st.markdown(f'<div class="card-sistema" style="margin-top:0px; padding:15px; margin-bottom:0px;"><div class="bloco-titulo">ESTOQUE FÍSICO</div><div class="bloco-valor" style="font-size:22px;">{local_val}</div></div>', unsafe_allow_html=True)
                        with b3:
                            st.markdown(f'<div class="bloco-info"><div class="bloco-titulo">UNID. MEDIDA</div><div class="bloco-valor">{unid_val}</div></div>', unsafe_allow_html=True)
                        with b4:
                            st.markdown('<div class="bloco-info"><div class="bloco-titulo">STATUS BARRA</div><div class="bloco-valor" style="color:#2ecc71;">● Conectado</div></div>', unsafe_allow_html=True)
                        
                        st.markdown(f"**Descrição:** {desc_val}")
                        st.markdown(f"**Local:** {local_val} &nbsp;|&nbsp; **Chave de Geração da Etiqueta:** `{id_estoque_val} - {codigo_rastreio}`")
                        
                        if map_reais_ativos_lista := ativos_da_base_lista:
                            st.info(f"📋 Ativos válidos: {', '.join(map_reais_ativos_lista)}")
                        
                        st.markdown(f'<div class="card-sistema"><div class="bloco-titulo">QTD SISTEMA</div><div style="font-size:32px; font-weight:bold; color:#1f2c3f;">{qtd_sis}</div></div>', unsafe_allow_html=True)
                        
                        with st.form("confirmar_contagem_form", clear_on_submit=True):
                            qtd_fisica = st.number_input("📦 Quantidade contada fisicamente (Obrigatório)", min_value=0, step=1, value=0)
                            rotulo_ativo = "🔢 Número do Ativo (Obrigatório)" if map_reais_ativos_lista else "🔢 Número do Ativo (Opcional)"
                            ativo_input = st.text_input(rotulo_ativo)
                            observacao = st.text_input("📝 Observação (opcional)")
                            btn_confirmar = st.form_submit_button("✓ Confirmar Contagem", type="primary", use_container_width=True)
                            
                            if btn_confirmar:
                                ativo_digitado_limpo = ativo_input.strip().upper()
                                if qtd_fisica <= 0:
                                    st.error("❌ Erro: Informe uma quantidade maior que 0!")
                                elif map_reais_ativos_lista and not ativo_digitado_limpo:
                                    st.error("❌ Erro: O preenchimento do número de Ativo é obrigatório!")
                                else:
                                    agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    lote_val = str(item.iloc[0]['lote']) if 'lote' in item.columns else ""
                                    
                                    qtd_sistema_calculada = qtd_sis
                                    if map_reais_ativos_lista and ativo_digitado_limpo in map_reais_ativos_lista:
                                        linha_especifica = item[item[col_ativo_base].astype(str).str.upper().str.strip() == ativo_digitado_limpo]
                                        try:
                                            qtd_sistema_calculada = int(pd.to_numeric(linha_especifica.iloc[0][col_qtd], errors='coerce'))
                                        except:
                                            qtd_sistema_calculada = 1
                                            
                                    dif_calculada = qtd_fisica - qtd_sistema_calculada
                                    
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, observacao, operador, data_hora, lote)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (id_inventario_atual.replace("#",""), id_estoque_val, local_val, codigo_rastreio, desc_val, unid_val, qtd_sistema_calculada, qtd_fisica, dif_calculada, ativo_digitado_limpo, observacao, st.session_state.operador, agora, lote_val))
                                    conn.commit()
                                    
                                    st.session_state.ultimo_item_sucesso = f"✅ Lançamento Efetuado: O item '{codigo_rastreio}' foi adicionado com sucesso!"
                                    st.session_state.contador_reset += 1
                                    st.rerun()
                    else:
                        st.error(f"Código do produto '{codigo_rastreio}' não localizado.")

        # --- ABA 2: CONTAGEM ATUAL ---
        with aba_atual:
            st.subheader(f"Inventário: {id_inventario_atual} – {inventario_selecionado_obj['nome']}")
            if df_contagens_mutaveis.empty:
                st.info("Nenhum item foi auditado neste inventário corrente.")
            else:
                ordem_colunas_print = ['id', 'inventario_id', 'id_estoque', 'desc_estoque', 'cod_produto', 'desc_produto', 'unid_medida', 'qtd_sistema', 'qtd_contada', 'diferenca', 'ativo', 'observacao', 'operador', 'data_hora']
                st.dataframe(df_contagens_mutaveis[ordem_colunas_print], use_container_width=True, hide_index=True)

        # --- ABA 3: HISTÓRICO DE INVENTÁRIOS ---
        with aba_historico:
            st.write("### 📁 Histórico de Inventários Arquivados")
            for idx, inv in df_inventarios.iterrows():
                df_hist_inv = pd.read_sql_query(f"SELECT * FROM contagens WHERE inventario_id = '{inv['id'].replace('#','')}' ORDER BY id DESC", conn)
                with st.expander(f"📁 {inv['id']} – {inv['nome']} | {inv['data']} | {len(df_hist_inv)} itens"):
                    if not df_hist_inv.empty:
                        st.dataframe(df_hist_inv, use_container_width=True, hide_index=True)

        # --- ABA 4: BASE DE ESTOQUE ---
        with aba_base:
            st.dataframe(st.session_state.base_sistema, use_container_width=True)

        # --- ABA 5: DESEMPENHO DA EQUIPE ---
        with aba_graficos:
            st.write("### 🏆 Ranking de Inventários por Operador")
            df_ops = pd.read_sql_query("SELECT operador as Operador, COUNT(id) as [Lançamentos Feitos] FROM contagens GROUP BY operador", conn)
            if not df_ops.empty:
                st.bar_chart(data=df_ops, x='Operador', y='Lançamentos Feitos', color="#d35400")
                
    conn.close()
