import os
import qrcode
import base64
import cv2
import numpy as np
from flask import Flask, render_template, request, make_response, redirect, url_for, flash
from werkzeug.utils import secure_filename
from xhtml2pdf import pisa
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Step 5: Dummy callosal angle function
def calculate_callosal_angle(image_path):
    # Simulated output
    return "Estimated Callosal Angle: 85°"


# Step 6: Dummy Evans Index function
def calculate_evans_index(image_path):
    # Simulated output
    return "Evans Index: 0.33 (borderline)"


@app.route("/upload-mri", methods=["GET", "POST"])
def upload_mri():
    analysis_result = {}

    if request.method == "POST":
        file = request.files.get("image")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            analysis_result["callosal_angle"] = calculate_callosal_angle(
                filepath)
            analysis_result["evans_index"] = calculate_evans_index(filepath)
            flash("✅ MRI image uploaded and analyzed successfully!", "success")
        else:
            flash("❌ Invalid file type. Please upload a .jpg or .png image.", "danger")

    return render_template("upload.html", result=analysis_result)


@app.route("/", methods=["GET", "POST"])
def index():
    score = None
    interpretation = ""

    if request.method == "POST":
        gait = request.form.get("gait")
        urine = request.form.get("urine")
        cognition = request.form.get("cognition")
        evans = request.form.get("evans")
        desh = request.form.get("desh")
        tug = request.form.get("tug")
        tap = request.form.get("tap")
        callosal = request.form.get("callosal")

        score = 0
        if gait == "yes":
            score += 2
        if urine == "yes":
            score += 1
        if cognition == "yes":
            score += 1
        if evans == "yes":
            score += 1
        if desh == "yes":
            score += 1
        if tug == "yes":
            score += 1
        if tap == "yes":
            score += 1
        if callosal == "yes":
            score += 1

        if score >= 6:
            interpretation = "✅ High Likelihood of NPH – consider further workup or referral"
        elif 4 <= score < 6:
            interpretation = "🟡 Moderate suspicion. Consider more testing or follow-up"
        else:
            interpretation = "🔻 NPH unlikely."

    return render_template("index.html", score=score, interpretation=interpretation)


@app.route("/download", methods=["POST"])
def download_pdf():
    responses = {key: request.form.get(key, "No response")
                 for key in request.form.keys()}

    score = 0
    if responses.get("gait") == "yes":
        score += 2
    if responses.get("urine") == "yes":
        score += 1
    if responses.get("cognition") == "yes":
        score += 1
    if responses.get("evans") == "yes":
        score += 1
    if responses.get("desh") == "yes":
        score += 1
    if responses.get("tug") == "yes":
        score += 1
    if responses.get("tap") == "yes":
        score += 1
    if responses.get("callosal") == "yes":
        score += 1

    if score >= 6:
        interpretation = "✅ High Likelihood of NPH – consider further workup or referral"
    elif 4 <= score < 6:
        interpretation = "🟡 Moderate suspicion. Consider more testing or follow-up"
    else:
        interpretation = "🔻 NPH unlikely."

    qr = qrcode.make("https://hydrotoolpro.onrender.com")
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode("utf-8")

    html = render_template("report.html", score=score, interpretation=interpretation,
                           responses=responses, qr_base64=qr_base64)

    pdf_buffer = BytesIO()
    pisa.CreatePDF(BytesIO(html.encode("utf-8")), dest=pdf_buffer)
    pdf_buffer.seek(0)

    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=HydroToolPro_Report.pdf'
    return response
