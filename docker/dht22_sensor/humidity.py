from flask import Flask, jsonify
import adafruit_dht
import board

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
    except RuntimeError as error:
        return jsonify({"status": "error", "message": str(error)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
