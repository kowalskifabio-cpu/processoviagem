import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DE NEGÓCIO ---
VALOR_DIARIA_ALIMENTACAO = 80.00  # Valor fixo para alimentação por dia
ID_PLANILHA = "1wnY0u6EpmdeKJicCaH8SU8AT4Ble2CBpODK9dKrKLsw"

# --- FUNÇÃO DE CONEXÃO COM GOOGLE SHEETS ---
def conectar_planilha():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Busca as credenciais configuradas no Secrets do Streamlit Cloud
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open_by_key(ID_PLANILHA).sheet1
    except Exception as e:
        st.error(f"Erro na conexão com a planilha: {e}")
        return None

# --- CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(page_title="Workflow Viagens Marcenaria", layout="wide", page_icon="🚀")

st.title("🪚 Sistema de Gestão de Viagens - Marcenaria")
st.markdown("---")

# Navegação por Abas
tab_solicitacao, tab_rh, tab_vouchers = st.tabs([
    "📝 Nova Solicitação", 
    "⚖️ Painel de Aprovação (RH)", 
    "📂 Meus Vouchers"
])

# --- ABA 1: SOLICITAÇÃO (COLABORADOR) ---
with tab_solicitacao:
    st.subheader("Registrar Pedido de Viagem")
    
    with st.form("form_viagem", clear_on_submit=True):
        nome = st.text_input("Nome do Colaborador")
        
        col1, col2 = st.columns(2)
        with col1:
            data_partida = st.date_input("Data de Partida", min_value=datetime.now().date())
            meio_transporte = st.selectbox("Meio de Transporte", ["Veículo Empresa", "Ônibus", "Avião"])
        
        with col2:
            data_retorno = st.date_input("Data de Retorno", min_value=data_partida)
            endereco_obra = st.text_input("Endereço Completo da Obra (para reserva de hotel)")
        
        enviar = st.form_submit_button("Enviar para o RH")

        if enviar:
            hoje = datetime.now().date()
            erros = []
            
            # Validação de 24 horas (Regra Geral)
            if data_partida < hoje + timedelta(days=1):
                erros.append("❌ Erro: Solicitações de viagem devem ter no mínimo 24h de antecedência.")
            
            # Validação de 20 dias (Regra Aéreo)
            if meio_transporte == "Avião" and data_partida < hoje + timedelta(days=20):
                erros.append("❌ Erro: Passagens aéreas exigem no mínimo 20 dias de antecedência.")
            
            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                sheet = conectar_planilha()
                if sheet:
                    # Cálculo de Diárias
                    quantidade_dias = (data_retorno - data_partida).days + 1
                    total_estimado = quantidade_dias * VALOR_DIARIA_ALIMENTACAO
                    
                    # Preparação da linha para o Google Sheets
                    nova_linha = [
                        nome, 
                        str(data_partida), 
                        str(data_retorno), 
                        meio_transporte, 
                        endereco_obra, 
                        "Pendente",         # Status inicial
                        "",                 # Campo para link do voucher (vazio)
                        total_estimado      # Valor calculado
