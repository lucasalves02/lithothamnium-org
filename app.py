from flask import Flask, render_template
import sqlite3
import os
from pathlib import Path

app = Flask(__name__)

# Função para conectar no novo banco de pesquisas
def conectar_banco():
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_banco = os.path.join(diretorio_atual, 'pesquisas.db')
    
    # Converte o caminho para URI e força o modo Somente Leitura (mode=ro)
    # Isso previne que o SQLite tente criar arquivos temporários no sistema bloqueado da Vercel
    caminho_uri = Path(caminho_banco).as_uri()
    conn = sqlite3.connect(f"{caminho_uri}?mode=ro", uri=True)
    
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
