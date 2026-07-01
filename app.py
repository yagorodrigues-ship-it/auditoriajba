import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Sistema de Inventário Inteligente JBA", layout="wide")

# -----------------------------------------------------------------------------
# PERSISTÊNCIA DE DADOS (Arquivos Locais para durar meses)
# -----------------------------------------------------------------------------
DB_INVENTARIOS = "db_inventarios.json"
DB_CONTAGENS = "db_contagens.csv"

def carregar_inventarios():
    if os.path.exists(DB_INVENTARIOS):
        with open(DB_INVENTARIOS, 'r') as f:
            return json.load(f)
    return {
        '#2 - 2194 teste (Aberto)': {
            'status': 'Aberto', 'data_fechamento': None, 'acuracidade': 0.0, 'obs': 'Teste de bipagem dinâmica'
        }
    }

def salvar_inventarios(dados):
    with open(DB_INVENTARIOS, 'w') as f:
        json.dump(dados, f, indent=4)

def carregar_contagens():
    if os.path.exists(DB_CONTAGENS):
        return pd.read_csv(DB_CONTAGENS)
    return pd.DataFrame(columns=[
        'Inventario', 'Cód. Produto', 'Desc. Produto', 'Id. Estoq. Físico', 'Desc. Estoque Físico',
        'Lote', 'Serial', 'Dt_Vencto', 'Complemento', 'Ativo', 'Quantidade_Contada', 'Saldo_Sistemico', 'Status'
    ])

def salvar_contagens(df):
    df.to_csv(DB_CONTAGENS, index=False)

# Inicializando no Session State
if 'inventarios' not in st.session_state:
    st.session_state.inventarios = carregar_inventarios()

if 'base_produtos' not in st.session_state:
    st.session_state.base_produtos = pd.DataFrame()

if 'contagens' not in st.session_state:
    st.session_state.contagens = carregar_contagens()

# Lista de estoques padrão solicitada para Frequência
if 'lista_estoques_fixos' not in st.session_state:
    st.session_state.lista_estoques_fixos = [
        {"Id. Estoq. Físico": 1077, "Desc. Estoque Físico": "JBA - CLASSE D", "Ultima_Contagem": "15/06/2026"},
        {"Id. Estoq. Físico": 1078, "Desc. Estoque Físico": "JBA - COPA E COZINHA", "Ultima_Contagem": "10/06/2026"},
        {"Id. Estoq. Físico": 1080, "Desc. Estoque Físico": "JBA - DADOS - CLIENTE", "Ultima_Contagem": "28/06/2026"},
        {"Id. Estoq. Físico": 1082, "Desc. Estoque Físico": "JBA - VIVO VITA - CLIENTE", "Ultima_Contagem": "25/05/2026"},
        {"Id. Estoq. Físico": 1084, "Desc. Estoque Físico": "JBA - EPI-EPC", "Ultima_Contagem": "12/06/2026"},
        {"Id. Estoq. Físico": 1086, "Desc. Estoque Físico": "JBA - EQUIPAMENTOS", "Ultima_Contagem": "14/06/2026"},
        {"Id. Estoq. Físico": 1088, "Desc. Estoque Físico": "JBA - FERRAMENTAL", "Ultima_Contagem": "19/06/2026"},
        {"Id. Estoq. Físico": 1089, "Desc. Estoque Físico": "JBA - KIT FERRAMENTAL CONTRATACOES", "Ultima_Contagem": "01/06/2026"},
        {"Id. Estoq. Físico": 1090, "Desc. Estoque Físico": "JBA - FERRAMENTAS DE CANTEIRO", "Ultima_Contagem": "15/05/2026"},
        {"Id. Estoq. Físico": 1102, "Desc. Estoque Físico": "1385 - LA JBA - CLIENTE", "Ultima_Contagem": "20/06/2026"},
        {"Id. Estoq. Físico": 1104, "Desc. Estoque Físico": "JBA - MATERIAL DE ESCRITORIO - SUPRIMENTOS DE INFORMATICA", "Ultima_Contagem": "18/06/2026"},
        {"Id. Estoq. Físico": 1106, "Desc. Estoque Físico": "JBA - MOBILIARIO", "Ultima_Contagem": "10/04/2026"},
        {"Id. Estoq. Físico": 1108, "Desc. Estoque Físico": "1071 - EXEC SEGREGADO IMPLANTACAO JBA - CLIENTE", "Ultima_Contagem": "29/06/2026"},
        {"Id. Estoq. Físico": 1113, "Desc. Estoque Físico": "1385 - MANUTENCAO JBA - CLIENTE", "Ultima_Contagem": "22/06/2026"},
        {"Id. Estoq. Físico": 1118, "Desc. Estoque Físico": "JBA - PROPRIO GERAL", "Ultima_Contagem": "20/06/2026"},
        {"Id. Estoq. Físico": 1122, "Desc. Estoque Físico": "JBA - GRANDES OBRAS IMPLANTACAO", "Ultima_Contagem": "11/06/2026"},
        {"Id. Estoq. Físico": 1124, "Desc. Estoque Físico": "JBA - PROPRIO TIM", "Ultima_Contagem": "12/06/2026"},
        {"Id. Estoq. Físico": 1140, "Desc. Estoque Físico": "JBA - SPEEDY/FTTX - CLIENTE", "Ultima_Contagem": "26/06/2026"},
        {"Id. Estoq. Físico": 1144, "Desc. Estoque Físico": "1385 - MANUTENCAO JBA CLIENTE RESERVADO", "Ultima_Contagem": "20/06/2026"},
        {"Id. Estoq. Físico": 1149, "Desc. Estoque Físico": "JBA - UNIFORME", "Ultima_Contagem": "17/06/2026"},
        {"Id. Estoq. Físico": 2149, "Desc. Estoque Físico": "JBA - SPEEDY/FTTX DEVOLUCAO NOVO COM DEFEITO - CLIENTE", "Ultima_Contagem": "10/06/2026"},
        {"Id. Estoq. Físico": 2183, "Desc. Estoque Físico": "1071 - BOL IMPLANTANCAO JBA - CLIENTE", "Ultima_Contagem": "15/06/2026"},
        {"Id. Estoq. Físico": 2185, "Desc. Estoque Físico": "JBA - PROPRIO FATURA B PLANTA EXTERNA - BDI", "Ultima_Contagem": "05/06/2026"},
        {"Id. Estoq. Físico": 2188, "Desc. Estoque Físico": "1071 - IMPLANTACAO JBA CLIENTE RESERVADO", "Ultima_Contagem": "21/06/2026"},
        {"Id. Estoq. Físico": 2189, "Desc. Estoque Físico": "JBA - DEFEITO", "Ultima_Contagem": "20/06/2026"},
        {"Id. Estoq. Físico": 2190, "Desc. Estoque Físico": "JBA - DEPARTAMENTO T.I", "Ultima_Contagem": "19/06/2026"},
        {"Id. Estoq. Físico": 2194, "Desc. Estoque Físico": "JBA - KITS FERRAMENTAL - DEVOLUCAO", "Ultima_Contagem": "30/06/2026"},
        {"Id. Estoq. Físico": 2197, "Desc. Estoque Físico": "JBA - EQUIPAMENTOS TI", "Ultima_Contagem": "29/06/2026"},
        {"Id. Estoq. Físico": 2641, "Desc. Estoque Físico": "1259 - IMPLANTACAO JBA - MATERIAL REUTILIZACAO", "Ultima_Contagem": "02/06/2026"},
        {"Id. Estoq. Físico": 2643, "Desc. Estoque Físico": "1724 - MANUTENCAO JBA - MATERIAL REUTILIZACAO", "Ultima_Contagem": "04/06/2026"},
        {"Id. Estoq. Físico": 2725, "Desc. Estoque Físico": "JBA - RESERVA TIM", "Ultima_Contagem": "20/05/2026"},
        {"Id. Estoq. Físico": 2983, "Desc. Estoque Físico": "JBA - FORNECEDORES P/ MANUTENCAO - RECARGA", "Ultima_Contagem": "14/06/2026"},
        {"Id. Estoq. Físico": 3193, "Desc. Estoque Físico": "JBA - PROPRIO MATERIAL REAPROVEITAVEL", "Ultima_Contagem": "15/06/2026"},
        {"Id. Estoq. Físico": 3395, "Desc. Estoque Físico": "LPA - FTTX - CLIENTE", "Ultima_Contagem": "18/06/2026"},
        {"Id. Estoq. Físico": 3484, "Desc. Estoque Físico": "JBA - CELULARES DEFEITO", "Ultima_Contagem": "01/05/2026"},
        {"Id. Estoq. Físico": 3546, "Desc. Estoque Físico": "JBA - CELULARES", "Ultima_Contagem": "12/06/2026"}
    ]

if 'limpar_bipe' not in st.session_state: st.session_state.limpar_bipe = False

# -----------------------------------------------------------------------------
# ESTILOS E COMPONENTES VISUAIS CUSTOMIZADOS
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    .metric-card { background-color: #1a2436; padding: 20px; border-radius: 10px; color: white; margin-bottom: 15px; border-left: 5px solid #2e66ff; }
    .metric-title { font-size: 12px; font-weight: bold; text-transform: uppercase; opacity: 0.8; }
    .metric-value { font-size: 32px; font-weight: bold; margin-top: 5px; }
    .alerta-obrigatorio { background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; border-left: 5px solid #ffc107; margin-bottom: 15px; font-weight: bold; }
    .info-estoque { background-color: #f0f2f6; padding: 12px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid #1c83e1; }
    
    /* Círculo de Acuracidade Estilizado */
    .kpi-container { display: flex; align-items: center; background-color: #f8f9fa; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef; margin-bottom: 20px; }
    .circle-green { width: 90px; height: 90px; background-color: #2ed573; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; font-weight: bold; box-shadow: 0 4px 10px rgba(46,213,115,0.3); }
    .circle-yellow { width: 90px; height: 90px; background-color: #ffa502; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; font-weight: bold; box-shadow: 0 4px 10px rgba(255,165,2,0.3); }
    .circle-red { width: 90px; height: 90px; background-color: #ff4757; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; font-weight: bold; box-shadow: 0 4px 10px rgba(255,71,87,0.3); }
    .kpi-text-box { margin-left: 20px; }
    .kpi-label { font-size: 14px; color: #747d8c; font-weight: 600; text-transform: uppercase; }
    .kpi-value-text { font-size: 28px; color: #2f3542; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

def normalizar_valor(val):
    if pd.isna(val) or str(val).strip().lower() == 'nan' or str(val).strip() == '': return ""
    v_str = str(val).strip()
    if v_str.endswith('.0'): return v_str[:-2]
    return v_str

# -----------------------------------------------------------------------------
# 2. BARRA LATERAL (Sidebar)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.subheader("👤 Operador Ativo")
    st.caption("Administrador Tel")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1: st.button("🔄 Atualizar", use_container_width=True)
    with col_btn2: st.button("🚪 Sair", use_container_width=True)
    
    st.write("---")
    
    # 1. Opção que abre o inventário (Criar)
    with st.expander("➕ Criar Novo Inventário", expanded=False):
        novo_id = st.text_input("ID / Nome do Inventário", placeholder="Ex: #3 - Almoxarifado")
        nova_obs = st.text_area("Observações Iniciais")
        if st.button("Salvar Novo Inventário"):
            if novo_id:
                st.session_state.inventarios[f"{novo_id} (Aberto)"] = {
                    'status': 'Aberto', 'data_fechamento': None, 'acuracidade': 0.0, 'obs': nova_obs
                }
                salvar_inventarios(st.session_state.inventarios)
                st.success("Inventário criado!")
                st.rerun()

    st.subheader("📂 Selecione o Inventário Ativo")
    lista_invs = list(st.session_state.inventarios.keys())
    inv_ativo = st.selectbox("Inventário em andamento:", lista_invs, index=0)
    
    # -----------------------------------------------------------------------------
    # MOVEU PARA CÁ: FECHAMENTO CORPORATIVO DO INVENTÁRIO (Embaixo da seleção)
    # -----------------------------------------------------------------------------
    st.write("---")
    st.caption("🔒 Fechamento Corporativo do Inventário")
    
    # Pré-carregar dados para calcular pendências reais na barra lateral
    contagens_atuais = st.session_state.contagens[st.session_state.contagens['Inventario'] == inv_ativo]
    linhas_contadas_set = set()
    if not contagens_atuais.empty:
        for idx, r in contagens_atuais.iterrows():
            linhas_contadas_set.add((normalizar_valor(r['Cód. Produto']), normalizar_valor(r['Lote']), normalizar_valor(r['Ativo'])))
            
    total_linhas_base = len(st.session_state.base_produtos)
    it_contados = 0
    if total_linhas_base > 0:
        for idx, row in st.session_state.base_produtos.iterrows():
            chave_row = (normalizar_valor(row['Cód. Produto']), normalizar_valor(row['Lote']), normalizar_valor(row['Ativo']))
            if chave_row in linhas_contadas_set: it_contados += 1
                
    pendencias_reais = max(0, total_linhas_base - it_contados)
    
    if st.session_state.inventarios[inv_ativo]['status'] == 'Fechado':
        st.error("🔒 Este inventário já está FECHADO.")
    else:
        if pendencias_reais > 0:
            st.warning(f"Existem ainda {pendencias_reais} pendências.")
            senha_supervisor = st.text_input("Senha do Supervisor para forçar fechar:", type="password", key="senha_lateral")
            if st.button("Forçar Fechamento", use_container_width=True):
                if senha_supervisor == "admin123":
                    st.session_state.inventarios[inv_ativo]['status'] = 'Fechado'
                    st.session_state.inventarios[inv_ativo]['data_fechamento'] = datetime.now().strftime('%d/%m/%Y %H:%M')
                    salvar_inventarios(st.session_state.inventarios)
                    st.success("Fechado pelo Supervisor!")
                    st.rerun()
                else:
                    st.error("Senha inválida!")
        else:
            if st.button("Finalizar Inventário (100% Concluído)", type="primary", use_container_width=True):
                st.session_state.inventarios[inv_ativo]['status'] = 'Fechado'
                st.session_state.inventarios[inv_ativo]['data_fechamento'] = datetime.now().strftime('%d/%m/%Y %H:%M')
                salvar_inventarios(st.session_state.inventarios)
                st.success("Fechado com sucesso!")
                st.rerun()
                
    st.write("---")
    st.subheader("📁 Carregar Planilha Base")
    uploaded_file = st.file_uploader("Arraste ou selecione o arquivo (.xlsx, .csv)", type=["xlsx", "csv"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'): df_upload = pd.read_csv(uploaded_file)
            else: df_upload = pd.read_excel(uploaded_file)
            
            df_upload.columns = [str(c).strip() for c in df_upload.columns]
            mapeamento_nomes = {
                'Codigo': 'Cód. Produto', 'Descricao': 'Desc. Produto',
                'Id. Estoque Fisico': 'Id. Estoq. Físico', 'Id. Estoque Físico': 'Id. Estoq. Físico',
                'Desc. Estoque Fisico': 'Desc. Estoque Físico'
            }
            df_upload.rename(columns=mapeamento_nomes, inplace=True)
            colunas_obrigatorias = ['Lote', 'Ativo', 'Qtd Estoque', 'Cód. Produto', 'Desc. Produto', 'Id. Estoq. Físico', 'Desc. Estoque Físico']
            for col in colunas_obrigatorias:
                if col not in df_upload.columns: df_upload[col] = None
            
            st.session_state.base_produtos = df_upload
            st.toast("Planilha carregada com sucesso!", icon="✅")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    st.write("---")
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">📋 Linhas Totais na Base</div>
        <div class="metric-value">{total_linhas_base}</div>
    </div>
    <div class="metric-card" style="border-left-color: #2ed573;">
        <div class="metric-title">✅ Itens Já Contados</div>
        <div class="metric-value">{it_contados}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"**PENDÊNCIAS RESTANTES:** `{pendencias_reais}`")

# -----------------------------------------------------------------------------
# 3. PAINEL PRINCIPAL (Abas de Navegação)
# -----------------------------------------------------------------------------
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "🔍 Contar Item", "📄 Base de Estoque (Tempo Real)", "📊 Painel Supervisor", "📈 Acuracidade", "🕒 Frequência", "🗄️ Histórico"
])

# -----------------------------------------------------------------------------
# ABA 1: TELA DE BIPAGEM DINÂMICA
# -----------------------------------------------------------------------------
with aba1:
    if st.session_state.base_produtos.empty:
        st.warning("⚠️ Mapeie o inventário e faça o upload da base na barra lateral para liberar a digitação.")
    else:
        st.header(f"🎥 Tela de Bipagem Dinâmica")
        if st.session_state.limpar_bipe:
            st.session_state.limpar_bipe = False
            st.rerun()
            
        texto_bipado_bruto = st.text_input("👉 BIPAR CÓDIGO DO MATERIAL:", value="", key="bipador_input")
        
        if texto_bipado_bruto:
            bip_limpo = str(texto_bipado_bruto).strip()
            linhas_produto = pd.DataFrame()
            codigo_verdadeiro_encontrado = None
            
            for cod_base in st.session_state.base_produtos['Cód. Produto'].dropna().unique():
                cod_base_str = str(cod_base).strip()
                if cod_base_str in bip_limpo:
                    linhas_produto = st.session_state.base_produtos[st.session_state.base_produtos['Cód. Produto'].astype(str).str.strip() == cod_base_str]
                    codigo_verdadeiro_encontrado = cod_base_str
                    break
            
            if linhas_produto.empty:
                linhas_produto = st.session_state.base_produtos[st.session_state.base_produtos['Cód. Produto'].astype(str) == bip_limpo]
                if not lines_produto.empty: codigo_verdadeiro_encontrado = bip_limpo

            if not linhas_produto.empty:
                desc_produto = linhas_produto.iloc[0]['Desc. Produto']
                id_estoque_fisico = linhas_produto.iloc[0]['Id. Estoq. Físico']
                desc_estoque_fisico = linhas_produto.iloc[0]['Desc. Estoque Físico']
                
                linhas_pendentes = []
                for idx, row in linhas_produto.iterrows():
                    foi_contado = False
                    if not contagens_atuais.empty:
                        match = contagens_atuais[
                            (contagens_atuais['Cód. Produto'].astype(str).apply(normalizar_valor) == normalizar_valor(codigo_verdadeiro_encontrado)) & 
                            (contagens_atuais['Lote'].astype(str).apply(normalizar_valor) == normalizar_valor(row['Lote'])) & 
                            (contagens_atuais['Ativo'].astype(str).apply(normalizar_valor) == normalizar_valor(row['Ativo']))
                        ]
                        if not match.empty: foi_contado = True
                    if not foi_contado: linhas_pendentes.append(row)
                
                if len(linhas_pendentes) == 0:
                    st.success("🎉 Todas as variações de Lote/Ativo deste produto já foram contabilizadas!")
                else:
                    st.markdown(f"""
                    <div class="info-estoque">
                        📦 <b>Item Identificado:</b> {desc_produto} (Código: <code>{codigo_verdadeiro_encontrado}</code>)<br>
                        📍 <b>ID Estoque Físico:</b> {id_estoque_fisico if id_estoque_fisico else 'Não informado'}<br>
                        🏢 <b>Descrição do Estoque:</b> {desc_estoque_fisico if desc_estoque_fisico else 'Não informado'}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    df_pendentes = pd.DataFrame(linhas_pendentes)
                    tem_ativo_valores = df_pendentes['Ativo'].apply(normalizar_valor).str.strip().any()
                    tem_lote_valores = df_pendentes['Lote'].apply(normalizar_valor).str.strip().any()
                    
                    with st.form("validacao_contagem", clear_on_submit=True):
                        if tem_ativo_valores:
                            st.markdown('<div class="alerta-obrigatorio">⚠️ ATENÇÃO: Este item possui controle por ATIVO. Selecione qual ativo está conferindo:</div>', unsafe_allow_html=True)
                            lista_ativos_limpos = df_pendentes['Ativo'].dropna().apply(normalizar_valor).unique()
                            ativo_selecionado_str = st.selectbox("Selecione o número do ATIVO obrigatório (Apenas Pendentes):", lista_ativos_limpos)
                            lote_selecionado = None
                            linha_selecionada = next(row for idx, row in df_pendentes.iterrows() if normalizar_valor(row['Ativo']) == ativo_selecionado_str)
                            ativo_selecionado = linha_selecionada['Ativo']
                        elif tem_lote_valores:
                            st.markdown('<div class="alerta-obrigatorio">⚠️ ATENÇÃO: Este item possui controle por LOTE. Selecione o lote correspondente:</div>', unsafe_allow_html=True)
                            lista_lotes_limpos = df_pendentes['Lote'].dropna().apply(normalizar_valor).unique()
                            lote_selecionado_str = st.selectbox("Selecione o LOTE correspondente (Apenas Pendentes):", lista_lotes_limpos)
                            ativo_selecionado = None
                            linha_selecionada = next(row for idx, row in df_pendentes.iterrows() if normalizar_valor(row['Lote']) == lote_selecionado_str)
                            lote_selecionado = linha_selecionada['Lote']
                        else:
                            st.write("📝 **Item Comum** (Sem variação de Lote ou Ativo pendente).")
                            ativo_selecionado = None; lote_selecionado = None
                            linha_selecionada = df_pendentes.iloc[0]
                        
                        col_c1, col_c2 = st.columns(2)
                        with col_c1: qtd_contada = st.number_input("Digite a quantidade física contada:", min_value=0, step=1, value=1)
                        with col_c2: obs_registro = st.text_input("Observações do lançamento:")
                            
                        submeter_registro = st.form_submit_button("💾 Salvar e Validar Contagem")
                        
                        if submeter_registro:
                            nova_contagem = {
                                'Inventario': inv_ativo, 'Cód. Produto': codigo_verdadeiro_encontrado, 'Desc. Produto': desc_produto,
                                'Id. Estoq. Físico': id_estoque_fisico, 'Desc. Estoque Físico': desc_estoque_fisico,
                                'Lote': lote_selecionado if lote_selecionado else linha_selecionada.get('Lote', None),
                                'Serial': linha_selecionada.get('Serial', None), 'Dt_Vencto': linha_selecionada.get('Dt. Vencto', None),
                                'Complemento': linha_selecionada.get('Complemento', None), 'Ativo': ativo_selecionado if ativo_selecionado else linha_selecionada.get('Ativo', None),
                                'Quantidade_Contada': qtd_contada, 'Saldo_Sistemico': linha_selecionada.get('Qtd Estoque', 0), 'Status': 'Contado'
                            }
                            st.session_state.contagens = pd.concat([st.session_state.contagens, pd.DataFrame([nova_contagem])], ignore_index=True)
                            salvar_contagens(st.session_state.contagens)
                            st.session_state.limpar_bipe = True
                            st.toast(f"Sucesso! Item adicionado.", icon="🚀")
                            st.rerun()
            else:
                st.error(f"❌ Código de barras `{bip_limpo}` não localizado.")

        st.write("---")
        st.write("### 📜 Seus Lançamentos Concluídos")
        if not contagens_atuais.empty:
            st.dataframe(contagens_atuais[['Cód. Produto', 'Desc. Produto', 'Id. Estoq. Físico', 'Lote', 'Ativo', 'Quantidade_Contada', 'Saldo_Sistemico', 'Status']], use_container_width=True)

# -----------------------------------------------------------------------------
# ABA 2: BASE DE ESTOQUE COMPLETA EM TEMPO REAL
# -----------------------------------------------------------------------------
with aba2:
    st.header("📄 Base de Estoque Carregada")
    if st.session_state.base_produtos.empty: st.info("Aguardando arquivo base.")
    else:
        df_visualizacao = st.session_state.base_produtos.copy()
        status_l, qtd_l = [], []
        for idx, row in df_visualizacao.iterrows():
            c, l, a = normalizar_valor(row['Cód. Produto']), normalizar_valor(row['Lote']), normalizar_valor(row['Ativo'])
            match = pd.DataFrame()
            if not contagens_atuais.empty:
                match = contagens_atuais[
                    (contagens_atuais['Cód. Produto'].astype(str).apply(normalizar_valor) == c) & 
                    (contagens_atuais['Lote'].astype(str).apply(normalizar_valor) == l) & 
                    (contagens_atuais['Ativo'].astype(str).apply(normalizar_valor) == a)
                ]
            if not match.empty:
                status_l.append("🟢 Contado"); qtd_l.append(int(match['Quantidade_Contada'].sum()))
            else:
                status_l.append("🔴 Pendente"); qtd_l.append(0)
        df_visualizacao.insert(0, "Status Contagem", status_l)
        df_visualizacao.insert(1, "Qtd Física Contada", qtd_l)
        st.dataframe(df_visualizacao, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# ABA 3: PAINEL DO SUPERVISOR (2ª CONTAGEM LIBERADA)
# -----------------------------------------------------------------------------
with aba3:
    st.header("🕵️‍♂️ Painel de Auditoria do Supervisor")
    df_divergentes = contagens_atuais[contagens_atuais['Quantidade_Contada'] != contagens_atuais['Saldo_Sistemico']]
    
    if df_divergentes.empty:
        st.success("🎉 Nenhuma divergência encontrada!")
    else:
        st.warning(f"Atenção: {len(df_divergentes)} linhas apresentam divergência de saldo.")
        st.dataframe(df_divergentes, use_container_width=True)
        
        st.write("---")
        st.subheader("🔄 Comando de Recalcular: Acionar Segunda Contagem")
        item_recontar = st.selectbox("Selecione o produto divergente para auditoria física:", df_divergentes['Desc. Produto'].unique())
        
        col_sup1, col_sup2 = st.columns(2)
        with col_sup1: nova_qtd_supervisor = st.number_input("Quantidade Apurada na 2ª Contagem pelo Supervisor:", min_value=0, step=1)
        with col_sup2:
            st.write("</br>", unsafe_allow_html=True)
            if st.button("Gravar 2ª Contagem e Atualizar Saldo", use_container_width=True):
                idx = st.session_state.contagens[
                    (st.session_state.contagens['Inventario'] == inv_ativo) & 
                    (st.session_state.contagens['Desc. Produto'] == item_recontar)
                ].index
                st.session_state.contagens.loc[idx, 'Quantidade_Contada'] = nova_qtd_supervisor
                st.session_state.contagens.loc[idx, 'Status'] = 'Ajustado em 2ª Contagem'
                salvar_contagens(st.session_state.contagens)
                st.success("Segunda contagem computada com sucesso!")
                st.rerun()

# -----------------------------------------------------------------------------
# ABA 4: ACURACIDADE COM ANEL/CÍRCULO FORMATADO
# -----------------------------------------------------------------------------
with aba4:
    st.header("📈 Relatório de Acuracidade Geral")
    if not contagens_atuais.empty:
        corretos = (contagens_atuais['Quantidade_Contada'] == contagens_atuais['Saldo_Sistemico']).sum()
        total_linhas_contadas = len(contagens_atuais)
        taxa = (corretos / total_linhas_contadas) * 100
        
        if taxa >= 95.0: classe_circulo = "circle-green"
        elif taxa >= 85.0: classe_circulo = "circle-yellow"
        else: classe_circulo = "circle-red"
        
        st.markdown(f"""
        <div class="kpi-container">
            <div class="{classe_circulo}">{taxa:.1f}%</div>
            <div class="kpi-text-box">
                <div class="kpi-label">Acuracidade Atual do Estoque</div>
                <div class="kpi-value-text">{corretos} corretos de {total_linhas_contadas} conferidos</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        id_est_visualizar = contagens_atuais.iloc[0]['Id. Estoq. Físico']
        desc_est_visualizar = contagens_atuais.iloc[0]['Desc. Estoque Físico']
        st.info(f"📍 **Estoque em Análise:** {id_est_visualizar} - {desc_est_visualizar}")
    else:
        st.info("Nenhum item lançado neste inventário para processamento de acuracidade.")

# -----------------------------------------------------------------------------
# ABA 5: FREQUÊNCIA DE ESTOQUES JBA (RESOLVIDO ERRO MAP/APPLYMAP)
# -----------------------------------------------------------------------------
with aba5:
    st.header("🕒 Frequência e Janela Crítica de Contagem")
    st.write("Critério: Status **CRÍTICO** se o setor estiver há mais de 2 semanas (14 dias) sem contagem registrada.")
    
    dados_tabela_frequencia = []
    data_limite = datetime.now() - timedelta(days=14)
    
    for est in st.session_state.lista_estoques_fixos:
        dt_contagem = datetime.strptime(est['Ultima_Contagem'], '%d/%m/%Y')
        dias_atraso = (datetime.now() - dt_contagem).days
        status_critico = "⚠️ CRÍTICO" if dt_contagem < data_limite else "🟢 Bom"
        
        dados_tabela_frequencia.append({
            "Id. Estoq. Físico": est['Id. Estoq. Físico'],
            "Desc. Estoque Físico": est['Desc. Estoque Físico'],
            "Última Contagem": est['Ultima_Contagem'],
            "Dias Sem Contar": dias_atraso,
            "Status de Criticidade": status_critico
        })
        
    df_freq_final = pd.DataFrame(dados_tabela_frequencia)
    
    def destacar_critico(val):
        color = 'red' if '⚠️' in str(val) else 'green'
        return f'color: {color}; font-weight: bold;'
        
    # 🔥 SOLUÇÃO: Mudança de .applymap para .map para compatibilidade com versões novas do Pandas
    st.dataframe(df_freq_final.style.map(destacar_critico, subset=['Status de Criticidade']), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# ABA 6: HISTÓRICO DE ARQUIVO (Eterno e Exportável)
# -----------------------------------------------------------------------------
with aba6:
    st.header("🗄️ Histórico Permanente de Inventários")
    st.write("Dados armazenados localmente e disponíveis para auditorias futuras.")
    
    for inv, info in list(st.session_state.inventarios.items()):
        status_cor = "🟢" if info['status'] == "Aberto" else "🔴"
        with st.expander(f"{status_cor} {inv} | Status: {info['status']}"):
            st.write(f"**Notas:** {info['obs']}")
            if info['data_fechamento']: st.write(f"**Fechado em:** {info['data_fechamento']}")
            
            dados_historicos_inv = st.session_state.contagens[st.session_state.contagens['Inventario'] == inv]
            if not dados_historicos_inv.empty:
                st.dataframe(dados_historicos_inv, use_container_width=True)
                csv_dados = dados_historicos_inv.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Baixar Arquivo Consolidado (CSV)", data=csv_dados, file_name=f"Historico_{inv.replace(' ', '_')}.csv", mime="text/csv", key=f"btn_{inv}")
            else:
                st.caption("Nenhum lançamento registrado neste inventário.")
