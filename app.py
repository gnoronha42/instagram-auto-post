from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import cloudinary
import requests 
import cloudinary.uploader
from dotenv import load_dotenv
from langchain_community.llms import Ollama

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configurações
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
UPLOAD_FOLDER = "uploads"
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')  


cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def enhance_caption(caption):
    try:
        print(f"Gerando legenda localmente para: {caption}")
        
        # Inicializa o modelo Llama
        llm = Ollama(model="mistral")
        
        # Prompt modificado para garantir resposta em português
        prompt = f"""
        Você é um especialista em marketing digital brasileiro.
        Sua tarefa é melhorar a seguinte legenda para uma postagem do Instagram sobre papelaria fofa.
        
        REGRAS IMPORTANTES:
        1. RESPONDA APENAS EM PORTUGUÊS BRASILEIRO
        2. Use emojis fofos e adequados
        3. Mantenha o tom kawaii e fofo
        4. Mencione cores pastéis e elementos Sanrio quando apropriado
        5. A resposta deve ser apenas a legenda, sem explicações
        
        Legenda original: '{caption}'
        
        Lembre-se: Responda SOMENTE em português brasileiro!
        """
        
        # Gera a resposta
        improved_caption = llm.invoke(prompt)
        
        print(f"Legenda melhorada: {improved_caption}")
        return improved_caption
        
    except Exception as e:
        print(f"Erro ao gerar legenda: {str(e)}")
        return caption


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/improve-caption", methods=["POST"])
def improve_caption_route():
    data = request.json
    caption = data.get("caption", "")

    if not caption:
        return jsonify({"error": "No caption provided!"}), 400

    improved_caption = enhance_caption(caption)
    return jsonify({"improved_caption": improved_caption})


@app.route("/upload", methods=["POST"])
def upload():
    print("Iniciando upload...")
    files = request.files
    captions = request.form
    media_ids = []

    print(f"Arquivos recebidos: {files}")
    print(f"Legendas recebidas: {captions}")

    if not files:
        return jsonify({"error": "No files uploaded!"}), 400

    for i, file_key in enumerate(files):
        file = files[file_key]
        caption = captions.get(f"caption{i}", "")

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        try:
            print(f"Starting Cloudinary upload: {file.filename}")
            upload_result = cloudinary.uploader.upload(file_path)
            image_url = upload_result["secure_url"]
            print(f"Cloudinary upload successful:")
            print(f"- Image URL: {image_url}")
            print(f"- Public ID: {upload_result['public_id']}")
            print(f"- Size: {upload_result['bytes']} bytes")
        except Exception as e:
            print(f"Error uploading to Cloudinary: {str(e)}")
            return jsonify({"error": f"Error uploading to Cloudinary: {str(e)}"}), 500

        # Creates media container on Instagram
        upload_url = f"https://graph.facebook.com/v22.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
        response = requests.post(
            upload_url,
            data={
                "image_url": image_url,
                "caption": caption,  # Uses the improved caption (already approved by user)
                "access_token": ACCESS_TOKEN,
            }
        )

        data = response.json()
        print(f"Container creation response: {response.status_code}, {data}")
        if "id" in data:
            media_ids.append(data["id"])
        else:
            return jsonify({"error": f"Error creating container: {data}"}), 500

    # Publishes each media container
    for media_id in media_ids:
        publish_url = f"https://graph.facebook.com/v22.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
        publish_response = requests.post(
            publish_url,
            data={
                "creation_id": media_id,
                "access_token": ACCESS_TOKEN,
            }
        )
        
        print(f"Container publishing response: {publish_response.status_code}, {publish_response.json()}")
        if publish_response.status_code != 200:
            return jsonify({"error": f"Error publishing media: {publish_response.json()}"}), 500

    return jsonify({"message": "Posts successfully sent!"})

if __name__ == "__main__":
    app.run(debug=True)