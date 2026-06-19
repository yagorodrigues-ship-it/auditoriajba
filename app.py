import streamlit as st
import pandas as pd
import time
from datetime import datetime

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTADO DA SESSÃO
# ==============================================================================
st.set_page_config(page_title="Controle de Estoque Interligado", layout="wide")

# Inicialização do banco de dados no Session State de forma fixa
if "usuarios" not in st.session_state:
    st.session_state.usuarios = [
        {"usuario": "adm", "senha": "123", "perfil": "ADM", "localidade": "TODAS", "cpf": "00000000000", "email": "adm@empresa.com"},
        {"usuario": "sup_jundiai", "senha": "123", "perfil": "Supervisor", "localidade": "JUNDIAI", "cpf": "11111111111", "email": "sup.jundiai@empresa.com"},
        {"usuario": "alm_jundiai", "senha": "123", "perfil": "Almoxarife", "localidade": "JUNDIAI", "cpf": "22222222222", "email": "alm.jundiai@empresa.com"},
    ]

if "solicitacoes_reset" not in st.session_state:
    st.session_state.solicitacoes_reset = []

if "inventarios_dados" not in st.session_state:
    st.session_state.inventarios_dados = {} 

if "logado" not in st.session_state:
    st.session_state.logado = False

if "input_key" not in st.session_state:
    st.session_state.input_key = 0

# ==============================================================================
# 2. TELA DE AUTENTICAÇÃO (LOGIN COM LOCALIDADE / CADASTRO REVISADO)
# ==============================================================================
def tela_autenticacao():
    st.title("🔐 Sistema de Controle de Estoque")
    aba_login, aba_cadastro = st.tabs(["Acessar Conta", "Criar Novo Login"])
    
    with aba_login:
        with st.form("login_form"):
            usuario = st.text_input("Usuário / Login").strip()
            senha = st.text_input("Senha", type="password").strip()
            # Adicionado a localidade obrigatória no ato do login
            localidade_login = st.selectbox("Selecione sua Localidade para Acesso", ["JURUBATUBA", "JUNDIAI", "CUBATÃO", "TODAS"])
            botao_entrar = st.form_submit_button("Entrar")
            
            if botao_entrar:
                # Validação cruzando Usuário, Senha e Localidade cadastrada
                user_auth = next((u for u in st.session_state.usuarios if 
                                  u["usuario"] == usuario and 
                                  u["senha"] == senha and 
                                  u["localidade"] == localidade_login), None)
                
                if user_auth:
                    st.session_state.logado = True
                    st.session_state.user_atual = user_auth
                    st.success(f"Bem-vindo, {usuario}!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Usuário, senha ou localidade incorretos para esta conta.")
                    
        if st.button("Esqueci minha senha"):
            st.warning("🔒 Solicitação enviada! Por favor, entre em contato com o ADM do APP.")
            st.session_state.solicitacoes_reset.append({"usuario": usuario if usuario else "Desconhecido", "data": time.strftime("%H:%M:%S")})

    with aba_cadastro:
        st.subheader("📝 Formulário de Primeiro Acesso")
        with st.form("cadastro_form"):
            novo_user = st.text_input("Defina seu Nome de Usuário (Sem espaços)").strip()
            novo_cpf = st.text_input("Digite seu CPF").strip()
            novo_email = st.text_input("E-mail Corporativo").strip()
            nova_senha_cad = st.text_input("Defina uma Senha", type="password").strip()
            nova_loc = st.selectbox("Selecione a sua Localidade de Trabalho", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"])
            botao_cadastrar = st.form_submit_button("Solicitar Cadastro")
            
            if botao_cadastrar:
                if novo_user and novo_cpf and novo_email and nova_senha_cad:
                    # Verifica se o usuário já existe para não duplicar
                    existe = any(u["usuario"] == novo_user for u in st.session_state.usuarios)
                    if existe:
                        st.error("Este nome de usuário já está sendo utilizado. Escolha outro.")
                    else:
                        # Insere diretamente na memória master global de usuários do app
                        st.session_state.usuarios.append({
                            "usuario": novo_user, 
                            "senha": nova_senha_cad, 
                            "perfil": "Almoxarife", 
                            "localidade": nova_loc,
                            "cpf": novo_cpf, 
                            "email": novo_email
                        })
                        st.success(f"Cadastro do usuário '{novo_user}' criado com sucesso para a localidade {nova_loc}! Mude para a aba 'Acessar Conta' para logar.")
                else:
                    st.error("Preencha todos os campos obrigatórios do formulário.")

if not st.session_state.logado:
    tela_autenticacao()
    st.stop()

u_atual = st.session_state.user_atual
localidade = u_atual["localidade"]

if localidade == "TODAS":
    if "adm_localidade_escolhida" not in st.session_state:
        st.session_state.adm_localidade_escolhida = "JUNDIAI"
    localidade = st.session_state.adm_localidade_escolhida

# Força a criação e garante todas as chaves mapeadas (Evita totalmente o KeyError)
if localidade not in st.session_state.inventarios_dados:
    st.session_state.inventarios_dados[localidade] = {}

loc_db = st.session_state.inventarios_dados[localidade]

if "banco_original" not in loc_db: loc_db["banco_original"] = None
if "inventarios_criados" not in loc_db: loc_db["inventarios_criados"] = {}
if "inventario_ativo" not in loc_db: loc_db["inventario_ativo"] = None
if "auditorias_criadas" not in loc_db: loc_db["auditorias_criadas"] = {}
if "prazos_alvo" not in loc_db: loc_db["prazos_alvo"] = "Não Definido"
if "historico_pastas" not in loc_db: loc_db["historico_pastas"] = []

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
        df.columns = [str(c).strip().upper() for c in df.columns]
        
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
menu_abas = ["Contar Item", "Contagem Atual & Faltantes", "Base de Estoque (Sinalizada)", "Histórico de Dados", "Desempenho e Prazos", "Acuracidade de Estoque"]
if u_atual["perfil"] in ["Supervisor", "ADM"]:
    menu_abas.extend(["Painel do Supervisor", "Auditoria Supervisor"])
if u_atual["perfil"] == "ADM":
    menu_abas.append("Painel ADM")

abas_principais = st.tabs(menu_abas)

# ------------------------------------------------------------------------------
# TELA 1: CONTAR ITEM
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
            
            itens_iguais = df_atual[df_atual["CODIGO_COMP_INTERNO"] == codigo_limpo]
            
            if itens_iguais.empty:
                st.error(f"❌ Código '{codigo_limpo}' extraído não localizado na coluna 'CÓD. PRODUTO' do Banco de Dados.")
            else:
                idx_item = itens_iguais.index[0]
                row = itens_iguais.iloc[0]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input("Descrição do Produto", value=row["DESC. PRODUTO"], disabled=True)
                with col2:
                    st.text_input("Unidade de Medida (UNID. MEDIDA)", value=row["UNID. MEDIDA"], disabled=True)
                
                lote_na_planilha = "LOTE" in df_atual.columns
                lote_valido = False
                if lote_na_planilha:
                    val_lote_original = str(row["LOTE"]).strip()
                    if val_lote_original and val_lote_original.lower() not in ["nan", "none", ""]:
                        lote_valido = True

                ativo_na_planilha = "ATIVO" in df_atual.columns
                ativo_valido = False
                if ativo_na_planilha:
                    val_ativo_original = str(row["ATIVO"]).strip()
                    if val_ativo_original and val_ativo_original.lower() not in ["nan", "none", ""]:
                        ativo_valido = True

                col_din1, col_din2 = st.columns(2)
                val_ativo = ""
                val_lote = ""
                
                with col_din1:
                    if ativo_valido:
                        val_ativo = st.text_input("📋 Número do ATIVO (OBRIGATÓRIO):", key="campo_ativo")
                    else:
                        st.caption("ℹ️ Campo 'ATIVO' não exigido para este produto.")
                        
                with col_din2:
                    if lote_valido:
                        val_lote = st.text_input("🔢 Número do LOTE (OBRIGATÓRIO):", key="campo_lote")
                    else:
                        st.caption("ℹ️ Campo 'LOTE' não exigido para este produto.")
                
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    if 'ATIVO' in df_atual.columns:
                        ativos_encontrados = itens_iguais["ATIVO"].dropna().astype(str).str.strip().unique()
                        ativos_encontrados = [a for a in ativos_encontrados if a and a.lower() not in ['nan', 'none']]
                        if ativos_encontrados:
                            st.caption(f"📋 Ativos salvos na base: `{', '.join(ativos_encontrados)}`")
                
                with col_info2:
                    if 'LOTE' in df_atual.columns:
                        lotes_encontrados = itens_iguais["LOTE"].dropna().astype(str).str.strip().unique()
                        lotes_encontrados = [l for l in lotes_encontrados if l and l.lower() not in ['nan', 'none']]
                        if lotes_encontrados:
                            st.caption(f"🔢 Lotes salvos na base: `{', '.join(lotes_encontrados)}`")
                
                qtd_fisica = st.number_input("📥 Quantidade Física Contada:", min_value=0, step=1, value=int(row["QTD_FISICA"]) if row["CONTADO"] == "Sim" else 0)
                
                if st.button("💾 Confirmar e Registrar Contagem", use_container_width=True):
                    if ativo_valido and not val_ativo:
                        st.error("Erro: O preenchimento do campo ATIVO é obrigatório para salvar este item.")
                    elif lote_valido and not val_lote:
                        st.error("Erro: O preenchimento do campo LOTE é obrigatório para salvar este item.")
                    else:
                        loc_db["inventarios_criados"][nome_inv].at[idx_item, "CONTADO"] = "Sim"
                        loc_db["inventarios_criados"][nome_inv].at[idx_item, "QTD_FISICA"] = qtd_fisica
                        if lote_na_planilha and val_lote: loc_db["inventarios_criados"][nome_inv].at[idx_item, "LOTE"] = val_lote
                        if ativo_na_planilha and val_ativo: loc_db["inventarios_criados"][nome_inv].at[idx_item, "ATIVO"] = val_ativo
                        
                        st.success(f"Item {codigo_limpo} registrado com sucesso!")
                        st.session_state.input_key += 1
                        time.sleep(0.4)
                        st.rerun()
        
        st.divider()
        st.subheader("🔒 Encerramento do Inventário")
        total_itens = len(df_atual)
        contados = len(df_atual[df_atual["CONTADO"] == "Sim"])
        concluido_100 = (total_itens == contados and total_itens > 0)
        
        if st.button("🏁 Fechar Inventário Atual", use_container_width=True):
            if concluido_100:
                loc_db["historico_pastas"].append({"nome": nome_inv, "data": time.strftime("%d/%m/%Y"), "tipo": "Almoxarifado", "dados": df_atual.copy()})
                loc_db["inventarios_criados"].pop(nome_inv)
                loc_db["inventario_ativo"] = None
                st.success("🎉 Inventário 100% concluído e fechado com sucesso!")
                time.sleep(0.5)
                st.rerun()
            else:
                if u_atual["perfil"] in ["Supervisor", "ADM"]:
                    loc_db["historico_pastas"].append({"nome": nome_inv, "data": time.strftime("%d/%m/%Y"), "tipo": "Almoxarifado (Forçado pelo Supervisor)", "dados": df_atual.copy()})
                    loc_db["inventarios_criados"].pop(nome_inv)
                    loc_db["inventario_ativo"] = None
                    st.success("⚠️ Inventário incompleto encerrado e arquivado com autorização do Supervisor.")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Erro: O inventário não está 100% concluído. Entre em contato com seu Supervisor para autorizar o fechamento.")

# ------------------------------------------------------------------------------
# TELA 2: CONTAGEM ATUAL & FALTANTES
# ------------------------------------------------------------------------------
with abas_principais[1]:
    st.header("📋 Status das Contagens em Andamento")
    if not loc_db["inventario_ativo"]:
        st.info("Nenhum inventário selecionado.")
    else:
        df_view = loc_db["inventarios_criados"][loc_db["inventario_ativo"]].copy()
        if 'CODIGO_COMP_INTERNO' in df_view.columns: df_view = df_view.drop(columns=['CODIGO_COMP_INTERNO'])
            
        aba_ja_contados, aba_faltantes = st.tabs(["✅ Itens Já Contados", "❌ Itens Faltando Contar"])
        with aba_ja_contados:
            df_contados = df_view[df_view["CONTADO"] == "Sim"]
            st.dataframe(df_contados, use_container_width=True)
        with aba_faltantes:
            df_nao_contados = df_view[df_view["CONTADO"] == "Não"]
            st.dataframe(df_nao_contados, use_container_width=True)

# ------------------------------------------------------------------------------
# TELA 3: BASE DE ESTOQUE SINALIZADA VISUALMENTE
# ------------------------------------------------------------------------------
with abas_principais[2]:
    st.header("🗄️ Visão Geral da Base de Estoque")
    if not loc_db["inventario_ativo"]:
        st.info("Carregue uma base e inicie um inventário para visualizar.")
    else:
        df_completo = loc_db["inventarios_criados"][loc_db["inventario_ativo"]].copy()
        if 'CODIGO_COMP_INTERNO' in df_completo.columns: df_completo = df_completo.drop(columns=['CODIGO_COMP_INTERNO'])
            
        def colorir_status(val):
            return f'background-color: #d4edda' if val == 'Sim' else 'background-color: #f8d7da'
            
        try:
            st.dataframe(df_completo.style.applymap(colorir_status, subset=['CONTADO']), use_container_width=True)
        except:
            st.dataframe(df_completo, use_container_width=True)

# ------------------------------------------------------------------------------
# TELA 4: HISTÓRICO DE DADOS
# ------------------------------------------------------------------------------
with abas_principais[3]:
    st.header("📜 Histórico de Dados")
    data_filtro = st.date_input("Filtrar por data:", value=None)
    
    pastas = loc_db["historico_pastas"]
    if not pastas:
        st.info("Nenhuma pasta de inventário fechada para esta localidade.")
    else:
        itens_por_pagina = 10
        total_paginas = max(1, (len(pastas) + itens_por_pagina - 1) // itens_por_pagina)
        pagina = st.number_input("Página", min_value=1, max_value=total_paginas, value=1)
        
        idx_inicio = (pagina - 1) * itens_por_pagina
        idx_fim = idx_inicio + itens_por_pagina
        
        for idx, p in enumerate(pastas[idx_inicio:idx_fim]):
            with st.expander(f"📁 Pasta: {p['nome']} - Fechado em: {p['data']} ({p['tipo']})"):
                st.dataframe(p["dados"], use_container_width=True)
                
                if u_atual["perfil"] in ["Supervisor", "ADM"]:
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        st.download_button("📥 Exportar para Excel", data=p["dados"].to_csv(index=False).encode('utf-8'), file_name=f"{p['nome']}.csv", mime='text/csv', key=f"dl_{idx}")
                    with col_b2:
                        if st.button("🚨 Excluir Pasta", key=f"del_{idx}"):
                            pastas.pop(idx_inicio + idx)
                            st.success("Pasta removida!")
                            time.sleep(0.4)
                            st.rerun()

# ------------------------------------------------------------------------------
# TELA 5: DESEMPENHO E PRAZOS
# ------------------------------------------------------------------------------
with abas_principais[4]:
    st.header("⏱️ Desempenho e Prazos")
    st.write("Acompanhamento das últimas datas de contagem física das localidades:")
    
    dados_locs = ["JURUBATUBA", "JUNDIAI", "CUBATÃO"]
    for l in dados_locs:
        db_l = st.session_state.inventarios_dados.get(l, {})
        historicos = db_l.get("historico_pastas", [])
        alvo_fisico = db_l.get("prazos_alvo", "Nenhum alvo cadastrado")
        
        if historicos:
            ultima_data = historicos[-1]["data"]
            status = "Bom"
        else:
            ultima_data = "Sem registros"
            status = "Crítico"
            
        if status == "Bom":
            st.success(f"🏬 Planta: **{l}** | Alvo Físico: {alvo_fisico} | Última Contagem: {ultima_data} -> **Status: Bom**")
        else:
            st.error(f"🏬 Planta: **{l}** | Alvo Físico: {alvo_fisico} | Última Contagem: {ultima_data} -> **Status: Crítico**")

# ------------------------------------------------------------------------------
# TELA 6: ACURACIDADE DE ESTOQUE
# ------------------------------------------------------------------------------
with abas_principais[5]:
    st.header("🎯 Acuracidade de Estoque")
    
    auditorias = [p for p in loc_db["historico_pastas"] if p["tipo"] == "Auditoria Supervisor"]
    if not auditorias:
        st.info("Nenhuma auditoria realizada pelo supervisor nesta planta ainda.")
        st.metric("Porcentagem Geral de Acuracidade", "0.0%")
    else:
        df_aud = auditorias[-1]["dados"]
        total = len(df_aud)
        certos = len(df_aud[df_aud["QTD ESTOQUE"] == df_aud["QTD_FISICA"]])
        acuracidade = (certos / total) * 100 if total > 0 else 100
        
        st.metric("Porcentagem Geral de Acuracidade (Última Auditoria)", f"{acuracidade:.2f}%")
        
        st.write("### Pastas de Auditoria (Exclusivas do Supervisor)")
        for idx, audit in enumerate(auditorias):
            with st.expander(f"📁 Auditoria: {audit['nome']} - Realizada em: {audit['data']}"):
                st.dataframe(audit["dados"], use_container_width=True)

# ------------------------------------------------------------------------------
# TELA 7: PAINEL DO SUPERVISOR
# ------------------------------------------------------------------------------
if u_atual["perfil"] in ["Supervisor", "ADM"]:
    with abas_principais[6]:
        st.header("⚡ Painel do Supervisor")
        st.subheader(f"Gerenciamento de Alvos e Metas para: {localidade}")
        
        novo_alvo = st.text_input("Acrescentar/Definir Alvo de Estoque Físico para esta planta:")
        if st.button("Salvar Alvo Físico"):
            loc_db["prazos_alvo"] = novo_alvo
            st.success("Alvo updated! Aparecerá na tela de 'Desempenho e Prazos'.")
            
        if st.button("Excluir Alvo Atual"):
            loc_db["prazos_alvo"] = "Não Definido"
            st.warning("Alvo removido.")

# ------------------------------------------------------------------------------
# TELA 8: AUDITORIA SUPERVISOR
# ------------------------------------------------------------------------------
if u_atual["perfil"] in ["Supervisor", "ADM"]:
    with abas_principais[7]:
        st.header("🕵️ Auditoria Supervisor")
        
        desc_aud = st.text_input("Descrição da Nova Auditoria:")
        if st.button("Abrir Contagem de Auditoria"):
            if loc_db["banco_original"] is not None:
                loc_db["auditorias_criadas"][desc_aud] = loc_db["banco_original"].copy()
                st.success(f"Auditoria '{desc_aud}' iniciada!")
            else:
                st.error("Suba o banco de dados na sidebar primeiro.")
                
        lista_auds = list(loc_db["auditorias_criadas"].keys())
        if lista_auds:
            aud_sel = st.selectbox("Auditoria Ativa:", lista_auds)
            df_aud = loc_db["auditorias_criadas"][aud_sel]
            
            st.write("Dê o fechamento para alimentar a Acuracidade:")
            if st.button("🏁 Fechar e Salvar Auditoria"):
                loc_db["historico_pastas"].append({"nome": aud_sel, "data": time.strftime("%d/%m/%Y"), "tipo": "Auditoria Supervisor", "dados": df_aud.copy()})
                loc_db["auditorias_criadas"].pop(aud_sel)
                st.success("Auditoria processada!")
                time.sleep(0.4)
                st.rerun()

# ------------------------------------------------------------------------------
# TELA 9: PAINEL ADM (CONTROLE MASTER DE CONTAS)
# ------------------------------------------------------------------------------
if u_atual["perfil"] == "ADM":
    idx_adm = len(menu_abas) - 1
    with abas_principais[idx_adm]:
        st.header("👑 Painel Administrativo Master")
        
        if st.session_state.solicitacoes_reset:
            st.error("🚨 Pedidos de Reset de Senha Recebidos:")
            for r in st.session_state.solicitacoes_reset:
                st.write(f"- Usuário **{r['usuario']}** solicitou redefinição.")
            if st.button("Limpar Alertas de Redefinição"):
                st.session_state.solicitacoes_reset = []
        
        st.write("### Lista Geral de Colaboradores")
        st.dataframe(pd.DataFrame(st.session_state.usuarios), use_container_width=True)
        
        st.write("### 🛠️ Alterar Senha, Perfil e Localidade de Usuários")
        user_selecionado = st.selectbox("Escolha o usuário para modificar:", [u["usuario"] for u in st.session_state.usuarios])
        
        idx_user = next((i for i, u in enumerate(st.session_state.usuarios) if u["usuario"] == user_selecionado), None)
        
        if idx_user is not None:
            dados_user = st.session_state.usuarios[idx_user]
            
            nova_senha_adm = st.text_input("Nova Senha:", value=dados_user["senha"])
            novo_perfil_adm = st.selectbox("Nova Função:", ["Almoxarife", "Supervisor", "ADM"], index=["Almoxarife", "Supervisor", "ADM"].index(dados_user["perfil"]))
            nova_loc_adm = st.selectbox("Nova Localidade de Acesso:", ["JURUBATUBA", "JUNDIAI", "CUBATÃO", "TODAS"], index=["JURUBATUBA", "JUNDIAI", "CUBATÃO", "TODAS"].index(dados_user["localidade"]))
            
            if st.button("💾 Gravar Alterações de Cadastro"):
                st.session_state.usuarios[idx_user]["senha"] = nova_senha_adm
                st.session_state.usuarios[idx_user]["perfil"] = novo_perfil_adm
                st.session_state.usuarios[idx_user]["localidade"] = nova_loc_adm
                st.success(f"Cadastro do usuário '{user_selecionado}' atualizado perfeitamente!")
                time.sleep(0.4)
                st.rerun()
