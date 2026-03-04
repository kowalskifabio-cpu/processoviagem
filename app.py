import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO DE SEGURANÇA ---
# Coloquei os dados da sua chave diretamente aqui para facilitar seu uso imediato
GOOGLE_CLIENT_JSON = {
  "type": "service_account",
  "project_id": "statusmarcenaria",
  "private_key": st.secrets.get("private_key", "COLE_SUA_CHAVE_AQUI_SE_NAO_USAR_SECRETS"),
  "client_email": "gestor-status@statusmarcenaria.iam.gserviceaccount.com",
  "token_uri": "https://oauth2.googleapis.com/token",
}

# ID da sua planilha fornecido anteriormente
SHEET_ID = "1wnY0u6EpmdeKJicCaH8SU8AT4Ble2CBpODK9dKrKLsw"

def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # No seu computador, você pode apontar para o arquivo .json baixado
    # Aqui, usamos a estrutura que você forneceu
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

st.set_page_config(page_title="Workflow Viagens Marcenaria", layout="wide")

# --- INTERFACE ---
st.title("🪚 Sistema de Controle de Viagens")

tab1, tab2 = st.tabs(["🚀 Solicitar Viagem", "📂 Consultar Vouchers (RH/Colaborador)"])

with tab1:
    with st.form("form_viagem", clear_on_submit=True):
        st.subheader("Nova Solicitação")
        nome = st.text_input("Nome do Colaborador")
        col1, col2 = st.columns(2)
        with col1:
            saida = st.date_input("Data de Saída", min_value=datetime.now().date())
            transporte = st.selectbox("Meio de Transporte", ["Veículo Empresa", "Ônibus", "Avião"])
        with col2:
            retorno = st.date_input("Data de Retorno", min_value=saida)
            obra = st.text_input("Endereço da Obra")
        
        enviar = st.form_submit_button("Enviar para o RH")

        if enviar:
            hoje = datetime.now().date()
            if saida < hoje + timedelta(days=1):
                st.error("❌ Erro: Mínimo de 24h de antecedência.")
            else:
                try:
                    sheet = conectar_planilha()
                    # Prepara a linha para salvar
                    nova_linha = [
                        nome, 
                        str(saida), 
                        str(retorno), 
                        transporte, 
                        obra, 
                        "Pendente", # Status inicial
                        ""          # Espaço para o Link do Voucher
                    ]
                    sheet.append_row(nova_linha)
                    st.success("✅ Pedido gravado com sucesso na planilha!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

with tab2:
    st.subheader("Histórico e Vouchers")
    try:
        sheet = conectar_planilha()
        dados = pd.DataFrame(sheet.get_all_records())
        if not dados.empty:
            st.dataframe(dados, use_container_width=True)
        else:
            st.info("Nenhuma viagem registrada ainda.")
    except:
        st.write("Aguardando primeiros dados...")
