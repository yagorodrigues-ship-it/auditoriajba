import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Contagem de Estoque Físico", layout="wide")

# --- SIMULAÇÃO DE BANCO DE DADOS EM MEMÓRIA ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'inventarios' not in st.session_state:
    st.session_state.inventarios = [{"id": "#37", "nome": "teste", "data": "2026-06-12", "status": "Aberto"}]
if 'base_sistema' not in st.session_state:
    st.session_state.base_sistema = None
if 'contagens' not in st.session_state:
    st.session_state.contagens = {}

# --- TELA DE LOGIN ---
if not st.session_state.logged_in:
    st.title("🔒 Acesso ao Sistema de Estoque")
    
    with st.form("login_form"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        botao_login = st.form_submit_button("Entrar")
        
        if botao_login:
            # Login simples para teste (Usuário: admin / Senha: 123)
            if usuario == "admin" and senha == "123":
                st.session_state.logged_in = True
                st.session_state.operador = usuario
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
else:
    # --- SE USUÁRIO LOGADO, MOSTRA O SISTEMA ---
    
    # 1. BARRA LATERAL (SIDEBAR) - Igual à imagem_bcbec8.png
    with st.sidebar:
        st.header("📁 Inventário Ativo")
        
        # Opções de inventários cadastrados
        lista_inv = [f"{i['id']} – {i['nome']} ({i['data']})" for i in st.session_state.inventarios]
        inventario_selecionado = st.selectbox("Selecione o inventário", lista_inv)
        
        st.markdown("---")
        
        # Criar novo inventário
        with st.expander("➕ Novo Inventário", expanded=False):
            novo_nome = st.text_input("Nome")
            nova_desc = st.text_input("Descrição (opcional)")
            if st.button("Criar", use_container_width=True):
                if novo_nome:
                    novo_id = f"#{len(st.session_state.inventarios) + 37}"
                    hoje = datetime.date.today().strftime("%Y-%m-%d")
                    st.session_state.inventarios.append({"id": novo_id, "nome": novo_nome, "data": hoje, "status": "Aberto"})
                    st.success("Inventário criado!")
                    st.rerun()
        
        if st.button("🔒 Fechar inventário atual", use_container_width=True):
            st.warning("Inventário fechado com sucesso.")
            
        st.markdown("---")
        st.write(f"👤 **Operador:** {st.session_state.operador}")
        
        st.markdown("---")
        # Botão de Upload do Excel na barra lateral
        st.write("📂 **Carregar / Atualizar Estoque**")
        arquivo_excel = st.file_uploader("Suba o arquivo do sistema (.xlsx)", type=["xlsx"])
        if arquivo_excel is not None:
            # Lendo o Excel e salvando na memória do app
            st.session_state.base_sistema = pd.read_excel(arquivo_excel)
            st.success("Base de estoque carregada!")

    # 2. PAINEL PRINCIPAL - Igual às imagens de contagem e relatório
    st.title("📦 Contagem de Estoque Físico")
    st.caption("Tel Telecomunicações · Gestão Ativa")
    
    # Abas principais (Menus superiores)
    aba_contar, aba_relatorio = st.tabs(["🔍 Contar Item", "📊 Contagem Atual & Relatório"])
    
    # --- ABA 1: CONTAR ITEM ---
    with aba_contar:
        if st.session_state.base_sistema is None:
            st.warning("⚠️ Nenhuma base de estoque carregada. Faça o upload do seu arquivo Excel na barra lateral.")
        else:
            st.write("### Buscar Produto para Contagem")
            codigo_busca = st.text_input("Código do Produto (etiqueta ou manual)", placeholder="Ex: TEFE0016Z")
            
            if codigo_busca:
                # Procura o produto na tabela que você subiu do Excel
                df_sistema = st.session_state.base_sistema
                # Tratando para ignorar maiúsculas/minúsculas
                produto_encontrado = df_sistema[df_sistema.iloc[:, 0].astype(str).str.upper() == codigo_busca.upper()]
                
                if not produto_encontrado.empty:
                    # Se achou o produto, mostra os detalhes (Cards baseados na imagem_bcba84.png)
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.info(f"**CÓD. PRODUTO**\n### {codigo_busca.upper()}")
                    with col2:
                        # Assumindo que a coluna 1 é descrição e a coluna 4 é a quantidade do sistema no seu Excel
                        desc = produto_encontrado.iloc[0, 1] if len(produto_encontrado.columns) > 1 else "Sem Descrição"
                        st.write(f"**Descrição:** {desc}")
                        local = produto_encontrado.iloc[0, 3] if len(produto_encontrado.columns) > 3 else "Não Informado"
                        st.write(f"**Local:** {local}")
                    with col3:
                        qtd_sis = produto_encontrado.iloc[0, 4] if len(produto_encontrado.columns) > 4 else 0
                        st.metric(label="QTD SISTEMA", value=int(qtd_sis))
                    
                    st.markdown("---")
                    
                    # Campo para digitar a contagem física (imagem_bcbaa6.png)
                    qtd_fisica = st.number_input("Estoque Físico Encontrado", min_value=0, value=0, step=1)
                    
                    if st.button("💾 Salvar Contagem", type="primary"):
                        st.session_state.contagens[codigo_busca.upper()] = {
                            "quantidade_contada": qtd_fisica,
                            "quantidade_sistema": int(qtd_sis),
                            "descricao": desc
                        }
                        st.success(f"Contagem do item {codigo_busca.upper()} salva!")
                else:
                    st.error("Produto não encontrado na base de dados do sistema.")

    # --- ABA 2: RELATÓRIO DE DIVERGÊNCIAS ---
    with aba_relatorio:
        st.write("### Relatório de Divergências em Tempo Real")
        
        if not st.session_state.contagens:
            st.info("Nenhum item foi contado ainda neste inventário.")
        else:
            # Transforma as contagens feitas em uma tabela para calcular
            df_relatorio = pd.DataFrame.from_dict(st.session_state.contagens, orient='index').reset_index()
            df_relatorio.columns = ['Código', 'Físico', 'Sistema', 'Descrição']
            
            # Cálculo matemático da divergência
            df_relatorio['Divergência'] = df_relatorio['Físico'] - df_relatorio['Sistema']
            
            # Filtra onde deu diferença
            itens_com_divergencia = df_relatorio[df_relatorio['Divergência'] != 0]
            
            # Cards de resumo (Igual à imagem_bcb782.png)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📦 ITENS CONTADOS", len(df_relatorio))
            c2.metric("⚠️ COM DIVERGÊNCIA", len(itens_com_divergencia))
            c3.metric("🔢 QTD TOTAL CONTADA", int(df_relatorio['Físico'].sum()))
            c4.metric("💻 QTD TOTAL SISTEMA", int(df_relatorio['Sistema'].sum()))
            
            # Alerta visual de porcentagem de erro
            porcentagem_erro = (len(itens_com_divergencia) / len(df_relatorio)) * 100
            st.warning(f"⚠️ {len(itens_com_divergencia)} itens com divergência ({porcentagem_erro:.1f}% do total contado)")
            
            st.markdown("---")
            st.write("#### Detalhes dos Itens Digitados")
            st.dataframe(df_relatorio, use_container_width=True)
