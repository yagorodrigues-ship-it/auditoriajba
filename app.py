import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import math

# Configuração da página e identidade visual do app
st.set_page_config(page_title="Sistema de Inventário Inteligente JBA", layout="wide")

# -----------------------------------------------------------------------------
# PERSISTÊNCIA DE DADOS (Arquivos Locais estáveis)
# -----------------------------------------------------------------------------
DB_INVENTARIOS = "db_inventarios.json"
DB_CONTAGENS = "db_contagens.csv"
DB_ESTOQUES_MASTER = "db_estoques_master.json"

def carregar_inventarios():
    if os.path.exists(DB_INVENTARIOS):
        with open(DB_INVENTARIOS, 'r') as f: return json.load(f)
    return {
        '#2 - 2194 teste (Aberto)': {
            'status': 'Aberto', 'data_fechamento': None, 'acuracidade': 0.0, 'obs': 'Teste de bipagem dinâmica',
            'timestamp_criacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }

def salvar_inventarios(dados):
    with open(DB_INVENTARIOS, 'w') as f: json.dump(dados, f, indent=4)

def carregar_contagens():
    if os.path.exists(DB_CONTAGENS): 
        df = pd.read_csv(DB_CONTAGENS)
        # Forçar criação das colunas novas caso o arquivo CSV seja antigo
        for col in ['Supervisor_Qtd', 'Supervisor_Etiqueta', 'Supervisor_Endereco']:
            if col not in df.columns:
                df[col] = None
        return df
    return pd.DataFrame(columns=[
        'Inventario', 'Cód. Produto', 'Desc. Produto', 'Id. Estoq. Físico', 'Desc. Estoque Físico',
        'Lote', 'Serial', 'Dt_Vencto', 'Complemento', 'Ativo', 'Quantidade_Contada', 'Saldo_Sistemico', 'Status',
        'Supervisor_Qtd', 'Supervisor_Etiqueta', 'Supervisor_Endereco'
    ])

def salvar_contagens(df): df.to_csv(DB_CONTAGENS, index=False)

def carregar_estoques_master():
    if os.path.exists(DB_ESTOQUES_MASTER):
        with open(DB_ESTOQUES_MASTER, 'r') as f: return json.load(f)
    return [
        {"Id. Estoq. Físico": 1077, "Desc. Estoque Físico": "JBA - CLASSE D", "Ultima_Contagem": "15/06/2026", "Acuracidade_Previa": 98.2},
        {"Id. Estoq. Físico": 1078, "Desc. Estoque Físico": "JBA - COPA E COZINHA", "Ultima_Contagem": "10/06/2026", "Acuracidade_Previa": 100.0},
        {"Id. Estoq. Físico": 1080, "Desc. Estoque Físico": "JBA - DADOS - CLIENTE", "Ultima_Contagem": "28/06/2026", "Acuracidade_Previa": 92.4},
        {"Id. Estoq. Físico": 1082, "Desc. Estoque Físico": "JBA - VIVO VITA - CLIENTE", "Ultima_Contagem": "25/05/2026", "Acuracidade_Previa": 84.1},
        {"Id. Estoq. Físico": 1084, "Desc. Estoque Físico": "JBA - EPI-EPC", "Ultima_Contagem": "12/06/2026", "Acuracidade_Previa": 99.0},
        {"Id. Estoq. Físico": 1086, "Desc. Estoque Físico": "JBA - EQUIPAMENTOS", "Ultima_Contagem": "14/06/2026", "Acuracidade_Previa": 95.5},
        {"Id. Estoq. Físico": 1088, "Desc. Estoque Físico": "JBA - FERRAMENTAL", "Ultima_Contagem": "19/06/2026", "Acuracidade_Previa": 91.0},
        {"Id. Estoq. Físico": 1089, "Desc. Estoque Físico": "JBA - KIT FERRAMENTAL CONTRATACOES", "Ultima_Contagem": "01/06/2026", "Acuracidade_Previa": 100.0},
        {"Id. Estoq. Físico": 1090, "Desc. Estoque Físico": "JBA - FERRAMENTAS DE CANTEIRO", "Ultima_Contagem": "15/05/2026", "Acuracidade_Previa": 76.5},
        {"Id. Estoq. Físico": 1102, "Desc. Estoque Físico": "1385 - LA JBA - CLIENTE", "Ultima_Contagem": "20/06/2026", "Acuracidade_Previa": 94.0},
        {"Id. Estoq. Físico": 2194, "Desc. Estoque Físico": "JBA - KITS FERRAMENTAL - DEVOLUCAO", "Ultima_Contagem": "10/06/2026", "Acuracidade_Previa": 85.7}
    ]

def salvar_estoques_master(dados):
    with open(DB_ESTOQUES_MASTER, 'w') as f: json.dump(dados, f, indent=4)

# Inicializações de controle
if 'inventarios' not in st.session_state: st.session_state.inventarios = carregar_inventarios()
if 'base_produtos' not in st.session_state: st.session_state.base_produtos = pd.DataFrame()
if 'contagens' not in st.session_state: st.session_state.contagens = carregar_contagens()
if 'lista_estoques_fixos' not in st.session_state: st.session_state.lista_estoques_fixos = carregar_estoques_master()
if 'pagina_atual_hist' not in st.session_state: st.session_state.pagina_atual_hist = 1
if 'limpar_bipe' not in st.session_state: st.session_state.limpar_bipe = False
if 'modo_auditoria_ativo' not in st.session_state: st.session_state.modo_auditoria_ativo = False

# Estilos CSS Customizados
st.markdown("""
    <style>
    .metric-card { background-color: #1a2436; padding: 20px; border-radius: 10px; color: white; margin-bottom: 15px; border-left: 5px solid #2e66ff; }
    .metric-title { font-size: 12px; font-weight: bold; text-transform: uppercase; opacity: 0.8; }
    .metric-value { font-size: 32px; font-weight: bold; margin-top: 5px; }
    .alerta-obrigatorio { background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; border-left: 5px solid #ffc107; margin-bottom: 15px; font-weight: bold; }
    .info-estoque { background-color: #f0f2f6; padding: 12px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid #1c83e1; }
    
    .acuracidade-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 15px; margin-top: 15px; }
    .acuracidade-card { background-color: #ffffff; border-radius: 8px; border: 1px solid #e9ecef; padding: 15px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .acuracidade-info { display: flex; flex-direction: column; }
    .acuracidade-nome { font-weight: bold; color: #2f3542; font-size: 14px; margin-bottom: 4px; }
    .acuracidade-id { font-size: 12px; color: #747d8c; font-weight: 600; }
    .acuracidade-tag-green { background-color: #2ed573; color: white; padding: 8px 12px; border-radius: 20px; font-weight: bold; font-size: 16px; min-width: 75px; text-align: center; }
    .acuracidade-tag-yellow { background-color: #ffa502; color: white; padding: 8px 12px; border-radius: 20px; font-weight: bold; font-size: 16px; min-width: 75px; text-align: center; }
    .acuracidade-tag-red { background-color: #ff4757; color: white; padding: 8px 12px; border-radius: 20px; font-weight: bold; font-size: 16px; min-width: 75px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

def normalizar_valor(val):
    if pd.isna(val) or str(val).strip().lower() == 'nan' or str(val).strip() == '': return ""
    v_str = str(val).strip()
    if v_str.endswith('.0'): return v_str[:-2]
    return v_str

# -----------------------------------------------------------------------------
# BARRA LATERAL (Sidebar)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.subheader("👤 Operador Ativo")
    operador_atual = "Administrador Tel"
    st.markdown(f"**{operador_atual}**")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1: st.button("🔄 Atualizar", use_container_width=True)
    with col_btn2: st.button("🚪 Sair", use_container_width=True)
    
    st.write("---")
    
    with st.expander("➕ Criar Novo Inventário", expanded=False):
        novo_id = st.text_input("ID / Nome do Inventário", placeholder="Ex: #3 - Almoxarifado Central")
        nova_obs = st.text_area("Observações Iniciais")
        if st.button("Salvar Novo Inventário", use_container_width=True):
            if novo_id:
                chave_nova = f"{novo_id} (Aberto)"
                st.session_state.inventarios[chave_nova] = {
                    'status': 'Aberto', 'data_fechamento': None, 'acuracidade': 100.0, 'obs': nova_obs,
                    'timestamp_criacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                salvar_inventarios(st.session_state.inventarios)
                st.success("Inventário inicializado!")
                st.rerun()

    st.subheader("📂 Selecione o Inventário Ativo")
    inventarios_ordenados = sorted(st.session_state.inventarios.items(), key=lambda item: item[1].get('timestamp_criacao', ''), reverse=True)
    lista_invs_nomes = [item[0] for item in inventarios_ordenados]
    inv_ativo = st.selectbox("Inventário em andamento:", lista_invs_nomes, index=0) if lista_invs_nomes else None

    contagens_atuais = st.session_state.contagens[st.session_state.contagens['Inventario'] == inv_ativo] if inv_ativo else pd.DataFrame()
    linhas_contadas_set = set()
    if not contagens_atuais.empty:
        for idx, r in contagens_atuais.iterrows():
            linhas_contadas_set.add((normalizar_valor(r['Cód. Produto']), normalizar_valor(r['Lote']), normalizar_valor(r['Ativo'])))
            
    total_linhas_base = len(st.session_state.base_produtos)
    it_contados = sum(1 for _, row in st.session_state.base_produtos.iterrows() if (normalizar_valor(row['Cód. Produto']), normalizar_valor(row['Lote']), normalizar_valor(row['Ativo'])) in linhas_contadas_set)
    pendencias_reais = max(0, total_linhas_base - it_contados)
    
    st.write("---")
    uploaded_file = st.file_uploader("📁 Carregar Planilha Base", type=["xlsx", "csv"])
    if uploaded_file:
        try:
            df_upload = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df_upload.columns = [str(c).strip() for c in df_upload.columns]
            mapeamento_nomes = {'Codigo': 'Cód. Produto', 'Descricao': 'Desc. Produto', 'Id. Estoque Físico': 'Id. Estoq. Físico', 'Desc. Estoque Fisico': 'Desc. Estoque Físico'}
            df_upload.rename(columns=mapeamento_nomes, inplace=True)
            for col in ['Lote', 'Ativo', 'Qtd Estoque', 'Cód. Produto', 'Desc. Produto', 'Id. Estoq. Físico', 'Desc. Estoque Físico']:
                if col not in df_upload.columns: df_upload[col] = None
            st.session_state.base_produtos = df_upload
            st.toast("Planilha carregada!", icon="✅")
        except Exception as e: st.error(f"Erro: {e}")

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

# -----------------------------------------------------------------------------
# 3. PAINEL PRINCIPAL
# -----------------------------------------------------------------------------
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "🔍 Contar Item", "📄 Base de Estoque", "📊 Painel Supervisor", "📈 Acuracidade", "🕒 Frequência", "🗄️ Histórico Geral"
])

# -----------------------------------------------------------------------------
# ABA 1: TELA DE BIPAGEM DO ALMOXARIFE
# -----------------------------------------------------------------------------
with aba1:
    if st.session_state.base_produtos.empty:
        st.warning("⚠️ Mapeie o inventário e faça o upload da base na barra lateral para liberar a digitação.")
    else:
        st.header("🎥 Tela de Bipagem Dinâmica")
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
                    if inv_ativo and not contagens_atuais.empty:
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
                            ativo_selecionado_str = st.selectbox("Selecione o número do ATIVO obrigatório:", lista_ativos_limpos)
                            lote_selecionado = None
                            linha_selecionada = next(row for idx, row in df_pendentes.iterrows() if normalizar_valor(row['Ativo']) == ativo_selecionado_str)
                            ativo_selecionado = linha_selecionada['Ativo']
                        elif tem_lote_valores:
                            st.markdown('<div class="alerta-obrigatorio">⚠️ ATENÇÃO: Este item possui controle por LOTE. Selecione o lote correspondente:</div>', unsafe_allow_html=True)
                            lista_lotes_limpos = df_pendentes['Lote'].dropna().apply(normalizar_valor).unique()
                            lote_selecionado_str = st.selectbox("Selecione o LOTE correspondente:", lista_lotes_limpos)
                            ativo_selecionado = None
                            linha_selecionada = next(row for idx, row in df_pendentes.iterrows() if normalizar_valor(row['Lote']) == lote_selecionado_str)
                            lote_selecionado = linha_selecionada['Lote']
                        else:
                            st.write("📝 **Item Regular** (Sem variação complexa de Lote ou Ativo).")
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
                                'Quantidade_Contada': qtd_contada, 'Saldo_Sistemico': linha_selecionada.get('Qtd Estoque', 0), 'Status': 'Contado',
                                'Supervisor_Qtd': None, 'Supervisor_Etiqueta': 'Sim', 'Supervisor_Endereco': 'Sim'
                            }
                            st.session_state.contagens = pd.concat([st.session_state.contagens, pd.DataFrame([nova_contagem])], ignore_index=True)
                            salvar_contagens(st.session_state.contagens)
                            st.session_state.limpar_bipe = True
                            st.toast("Lançamento efetuado com sucesso!", icon="🚀")
                            st.rerun()
            else: st.error(f"❌ Código `{bip_limpo}` não mapeado na planilha base.")

        st.write("---")
        st.write("### 📜 Seus Lançamentos Concluídos neste Inventário")
        if not contagens_atuais.empty:
            st.dataframe(contagens_atuais[['Cód. Produto', 'Desc. Produto', 'Id. Estoq. Físico', 'Lote', 'Ativo', 'Quantidade_Contada', 'Saldo_Sistemico', 'Status']], use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# ABA 2: BASE DE ESTOQUE COMPLETA EM TEMPO REAL
# -----------------------------------------------------------------------------
with aba2:
    st.header("📄 Base de Estoque Carregada")
    if st.session_state.base_produtos.empty: st.info("Aguardando importação da planilha base.")
    else:
        df_visualizacao = st.session_state.base_produtos.copy()
        status_l, qtd_l = [], []
        for idx, row in df_visualizacao.iterrows():
            c, l, a = normalizar_valor(row['Cód. Produto']), normalizar_valor(row['Lote']), normalizar_valor(row['Ativo'])
            match = pd.DataFrame()
            if not contagens_atuais.empty:
                match = contagens_atuais[(contagens_atuais['Cód. Produto'].astype(str).apply(normalizar_valor) == c) & (contagens_atuais['Lote'].astype(str).apply(normalizar_valor) == l) & (contagens_atuais['Ativo'].astype(str).apply(normalizar_valor) == a)]
            if not match.empty:
                status_l.append("🟢 Contado"); qtd_l.append(int(match['Quantidade_Contada'].sum()))
            else:
                status_l.append("🔴 Pendente"); qtd_l.append(0)
        df_visualizacao.insert(0, "Status Contagem", status_l)
        df_visualizacao.insert(1, "Qtd Física Contada", qtd_l)
        st.dataframe(df_visualizacao, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# ABA 3: PAINEL SUPERVISOR (CONDUÇÃO DO FORMULÁRIO + TRAVA DE FECHAMENTO)
# -----------------------------------------------------------------------------
with aba3:
    st.header("🕵️‍♂️ Painel de Auditoria e Controle do Supervisor")
    
    if operador_atual != "Administrador Tel":
        st.error("🔒 Acesso restrito apenas ao Perfil de Supervisor/Administrador.")
    elif contagens_atuais.empty:
        st.info("Nenhum item foi bipado na aba de contagens para este inventário ainda. Painel em branco.")
    else:
        col_esq, col_dir = st.columns([2, 1.2])
        
        with col_esq:
            st.write("### 🛠️ Gestão de Qualidade Física")
            if not st.session_state.modo_auditoria_ativo:
                st.info("ℹ️ O painel de auditoria por amostragem está fechado. Clique abaixo para abrir o formulário.")
                if st.button("▶️ Iniciar Nova Auditoria de Supervisor", type="primary"):
                    st.session_state.modo_auditoria_ativo = True
                    st.rerun()
            else:
                if st.button("🛑 Fechar Painel de Auditoria (Limpar Tela)"):
                    st.session_state.modo_auditoria_ativo = False
                    st.rerun()
                    
                st.write("---")
                st.subheader("📋 Iniciar Auditoria por Amostragem")
                st.write("Preencha os dados coletados. Itens não conformes (Sem etiqueta/endereço) afetam diretamente o índice de acuracidade.")
                
                with st.form("auditoria_supervisor_form", clear_on_submit=True):
                    item_amostra = st.selectbox("Selecione o Item para Auditar/Validar:", contagens_atuais['Desc. Produto'].unique())
                    
                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        qtd_sup_real = st.number_input("Quantidade Real Apurada (Supervisor):", min_value=0, step=1)
                    with col_s2:
                        tem_etiqueta = st.selectbox("O material possui Etiqueta de Identificação?", ["Sim", "Não"])
                    with col_s3:
                        tem_endereco = st.selectbox("O material está no Endereçamento correto?", ["Sim", "Não"])
                        
                    gravar_auditoria = st.form_submit_button("💾 Validar Parâmetros e Atualizar Acuracidade")
                    
                    if gravar_auditoria:
                        # 🛡️ PROTEÇÃO CONTRA KEYERROR: Busca e alteração controlada com tratamento dinâmico do Saldo do Sistema
                        idx_global = st.session_state.contagens[(st.session_state.contagens['Inventario'] == inv_ativo) & (st.session_state.contagens['Desc. Produto'] == item_amostra)].index
                        
                        st.session_state.contagens.loc[idx_global, 'Quantidade_Contada'] = qtd_sup_real
                        st.session_state.contagens.loc[idx_global, 'Supervisor_Etiqueta'] = tem_etiqueta
                        st.session_state.contagens.loc[idx_global, 'Supervisor_Endereco'] = tem_endereco
                        st.session_state.contagens.loc[idx_global, 'Status'] = 'Auditado por Supervisor'
                        
                        salvar_contagens(st.session_state.contagens)
                        st.success(f"Auditoria para '{item_amostra}' gravada com sucesso!")
                        st.rerun()

            # Monitor de Divergências Atuais do Almoxarife (Filtragem Segura das Colunas)
            st.write("---")
            st.subheader("⚠️ Divergências Atuais de Saldo (Almoxarife)")
            df_divergentes = contagens_atuais[contagens_atuais['Quantidade_Contada'] != contagens_atuais['Saldo_Sistemico']]
            
            if df_divergentes.empty: 
                st.success("🎉 Nenhuma divergência de saldo pendente!")
            else: 
                colunas_desejadas = ['Cód. Produto', 'Desc. Produto', 'Lote', 'Ativo', 'Saldo_Sistemico', 'Quantidade_Contada', 'Supervisor_Etiqueta', 'Supervisor_Endereco', 'Status']
                colunas_validas = [c for c in colunas_desejadas if c in df_divergentes.columns]
                st.dataframe(df_divergentes[colunas_validas], use_container_width=True, hide_index=True)

        # 📊 COLUNA DA DIREITA: BLOCO INTEGRA DO FECHAMENTO DO INVENTÁRIO
        with col_dir:
            st.write("### 🔒 Encerramento Oficial")
            st.markdown("O fechamento consolida o inventário atual e atualiza permanentemente a aba ao lado.")
            
            if st.session_state.inventarios[inv_ativo]['status'] == 'Fechado':
                st.error("🔒 Este inventário já se encontra ENCERRADO e homologado no banco permanente.")
            else:
                if pendencias_reais > 0:
                    st.warning(f"Atenção: Ainda restam {pendencias_reais} itens pendentes de contagem na base.")
                    st.info("🔓 Perfil Administrador detectado. Liberação para fechamento parcial ativa.")
                    pode_fechar_real = st.button("Forçar Fechamento Parcial", use_container_width=True, type="primary")
                else:
                    st.success("✨ 100% dos materiais cadastrados foram auditados e bipados!")
                    pode_fechar_real = st.button("Finalizar e Homologar Inventário (100%)", type="primary", use_container_width=True)
                
                if pode_fechar_real:
                    dt_atual_str = datetime.now().strftime('%d/%m/%Y')
                    id_estoque_alvo = None
                    
                    if not contagens_atuais.empty:
                        id_estoque_alvo = int(contagens_atuais.iloc[0].get('Id. Estoq. Físico', 0))
                        linhas_corretas = 0
                        
                        for idx, row in contagens_atuais.iterrows():
                            # Se a coluna 'Saldo_Sistemico' falhar, busca na 'Saldo_Sistemico' padrão gravada na bipagem
                            val_sistemico = row.get('Saldo_Sistemico', 0)
                            bateu_qtd = row['Quantidade_Contada'] == val_sistemico
                            etiqueta_ok = str(row.get('Supervisor_Etiqueta', 'Sim')) == 'Sim'
                            endereco_ok = str(row.get('Supervisor_Endereco', 'Sim')) == 'Sim'
                            
                            if bateu_qtd and etiqueta_ok and endereco_ok:
                                linhas_corretas += 1
                                
                        acuracidade_final_calculada = (linhas_corretas / len(contagens_atuais)) * 100
                    else:
                        acuracidade_final_calculada = 100.0
                    
                    # Atualiza Status do Inventário
                    st.session_state.inventarios[inv_ativo]['status'] = 'Fechado'
                    st.session_state.inventarios[inv_ativo]['data_fechamento'] = datetime.now().strftime('%d/%m/%Y %H:%M')
                    st.session_state.inventarios[inv_ativo]['acuracidade'] = acuracidade_final_calculada
                    salvar_inventarios(st.session_state.inventarios)
                    
                    # Alimenta permanentemente a tabela master e muda o painel ao lado
                    if id_estoque_alvo:
                        for est in st.session_state.lista_estoques_fixos:
                            if est['Id. Estoq. Físico'] == id_estoque_alvo:
                                est['Ultima_Contagem'] = dt_atual_str
                                est['Acuracidade_Previa'] = round(acuracidade_final_calculada, 1)
                                break
                        salvar_estoques_master(st.session_state.lista_estoques_fixos)
                        
                    st.success("Inventário Encerrado com Sucesso!")
                    st.rerun()

# -----------------------------------------------------------------------------
# ABA 4: RELATÓRIO DE ACURACIDADE
# -----------------------------------------------------------------------------
with aba4:
    st.header("📈 Painel de Acuracidade Geral e Setorial")
    st.write("Acompanhe o nível de assertividade. **Nota:** Os índices só mudam após o fechamento completo do inventário.")
    
    st.markdown('<div class="acuracidade-container">', unsafe_allow_html=True)
    for est in st.session_state.lista_estoques_fixos:
        id_est = est['Id. Estoq. Físico']
        taxa_acuracidade = est.get('Acuracidade_Previa', 100.0)
            
        if taxa_acuracidade >= 95.0: classe_tag = "acuracidade-tag-green"
        elif taxa_acuracidade >= 85.0: classe_tag = "acuracidade-tag-yellow"
        else: classe_tag = "acuracidade-tag-red"
            
        st.markdown(f"""
        <div class="acuracidade-card">
            <div class="acuracidade-info">
                <div class="acuracidade-nome">{est['Desc. Estoque Físico']}</div>
                <div class="acuracidade-id">ID SETOR: {id_est} | Última Homologação: {est['Ultima_Contagem']}</div>
            </div>
            <div class="{classe_tag}">{taxa_acuracidade:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# ABA 5: FREQUÊNCIA DE ESTOQUES JBA
# -----------------------------------------------------------------------------
with aba5:
    st.header("🕒 Frequência e Janela Crítica de Contagem")
    st.write("Janela de segurança: Status **CRÍTICO** se o almoxarifado estiver há mais de 14 dias sem um encerramento homologado.")
    
    dados_tabela_frequencia = []
    data_limite = datetime.now() - timedelta(days=14)
    
    for est in st.session_state.lista_estoques_fixos:
        dt_contagem = datetime.strptime(est['Ultima_Contagem'], '%d/%m/%Y')
        dias_atraso = (datetime.now() - dt_contagem).days
        status_critico = "⚠️ CRÍTICO" if dt_contagem < data_limite else "🟢 Bom"
        
        dados_tabela_frequencia.append({
            "Id. Estoq. Físico": est['Id. Estoq. Físico'],
            "Desc. Estoque Físico": est['Desc. Estoque Físico'],
            "Última Homologação": est['Ultima_Contagem'],
            "Dias Sem Contar": dias_atraso,
            "Status de Criticidade": status_critico
        })
        
    df_freq_final = pd.DataFrame(dados_tabela_frequencia)
    def destacar_critico(val): return f"color: {'red' if '⚠️' in str(val) else 'green'}; font-weight: bold;"
    st.dataframe(df_freq_final.style.map(destakar_critico if 'destakar_critico' in locals() else destacar_critico, subset=['Status de Criticidade']), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# ABA 6: HISTÓRICO GERAL
# -----------------------------------------------------------------------------
with aba6:
    st.header("🗄️ Histórico Permanente de Inventários")
    inventarios_totais = sorted(st.session_state.inventarios.items(), key=lambda item: item[1].get('timestamp_criacao', ''), reverse=True)
    
    total_inventarios = len(inventarios_totais)
    itens_por_pagina = 15
    paginas_totais = math.ceil(total_inventarios / itens_por_pagina) if total_inventarios > 0 else 1
    
    if st.session_state.pagina_atual_hist > paginas_totais: st.session_state.pagina_atual_hist = paginas_totais
    inicio_idx = (st.session_state.pagina_atual_hist - 1) * itens_por_pagina
    inventarios_pagina = inventarios_totais[inicio_idx:inicio_idx + itens_por_pagina]
    
    for inv, info in inventarios_pagina:
        status_cor = "🟢" if info['status'] == "Aberto" else "🔴"
        with st.expander(f"{status_cor} {inv} | Status: {info['status']}"):
            st.write(f"**Notas:** {info['obs']}")
            if info['data_fechamento']: st.write(f"**Fechado em:** {info['data_fechamento']} | **Acuracidade Apurada:** {info.get('acuracidade', 100.0):.1f}%")
            
            dados_historicos_inv = st.session_state.contagens[st.session_state.contagens['Inventario'] == inv]
            if not dados_historicos_inv.empty:
                st.dataframe(dados_historicos_inv, use_container_width=True, hide_index=True)
                csv_dados = dados_historicos_inv.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Exportar Dados Completos (CSV)", data=csv_dados, file_name=f"Relatorio_{inv.replace(' ', '_')}.csv", mime="text/csv", key=f"dl_{inv}")
            else: st.caption("Nenhum lançamento físico associado.")
                
            if operador_atual == "Administrador Tel":
                if st.button(f"🗑️ Deletar Pasta Permanente: {inv}", key=f"del_{inv}", type="secondary"):
                    del st.session_state.inventarios[inv]
                    st.session_state.contagens = st.session_state.contagens[st.session_state.contagens['Inventario'] != inv]
                    salvar_inventarios(st.session_state.inventarios)
                    salvar_contagens(st.session_state.contagens)
                    st.toast(f"Pasta {inv} excluída permanentemente.", icon="🗑️")
                    st.rerun()

    if paginas_totais > 1:
        st.write("---")
        col_pag1, col_pag2, col_pag3 = st.columns([1, 2, 1])
        with col_pag1:
            if st.button("◀️ Página Anterior", disabled=(st.session_state.pagina_atual_hist == 1), use_container_width=True):
                st.session_state.pagina_atual_hist -= 1; st.rerun()
        with col_pag2: st.markdown(f"<p style='text-align: center; font-weight: bold;'>Exibindo página {st.session_state.pagina_atual_hist} de {paginas_totais}</p>", unsafe_allow_html=True)
        with col_pag3:
            if st.button("Próxima Página ▶️", disabled=(st.session_state.pagina_atual_hist == paginas_totais), use_container_width=True):
                st.session_state.pagina_atual_hist += 1; st.rerun()
