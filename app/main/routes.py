from itertools import groupby

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, make_response, send_file
from flask_login import login_required, current_user
from ..db import get_db_connection
import os
import io
from werkzeug.utils import secure_filename
#from xhtml2pdf import pisa
import openai
from openai import OpenAI
from dotenv import load_dotenv
import re
import pandas as pd

#from PROJETO_PLANTAE.app.utils.api_control import can_call_api, oncrement_api_usage, log_api_usage
from ..utils.api_control import can_call_api, oncrement_api_usage, log_api_usage
from ..utils.wikipedia import buscar_curiosidades_wikipedia as wiki
from ..utils.takon_key import buscar_ocorrencias_gbif, buscar_takonkey_gbif
#pip install xhtml2pdf



main_bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

client = OpenAI(api_key=api_key)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    per_page = 10
    offset = (page - 1) * per_page
    print('offset', offset)


    conn = get_db_connection();
    cursor = conn.cursor(dictionary=True)
    id_usuario = current_user.id

    grupo = request.args.get('grupo')
    localizacao = request.args.get('localizacao')
    filtros = ['user_id = %s']
    params = [id_usuario]

    print("%", q)
    if q:
        filtros.append('(especie LIKE %s OR nome_popular LIKE %s OR familia LIKE %s OR grupo LIKE %s OR localizacao LIKE %s)')
        for _ in range(5):
            params.append("%",q)
    if grupo:
        filtros.append('grupo = %s')
        params.append(grupo)

    if localizacao:
        filtros.append('localizacao = %s')
        params.append(localizacao)

    '''    if q:

        print(q)
        cursor.execute('SELECT COUNT(*) as total FROM angiospermas WHERE user_id = %s AND ( especie LIKE %s OR nome_popular LIKE %s OR familia LIKE %s OR grupo LIKE %s OR localizacao LIKE %s)', (id_usuario, q, q, q, q, q))
        total_rows = cursor.fetchone()['total']

        total_pages = (total_rows + per_page - 1) // per_page
        query = 'SELECT * FROM angiospermas WHERE user_id = %s AND ( especie LIKE %s OR nome_popular LIKE %s OR familia LIKE %s OR grupo LIKE %s OR localizacao LIKE %s) LIMIT %s OFFSET %s'
        cursor.execute(query, (id_usuario, q, q, q,q,q, per_page, offset))
        plantas = cursor.fetchall()
    else:
        cursor.execute('SELECT COUNT(*) as total FROM angiospermas WHERE user_id = %s', (id_usuario,))

        total_rows = cursor.fetchone()['total']
        total_pages = (total_rows + per_page-1) // per_page
        print('per_page', per_page)

        cursor.execute("SELECT * FROM angiospermas WHERE user_id = %s LIMIT %s OFFSET %s", (id_usuario, per_page, offset))

        plantas = cursor.fetchall()'''



    # Se houver pesquisa
    where_clause = ' AND '.join(filtros)
    count_query =   'SELECT COUNT(*) as total FROM angiospermas WHERE ' + where_clause
    cursor.execute(count_query, tuple(params))
    total_rows = cursor.fetchone()['total']
    total_pages = (total_rows + per_page - 1) // per_page

    params_with_limit = params + [per_page, offset]
    query = 'SELECT * FROM angiospermas WHERE ' + where_clause + ' LIMIT %s OFFSET %s'
    cursor.execute(query, tuple(params_with_limit))
    plantas = cursor.fetchall()

    cursor.execute('SELECT DISTINCT localizacao FROM angiospermas WHERE user_id = %s AND localizacao IS NOT NULL', (id_usuario,))
    localizacoes = [row['localizacao'] for row in cursor.fetchall()]



    cursor.close()
    conn.close()
    print(request.endpoint)
    return render_template(
        'index.html',
        plantas=plantas,
        page = page,
        total_pages = total_pages,
        localizacoes=localizacoes,
        grupo_atual=grupo,
        localizacao_atual=localizacao,
        q=q,
        planta='planta',
        animal='animal',
        artropode='artropode',
        outros='outros'
    )

@main_bp.route('/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar():
    if request.method == 'POST':
        especie = request.form['especie']
        familia = request.form['familia']
        nome_popular = request.form['nome_popular']
        habitat = request.form['habitat']
        localizacao = request.form['localizacao']
        descricao = request.form['descricao']
        situacao = request.form.getlist('situacao')
        grupo = request.form.getlist('grupo')
        latitude = request.form['latitude'] if len(request.form['latitude']) > 0 else None
        longitude = request.form['longitude'] if len(request.form['longitude'])>0 else None

        lista = {"espécie" : especie, "habitat":habitat}
        excecao = list(map(lambda x:  "Campo obrigatório-" + x if not lista[x] else "-" + x ,lista.keys()))
        for x in excecao:
            if x.split("-")[0] ==  "Campo obrigatório":
                flash("Campo obrigatório:" + lista[x.split("-")[-1]])
                return redirect(url_for('main.adicionar'))



        # Tratamentos exceção


        #imagem = request.files['imagem']
        #imagem_filename = None

        '''if imagem and allowed_file(imagem.filename):
            filename = secure_filename(imagem.filename)
            imagem.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            imagem_filename = filename'''

        print('latitude:', latitude)
        conn = get_db_connection()
        cursor = conn.cursor()
        id_usuario = current_user.id
        cursor.execute('INSERT INTO angiospermas (especie, familia, nome_popular, habitat, localizacao, descricao, situacao, user_id, latitude, longitude, grupo) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', (especie, familia, nome_popular, habitat,localizacao, descricao, situacao[0], id_usuario, latitude, longitude, grupo[0]))
        planta_id = cursor.lastrowid

        # Agora, salva as imagens
        imagens = request.files.getlist('imagens')
        for imagem in imagens:
            if imagem and allowed_file(imagem.filename):
                filename = secure_filename(imagem.filename)
                imagem.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                cursor.execute('INSERT INTO imagens_angiospermas (planta_id, imagem) VALUES (%s, %s)', (planta_id, filename))

        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('main.index'))
    return render_template('adicionar.html')

@main_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM angiospermas WHERE id = %s', (id,))
    planta = cursor.fetchone()

    if request.method == 'POST':
        especie = request.form['especie']
        familia = request.form['familia']
        nome_popular = request.form['nome_popular']
        habitat = request.form['habitat']
        localizacao = request.form['localizacao']

        cursor.execute(
            'UPDATE angiospermas SET especie = %s, familia = %s, nome_popular = %s, habitat = %s, localizacao = %s WHERE id = %s',
            (especie, familia, nome_popular, habitat,localizacao, id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('main.index'))
    conn.close()
    cursor.close()
    return render_template('editar.html', planta=planta)

@main_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def deletar(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM imagens_angiospermas WHERE planta_id = %s', (id,))
    cursor.execute('DELETE FROM angiospermas WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('main.index'))

@main_bp.route('/info/<int:id>')
@login_required
def info(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM angiospermas WHERE id = %s', (id,))
    planta = cursor.fetchone()

    cursor.execute('SELECT * FROM imagens_angiospermas WHERE planta_id = %s', (id,))
    imagens = cursor.fetchall()

    cursor.execute('SELECT c.texto, c.data, u.username FROM comentarios2 c JOIN usuarios u ON c.usuario_id = u.id WHERE c.especie_id = %s ORDER BY c.data DESC', (id,))
    comentarios = cursor.fetchall()

    cursor.close()
    conn.close()

    curiosidades = wiki(planta['nome_popular'])

    return render_template('informacoes.html', planta=planta, imagens=imagens, curiosidades=curiosidades, comentarios=comentarios)

@main_bp.route('/home')
def home():
    

    
    return render_template('Home.html')

@main_bp.route('/ecologia_home')
def ecologia_home():
    return render_template('/ecologia_home.html')

'''@main_bp.route('/relatorio_pdf', methods = ['GET'])
@login_required
def gerar_relatorio_pdf():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    user_id = current_user.id
    grupo = request.args.getlist('grupo')
    localizacao = request.args.getlist('localizacao')
    lista = [grupo[0], localizacao[0]]

    query = [ ' AND ' +x+'@= %s' for x in lista]

    l = lambda c: c if not 'AND @=' in c else ''
    q = list(map(lambda e: e.replace('@',''),list(map(l, query))))
    print(q)

    print(grupo)
    print(len(localizacao[0]))
    if len(grupo[0]) > 2 and len(localizacao[0]) > 2:
        cursor.execute('SELECT * FROM angiospermas WHERE user_id = %s AND grupo = %s AND localizacao = %s', (user_id, grupo[0], localizacao[0]))
        print('entrou aqui')
        dados = cursor.fetchall()

    elif len(grupo[0]) <2  and  len(localizacao[0]) < 2:
        cursor.execute('SELECT * FROM angiospermas WHERE user_id = %s', (user_id,))
        dados = cursor.fetchall()
        print("entrou")


    cursor.execute('SELECT * FROM imagens_angiospermas')
    imagens = cursor.fetchall()
    caminho = 'file:///' + os.getcwd().replace('\\main','').replace('\\','/') + '/app/static/uploads/'

    html = render_template('relatorio_pdf.html', dados=dados, imagens=imagens, caminho=caminho)

    resultado = io.BytesIO()
    pisa.CreatePDF(src=html, dest=resultado)

    # Envia como resposta para download
    response = make_response(resultado.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=relatorio.pdf'
    return response'''

@main_bp.route('/mapa')
@login_required
def mapa():
    acesso = current_user.tipo_acesso
    if acesso not in ['pro', 'premium']:
        return redirect(url_for('main.index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT especie, latitude, longitude FROM angiospermas WHERE user_id = %s AND latitude IS NOT NULL AND longitude IS NOT NULL', (current_user.id,))
    pontos = cursor.fetchall()
    print(pontos)
    cursor.close()
    return render_template('mapa.html', pontos=pontos)

@main_bp.route('/CuriosidadesAnimais', methods=['GET', 'POST'])
@login_required
def curiosidades_animais():
    if request.method == "POST":
        nome = request.form["nome"]
        print(nome)
        taxonKey = buscar_takonkey_gbif(nome)
        print(taxonKey)
        if taxonKey != None:
            curiosidades = buscar_ocorrencias_gbif(taxonKey)
            print(curiosidades)
            return render_template('resultado_curiosidades_animais.html', curiosidades=curiosidades, nome=nome)
        else:
            return redirect(url_for('main.curiosidades_animais'))
    return render_template('curiosidades_animais.html')

@main_bp.route('/distribuicao', methods=['GET', 'POST'])
@login_required
def distribuicao_especie():
    acesso = current_user.tipo_acesso
    if acesso not in ['pro', 'premium']:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        nome = request.form['nome']
        taxonKey = buscar_takonkey_gbif(nome)
        if taxonKey:
            ocorrencias = buscar_ocorrencias_gbif(taxonKey)
            return render_template('resultado_distribuicao.html', nome=nome, ocorrencias=ocorrencias)
        else:
            flash("Espécie não encontrada.")
            return redirect(url_for('main.distribuicao_especie'))
    return render_template('form_distribuicao.html')


@main_bp.route('/descricao_organismo', methods=['GET', 'POST'])
@login_required
def descricao_organismo():
    acesso = current_user.tipo_acesso
    if acesso not in ['pro', 'premium']:
        return redirect(url_for('main.index'))
    if not can_call_api(current_user.id):
        flash("Limite de uso mensal atingido. Faça upgrade para continuar.", "warning")
        return redirect(url_for('main.index'))


    descricao = None
    erro = None
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()

        if not nome:
            flash("Por favor, digite o nome de um animal ou planta.")
            return redirect(url_for('main.descricao_organismo'))

        prompt = "Por favor, forneça uma descrição detalhada sobre o organismo chamado " + nome +"Incluindo características, habitat, alimentação, curiosidades e escreva o nome científico SEMPRE exatamente assim: Espécie:...."
        try:
            resposta = client.chat.completions.create(
                model = 'gpt-4o-mini',
                messages = [
                    {'role': 'system', 'content': 'Você é um assistente especializado em biologia'},
                    {'role': 'user', 'content': prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )


            descricao = resposta.choices[0].message.content
            oncrement_api_usage(current_user.id)
            log_api_usage(current_user.id, 'openAi', "success")

        except Exception as e:
            erro = str(e)
            log_api_usage(current_user.id, 'openAi', "fail")
    especie = list(re.findall("[Ee]sp[eé]cie: ?[*]{,2}? ?[A-z]* [A-z]*", descricao)) if descricao else None
    especie2 = especie[0].split(":")[-1].replace("*","").strip() if especie else None
    print("espécie: ", especie2)

    ocorrencias = ["-"]
    if especie2:
        taxonKey = buscar_takonkey_gbif(especie2)
        if taxonKey:
            ocorrencias = buscar_ocorrencias_gbif(taxonKey)

        else:
            flash("Espécie não encontrada.")

    return render_template('descricao_organismo.html', descricao=descricao, erro=erro, ocorrencias=ocorrencias, cont=len(ocorrencias))

@main_bp.route('/comentar/<int:especie_id>', methods=['POST'])
@login_required
def comentar(especie_id):
    texto = request.form['comentario']
    usuario_id = current_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO comentarios2 (especie_id, usuario_id, texto) VALUES (%s, %s, %s)', (especie_id, usuario_id, texto))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('main.info', id=especie_id))

@main_bp.route('/relatorio/excel', methods=['GET'])
@login_required
def gerar_relatorio_excel():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    id = current_user.id
    cursor.execute('SELECT * FROM angiospermas WHERE user_id = %s', (id,))
    dados = cursor.fetchall()
    if dados:
        colunas = dados[0].keys()
        colunas = list(map(lambda x : str(x), colunas))
        dicionario = {colunas[x]: [dados[y][colunas[x]] for y in range(0, len(dados))] for x in range(0, len(colunas))}
        dataframe = pd.DataFrame(dicionario)
        print(dataframe)

        # Cria um buffer para Dataframe
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            dataframe.to_excel(writer, index=False, sheet_name='Relatório')
        output.seek(0)
        return  send_file(
            output,
            as_attachment=True,
            download_name='relatorio_especies.xlsx',
            mimetype='application,vnd.openxmlformats-officedocument.spreadsheetml.sheet')





