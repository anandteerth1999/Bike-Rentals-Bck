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


@app.route("/getBikes", methods=["GET"])
def getBikes():
    try:
        jwt.decode(
            request.headers['Authorization'], JWT_SECRET, verify=True)
        conn = e.connect()
        query = conn.execute('select * from bike').fetchall()
        for i in query:
           result.append({
               "id": i[0],
                "priceperday": i[1],
                "model": i[2],
                "imageurl": i[3],
                "location": i[4],
                "no_of_units": i[5],
           })
        return {'result': result}
    except KeyError:
        return "Token Not found"
    except jwt.exceptions.DecodeError:
        return "TOKEN DECODE FAILED"


if __name__ == '__main__':
    app.run(debug=True)
