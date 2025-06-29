from flask import Blueprint, request, render_template, flash, current_app, redirect, url_for
from flask_login import login_required
import os, base64, requests
from ..db import get_db_connection
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from ..main.routes import allowed_file

load_dotenv()
PLANT_ID_API_KEY = os.getenv('PLANT_ID_API_KEY')

identificar_bp = Blueprint('identificar', __name__)
UPLOADER_FOLDER = 'static/uploads'

@identificar_bp.route('/identificar', methods=['GET', 'POST'])
@login_required
def identificar():
    if request.method == 'POST':
        imagem = request.files['imagem']
        if imagem and allowed_file(imagem.filename):
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(imagem.filename))
            imagem.save(filepath)

            # Converter imagem para base64
            with open(filepath, "rb") as img_file:
                ima_base64 = base64.b64encode(img_file.read()).decode('utf-8')

            # Requisição para a API
            url = "https://api.plant.id/v2/identify"
            headers = {
                "Content-Type" : "application/json",
                "Api-Key": PLANT_ID_API_KEY
            }
            payload = {
                "images": [ima_base64],
                "organs": ["leaf", "flowers", "fruit"],
                "details": ["common_names", "url", "name_authority", "wiki_description"]
            }
            response = requests.post(url, json=payload, headers=headers)
            print("Status code:", response.status_code)
            print("Response text:", response.text)
            result = response.json()

            if 'suggestions' in result:
                conn = get_db_connection()
                cursor = conn.cursor()
                especie = result['suggestions'][0]['plant_name']
                descricao = result['suggestions'][0].get('plant_details', {}).get('wiki_description', {}).get('value', 'Descrição não disponível')
                cursor.execute('INSERT INTO angiospermas (especie, familia, nome_popular, habitat, descricao, situacao) VALUES (%s, %s, %s, %s, %s, %s)', (especie, "teste", "teste2", "teste3", descricao, "teste4" ))
                conn.commit()
                cursor.close()
                conn.close()
                print("Inseriu")
                return render_template('resultado_identificacao.html', especie=especie, descricao=descricao, imagem=filepath)
            else:
                flash("Não foi possível identificar a planta")
    return render_template('identificar.html')

@identificar_bp.route("/identificar_insetos", methods = ['GET', 'POST'])
@login_required
def identificar_insetos():
    if request.method == 'POST':
        imagem = request.files['imagem']
        if imagem and allowed_file(imagem.filename):
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(imagem.filename))
            imagem.save(filepath)
        # Converter imagem para base 64
        with open(filepath, 'rb') as img_file:
            ima_base64 = base64.b64encode(img_file.read()).decode('utf-8')

        # requisição para a API
        url = 'https://insect.kindwise.com/api/v1/identification'
        headers = {
            "Content-Type":"application/json",
            "Api-Key": os.getenv('INSECT_ID_API_KEY')
        }
        payload = {
            "images":[ima_base64],
            "similar_images": True
        }


        try:
          response = requests.post(url, json=payload, headers=headers)
          print("Status code:", response.status_code)
          print(response.text)
          data = response.json()
          #response = requests.post(url, json=payload, headers=headers)
          #data = response.json()


          if response.status_code==201 and 'result' in data:
              sugestoes = data['result']['classification']['suggestions']

              imagem_nome = imagem.filename

              return render_template('resultado_identificacao_insetos.html', sugestoes=sugestoes, imagem=imagem_nome)
          else:
              flash("Não foi possível identificar o inseto. Tente novamente")
              return redirect(url_for('identificar.identificar_insetos'))
        except Exception as a:
            print("Erro:", a)
            flash("Erro na comunicação com a API")
            return redirect(url_for('identificar.identificar_insetos'))
    return render_template("identificar_insetos.html")

@identificar_bp.route('/identificar_cogumelos', methods=['GET', 'POST'])
@login_required
def identificar_cogumelos():
    if request.method == 'POST':
        imagem = request.files['imagem']
        if imagem and allowed_file(imagem.filename):
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(imagem.filename))
            imagem.save(filepath)
        # Converter a imagem por base 64
        with open(filepath, 'rb') as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')

        # Requisição API
        url ='https://mushroom.kindwise.com/api/v1/identification?details=common_names,url,edibility,psychoactive,characteristic,look_alike&language=pt'
        headers = {
            "Content-Type":"application/json",
            "Api-Key":os.getenv("MUSHROOM_ID_API_KEY")
        }
        payload = {
            "images":[img_base64],
            "similar_images":True
        }

        try:

            response = requests.post(url, json=payload, headers=headers)
            print(response.status_code)
            if response.status_code == 200 or response.status_code == 201:

                data = response.json()
                sugestoes = data["result"]["classification"]["suggestions"]
                print("Teste")
                imagem_nome = imagem.filename
                return render_template('resultado_identificacao_cogumelos.html', sugestoes=sugestoes, imagem=imagem_nome)
            else:
                print("Teste else")
                flash("Erro o identificar o cogumelo. Verifique a imagem ou tente novamente")
                return redirect(url_for("identificar.identificar_cogumelos"))
        except Exception as e:
            print("Teste erro")
            print("Erro:", e)
            flash("Erro ao se conectar com a API de identificação")
            return redirect(url_for("identificar.identificar_cogumelos"))
    return render_template("identificar_cogumelos.html")


