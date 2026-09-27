from datetime import datetime
import hashlib
import json
import os
import threading
import time

import qrcode
import serial
from flask import Flask, render_template, request

app = Flask(__name__)

# Arduino IDE-la Tools > Port-la paatha actual port-a inga set pannunga.
# Example: COM3 / COM4 / COM5
ARDUINO_PORT = "COM4"
BAUD_RATE = 9600

QR_FOLDER = os.path.join("static", "qr_codes")
os.makedirs(QR_FOLDER, exist_ok=True)

# Arduino-lendhu varra latest REAL sensor data.
latest_sensor_data = {
    "conductivity": None,
    "hive_temperature": None,
    "hive_humidity": None,
    "bee_activity": None,
    "source": "Arduino not connected",
    "last_updated": "No live sensor data received yet"
}


def calculate_screening_score(conductivity, temperature, humidity, activity):
    """
    Prototype screening score.
    Uses REAL Arduino readings, but it is NOT laboratory certification.
    Calibration is required for real field deployment.
    """
    score = 100.0

    # Conductivity screening band — prototype only.
    if not 0.20 <= conductivity <= 0.80:
        score -= 35
    elif not 0.30 <= conductivity <= 0.70:
        score -= 12

    # Hive context values are not honey-purity evidence.
    # They are included only as production-context indicators.
    if temperature < 30 or temperature > 37:
        score -= 10

    if humidity < 40 or humidity > 75:
        score -= 10

    if activity < 20:
        score -= 10

    return max(0, min(100, round(score, 1)))


def get_screening_status(score):
    if score >= 90:
        return "Normal — Prototype Screening Range"
    if score >= 75:
        return "Acceptable — Review if needed"
    if score >= 60:
        return "Needs Further Checking"
    return "Flagged for Laboratory Confirmation"


def get_colony_alert(temperature, humidity, activity):
    if temperature < 30 or temperature > 37:
        return "Manual Hive Inspection Recommended"
    if humidity < 40 or humidity > 75:
        return "Manual Hive Inspection Recommended"
    if activity < 20:
        return "Manual Hive Inspection Recommended"
    return "Normal Prototype Range"


def read_arduino_data():
    """
    Arduino must send exactly one JSON line every few seconds:

    {
      "conductivity": 0.42,
      "temperature": 34.7,
      "humidity": 64.0,
      "bee_activity": 84
    }
    """

    global latest_sensor_data

    while True:
        try:
            with serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=2) as arduino:
                print(f"Arduino connected on {ARDUINO_PORT}")

                # Arduino reset aagura first seconds-ku wait pannrom.
                time.sleep(2)

                while True:
                    raw_line = arduino.readline().decode(
                        "utf-8",
                        errors="ignore"
                    ).strip()

                    if not raw_line:
                        continue

                    print("Arduino serial:", raw_line)

                    # DHT22 failure JSON vandha skip pannrom.
                    if '"error"' in raw_line:
                        print("Arduino sensor error:", raw_line)
                        continue

                    data = json.loads(raw_line)

                    # Real sensor readings-ai memory-la store pannrom.
                    latest_sensor_data["conductivity"] = float(
                        data["conductivity"]
                    )
                    latest_sensor_data["hive_temperature"] = float(
                        data["temperature"]
                    )
                    latest_sensor_data["hive_humidity"] = float(
                        data["humidity"]
                    )
                    latest_sensor_data["bee_activity"] = int(
                        data["bee_activity"]
                    )

                    latest_sensor_data["source"] = "Arduino Live Sensor Mode"
                    latest_sensor_data["last_updated"] = (
                        datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
                    )

        except serial.SerialException as error:
            print("Arduino connection waiting:", error)

            latest_sensor_data["source"] = (
                "Arduino not connected — waiting for live sensor data"
            )
            time.sleep(3)

        except (json.JSONDecodeError, KeyError, ValueError) as error:
            print("Arduino data format error:", error)
            time.sleep(1)


@app.route("/api/live-sensors")
def live_sensors():
    """
    Browser dashboard 2-second interval-la call pannum.
    Latest actual Arduino reading JSON-aa return pannum.
    """
    return {
        "conductivity": latest_sensor_data["conductivity"],
        "hive_temperature": latest_sensor_data["hive_temperature"],
        "hive_humidity": latest_sensor_data["hive_humidity"],
        "bee_activity": latest_sensor_data["bee_activity"],
        "source": latest_sensor_data["source"],
        "last_updated": latest_sensor_data["last_updated"]
    }


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":

        # Live Arduino reading vandha mattum report.
        if latest_sensor_data["conductivity"] is None:
            return """
            <html>
            <body style="font-family:Arial; padding:30px;">
                <h2>Live Arduino sensor data is not available</h2>
                <p>
                    Connect the Arduino, select the correct COM port,
                    upload the sensor code, and wait for live readings.
                </p>
                <a href="/">← Back to registration</a>
            </body>
            </html>
            """

        # Latest actual values from Arduino.
        conductivity = latest_sensor_data["conductivity"]
        hive_temperature = latest_sensor_data["hive_temperature"]
        hive_humidity = latest_sensor_data["hive_humidity"]
        bee_activity = latest_sensor_data["bee_activity"]

        screening_score = calculate_screening_score(
            conductivity,
            hive_temperature,
            hive_humidity,
            bee_activity
        )

        report_id = "HNY-" + datetime.now().strftime("%Y%m%d-%H%M%S")

        # Final real Arduino report.
        report = {
            "report_id": report_id,
            "created_at": datetime.now().strftime("%d-%m-%Y %I:%M %p"),

            # User registration details.
            "beekeeper_name": request.form["beekeeper_name"],
            "hive_id": request.form["hive_id"],
            "sample_location": request.form["sample_location"],
            "batch_id": request.form["batch_id"],
            "honey_type": request.form["honey_type"],

            # ACTUAL LIVE ARDUINO SENSOR VALUES.
            "conductivity": conductivity,
            "hive_temperature": hive_temperature,
            "hive_humidity": hive_humidity,
            "bee_activity": bee_activity,

            # Camera and calibrated moisture modules not yet connected.
            "pollen_count": "Not connected — camera module pending",
            "moisture": "Not connected — calibrated module pending",

            # Software-generated outcomes.
            "screening_score": screening_score,
            "screening_status": get_screening_status(screening_score),
            "colony_alert": get_colony_alert(
                hive_temperature,
                hive_humidity,
                bee_activity
            ),

            "sensor_source": latest_sensor_data["source"],
            "sensor_last_updated": latest_sensor_data["last_updated"],

            "mode": "Live Arduino Sensor Analysis",

            "ledger_type": "SHA-256 Tamper-Evident Hash Record",
            "disclaimer": (
                "Prototype live-sensor screening and traceability result — "
                "not laboratory-certified. Conductivity requires calibration; "
                "pollen and calibrated moisture modules are pending connection."
            )
        }

        # Report data-a canonical JSON format-la convert panni hash create pannrom.
        hash_input = json.dumps(
            report,
            sort_keys=True,
            separators=(",", ":")
        )

        report["report_hash"] = hashlib.sha256(
            hash_input.encode("utf-8")
        ).hexdigest()

        # QR-la report reference + hash irukkum.
        qr_data = (
            "HoneyChain Report Verification\n"
            f"Report ID: {report['report_id']}\n"
            f"Hive ID: {report['hive_id']}\n"
            f"Batch ID: {report['batch_id']}\n"
            f"Report Hash: {report['report_hash']}\n"
            "Status: Live Arduino Sensor Analysis"
        )

        qr_filename = f"{report_id}.png"
        qr_path = os.path.join(QR_FOLDER, qr_filename)

        qrcode.make(qr_data).save(qr_path)

        report["qr_image"] = qr_filename

        # Report page display.
        return render_template("report.html", report=report)

    return render_template("index.html")


if __name__ == "__main__":
    sensor_thread = threading.Thread(
        target=read_arduino_data,
        daemon=True
    )
    sensor_thread.start()

    app.run(debug=True, use_reloader=False)