from flask import Flask,render_template,request as req
from flask_pymongo import PyMongo
import requests
import json
import cv2
from bson.objectid import ObjectId
import numpy as np
import copy

droneURL = "http://127.0.0.1:8080"

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://nein:nein7961!@localhost:27017/nein"
mongo = PyMongo(app)

@app.route('/')
def hello_world():
    data = {'data':'test'}
    res = requests.post(droneURL+'/json_test',data=json.dumps(data))
    images=mongo.db.image.find()
    return 'Hello World!'

@app.route('/imageListForFiltering')
def imageListForFiltering():
    images = mongo.db.image.find()
    return render_template("imageListForFiltering.html",images=images)

@app.route('/api/imageListForFiltering')
def imageListForFilteringJSON():
    images = list(mongo.db.image.find())
    images = sorted(images,key=lambda x:x["filename"])
    for image in images:
        image["_id"] = str(image["_id"])
    return json.dumps(images)


@app.route('/insertImage')
def insertImage():
    return render_template("insertImage.html")

@app.route('/insertImagePost',methods=["POST"])
def insertImagePost():
    files = req.files.getlist("file")
    files_dict_3d = {}
    files_dict_2d={}
    files_dict_gif = {}
    for file in files:
        if file.filename[-4:].lower() == ".obj":
            files_dict_3d[file.filename]=file.read()
        elif file.filename[-4:].lower()==".gif":
            files_dict_gif[file.filename]=file
        else:
            files_dict_2d[file.filename]=file.read()
    #headers = {"content-type":"multipart/form-data"}
    ret = []
    if files_dict_3d:
        res = requests.post(droneURL+"/getPointsByObj",files=files_dict_3d)
        pcs = res.json()
        for pc in pcs:

            mongo.db.image.insert(pc)

        ret = copy.deepcopy(pcs)
    imagelist = []
    if files_dict_gif:
        import imageio
        for filename in files_dict_gif.keys():
            gif = imageio.mimread(files_dict_gif[filename])
            print("total frames : {}".format(len(gif)))

            imgs = [cv2.cvtColor(img, cv2.COLOR_RGB2BGR) for img in gif]

            for i, img in enumerate(imgs):
                imagelist.append((filename + ' ({})'.format(i),img))

    if files_dict_2d:
        for filename in files_dict_2d.keys():
            nparr = np.fromstring(files_dict_2d[filename], np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            imagelist.append((filename,image))

    if imagelist:
        for filename,image in imagelist:
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

            mongo.db.image.insert(image_dict)
            ret.append(copy.deepcopy(image_dict))
    for image in ret:
        image["_id"] = str(image["_id"])
    return json.dumps(ret)

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

@app.route('/api/imageList')
def imageListJSON():
    images = list(mongo.db.filteringImage.find())
    images = sorted(images,key=lambda x:x["filename"])
    for image in images:
        image["_id"] = str(image["_id"])
    return json.dumps(images)


@app.route('/findPath',methods=["POST"])
def findPath():
    checkbox = req.form.getlist("image")
    rest = req.form.get('rest')
    opti = req.form.get('optimization')
    images = [mongo.db.filteringImage.find_one({"_id":ObjectId(_id)},{"_id":False}) for _id in checkbox]
    algorithm = req.form.get('algorithm')
    para = {'objects':images,'rest':int(rest),"algorithm":algorithm,"optimization":int(opti)}

    res = requests.post(droneURL+"/calculatePath",data=json.dumps(para)).json()
    ret= json.dumps(res)
    mongo.db.paths.insert(res)

    return ret

@app.route('/pathList')
def pathList():
    paths = list(mongo.db.paths.find())
    return render_template("pathList.html",paths=paths)

@app.route('/api/pathList')
def pathListJSON():
    paths = list(mongo.db.paths.find())
    for path in paths:
        path["_id"] = str(path["_id"])
    return json.dumps(paths)

@app.route('/path/<pathid>')
def path(pathid):
    return "OK"

@app.route('/getPath',methods=["POST"])
def getPath():
    _id = req.form.get('id')
    path = mongo.db.paths.find_one({"_id":ObjectId(_id)},{"_id":False})
    return json.dumps(path)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
