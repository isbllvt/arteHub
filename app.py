import os
import time
from flask import Flask, request, render_template, url_for, redirect
import pyembroidery
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuração de Diretório
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MongoDB
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")

client = MongoClient(MONGO_URI)

db = client[MONGO_DB]
colecao = db[MONGO_COLLECTION]

@app.route('/')
def biblioteca():
    # Busca todas as matrizes no MongoDB
    matrizes_db = list(colecao.find({}))
    matrizes = []
    
    # Busca todas as categorias únicas que existem no banco para criar os filtros
    categorias_unicas = sorted(list(colecao.distinct("categoria")))
    categorias = [c for c in categorias_unicas if c.strip()] # Remove vazias
    
    for m in matrizes_db:
        arquivo = m.get("arquivo", "")
        arquivo_png = arquivo.rsplit('.', 1)[0] + '.png'
        
        cores_formatadas = []
        for i, cor_hex in enumerate(m.get("cores", [])):
            cores_formatadas.append({
                "hex": cor_hex,
                "nome": f"Linha {i+1}",
                "marca": "Matriz",
                "cod": str(i+1)
            })

        matrizes.append({
            "id": str(m["_id"]),
            "nome": m.get("nome", "Sem Nome"),
            "categoria": m.get("categoria", "Outros"),
            "tema": m.get("tema", "Geral"),
            "pontos": m.get("pontos", 0),
            "dimensoes": f"{m.get('tamanho', {}).get('largura_cm', 0)} × {m.get('tamanho', {}).get('altura_cm', 0)} cm",
            "vezesUsada": m.get("vezesUsada", 0),
            "cores": cores_formatadas,
            "arquivo": arquivo,
            "png_url": url_for('static', filename=f'uploads/{arquivo_png}')
        })

    return render_template('biblioteca.html', matrizes=matrizes, categorias=categorias)

@app.route('/nova', methods=['GET', 'POST'])
def upload_matriz():
    # Busca as categorias para o autocompletar do formulário
    categorias_unicas = sorted(list(colecao.distinct("categoria")))
    categorias = [c for c in categorias_unicas if c.strip()]

    if request.method == 'POST':
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            nome = request.form.get('nome_matriz')
            # Recebe a categoria (pode ser uma existente da lista ou uma digitada nova)
            categoria = request.form.get('categoria', 'Outros').strip()
            tema = request.form.get('tema', 'Geral')

            if file.filename.lower().endswith('.pes'):
                pes_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(pes_path)
                pattern = pyembroidery.read_pes(pes_path)
                
                stitch_count = sum(1 for s in pattern.stitches if (s[2] & 0xFF) == pyembroidery.STITCH)
                bounds = pattern.bounds()
                w = round((bounds[2] - bounds[0]) / 100.0, 2) if bounds else 0
                h = round((bounds[3] - bounds[1]) / 100.0, 2) if bounds else 0

                colors = []
                for thread in pattern.threadlist:
                    colors.append(f"#{thread.color & 0xFFFFFF:06x}")
                
                png_name = file.filename.rsplit('.', 1)[0] + '.png'
                pyembroidery.write_png(pattern, os.path.join(app.config['UPLOAD_FOLDER'], png_name))
                
                doc = {
                    "nome": nome, 
                    "categoria": categoria, 
                    "tema": tema,
                    "arquivo": file.filename,
                    "pontos": stitch_count, 
                    "tamanho": {"largura_cm": w, "altura_cm": h},
                    "cores": colors, 
                    "vezesUsada": 0
                }
                colecao.update_one({"arquivo": file.filename}, {"$set": doc}, upsert=True)
                return redirect(url_for('biblioteca'))

    return render_template('index.html', categorias=categorias)

@app.route('/update_colors/<id>', methods=['POST'])
def update_colors(id):
    matriz = colecao.find_one({"_id": ObjectId(id)})
    if matriz:
        pes_path = os.path.join(app.config['UPLOAD_FOLDER'], matriz['arquivo'])
        
        if os.path.exists(pes_path):
            pattern = pyembroidery.read_pes(pes_path)
            novas_cores = []
            
            for i in range(len(pattern.threadlist)):
                nova_cor_hex = request.form.get(f'color_{i}')
                if nova_cor_hex:
                    pattern.threadlist[i].color = int(nova_cor_hex.lstrip('#'), 16)
                    novas_cores.append(nova_cor_hex)
                else:
                    novas_cores.append(f"#{pattern.threadlist[i].color & 0xFFFFFF:06x}")
            
            png_path = os.path.join(app.config['UPLOAD_FOLDER'], matriz['arquivo'].rsplit('.', 1)[0] + '.png')
            pyembroidery.write_png(pattern, png_path)
            
            colecao.update_one({"_id": ObjectId(id)}, {"$set": {"cores": novas_cores}})
            
    return redirect(url_for('biblioteca'))

@app.route('/delete/<id>', methods=['POST'])
def deletar_matriz(id):
    matriz = colecao.find_one({"_id": ObjectId(id)})
    if matriz:
        pes = os.path.join(app.config['UPLOAD_FOLDER'], matriz['arquivo'])
        png = pes.rsplit('.', 1)[0] + '.png'
        if os.path.exists(pes): os.remove(pes)
        if os.path.exists(png): os.remove(png)
        colecao.delete_one({"_id": ObjectId(id)})
# ---------------------------------------------------
# ENCOMENDAS
# ---------------------------------------------------
colecao_encomendas = db["encomendas"]

@app.route('/encomenda')
def listar_encomendas():
    encomendas_db = list(colecao_encomendas.find({}).sort("data_pedido", -1))
    encomendas = []
    
    # Preparando os dados para serem usados pelo JavaScript no frontend
    for enc in encomendas_db:
        encomendas.append({
            "_id": str(enc["_id"]),
            "cliente_nome": enc.get("cliente_nome", ""),
            "produto_tipo": enc.get("produto_tipo", ""),
            "quantidade": enc.get("quantidade", 1),
            "status": enc.get("status", "Pendente"),
            "data_pedido": enc.get("data_pedido", ""),
            "data_entrega": enc.get("data_entrega", ""),
            "cores_sugeridas": enc.get("cores_sugeridas", []),
            "matriz_id": enc.get("matriz_id", "")
        })
        
    return render_template('encomenda.html', encomenda=encomendas)

@app.route('/encomenda/nova', methods=['GET', 'POST'])
def nova_encomenda():
    if request.method == 'POST':
        cores = request.form.getlist('cores_sugeridas')
        doc = {
            "cliente_nome": request.form.get("cliente_nome"),
            "produto_tipo": request.form.get("produto_tipo"),
            "quantidade": int(request.form.get("quantidade", 1)),
            "status": request.form.get("status", "Pendente"),
            "data_pedido": request.form.get("data_pedido"),
            "data_entrega": request.form.get("data_entrega"),
            "cores_sugeridas": cores,
            "matriz_id": request.form.get("matriz_id", "") # Salva a referência da matriz
        }
        colecao_encomendas.insert_one(doc)
        return redirect(url_for('listar_encomendas'))
    
    # Lógica para pegar as cores enviadas pelo painel da biblioteca (GET)
    matriz_id = request.args.get('matriz_id')
    cores_sugeridas = []
    
    if matriz_id:
        i = 0
        # Lê os parâmetros color_0, color_1 da URL gerada pelo painel
        while f'color_{i}' in request.args:
            cores_sugeridas.append(request.args.get(f'color_{i}'))
            i += 1
            
    encomenda_mock = None
    if matriz_id or cores_sugeridas:
        encomenda_mock = {"cores_sugeridas": cores_sugeridas, "matriz_id": matriz_id}
        
    return render_template('nova_encomenda.html', encomenda=encomenda_mock)

@app.route('/encomenda/editar/<id>', methods=['GET', 'POST'])
def editar_encomenda(id):
    encomenda = colecao_encomendas.find_one({"_id": ObjectId(id)})
    
    if request.method == 'POST':
        cores = request.form.getlist('cores_sugeridas')
        dados_atualizados = {
            "cliente_nome": request.form.get("cliente_nome"),
            "produto_tipo": request.form.get("produto_tipo"),
            "quantidade": int(request.form.get("quantidade", 1)),
            "status": request.form.get("status"),
            "data_pedido": request.form.get("data_pedido"),
            "data_entrega": request.form.get("data_entrega"),
            "cores_sugeridas": cores,
            "matriz_id": request.form.get("matriz_id", encomenda.get("matriz_id", ""))
        }
        colecao_encomendas.update_one({"_id": ObjectId(id)}, {"$set": dados_atualizados})
        return redirect(url_for('listar_encomendas'))
    
    return render_template('nova_encomenda.html', encomenda=encomenda)

@app.route('/encomenda/deletar/<id>', methods=['POST'])
def deletar_encomenda(id):
    colecao_encomendas.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('listar_encomendas'))

if __name__ == '__main__':
    app.run(debug=True)