from flask import Flask, request, send_file
from flask_cors import CORS 
import pandas as pd
import io



from processador_folhas import processar_arquivos

app = Flask(__name__)
CORS(app)




@app.route('/health')
def health_check():
    """Um endpoint simples que o serviço de ping pode chamar."""
    return "OK", 200

@app.route('/upload', methods=['POST'])
def upload_files():
    uploaded_files = request.files.getlist('files')
    
    if not uploaded_files:
        return "Nenhum arquivo enviado.", 400

    


    lista_de_streams = [io.BytesIO(file.read()) for file in uploaded_files]
    nomes_dos_arquivos = [file.filename for file in uploaded_files]

    
    dados_df, resumo_df, sucesso_log, falha_log = processar_arquivos(lista_de_streams, nomes_dos_arquivos)

    
    print("--- Relatório de Processamento ---")
    if sucesso_log:
        print("Arquivos com Sucesso:", sucesso_log)
    if falha_log:
        print("Arquivos com Falha:", falha_log)
    print("---------------------------------")

   
    if dados_df is None:
        return "Não foi possível extrair dados de nenhum dos arquivos enviados.", 400

   
    output = io.BytesIO()
    
   
    with pd.ExcelWriter(output, engine='xlsxwriter', datetime_format='dd-mm-yyyy', date_format='dd-mm-yyyy') as writer:
        dados_df.to_excel(writer, index=False, sheet_name='Dados Consolidados')
        # Verifica se o resumo_df foi criado antes de salvar
        #if resumo_df is not None and not resumo_df.empty:
        #    resumo_df.to_excel(writer, index=False, sheet_name='Resumo')
    
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        # NOVO: Nome do arquivo alterado para refletir a nova saída
        download_name='Folha_Extraida.xlsx'
    )

if __name__ == '__main__':
    app.run(debug=True)






