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
    
    # --- MIGRAÇÕES E CARGA INICIAL DE VALORES PADRÕES ---
    try:
        cursor.execute("PRAGMA table_info(usuarios)")
        cols = [c[1] for c in cursor.fetchall()]
        if "cargo" not in cols:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN cargo TEXT DEFAULT 'Almoxarife'")
            conn.commit()
    except:
        pass

    # Garantir que os administradores e seu usuário comecem com nível máximo
    try:
        cursor.execute("UPDATE usuarios SET cargo = 'Supervisor' WHERE nome LIKE '%Yago Rodrigues%' OR nome LIKE '%Administrador%'")
        conn.commit()
    except:
        pass

    # Inserção padrão caso a tabela de estoques iniciais de Jurubatuba esteja vazia
    cursor.execute("SELECT COUNT(*) FROM cadastros_estoques WHERE unidade = 'JURUBATUBA'")
    if cursor.fetchone()[0] == 0:
        estoques_padrao_jba = [
            ("1077", "JBA - CLASSE D"), ("1078", "JBA - COPA E COZINHA"),
            ("1080", "JBA - DADOS - CLIENTE"), ("1082", "JBA - VIVO VITA - CLIENTE"),
            ("1084", "JBA - EPI-EPC"), ("1086", "JBA - EQUIPAMENTOS"),
            ("1088", "JBA - FERRAMENTAL"), ("1089", "JBA - KIT FERRAMENTAL CONTRATACOES"),
            ("1090", "JBA - FERRAMENTAS DE CANTEIRO"), ("1102", "1385 - LA JBA - CLIENTE"),
            ("1104", "JBA - MATERIAL DE ESCRITORIO - SUPRIMENTOS DE INFORMATICA"), ("1106", "JBA - MOBILIARIO"),
            ("1108", "1071 - EXEC SEGREGADO IMPLANTACAO JBA - CLIENTE"), ("1113", "1385 - MANUTENCAO JBA - CLIENTE"),
            ("1118", "JBA - PROPRIO GERAL"), ("1122", "JBA - GRANDES OBRAS IMPLANTACAO"),
            ("1124", "JBA - PROPRIO TIM"), ("1140", "JBA - SPEEDY/FTTX - CLIENTE"),
            ("1144", "1385 - MANUTENCAO JBA CLIENTE RESERVADO"), ("1149", "JBA - UNIFORME"),
            ("2149", "JBA - SPEEDY/FTTX DEVOLUCAO NOVO COM DEFEITO - CLIENTE"), ("2183", "1071 - BOL IMPLANTANCAO JBA - CLIENTE"),
            ("2185", "JBA - PROPRIO FATURA B PLANTA EXTERNA - BDI"), ("2188", "1071 - IMPLANTACAO JBA CLIENTE RESERVADO"),
            ("2189", "JBA - DEFEITO"), ("2190", "JBA - DEPARTAMENTO T.I"),
            ("2194", "JBA - KITS FERRAMENTAL - DEVOLUCAO"), ("2197", "JBA - EQUIPAMENTOS TI"),
            ("2641", "1259 - IMPLANTACAO JBA - MATERIAL REUTILIZACAO"), ("2643", "1724 - MANUTENCAO JBA - MATERIAL REUTILIZACAO"),
            ("2725", "JBA - RESERVA TIM"), ("2983", "JBA - FORNECEDORES P/ MANUTENCAO - RECARGA"),
            ("3193", "JBA - PROPRIO MATERIAL REAPROVEITAVEL"), ("3395", "LPA - FTTX - CLIENTE"),
            ("3484", "JBA - CELULARES DEFEITO"), ("3546", "JBA - CELULARES")
        ]
        cursor.executemany("INSERT OR IGNORE INTO cadastros_estoques (id, descricao, unidade) VALUES (?, ?, 'JURUBATUBA')", estoques_padrao_jba)
        conn.commit()

    # Criar administrador raiz se não existir nenhum registro
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO usuarios (nome, cpf, email, senha, unidade, cargo) 
            VALUES (?, ?, ?, ?, ?, 'Supervisor')
        """, ("Administrador Tel", "00000000000", "admin@tel.com.br", "123", "JURUBATUBA"))
        
    conn.commit()
    conn.close()

inicializar_banco()

# --- ESTADOS DE SESSÃO DA PLATAFORMA ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'operador' not in st.session_state:
    st.session_state.operador = ""
if 'tela_acesso' not in st.session_state:
    st.session_state.tela_acesso = "login"
if 'unidade_selecionada' not in st.session_state:
    st.session_state.unidade_selecionada = "JURUBATUBA"
if 'cargo_usuario' not in st.session_state:
    st.session_state.cargo_usuario = "Almoxarife"
if 'base_sistema' not in st.session_state:
    st.session_state.base_sistema = None

# --- ESTILIZAÇÃO INTERNA CSS ---
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
    }
    </style>
""", unsafe_allow_html=True)

def limpar_documento(doc):
    return str(doc).strip().replace(".", "").replace("-", "").replace("/", "")

# --- GESTÃO DE ACESSO / LOGIN ---
if not st.session_state.logged_in:
    conn = conectar_banco()
    _, col_login_focada, _ = st.columns([3, 4, 3])
    
    with col_login_focada:
        if st.session_state.tela_acesso == "login":
            st.markdown("<h2 style='text-align: center;'>🔒 Acesso ao Sistema JBA</h2>", unsafe_allow_html=True)
            with st.form("login_form"):
                identificador = st.text_input("CPF (somente números) ou E-mail")
                senha = st.text_input("Senha", type="password")
                unidade_login = st.selectbox("📍 Localidade da Operação", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"])
                
                if st.form_submit_button("Entrar no Sistema", type="primary", use_container_width=True):
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
                        st.error("❌ Credenciais incorretas ou não vinculadas a esta localidade!")
                        
            c_cad, c_rec = st.columns(2)
            with c_cad:
                if st.button("📝 Criar nova conta", use_container_width=True):
                    st.session_state.tela_acesso = "cadastro"; st.rerun()
            with c_rec:
                if st.button("🔑 Alterar Senha", use_container_width=True):
                    st.session_state.tela_acesso = "recuperar"; st.rerun()
                    
        elif st.session_state.tela_acesso == "cadastro":
            st.markdown("<h2 style='text-align: center;'>📝 Cadastro de Colaborador</h2>", unsafe_allow_html=True)
            with st.form("cadastro_form"):
                novo_nome = st.text_input("Nome Completo")
                novo_cpf = st.text_input("CPF (Apenas números)")
                novo_email = st.text_input("E-mail")
                nova_senha = st.text_input("Senha", type="password")
                confirma_senha = st.text_input("Confirme a Senha", type="password")
                unidade_cadastro = st.selectbox("📍 Vincular à Localidade", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"])
                
                if st.form_submit_button("Finalizar Cadastro", type="primary", use_container_width=True):
                    cpf_l = limpar_documento(novo_cpf)
                    email_l = novo_email.strip()
                    if not novo_nome or not cpf_l or not email_l or not nova_senha:
                        st.error("⚠️ Preencha todos os campos!")
                    elif nova_senha != confirma_senha:
                        st.error("❌ As senhas não conferem!")
                    else:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO usuarios (nome, cpf, email, senha, unidade, cargo) VALUES (?, ?, ?, ?, ?, 'Almoxarife')", (novo_nome.strip(), cpf_l, email_l, nova_senha, unidade_cadastro))
                            conn.commit()
                            st.success("✅ Cadastro efetuado com sucesso! Aguarde o supervisor conceder permissões se necessário.")
                            st.session_state.tela_acesso = "login"
                            st.rerun()
                        except:
                            st.error("❌ CPF ou E-mail já registrado no sistema.")
            if st.button("◀ Voltar"):
                st.session_state.tela_acesso = "login"; st.rerun()
    conn.close()

# --- TELA INTERNA PRINCIPAL DO SISTEMA ---
else:
    conn = conectar_banco()
    
    # Validação de permissões de visualização hierárquica
    nome_limpo_check = st.session_state.operador.lower()
    eh_supervisor = st.session_state.cargo_usuario == "Supervisor" or "yago" in nome_limpo_check or "admin" in nome_limpo_check
    eh_yago_master = "yago" in nome_limpo_check or "admin" in nome_limpo_check

    # Leitura dos inventários da unidade atual
    df_inventarios = pd.read_sql_query("SELECT * FROM inventarios WHERE unidade = ? ORDER BY id DESC", conn, params=(st.session_state.unidade_selecionada,))
    
    # MAPEAMENTO DE COLUNAS DA PLANILHA EXCEL CARREGADA
    col_cod, col_desc, col_local, col_unidade, col_qtd, col_id_estoque = "", "", "", "", "", ""
    if st.session_state.base_sistema is not None:
        colunas_reais = list(st.session_state.base_sistema.columns)
        def encontrar_coluna(opcoes, default_idx):
            for opcao in opcoes:
                for col in colunas_reais:
                    if opcao.lower().replace(" ", "") in col.lower().replace(" ", ""):
                        return col
            return colunas_reais[default_idx] if default_idx < len(colunas_reais) else colunas_reais[0]
        col_cod = encontrar_coluna(['códproduto', 'codproduto', 'codigo'], 0)
        col_desc = encontrar_coluna(['descproduto', 'descricao'], 1)
        col_local = encontrar_coluna(['descestoquefisico', 'localizacao'], 2)
        col_qtd = encontrar_coluna(['qtdestoque', 'quantidade', 'saldo'], -1)
        col_id_estoque = encontrar_coluna(['idestoquefísico', 'idestoque'], 0)

    # BARRA LATERAL (SIDEBAR)
    with st.sidebar:
        st.subheader(f"🏢 Unidade: {st.session_state.unidade_selecionada}")
        st.write(f"👤 **Usuário:** {st.session_state.operador}")
        st.write(f"💼 **Perfil:** {st.session_state.cargo_usuario}")
        
        if st.button("🚪 Desconectar", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.operador = ""
            st.rerun()
            
        st.markdown("---")
        st.write("📂 **Carregar Planilha Base de Estoque**")
        arquivo_excel = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"], label_visibility="collapsed")
        if arquivo_excel is not None and st.session_state.base_sistema is None:
            st.session_state.base_sistema = pd.read_excel(arquivo_excel)
            st.rerun()
            
        st.markdown("---")
        st.write("📁 **Seleção do Inventário Ativo**")
        if df_inventarios.empty:
            st.info("Nenhum inventário aberto nesta unidade.")
            id_inventario_atual = None
            inventario_selected_obj = None
        else:
            lista_inv = [f"{row['id']} – {row['nome']} ({row['status']})" for idx, row in df_inventarios.iterrows()]
            inventario_selected = st.selectbox("Selecione", lista_inv, label_visibility="collapsed")
            id_inventario_atual = inventario_selected.split(" – ")[0]
            inventario_selected_obj = df_inventarios[df_inventarios['id'] == id_inventario_atual].iloc[0]

        if eh_supervisor:
            with st.expander("➕ Criar Novo Lote de Inventário"):
                with st.form("form_novo_inv", clear_on_submit=True):
                    nome_inv_f = st.text_input("Identificação do Lote")
                    if st.form_submit_button("Gerar", type="primary") and nome_inv_f:
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM inventarios ORDER BY ROWID DESC LIMIT 1")
                        last = cursor.fetchone()
                        prox_id = int(last[0].replace('#','')) + 1 if last else 1
                        cursor.execute("INSERT INTO inventarios (id, nome, data, status, unidade) VALUES (?, ?, ?, 'Aberto', ?)", (f"#{prox_id}", nome_inv_f, datetime.date.today().strftime("%Y-%m-%d"), st.session_state.unidade_selecionada))
                        conn.commit()
                        st.rerun()

    # MONTAGEM DINÂMICA DAS ABAS BASEADO NO CARGO DO USUÁRIO
    lista_abas = ["🔍 Bipar / Contar", "📊 Contagens Realizadas"]
    if eh_supervisor:
        lista_abas += ["⚙️ Gerenciar Estoques (Unidade)", "🏆 Desempenho e Prazos", "📁 Histórico da Unidade"]
    if eh_yago_master:
        lista_abas += ["👥 Controle de Usuários e Acessos"]
        
    abas = st.tabs(lista_abas)
    
    # ABA 1: BIPAGEM (COMUM A TODOS)
    with abas[0]:
        if id_inventario_atual is None or st.session_state.base_sistema is None:
            st.warning("⚠️ Carregue a planilha de saldos na barra lateral e selecione um lote de inventário ativo para liberar a contagem.")
        elif inventario_selected_obj['status'] == "Fechado":
            st.error("🔒 Este lote de inventário encontra-se fechado e consolidado.")
        else:
            cod_bipado = st.text_input("💻 Bipar Código do Item / Produto", value="", placeholder="Aguardando leitura do leitor...")
            if cod_bipado:
                item_filtrado = st.session_state.base_sistema[st.session_state.base_sistema[col_cod].astype(str).str.strip() == cod_bipado.strip()]
                if not item_filtrado.empty:
                    row_item = item_filtrado.iloc[0]
                    st.info(f"📦 **Item:** {cod_bipado} - {row_item[col_desc]} | **Local Padrão:** {row_item[col_local]}")
                    with st.form("form_salvar_contagem", clear_on_submit=True):
                        qtd_f = st.number_input("Quantidade Física Contada", min_value=0, step=1)
                        ativo_f = st.text_input("Número do Ativo / Etiqueta Patrimonial (Opcional)")
                        if st.form_submit_button("Confirmar Lançamento"):
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO contagens (inventario_id, id_estoque, desc_estoque, cod_produto, desc_produto, unid_medida, qtd_sistema, qtd_contada, diferenca, ativo, operador, data_hora, unidade)
                                VALUES (?, ?, ?, ?, ?, 'UN', ?, ?, ?, ?, ?, ?, ?)
                            """, (id_inventario_atual.replace("#",""), str(row_item[col_id_estoque]), str(row_item[col_local]), cod_bipado, str(row_item[col_desc]), int(row_item[col_qtd]), qtd_f, qtd_f - int(row_item[col_qtd]), ativo_f.upper().strip(), st.session_state.operador, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.unidade_selecionada))
                            conn.commit()
                            st.success("✅ Lançamento computado!")
                            st.rerun()
                else:
                    st.error("❌ Código de material não localizado na planilha base de dados.")

    # ABA 2: VISUALIZAR LANÇAMENTOS (COMUM A TODOS)
    with abas[1]:
        st.subheader("📋 Histórico Recente de Lançamentos")
        if id_inventario_atual:
            df_contados_rec = pd.read_sql_query("SELECT operador, cod_produto, desc_produto, desc_estoque, qtd_contada, data_hora FROM contagens WHERE inventario_id = ? AND unidade = ?", conn, params=(id_inventario_atual.replace('#',''), st.session_state.unidade_selecionada))
            st.dataframe(df_contados_rec, use_container_width=True)

    # RECURSOS EXCLUSIVOS: SUPERVISOR REGIONAL
    if eh_supervisor:
        # ABA 3: GERENCIAR ESTOQUES DINAMICAMENTE
        with abas[2]:
            st.title("⚙️ Gerenciamento de Estoques Físicos da Unidade")
            st.write("Utilize este espaço para cadastrar, editar ou remover as sublocalidades e códigos de estoques que sua equipe audita temporariamente.")
            
            col_cad1, col_cad2 = st.columns([1, 2])
            with col_cad1:
                st.write("### ➕ Adicionar Novo Estoque")
                with st.form("form_add_estoque", clear_on_submit=True):
                    id_novo_est = st.text_input("ID do Estoque (Ex: 1077)")
                    desc_novo_est = st.text_input("Descrição do Estoque (Ex: JBA - CLASSE D)")
                    if st.form_submit_button("Cadastrar no Sistema", type="primary"):
                        if id_novo_est and desc_novo_est:
                            try:
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO cadastros_estoques (id, descricao, unidade) VALUES (?, ?, ?)", (id_novo_est.strip(), desc_novo_est.strip(), st.session_state.unidade_selecionada))
                                conn.commit()
                                st.success("🎉 Estoque cadastrado com sucesso!")
                                st.rerun()
                            except:
                                st.error("❌ Código de estoque já existente nesta filial.")
                        else:
                            st.warning("⚠️ Preencha ambos os campos.")
                            
            with col_cad2:
                st.write("### 📋 Estoques Ativos para Auditoria")
                df_estoques_atuais = pd.read_sql_query("SELECT id as 'ID Estoque', descricao as 'Descrição' FROM cadastros_estoques WHERE unidade = ? ORDER BY id", conn, params=(st.session_state.unidade_selecionada,))
                st.dataframe(df_estoques_atuais, use_container_width=True, hide_index=True)
                
                estoque_deletar = st.selectbox("Selecione um estoque para remover se necessário", df_estoques_atuais['ID Estoque'].tolist() if not df_estoques_atuais.empty else ["Nenhum"])
                if st.button("🗑️ Remover Estoque Selecionado") and estoque_deletar != "Nenhum":
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM cadastros_estoques WHERE id = ? AND unidade = ?", (estoque_deletar, st.session_state.unidade_selecionada))
                    conn.commit()
                    st.success("Removido com sucesso!")
                    st.rerun()

        # ABA 4: VALIDADE, STATUS E DIAS SEM CONTAR (DINÂMICO)
        with abas[3]:
            st.title("🏆 Validade e Prazos de Auditoria Temporal")
            df_meus_estoques = pd.read_sql_query("SELECT id, descricao FROM cadastros_estoques WHERE unidade = ?", conn, params=(st.session_state.unidade_selecionada,))
            
            df_datas_calculadas = pd.read_sql_query("SELECT id_estoque, MAX(data_hora) as ultima_data FROM contagens WHERE unidade = ? GROUP BY id_estoque", conn, params=(st.session_state.unidade_selecionada,))
            mapa_prazos = dict(zip(df_datas_calculadas['id_estoque'].astype(str).str.strip(), df_datas_calculadas['ultima_data']))
            
            hoje_dt = datetime.datetime.now()
            linhas_prazos = []
            
            for _, r_est in df_meus_estoques.iterrows():
                id_e = str(r_est['id']).strip()
                ultima_data_str = mapa_prazos.get(id_e, None)
                if ultima_data_str:
                    try:
                        dt_c = datetime.datetime.strptime(ultima_data_str, "%Y-%m-%d %H:%M:%S")
                        dias_passados = (hoje_dt - dt_c).days
                        data_exibida = dt_c.strftime("%d/%m/%Y %H:%M")
                    except: dias_passados = 999; data_exibida = "Sem histórico válido"
                else:
                    dias_passados = 999; data_exibida = "Nunca Contado"
                    
                status_f = "🟢 Bom" if dias_passados <= 7 else "🟡 Precisa de Atenção" if dias_passados <= 14 else "🔴 Crítico"
                linhas_prazos.append({
                    "Id. Estoque Físico": id_e,
                    "Descrição": r_est['descricao'],
                    "Última Contagem": data_exibida,
                    "Dias sem Contar": dias_passados if dias_passados != 999 else "—",
                    "Status": status_f
                })
                
            if linhas_prazos:
                st.dataframe(pd.DataFrame(linhas_prazos), use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum subestoque configurado para monitoramento temporal.")

        # ABA 5: HISTÓRICO DA UNIDADE
        with abas[4]:
            st.title("📁 Arquivo Geral de Movimentações da Unidade")
            df_consolidados = pd.read_sql_query("SELECT * FROM inventarios WHERE unidade = ?", conn, params=(st.session_state.unidade_selecionada,))
            st.dataframe(df_consolidados, use_container_width=True, hide_index=True)

    # ABA RESTRITA MÁXIMA (YAGO SOBERANO / MASTER ADMIN)
    if eh_yago_master:
        with abas[-1]:
            st.title("👥 Painel de Controle e Gestão de Usuários")
            df_usuarios_totais = pd.read_sql_query("SELECT id, nome, cpf, email, senha, unidade, cargo FROM usuarios ORDER BY unidade, nome", conn)
            st.dataframe(df_usuarios_totais, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.write("### 🛠️ Alterar Atribuições e Níveis de Acesso")
            with st.form("form_ajuste_permissao"):
                id_alvo = st.selectbox("Selecione o Usuário para Ajuste", df_usuarios_totais['id'].tolist(), format_func=lambda x: f"ID {x} - {df_usuarios_totais[df_usuarios_totais['id']==x]['nome'].values[0]} ({df_usuarios_totais[df_usuarios_totais['id']==x]['unidade'].values[0]})")
                dados_alvo = df_usuarios_totais[df_usuarios_totais['id'] == id_alvo].iloc[0]
                
                nome_editado = st.text_input("Nome Completo", value=dados_alvo['nome'])
                senha_editada = st.text_input("Senha", value=dados_alvo['senha'])
                unidade_editada = st.selectbox("Unidade de Lotação", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"], index=["JURUBATUBA", "JUNDIAI", "CUBATÃO"].index(dados_alvo['unidade']))
                
                # SELETOR DE NÍVEL DE PERMISSÃO / CARGO SOLICITADO
                cargo_atual_idx = ["Almoxarife", "Supervisor"].index(dados_alvo['cargo']) if dados_alvo['cargo'] in ["Almoxarife", "Supervisor"] else 0
                cargo_editado = st.selectbox("💼 Cargo (Nível de Acesso)", ["Almoxarife", "Supervisor"], index=cargo_atual_idx)
                
                if st.form_submit_button("💾 Salvar Alterações", type="primary"):
                    cursor = conn.cursor()
                    cursor.execute("UPDATE usuarios SET nome = ?, senha = ?, unidade = ?, cargo = ? WHERE id = ?", (nome_editado.strip(), senha_editada.strip(), unidade_editada, cargo_editado, id_alvo))
                    conn.commit()
                    st.success("✅ Privilégios salvos e alterados no banco com sucesso!")
                    st.rerun()

    conn.close()
