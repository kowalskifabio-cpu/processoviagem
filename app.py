import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DE ACESSO E ID ---
SHEET_ID = "1wnY0u6EpmdeKJicCaH8SU8AT4Ble2CBpODK9dKrKLsw"

# Função para conectar à planilha usando os Secrets do Streamlit Cloud
def conectar_planilha():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Puxa o JSON que você configurou no campo 'Secrets' do Streamlit
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

# Função para ler dados (usada nas abas de RH e Vouchers)
def carregar_dados():
    try:
        sheet = conectar_planilha()
        if sheet:
            df = pd.DataFrame(sheet.get_all_records())
            return df
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame(columns=["nome", "data_partida", "data_retorno", "meio_transporte", "endereco_obra", "status", "link_voucher"])

st.set_page_config(page_title="Gestão de Viagens - Marcenaria", layout="wide")

# --- INTERFACE DO USUÁRIO ---
st.title("🪚 Sistema de Controle de Viagens")
st.markdown("---")

# Criando as abas para organizar o fluxo
tab_colaborador, tab_rh, tab_vouchers = st.tabs([
    "🚀 Solicitar Viagem", 
    "⚖️ Painel de Aprovação (RH)", 
    "📂 Meus Vouchers"
])

# --- ABA 1: SOLICITAÇÃO DO COLABORADOR ---
with tab_colaborador:
    st.subheader("Nova Solicitação de Viagem")
    
    with st.form("form_viagem", clear_on_submit=True):
        nome_colaborador = st.text_input("Nome Completo do Colaborador")
        
        col1, col2 = st.columns(2)
        with col1:
            data_saida = st.date_input("Data de Saída", min_value=datetime.now().date())
            meio_transporte = st.selectbox("Meio de Transporte", ["Veículo Próprio", "Veículo da Empresa", "Ônibus", "Avião"])
        
        with col2:
            data_volta = st.date_input("Data de Retorno", min_value=data_saida)
            endereco_obra = st.text_input("Endereço Completo da Obra (para Hotel)")
        
        st.info("💡 Lembrete: Viagens comuns (24h de antecedência). Aéreas (20 dias).")
        
        enviar = st.form_submit_button("Enviar Solicitação")
        
        if enviar:
            hoje = datetime.now().date()
            pode_prosseguir = True
            
            # Validação de 24 horas
            if data_saida < hoje + timedelta(days=1):
                st.error("❌ Bloqueado: A solicitação deve ter no mínimo 24h de antecedência.")
                pode_prosseguir = False
            
            # Validação de 20 dias para Avião
            if meio_transporte == "Avião" and data_saida < hoje + timedelta(days=20):
                st.warning("⚠️ Alerta: Passagens aéreas exigem 20 dias de antecedência. O RH será notificado desta urgência.")
            
            if pode_prosseguir:
                # Cálculo de diárias
                dias = (data_volta - data_saida).days + 1
                valor_diaria = 70.00
                total_alimentacao = dias * valor_diaria
                
                try:
                    sheet = conectar_planilha()
                    # AQUI ESTAVA O ERRO DE SINTAXE - AGORA FECHADO CORRETAMENTE
                    nova_linha = [
                        nome_colaborador, 
                        str(data_saida), 
                        str(data_volta), 
                        meio_transporte, 
                        endereco_obra, 
                        "Pendente", 
                        ""
                    ]
                    sheet.append_row(nova_linha)
                    
                    st.success(f"Solicitação enviada com sucesso para o RH!")
                    st.write(f"**Resumo:** {dias} dias de viagem. Valor previsto para alimentação: R$ {total_alimentacao:.2f}")
                except Exception as e:
                    st.error(f"Erro ao salvar na planilha: {e}")

# --- ABA 2: PAINEL DO RH ---
with tab_rh:
    st.subheader("Pedidos Pendentes")
    df_atual = carregar_dados()
    
    if df_atual.empty:
        st.write("Não há dados na planilha ou ela está vazia.")
    else:
        st.dataframe(df_atual, use_container_width=True)
        st.write("---")
        st.write("👉 **Instrução para o RH:** Para aprovar, acesse a planilha diretamente e mude o status para 'Aprovado' e cole o link do Google Drive no campo 'link_voucher'.")
        st.link_button("Abrir Planilha no Google Sheets", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")

# --- ABA 3: CONSULTA DE VOUCHERS ---
with tab_vouchers:
    st.subheader("Consultar Meus Documentos")
    nome_busca = st.text_input("Digite seu nome para filtrar")
    
    df_vouchers = carregar_dados()
    if not df_vouchers.empty and nome_busca:
        # Busca o nome na coluna 'nome' ignorando maiúsculas/minúsculas
        filtro = df_vouchers[df_vouchers['nome'].astype(str).str.contains(nome_busca, case=False, na=False)]
        if not filtro.empty:
            for index, row in filtro.iterrows():
                with st.expander(f"Viagem para {row['endereco_obra']} - Status: {row['status']}"):
                    st.write(f"**Transporte:** {row['meio_transporte']}")
                    st.write(f"**Saída:** {row['data_partida']} | **Retorno:** {row['data_retorno']}")
                    
                    if not row['link_voucher'] or row['link_voucher'] == "":
                        st.warning("Voucher ainda não disponível. Aguarde a compra pelo RH.")
                    else:
                        st.link_button("📥 Baixar Voucher (Google Drive)", str(row['link_voucher']))
        else:
            st.warning("Nenhuma viagem encontrada para este nome.")
