import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# --- FUNÇÃO DE CONEXÃO ---
def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # Usando o ID da sua planilha fornecido
    return client.open_by_key("1wnY0u6EpmdeKJicCaH8SU8AT4Ble2CBpODK9dKrKLsw").sheet1

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Workflow Viagens Marcenaria", layout="wide")

st.title("🪚 Fluxo de Viagens - Marcenaria")
st.markdown("---")

tab1, tab2 = st.tabs(["🚀 Solicitar Viagem", "📑 Painel Administrativo"])

# --- ABA DE SOLICITAÇÃO ---
with tab1:
    with st.form("form_viagem", clear_on_submit=True):
        st.subheader("Nova Solicitação")
        nome = st.text_input("Nome do Colaborador")
        col1, col2 = st.columns(2)
        
        with col1:
            data_partida = st.date_input("Data de Partida", min_value=datetime.now().date())
            transporte = st.selectbox("Meio de Transporte", ["Veículo Próprio", "Ônibus", "Avião"])
        
        with col2:
            data_retorno = st.date_input("Data de Retorno", min_value=data_partida)
            endereco_obra = st.text_input("Endereço da Obra")

        enviar = st.form_submit_button("Enviar para RH")

        if enviar:
            hoje = datetime.now().date()
            erros = []
            
            # Validação 24h
            if data_partida < hoje + timedelta(days=1):
                erros.append("❌ Solicitações gerais precisam de 24h de antecedência.")
            
            # Validação Avião 20 dias
            if transporte == "Avião" and data_partida < hoje + timedelta(days=20):
                erros.append("⚠️ Viagens aéreas exigem 20 dias de antecedência para emissão de passagens.")

            if erros:
                for erro in erros:
                    st.error(erro)
            else:
                try:
                    sheet = conectar_planilha()
                    # Organizando os dados para a planilha
                    nova_linha = [
                        nome, 
                        str(data_partida), 
                        str(data_retorno), 
                        transporte, 
                        endereco_obra, 
                        "Pendente", # Status para o RH alterar
                        ""          # Espaço para o link do Voucher
                    ]
                    sheet.append_row(nova_linha)
                    st.success("✅ Solicitação enviada! O RH analisará seu pedido.")
                except Exception as e:
                    st.error(f"Erro ao salvar na planilha: {e}")

# --- ABA DE CONSULTA ---
with tab2:
    st.subheader("Status de Viagens e Vouchers")
    try:
        sheet = conectar_planilha()
        # Lê todos os dados da planilha e transforma em tabela
        dados = pd.DataFrame(sheet.get_all_records())
        if not dados.empty:
            st.dataframe(dados, use_container_width=True)
        else:
            st.info("Nenhuma solicitação encontrada.")
    except Exception as e:
        st.error("Erro ao carregar dados. Verifique se a planilha tem cabeçalhos na primeira linha.")
