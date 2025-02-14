from flask import Flask, request, jsonify, render_template
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from openai import OpenAI  # Importe o SDK da OpenAI

load_dotenv()

app = Flask(__name__)

# Configurações
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
UPLOAD_FOLDER = "uploads"
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')  # Chave da API do DeepSeek

# Configurações do Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Cria a pasta de uploads se não existir
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configuração do cliente da OpenAI (DeepSeek)
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"  # Endpoint da API do DeepSeek
)

# Função para aprimorar a legenda usando a API do DeepSeek
def melhorar_legenda(legenda):
    try:
        print(f"Enviando legenda para a API do DeepSeek: {legenda}")
        
        # Chama a API do DeepSeek usando o SDK da OpenAI
        response = client.chat.completions.create(
            model="deepseek-chat",  # Modelo do DeepSeek
            messages=[
                {"role": "system", "content": "Você é um assistente útil que aprimora legendas para posts de Instagram."},
                {"role": "user", "content": f"Aprimore a seguinte legenda para um post de Instagram sobre papelaria fofa, tons pastéis e produtos da Sanrio: '{legenda}'"}
            ],
            stream=False
        )

        # Extrai a legenda aprimorada
        improved_caption = response.choices[0].message.content
        print(f"Legenda aprimorada: {improved_caption}")
        return improved_caption
    except Exception as e:
        print(f"Erro ao chamar a API do DeepSeek: {str(e)}")
        return legenda  # Retorna a legenda original em caso de erro

# Rota principal para renderizar a página HTML
@app.route("/")
def index():
    return render_template("index.html")

# Rota para aprimorar a legenda
@app.route("/improve-caption", methods=["POST"])
def improve_caption():
    data = request.json
    caption = data.get("caption", "")

    if not caption:
        return jsonify({"error": "Nenhuma legenda fornecida!"}), 400

    # Aprimora a legenda usando a API do DeepSeek
    legenda_aprimorada = melhorar_legenda(caption)
    return jsonify({"improved_caption": legenda_aprimorada})

# Rota para upload e publicação de posts
@app.route("/upload", methods=["POST"])
def upload():
    files = request.files
    captions = request.form
    media_ids = []

    if not files:
        return jsonify({"error": "Nenhum arquivo enviado!"}), 400

    for i, file_key in enumerate(files):
        file = files[file_key]
        caption = captions.get(f"caption{i}", "")

        # Salva o arquivo na pasta de uploads
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        try:
            print(f"Iniciando upload para Cloudinary: {file.filename}")
            upload_result = cloudinary.uploader.upload(file_path)
            image_url = upload_result["secure_url"]
            print(f"Upload para Cloudinary bem sucedido:")
            print(f"- URL da imagem: {image_url}")
            print(f"- Public ID: {upload_result['public_id']}")
            print(f"- Tamanho: {upload_result['bytes']} bytes")
        except Exception as e:
            print(f"Erro no upload para Cloudinary: {str(e)}")
            return jsonify({"error": f"Erro no upload para Cloudinary: {str(e)}"}), 500

        # Cria o contêiner de mídia no Instagram
        upload_url = f"https://graph.facebook.com/v22.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
        response = requests.post(
            upload_url,
            data={
                "image_url": image_url,
                "caption": caption,  # Usa a legenda aprimorada (já foi aprovada pelo usuário)
                "access_token": ACCESS_TOKEN,
            }
        )

        data = response.json()
        print(f"Resposta ao criar contêiner: {response.status_code}, {data}")  # Depuração
        if "id" in data:
            media_ids.append(data["id"])
        else:
            return jsonify({"error": f"Erro ao criar contêiner: {data}"}), 500

    # Publica cada contêiner de mídia
    for media_id in media_ids:
        publish_url = f"https://graph.facebook.com/v22.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
        publish_response = requests.post(
            publish_url,
            data={
                "creation_id": media_id,
                "access_token": ACCESS_TOKEN,
            }
        )

        # Verifica se a publicação foi bem-sucedida
        print(f"Resposta ao publicar contêiner: {publish_response.status_code}, {publish_response.json()}")  # Depuração
        if publish_response.status_code != 200:
            return jsonify({"error": f"Erro ao publicar mídia: {publish_response.json()}"}), 500

    return jsonify({"message": "Posts enviados com sucesso!"})

if __name__ == "__main__":
    app.run(debug=True)