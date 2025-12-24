from flask import Flask, render_template, request, send_from_directory
import pandas as pd
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

CURRENT_FILE = os.path.join(OUTPUT_FOLDER, "current_attendance.xlsx")

df = None
sessions = 0
roll_col = None
name_col = None


def detect_columns(columns):
    roll_keywords = ["roll", "reg", "register", "id", "number"]
    name_keywords = ["name"]

    roll = None
    name = None

    for col in columns:
        c = col.lower()
        if any(k in c for k in roll_keywords):
            roll = col
        if any(k in c for k in name_keywords):
            name = col

    return roll, name


@app.route("/", methods=["GET", "POST"])
def upload():
    global df, sessions, roll_col, name_col

    # Resume if file already exists
    if request.method == "GET" and os.path.exists(CURRENT_FILE):
        return render_template("resume.html")

    if request.method == "POST":
        file = request.files["excel"]
        sessions = int(request.form["sessions"])

        df = pd.read_excel(file)

        roll_col, name_col = detect_columns(df.columns)

        if not roll_col or not name_col:
            return "ERROR: Excel must contain Register/Roll Number and Name columns"

        # Initialize attendance columns
        for s in range(1, sessions + 1):
            if f"Session {s}" not in df.columns:
                df[f"Session {s}"] = "Absent"

        if "Total Present" not in df.columns:
            df["Total Present"] = 0

        df.to_excel(CURRENT_FILE, index=False)

        return render_template(
            "mark.html",
            students=df.to_dict(orient="records"),
            sessions=sessions,
            roll_col=roll_col,
            name_col=name_col
        )

    return render_template("upload.html")


@app.route("/submit", methods=["POST"])
def submit():
    global df, sessions

    form_data = request.form.to_dict(flat=False)

    for row in range(len(df)):
        for s in range(1, sessions + 1):
            key = f"attendance[{row}][{s}]"
            df.loc[row, f"Session {s}"] = form_data.get(key, ["Absent"])[0]

    df["Total Present"] = df.apply(
        lambda r: sum(
            1 for s in range(1, sessions + 1)
            if r[f"Session {s}"] == "Present"
        ),
        axis=1
    )

    df.to_excel(CURRENT_FILE, index=False)

    return send_from_directory(
        OUTPUT_FOLDER,
        "current_attendance.xlsx",
        as_attachment=True
    )


@app.route("/resume", methods=["POST"])
def resume():
    global df, sessions, roll_col, name_col

    df = pd.read_excel(CURRENT_FILE)

    sessions = len([c for c in df.columns if c.startswith("Session")])
    roll_col, name_col = detect_columns(df.columns)

    return render_template(
        "mark.html",
        students=df.to_dict(orient="records"),
        sessions=sessions,
        roll_col=roll_col,
        name_col=name_col
    )


from flask import redirect, url_for

@app.route("/reset", methods=["POST"])
def reset():
    global df, sessions, roll_col, name_col

    if os.path.exists(CURRENT_FILE):
        os.remove(CURRENT_FILE)

    # clear server state
    df = None
    sessions = 0
    roll_col = None
    name_col = None

    # IMPORTANT: redirect, do NOT render
    return redirect(url_for("upload"))



if __name__ == "__main__":
    print("✅ Flask app starting...")
    app.run(debug=True)
