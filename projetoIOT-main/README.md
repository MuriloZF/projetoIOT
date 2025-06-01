# 🛠️ Como Rodar a APP

## 1. Instalar os Pacotes

É necessário instalar os pacotes do `requirements.txt` com o comando:

```bash
pip install -r requirements.txt
```

---

## 2. Criar o Arquivo `.env`

Após isso, é necessário criar um arquivo chamado `.env`, onde serão guardadas as variáveis do banco de dados MySQL, desse jeito:

```env
# ======= DATABASE CONFIGURATION =======
MYSQL_USER=
MYSQL_PASSWORD=
MYSQL_HOST=
MYSQL_PORT=
MYSQL_DB=

# ======= FLASK SECURITY =======
FLASK_SECRET_KEY=your-very-secret-key-replace-me-123

# ======= MQTT BROKER CONFIG =======
MQTT_BROKER_URL=
MQTT_BROKER_PORT=
MQTT_USERNAME=
MQTT_PASSWORD=
MQTT_TLS_ENABLED=
```

---

## 3. Criar o Banco de Dados

Depois disso, é necessário rodar o comando:

```bash
python create_database.py
```

Isso é para a criação do banco de dados.

---

## 4. Rodar a Aplicação

E finalmente, rodar a aplicação web com:

```bash
python app.py
```
