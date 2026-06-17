import os
import time
from flask import Flask, request, render_template, url_for, redirect, send_file, jsonify  # type: ignore
import pyembroidery  # type: ignore
from pymongo import MongoClient  # type: ignore
from bson import ObjectId  # type: ignore
import io

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except ImportError:
    pass

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
                    "cores": colors
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
    return redirect(url_for('biblioteca'))
# ---------------------------------------------------
# ENCOMENDAS
# ---------------------------------------------------
colecao_encomendas = db["encomendas"]

@app.route('/encomenda')
def listar_encomendas():
    encomendas_db = list(colecao_encomendas.find({}).sort("data_pedido", -1))
    matrizes_db = list(colecao.find({}, {"_id": 1, "nome": 1}))
    encomendas = []
    
    for enc in encomendas_db:
        # Busca o nome da matriz vinculada
        matriz_nome = "Nenhuma"
        if enc.get("matriz_id"):
            try:
                matriz = colecao.find_one({"_id": ObjectId(enc["matriz_id"])})
                if matriz: matriz_nome = matriz.get("nome", "Matriz Excluída")
            except:
                pass

        encomendas.append({
            "_id": str(enc["_id"]),
            "cliente_nome": enc.get("cliente_nome", ""),
            "produto_tipo": enc.get("produto_tipo", ""),
            "quantidade": enc.get("quantidade", 1),
            "status": enc.get("status", "Pendente"),
            "data_pedido": enc.get("data_pedido", ""),
            "data_entrega": enc.get("data_entrega", ""),
            "cores_sugeridas": enc.get("cores_sugeridas", []),
            "matriz_id": enc.get("matriz_id", ""),
            "matriz_nome": matriz_nome
        })
        
    return render_template('encomenda.html', encomenda=encomendas, matrizes=matrizes_db)

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
            "matriz_id": request.form.get("matriz_id", "") 
        }
        colecao_encomendas.insert_one(doc)
        return redirect(url_for('listar_encomendas'))
    
    # GET request - redireciona para encomenda com query params (para pre-preencher modal)
    query_string = ""
    matriz_id = request.args.get('matriz_id')
    if matriz_id:
        params = [f"matriz_id={matriz_id}"]
        i = 0
        while f'color_{i}' in request.args:
            params.append(f"color_{i}={request.args.get(f'color_{i}')}")
            i += 1
        query_string = "&".join(params)
        return redirect(url_for('listar_encomendas') + f"?{query_string}")
    
    return redirect(url_for('listar_encomendas'))

@app.route('/encomenda/editar/<id>', methods=['GET', 'POST'])
def editar_encomenda(id):
    encomenda = colecao_encomendas.find_one({"_id": ObjectId(id)})
    matrizes_db = list(colecao.find({}, {"_id": 1, "nome": 1}))
    
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
            "matriz_id": request.form.get("matriz_id", "")
        }
        colecao_encomendas.update_one({"_id": ObjectId(id)}, {"$set": dados_atualizados})
        return redirect(url_for('listar_encomendas'))
    
    return render_template('nova_encomenda.html', encomenda=encomenda, matrizes=matrizes_db)

@app.route('/encomenda/deletar/<id>', methods=['POST'])
def deletar_encomenda(id):
    colecao_encomendas.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('listar_encomendas'))

@app.route('/relatorio')
def relatorios():
    encomendas_db = list(colecao_encomendas.find({}).sort("data_pedido", -1))
    encomendas = []
    
    for enc in encomendas_db:
        encomendas.append({
            "_id": str(enc["_id"]),
            "cliente_nome": enc.get("cliente_nome", ""),
            "produto_tipo": enc.get("produto_tipo", ""),
            "quantidade": enc.get("quantidade", 1),
            "status": enc.get("status", "Pendente"),
            "data_pedido": enc.get("data_pedido", ""),
            "data_entrega": enc.get("data_entrega", "")
        })
        
    return render_template('relatorio.html', encomendas=encomendas)

# ---------------------------------------------------
# CLIENTES
# ---------------------------------------------------
colecao_clientes = db["clientes"]

@app.route('/clientes')
def listar_clientes():
    clientes_db = list(colecao_clientes.find({}).sort("nome", 1))
    clientes = []
    
    for cli in clientes_db:
        clientes.append({
            "_id": str(cli["_id"]),
            "id": cli.get("id", ""),
            "nome": cli.get("nome", ""),
            "telefone": cli.get("telefone", ""),
            "email": cli.get("email", ""),
            "endereco": cli.get("endereco", {})
        })
    
    return render_template('clientes.html', clientes=clientes)

@app.route('/cliente/novo', methods=['POST'])
def novo_cliente():
    endereco = {
        "rua": request.form.get("endereco_rua", ""),
        "bairro": request.form.get("endereco_bairro", ""),
        "numero": request.form.get("endereco_numero", ""),
        "cep": request.form.get("endereco_cep", ""),
        "cidade": request.form.get("endereco_cidade", ""),
        "estado": request.form.get("endereco_estado", "")
    }
    
    # Auto-generate sequential ID
    all_clientes = list(colecao_clientes.find({}, {"id": 1}).sort("id", -1).limit(1))
    next_id = 1
    if all_clientes and all_clientes[0].get("id"):
        try:
            last_id = int(all_clientes[0].get("id", 0))
            next_id = last_id + 1
        except (ValueError, TypeError):
            next_id = 1
    
    doc = {
        "id": str(next_id),
        "nome": request.form.get("nome", ""),
        "telefone": request.form.get("telefone", ""),
        "email": request.form.get("email", ""),
        "endereco": endereco
    }
    
    resultado = colecao_clientes.insert_one(doc)
    return redirect(url_for('listar_clientes'))

@app.route('/cliente/editar/<id>', methods=['POST'])
def editar_cliente(id):
    endereco = {
        "rua": request.form.get("endereco_rua", ""),
        "bairro": request.form.get("endereco_bairro", ""),
        "numero": request.form.get("endereco_numero", ""),
        "cep": request.form.get("endereco_cep", ""),
        "cidade": request.form.get("endereco_cidade", ""),
        "estado": request.form.get("endereco_estado", "")
    }
    
    dados_atualizados = {
        "id": request.form.get("id", ""),
        "nome": request.form.get("nome", ""),
        "telefone": request.form.get("telefone", ""),
        "email": request.form.get("email", ""),
        "endereco": endereco
    }
    
    colecao_clientes.update_one({"_id": ObjectId(id)}, {"$set": dados_atualizados})
    return redirect(url_for('listar_clientes'))

@app.route('/cliente/deletar/<id>', methods=['POST'])
def deletar_cliente(id):
    colecao_clientes.delete_one({"_id": ObjectId(id)})
    return redirect(url_for('listar_clientes'))

@app.route('/api/clientes', methods=['GET'])
def api_clientes():
    """Retorna lista de clientes em JSON para autocomplete"""
    from flask import jsonify
    clientes_db = list(colecao_clientes.find({}, {"nome": 1, "_id": 1, "telefone": 1, "email": 1}).sort("nome", 1))
    clientes = [{"_id": str(c["_id"]), "nome": c.get("nome", ""), "telefone": c.get("telefone", ""), "email": c.get("email", "")} for c in clientes_db]
    return jsonify(clientes)

@app.route('/api/cliente/<id>', methods=['GET'])
def api_cliente_detail(id):
    """Retorna detalhes completos de um cliente"""
    try:
        cliente = colecao_clientes.find_one({"_id": ObjectId(id)})
        if cliente:
            return jsonify({
                "_id": str(cliente["_id"]),
                "id": cliente.get("id", ""),
                "nome": cliente.get("nome", ""),
                "telefone": cliente.get("telefone", ""),
                "email": cliente.get("email", ""),
                "endereco": cliente.get("endereco", {})
            })
    except:
        pass
    return jsonify({"error": "Cliente não encontrado"}), 404

# ---------------------------------------------------
# CORES PREVIEW - Visualizar cores selecionadas
# ---------------------------------------------------
@app.route('/api/preview-colors/<id>', methods=['GET'])
def preview_colors(id):
    """Gera uma preview PNG com as cores selecionadas sem modificar a matriz original"""
    try:
        # Busca a matriz original
        matriz = colecao.find_one({"_id": ObjectId(id)})
        if not matriz:
            return jsonify({"error": "Matriz não encontrada"}), 404
        
        # Lê o arquivo PES original
        pes_path = os.path.join(app.config['UPLOAD_FOLDER'], matriz['arquivo'])
        if not os.path.exists(pes_path):
            return jsonify({"error": "Arquivo PES não encontrado"}), 404
        
        # Lê o pattern original
        pattern = pyembroidery.read_pes(pes_path)
        
        # Pega as cores selecionadas da query string (cor_0, cor_1, etc)
        for i in range(len(pattern.threadlist)):
            color_key = f'cor_{i}'
            if color_key in request.args:
                cor_hex = request.args.get(color_key)
                try:
                    # Converte hex para int (sem o #)
                    pattern.threadlist[i].color = int(cor_hex.lstrip('#'), 16)
                except:
                    pass
        
        # Gera PNG em memória (sem salvar no disco)
        png_buffer = io.BytesIO()
        pyembroidery.write_png(pattern, png_buffer)
        png_buffer.seek(0)
        
        return send_file(
            png_buffer,
            mimetype='image/png',
            as_attachment=False,
            download_name='preview.png'
        )
    
    except Exception as e:
        return jsonify({"error": f"Erro ao gerar preview: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)