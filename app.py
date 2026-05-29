from flask import Flask, render_template
import sqlite3
import os

app = Flask(__name__)

# Função para conectar no novo banco de pesquisas
def conectar_banco():
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_banco_original = os.path.join(diretorio_atual, 'pesquisas.db')
    
    # 1. Verifica se o banco de dados realmente subiu para o GitHub/Vercel
    if not os.path.exists(caminho_banco_original):
        raise FileNotFoundError("ERRO FATAL: O arquivo pesquisas.db nao foi encontrado! Ele provavelmente nao foi enviado para o GitHub.")
        
    # 2. Conecta em modo read-only para ser compatível com o sistema de arquivos da Vercel.
    db_uri = f'file:{caminho_banco_original}?mode=ro'
    conn = sqlite3.connect(db_uri, uri=True)
    
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
