from flask import Blueprint, request, render_template, flash, current_app
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



