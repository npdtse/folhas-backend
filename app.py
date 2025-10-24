from flask import Flask, request, send_file
from flask_cors import CORS 
import pandas as pd
import io

from processador_folhas import (
    identificar_modelo,
    extrair_dados_modelo_ge,
    extrair_dados_modelo_senior,
    extrair_dados_modelo_siga,
    extrair_dados_modelo_tipo_2,
    extrair_dados_modelo_fundacao,
    extrair_dados_modelo_amazon,
    extrair_dados_modelo_chain
)

app = Flask(__name__)
CORS(app)

EXTRACTORS = {
    "MODELO_GE": extrair_dados_modelo_ge,
    "MODELO_SENIOR": extrair_dados_modelo_senior,
    "MODELO_SIGA": extrair_dados_modelo_siga,
    "MODELO_TIPO_2": lambda stream: extrair_dados_modelo_tipo_2(stream, identificar_modelo(stream)),
    "MODELO_FUNDACAO": extrair_dados_modelo_fundacao,
    "MODELO_AMAZON": extrair_dados_modelo_amazon,
    "MODELO_CHAIN": extrair_dados_modelo_chain
}

# Verificar se a API está viva
@app.route('/health')
def health_check():
    """Um endpoint simples que o serviço de ping pode chamar."""
    return "OK", 200

@app.route('/upload', methods=['POST'])
def upload_files():
    uploaded_files = request.files.getlist('files')
    
    if not uploaded_files:
        return "Nenhum arquivo enviado.", 400

    dados_consolidados = []

    for file in uploaded_files:
        pdf_stream = io.BytesIO(file.read())
        modelo = identificar_modelo(pdf_stream)
        extractor_func = EXTRACTORS.get(modelo)
        
        if extractor_func:
            dados_extraidos = extractor_func(pdf_stream)
            if dados_extraidos:
                print(f"Sucesso! {len(dados_extraidos)} registros extraídos de '{file.filename}'.")
                dados_consolidados.extend(dados_extraidos)
            else:
                 print(f"Aviso: Nenhum registro extraído de '{file.filename}' (Modelo: {modelo}).")
        else:
            print(f"Aviso: Modelo '{modelo}' não reconhecido para o arquivo '{file.filename}'.")

    if not dados_consolidados:
        return "Não foi possível extrair dados de nenhum dos arquivos enviados.", 400

    df_final = pd.DataFrame(dados_consolidados)
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Consolidado')
    
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='Planilha_Pagamentos.xlsx'
    )

if __name__ == '__main__':
    app.run(debug=True)



