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
    reserved = conn.execute('select Bike.model,count(*) from booking,Bike where sdate in '+reservation_dates +
                            ' and booking.id = Bike.id and Bike.location = \''+data['location']+'\' group by(Bike.model)').fetchall()
    for i in reserved:
        dict1 = {
            'model': i[0],
            'no_units': i[1]
        }
        for j in total:
            if dict1['model'] == j['model']:
                rem = (j['no_units']-dict1['no_units']
                       ) if(j['no_units']-dict['no_units'] > 0) else 0
                if rem > 0:
                    result.append(dict1['model'])
    return {'result': result}


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


if __name__ == '__main__':
    app.run(debug=True)
