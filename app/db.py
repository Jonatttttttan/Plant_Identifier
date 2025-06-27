import mysql.connector

def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='password',
        database='plantas'
    )
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS angiospermas(
        id INT AUTO_INCREMENT PRIMARY KEY,
        especie VARCHAR(255) NOT NULL,
        familia VARCHAR(255),
        nome_popular VARCHAR(255),
        habitat VARCHAR(255) NOT NULL,
        descricao VARCHAR(255) NOT NULL,
        situacao VARCHAR(255) NOT NULL,
        imagem VARCHAR(255)
    )''')

    # Cria tabela de imagens
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS imagens_angiospermas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    planta_id INT NOT NULL,
    imagem VARCHAR(255) NOT NULL,
    FOREIGN KEY (planta_id) REFERENCES angiospermas(id) ON DELETE CASCADE
    )''')

    # Cria login
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
      id INT AUTO_INCREMENT PRIMARY KEY,
      username VARCHAR(255) UNIQUE NOT NULL,
      password VARCHAR(255) NOT NULL)
    ''')

    conn.commit()
    cursor.close()
    conn.close()