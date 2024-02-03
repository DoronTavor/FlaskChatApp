from flask import Flask, render_template, request, session, redirect,url_for
from flask_socketio import join_room,leave_room,send,SocketIO
import random
from string import ascii_uppercase
from flask import send_file
from docx import Document
from reportlab.pdfgen import canvas



app= Flask(__name__)
app.config["SECRET_KEY"]="tavor3504"
socketio= SocketIO(app)

rooms= {}
def generate_unique_code(length):
    while True:
        code= ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        if code not in rooms:
            break

    return code

@app.route('/',methods=["POST","GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join",False)
        create = request.form.get("create",False)

        if not name:
            return render_template("home.html",error="Please enter a name",code=code,name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code",code=code,name=name)

        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room]= {"members" : 0, "messages":[]}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.",code=code,name=name)

        session["room"]= room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room")
    name= session.get("name")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    return render_template("room.html",code=room,name=name,messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room= session.get("room")
    if room not in rooms:
        return
    content= {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to = room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    join_room(room)
    send({"name":name,"message":"has entered the room"},to=room)
    rooms[room]["members"]+=1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)
    if room in rooms:
        rooms[room]["members"]-=1
    if rooms[room]["members"] <= 0:
        del rooms[room]
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")


@app.route("/getMessages", methods=["GET"])
def getMessages():
    room = session.get("room")
    print(rooms[room]["messages"])
    return {"messages": rooms[room]["messages"]}  # Return as JSON
@app.route("/save_messages", methods=["POST"])
def save_messages():
    room = session.get("room")
    if room is None or room not in rooms:
        return redirect(url_for("home"))

    messages = rooms[room]["messages"]
    if not messages:
        return redirect(url_for("room"))

    # Create a PDF document
    file_path = f"messages_{room}.pdf"
    with open(file_path, "wb") as pdf_file:
        pdf = canvas.Canvas(pdf_file)
        pdf.setTitle(f"Chat Room: {room}")

        # Add messages to the PDF
        y_position = 750  # Starting y position
        pdf.drawString(100, y_position, f"Chat Room :{room}")
        y_position -= 20  # Adjust for the next line
        for message in messages:
            pdf.drawString(100, y_position, f"{message['name']}: {message['message']}")
            y_position -= 20  # Adjust for the next line

        pdf.save()

    # Send the PDF file as a response
    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    socketio.run(app, debug=True)