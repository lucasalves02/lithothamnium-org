import sqlite3
from datetime import datetime
import os
import shutil
import PyPDF2
from deep_translator import GoogleTranslator
import re
import fitz  # Importa a biblioteca PyMuPDF
import unicodedata

# 1. Configurar o Banco de Dados (SQLite)
def configurar_banco_de_dados():
    # Garante que o script sempre encontre o banco de dados na pasta correta
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_banco = os.path.join(diretorio_atual, 'pesquisas.db')
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pesquisas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            autores TEXT,
            resumo TEXT,
            conteudo TEXT,
            link_original TEXT UNIQUE,
            data_coleta TEXT,
            imagem TEXT
        )
    ''')
    conn.commit()
    return conn

# 2. Função para ler pasta de PDFs e gerar artigos
def processar_pdfs_locais(conn):
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    
    # Pastas de entrada e saída
    pasta_entrada = os.path.join(diretorio_atual, 'pdfs_entrada')
    pasta_estatica_pdfs = os.path.join(diretorio_atual, 'static', 'pdfs')
    pasta_estatica_capas = os.path.join(diretorio_atual, 'static', 'capas')
    
    # Cria as pastas caso não existam
    os.makedirs(pasta_entrada, exist_ok=True)
    os.makedirs(pasta_estatica_pdfs, exist_ok=True)
    os.makedirs(pasta_estatica_capas, exist_ok=True)
    
    arquivos_pdf = [f for f in os.listdir(pasta_entrada) if f.lower().endswith('.pdf')]
    
    if not arquivos_pdf:
        print(f"Nenhum arquivo PDF encontrado na pasta: {pasta_entrada}")
        print("Adicione seus artigos lá e rode o script novamente.")
        return

    print(f"Processando {len(arquivos_pdf)} PDFs encontrados na pasta de entrada...")
    
    cursor = conn.cursor()
    pesquisas_salvas = 0

    for arquivo in arquivos_pdf:
        # Gera um nome de arquivo seguro para a web (Vercel/Linux)
        nome_seguro = ''.join(c for c in unicodedata.normalize('NFD', arquivo) if unicodedata.category(c) != 'Mn')
        nome_seguro = re.sub(r'[^a-zA-Z0-9.\-]', '_', nome_seguro)

        caminho_pdf_entrada = os.path.join(pasta_entrada, arquivo)
        caminho_pdf_destino = os.path.join(pasta_estatica_pdfs, nome_seguro)
        
        texto_extraido = ""
        
        # Tenta ler o conteúdo da primeira página do PDF
        try:
            with open(caminho_pdf_entrada, 'rb') as f:
                leitor = PyPDF2.PdfReader(f)
                # Lê as primeiras 2 páginas para ter mais chance de englobar o resumo completo
                for i in range(min(2, len(leitor.pages))):
                    texto_extraido += leitor.pages[i].extract_text() + " "
        except Exception as e:
            print(f"  -> Erro ao ler PDF {arquivo}: {e}")
            continue

        if not texto_extraido or not texto_extraido.strip():
            print(f"  -> Não foi possível extrair texto do PDF '{arquivo}'. Pulando.")
            continue

        # Limpa quebras de linha estranhas para facilitar a busca
        texto_extraido = texto_extraido.replace('\n', ' ').strip()

        # Busca inteligente pelo Resumo/Abstract usando Expressão Regular
        match = re.search(r'(?i)\b(abstract|resumo)\b[\s\.\:\-]+(.*?)(?=\b(introduction|introdução|keywords|palavras-chave)\b|$)', texto_extraido)
        
        if match and len(match.group(2)) > 50:
            texto_sintese = match.group(2).strip()[:1500] # Limita a 1500 caracteres para a síntese
        else:
            texto_sintese = texto_extraido[:1000] # Fallback se não encontrar as palavras-chave

        # Etapa de Tradução
        try:
            print(f"  -> Traduzindo síntese de '{arquivo}'...")
            texto_traduzido = GoogleTranslator(source='auto', target='pt').translate(texto_sintese)
        except Exception as e:
            print(f"  -> Erro na tradução do arquivo {arquivo}: {e}. Usando texto original.")
            texto_traduzido = texto_sintese

        # Usaremos o texto traduzido daqui em diante
        texto_processado = texto_traduzido.strip()
        
        # Heurísticas de Extração
        # 1. Título: Usa o nome do arquivo limpo (ex: "Efeito_das_Algas.pdf" vira "Efeito Das Algas")
        titulo = arquivo[:-4].replace('_', ' ').replace('-', ' ').title()
        
        # 2. Autores: Difícil extrair perfeitamente do layout de PDFs variados, usaremos fallback
        autores = "Autoria listada no documento original"
        
        # 3. Resumo: Pega os primeiros 600 caracteres úteis
        resumo_bruto = texto_processado[:600] + "..." if len(texto_processado) > 10 else "Resumo não disponível para extração automática."
        
        # O link agora é a rota local servida pelo Flask
        link_original = f"/static/pdfs/{nome_seguro}"
        data_coleta = datetime.now().strftime("%d/%m/%Y")

        # Geração da Capa do Artigo em Imagem (Thumbnail da 1ª Página)
        nome_base_seguro = nome_seguro[:-4]
        caminho_capa_destino = os.path.join(pasta_estatica_capas, f"{nome_base_seguro}.png")
        link_imagem = f"/static/capas/{nome_base_seguro}.png"
        
        try:
            with fitz.open(caminho_pdf_entrada) as pdf_doc:
                pagina_capa = pdf_doc.load_page(0)
                pix = pagina_capa.get_pixmap(matrix=fitz.Matrix(2, 2)) # Matriz 2x2 para melhor resolução visual
                pix.save(caminho_capa_destino)
        except Exception as e:
            print(f"  -> Erro ao gerar capa para {arquivo}: {e}")
            link_imagem = "https://placehold.co/600x800/e2e8f0/475569?text=Sem+Capa"

        # Gera o corpo do artigo que ficará hospedado no seu site
        conteudo_artigo = f"""
        <h3 class="text-2xl font-bold text-green-800 mb-4">Principais Contribuições Científicas (Tradução Automática)</h3>
        <p class="text-gray-700 mb-5">A partir da análise do documento submetido ao nosso acervo, destacam-se as seguintes informações extraídas e traduzidas da obra:</p>
        
        <ul class="list-none space-y-4 mb-8">
            <li class="flex items-start">
                <svg class="w-6 h-6 text-green-500 mr-3 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                <span class="text-gray-800"><strong>Identificação:</strong> Documento indexado sob o título original <em>{titulo}</em>.</span>
            </li>
            <li class="flex items-start">
                <svg class="w-6 h-6 text-green-500 mr-3 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                <span class="text-gray-800"><strong>Síntese Inicial (Tradução):</strong> {resumo_bruto[:250]}...</span>
            </li>
            <li class="flex items-start">
                <svg class="w-6 h-6 text-green-500 mr-3 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                <span class="text-gray-800"><strong>Disponibilidade:</strong> Este artigo está hospedado e disponível em sua totalidade no repositório local do LithothamniumBR.</span>
            </li>
        </ul>

        <div class="bg-yellow-50 border-l-4 border-yellow-500 p-5 rounded-r-lg shadow-sm">
            <p class="text-gray-800 italic m-0"><strong>Aviso:</strong> A tradução foi gerada automaticamente e pode conter imprecisões. Para validação detalhada das metodologias aplicadas, ensaios de campo e visualização de gráficos e tabelas originais, acesse o PDF na íntegra através do botão abaixo.</p>
        </div>
        """

        try:
            cursor.execute('''
                INSERT INTO pesquisas (titulo, autores, resumo, conteudo, link_original, data_coleta, imagem)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (titulo, autores, resumo_bruto[:200] + "...", conteudo_artigo, link_original, data_coleta, link_imagem))
            
            # Move o PDF da pasta de "entrada" para a pasta de hospedagem do site
            shutil.move(caminho_pdf_entrada, caminho_pdf_destino)
            
            pesquisas_salvas += 1
            print(f"  -> Artigo importado e movido: {titulo}")
        except sqlite3.IntegrityError:
            print(f"  -> O arquivo '{arquivo}' já foi indexado. Pulando...")
            continue

    conn.commit()
    print(f"\n{pesquisas_salvas} novos artigos baseados em PDFs foram indexados!")

if __name__ == "__main__":
    banco_conn = configurar_banco_de_dados()
    processar_pdfs_locais(banco_conn)
    banco_conn.close()
