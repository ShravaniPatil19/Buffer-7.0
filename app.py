from flask import Flask, render_template, request, redirect, session, send_file
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

import main
import db

app = Flask(__name__)
app.secret_key = "navsafe_secret"

db.init_db()


@app.route('/')
def home():
    if 'user' in session:
        return redirect('/dashboard')
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    if db.validate_user(username, password):
        session['user'] = username
        return redirect('/dashboard')

    return "Invalid credentials"


@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    success = db.register_user(username, password)
    if not success:
        return "User already exists"

    return redirect('/')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')

    history = db.get_route_history(session['user'], limit=5)
    return render_template("dashboard.html", username=session['user'], history=history)


@app.route('/route', methods=['POST'])
def route():
    if 'user' not in session:
        return redirect('/')

    start = request.form['start']
    end = request.form['end']

    try:
        shortest_distance, safest_distance, safety_score, file_name, analytics = main.run_navigation(start, end)

        db.save_route(
            session['user'],
            start,
            end,
            shortest_distance,
            safest_distance,
            safety_score
        )

        # Store last route for PDF export
        session["last_route"] = {
            "start": start,
            "end": end,
            "shortest": round(shortest_distance, 2),
            "safest": round(safest_distance, 2),
            "score": round(safety_score, 2),
            "time_factor": analytics.get("time_factor", 1.0),
            "cctv": analytics.get("cctv_points", 0),
            "police": analytics.get("police_points", 0),
            "hospital": analytics.get("hospital_points", 0)
        }

        return render_template(
            'map.html',
            shortest_distance=round(shortest_distance, 2),
            safest_distance=round(safest_distance, 2),
            safety_score=round(safety_score, 2),
            map_file=file_name,
            analytics=analytics
        )

    except Exception as e:
        return f"Something went wrong: {e}"


@app.route("/download_pdf")
def download_pdf():
    if "user" not in session:
        return redirect("/")

    if "last_route" not in session:
        return "No route found. Generate a route first."

    data = session["last_route"]

    os.makedirs("static", exist_ok=True)
    file_path = "static/route_report.pdf"

    c = canvas.Canvas(file_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 760, "NavSafe Route Report")

    c.setFont("Helvetica", 12)
    c.drawString(50, 730, f"User: {session['user']}")
    c.drawString(50, 710, f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, 675, "Route Details")

    c.setFont("Helvetica", 12)
    c.drawString(50, 650, f"Start Location: {data['start']}")
    c.drawString(50, 630, f"End Location: {data['end']}")
    c.drawString(50, 610, f"Shortest Distance: {data['shortest']} meters")
    c.drawString(50, 590, f"Safest Distance: {data['safest']} meters")
    c.drawString(50, 570, f"Safety Score: {data['score']}/100")

    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, 530, "Real-Time Insights")

    c.setFont("Helvetica", 12)
    c.drawString(50, 505, f"Time Risk Factor: {data['time_factor']}")
    c.drawString(50, 485, f"Total CCTV Points (City): {data['cctv']}")
    c.drawString(50, 465, f"Total Police Stations (City): {data['police']}")
    c.drawString(50, 445, f"Total Hospitals (City): {data['hospital']}")

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 400, "Note: Safety Score is estimated based on isolation, CCTV proximity, police proximity, hospitals and time risk.")

    c.save()

    return send_file(file_path, as_attachment=True)


@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('last_route', None)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)