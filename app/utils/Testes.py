import os
import pandas as pd
import PROJETO_PLANTAE.app.db as db
print(os.getcwd().replace('\\utils','').replace('\\', '/') + '/static/')

conn = db.get_db_connection()
cursor = conn.cursor(dictionary=True)
cursor.execute('SELECT * FROM angiospermas WHERE user_id = 2')

dados = cursor.fetchall()
colunas = dados[0].keys()
colunas = list(map(lambda x: str(x), colunas))
print(colunas)

dicionario2 = {colunas[x]: [dados[y][colunas[x]] for y in range(0, len(dados))] for x in range(0, len(colunas))}

#dicionario = {str(x): [dados[y][x] for y in range(0, len(dados))] for x in range (0, len(dados[0]))}
dataframe = pd.DataFrame(dicionario2)
print(dataframe)


