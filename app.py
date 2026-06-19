import streamlit as st
import pandas as pd
import time

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTADO DA SESSÃO
# ==============================================================================
st.set_page_config(page_title="Controle de Estoque Interligado", layout="wide")

# Inicialização de banco de dados simulado no Session State
if "usuarios" not in st.session_state:
    st.session_state.usuarios = [
        {"usuario": "adm", "senha": "123", "perfil": "ADM", "localidade": "TODAS", "cpf": "00000000000", "email": "adm@empresa.com"},
        {"usuario": "alm_jundiai", "senha": "123", "perfil": "Almoxarife", "localidade": "JUNDIAI", "cpf": "22222222222", "email": "alm.jundiai@empresa.com"},
    ]

if "solicitacoes_reset" not in st.session_state:
    st.session_state.solicitacoes_reset = []

# Dicionário estruturado por localidade para isolar os dados
if "inventarios_dados" not in st.session_state:
    st.session_state.inventarios_dados = {} 

if "logado" not in st.session_state:
    st.session_state.logado = False

# Gatilho para limpar o campo de texto do BIPE
if "input_key" not in st.session_state:
    st.session_state.input_key = 0

# ==============================================================================
# 2. TELA DE AUTENTICAÇÃO (LOGIN / CADASTRO)
# ==============================================================================
def tela_autenticacao():
    st.title("🔐 Sistema de Controle de Estoque")
    aba_login, aba_cadastro = st.tabs(["Acessar Conta", "Criar Novo Login"])
    
    with aba_login:
        with st.form("login_form"):
            usuario = st.text_input("Usuário / Login")
            senha = st.text_input("Senha", type="password")
            botao_entrar = st.form_submit_button("Entrar")
            
            if botao_entrar:
                user_auth = next((u for u in st.session_state.usuarios if u["usuario"] == usuario and u["senha"] == senha), None)
                if user_auth:
                    st.session_state.logado = True
                    st.session_state.user_atual = user_auth
                    st.success(f"Bem-vindo, {usuario}!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
                    
        if st.button("Esqueci minha senha"):
            st.warning("🔒 Solicitação enviada! Por favor, entre em contato com o ADM do APP.")
            st.session_state.solicitacoes_reset.append({"usuario": usuario if usuario else "Desconhecido", "data": time.strftime("%H:%M:%S")})

    with aba_cadastro:
        st.subheader("📝 Formulário de Primeiro Acesso")
        with st.form("cadastro_form"):
            novo_user = st.text_input("Nome de Usuário")
            novo_cpf = st.text_input("CPF")
            novo_email = st.text_input("E-mail Corporativo")
            nova_senha_cad = st.text_input("Senha", type="password")
            nova_loc = st.selectbox("Sua Localidade", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"])
            botao_cadastrar = st.form_submit_button("Solicitar Cadastro")
            
            if botao_cadastrar:
                if novo_user and novo_cpf and novo_email and nova_senha_cad:
                    st.session_state.usuarios.append({
                        "usuario": novo_user, "senha": nova_senha_cad, 
                        "perfil": "Almoxarife", "localidade": nova_loc,
                        "cpf": novo_cpf, "email": novo_email
                    })
                    st.success("Cadastro realizado com sucesso!")
                else:
                    st.error("Preencha todos os campos.")

if not st.session_state.logado:
    tela_autenticacao()
    st.stop()

# Dados do usuário conectado
u_atual = st.session_state.user_atual
localidade = u_atual["localidade"]

if localidade == "TODAS":
    if "adm_localidade_escolhida" not in st.session_state:
        st.session_state.adm_localidade_escolhida = "JUNDIAI"
    localidade = st.session_state.adm_localidade_escolhida

# Garante que a estrutura daquela localidade específica exista
if localidade not in st.session_state.inventarios_dados:
    st.session_state.inventarios_dados[localidade] = {
        "banco_original": None,
        "inventarios_criados": {},
        "inventario_ativo": None
    }

loc_db = st.session_state.inventarios_dados[localidade]

# ==============================================================================
# 3. BARRA LATERAL (SIDEBAR) - CONTROLADOR COMPLETO
# ==============================================================================
with st.sidebar:
    st.title("🏭 Painel de Controle")
    st.subheader("👤 Identificação")
    st.write(f"**Localidade:** {u_atual['localidade']}")
    if u_atual['localidade'] == "TODAS":
        localidade = st.selectbox("Simular Planta:", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"], index=1)
        st.session_state.adm_localidade_escolhida = localidade
    st.write(f"**Login:** {u_atual['usuario']}")
    st.write(f"**Função:** {u_atual['perfil']}")
    
    @st.fragment(run_every=5)
    def render_btn_atualizar():
        st.button("🔄 Atualizar Dados (Auto 5s)", use_container_width=True)
    render_btn_atualizar()
    
    if st.button("🚪 Sair (Logoff)", use_container_width=True):
        st.session_state.logado = False
        st.rerun()
        
    st.divider()
    st.subheader("📥 Carga de Arquivos")
    uploaded_file = st.file_uploader("Upload Banco de Dados (Excel/CSV)", type=["xlsx", "csv"], key=f"file_{localidade}")
    if uploaded_file:
        df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        
        # Limpeza padronizada nos nomes das colunas da planilha
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # --- REGRA DE IDENTIFICAÇÃO E REPADRONIZAÇÃO EXATA DE COLUNAS ---
        mapeamento_colunas = {}
        for c in df.columns:
            if c in ["CÓD. PRODUTO", "COD. PRODUTO", "COD PRODUTO", "COD_PRODUTO"]:
                mapeamento_colunas[c] = "CÓD. PRODUTO"
            if c in ["DESC. PRODUTO", "DESC PRODUTO", "DESCRIÇÃO", "DESCRICAO"]:
                mapeamento_colunas[c] = "DESC. PRODUTO"
            if c in ["UNID. MEDIDA", "UNID MEDIDA", "UNIDADE MEDIDA", "UN"]:
                mapeamento_colunas[c] = "UNID. MEDIDA"
            if c in ["QTD ESTOQUE", "QTD ESTOQUE ", "QTD_ESTOQUE", "ESTOQUE SISTEMA", "ESTOQUE_SISTEMA"]:
                mapeamento_colunas[c] = "QTD ESTOQUE"
            if c in ["LOTE", "LOTES"]:
                mapeamento_colunas[c] = "LOTE"
            if c in ["ATIVO", "ATIVOS"]:
                mapeamento_colunas[c] = "ATIVO"
        
        if mapeamento_colunas:
            df = df.rename(columns=mapeamento_colunas)
            
        # Fallbacks de segurança se as colunas obrigatórias não existirem na planilha
        if "CÓD. PRODUTO" not in df.columns:
            df = df.rename(columns={df.columns[0]: "CÓD. PRODUTO"})
        if "DESC. PRODUTO" not in df.columns:
            df["DESC. PRODUTO"] = "Não Informado"
        if "UNID. MEDIDA" not in df.columns:
            df["UNID. MEDIDA"] = "UN"
        if "QTD ESTOQUE" not in df.columns:
            df["QTD ESTOQUE"] = 0
        
        if "CONTADO" not in df.columns: df["CONTADO"] = "Não"
        if "QTD_FISICA" not in df.columns: df["QTD_FISICA"] = 0
        
        loc_db["banco_original"] = df
        st.success("Banco de dados carregado com sucesso!")

    st.divider()
    st.subheader("📋 Gerenciamento de Inventários")
    
    nova_desc = st.text_input("Descrição do Novo Inventário:")
    if st.button("➕ Abrir Inventário", use_container_width=True) and nova_desc:
        if loc_db["banco_original"] is not None:
            loc_db["inventarios_criados"][nova_desc] = loc_db["banco_original"].copy()
            loc_db["inventario_ativo"] = nova_desc
            st.success(f"Inventário '{nova_desc}' Aberto!")
            st.rerun()
        else:
            st.error("Faça o upload do banco de dados primeiro!")
            
    lista_invs = list(loc_db["inventarios_criados"].keys())
    if lista_invs:
        inv_selecionado = st.selectbox("Selecionar Inventário Ativo:", lista_invs, index=lista_invs.index(loc_db["inventario_ativo"]) if loc_db["inventario_ativo"] else 0)
        loc_db["inventario_ativo"] = inv_selecionado
    else:
        st.info("Nenhum inventário aberto ainda.")

    st.divider()
    st.subheader("📊 Progresso da Contagem")
    if loc_db["inventario_ativo"]:
        df_ativo = loc_db["inventarios_criados"][loc_db["inventario_ativo"]]
        total_itens = len(df_ativo)
        contados = len(df_ativo[df_ativo["CONTADO"] == "Sim"])
        faltam = total_itens - contados
        porcentagem = (contados / total_itens) * 100 if total_itens > 0 else 0
        
        st.metric("Total de Itens", f"{total_itens}")
        st.metric("Contados", f"{contados} ({porcentagem:.1f}%)")
        st.metric("Faltam Contar", f"{faltam}")
        st.progress(porcentagem / 100)
    else:
        st.write("Nenhum inventário em andamento.")

# ==============================================================================
# 4. ÁREA CENTRAL - MÓDULOS OPERACIONAIS
# ==============================================================================
menu_abas = ["Contar Item", "Contagem Atual & Faltantes", "Base de Estoque (Sinalizada)", "Histórico & Outros"]
if u_atual["perfil"] == "ADM":
    menu_abas.append("Painel ADM")

abas_principais = st.tabs(menu_abas)

# ------------------------------------------------------------------------------
# TELA 1: CONTAR ITEM (EXIBIÇÃO DOS LOTES/ATIVOS DISPONÍVEIS NA BASE)
# ------------------------------------------------------------------------------
with abas_principais[0]:
    st.header("🔍 Área de Bipagem e Lançamento")
    
    if not loc_db["inventario_ativo"]:
        st.warning("⚠️ Abra ou Selecione um Inventário Ativo na barra lateral para começar a contagem.")
    else:
        nome_inv = loc_db["inventario_ativo"]
        df_atual = loc_db["inventarios_criados"][nome_inv]
        
        st.info(f"Inventário em Execução: **{nome_inv}**")
        
        codigo_bipado = st.text_input("BIPE O CÓDIGO DA ETIQUETA:", key=f"bipe_field_{st.session_state.input_key}")
        
        if codigo_bipado:
            input_string = str(codigo_bipado).strip()
            if " - " in input_string:
                codigo_limpo = input_string.split(" - ")[-1].strip().upper()
            else:
                codigo_limpo = input_string.upper()
                
            codigo_limpo = codigo_limpo.split('.')[0]
            
            df_atual['CODIGO_COMP_INTERNO'] = df_atual['CÓD. PRODUTO'].astype(str).str.strip().str.split('.').str[0].str.upper()
            
            # Buscamos TODOS os registros correspondentes ao código na base para cruzar Lotes/Ativos repetidos
            itens_iguais = df_atual[df_atual["CODIGO_COMP_INTERNO"] == codigo_limpo]
            
            if itens_iguais.empty:
                st.error(f"❌ Código '{codigo_limpo}' extraído não localizado na coluna 'CÓD. PRODUTO' do Banco de Dados.")
            else:
                idx_item = itens_iguais.index[0]
                row = itens_iguais.iloc[0]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.text_input("Descrição do Produto", value=row["DESC. PRODUTO"], disabled=True)
                with col2:
                    st.text_input("Unidade de Medida (UNID. MEDIDA)", value=row["UNID. MEDIDA"], disabled=True)
                with col3:
                    st.text_input("Quantidade Sistema (QTD ESTOQUE)", value=str(row["QTD ESTOQUE"]), disabled=True)
                
                tem_ativo = "ATIVO" in df_atual.columns
                tem_lote = "LOTE" in df_atual.columns
                
                col_din1, col_din2 = st.columns(2)
                val_ativo = ""
                val_lote = ""
                
                with col_din1:
                    if tem_ativo:
                        val_ativo = st.text_input("📋 Número do ATIVO (OBRIGATÓRIO):", key="campo_ativo")
                    else:
                        st.caption("ℹ️ Campo 'ATIVO' não exigido (Coluna ausente na planilha).")
                        
                with col_din2:
                    if tem_lote:
                        val_lote = st.text_input("🔢 Número do LOTE (OBRIGATÓRIO):", key="campo_lote")
                    else:
                        st.caption("ℹ️ Campo 'LOTE' não exigido (Coluna ausente na planilha).")
                
                # --- NOVO BLOCO EXIBIDOR DE INFORMACÕES MENORES (LOTES E ATIVOS DA BASE) ---
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    if tem_ativo:
                        # Remove duplicados e valores nulos/vazios antes de listar
                        ativos_encontrados = itens_iguais["ATIVO"].dropna().astype(str).str.strip().unique()
                        ativos_encontrados = [a for a in ativos_encontrados if a and a.lower() != 'nan']
                        if ativos_encontrados:
                            st.caption(f"📋 **Ativos do produto encontrados no Banco:** `{', '.join(ativos_encontrados)}`")
                        else:
                            st.caption("📋 *Nenhum Ativo pré-cadastrado na base para este produto.*")
                
                with col_info2:
                    if tem_lote:
                        lotes_encontrados = itens_iguais["LOTE"].dropna().astype(str).str.strip().unique()
                        lotes_encontrados = [l for l in lotes_encontrados if l and l.lower() != 'nan']
                        if lotes_encontrados:
                            st.caption(f"🔢 **Lotes do produto encontrados no Banco:** `{', '.join(lotes_encontrados)}`")
                        else:
                            st.caption("🔢 *Nenhum Lote pré-cadastrado na base para este produto.*")
                
                qtd_fisica = st.number_input("📥 Quantidade Física Contada:", min_value=0, step=1, value=int(row["QTD_FISICA"]) if row["CONTADO"] == "Sim" else 0)
                
                if st.button("💾 Confirmar e Registrar Contagem", use_container_width=True):
                    if tem_ativo and not val_ativo:
                        st.error("Erro: O preenchimento do campo ATIVO é obrigatório para salvar este item.")
                    elif tem_lote and not val_lote:
                        st.error("Erro: O preenchimento do campo LOTE é obrigatório para salvar este item.")
                    else:
                        loc_db["inventarios_criados"][nome_inv].at[idx_item, "CONTADO"] = "Sim"
                        loc_db["inventarios_criados"][nome_inv].at[idx_item, "QTD_FISICA"] = qtd_fisica
                        
                        if tem_ativo: loc_db["inventarios_criados"][nome_inv].at[idx_item, "ATIVO"] = val_ativo
                        if tem_lote: loc_db["inventarios_criados"][nome_inv].at[idx_item, "LOTE"] = val_lote
                        
                        st.success(f"Item {codigo_limpo} registrado com sucesso!")
                        
                        st.session_state.input_key += 1
                        time.sleep(0.4)
                        st.rerun()

# ------------------------------------------------------------------------------
# TELA 2: CONTAGEM ATUAL & FALTANTES
# ------------------------------------------------------------------------------
with abas_principais[1]:
    st.header("📋 Status das Contagens em Andamento")
    if not loc_db["inventario_ativo"]:
        st.info("Nenhum inventário selecionado.")
    else:
        df_view = loc_db["inventarios_criados"][loc_db["inventario_ativo"]].copy()
        if 'CODIGO_COMP_INTERNO' in df_view.columns:
            df_view = df_view.drop(columns=['CODIGO_COMP_INTERNO'])
            
        aba_ja_contados, aba_faltantes = st.tabs(["✅ Itens Já Contados", "❌ Itens Faltando Contar"])
        
        with aba_ja_contados:
            df_contados = df_view[df_view["CONTADO"] == "Sim"]
            if df_contados.empty:
                st.write("Nenhum item bipado neste inventário até o momento.")
            else:
                st.dataframe(df_contados, use_container_width=True)
                
        with aba_faltantes:
            df_nao_contados = df_view[df_view["CONTADO"] == "Não"]
            if df_nao_contados.empty:
                st.success("🎉 Excelente! Todos os itens cadastrados foram bipados e auditados.")
            else:
                st.dataframe(df_nao_contados, use_container_width=True)

# ------------------------------------------------------------------------------
# TELA 3: BASE DE ESTOQUE SINALIZADA VISUALMENTE (VERDE / VERMELHO)
# ------------------------------------------------------------------------------
with abas_principais[2]:
    st.header("🗄️ Visão Geral da Base de Estoque")
    if not loc_db["inventario_ativo"]:
        st.info("Carregue uma base e inicie um inventário para visualizar.")
    else:
        st.write("Abaixo consta a base de estoque original e suas atualizações de contagem em tempo real:")
        df_completo = loc_db["inventarios_criados"][loc_db["inventario_ativo"]].copy()
        
        if 'CODIGO_COMP_INTERNO' in df_completo.columns:
            df_completo = df_completo.drop(columns=['CODIGO_COMP_INTERNO'])
            
        def colorir_status(val):
            color = '#d4edda' if val == 'Sim' else '#f8d7da'
            return f'background-color: {color}'
            
        try:
            st.dataframe(df_completo.style.applymap(colorir_status, subset=['CONTADO']), use_container_width=True)
        except:
            st.dataframe(df_completo, use_container_width=True)

# ------------------------------------------------------------------------------
# TELA 4: RELATÓRIOS E HISTÓRICO
# ------------------------------------------------------------------------------
with abas_principais[3]:
    st.subheader("🕒 Histórico, Desempenho e Auditorias")
    st.info("Painéis e diretórios operacionais consolidados de forma segregada.")

# ------------------------------------------------------------------------------
# TELA 5: CONTROLE MASTER ADMINISTRATIVO
# ------------------------------------------------------------------------------
if u_atual["perfil"] == "ADM":
    with abas_principais[4]:
        st.header("👑 Painel Administrativo Master")
        
        if st.session_state.solicitacoes_reset:
            st.error("🚨 Pedidos de Reset de Senha Recebidos:")
            for r in st.session_state.solicitacoes_reset:
                st.write(f"- Usuário **{r['usuario']}** solicitou redefinição de acesso.")
            if st.button("Limpar Histórico de Alertas"):
                st.session_state.solicitacoes_reset = []
        else:
            st.success("Nenhuma solicitação pendente no servidor.")
            
        st.write("### Base de Credenciais de Colaboradores")
        st.dataframe(pd.DataFrame(st.session_state.usuarios), use_container_width=True)
