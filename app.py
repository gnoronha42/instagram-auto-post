from flask import Flask, request, jsonify, render_template
import requests
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)

# Configurações
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
UPLOAD_FOLDER = "uploads"

# Configurações do Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)


if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route("/")
def index():
    return render_template("index.html")

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
                "image_url": image_url,  # Use a URL pública da imagem
                "caption": caption,
                "access_token": ACCESS_TOKEN,
            }
        )
         
         
        # Verifica se o contêiner foi criado com sucesso
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
