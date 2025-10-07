import fitz
import pandas as pd
import re
import io


# EXTRATOR 1: MODELO "GE SERVIÇOS" (VERSÃO CORRIGIDA PARA API)

def extrair_dados_modelo_ge(pdf_stream):
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        texto_completo = "".join([pagina.get_text("text", sort=True) for pagina in doc])
        doc.close()

        
        padrao_cabecalho = r'\d{5,}\s*-\s*.*?CPF:.*'
        inicios = [m.start() for m in re.finditer(padrao_cabecalho, texto_completo)]

        if not inicios:
            return []

        blocos = []
        for i in range(len(inicios)):
            start = inicios[i]
            end = inicios[i + 1] if i + 1 < len(inicios) else len(texto_completo)
            blocos.append(texto_completo[start:end])

        lista_funcionarios = []
        for bloco in blocos:
            dados = {}
            if m := re.search(r'^(\d{5,})\s*-\s*(.*?)\s*CPF:', bloco, re.DOTALL):
                dados['Matricula'] = m.group(1).strip()
                dados['Nome'] = " ".join(m.group(2).strip().split())
            else:
                continue
            
            if m := re.search(r'Cargo:\s*(.*?)\s*Função:', bloco, re.DOTALL): dados['Cargo'] = m.group(1).strip()
            if m := re.search(r'Admissão:\s*([\d/]+)', bloco): dados['Admissão'] = m.group(1).strip()
            if m := re.search(r'Salário Base:\s*([\d.,]+)', bloco): dados['Salário Base'] = m.group(1).strip()
            if m := re.search(r'Total Bruto:\s*([\d.,]+)', bloco): dados['Total Bruto'] = m.group(1).strip()
            if m := re.search(r'Total de Descontos:\s*([\d.,]+)', bloco): dados['Total de Descontos'] = m.group(1).strip()
            if m := re.search(r'9010\s*-\s*INSS.*?\s([\d.,]+)', bloco): dados['INSS'] = m.group(1).strip()
            if m := re.search(r'76\s*-\s*IRRF.*?\s([\d.,]+)', bloco): dados['IRRF'] = m.group(1).strip()
            if m := re.search(r'Valor FGTS:\s*([\d.,]+)', bloco): dados['Valor FGTS'] = m.group(1).strip()
            if m := re.search(r'Total Salário Líquido:\s*([\d.,]+)', bloco): dados['Total Salário Líquido'] = m.group(1).strip()
            
            dados['Origem'] = 'Modelo GE'
            lista_funcionarios.append(dados)
        return lista_funcionarios
    except Exception as e:
        print(f"[ERRO] Exceção no extrator GE: {e}")
        return []



# EXTRATOR 2: MODELO "G4F" / "SENIOR"

def extrair_dados_modelo_senior(pdf_stream):
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        texto_completo = "".join([pagina.get_text("text", sort=True) for pagina in doc])
        doc.close()
        padrao_inicio_bloco = r'Tipo:\s*\d+\s*Colaborador:'
        inicios = [m.start() for m in re.finditer(padrao_inicio_bloco, texto_completo)]
        if not inicios: return []
        blocos = []
        for i in range(len(inicios)):
            inicio = inicios[i]
            fim = inicios[i + 1] if i + 1 < len(inicios) else len(texto_completo)
            blocos.append(texto_completo[inicio:fim])
        lista_funcionarios = []
        for bloco in blocos:
            dados = {}
            if m := re.search(r'Colaborador:\s*(\d+)\s*-\s*(.*?)\s*Admissão:', bloco, re.DOTALL):
                dados['Matricula'] = m.group(1).strip()
                dados['Nome'] = m.group(2).strip().replace('\n', ' ')
            else: continue
            if m := re.search(r'Cargo:\s*\d+\s*-\s*(.*?)\n', bloco): dados['Cargo'] = m.group(1).strip()
            if m := re.search(r'Admissão:\s*([\d/]+)', bloco): dados['Admissão'] = m.group(1).strip()
            if m := re.search(r'Salário Base:\s*([\d.,]+)', bloco): dados['Salário Base'] = m.group(1).strip()
            if m := re.search(r'Proventos:\s*([\d.,]+)', bloco): dados['Total Bruto'] = m.group(1).strip()
            if m := re.search(r'Descontos:\s*([\d.,]+)', bloco): dados['Total de Descontos'] = m.group(1).strip()
            if m := re.search(r'Líquido:\s*([\d.,]+)', bloco): dados['Total Salário Líquido'] = m.group(1).strip()
            if m := re.search(r'\n\d+\s+03\s+INSS\s+.*?([\d.,]+)', bloco): dados['INSS'] = m.group(1).strip()
            if m := re.search(r'\n\d+\s+03\s+IRRF\s+.*?([\d.,]+)', bloco): dados['IRRF'] = m.group(1).strip()
            if m := re.search(r'\n\d+\s+04\s+FGTS\s+.*?([\d.,]+)', bloco): dados['Valor FGTS'] = m.group(1).strip()
            dados['Origem'] = 'Modelo Senior'
            lista_funcionarios.append(dados)
        return lista_funcionarios
    except Exception: return []


# EXTRATOR 3: MODELO "SIGA"

def extrair_dados_modelo_siga(pdf_stream):
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        texto_completo = "".join([pagina.get_text("text", sort=True) for pagina in doc])
        doc.close()
        blocos = re.split(r'\nNome\s', texto_completo)
        if len(blocos) <= 1: return []
        lista_funcionarios = []
        for bloco in blocos[1:]:
            dados = {}
            bloco_com_nome = "Nome " + bloco
            if m := re.search(r'Nome\s(.*?)\s+Matricula\s+(\d+)', bloco_com_nome, re.DOTALL):
                dados['Nome'] = m.group(1).strip().replace('\n', ' ')
                dados['Matricula'] = m.group(2).strip()
            else: continue
            if m := re.search(r'Descricao\s+([A-Z\s]+)\n', bloco_com_nome): dados['Cargo'] = m.group(1).strip()
            if m := re.search(r'Data Admis\.\s*([\d/]+)', bloco_com_nome): dados['Admissão'] = m.group(1).strip()
            if m := re.search(r'I\.R\.F\. S/FOL\s+.*?([\d.,]+)\s*\|', bloco_com_nome): dados['IRRF'] = m.group(1).strip()
            if m := re.search(r'INSS FOLHA\s+.*?([\d.,]+)\s*\|', bloco_com_nome): dados['INSS'] = m.group(1).strip()
            if m := re.search(r'FGTS SAL\.DEPOS\s+([\d.,]+)', bloco_com_nome): dados['Valor FGTS'] = m.group(1).strip()
            if m := re.search(r'Totais Funcionário.*? ([\d.,]+)\s+.*? ([\d.,]+)\s+.*?LIQUIDO:\s+([\d.,]+)', bloco_com_nome, re.DOTALL):
                dados['Total Bruto'] = m.group(1).strip()
                dados['Total de Descontos'] = m.group(2).strip()
                dados['Total Salário Líquido'] = m.group(3).strip()
            dados['Origem'] = 'Modelo SIGA'
            lista_funcionarios.append(dados)
        return lista_funcionarios
    except Exception: return []


# EXTRATOR 4: MODELO "MULTSERV"

def extrair_dados_modelo_multserv(pdf_stream):
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        texto_completo = "".join([pagina.get_text("text", sort=True) for pagina in doc])
        doc.close()

        blocos = re.split(r'\n_+\n', texto_completo)
        if len(blocos) <= 1: return []

        lista_funcionarios = []
        for bloco in blocos:
            if "ADMISSÃO EM" not in bloco:
                continue

            dados = {}
            if m := re.search(r'^\s*(\d{6})\s(.*?)(?=\s{2,}\d{2}\s|\s{2,}PROVENTOS)', bloco, re.DOTALL):
                dados['Matricula'] = m.group(1).strip()
                dados['Nome'] = " ".join(m.group(2).strip().split('\n'))
            else:
                continue

            if m := re.search(r'\n\s{3,}([A-ZÀ-Ú\s/]+?)\s{2,}/\d+', bloco): dados['Cargo'] = m.group(1).strip()
            if m := re.search(r'ADMISSÃO EM\s+([\d/]+)', bloco): dados['Admissão'] = m.group(1).strip()
            if m := re.search(r'SALÁRIO BASE\s*:\s*([\d.,]+)', bloco): dados['Salário Base'] = m.group(1).strip()
            if m := re.search(r'1074 INSS - MENSAL\s+.*?([\d.,]+)', bloco): dados['INSS'] = m.group(1).strip()
            if m := re.search(r'FGTS A RECOLHER MÊS\s*:\s*([\d.,]+)', bloco): dados['Valor FGTS'] = m.group(1).strip()
            if m := re.search(r'TOTAL DE PROVENTOS\s*:\s*([\d.,]+)', bloco): dados['Total Bruto'] = m.group(1).strip()
            if m := re.search(r'TOTAL DE DESCONTOS\s*:\s*([\d.,]+)', bloco): dados['Total de Descontos'] = m.group(1).strip()
            if m := re.search(r'SALÁRIO LÍQUIDO\s*:\s*([\d.,]+)', bloco): dados['Total Salário Líquido'] = m.group(1).strip()
            
            dados['Origem'] = 'Modelo MULTSERV'
            lista_funcionarios.append(dados)
            
        return lista_funcionarios
    except Exception as e:
        print(f"  [ERRO] Ocorreu uma exceção no extrator MULTSERV: {e}")
        return []


# CLASSIFICADOR

def identificar_modelo(pdf_stream):
    try:
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        primeira_pagina = doc[0].get_text("text", sort=True)
        doc.close()
        pdf_stream.seek(0)

        if "GE SERVICOS TERCEIRIZADOS LTDA" in primeira_pagina: return "MODELO_GE"
        if "SIGA/GPER106" in primeira_pagina: return "MODELO_SIGA"
        if "MULTSERV SEGURANCA" in primeira_pagina: return "MODELO_MULTSERV"
        if "G4F SOLUCOES CORPORATIVAS" in primeira_pagina: return "MODELO_SENIOR"
        if "Digisystem Serviços Especializados" in primeira_pagina: return "MODELO_SENIOR"
        return "DESCONHECIDO"
    except Exception:
        pdf_stream.seek(0)
        return "ERRO_LEITURA"