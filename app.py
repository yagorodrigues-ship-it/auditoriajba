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
# 2. BARRA LATERAL (Mapeamento de colunas flexível)
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
            
            # Padronizar nomes de colunas removendo espaços e tratando maiúsculas/minúsculas
            df_upload.columns = [str(c).strip() for c in df_upload.columns]
            
            # Garantir que as colunas críticas existam mesmo que vazias
            for col_obrigatoria in ['Lote', 'Ativo', 'Qtd Estoque', 'Codigo', 'Descricao']:
                if col_obrigatoria not in df_upload.columns:
                    df_upload[col_obrigatoria] = None
            
            st.session_state.base_produtos = df_upload
            st.toast("Planilha carregada e colunas mapeadas!", icon="✅")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")

    st.write("---")
    
    # Métricas da Lateral
    qtd_itens_base = len(st.session_state.base_produtos)
    qtd_lancamentos = len(st.session_state.contagens[st.session_state.contagens['Inventario'] == inv_ativo])
    
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">📋 Linhas Totais na Base</div>
        <div class="metric-value">{qtd_itens_base}</div>
    </div>
    <div class="metric-card" style="border-left-color: #2ed573;">
        <div class="metric-title">✅ Itens Já Contados</div>
        <div class="metric-value">{qtd_lancamentos}</div>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. PAINEL PRINCIPAL
# -----------------------------------------------------------------------------
aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "🔍 Contar Item", "📊 Painel Supervisor", "📈 Acuracidade", "🕒 Frequência", "🗄️ Histórico"
])

# -----------------------------------------------------------------------------
# ABA 1: CONTAGEM COM VALIDAÇÃO DE ATIVO E LOTE
# -----------------------------------------------------------------------------
with aba1:
    if st.session_state.base_produtos.empty:
        st.warning("⚠️ Mapeie o inventário e faça o upload da base na barra lateral para liberar a digitação.")
    else:
        st.header(f"🎥 Tela de Bipagem Dinâmica")
        
        # Campo de Bipagem do código de barras principal do item
        codigo_bipado = st.text_input("👉 BIPAR CÓDIGO DO MATERIAL:", key="bipador_input")
        
        if codigo_bipado:
            # Filtrar todas as ocorrências desse código na planilha base
            linhas_produto = st.session_state.base_produtos[st.session_state.base_produtos['Codigo'].astype(str) == str(codigo_bipado)]
            
            if not lines_produto.empty:
                descricao_item = linhas_produto.iloc[0]['Descricao']
                st.info(f"📦 **Item Identificado:** {descricao_item} (Código: {codigo_bipado})")
                
                # Procurar o que já foi preenchido para esse inventário para remover da tela e evitar duplicidade
                ja_contados = st.session_state.contagens[st.session_state.contagens['Inventario'] == inv_ativo]
                
                # Filtrar as opções que ainda estão PENDENTES de contagem
                linhas_pendentes = []
                for idx, row in linhas_produto.iterrows():
                    # Verificar se essa combinação exata de código + lote + ativo já foi computada
                    foi_contado = False
                    if not ja_contados.empty:
                        match = ja_contados[
                            (ja_contados['Codigo'].astype(str) == str(codigo_bipado)) & 
                            (ja_contados['Lote'].astype(str) == str(row['Lote'])) & 
                            (ja_contados['Ativo'].astype(str) == str(row['Ativo']))
                        ]
                        if not match.empty:
                            foi_contado = True
                    
                    if not foi_contado:
                        linhas_pendentes.append(row)
                
                # Se não houver mais linhas pendentes para esse código
                if len(linhas_pendentes) == 0:
                    st.success("🎉 Todas as variações (Lotes/Ativos) deste item já foram totalmente contabilizadas para este inventário!")
                else:
                    df_pendentes = pd.DataFrame(linhas_pendentes)
                    
                    # 💡 Regra de Negócio: Identificar o que a planilha exige
                    tem_ativo_valores = df_pendentes['Ativo'].notna().any() and (df_pendentes['Ativo'] != '').any()
                    tem_lote_valores = df_pendentes['Lote'].notna().any() and (df_pendentes['Lote'] != '').any()
                    
                    # Formulário dinâmico de inserção
                    with st.form("validacao_contagem", clear_on_submit=True):
                        
                        # CASO 1: A planilha possui dados na coluna ATIVO para este código
                        if tem_ativo_valores:
                            st.markdown('<div class="alerta-obrigatorio">⚠️ ATENÇÃO: Este item possui controle por ATIVO. Selecione qual ativo está conferindo:</div>', unsafe_allow_html=True)
                            lista_ativos = df_pendentes['Ativo'].dropna().unique()
                            ativo_selecionado = st.selectbox("Selecione o número do ATIVO obrigatório:", lista_ativos)
                            lote_selecionado = None
                            
                            # Filtra a linha correspondente ao Ativo escolhido para resgatar o saldo correto
                            linha_selecionada = df_pendentes[df_pendentes['Ativo'] == ativo_selecionado].iloc[0]
                        
                        # CASO 2: A planilha possui dados na coluna LOTE para este código
                        elif tem_lote_valores:
                            st.markdown('<div class="alerta-obrigatorio">⚠️ ATENÇÃO: Este item possui controle por LOTE. Selecione o lote que está conferindo:</div>', unsafe_allow_html=True)
                            lista_lotes = df_pendentes['Lote'].dropna().unique()
                            lote_selecionado = st.selectbox("Selecione o LOTE correspondente:", lista_lotes)
                            ativo_selecionado = None
                            
                            linha_selecionada = df_pendentes[df_pendentes['Lote'] == lote_selecionado].iloc[0]
                        
                        # CASO 3: Sem lote e sem ativo (Item de contagem simples por quantidade)
                        else:
                            st.write("📝 **Item Comum** (Sem exigência de Lote ou Ativo diferenciado).")
                            ativo_selecionado = None
                            lote_selecionado = None
                            linha_selecionada = df_pendentes.iloc[0]
                        
                        # Inputs de quantidades e confirmação
                        col_c1, col_c2 = st.columns(2)
                        with col_c1:
                            qtd_contada = st.number_input("Digite a quantidade física contada:", min_value=0, step=1, value=1)
                        with col_c2:
                            obs_registro = st.text_input("Observações do lançamento:")
                            
                        submeter_registro = st.form_submit_button("💾 Salvar e Validar Contagem")
                        
                        if submeter_registro:
                            # Adicionar no histórico de contagens feitas
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
                st.error("❌ Código de barras não localizado em nenhuma linha da planilha base carregada.")

        # Tabela das contagens já realizadas abaixo para visualização do operador
        st.write("---")
        st.write("### 📜 Seus Lançamentos Concluídos neste Inventário")
        contagens_atuais = st.session_state.contagens[st.session_state.contagens['Inventario'] == inv_ativo]
        st.dataframe(contagens_atuais, use_container_width=True)

# -----------------------------------------------------------------------------
# DEMAIS ABAS (Manutenção do fluxo do painel anterior)
# -----------------------------------------------------------------------------
with aba2:
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

with aba3:
    st.header("📈 Relatório de Acuracidade Geral")
    if not contagens_atuais.empty:
        corretos = (contagens_atuais['Quantidade_Contada'] == contagens_atuais['Saldo_Sistemico']).sum()
        total = len(contagens_atuais)
        taxa = (corretos / total) * 100
        st.metric("🎯 Taxa de Acuracidade Atual", f"{taxa:.2f} %")
    else:
        st.info("Nenhum dado lançado para calcular acuracidade.")

with aba4:
    st.header("🕒 Status e Frequência por Setor")
    st.dataframe(st.session_state.frequencia_estoques, use_container_width=True)

with aba5:
    st.header("🗄️ Histórico e Exportação")
    if not contagens_atuais.empty:
        csv_data = contagens_atuais.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exportar Relatório de Contagem Atual para Excel/CSV", data=csv_data, file_name="inventario_final.csv", mime="text/csv")
