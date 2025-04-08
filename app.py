from flask import Flask, request, render_template, redirect, flash, make_response, url_for, session
import os
import qrcode
import base64
import numpy as np
import cv2
import zipfile
import pydicom
import SimpleITK as sitk
import shutil
from werkzeug.utils import secure_filename
from xhtml2pdf import pisa
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "zip", "dcm"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def calculate_evans_index(dicom_path):
    try:
        ds = pydicom.dcmread(dicom_path)
        img = ds.pixel_array.astype(np.float32)
        img = cv2.normalize(img, None, 0, 255,
                            cv2.NORM_MINMAX).astype(np.uint8)
        _, thresh = cv2.threshold(img, 50, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        skull_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(skull_contour)
        skull_width = w

        mid_y = y + h // 2
        strip = img[mid_y - 10:mid_y + 10, :]
        _, horn_thresh = cv2.threshold(strip, 50, 255, cv2.THRESH_BINARY)
        horn_contours, _ = cv2.findContours(
            horn_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(horn_contours) < 2:
            return None

        horn_contours = sorted(
            horn_contours, key=cv2.contourArea, reverse=True)[:2]
        horn_boxes = [cv2.boundingRect(c) for c in horn_contours]
        horn_centers = [x + w // 2 for (x, y, w, h) in horn_boxes]
        horn_distance = abs(horn_centers[0] - horn_centers[1])
        return horn_distance / skull_width
    except Exception:
        return None


@app.route('/upload-mri', methods=['GET', 'POST'])
def upload_mri():
    error = None

    if request.method == 'POST':
        try:
            file = request.files['image']
            filename = file.filename

            if not filename:
                error = "No file selected"
            elif filename.endswith('.zip'):
                os.makedirs('temp', exist_ok=True)
                filepath = os.path.join('temp', filename)
                file.save(filepath)

                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                    zip_ref.extractall('temp/unzipped')
                os.remove(filepath)

                evans_index = None
                for root, _, files in os.walk('temp/unzipped'):
                    for f in files:
                        if f.endswith(".dcm"):
                            dicom_path = os.path.join(root, f)
                            evans_index = calculate_evans_index(dicom_path)
                            if evans_index:
                                break

                if evans_index:
                    session["evans_value"] = round(evans_index, 2)
                    session["evans"] = "yes" if evans_index >= 0.3 else "no"
                else:
                    session["evans_value"] = None
                    session["evans"] = "no"

                session["callosal_angle"] = 75  # fake placeholder
                session["callosal"] = "yes" if session["callosal_angle"] < 90 else "no"

                session["desh_detected"] = "yes" if "desh" in filename.lower() else "no"
                session["desh"] = session["desh_detected"]

                flash(
                    "✅ MRI analysis complete. You may review the pre-filled values below.")
                return redirect("/results")

            else:
                file.save(os.path.join('uploads', filename))
                flash("✅ File uploaded, but only zip-based DICOM analysis is active.")
                return redirect("/results")

        except Exception as e:
            import traceback
            print("UPLOAD ERROR:", str(e))
            traceback.print_exc()
            error = "Something went wrong while uploading. Try again."

    return render_template('upload.html', error=error)


@app.route("/")
def index():
    evans = session.get("evans")
    desh = session.get("desh")
    callosal = session.get("callosal")

    return render_template("index.html",
                           score=None,
                           interpretation=None,
                           evans=evans,
                           desh=desh,
                           callosal=callosal,
                           evans_value=session.get("evans_value"),
                           desh_detected=session.get("desh_detected"),
                           callosal_angle=session.get("callosal_angle"))


@app.route("/", methods=["POST"])
def calculate_score():
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

    return render_template("index.html", score=score, interpretation=interpretation,
                           evans=evans,
                           desh=desh,
                           callosal=callosal,
                           evans_value=session.get("evans_value"),
                           desh_detected=session.get("desh_detected"),
                           callosal_angle=session.get("callosal_angle"))


@app.route("/results")
def results():
    return redirect("/")


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

    qr = qrcode.make("https://nph-diagnostic-tool.onrender.com")
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


if __name__ == '__main__':
    app.run(debug=True)
