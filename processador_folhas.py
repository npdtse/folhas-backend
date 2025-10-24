import fitz
import pandas as pd
import re
import io
from pathlib import Path
import numpy as np
import traceback


# ====================================================================
# FUNÇÕES EXTRATORAS
# ====================================================================

def extrair_dados_modelo_ge(pdf_stream):
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        texto_completo = "".join([pagina.get_text("text", sort=True) for pagina in doc])
        doc.close()
        padrao_cabecalho = r'\d{5,}\s*-\s*.*?CPF:.*'
        inicios = [m.start() for m in re.finditer(padrao_cabecalho, texto_completo)]
        if not inicios: return []
        blocos = [texto_completo[inicios[i]:inicios[i+1]] if i + 1 < len(inicios) else texto_completo[inicios[i]:] for i in range(len(inicios))]
        lista_funcionarios = []
        for bloco in blocos:
            dados = {}
            if m := re.search(r'^(\d{5,})\s*-\s*(.*?)\s*CPF:', bloco, re.DOTALL):
                dados['Matricula'] = m.group(1).strip()
                dados['Nome'] = " ".join(m.group(2).strip().split())
            else: continue
            if m := re.search(r'Cargo:\s*(.*?)\s*Função:', bloco, re.DOTALL): dados['Cargo'] = m.group(1).strip()
            if m := re.search(r'Admissão:\s*([\d/]+)', bloco): dados['Admissão'] = m.group(1).strip()
            if m := re.search(r'Salário Base:\s*([\d.,]+)', bloco): dados['Salário Base'] = m.group(1).strip()
            if m := re.search(r'Total Bruto:\s*([\d.,]+)', bloco): dados['Total Bruto'] = m.group(1).strip()
            if m := re.search(r'Total de Descontos:\s*([\d.,]+)', bloco): dados['Total de Descontos'] = m.group(1).strip()
            if m := re.search(r'76\s*-\s*IRRF\s+[\d.,]+\s+([\d.,]+)', bloco): dados['IRRF'] = m.group(1).strip()
            if m := re.search(r'9010\s*-\s*INSS\s+[\d.,]+\s+([\d.,]+)', bloco): dados['INSS'] = m.group(1).strip()
            if m := re.search(r'Valor FGTS:\s*([\d.,]+)', bloco): dados['Valor FGTS'] = m.group(1).strip()
            if m := re.search(r'Total Salário Líquido:\s*([\d.,]+)', bloco): dados['Total Salário Líquido'] = m.group(1).strip()
            dados['Origem'] = 'Modelo GE'
            lista_funcionarios.append(dados)
        return lista_funcionarios
    except Exception: return []

def extrair_dados_modelo_senior(pdf_stream):
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        texto_completo = "".join([pagina.get_text("text", sort=True) for pagina in doc])
        doc.close()
        padrao_inicio_bloco = r'Tipo:\s*\d+\s*Colaborador:|Colaborador:\s*\d+\s*-\s*\d+\s*-'
        inicios = [m.start() for m in re.finditer(padrao_inicio_bloco, texto_completo)]
        if not inicios: return []
        blocos = [texto_completo[inicios[i]:inicios[i+1]] if i + 1 < len(inicios) else texto_completo[inicios[i]:] for i in range(len(inicios))]
        lista_funcionarios = []
        for bloco in blocos:
            dados = {}
            if m := re.search(r'Colaborador:(?:\s*\d+\s*-\s*)?\s*(\d+)\s*-\s*(.*?)\s*Admissão:', bloco, re.DOTALL):
                dados['Matricula'] = m.group(1).strip()
                dados['Nome'] = m.group(2).strip().replace('\n', ' ')
            else: continue
            if m := re.search(r'Cargo:\s*\d+\s*-\s*(.*?)(?=\s{2,}Salário Base:)', bloco):
                dados['Cargo'] = m.group(1).strip()
            if m := re.search(r'Admissão:\s*([\d/]+)', bloco): dados['Admissão'] = m.group(1).strip()
            if m := re.search(r'Salário Base:\s*([\d.,]+)', bloco): dados['Salário Base'] = m.group(1).strip()
            if m := re.search(r'Proventos:\s*([\d.,]+)', bloco): dados['Total Bruto'] = m.group(1).strip()
            if m := re.search(r'Descontos:\s*([\d.,]+)', bloco): dados['Total de Descontos'] = m.group(1).strip()
            if m := re.search(r'Líquido:\s*([\d.,]+)', bloco): dados['Total Salário Líquido'] = m.group(1).strip()
            if m := re.search(r'\d+\s+03\s+IRRF\s+[\d.,]+\s+([\d.,]+)', bloco): dados['IRRF'] = m.group(1).strip()
            if m := re.search(r'\d+\s+03\s+INSS\s+[\d.,]+\s+([\d.,]+)', bloco): dados['INSS'] = m.group(1).strip()
            if m := re.search(r'\d+\s+04\s+FGTS\s+[\d.,]+\s+([\d.,]+)', bloco): dados['Valor FGTS'] = m.group(1).strip()
            dados['Origem'] = 'Modelo Senior'
            lista_funcionarios.append(dados)
        return lista_funcionarios
    except Exception: return []

def extrair_dados_modelo_siga(pdf_stream):
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        texto_completo = "".join([pagina.get_text("text", sort=True) for pagina in doc])
        doc.close()
        # A divisão por '\nNome ' parece funcionar razoavelmente bem, mantida.
        blocos = re.split(r'\nNome\s', texto_completo)
        if len(blocos) <= 1: return []
        lista_funcionarios = []
        for bloco in blocos[1:]:
            dados = {}
            bloco_com_nome = "Nome " + bloco # Mantido
            # Extração de Nome e Matrícula (Mantida)
            if m := re.search(r'Nome\s(.*?)\s+Matricula\s+(\d+)', bloco_com_nome, re.DOTALL):
                dados['Nome'] = m.group(1).strip().replace('\n', ' ')
                dados['Matricula'] = m.group(2).strip()
            else: continue # Pula se não encontrar nome/matrícula

            # Demais extrações (Mantidas)
            if m := re.search(r'Descricao\s+(TECNICO SECRETARIADO)', bloco_com_nome): dados['Cargo'] = m.group(1).strip() # Ajustado para ser mais específico se necessário
            if m := re.search(r'Data Admis\.\s*([\d/]+)', bloco_com_nome): dados['Admissão'] = m.group(1).strip()
            if m := re.search(r'Sal\.:\s+([\d.,]+)', bloco_com_nome): dados['Salário'] = m.group(1).strip()

            # --- CORREÇÃO APLICADA ABAIXO ---
            # Regex Corrigido para IRRF (Código 410): Não exige mais o pipe '|' no final e busca especificamente após o código 410.
            if m := re.search(r'410\s+I\.R\.F\.\s+S/FOL\s+[\d.,]+\s+([\d.,]+)', bloco_com_nome):
                 dados['IRRF'] = m.group(1).strip()
            else: # Inicializa se não encontrar para evitar KeyErrors
                 dados['IRRF'] = '0,00' # Ou outra representação de zero/nulo

            # Regex Corrigido para INSS (Código 412): Não exige mais o pipe '|' no final e busca especificamente após o código 412.
            if m := re.search(r'412\s+INSS FOLHA\s+[\d.,]+\s+([\d.,]+)', bloco_com_nome):
                 dados['INSS'] = m.group(1).strip()
            else: # Inicializa se não encontrar
                 dados['INSS'] = '0,00'

            # --- FIM DA CORREÇÃO ---

            # Extração de FGTS (Mantida)
            if m := re.search(r'FGTS SAL\.DEPOS\s+([\d.,]+)', bloco_com_nome): dados['Valor FGTS'] = m.group(1).strip()

            # Extração de Totais (Mantida - ATENÇÃO: pode precisar de ajustes futuros se o formato variar)
            if m := re.search(r'Totais Funcionário.*?\n\s*[\d.,]+\s+([\d.,]+)\s+[\d.,]+\s+([\d.,]+)\s+.*?LIQUIDO:\s+([\d.,]+)', bloco_com_nome, re.DOTALL):
                dados['Total Bruto'] = m.group(1).strip()
                dados['Total de Descontos'] = m.group(2).strip()
                dados['Total Salário Líquido'] = m.group(3).strip()

            # Adiciona valores padrão se não encontrados, para manter a estrutura
            dados.setdefault('Cargo', None)
            dados.setdefault('Admissão', None)
            dados.setdefault('Salário', '0,00')
            # IRRF e INSS já são tratados acima com setdefault implícito pelo else
            dados.setdefault('Valor FGTS', '0,00')
            dados.setdefault('Total Bruto', '0,00')
            dados.setdefault('Total de Descontos', '0,00')
            dados.setdefault('Total Salário Líquido', '0,00')


            dados['Origem'] = 'Modelo SIGA' # Mantido
            lista_funcionarios.append(dados)

        return lista_funcionarios
    except Exception as e:
        # É uma boa prática logar o erro aqui para depuração
        print(f"Erro durante a extração: {e}")
        return []

def extrair_dados_modelo_tipo_2(pdf_stream, nome_modelo):
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        texto_completo = "".join([pagina.get_text("text", sort=True) for pagina in doc])
        doc.close()
        blocos = re.split(r'\n(?=\d{6}\s)', texto_completo)
        if len(blocos) <= 1: return []
        lista_funcionarios = []
        for bloco in blocos[1:]:
            dados = {}
            if m := re.search(r'^(\d{6})\s(.*?)(?=\s{2,}\d{1,2}\s|\s{2,}PROVENTOS)', bloco, re.DOTALL):
                dados['Matricula'] = m.group(1).strip()
                dados['Nome'] = " ".join(m.group(2).strip().split('\n'))
            else: continue
            if m := re.search(r'\n\s{3,}([A-ZÀ-Ú\s/()]+?)\s{2,}/\s*\d+', bloco): dados['Cargo'] = m.group(1).strip()
            if m := re.search(r'Admissão em\s+([\d/]+)', bloco): dados['Admissão'] = m.group(1).strip()
            if m := re.search(r'SALÁRIO BASE\s*:\s*([\d.,]+)', bloco): dados['Salário Base'] = m.group(1).strip()
            if m := re.search(r'INSS - MENSAL\s+[\d.,]+\s+([\d.,]+)', bloco): dados['INSS'] = m.group(1).strip()
            if m := re.search(r'IRRF - MENSAL\s+[\d.,]+\s+([\d.,]+)', bloco): dados['IRRF'] = m.group(1).strip()
            if m := re.search(r'BASE DO INSS\s*:\s*([\d.,]+)', bloco): dados['Total Bruto'] = m.group(1).strip()
            if m := re.search(r'FGTS A RECOLHER MÊS\s*:\s*([\d.,]+)', bloco): dados['Valor FGTS'] = m.group(1).strip()
            if m := re.search(r'TOTAL DE DESCONTOS\s*:\s*([\d.,]+)', bloco): dados['Total de Descontos'] = m.group(1).strip()
            if m := re.search(r'SALÁRIO LÍQUIDO\s*:\s*([\d.,]+)', bloco): dados['Total Salário Líquido'] = m.group(1).strip()
            dados['Origem'] = nome_modelo
            lista_funcionarios.append(dados)
        return lista_funcionarios
    except Exception: return []

def extrair_dados_modelo_fundacao(pdf_stream):
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        texto_completo = "".join([pagina.get_text("text", sort=True) for pagina in doc])
        doc.close()
        blocos = re.split(r'\nEmpr\.:', texto_completo)
        if len(blocos) <= 1: return []
        lista_funcionarios = []
        for bloco in blocos[1:]:
            dados = {}
            if m := re.search(r'^\s*(\d+)\s+(.*?)\s+Situação:', bloco, re.DOTALL):
                dados['Matricula'] = m.group(1).strip()
                dados['Nome'] = " ".join(m.group(2).strip().split('\n'))
            else: continue
            if m := re.search(r'Adm:\s*([\d/]+)', bloco): dados['Admissão'] = m.group(1).strip()
            if m := re.search(r'Cargo:\s*\d+\s*(.*?)\s+C\.B\.O:', bloco): dados['Cargo'] = m.group(1).strip()
            if m := re.search(r'Salário:\s*([\d.,]+)', bloco): dados['Salário Base'] = m.group(1).strip()
            if m := re.search(r'I\.N\.S\.S\.\s+[\d.,]+\s+([\d.,]+)\s+D', bloco): dados['INSS'] = m.group(1).strip()
            if m := re.search(r'IMPOSTO DE RENDA\s+[\d.,]+\s+([\d.,]+)\s+D', bloco): dados['IRRF'] = m.group(1).strip()
            if m := re.search(r'Proventos:\s*([\d.,]+)', bloco): dados['Total Bruto'] = m.group(1).strip()
            if m := re.search(r'Descontos:\s*([\d.,]+)', bloco): dados['Total de Descontos'] = m.group(1).strip()
            if m := re.search(r'Líquido:\s*([\d.,]+)', bloco): dados['Total Salário Líquido'] = m.group(1).strip()
            if m := re.search(r'Valor FGTS:\s*([\d.,]+)', bloco): dados['Valor FGTS'] = m.group(1).strip()
            dados['Origem'] = 'Modelo FUNDACAO'
            lista_funcionarios.append(dados)
        return lista_funcionarios
    except Exception: return []

def extrair_dados_modelo_amazon(pdf_stream):
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        texto_completo = "".join([pagina.get_text("text", sort=True) for pagina in doc])
        doc.close()
        
        blocos = re.split(r'\n(?=\d{6}\s)', texto_completo)
        if len(blocos) <= 1: return []
        
        lista_funcionarios = []
        for bloco in blocos[1:]:
            dados = {}
            if m := re.search(r'^(\d{6})\s(.*?)\s+[\d.,]+', bloco, re.DOTALL):
                dados['Matricula'] = m.group(1).strip()
                dados['Nome'] = " ".join(m.group(2).strip().split('\n'))
            else: continue
            if m := re.search(r'Função\s*:(.*?)\s+Livro:', bloco): dados['Cargo'] = m.group(1).strip()
            if m := re.search(r'Admissão\s*:\s*([\d/]+)', bloco): dados['Admissão'] = m.group(1).strip()
            if m := re.search(r'Salário Base\s+[\d:]+\s+([\d.,]+)', bloco): dados['Salário Base'] = m.group(1).strip()
            if m := re.search(r'INSS Folha\s+([\d.,]+)', bloco): dados['INSS'] = m.group(1).strip()
            if m := re.search(r'IRRF Folha\s+([\d.,]+)', bloco): dados['IRRF'] = m.group(1).strip()
            if m := re.search(r'FGTS\s+([\d.,]+)', bloco): dados['Valor FGTS'] = m.group(1).strip()
            if m := re.search(r'Resumo do Líquido\s+([\d.,]+)\s+([\d.,]+)\s+\*+([\d.,]+)', bloco):
                dados['Total Bruto'] = m.group(1).strip()
                dados['Total de Descontos'] = m.group(2).strip()
                dados['Total Salário Líquido'] = m.group(3).strip()
            dados['Origem'] = 'Modelo AMAZON'
            lista_funcionarios.append(dados)
        return lista_funcionarios
    except Exception: return []


def extrair_dados_modelo_chain(pdf_stream):
    lista_funcionarios = [] 
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        texto_completo = "".join([pagina.get_text("text", sort=True) for pagina in doc])
        doc.close()
        blocos = re.split(r'\nFunc:', texto_completo)
        if len(blocos) <= 1:
            print("Aviso: Nenhum bloco de funcionário encontrado após 'Func:'.")
            return []
        for bloco in blocos[1:]:
            dados = {} 
            match_matricula_nome = re.search(r'^\s*(\d+)\s+(.*?)\s+Adm', bloco, re.DOTALL)
            if match_matricula_nome:
                dados['Matricula'] = match_matricula_nome.group(1).strip()
                
                dados['Nome'] = " ".join(match_matricula_nome.group(2).strip().split('\n'))
            else:
                print(f"Aviso: Bloco ignorado - Não foi possível extrair Matrícula/Nome:\n---\n{bloco[:100]}...\n---")
                continue #
            matricula_atual = dados.get('Matricula') 
            if m := re.search(r'Adm\s+([\d/]+)', bloco):
                dados['Admissão'] = m.group(1).strip()
            if m := re.search(r'Cargo:\s*(.*?)\s+C\.H\.M:', bloco, re.DOTALL):
                 dados['Cargo'] = " ".join(m.group(1).strip().split('\n'))
            if m := re.search(r'Salário:\s*([\d.,]+)', bloco):
                dados['Salário Base'] = m.group(1).strip()
            texto_tabela = bloco 
            match_fim_tabela = re.search(r'\n\s*Proventos:\s*[\d.,]+', bloco)
            if match_fim_tabela:
                texto_tabela = bloco[:match_fim_tabela.start()]
                #if matricula_atual == '78': print(f"DEBUG Mat 78: Tabela isolada até 'Proventos:'.")
            else:
                match_fim_tabela_alt = re.search(r'\n\s*Base Impostos', bloco)
                if match_fim_tabela_alt:
                    texto_tabela = bloco[:match_fim_tabela_alt.start()]
                    #if matricula_atual == '78': print(f"DEBUG Mat 78: Tabela isolada até 'Base Impostos'.")
                else:
                    print(f"AVISO Matrícula {matricula_atual}: Não encontrou 'Proventos:' nem 'Base Impostos'. Buscando INSS/IRRF no bloco inteiro.")
            
            inss_total = 0.0
            linhas_inss = re.findall(r'^(.*\b195\d\b.*)$', texto_tabela, re.MULTILINE)
            """if matricula_atual == '78':
                print(f"\n--- DEBUG MAT 78 (Tabela Isolada): Linhas INSS encontradas ({len(linhas_inss)}) ---")
                for i, l in enumerate(linhas_inss): print(f"  Linha {i}: {l}")
                print(f"----------------------------------------------------------")"""
            for idx, linha in enumerate(linhas_inss):
                valores_na_linha = re.findall(r'(\b[\d.,]+\b)', linha)
                valor_monetario_encontrado = None
                if valores_na_linha:
                    for val in reversed(valores_na_linha):
                        if ',' in val or '.' in val:
                             match_percent = re.search(re.escape(val) + r'\s*%', linha)
                             if not match_percent and len(val) > 2 :
                                  valor_monetario_encontrado = val
                                  break
                if valor_monetario_encontrado:
                    val_str = valor_monetario_encontrado.strip()
                    #if matricula_atual == '78': print(f"DEBUG Mat 78 - INSS Linha {idx}: Escolhido '{val_str}' de {valores_na_linha}")
                    try:
                        cleaned_val_str = val_str.replace('.', '').replace(',', '.')
                        valor_float = 0.0
                        if cleaned_val_str.count('.') <= 1:
                            valor_float = float(cleaned_val_str)
                        else:
                            parts = cleaned_val_str.split('.')
                            if len(parts) > 1 and len(parts[-1]) == 2:
                                 reconstructed_val = "".join(parts[:-1]) + "." + parts[-1]
                                 valor_float = float(reconstructed_val)
                                 #if matricula_atual == '78': print(f"DEBUG Mat 78 - INSS MultiPonto: '{val_str}' -> '{reconstructed_val}'")
                            else: print(f"Aviso Matrícula {matricula_atual}: Formato INSS inesperado '{val_str}'")
                        inss_total += valor_float
                        #if matricula_atual == '78': print(f"DEBUG Mat 78 - INSS Somando (Tabela): {valor_float}, Total Parcial: {inss_total}")
                    except ValueError: print(f"Aviso Matrícula {matricula_atual}: Valor INSS inválido '{val_str}' -> '{cleaned_val_str}'")
                    except IndexError: print(f"Aviso Matrícula {matricula_atual}: Erro índice INSS '{cleaned_val_str}'")
                #elif matricula_atual == '78': print(f"DEBUG Mat 78 - INSS Linha {idx}: Nenhum valor válido em {valores_na_linha}")
            dados['INSS'] = f"{inss_total:.2f}".replace('.', ',') if inss_total > 0 else '0,0'

            irrf_total = 0.0
            linhas_irrf = re.findall(r'^(.*\b192\d\b.*)$', texto_tabela, re.MULTILINE)
            if matricula_atual == '78':
                #print(f"\n--- DEBUG MAT 78 (Tabela Isolada): Linhas IRRF encontradas ({len(linhas_irrf)}) ---")
                for i, l in enumerate(linhas_irrf): print(f"  Linha {i}: {l}")
                #print(f"-----------------------------------------------------------")
            for idx, linha in enumerate(linhas_irrf):
                valores_na_linha = re.findall(r'(\b[\d.,]+\b)', linha)
                valor_monetario_encontrado = None
                if valores_na_linha:
                    for val in reversed(valores_na_linha):
                        if ',' in val or '.' in val:
                             match_percent = re.search(re.escape(val) + r'\s*%', linha)
                             if not match_percent and len(val) > 2:
                                  valor_monetario_encontrado = val
                                  break
                if valor_monetario_encontrado:
                    val_str = valor_monetario_encontrado.strip()
                    #if matricula_atual == '78': print(f"DEBUG Mat 78 - IRRF Linha {idx}: Escolhido '{val_str}' de {valores_na_linha}")
                    try:
                        cleaned_val_str = val_str.replace('.', '').replace(',', '.')
                        valor_float = 0.0
                        if cleaned_val_str.count('.') <= 1:
                            valor_float = float(cleaned_val_str)
                        else:
                            parts = cleaned_val_str.split('.')
                            if len(parts) > 1 and len(parts[-1]) == 2:
                                 reconstructed_val = "".join(parts[:-1]) + "." + parts[-1]
                                 valor_float = float(reconstructed_val)
                                 #if matricula_atual == '78': print(f"DEBUG Mat 78 - IRRF MultiPonto: '{val_str}' -> '{reconstructed_val}'")
                            else: print(f"Aviso Matrícula {matricula_atual}: Formato IRRF inesperado '{val_str}'")
                        irrf_total += valor_float
                        #if matricula_atual == '78': print(f"DEBUG Mat 78 - IRRF Somando (Tabela): {valor_float}, Total Parcial: {irrf_total}")
                    except ValueError: print(f"Aviso Matrícula {matricula_atual}: Valor IRRF inválido '{val_str}' -> '{cleaned_val_str}'")
                    except IndexError: print(f"Aviso Matrícula {matricula_atual}: Erro índice IRRF '{cleaned_val_str}'")
                #elif matricula_atual == '78': print(f"DEBUG Mat 78 - IRRF Linha {idx}: Nenhum valor válido em {valores_na_linha}")
            dados['IRRF'] = f"{irrf_total:.2f}".replace('.', ',') if irrf_total > 0 else '0,0'

            # DEBUG Prints Finais
            # print(f"FINAL DEBUG - Mat: {matricula_atual}, INSS_F: {inss_total:.2f}, IRRF_F: {irrf_total:.2f}")
            # print(f"FINAL DEBUG - Mat: {matricula_atual}, INSS_S: {dados.get('INSS')}, IRRF_S: {dados.get('IRRF')}")

            if m := re.search(r'Proventos:\s*([\d.,]+)', bloco):
                dados['Total Bruto'] = m.group(1).strip()
            if m := re.search(r'Descontos:\s*([\d.,]+)', bloco):
                dados['Total de Descontos'] = m.group(1).strip()
            if m := re.search(r'Líquido:\s*([\d.,]+)', bloco):
                dados['Total Salário Líquido'] = m.group(1).strip()
            
            if m := re.search(r'FGTS GFIP\s+[\d.,]+\s+([\d.,]+)', bloco):
                dados['Valor FGTS'] = m.group(1).strip()
            dados['Origem'] = 'Modelo CHAIN' 
            lista_funcionarios.append(dados) 
        if lista_funcionarios: 
            df = pd.DataFrame(lista_funcionarios)
            df.drop_duplicates(subset=['Matricula'], keep='first', inplace=True)
            lista_funcionarios_sem_duplicatas = df.to_dict('records')
            # print(f"INFO: Extração concluída. {len(lista_funcionarios_sem_duplicatas)} funcionários únicos encontrados.")
            return lista_funcionarios_sem_duplicatas
        else:
            # print("INFO: Nenhum funcionário válido extraído após processar os blocos.")
            return [] 
    except Exception as e:
        # print(f"ERRO GERAL na extração: {e}")
        traceback.print_exc() 
        return [] 
    
# ====================================================================
# FUNÇÃO IDENTIFICADORA E ORQUESTRADORA
# ====================================================================

def identificar_modelo(pdf_stream):
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        primeira_pagina = doc[0].get_text("text", sort=True)
        doc.close()
        pdf_stream.seek(0)

        if "CHAIN TECNOLOGIA" in primeira_pagina: return "MODELO_CHAIN"
        if "AMAZON INFORMATICA" in primeira_pagina: return "MODELO_AMAZON"
        if "FUNDACAO PARA O DESENVOLVIMENTO" in primeira_pagina: return "MODELO_FUNDACAO"
        if "GE SERVICOS TERCEIRIZADOS LTDA" in primeira_pagina: return "MODELO_GE"
        if "SIGA/GPER106" in primeira_pagina: return "MODELO_SIGA"
        if any(keyword in primeira_pagina for keyword in ["G4F SOLUCOES CORPORATIVAS", "Digisystem Serviços Especializados", "WYNTECH SERVIÇOS", "ALMEIDA FRANÇA ENGENHARIA", "SEFIX GESTAO DE PROFISSIONAIS"]):
            return "MODELO_SENIOR" 
        if any(keyword in primeira_pagina for keyword in ["MULTSERV SEGURANCA", "DLF ENGENHARIA", "ESPLANADA SERVIÇOS", "GREEN HOUSE SERVICOS"]):
            return "MODELO_TIPO_2"
        
        return "DESCONHECIDO"
    except Exception:
        pdf_stream.seek(0)
        return "ERRO_LEITURA"

def processar_arquivos(lista_de_streams, nomes_dos_arquivos):
    dados_consolidados = []
    arquivos_com_sucesso = []
    arquivos_com_falha = []
    
    EXTRACTORS = {
        "MODELO_GE": extrair_dados_modelo_ge,
        "MODELO_SENIOR": extrair_dados_modelo_senior,
        "MODELO_SIGA": extrair_dados_modelo_siga,
        "MODELO_TIPO_2": lambda stream: extrair_dados_modelo_tipo_2(stream, identificar_modelo(stream)),
        "MODELO_FUNDACAO": extrair_dados_modelo_fundacao,
        "MODELO_AMAZON": extrair_dados_modelo_amazon,
        "MODELO_CHAIN": extrair_dados_modelo_chain,
    }

    for i, pdf_stream in enumerate(lista_de_streams):
        nome_arquivo = nomes_dos_arquivos[i]
        try:
            modelo = identificar_modelo(pdf_stream)
            extractor_func = EXTRACTORS.get(modelo)
            
            if extractor_func:
                dados_extraidos = extractor_func(pdf_stream)
                if dados_extraidos:
                    dados_consolidados.extend(dados_extraidos)
                    arquivos_com_sucesso.append(nome_arquivo)
                else:
                    arquivos_com_falha.append(f"{nome_arquivo} (Modelo: {modelo}, sem dados)")
            else:
                arquivos_com_falha.append(f"{nome_arquivo} (Modelo desconhecido)")
        except Exception as e:
            arquivos_com_falha.append(f"{nome_arquivo} (Erro: {e})")
            
    if not dados_consolidados:
        return None, None, arquivos_com_sucesso, arquivos_com_falha

    df = pd.DataFrame(dados_consolidados)

    if 'Matricula' in df.columns:
        df['Matricula'] = df['Matricula'].astype(str)
        
        # Define as regras de agregação
        agg_rules = {}
        for col in df.columns:
            if col != 'Matricula': # Não agrega a chave de agrupamento
                # Soma colunas numéricas, pega o primeiro valor para as outras (texto, datas)
                if pd.api.types.is_numeric_dtype(df[col]):
                    agg_rules[col] = 'sum'
                else:
                    agg_rules[col] = 'first'
        
        # Agrupa por matrícula e aplica as regras de fusão
        if agg_rules:
            df = df.groupby('Matricula', as_index=False).agg(agg_rules)
    
    colunas_numericas = ['Salário', 'Salário Base', 'Total Bruto', 'Total de Descontos', 'INSS', 'IRRF', 'Valor FGTS', 'Total Salário Líquido']
    for col in colunas_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
                errors='coerce'
            ).fillna(0)
    if 'Admissão' in df.columns:
        df['Admissão'] = pd.to_datetime(df['Admissão'], format='%d/%m/%Y', errors='coerce').dt.date
    if 'Total Bruto' in df.columns:
        df.rename(columns={'Total Bruto': 'Base de Cálculo (Bruto)'}, inplace=True)
    #if 'Base de Cálculo (Bruto)' in df.columns and 'INSS' in df.columns:
    #    df['INSS_Calculado'] = df['Base de Cálculo (Bruto)'].apply(calcular_inss)
    #    df['INSS_Diferenca'] = np.round(df['INSS_Calculado'] - df['INSS'], 2)
    #if 'Base de Cálculo (Bruto)' in df.columns and 'IRRF' in df.columns:
    #    df['IRRF_Calculado_Simplificado'] = df.apply(lambda row: calcular_irrf_simplificado(row['Base de Cálculo (Bruto)'], row['INSS']), axis=1)
    #    df['IRRF_Diferenca_Simplificada'] = np.round(df['IRRF_Calculado_Simplificado'] - df['IRRF'], 2)
    agg_funcs = {
        'Quantidade_Registros': ('Matricula', 'count'),
        'Soma_Base_Calculo': ('Base de Cálculo (Bruto)', 'sum'),
        'Soma_Total_Liquido': ('Total Salário Líquido', 'sum')
    }
    #if 'INSS_Diferenca' in df.columns:
    #    agg_funcs['Soma_Diferenca_INSS'] = ('INSS_Diferenca', 'sum')
    #if 'IRRF_Diferenca_Simplificada' in df.columns:
    #    agg_funcs['Soma_Diferenca_IRRF'] = ('IRRF_Diferenca_Simplificada', 'sum')
    resumo_df = df.groupby('Origem').agg(**agg_funcs).reset_index()
    for col in resumo_df.columns:
        if col.startswith('Soma_'):
            resumo_df[col] = resumo_df[col].map('{:,.2f}'.format)
    return df, resumo_df, arquivos_com_sucesso, arquivos_com_falha
"""
def calcular_inss(salario_bruto):
    tabela_inss = [
        {"faixa": (0, 1412.00), "aliquota": 0.075, "deducao": 0},
        {"faixa": (1412.01, 2666.68), "aliquota": 0.09, "deducao": 21.18},
        {"faixa": (2666.69, 4000.03), "aliquota": 0.12, "deducao": 101.18},
        {"faixa": (4000.04, 7786.02), "aliquota": 0.14, "deducao": 181.18},
    ]
    teto_inss = 908.85
    for item in reversed(tabela_inss):
        if salario_bruto >= item["faixa"][0]:
            inss_calculado = (salario_bruto * item["aliquota"]) - item["deducao"]
            return min(round(inss_calculado, 2), teto_inss)
    return 0.0

def calcular_irrf_simplificado(salario_bruto, inss_descontado):
    base_calculo = salario_bruto - inss_descontado
    tabela_irrf = [
        {"faixa": (0, 2112.00), "aliquota": 0, "deducao": 0},
        {"faixa": (2112.01, 2826.65), "aliquota": 0.075, "deducao": 158.40},
        {"faixa": (2826.66, 3751.05), "aliquota": 0.15, "deducao": 370.40},
        {"faixa": (3751.06, 4664.68), "aliquota": 0.225, "deducao": 651.73},
        {"faixa": (4664.69, float('inf')), "aliquota": 0.275, "deducao": 884.96},
    ]
    for item in tabela_irrf:
        if base_calculo <= item["faixa"][1]:
            irrf_calculado = (base_calculo * item["aliquota"]) - item["deducao"]
            return round(max(irrf_calculado, 0), 2)
    return 0.0"""
