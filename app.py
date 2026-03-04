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
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # Retorna a aba 'viagens' (Sheet1)
        return client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

# Função para ler dados em tempo real
def carregar_dados():
    try:
        sheet = conectar_planilha()
        if sheet:
            # get_all_records() garante que lemos o dado mais atualizado do Google
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
            
            if data_saida < hoje + timedelta(days=1):
                st.error("❌ Bloqueado: A solicitação deve ter no mínimo 24h de antecedência.")
                pode_prosseguir = False
            
            if meio_transporte == "Avião" and data_saida < hoje + timedelta(days=20):
                st.warning("⚠️ Alerta: Passagens aéreas exigem 20 dias de antecedência. O RH será notificado desta urgência.")
            
            if pode_prosseguir:
                dias = (data_volta - data_saida).days + 1
                valor_diaria = 70.00
                total_alimentacao = dias * valor_diaria
                
                try:
                    sheet = conectar_planilha()
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

# --- ABA 2: PAINEL DO RH (AUTOMAÇÃO DE APROVAÇÃO) ---
with tab_rh:
    st.subheader("Gestão de Pedidos")
    df_rh = carregar_dados()
    
    if df_rh.empty:
        st.info("Não há solicitações registradas.")
    else:
        # Filtramos apenas os pendentes para o RH agir
        pendentes = df_rh[df_rh['status'] == "Pendente"]
        
        if pendentes.empty:
            st.success("🎉 Todas as solicitações foram processadas!")
        else:
            st.write(f"Existem **{len(pendentes)}** pedidos aguardando sua análise.")
            
            for index, row in pendentes.iterrows():
                # Criamos um cartão para cada pedido
                with st.expander(f"🔔 Pedido de {row['nome']} - Destino: {row['endereco_obra']}"):
                    st.write(f"📅 **Período:** {row['data_partida']} até {row['data_retorno']}")
                    st.write(f"Transporte: **{row['meio_transporte']}**")
                    
                    # Formulário de aprovação específico para esta linha
                    with st.form(key=f"form_rh_{index}"):
                        novo_link = st.text_input("Cole aqui o link do Voucher (Google Drive)", placeholder="https://drive.google.com/...")
                        col_btn1, col_btn2 = st.columns(2)
                        
                        aprovado = col_btn1.form_submit_button("✅ Aprovar e Salvar")
                        negado = col_btn2.form_submit_button("❌ Negar Solicitação")
                        
                        if aprovado:
                            sheet = conectar_planilha()
                            # Somamos +2 pois o Sheets começa em 1 e tem o cabeçalho
                            linha_index = index + 2 
                            sheet.update_cell(linha_index, 6, "Aprovado") # Coluna F (Status)
                            sheet.update_cell(linha_index, 7, novo_link)  # Coluna G (Voucher)
                            st.success(f"Solicitação de {row['nome']} APROVADA!")
                            st.rerun()
                            
                        if negado:
                            sheet = conectar_planilha()
                            linha_index = index + 2
                            sheet.update_cell(linha_index, 6, "Negado")
                            st.warning(f"Solicitação de {row['nome']} NEGADA.")
                            st.rerun()

# --- ABA 3: CONSULTA DE VOUCHERS ---
with tab_vouchers:
    st.subheader("Consultar Meus Documentos")
    nome_busca = st.text_input("Digite seu nome para filtrar")
    
    df_vouchers = carregar_dados()
    if not df_vouchers.empty and nome_busca:
        filtro = df_vouchers[df_vouchers['nome'].astype(str).str.contains(nome_busca, case=False, na=False)]
        if not filtro.empty:
            for index, row in filtro.iterrows():
                cor_status = "green" if row['status'] == "Aprovado" else "red" if row['status'] == "Negado" else "orange"
                
                with st.expander(f"Viagem para {row['endereco_obra']} - Status: {row['status']}"):
                    st.markdown(f"Status: :{cor_status}[**{row['status']}**]")
                    st.write(f"**Transporte:** {row['meio_transporte']}")
                    st.write(f"**Saída:** {row['data_partida']} | **Retorno:** {row['data_retorno']}")
                    
                    if row['status'] == "Aprovado" and row['link_voucher']:
                        st.link_button("📥 Baixar Voucher (Google Drive)", str(row['link_voucher']))
                    elif row['status'] == "Negado":
                        st.error("Esta solicitação foi negada pelo RH. Entre em contato para saber o motivo.")
                    else:
                        st.warning("Voucher ainda não disponível. Aguarde a compra pelo RH.")
        else:
            st.warning("Nenhuma viagem encontrada para este nome.")
