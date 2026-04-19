from flask import Flask, jsonify
import adafruit_dht
import board
import os

port = int(os.getenv("PORT", 5000))

app = Flask(__name__)

dhtDevice = adafruit_dht.DHT22(board.D12)

@app.route('/metrics')
def get_sensor_data():
    try:
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity
        
        return jsonify({
            "status": "success",
            "Temperatur": temperature_c,
            "Luftfeuchtigkeit": humidity
        })
    except Exception as error:
        return jsonify({"status": "error", "message": str(error)}), 500


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)
