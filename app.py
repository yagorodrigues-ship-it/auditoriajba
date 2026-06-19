import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E SESSÃO
# ==============================================================================
st.set_page_config(page_title="Controle de Estoque Interligado", layout="wide")

# Inicialização do banco de dados simulado no Session State
# Em produção, substitua por um banco de dados real (SQLite, PostgreSQL, etc.)
if "usuarios" not in st.session_state:
    st.session_state.usuarios = [
        {"usuario": "adm", "senha": "123", "perfil": "ADM", "localidade": "TODAS"},
        {"usuario": "sup_jundiai", "senha": "123", "perfil": "Supervisor", "localidade": "JUNDIAI"},
        {"usuario": "alm_jundiai", "senha": "123", "perfil": "Almoxarife", "localidade": "JUNDIAI"},
        {"usuario": "alm_cubatao", "senha": "123", "perfil": "Almoxarife", "localidade": "CUBATÃO"},
    ]

if "inventarios" not in st.session_state:
    # Armazena os itens carregados e contados por localidade
    st.session_state.inventarios = {} 

if "historico" not in st.session_state:
    st.session_state.historico = []

if "auditorias" not in st.session_state:
    st.session_state.auditorias = []

if "logado" not in st.session_state:
    st.session_state.logado = False

# ==============================================================================
# 2. SESSÃO DE LOGIN
# ==============================================================================
def tela_login():
    st.title("🔐 Sistema de Controle de Estoque")
    with st.form("login_form"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        botao = st.form_submit_button("Entrar")
        
        if botao:
            user_auth = next((u for u in st.session_state.usuarios if u["usuario"] == usuario and u["senha"] == senha), None)
            if user_auth:
                st.session_state.logado = True
                st.session_state.user_atual = user_auth
                st.success(f"Bem-vindo, {usuario}!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

if not st.session_state.logado:
    tela_login()
    st.stop()

# Dados do usuário logado
u_atual = st.session_state.user_atual
nome_usuario = u_atual["usuario"]
perfil_usuario = u_atual["perfil"]
localidade_usuario = u_atual["localidade"]

# ==============================================================================
# 3. SIDEBAR (MENU LATERAL)
# ==============================================================================
st.sidebar.title("📌 Painel do Usuário")
st.sidebar.write(f"**Colaborador:** {nome_usuario}")
st.sidebar.write(f"**Perfil:** {perfil_usuario}")
st.sidebar.write(f"**Localidade:** {localidade_usuario}")

if st.sidebar.button("Logoff"):
    st.session_state.logado = False
    st.rerun()

st.sidebar.divider()
st.sidebar.title("Navegação")

# Definição de telas por perfil
telas = ["Contar Item & Progresso", "Base de Estoque", "Histórico de Dados", "Desempenho e Prazos", "Acuracidade de Estoque"]
if perfil_usuario in ["Supervisor", "ADM"]:
    telas.extend(["Painel do Supervisor", "Auditoria Supervisor"])
if perfil_usuario == "ADM":
    telas.append("Painel ADM")

tela_selecionada = st.sidebar.radio("Ir para:", telas)

# Filtro global invisível: Garante que as localidades não se misturem
loc_filtro = localidade_usuario

# ==============================================================================
# 4. COMPONENTE DE ATUALIZAÇÃO EM TEMPO REAL (FRAGMENT)
# ==============================================================================
@st.fragment(run_every=10) # Atualiza a cada 10 segundos sem dar F5 na página toda
def widget_tempo_real():
    st.subheader("🔄 Monitoramento em Tempo Real (Auto-refresh 10s)")
    # Simulação de métricas rápidas baseadas na localidade
    if loc_filtro == "TODAS":
        st.info("Visualizando dados consolidados de todas as plantas.")
    else:
        st.metric(label=f"Status Atual em {loc_filtro}", value="Inventário Ativo", delta="Aguardando bipagem")

# Executa o fragmento no topo da página
widget_tempo_real()
st.divider()

# ==============================================================================
# TELAS DO APLICATIVO
# ==============================================================================

# --- TELA 1: CONTAR ITEM & PROGRESSO ---
if tela_selecionada == "Contar Item & Progresso":
    st.title("📋 Contar Item & Progresso do Inventário")
    
    if loc_filtro == "TODAS":
        st.warning("Como ADM, selecione uma localidade para simular a contagem:")
        loc_filtro = st.selectbox("Localidade Simulada", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"])

    # Upload da Base (Visível para todos, mas regras se aplicam)
    uploaded_file = st.file_uploader("Upload do Banco de Dados (Excel/CSV)", type=["xlsx", "csv"])
    if uploaded_file:
        df_upload = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        if "inventarios" not in st.session_state: st.session_state.inventarios = {}
        st.session_state.inventarios[loc_filtro] = df_upload
        st.success(f"Base carregada com sucesso para a unidade {loc_filtro}!")

    # Controle de abertura de Inventário
    desc_inv = st.text_input("Descrição do Inventário Novo:")
    if st.button("Abrir Inventário"):
        st.session_state[f"status_inv_{loc_filtro}"] = "Aberto"
        st.session_state[f"desc_inv_{loc_filtro}"] = desc_inv
        st.success("Inventário Liberado para Contagem!")

    # Se o inventário estiver aberto, mostra a tela de BIPE e Progresso
    if st.session_state.get(f"status_inv_{loc_filtro}") == "Aberto":
        st.subheader("🔍 Área de Bipagem")
        codigo_bipado = st.text_input("BIPE O CÓDIGO DA ETIQUETA:")
        
        # Simulação de busca na planilha carregada
        if codigo_bipado:
            st.info(f"Produto Identificado: [Exemplo] Código {codigo_bipado}")
            # Verificação da coluna ATIVO obrigatória
            st.warning("⚠️ Coluna ATIVO detectada na planilha. Preenchimento do número do ativo obrigatório!")
            ativo_input = st.text_input("Digite o Número do Ativo:")
            qtd_contada = st.number_input("Quantidade Física Contada:", min_value=0, value=0)
            
            if st.button("Confirmar Contagem"):
                st.success("Item contabilizado!")
                # Aqui você salvaria a linha no dataframe do session_state correspondente à localidade

        # Indicadores de Progresso
        st.divider()
        st.subheader("📊 Progresso do Inventário")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Itens", "100")
        col2.metric("Faltam Contar", "45")
        col3.metric("Acuracidade Atual", "98.5%")
        
        # Fechamento de Inventário
        if st.button("Fechar Inventário"):
            # Regra: Só fecha se 100% ou se for Supervisor/ADM
            if perfil_usuario in ["Supervisor", "ADM"]:
                st.session_state[f"status_inv_{loc_filtro}"] = "Fechado"
                st.success("Inventário encerrado pelo Supervisor.")
            else:
                st.error("Erro: O inventário só pode ser fechado 100% concluído ou por um Supervisor.")

# --- TELA 2: BASE DE ESTOQUE ---
elif tela_selecionada == "Base de Estoque":
    st.title("🗄️ Base de Estoque")
    st.write(f"Exibindo dados da localidade: **{loc_filtro}**")
    if loc_filtro in st.session_state.inventarios:
        st.dataframe(st.session_state.inventarios[loc_filtro])
    else:
        st.info("Nenhuma base carregada para esta localidade ainda.")

# --- TELA 3: HISTÓRICO DE DADOS ---
elif tela_selecionada == "Histórico de Dados":
    st.title("📜 Histórico de Dados")
    # Filtro por data
    data_filtro = st.date_input("Filtrar por Data (Deixe em branco ou ignore para ver tudo)", value=None)
    
    st.write("Pastas de Inventários Arquivados (Limite de 10 por página):")
    # Paginação simples simulada
    page = st.number_input("Página", min_value=1, value=1)
    
    # Regra de Exportação/Exclusão do Supervisor
    if perfil_usuario in ["Supervisor", "ADM"]:
        st.button("📥 Exportar Pasta Selecionada para Excel")
        st.button("🚨 Excluir Pasta de Inventário")
    else:
        st.info("Visualização restrita. Apenas supervisores podem exportar ou excluir dados históricos.")

# --- TELA 4: DESEMPENHO E PRAZOS ---
elif tela_selecionada == "Desempenho e Prazos":
    st.title("⏱️ Desempenho e Prazos")
    st.write("Status de atualização dos estoques físicos por localidade:")
    
    # Tabela de prazos simulada
    dados_prazos = [
        {"Localidade": "JURUBATUBA", "Última Contagem": "Há 2 dias", "Status": "Bom"},
        {"Localidade": "JUNDIAI", "Última Contagem": "Há 7 dias", "Status": "Atenção"},
        {"Localidade": "CUBATÃO", "Última Contagem": "Há 15 dias", "Status": "Crítico"},
    ]
    
    for item in dados_prazos:
        if item["Status"] == "Bom": st.success(f"{item['Localidade']}: {item['Última Contagem']} - Status: {item['Status']}")
        elif item["Status"] == "Atenção": st.warning(f"{item['Localidade']}: {item['Última Contagem']} - Status: {item['Status']}")
        else: st.error(f"{item['Localidade']}: {item['Última Contagem']} - Status: {item['Status']}")

# --- TELA 5: ACURACIDADE DE ESTOQUE ---
elif tela_selecionada == "Acuracidade de Estoque":
    st.title("🎯 Acuracidade de Estoque (Auditorias)")
    st.metric("Porcentagem Geral de Acuracidade", "94.2%")
    st.checkbox("Material Devidamente Etiquetado", value=True, disabled=True)
    st.checkbox("Material Endereçado", value=True, disabled=True)
    
    st.write("### Pastas de Auditoria (Apenas Contagens do Supervisor)")
    # Mostra histórico exclusivo de auditorias

# --- TELA 6: PAINEL DO SUPERVISOR ---
elif tela_selecionada == "Painel do Supervisor":
    st.title("⚡ Painel do Supervisor")
    st.write(f"Gerenciamento da planta: {loc_filtro}")
    st.button("Adicionar Estoque Físico Alvo")
    st.button("Excluir Estoque Alvo")

# --- TELA 7: AUDITORIA SUPERVISOR ---
elif tela_selecionada == "Auditoria Supervisor":
    st.title("🕵️ Auditoria do Supervisor")
    st.button("Abrir Contagem de Auditoria")
    # Fluxo idêntico de auditoria que alimenta a tela de acuracidade

# --- TELA 8: PAINEL ADM ---
elif tela_selecionada == "Painel ADM":
    st.title("👑 Painel Administrativo (Master ADM)")
    
    st.write("### Usuários Cadastrados no Sistema")
    df_users = pd.DataFrame(st.session_state.usuarios)
    st.dataframe(df_users)
    
    st.write("### Alterar Cadastro / Resetar Senha")
    user_to_mod = st.selectbox("Selecione o usuário para alterar:", [u["usuario"] for u in st.session_state.usuarios])
    nova_senha = st.text_input("Nova Senha")
    novo_perfil = st.selectbox("Alterar Perfil", ["Almoxarife", "Supervisor", "ADM"])
    nova_loc = st.selectbox("Alterar Localidade", ["JURUBATUBA", "JUNDIAI", "CUBATÃO", "TODAS"])
    
    if st.button("Salvar Alterações do Usuário"):
        for u in st.session_state.usuarios:
            if u["usuario"] == user_to_mod:
                u["senha"] = nova_senha if nova_senha else u["senha"]
                u["perfil"] = novo_perfil
                u["localidade"] = nova_loc
        st.success(f"Usuário {user_to_mod} modificado com sucesso!")
