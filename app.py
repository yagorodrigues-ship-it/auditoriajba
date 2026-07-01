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
        'Inventario', 'Cód. Produto', 'Desc. Produto', 'Id. Estoq. Físico', 'Desc. Estoque Físico',
        'Lote', 'Serial', 'Dt_Vencto', 'Complemento', 'Ativo', 'Quantidade_Contada', 'Saldo_Sistemico', 'Status'
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
    .info-estoque { background-color: #f0f2f6; padding: 12px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid #1c83e1; }
    </style>
""", unsafe_allow_html=True)

# Helper para normalizar e limpar valores em strings comparáveis (corrige problemas com .0 e espaços)
def normalizar_valor(val):
    if pd.isna(val) or str(val).strip().lower() == 'nan' or str(val).strip() == '':
        return ""
    v_str = str(val).strip()
    if v_str.endswith('.0'):
        return v_str[:-2]
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
            
            df_upload.columns = [str(c).strip() for c in df_upload.columns]
            
            mapeamento_nomes = {
                'Codigo': 'Cód. Produto', 'Descricao': 'Desc. Produto',
                'Id. Estoque Fisico': 'Id. Estoq. Físico', 'Id. Estoque Físico': 'Id. Estoq. Físico',
                'Desc. Estoque Fisico': 'Desc. Estoque Físico'
            }
            df_upload.rename(columns=mapeamento_nomes, inplace=True)
            
            colunas_obrigatorias = ['Lote', 'Ativo', 'Qtd Estoque', 'Cód. Produto', 'Desc. Produto', 'Id. Estoq. Físico', 'Desc. Estoque Físico']
            for col in colunas_obrigatorias:
                if col not in df_upload.columns:
                    df_upload[col] = None
            
            st.session_state.base_produtos = df_upload
            st.toast("Planilha carregada com sucesso!", icon="✅")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    st.write("---")
    
    # FILTRAGEM GLOBAL DE CONTAGENS
    contagens_atuais = st.session_state.contagens[st.session_state.contagens['Inventario'] == inv_ativo]
    
    # Calcular pendências reais cruzando chaves tratadas
    linhas_contadas_set = set()
    if not contagens_atuais.empty:
        for idx, r in contagens_atuais.iterrows():
            linhas_contadas_set.add((normalizar_valor(r['Cód. Produto']), normalizar_valor(r['Lote']), normalizar_valor(r['Ativo'])))
            
    total_linhas_base = len(st.session_state.base_produtos)
    it_contados = 0
    
    if total_linhas_base > 0:
        for idx, row in st.session_state.base_produtos.iterrows():
            chave_row = (normalizar_valor(row['Cód. Produto']), normalizar_valor(row['Lote']), normalizar_valor(row['Ativo']))
            if chave_row in linhas_contadas_set:
                it_contados += 1
                
    pendencias_reais = max(0, total_linhas_base - it_contados)
    
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
# ABA 1: TELA DE BIPAGEM COM RESET AUTOMÁTICO E TRAVA DE DUPLICIDADE
# -----------------------------------------------------------------------------
with aba1:
    if st.session_state.base_produtos.empty:
        st.warning("⚠️ Mapeie o inventário e faça o upload da base na barra lateral para liberar a digitação.")
    else:
        st.header(f"🎥 Tela de Bipagem Dinâmica")
        
        # Campo para o leitor de código de barras
        texto_bipado_bruto = st.text_input("👉 BIPAR CÓDIGO DO MATERIAL:", key="bipador_input")
        
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
                if not linhas_produto.empty:
                    codigo_verdadeiro_encontrado = bip_limpo

            if not linhas_produto.empty:
                desc_produto = linhas_produto.iloc[0]['Desc. Produto']
                id_estoque_fisico = linhas_produto.iloc[0]['Id. Estoq. Físico']
                desc_estoque_fisico = líneas_produto.iloc[0]['Desc. Estoque Físico']
                
                # Filtrar estritamente o que ainda NÃO foi contado para remover do Dropdown em tempo real
                linhas_pendentes = []
                for idx, row in linhas_produto.iterrows():
                    foi_contado = False
                    if not contagens_atuais.empty:
                        match = contagens_atuais[
                            (contagens_atuais['Cód. Produto'].astype(str).apply(normalizar_valor) == normalizar_valor(codigo_verdadeiro_encontrado)) & 
                            (contagens_atuais['Lote'].astype(str).apply(normalizar_valor) == normalizar_valor(row['Lote'])) & 
                            (contagens_atuais['Ativo'].astype(str).apply(normalizar_valor) == normalizar_valor(row['Ativo']))
                        ]
                        if not match.empty:
                            foi_contado = True
                    
                    if not foi_contado:
                        linhas_pendentes.append(row)
                
                # Se tudo já foi bipado, exibe mensagem e não renderiza formulários antigos
                if len(linhas_pendentes) == 0:
                    st.success("🎉 Todas as variações de Lote/Ativo deste produto já foram contabilizadas!")
                    if st.button("Limpar Tela para Próximo Bipe"):
                        st.session_state.bipador_input = ""
                        st.rerun()
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
                            
                            linha_selecionada = None
                            for idx, row in df_pendentes.iterrows():
                                if normalizar_valor(row['Ativo']) == ativo_selecionado_str:
                                    linha_selecionada = row
                                    break
                            ativo_selecionado = linha_selecionada['Ativo']
                        
                        elif tem_lote_valores:
                            st.markdown('<div class="alerta-obrigatorio">⚠️ ATENÇÃO: Este item possui controle por LOTE. Selecione o lote correspondente:</div>', unsafe_allow_html=True)
                            lista_lotes_limpos = df_pendentes['Lote'].dropna().apply(normalizar_valor).unique()
                            lote_selecionado_str = st.selectbox("Selecione o LOTE correspondente (Apenas Pendentes):", lista_lotes_limpos)
                            ativo_selecionado = None
                            
                            linha_selecionada = None
                            for idx, row in df_pendentes.iterrows():
                                if normalizar_valor(row['Lote']) == lote_selecionado_str:
                                    linha_selecionada = row
                                    break
                            lote_selecionado = linha_selecionada['Lote']
                        
                        else:
                            st.write("📝 **Item Comum** (Sem variação de Lote ou Ativo pendente).")
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
                                'Cód. Produto': codigo_verdadeiro_encontrado,
                                'Desc. Produto': desc_produto,
                                'Id. Estoq. Físico': id_estoque_fisico,
                                'Desc. Estoque Físico': desc_estoque_fisico,
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
                            
                            # 🔥 ESSENCIAL: Reseta o input do bipe para apagar a descrição e deixar pronto para o próximo código
                            st.session_state.bipador_input = ""
                            st.toast(f"Sucesso! Item adicionado.", icon="🚀")
                            st.rerun()
            else:
                st.error(f"❌ Código de barras `{bip_limpo}` não localizado.")

        st.write("---")
        st.write("### 📜 Seus Lançamentos Concluídos neste Inventário")
        
        # Filtrar exibição final para conter apenas as colunas estruturadas, evitando colunas fantasmas duplicadas
        if not contagens_atuais.empty:
            st.dataframe(contagens_atuais[[
                'Inventario', 'Cód. Produto', 'Desc. Produto', 'Id. Estoq. Físico', 'Desc. Estoque Físico',
                'Lote', 'Ativo', 'Quantidade_Contada', 'Saldo_Sistemico', 'Status'
            ]], use_container_width=True)
        else:
            st.info("Nenhum lançamento feito ainda.")

# -----------------------------------------------------------------------------
# ABA 2: BASE DE ESTOQUE COMPLETA EM TEMPO REAL
# -----------------------------------------------------------------------------
with aba2:
    st.header("📄 Base de Estoque Carregada")
    if st.session_state.base_produtos.empty:
        st.info("Aguardando upload da planilha base.")
    else:
        df_visualizacao = st.session_state.base_produtos.copy()
        status_contagem_lista = []
        qtd_contada_lista = []
        
        for idx, row in df_visualizacao.iterrows():
            c_row = normalizar_valor(row['Cód. Produto'])
            l_row = normalizar_valor(row['Lote'])
            a_row = normalizar_valor(row['Ativo'])
            
            match = pd.DataFrame()
            if not contagens_atuais.empty:
                match = contagens_atuais[
                    (contagens_atuais['Cód. Produto'].astype(str).apply(normalizar_valor) == c_row) & 
                    (contagens_atuais['Lote'].astype(str).apply(normalizar_valor) == l_row) & 
                    (contagens_atuais['Ativo'].astype(str).apply(normalizar_valor) == a_row)
                ]
            
            if not match.empty:
                status_contagem_lista.append("🟢 Contado")
                qtd_contada_lista.append(int(match['Quantidade_Contada'].sum()))
            else:
                status_contagem_lista.append("🔴 Pendente")
                qtd_contada_lista.append(0)
        
        df_visualizacao.insert(0, "Status Contagem", status_contagem_lista)
        df_visualizacao.insert(1, "Qtd Física Contada", qtd_contada_lista)
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_status = st.multiselect("Filtrar por Status:", ["🔴 Pendente", "🟢 Contado"], default=["🔴 Pendente", "🟢 Contado"], key="f_b_stat")
        with col_f2:
            busca_texto = st.text_input("Buscar por Descrição:", placeholder="Digite...", key="b_b_txt")
            
        if filtro_status:
            df_visualizacao = df_visualizacao[df_visualizacao['Status Contagem'].isin(filtro_status)]
        if busca_texto:
            df_visualizacao = df_visualizacao[df_visualizacao['Desc. Produto'].astype(str).str.contains(busca_texto, case=False, na=False)]
            
        st.dataframe(df_visualizacao, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# DEMAIS ABAS (Supervisor, Acuracidade, Frequência, Histórico)
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
        st.warning(f"Atenção: {len(df_divergentes)} linhas apresentam divergência.")
        st.dataframe(df_divergentes[['Cód. Produto', 'Desc. Produto', 'Id. Estoq. Físico', 'Lote', 'Ativo', 'Saldo_Sistemico', 'Quantidade_Contada']], use_container_width=True)

with aba4:
    st.header("📈 Relatório de Acuracidade Geral")
    if not contagens_atuais.empty:
        corretos = (contagens_atuais['Quantidade_Contada'] == contagens_atuais['Saldo_Sistemico']).sum()
        total = len(contagens_atuais)
        taxa = (corretos / total) * 100
        st.metric("🎯 Taxa de Acuracidade Atual", f"{taxa:.2f} %")
    else:
        st.info("Nenhum dado lançado.")

with aba5:
    st.header("🕒 Status e Frequência por Setor")
    st.dataframe(st.session_state.frequencia_estoques, use_container_width=True)

with aba6:
    st.header("🗄️ Histórico e Exportação")
    if not contagens_atuais.empty:
        csv_data = contagens_atuais.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exportar Relatório para CSV", data=csv_data, file_name="inventario_final.csv", mime="text/csv")
