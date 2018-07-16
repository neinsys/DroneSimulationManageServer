from flask import Flask,render_template,request as req
from flask_pymongo import PyMongo
import requests
import json
import cv2
from bson.objectid import ObjectId
import numpy as np

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
    files_dict_3d = {}
    files_dict_2d={}
    for file in files:
        if file.filename[-4:].lower() == ".obj":
            files_dict_3d[file.filename]=file.read()
        else:
            files_dict_2d[file.filename]=file.read()
    #headers = {"content-type":"multipart/form-data"}
    ret = ""
    if files_dict_3d:
        res = requests.post(droneURL+"/getPointsByObj",files=files_dict_3d)
        pcs = res.json()
        ret = json.dumps(pcs)
        for pc in pcs:

            mongo.db.image.insert(pc)
    if files_dict_2d:
        for filename in files_dict_2d.keys():
            nparr = np.fromstring(files_dict_2d[filename], np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

            edge = cv2.Canny(image, 1, 200)

            image_dict = {}
            image_dict["filename"]=filename
            image_dict["points"] = []
            cnt = 0
            for i in range(0, len(edge)):
                for j in range(0, len(edge[i])):
                    if edge[i][j] > 0:
                        image_dict["points"].append("{}.0 0.0 {}.0".format(-j,-i))
                        cnt = cnt + 1

            print(cnt)
            mongo.db.image.insert(image_dict)
    return ret

@app.route('/filteringImage',methods=["POST"])
def filteringImage():
    checkbox = req.form.getlist("image")
    num=req.form.get("number")
    leaf_size=req.form.get("leaf_size")
    width=req.form.get("width")
    images = [mongo.db.image.find_one({"_id": ObjectId(_id)}, {"_id": False}) for _id in checkbox]
    para={"number":int(num),"objs":images,"leaf_size":float(leaf_size),"width":float(width)}
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
