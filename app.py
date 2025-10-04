from flask import Flask, render_template, request, redirect, url_for, session, send_file
import pandas as pd
import os, json, io, zipfile
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

# --- Configurare aplicație Flask ---
app = Flask(__name__)
app.secret_key = "bolt_secret_key_2025"

# --- Foldere pentru fișiere ---
UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "rezultate"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# --- Citim utilizatorii validați ---
with open("users.json", "r", encoding="utf-8") as f:
    USERS = json.load(f)

# --- Ruta principală ---
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return redirect(url_for("login"))

# --- Login ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        password = request.form["password"]
        if user in USERS and USERS[user] == password:
            session["username"] = user
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Date de autentificare greșite!")
    return render_template("login.html")

# --- Logout ---
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

# --- Pagina principală (după autentificare) ---
@app.route("/home", methods=["GET", "POST"])
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            return render_template("home.html", message="Selectează un fișier CSV!")

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # Procesăm fișierul CSV
        df = pd.read_csv(file_path)

        if "Câștiguri nete|LEI" not in df.columns:
            return render_template("home.html", message="Lipsește coloana 'Câștiguri nete|LEI'!")

        coloane_posibile = ["Șofer", "Nume complet"]
        coloana_sofer = next((c for c in coloane_posibile if c in df.columns), None)

        if not coloana_sofer:
            return render_template("home.html", message="Lipsește coloana 'Șofer' sau 'Nume complet'!")

        # Calcul comision și total
        df["Comision 12%|LEI"] = df["Câștiguri nete|LEI"] * 0.12
        df["De primit|LEI"] = df["Câștiguri nete|LEI"] - df["Comision 12%|LEI"]

        output_csv = os.path.join(RESULT_FOLDER, f"{session['username']}_calculat.csv")
        df.to_csv(output_csv, index=False)

        # Creăm PDF-uri pentru fiecare șofer
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for _, row in df.iterrows():
                nume = str(row[coloana_sofer])
                pdf_path = os.path.join(RESULT_FOLDER, f"{nume}.pdf")

                c = canvas.Canvas(pdf_path, pagesize=A4)
                c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(10.5 * cm, 27 * cm, "Situație Câștiguri Șofer")

                c.setFont("Helvetica", 12)
                c.drawString(3 * cm, 25 * cm, f"Nume: {nume}")
                c.drawString(3 * cm, 24 * cm, f"Câștiguri nete: {row['Câștiguri nete|LEI']:.2f} LEI")
                c.drawString(3 * cm, 23 * cm, f"Comision 12%: {row['Comision 12%|LEI']:.2f} LEI")
                c.line(3 * cm, 22.5 * cm, 18 * cm, 22.5 * cm)
                c.drawString(3 * cm, 22 * cm, f"Total de primit: {row['De primit|LEI']:.2f} LEI")
                c.save()

                zf.write(pdf_path, os.path.basename(pdf_path))

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="PDF_Soferi.zip"
        )

    return render_template("home.html")

# --- Pornire aplicație ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
