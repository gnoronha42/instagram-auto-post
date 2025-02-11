from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# 🔹 Configurações de autenticação da API do Instagram
ACCESS_TOKEN = ""
INSTAGRAM_BUSINESS_ACCOUNT_ID = "SEU_INSTAGRAM_BUSINESS_ID"
UPLOAD_FOLDER = "uploads"



# Criar a pasta de uploads se não existir
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files
    captions = request.form
    media_ids = []

    for i, file_key in enumerate(files):
        file = files[file_key]
        caption = captions.get(f"caption{i}", "")
        
        # Salvar o arquivo temporariamente
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # 🔹 Fazer upload para o Instagram
        upload_url = f"https://graph.facebook.com/v17.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
        with open(file_path, "rb") as img:
            response = requests.post(
                upload_url,
                data={
                    "image_url": f"file://{file_path}",
                    "caption": caption,
                    "access_token": ACCESS_TOKEN,
                }
            )

        data = response.json()
        if "id" in data:
            media_ids.append(data["id"])

    # 🔹 Publicar cada imagem após o upload
    for media_id in media_ids:
        publish_url = f"https://graph.facebook.com/v17.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
        publish_response = requests.post(
            publish_url,
            data={
                "creation_id": media_id,
                "access_token": ACCESS_TOKEN,
            }
        )

    return jsonify({"message": "Posts enviados com sucesso!"})


if __name__ == "__main__":
    app.run(debug=True)


curl -X POST "https://graph.facebook.com/v21.0/17841470274161446/messages" \
  -H "Authorization: Bearer EAANTHhSIYhUBO5I5fSjse2Q8KZADGsjXFOkbhbCZACgszeNjG7MCXbMhYuyV0iUH7g3KCwOBFgt2R10GLHsitV69r6YcLH8IOQVU41jELdaqVY9bj4vNUuntjYAZCLW065DRXN4LM8no2yqGKZCApaLUFmasZBQKw8CQ7tdectgzW8CaRP0m1u0kjrdv6F6ZAeathfxrP92JY1Pu6UKgZDZD" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": {
      "id": "108363574631629"
    },
    "message": {
      "text": "Hello Flor de Maria, this is a test message from my Instagram bot!"
    }
  }'



curl -X GET "https://graph.facebook.com/v21.0/