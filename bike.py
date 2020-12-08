import datetime
from flask import Flask, request, send_file
from flask_restful import Resource, Api
from sqlalchemy import create_engine, null
from flask_cors import CORS
from flask.globals import request
from datetime import date, timedelta
import jwt
JWT_SECRET = "We live in a twilight world"

e = create_engine('sqlite:///bike.db')

app = Flask(__name__)
api = Api(app)
result = []
CORS(app)


@app.route('/locations', methods=['GET'])
def getLocation():
    result.clear()
    conn = e.connect()
    query = conn.execute('select distinct location from bike').fetchall()
    for i in query:
        result.append(i[0])
    return {'location': result}


@app.route('/available', methods=['POST'])
def availableBikes():
    data = request.get_json()
    result.clear()
    conn = e.connect()
    d = {}
    booked = []
    res = []
    total = []
    sdate = [int(i) for i in data['startDate'].split('/')]
    edate = [int(i) for i in data['endDate'].split('/')]
    sdate = date(sdate[2], sdate[1], sdate[0])
    edate = date(edate[2], edate[1], edate[0])
    delta = edate - sdate
    reservation_dates = list(
        map(lambda x: (sdate+timedelta(days=x)), range(delta.days+1)))
    reservation_dates = list(map(lambda s: ('\''+str(s.day) if(s.day > 9) else "\'0"+str(
        s.day))+'/'+str(s.month)+'/'+str(s.year)+'\'', reservation_dates))
    reservation_dates = '('+",".join(reservation_dates)+')'
    selected_location = conn.execute(
        'select model,no_of_units from bike where location =\''+data['location']+'\' group by(model)').fetchall()
    for i in selected_location:
        dict = {
            'model': i[0],
            'no_units': i[1]
        }
        total.append(dict)
        res.append(i[0])
    reserved = conn.execute('select Bike.model,count(*) from booking,Bike where sdate in '+reservation_dates +
                            ' and booking.id = Bike.id and Bike.location = \''+data['location']+'\' group by(Bike.model)').fetchall()
    for i in reserved:
        dict1 = {
            'model': i[0],
            'no_units': i[1]
        }
        booked.append(i[0])
        for j in total:
            if dict1['model'] == j['model']:
                rem = (j['no_units']-dict1['no_units']
                       ) if(j['no_units']-dict1['no_units'] > 0) else 0
                if rem > 0:
                    d[dict1['model']] = rem
    for i in res:
        if i not in booked:
            l = list(filter(lambda x: True if(
                x['model'] == i) else False, total))
            d[l[0]['model']] = l[0]['no_units']
    for i in d.keys():
        query = conn.execute('select id,imageurl,priceperday from Bike where model = \'' +
                             i+'\' and location = \''+data['location']+'\'').fetchall()[0]
        dict = {
            'id': query[0],
            'model': i,
            'priceperday': query[2]*delta.days,
            'location': data['location'],
            'no_of_units': d[i],
            'imageurl': query[1]
        }
        result.append(dict)
    return {'result': result}


@app.route("/reserve", methods=["POST"])
def reserve():
    data = request.get_json()
    conn = e.connect()
    booking_id = (conn.execute(
        "select max(booking_id) from booking").fetchall()[0][0])

    INSERT_QUERY = """INSERT INTO "main"."booking" ("booking_id", "Name", "age", "gender", "drivinglicense", "address", "sdate", "edate", "id", "email") 
                    VALUES (%d, '%s', %d, '%s', '%s', '%s', '%s', '%s', %d, '%s');""" % (int(booking_id)+1, data['Name'], int(data['age']), data['gender'],
                                                                                         data['License'], data['Address'], data['startDate'], data['endDate'], int(data['id']), data['email'])

    conn.execute(INSERT_QUERY)

    MAIL_QUERY = """SELECT email,Name,model,location,booking_id,priceperday,imageurl, sdate, edate
    from Bike, booking
    where Bike.id = booking.id and
    booking_id = %d
    """ % (int(booking_id)+1)

    data = conn.execute(MAIL_QUERY).fetchall()[0]
    mail(data)
    return "Done"


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if(data['username'] == "admin" and data["password"] == "bikemgmtadmin"):
        return jwt.encode({"user": "admin", 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, JWT_SECRET, algorithm='HS256')
    else:
        return "BAD CREDS"


@app.route("/getAdmin", methods=["GET"])
def getBikes():
    result = {}
    try:
        res = []
        jwt.decode(
            request.headers['Authorization'], JWT_SECRET, verify=True)
        conn = e.connect()
        query = conn.execute(
            'select id,priceperday,model,imageurl,location,no_of_units from bike').fetchall()
        for i in query:
            res.append({
                "id": i[0],
                "priceperday": i[1],
                "model": i[2],
                "imageurl": i[3],
                "location": i[4],
                "no_of_units": i[5],
            })
        result['bikes'] = res
        res = []
        query = conn.execute('select booking_id,Name,age,gender,drivinglicense,address,email,sdate,edate,model,location\
                               from Bike,booking\
                               where Bike.id = booking.id;').fetchall()
        for i in query:
            res.append({
                "booking_id": i[0],
                "Name": i[1],
                "age": i[2],
                "gender": i[3],
                "drivinglicense": i[4],
                "address": i[5],
                "email": i[6],
                "sdate": i[7],
                "edate": i[8],
                "model": i[9],
                "location": i[10],
            })
        result['reservations'] = res
        return result
    except KeyError:
        return "Token Not found"
    except jwt.exceptions.DecodeError:
        return "TOKEN DECODE FAILED"
    except jwt.exceptions.ExpiredSignatureError:
        return "TOKEN DECODE FAILED"


@app.route("/deleteBike", methods=["POST"])
def deleteBike():
    try:
        data = request.get_json()
        jwt.decode(
            request.headers['Authorization'], JWT_SECRET, verify=True)
        conn = e.connect()
        conn.execute("delete from Bike where id=%d" % (int(data['id'])))
        return "Done"
    except KeyError:
        return "Token Not found"
    except jwt.exceptions.DecodeError:
        return "TOKEN DECODE FAILED"
    except jwt.exceptions.ExpiredSignatureError:
        return "TOKEN DECODE FAILED"


@app.route("/deleteReservation", methods=["POST"])
def deleteReservation():
    try:
        data = request.get_json()
        jwt.decode(
            request.headers['Authorization'], JWT_SECRET, verify=True)
        conn = e.connect()
        conn.execute("delete from booking where booking_id=%d" %
                     (int(data['id'])))
        return "Done"
    except KeyError:
        return "Token Not found"
    except jwt.exceptions.DecodeError:
        return "TOKEN DECODE FAILED"
    except jwt.exceptions.ExpiredSignatureError:
        return "TOKEN DECODE FAILED"


@app.route("/insertBike", methods=["POST"])
def insertBike():
    try:
        data = request.get_json()
        jwt.decode(
            request.headers['Authorization'], JWT_SECRET, verify=True)
        conn = e.connect()
        INSERT_QUERY = "insert into Bike(id,imageurl,location,model,no_of_units,priceperday) values(%d,'%s','%s','%s',%d,%f);" % (
            int(data['id']), data['imageurl'], data['location'], data['model'], int(data['no_of_units']), float(data['priceperday']))
        conn.execute(INSERT_QUERY)
        return "Done"
    except KeyError:
        return "Token Not found"
    except jwt.exceptions.DecodeError:
        return "TOKEN DECODE FAILED"
    except jwt.exceptions.ExpiredSignatureError:
        return "TOKEN DECODE FAILED"


def mail(data):
    import smtplib
    import ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    sender_email = "bookanybike@gmail.com"
    receiver_email = data[0]
    port = 465  # For SSL
    password = "9535652311"

    message = MIMEMultipart("alternative")
    message["Subject"] = "Bike Rental Booking Conformation"
    message["From"] = sender_email
    message["To"] = receiver_email

    # Create the plain-text and HTML version of your message
    text = """\
    Hi %s,
    Your booking for %s has been confirmed.
    Location: %s
    Booking ID: %d
    Price/day: %d
    """ % (data[1], data[2], data[3], int(data[4]), int(data[5]))
    html = """\
    <html>
  <body>
    <div>
      <span style="font-size: 3rem; font-family: sans-serif; color: green"
        >Booking Confirmed</span
      ><br/><br/> <span style="font-size: 2.5rem; font-family: sans-serif; color: purple"
        >%s</span
      ><br/><br/><span style="font-size: 2.5rem; font-family: sans-serif; color: orange"
        >%s-%s</span
      ><br/><br/>
      <span style="font-size: 2rem; font-family: sans-serif; color: red"
        >%s</span
      ><br/><br/>
      <img
        style="width: 200px; height: 200px"
        src="%s"
      />
      <br/><br/>
      <table cellpadding="0" cellspacing="0" width="640" align="center" border="1">
        <tr>
          <td>Location:</td>
          <td>%s</td>
        </tr>
        <tr>
          <td>Booking ID:</td>
          <td>%d</td>
        </tr>
        <tr>
          <td>Price/day:</td>
          <td>%d</td>
        </tr>
      </table>
    </div>
  </body>
</html>

    """ % (data[1], data[7], data[8], data[2], data[6], data[3], int(data[4]), int(data[5]))
    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    message.attach(part1)
    message.attach(part2)

    # Create a secure SSL context
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login("bookanybike@gmail.com", password)
        server.sendmail(
            sender_email, receiver_email, message.as_string()
        )


if __name__ == '__main__':
    app.run(debug=True)
