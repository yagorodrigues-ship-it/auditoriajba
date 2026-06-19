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
        {"usuario": "sup_jundiai", "senha": "123", "perfil": "Supervisor", "localidade": "JUNDIAI", "cpf": "11111111111", "email": "sup.jundiai@empresa.com"},
        {"usuario": "alm_jundiai", "senha": "123", "perfil": "Almoxarife", "localidade": "JUNDIAI", "cpf": "22222222222", "email": "alm.jundiai@empresa.com"},
    ]

if "solicitacoes_reset" not in st.session_state:
    st.session_state.solicitacoes_reset = []

if "inventarios" not in st.session_state:
    st.session_state.inventarios = {} 

if "logado" not in st.session_state:
    st.session_state.logado = False

# ==============================================================================
# 2. TELA DE LOGIN, CADASTRO E RESET DE SENHA
# ==============================================================================
def tela_autenticacao():
    st.title("🔐 Sistema de Controle de Estoque")
    
    # Abas para separar Login de Cadastro
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
                    
        # Botão/Mecanismo fora do Form para Reset de Senha
        if st.button("Esqueci minha senha"):
            st.warning("🔒 Solicitação enviada! Por favor, entre em contato com o ADM do APP para liberar este reset.")
            # Registra uma simulação de pedido de reset para o painel do ADM ver
            st.session_state.solicitacoes_reset.append({"usuario": usuario if usuario else "Desconhecido", "data": time.strftime("%H:%M:%S")})

    with aba_cadastro:
        st.subheader("📝 Formulário de Primeiro Acesso (Almoxarife)")
        with st.form("cadastro_form"):
            novo_user = st.text_input("Defina um Nome de Usuário")
            novo_cpf = st.text_input("CPF (Somente números)")
            novo_email = st.text_input("E-mail Corporativo")
            nova_senha_cad = st.text_input("Defina uma Senha", type="password")
            nova_loc = st.selectbox("Sua Localidade", ["JURUBATUBA", "JUNDIAI", "CUBATÃO"])
            botao_cadastrar = st.form_submit_button("Solicitar Cadastro")
            
            if botao_cadastrar:
                if novo_user and novo_cpf and novo_email and nova_senha_cad:
                    # Todo cadastro via app entra como Almoxarife por padrão até o ADM validar/mudar
                    st.session_state.usuarios.append({
                        "usuario": novo_user, "senha": nova_senha_cad, 
                        "perfil": "Almoxarife", "localidade": nova_loc,
                        "cpf": novo_cpf, "email": novo_email
                    })
                    st.success("Cadastro realizado! Aguarde a liberação ou use seus dados para logar.")
                else:
                    st.error("Por favor, preencha todos os campos.")

if not st.session_state.logado:
    tela_autenticacao()
    st.stop()

# Dados do usuário logado
u_atual = st.session_state.user_atual
nome_usuario = u_atual["usuario"]
perfil_usuario = u_atual["perfil"]
localidade_usuario = u_atual["localidade"]

# ==============================================================================
# 3. BARRA SUPERIOR (AUTO-REFRESH SEM F5)
# ==============================================================================
# Mudando o local do monitoramento para o topo exato, simulando um cabeçalho fixo
@st.fragment(run_every=10)
def cabecalho_tempo_real():
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.markdown(f"### 🔄 Acompanhamento em Tempo Real (Localidade: **{localidade_usuario}**) — *Auto-refresh 10s*")
    with col_t2:
        # Mostra o progresso de itens rápido no topo de forma discreta
        st.caption("Progresso Atual: **55% Concluído** (55/100 itens)")

cabecalho_tempo_real()
st.divider()

# ==============================================================================
# 4. NAVEGAÇÃO CENTRALIZADA (UM AO LADO DO OUTRO)
# ==============================================================================
# Removido os botões de navegação da sidebar e transformados em botões horizontais/tabs na tela central
telas_disponiveis = ["Contar Item & Progresso", "Base de Estoque", "Histórico de Dados", "Desempenho e Prazos", "Acuracidade de Estoque"]
if perfil_usuario in ["Supervisor", "ADM"]:
    telas_disponiveis.extend(["Painel do Supervisor", "Auditoria Supervisor"])
if perfil_usuario == "ADM":
    telas_disponiveis.append("Painel ADM")

# Cria abas horizontais no centro da tela
abas_navegacao = st.tabs(telas_disponiveis)

# Guardamos qual aba está ativa mapeando o clique do usuário
for idx, aba in enumerate(abas_navegacao):
    with aba:
        tela_selecionada = telas_disponiveis[idx]
        
        # ==============================================================================
        # 5. DISPOSIÇÃO EM COLUNAS: LATERAL COM GERENCIAMENTO E CENTRO COM A CONTAGEM
        # ==============================================================================
        if tela_selecionada == "Contar Item & Progresso":
            st.header("📋 Contar Item & Progresso do Inventário")
            
            # Divide a tela: Esquerda (Upload, Descrição, Abertura) | Direita (Bipagem e Progresso)
            col_lateral_dados, col_central_contagem = st.columns([1, 2], gap="large")
            
            with col_lateral_dados:
                st.markdown("### ⚙️ Gerenciar Inventário")
                
                # Upload da planilha (sem campo de localidade, usa a do login)
                uploaded_file = st.file_uploader("Upload do Banco de Dados (Excel/CSV)", type=["xlsx", "csv"], key=f"upload_{localidade_usuario}")
                if uploaded_file:
                    df_upload = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
                    st.session_state.inventarios[localidade_usuario] = df_upload
                    st.success("Base de dados carregada com sucesso!")

                st.divider()
                desc_inv = st.text_input("Descrição do Inventário Novo:", key="desc_inv_key")
                if st.button("Abrir Inventário", use_container_width=True):
                    st.session_state[f"status_inv_{localidade_usuario}"] = "Aberto"
                    st.success("Inventário Liberado para Contagem!")
                
                st.divider()
                st.caption(f"Logado como: **{nome_usuario}** ({perfil_usuario})")
                if st.button("Sair / Logoff", key="logoff_btn"):
                    st.session_state.logado = False
                    st.rerun()

            with col_central_contagem:
                st.markdown("### 🔍 Área de Bipagem")
                
                if st.session_state.get(f"status_inv_{localidade_usuario}") == "Aberto":
                    codigo_bipado = st.text_input("BIPE O CÓDIGO DA ETIQUETA:", placeholder="Aguardando bipagem...")
                    
                    if codigo_bipado:
                        st.info(f"📦 Produto Identificado (Exemplo) | Código: {codigo_bipado}")
                        st.text_input("Descrição: Rolamento Blindado 6204")
                        st.text_input("Unidade de Medida: UN")
                        st.text_input("Qtd em Sistema: 150")
                        
                        # Exemplo de Ativo obrigatório
                        st.warning("⚠️ Campo ATIVO obrigatório para este item!")
                        st.text_input("Número do Ativo:")
                        st.number_input("Quantidade Física Contada:", min_value=0)
                        st.button("Confirmar Bipagem")
                else:
                    st.info("Aguardando a abertura do inventário na barra lateral para iniciar as bipagens.")
                
                st.divider()
                st.markdown("### 📊 Progresso Real da Unidade")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total a Contar", "100 itens")
                c2.metric("Faltam", "45 itens")
                c3.metric("Acuracidade", "96.4%")

        # --- TELA: BASE DE ESTOQUE ---
        elif tela_selecionada == "Base de Estoque":
            st.header("🗄️ Base de Estoque")
            if localidade_usuario in st.session_state.inventarios:
                st.dataframe(st.session_state.inventarios[localidade_usuario], use_container_width=True)
            else:
                st.info(f"Nenhum banco de dados carregado para a unidade **{localidade_usuario}** ainda.")

        # --- TELA: HISTÓRICO DE DADOS ---
        elif tela_selecionada == "Histórico de Dados":
            st.header("📜 Histórico de Dados")
            data_filtro = st.date_input("Filtrar por Data", value=None, help="Deixe em branco para atualizações recentes")
            
            st.write("### Pastas de Inventários (Máx. 10 por página)")
            st.select_slider("Navegar Páginas", options=[1, 2, 3])
            
            if perfil_usuario in ["Supervisor", "ADM"]:
                st.button("📥 Exportar para Excel")
                st.button("🚨 Excluir Pasta")

        # --- TELA: DESEMPENHO E PRAZOS ---
        elif tela_selecionada == "Desempenho e Prazos":
            st.header("⏱️ Desempenho e Prazos")
            # Mostra apenas a localidade atual do funcionário ("cada macaco no seu galho")
            st.success(f"Status de **{localidade_usuario}**: Bom (Contado há menos de 5 dias)")

        # --- TELA: ACURACIDADE DE ESTOQUE ---
        elif tela_selecionada == "Acuracidade de Estoque":
            st.header("🎯 Acuracidade de Estoque (Auditorias)")
            st.metric("Porcentagem de Acuracidade", "98.1%")

        # --- TELA: PAINEL DO SUPERVISOR ---
        elif tela_selecionada == "Painel do Supervisor":
            st.header("⚡ Painel do Supervisor")
            st.button("Liberar tela para 2ª contagem")

        # --- TELA: AUDITORIA SUPERVISOR ---
        elif tela_selecionada == "Auditoria Supervisor":
            st.header("🕵️ Auditoria do Supervisor")
            st.button("Iniciar Auditoria de Estoque")

        # --- TELA: PAINEL ADM ---
        elif tela_selecionada == "Painel ADM":
            st.header("👑 Painel Administrativo Master")
            
            # Área de Alerta de Resets Solicitados
            if st.session_state.solicitacoes_reset:
                st.error("🚨 Solicitacões de Reset de Senha Pendentes:")
                for r in st.session_state.solicitacoes_reset:
                    st.write(f"- Usuário: **{r['usuario']}** pediu reset às {r['data']}")
                if st.button("Limpar Alertas de Reset"):
                    st.session_state.solicitacoes_reset = []
            
            st.write("### Gerenciamento de Usuários")
            st.dataframe(pd.DataFrame(st.session_state.usuarios), use_container_width=True)
