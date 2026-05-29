from flask import Flask, render_template
import sqlite3
import os
import shutil
import tempfile

app = Flask(__name__)

# Função para conectar no novo banco de pesquisas
def conectar_banco():
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_banco_original = os.path.join(diretorio_atual, 'pesquisas.db')
    caminho_banco_temp = os.path.join(tempfile.gettempdir(), 'pesquisas.db')
    
    # 1. Verifica se o banco de dados realmente subiu para o GitHub/Vercel
    if not os.path.exists(caminho_banco_original):
        raise FileNotFoundError("ERRO FATAL: O arquivo pesquisas.db nao foi encontrado! Ele provavelmente nao foi enviado para o GitHub.")
        
    # 2. Copia para um diretório temporário que permite escrita (cross-platform: Vercel / Local)
    if not os.path.exists(caminho_banco_temp) or os.path.getmtime(caminho_banco_original) > os.path.getmtime(caminho_banco_temp):
        shutil.copy2(caminho_banco_original, caminho_banco_temp)
        
    # 3. Conecta no banco localizado na pasta temporária
    conn = sqlite3.connect(caminho_banco_temp)
    
    conn.row_factory = sqlite3.Row 
    return conn

# Rota principal (Lista de pesquisas)
@app.route('/')
def index():
    conn = conectar_banco()
    cursor = conn.cursor()
    # Busca os 20 artigos gerados mais recentes
    cursor.execute('SELECT id, titulo, resumo, autores, imagem FROM pesquisas ORDER BY id DESC LIMIT 20')
    pesquisas = cursor.fetchall()
    conn.close()
    return render_template('index.html', pesquisas=pesquisas)

# Nova Rota Dinâmica (Página hospedada individual do artigo)
@app.route('/artigo/<int:id>')
def artigo(id):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pesquisas WHERE id = ?', (id,))
    pesquisa = cursor.fetchone()
    conn.close()
    
    if pesquisa is None:
        return "Artigo não encontrado", 404
        
    return render_template('artigo.html', pesquisa=pesquisa)

if __name__ == '__main__':
    # Inicia o servidor em modo de desenvolvimento
    app.run(debug=True)
