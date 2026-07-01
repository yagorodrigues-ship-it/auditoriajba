import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Configuração da página
st.set_page_config(page_title="Sistema de Inventário Inteligente", layout="wide")

# -----------------------------------------------------------------------------
# 1. INICIALIZAÇÃO DO BANCO DE DADOS EM MEMÓRIA (Session State)
# -----------------------------------------------------------------------------
if 'inventarios' not in st.session_state:
    st.session_state.inventarios = {
        '#2 - 2194 teste (Aberto)': {
            'status': 'Aberto', 'data_fechamento': None, 'acuracidade': 0.0, 'obs': 'Teste de bipagem dinâmica'
        }
    }

if 'base_produtos' not in st.session_state:
    st.session_state.base_produtos = pd.DataFrame()

if 'contagens' not in st.session_state:
    st.session_state.contagens = pd.DataFrame(columns=[
        'Inventario', 'Codigo', 'Descricao', 'Lote', 'Serial', 'Dt_Vencto', 'Complemento', 'Ativo', 
        'Quantidade_Contada', 'Saldo_Sistemico', 'Status'
    ])

if 'frequencia_estoques' not in st.session_state:
    st.session_state.frequencia_estoques = pd.DataFrame([
        {"Estoque": "Almoxarifado Central", "Ultima_Contagem": "20/06/2026", "Dias_Sem_Contar": 10, "Frequencia_Exigida": "Mensal (30 dias)", "Status": "Normal"},
        {"Estoque": "Depósito de Químicos", "Ultima_Contagem": "15/03/2026", "Dias_Sem_Contar": 108, "Frequencia_Exigida": "Trimestral (90 dias)", "Status": "CRÍTICO"}
    ])

# Estilos CSS
st.markdown("""
    <style>
    .metric-card { background-color: #1a2436; padding: 20px; border-radius: 10px; color: white; margin-bottom: 15px; border-left: 5px solid #2e66ff; }
    .metric-title { font-size: 12px; font-weight: bold; text-transform: uppercase; opacity: 0.8; }
    .metric-value { font-size: 32px; font-weight: bold; margin-top: 5px; }
    .alerta-obrigatorio { background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 5px; border-left: 5px solid #ffc107; margin-bottom: 15px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

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
    
    st.subheader("📂 Selecione o Inventário Ativo")
    lista_invs = list(st.session_state.inventarios.keys())
    inv_ativo = st.selectbox("Inventário em andamento:", lista_invs, index=0)
    
    st.write("---")
    
    st.subheader("📁 Carregar Planilha Base")
    uploaded_file = st.file_uploader("Arraste ou selecione o arquivo (.xlsx, .csv)", type=["xlsx", "csv"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_upload = pd.read_csv(uploaded_file)
            else:
                df_upload = pd.read_excel(uploaded_file)
            
            # Padronizar nomes de colunas eliminando espaços extras
            df_upload.columns = [str(c).strip() for c in df_upload.columns]
            
            # Garantir existência das colunas críticas para o motor de busca funcionar
            for col_obrigatoria in ['Lote', 'Ativo', 'Qtd Estoque', 'Codigo', 'Descricao']:
                if col_obrigatoria not in df_upload.columns:
                    df_upload[col_obrigatoria] = None
            
            st.session_state.base_produtos = df_upload
            st.toast("Planilha carregada com sucesso!", icon="✅")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    st.write("---")
    
    # FILTRAGEM GLOBAL DE CONTAGENS (Evita o NameError entre as abas)
    contagens_atuais = st.session_state.contagens[st.session_state.contagens['Inventario'] == inv_ativo]
    
    # Contagem de pendências dinâmicas baseadas na regra de chaves únicas
    linhas_contadas_set = set()
    if not contagens_atuais.empty:
        for idx, r in contagens_atuais.iterrows():
            linhas_contadas_set.add((str(r['Codigo']), str(r['Lote']), str(r['Ativo'])))
            
    total_linhas_base = len(st.session_state.base_produtos)
    it_contados = len(linhas_contadas_set)
    pendencias_reais = max(0, total_linhas_base - it_contados)
    
    # Métricas Visuais da Lateral
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
# 3. PAINEL PRINCIPAL (Abas de Navegação conforme seu Layout)
# -----------------------------------------------------------------------------
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "🔍 Contar Item", 
    "📄 Base de Estoque (Tempo Real)", 
    "📊 Painel Supervisor", 
    "📈 Acuracidade", 
    "🕒 Frequência", 
    "🗄️ Histórico"
])

# -----------------------------------------------------------------------------
# ABA 1: TELA DE BIPAGEM E VALIDAÇÃO
# -----------------------------------------------------------------------------
with aba1:
    if st.session_state.base_produtos.empty:
        st.warning("⚠️ Mapeie o inventário e faça o upload da base na barra lateral para liberar a digitação.")
    else:
        st.header(f"🎥 Tela de Bipagem Dinâmica")
        
        codigo_bipado = st.text_input("👉 BIPAR CÓDIGO DO MATERIAL:", key="bipador_input")
        
        if codigo_bipado:
            linhas_produto = st.session_state.base_produtos[st.session_state.base_produtos['Codigo'].astype(str) == str(codigo_bipado)]
            
            if not linhas_produto.empty:
                descricao_item = linhas_produto.iloc[0]['Descricao']
                st.info(f"📦 **Item Identificado:** {descricao_item} (Código: {codigo_bipado})")
                
                # Filtrar sub-itens pendentes
                linhas_pendentes = []
                for idx, row in linhas_produto.iterrows():
                    foi_contado = False
                    if not contagens_atuais.empty:
                        match = contagens_atuais[
                            (contagens_atuais['Codigo'].astype(str) == str(codigo_bipado)) & 
                            (contagens_atuais['Lote'].astype(str) == str(row['Lote'])) & 
                            (contagens_atuais['Ativo'].astype(str) == str(row['Ativo']))
                        ]
                        if not match.empty:
                            foi_contado = True
                    
                    if not foi_contado:
                        linhas_pendentes.append(row)
                
                if len(linhas_pendentes) == 0:
                    st.success("🎉 Todas as variações (Lotes/Ativos) deste item já foram totalmente contabilizadas!")
                else:
                    df_pendentes = pd.DataFrame(linhas_pendentes)
                    
                    tem_ativo_valores = df_pendentes['Ativo'].notna().any() and (df_pendentes['Ativo'] != '').any()
                    tem_lote_valores = df_pendentes['Lote'].notna().any() and (df_pendentes['Lote'] != '').any()
                    
                    with st.form("validacao_contagem", clear_on_submit=True):
                        
                        if tem_ativo_valores:
                            st.markdown('<div class="alerta-obrigatorio">⚠️ ATENÇÃO: Este item possui controle por ATIVO. Selecione qual ativo está conferindo:</div>', unsafe_allow_html=True)
                            lista_ativos = df_pendentes['Ativo'].dropna().unique()
                            ativo_selecionado = st.selectbox("Selecione o número do ATIVO obrigatório:", lista_ativos)
                            lote_selecionado = None
                            linha_selecionada = df_pendentes[df_pendentes['Ativo'] == ativo_selecionado].iloc[0]
                        
                        elif tem_lote_valores:
                            st.markdown('<div class="alerta-obrigatorio">⚠️ ATENÇÃO: Este item possui controle por LOTE. Selecione o lote que está conferindo:</div>', unsafe_allow_html=True)
                            lista_lotes = df_pendentes['Lote'].dropna().unique()
                            lote_selecionado = st.selectbox("Selecione o LOTE correspondente:", lista_lotes)
                            ativo_selecionado = None
                            linha_selecionada = df_pendentes[df_pendentes['Lote'] == lote_selecionado].iloc[0]
                        
                        else:
                            st.write("📝 **Item Comum** (Sem exigência de Lote ou Ativo diferenciado).")
                            ativo_selecionado = None
                            lote_selecionado = None
                            linha_selecionada = df_pendentes.iloc[0]
                        
                        col_c1, col_c2 = st.columns(2)
                        with col_c1:
                            qtd_contada = st.number_input("Digite a quantidade física contada:", min_value=0, step=1, value=1)
                        with col_c2:
                            obs_registro = st.text_input("Observações do lançamento:")
                            
                        submeter_registro = st.form_submit_button("💾 Salvar e Validar Contagem")
                        
                        if submeter_registro:
                            nova_contagem = {
                                'Inventario': inv_ativo,
                                'Codigo': codigo_bipado,
                                'Descricao': descricao_item,
                                'Lote': lote_selecionado if lote_selecionado else linha_selecionada.get('Lote', None),
                                'Serial': linha_selecionada.get('Serial', None),
                                'Dt_Vencto': linha_selecionada.get('Dt. Vencto', None),
                                'Complemento': linha_selecionada.get('Complemento', None),
                                'Ativo': ativo_selecionado if ativo_selecionado else linha_selecionada.get('Ativo', None),
                                'Quantidade_Contada': qtd_contada,
                                'Saldo_Sistemico': linha_selecionada.get('Qtd Estoque', 0),
                                'Status': 'Contado'
                            }
                            st.session_state.contagens = pd.concat([st.session_state.contagens, pd.DataFrame([nova_contagem])], ignore_index=True)
                            st.toast(f"Sucesso! Item contabilizado.", icon="🚀")
                            st.rerun()
            else:
                st.error("❌ Código de barras não localizado na planilha base.")

        st.write("---")
        st.write("### 📜 Seus Lançamentos Concluídos neste Inventário")
        st.dataframe(contagens_atuais, use_container_width=True)

# -----------------------------------------------------------------------------
# ABA 2: BASE DE ESTOQUE COMPLETA EM TEMPO REAL (NOVA ABA SOLICITADA)
# -----------------------------------------------------------------------------
with aba2:
    st.header("📄 Base de Estoque Carregada")
    st.write("Abaixo consta a lista completa dos itens da sua planilha. As colunas atualizam em tempo real conforme as bipagens acontecem.")
    
    if st.session_state.base_produtos.empty:
        st.info("Aguardando upload da planilha base na barra lateral para exibir a lista completa de estoque.")
    else:
        # Fazer uma cópia para não mexer na planilha original bruta
        df_visualizacao = st.session_state.base_produtos.copy()
        
        status_contagem_lista = []
        qtd_contada_lista = []
        
        # Varre linha por linha da planilha importada e verifica se já consta na aba de contados
        for idx, row in df_visualizacao.iterrows():
            codigo_row = str(row['Codigo'])
            lote_row = str(row['Lote'])
            ativo_row = str(row['Ativo'])
            
            match = pd.DataFrame()
            if not contagens_atuais.empty:
                match = contagens_atuais[
                    (contagens_atuais['Codigo'].astype(str) == codigo_row) & 
                    (contagens_atuais['Lote'].astype(str) == lote_row) & 
                    (contagens_atuais['Ativo'].astype(str) == ativo_row)
                ]
            
            if not match.empty:
                status_contagem_lista.append("🟢 Contado")
                # Soma caso tenha mais de um lançamento do mesmo item
                qtd_contada_lista.append(int(match['Quantidade_Contada'].sum()))
            else:
                status_contagem_lista.append("🔴 Pendente")
                qtd_contada_lista.append(0)
        
        # Insere as duas novas colunas de controle no início do dataframe visual
        df_visualizacao.insert(0, "Status Contagem", status_contagem_lista)
        df_visualizacao.insert(1, "Qtd Física Contada", qtd_contada_lista)
        
        # Filtros Rápidos no topo da tabela
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_status = st.multiselect("Filtrar por Status de Processamento:", ["🔴 Pendente", "🟢 Contado"], default=["🔴 Pendente", "🟢 Contado"])
        with col_f2:
            busca_texto = st.text_input("Filtrar por Nome / Descrição do Material:", placeholder="Digite para buscar...")
            
        # Aplicar filtros dinâmicos na tabela
        if filtro_status:
            df_visualizacao = df_visualizacao[df_visualizacao['Status Contagem'].isin(filtro_status)]
        if busca_texto:
            df_visualizacao = df_visualizacao[df_visualizacao['Descricao'].astype(str).str.contains(busca_texto, case=False, na=False)]
            
        # Exibe a planilha formatada
        st.dataframe(df_visualizacao, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# ABA 3: PAINEL DO SUPERVISOR
# -----------------------------------------------------------------------------
with aba3:
    st.header("🕵️‍♂️ Painel de Auditoria do Supervisor")
    df_divergentes = st.session_state.contagens[
        (st.session_state.contagens['Inventario'] == inv_ativo) & 
        (st.session_state.contagens['Quantidade_Contada'] != st.session_state.contagens['Saldo_Sistemico'])
    ]
    if df_divergentes.empty:
        st.success("🎉 Nenhuma divergência encontrada no momento!")
    else:
        st.warning(f"Atenção: {len(df_divergentes)} linhas apresentam divergência de saldo.")
        st.dataframe(df_divergentes[['Codigo', 'Descricao', 'Lote', 'Ativo', 'Saldo_Sistemico', 'Quantidade_Contada', 'Status']], use_container_width=True)

# -----------------------------------------------------------------------------
# ABA 4: ACURACIDADE
# -----------------------------------------------------------------------------
with aba4:
    st.header("📈 Relatório de Acuracidade Geral")
    if not contagens_atuais.empty:
        corretos = (contagens_atuais['Quantidade_Contada'] == contagens_atuais['Saldo_Sistemico']).sum()
        total = len(contagens_atuais)
        taxa = (corretos / total) * 100
        st.metric("🎯 Taxa de Acuracidade Atual", f"{taxa:.2f} %")
    else:
        st.info("Nenhum dado lançado para calcular acuracidade.")

# -----------------------------------------------------------------------------
# ABA 5: FREQUÊNCIA
# -----------------------------------------------------------------------------
with aba5:
    st.header("🕒 Status e Frequência por Setor")
    st.dataframe(st.session_state.frequencia_estoques, use_container_width=True)

# -----------------------------------------------------------------------------
# ABA 6: HISTÓRICO
# -----------------------------------------------------------------------------
with aba6:
    st.header("🗄️ Histórico e Exportação")
    if not contagens_atuais.empty:
        csv_data = contagens_atuais.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exportar Relatório de Contagem Atual para Excel/CSV", data=csv_data, file_name="inventario_final.csv", mime="text/csv")
    else:
        st.info("Faça lançamentos para liberar a exportação de dados.")
