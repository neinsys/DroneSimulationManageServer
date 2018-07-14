from flask import Flask,render_template,request as req
from flask_pymongo import PyMongo
import requests
import json
from bson.objectid import ObjectId

droneURL = "http://127.0.0.1:8080"

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://nein:nein7961!@neinsys.io:27017/nein"
mongo = PyMongo(app)

@app.route('/')
def hello_world():
    data = {'data':'test'}
    res = requests.post(droneURL+'/json_test',data=json.dumps(data))
    images=mongo.db.image.find()
    for image in images:
        print(image)
    return 'Hello World!'

@app.route('/imageListForFiltering')
def imageListForFiltering():
    images = mongo.db.image.find()
    return render_template("imageListForFiltering.html",images=images)


@app.route('/insertImage')
def insertImage():
    return render_template("insertImage.html")

@app.route('/insertImagePost',methods=["POST"])
def insertImagePost():
    files = req.files.getlist("file")
    files_dict = {}
    for file in files:
        files_dict[file.filename]=file.read()
    #headers = {"content-type":"multipart/form-data"}
    res = requests.post(droneURL+"/getPointsByObj",files=files_dict)
    pcs = res.json()
    ret = json.dumps(pcs)
    for pc in pcs:

        mongo.db.image.insert(pc)
    return ret

@app.route('/filteringImage',methods=["POST"])
def filteringImage():
    checkbox = req.form.getlist("image")
    num=req.form.get("number")
    images = [mongo.db.image.find_one({"_id": ObjectId(_id)}, {"_id": False}) for _id in checkbox]
    para={"number":int(num),"objs":images}
    res = requests.post(droneURL+"/filteringPoints",data=json.dumps(para))
    pcs = res.json()
    ret = json.dumps(pcs)
    for pc in pcs:
        mongo.db.filteringImage.insert(pc)
    return ret

@app.route('/imageList')
def imageList():
    images = list(mongo.db.filteringImage.find())

    images = sorted(images,key=lambda x:x["filename"])
    return render_template("imageList.html",images=images)

@app.route('/findPath',methods=["POST"])
def findPath():
    checkbox = req.form.getlist("image")
    rest = req.form.get('rest')
    images = [mongo.db.filteringImage.find_one({"_id":ObjectId(_id)},{"_id":False}) for _id in checkbox]
    algorithm = req.form.get('algorithm')
    para = {'objects':images,'rest':int(rest),"algorithm":algorithm}

    res = requests.post(droneURL+"/calculatePath",data=json.dumps(para)).json()
    ret= json.dumps(res)
    mongo.db.paths.insert(res)
    print(res['analysis'])

    return ret

@app.route('/getPath',methods=["POST"])
def getPath():
    _id = req.form.get('id')
    path = mongo.db.paths.find_one({"_id":ObjectId(_id)},{"_id":False})
    return json.dumps(path)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
