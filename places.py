from flask import Flask, render_template, request, redirect, jsonify
from flask import g, url_for, flash
from sqlalchemy import create_engine, asc, desc, DateTime, func
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User, VisitorVoting, Admin, Comments
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
import datetime
from werkzeug.utils import secure_filename
import os
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func
from profanity_filter import Filter
from functools import wraps
import pandas as pd
from pandas import ExcelWriter
from pandas import ExcelFile
from sqlalchemy import and_
from flask import send_from_directory
import PIL
from PIL import Image

import aws_config as cfg
from boto.s3.connection import S3Connection
import shutil
from urllib.parse import quote

import atexit

# Elastic Beanstalk initalization
app = Flask(__name__)
app.secret_key = "AKIAJWLMQFWVS7WK6BNQ"
#app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # for 2MB max-limit.



CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APP_ID = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
APPLICATION_NAME = "Places to visit Application"


# Connect to Database and create database session
engine = create_engine('mysql+pymysql://yanyanwu:yanyanwu1@newplaces.cesd6mfvvfji.us-west-2.rds.amazonaws.com:3306/newplaces?charset=utf8')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

aws_connection = S3Connection(cfg.AWS_APP_ID, cfg.AWS_APP_SECRET)
BUCKET = aws_connection.get_bucket(cfg.AWS_BUCKET)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            print("request.url= ", request.url)
            return redirect(url_for('showLogin', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/test', methods=['GET', 'POST'])
def test():
#    delete_folder("temp", 5)
    return "success"


def save_excel_to_S3(item_id, folder_name, excelfile):
    ID=str(item_id)
    aws_dir_excel = folder_name+'/'+ID+'/'

    UPLOAD_FOLDER = './upload_excel'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    if not os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], ID)):
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], ID))
    UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER                
    excelname = secure_filename(excelfile.filename)
    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], excelname)
    excelfile.save(excel_path)

    aws_excel_path = aws_dir_excel+excelname
    k = BUCKET.new_key(aws_excel_path)
    k.set_contents_from_filename(excel_path)
    shutil.rmtree(UPLOAD_FOLDER)
    return "excel saved to S3: success"

def save_images_to_S3(item_id, folder_name, file_list):
    ID=str(item_id)
#            aws_connection = S3Connection(cfg.AWS_APP_ID, cfg.AWS_APP_SECRET)
#            BUCKET = aws_connection.get_bucket(cfg.AWS_BUCKET)
    aws_dir_name = folder_name+'/'+ID+'/'
    print("aws_dir_name:", aws_dir_name)
    UPLOAD_FOLDER = './uploads'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    if not os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], ID)):
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], ID))
    UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER                
    for f in file_list:
        baseheight = 400
        img = Image.open(f)
#       hpercent = (baseheight / float(img.size[1]))
#       wsize = int((float(img.size[0]) * float(hpercent)))
#       img = img.resize((wsize, baseheight), PIL.Image.ANTIALIAS)
                
        fill_color = '#ffffff'  # your background
        if img.mode in ('RGBA', 'LA'):
            background = Image.new(img.mode[:-1], img.size, fill_color)
            background.paste(img, img.split()[-1])
            img = background
 
        basewidth = 533
        img = img.resize((basewidth, baseheight), PIL.Image.ANTIALIAS)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename))
        img.save(file_path)

        aws_file_path = aws_dir_name+f.filename
        print("aws_file_path:",aws_file_path)
        print("file_path: ",file_path)
        k = BUCKET.new_key(aws_file_path)
        k.set_contents_from_filename(file_path)

    shutil.rmtree(UPLOAD_FOLDER)
    return "files saved to S3: success"


@app.route('/delete_folder/<string:folder_name>/<int:ID>', methods=['GET', 'POST'])
def delete_folder(folder_name, ID):
    sub_folder= folder_name+'/'+str(ID)+'/'
    for file_key in BUCKET.list(prefix=sub_folder):
        BUCKET.delete_key(file_key.key)
    return "success"

def get_1st_image_for_items(items):
    image_files=[]
    img_items = []

    for item in items:
        sub_folder= 'images/'+str(item.id)+'/'
        sub_folder_len = len(sub_folder)
        image_names=[]
        for file_key in BUCKET.list(prefix=sub_folder):
            image_names.append(file_key.name[sub_folder_len:])
           # print("file_key.name: ", file_key.name[sub_folder_len:])           
        if(len(image_names) >0):
            image_names.sort()
            image_files.append(image_names[0])
            img_items.append(item)
    img_length= len(image_files)
    return img_length, image_files, img_items


def get_1st_image_for_items_including_none_image(items):
    image_files=[]
    img_items = []

    for item in items:
        sub_folder= 'images/'+str(item.id)+'/'
        sub_folder_len = len(sub_folder)
        image_names=[]
        for file_key in BUCKET.list(prefix=sub_folder):
            image_names.append(file_key.name[sub_folder_len:])
           # print("file_key.name: ", file_key.name[sub_folder_len:])           
        if(len(image_names) >0):
            image_names.sort()
            image_files.append(image_names[0])
            img_items.append(item)
        else:
            img_items.append(item)
            image_files.append(None)
    img_length= len(image_files)
    return img_length, image_files, img_items


def get_excel_data_for_item(item_id):
    sub_folder= 'excel/'+str(item_id)+'/'
    sub_folder_len = len(sub_folder)
    excel_names=[]
    for file_key in BUCKET.list(prefix=sub_folder):
        excel_names.append(file_key.name[sub_folder_len:])
    if len(excel_names) >0:
        url=quote(cfg.AWS_S3_FOLDER+file_key.name, safe=':/?*=\'')
        data = pd.read_excel(url)
    else:
        data=None
        excel_names=None
    return excel_names, data

def get_image_data_for_item(item_id):
    sub_folder= 'images/'+str(item_id)+'/'
    sub_folder_len = len(sub_folder)
    img_length= 0
    image_names=[]
    for file_key in BUCKET.list(prefix=sub_folder):
        img_length = img_length+1
        image_names.append(file_key.name[sub_folder_len:])
     #   print("file_key.name: ", file_key.name[sub_folder_len:])
    if img_length < 1:
        image_names=None
        flash("No gallery for this item_id of %s" %item_id)
    else:
        image_names.sort()
    #print ("image_names: ", image_names)
    return img_length, image_names

# Create anti-forgery state token
@app.route('/login', methods=['GET', 'POST'])
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    next = request.args.get('next')
    if next is None:
        next = '/'
    return render_template('login.html', STATE=state, next=next, client_id=CLIENT_ID, app_id=APP_ID)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data.decode("utf-8")
    print("access token received %s " % access_token)

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type='\
          'fb_exchange_token&client_id=%s&client_secret='\
          '%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1].decode('utf-8')

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the server token exchange
        we have to split the token first on commas and select the first index
        which gives us the key : value for the server access token then we
        split it on colons to pull out the actual token value and replace
        the remaining quotes with nothing so that it can be used directly
        in the graph api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    print("token tested:  ", token)

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields='\
          'name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1].decode('utf-8')
    print("url sent for API access:%s" % url)
    print("API JSON result: %s" % result)

    data = json.loads(result)
    print(data)

    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&'\
          'redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1].decode('utf-8')
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'\
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s'\
          % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1].decode('utf-8')
    return "You have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():

 #   login_session.clear() #added by Yanyan
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token

    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already '
                                            'connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
   

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    print("username: ", data['name'])
    print("email: ", data['email'])
    print("picture: ", data['picture'])
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    print("user_id by gmail: ", user_id)
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'\
              '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("You are now logged in as %s" % login_session['username'])
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'], date =datetime.datetime.now(), credits =0)
    session.add(newUser)
    try:
        session.commit()
        user = session.query(User).filter_by(email=login_session['email']).one()
        return user.id
    except:
        return None



def getUserInfo(user_id):

    try:
        user = session.query(User).filter_by(id=user_id).one()
    except:
        user = None
    return user


def getUserID(email):
    print("email in getUserID: ", email)
    print ("session users number: ",session.query(User).count())
    try:
        user = session.query(User).filter_by(email=email).one()
        print("user object: ", user)
        return user.id
    except:
        return None

def getAdminID(email):
    print("email in getAdminID: ", email)
    try:
        admin = session.query(Admin).filter_by(email=email).one()
        return admin.id
    except:
        return None

@app.route('/isAdminUser')
def isAdminUser():
    try:
        this_user= session.query(User).filter_by(id=login_session['user_id']).one()
        admin_id= getAdminID(email=this_user.email)
    except :
        admin_id = None
    if admin_id is None:
        return False
    else:
        return True

# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():

#    credentials= login_session['credentials'] #Yanyan added
    # Check that the access token is valid.    
#    if credentials.access_token_expired:   #Yanyan added for google OAuth
#        credentials.refresh(httplib2.Http())   #Yanya  for google OAuth
   
   # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    print("access_token:  ", access_token)
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for '
                                            'given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Category Information
@app.route('/category/<int:category_id>/items/JSON')
def categoryItemJSON(category_id):
    try:
        category = session.query(Category).filter_by(id=category_id).one()
        items = session.query(Item).filter_by(
            category_id=category_id).order_by(desc(Item.date)).all()
        return jsonify(Items=[i.serialize for i in items])
    except :
        session.rollback()
        return render_template('error.html')
    

# JSON APIs to view item Information
@app.route('/items/JSON')
def itemsJSON():
    try:
        items = session.query(Item).order_by(desc(Item.date)).all()
        return jsonify(Items=[i.serialize for i in items])
    except :
        session.rollback()
        return render_template('error.html')
    

@app.route('/category/<int:category_id>/item/<int:item_id>/JSON')
def ItemJSON(category_id, item_id):
    try:
        item = session.query(Item).filter_by(id=item_id).order_by(desc(Item.date)).one()
        return jsonify(Item=item.serialize)
    except:
        session.rollback()
        return render_template('error.html')


@app.route('/categorys/JSON')
def categorysJSON():
    try:
        categorys = session.query(Category).order_by(desc(Category.user_id)).all()
        return jsonify(categorys=[r.serialize for r in categorys])
    except :
        session.rollback()
        return render_template('error.html')


@app.route('/users/JSON')
@login_required
def usersJSON():
    if isAdminUser() == True :
        try:
            users = session.query(User).order_by(asc(User.id)).all()
            return jsonify(users=[r.serialize for r in users])
        except :
            session.rollback()
            return render_template('error.html')      
    else:
        return "<script>function myFunction() {alert('You are not authorized to view this page.');}</script><body onload='myFunction()'>"

@app.route('/admins/JSON')
@login_required
def adminsJSON():
    if isAdminUser() == True :
        try:
            admins = session.query(Admin).order_by(asc(Admin.id)).all()
            return jsonify(admins=[r.serialize for r in admins])
        except :
            session.rollback()
            return render_template('error.html') 
    else:
        return "<script>function myFunction() {alert('You are not authorized to view this page.');}</script><body onload='myFunction()'>"

@app.route('/votings/JSON')
def votingsJSON():
    try:
        votings = session.query(VisitorVoting).order_by(desc(VisitorVoting.date)).all()
        return jsonify(votings=[r.serialize for r in votings])
    except :
        session.rollback()
        return render_template('error.html')

@app.route('/user/<int:user_id>/items/JSON')
def userItemJSON(user_id):
    try:
        items = session.query(Item).filter_by(
            user_id=user_id).order_by(desc(Item.date)).all()
        return jsonify(Items=[i.serialize for i in items])
    except :
        session.rollback()
        return render_template('error.html')

@app.route('/user_name/<string:user_name>/items/JSON')
def usernameItemJSON(user_name):
    try:
        user = session.query(User).filter_by(name=user_name).one()
        items = session.query(Item).filter_by(user_id=user.id).order_by(desc(Item.date)).all()
        return jsonify(Items=[i.serialize for i in items])
    except:
        session.rollback()
        return render_template('error.html')

@app.route('/user/<int:user_id>/categorys/JSON')
def userCategoryJSON(user_id):
    try:
        categorys = session.query(Category).filter_by(
            user_id=user_id).order_by(asc(Category.name)).all()
        return jsonify(Categorys=[i.serialize for i in categorys])
    except :
        session.rollback()
        return render_template('error.html')

@app.route('/user_name/<string:user_name>/categorys/JSON')
def usernameCategoryJSON(user_name):
    try:
        user = session.query(User).filter_by(name=user_name).one()
        categorys = session.query(Category).filter_by(user_id=user.id).order_by(asc(Category.name)).all()
        return jsonify(Categorys=[i.serialize for i in categorys])
    except:
        session.rollback()
        return render_template('error.html')

@app.route('/user/<int:user_id>/votings/JSON')
def userVotingJSON(user_id):
    try:
        votings = session.query(VisitorVoting).filter_by(
            user_id=user_id).order_by(desc(VisitorVoting.date)).all()
        return jsonify(votings=[i.serialize for i in votings])
    except :
        session.rollback()
        return render_template('error.html')
    

@app.route('/user_name/<string:user_name>/votings/JSON')
def usernameVotingJSON(user_name):
    try:
        user = session.query(User).filter_by(name=user_name).one()
        votings = session.query(VisitorVoting).filter_by(user_id=user.id).order_by(desc(VisitorVoting.date)).all()
        return jsonify(votings=[i.serialize for i in votings])
    except:
        session.rollback()
        return render_template('error.html')

@app.route('/comments/JSON')
def commentsJSON():
    try:
        comments = session.query(Comments).order_by(desc(Comments.date)).all()
        return jsonify(comments=[r.serialize for r in comments])
    except :
        session.rollback()
        return render_template('error.html')


@app.route('/user/<int:user_id>/comments/JSON')
def userCommentsJSON(user_id):
    try:
        comments = session.query(Comments).order_by(desc(Comments.date)).filter_by(
            user_id=user_id).all()
        return jsonify(comments=[i.serialize for i in comments])
    except :
        session.rollback()
        return render_template('error.html')

@app.route('/user_name/<string:user_name>/comments/JSON')
def usernameCommentsJSON(user_name):
    try:
        user = session.query(User).filter_by(name=user_name).one()
        comments = session.query(Comments).filter_by(user_id=user.id).order_by(desc(Comments.date)).all()
        return jsonify(comments=[i.serialize for i in comments])
    except:
        session.rollback()
        return render_template('error.html')

# Show all categorys
@app.route('/')
@app.route('/category/')
def showCategorys():
    try:
        categorys = session.query(Category).order_by(asc(Category.name))
        latest_items = session.query(Item).order_by(
                desc(Item.date)).limit(10).all()
    except :
        session.rollback()
        return render_template('error.html')
#    pic_files=[]
#    for item in latest_items:
#        ID=str(item.id)
#        UPLOAD_FOLDER = './static/images'
#        app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#        UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
#        if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
#            image_names = os.listdir(UPLOAD_FOLDER)
#            if(len(image_names) >0):
#                image_names.sort()
#                pic_files.append(image_names[0]) 
#            else:
#                pic_files.append(None)
#        else:
#            pic_files.append(None)
    # get representative images of lagest items
    pic_length, pic_files, pic_items = get_1st_image_for_items_including_none_image(items=latest_items)

    # to get a clean image list with no none image files for display
    try:
        top_items = session.query(VisitorVoting.item_id, Item.id.label('id'), Item.category_id, Item.name.label('item_name'), func.sum(VisitorVoting.like_counts).label('total_counts'), User.name, Category.name, Item.date).filter(VisitorVoting.item_id == Item.id, Item.user_id==User.id, Item.category_id==Category.id, Item.date> datetime.date(2017, 12,1)). group_by(
            VisitorVoting.item_id).order_by(desc('total_counts')).order_by(desc(Item.date)).limit(16)
    except :
        session.rollback()
        return render_template('error.html')
#    image_files=[]
#    img_items = []
#    for item in top_items:
#        ID=str(item.id)
#        UPLOAD_FOLDER = './static/images'
#        app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#        UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
#        if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
#            image_names = os.listdir(UPLOAD_FOLDER)
#            if(len(image_names) >0):
#                image_names.sort()
#                image_files.append(image_names[0])
#                img_items.append(item)
#    img_length= len(image_files)

    # get representative iamges of top items
    img_length, image_files, img_items = get_1st_image_for_items(items=top_items)
   
    if 'username' not in login_session:
        return render_template('publicCategorys.html',
                               categorys=categorys, lates_items_names=zip(latest_items,pic_files), image_names=image_files, img_length=img_length, img_items=img_items, image_names_items=zip(image_files, img_items), image_names_items_copy=zip(image_files, img_items))
    else:
        return render_template('categorys.html',
                               categorys=categorys, lates_items_names=zip(latest_items,pic_files), image_names=image_files, img_length=img_length, img_items=img_items, image_names_items=zip(image_files, img_items), image_names_items_copy=zip(image_files, img_items))

# Create a new category


@app.route('/category/new/', methods=['GET', 'POST'])
@login_required
def newCategory():
    if request.method == 'POST':
        if  'name' in request.form:
            new_name = request.form['name']
            newCategory = Category(
                name=Filter(new_name, "???").clean(),
                user_id=login_session['user_id'])
            session.add(newCategory)
            try:
                session.commit()
                flash('New Category "%s "Successfully Created' % newCategory.name)
            except:
                session.rollback()
                return render_template('error.html')
            return redirect(url_for('showCategorys'))
    else:
        return render_template('newCategory.html')

# Edit a category


@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
@login_required
def editCategory(category_id):
    #   if 'username' not in login_session:
    #       return redirect('/login')
    try:
        editedCategory = session.query(
            Category).filter_by(id=category_id).one()
    except :
        session.rollback()
        return render_template('error.html')
    if editedCategory.user_id != login_session['user_id']:
        if (isAdminUser()== False):
            flash('You are not authorized to edit this Category.'
                'You can only edit your own Category.')
            return redirect(url_for('showCategoryItems', category_id=category_id))
        else:
            flash('You logged in as an Admin user')
    #  return "<script>function myFunction() {alert('You are not authorized"
    #   " to edit this Category. Please create your own Category in order "
    #   "to edit.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if  'name' in request.form:
            new_name = request.form['name']
            editedCategory.name = Filter(new_name, "???").clean()
            session.add(editedCategory)
            try:
                session.commit()
                flash('Category " %s " Successfully Edited' % editedCategory.name)
            except:
                session.rollback()
                return render_template('error.html')         
            return redirect(url_for('showCategoryItems',
                                    category_id=category_id))
    else:
        return render_template('editCategory.html', category=editedCategory)


# Delete a category
@app.route('/category/<int:category_id>/delete/', methods=['GET', 'POST'])
@login_required
def deleteCategory(category_id):
    #    if 'username' not in login_session:
    #        return redirect('/login')
    try:
        CategoryToDelete = session.query(
            Category).filter_by(id=category_id).one()
        counts = session.query(func.count(Item.id)).\
            filter_by(category_id=category_id).scalar()
    except :
        session.rollback()
        return render_template('error.html')
    if counts > 0:
        flash('You cannot delete %s category since there were items created '
              'under it.' % CategoryToDelete.name)
        return redirect(url_for('showCategoryItems', category_id=category_id))
    
 #   this_user= session.query(User).filter_by(id=login_session['user_id']).one()
 #   admin_id = session.query(Admin).filter_by(email=this_user.email)
    if CategoryToDelete.user_id != login_session['user_id']: 
        if isAdminUser() == False :
            flash('You are not authorized to delete this Category. '
                  'You can only delete the Category created by you.')
            return redirect(url_for('showCategoryItems', category_id=category_id))
        else:
            flash('You logged in as an Admin user')
#           return "<script>function myFunction() {alert('You are not authorized
#           to delete this Category.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(CategoryToDelete)
        try:
            session.commit()
            flash('Category " %s " Successfully Deleted' % CategoryToDelete.name)
        except:
            session.rollback()
            return render_template('error.html')
        return redirect(url_for('showCategorys'))
    else:
        return render_template('deleteCategory.html',
                               category=CategoryToDelete)


# Show a category item
@app.route('/category/<int:category_id>/')
@app.route('/category/<int:category_id>/item/')
def showCategoryItems(category_id):
    try:
        categorys = session.query(Category).order_by(asc(Category.name))
        category = session.query(Category).filter_by(id=category_id).one()
        creator = getUserInfo(category.user_id)
        items = session.query(Item).filter_by(
            category_id=category_id).order_by(desc(Item.date)).all()
        counts = session.query(func.count(Item.id)).filter_by(
            category_id=category_id).scalar()
    except :
        session.rollback()
        return render_template('error.html')

 #   this_user= session.query(User).filter_by(id=login_session['user_id']).one()
 #   admin_id = session.query(Admin).filter_by(email=this_user.email)

    #get image files

#    pic_files=[]
#    for item in items:
#        ID=str(item.id)
#        UPLOAD_FOLDER = './static/images'
#        app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#        UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
#        if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
#            image_names = os.listdir(UPLOAD_FOLDER)
#            if len(image_names) >0 :
#                pic_files.append(image_names[0])
#            else:
#                pic_files.append(None)
#        else:
#            pic_files.append(None)
     #get first image files for each items
    pic_length, pic_files, pic_items = get_1st_image_for_items_including_none_image(items=items)


    if 'username' not in login_session:
        return render_template('publicCategoryItems.html', items=items,
                               category=category, creator=creator,
                               categorys=categorys, counts=counts,
                               items_names=zip(items,pic_files))
    else:
        if creator.id != login_session['user_id']:
            if isAdminUser() == False:
                return render_template('publicCategoryItems.html', items=items,
                                        category=category, creator=creator,
                                        categorys=categorys, counts=counts,
                                        items_names=zip(items,pic_files))
            else:
                flash('You logged in as an Admin user')
                return render_template('categoryItems.html', items=items,
                                    category=category, creator=creator,
                                    categorys=categorys, counts=counts,
                                    items_names=zip(items,pic_files))
        else:
            return render_template('categoryItems.html', items=items,
                                    category=category, creator=creator,
                                    categorys=categorys, counts=counts,
                                    items_names=zip(items,pic_files))


# Create a new item
@app.route('/category/<int:category_id>/item/new/', methods=['GET', 'POST'])
@login_required
def newItem(category_id):
    #    if 'username' not in login_session:
    #        return redirect('/login')
    try:
        category = session.query(Category).filter_by(id=category_id).one()
        categorys = session.query(Category).order_by(asc(Category.name))
    except :
        session.rollback()
        return render_template('error.html')
#    if login_session['user_id'] != category.user_id:
#        return "<script>function myFunction() {alert('You are not authorized
#   to add items to this Category.');}</script><body onload='myFunction()'>"
    states = ['ALABAMA', 'ALASKA', 'ARIZONA', 'ARKANSAS', 'CALIFORNIA',
              'COLORADO', 'CONNECTICUT', 'DELAWARE', 'FLORIDA', 'GEORGIA',
              'HAWAII', 'IDAHO', 'ILLINOIS', 'INDIANA', 'IOWA', 'KANSAS',
              'KENTUCKY', 'LOUISIANA', 'MAINE', 'MARYLAND', 'MASSACHUSETTS',
              'MICHIGAN', 'MINNESOTA', 'MISSISSIPPI', 'MISSOURI', 'MONTANA',
              'NEBRASKA', 'NEVADA', 'NEW HAMPSHIRE', 'NEW JERSEY',
              'NEW MEXICO', 'NEW YORK', 'NORTH CAROLINA', 'NORTH DAKOTA',
              'OHIO', 'OKLAHOMA', 'OREGON', 'PENNSYLVANIA', 'RHODE ISLAND',
              'SOUTH CAROLINA', 'SOUTH DAKOTA', 'TENNESSEE', 'TEXAS', 'UTAH',
              'VERMONT', 'VIRGINIA', 'WASHINGTON', 'WEST VIRGINIA',
              'WISCONSIN', 'WYOMING', 'GUAM', 'PUERTO RICO', 'VIRGIN ISLANDS', 
              'Others outside US']
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
              'August', 'September', 'October', 'November', 'December']

    countrys = ['Afghanistan', 'Algeria', 'Angola', 'Argentina', 'Armenia', 'Australia', 
                'Austria', 'Azerbaijan', 'Bahamas', 'Bahrain', 'Bangladesh',
                'Belgium', 'Bolivia', 'Brazil','Cambodia', 'Cameroon', 'Canada',
                'Central African Republic', 'Chad', 'Chile', 'China', 'Colombia',
                'Congo', 'Costa Rica', 'Cuba', 'Cyprus', 'Republic of Congo',
                'Denmark', 'Dominican Republic', 'Dominica', 'Ecuador', 'Egypt',
                'El Salvador', 'Ethiopia', 'Fiji', 'Finland', 'France', 'Georgia',
                'Germany', 'Ghana', 'Great Britain', 'Greece', 'Guadeloupe',
                'Haiti' ,'Honduras', 'Hungary', 'Iceland', 'India', 'Indonesia', 
                'Iran', 'Iraq', 'Israel', 'Italy', 'Ivory Coast', 'Jamaica',
                'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kuwait', 'Laos',
                'Liberia', 'Libya', 'Malaysia', 'Mali', 'Malta', 'Mexico',
                'Mongolia', 'Morocco', 'Mozambique', 'Namibia', 'Nepal',
                'Netherlands', 'New Zealand', 'Nigeria', 'North Korea',
                'Norway', 'Pacific Islands', 'Pakistan', 'Panama', 
                'Papua New Guinea', 'Peru', 'Philippines', 'Poland', 'Portugal'
                'Puerto Rico', 'Qatar', 'Romania', 'Russia', 'Rwanda',
                'Saudi Arabia', 'Singapore', 'Slovenia', 'Solomon Islands',
                'South Africa', 'South Korea', 'South Sudan', 'Spain', 
                'Sri Lanka', 'Sudan', 'Swaziland', 'Sweden', 'Switzerland',
                'Syria', 'Tajikistan', 'Tanzania', 'Thailand', 'Tunisia',
                'Turkey', 'Turkmenistan', 'Uganda', 'Ukraine', 'United Arab Emirates',
                'United States', 'Uzbekistan', 'Venezuela', 'Vietnam',
                'Virgin Islands', 'Yemen', 'Zambia', 'Zimbabwe', 'Others']

    if request.method == 'POST':

        if 'name' in request.form:
            item_name = request.form['name']
        else:
            item_name = ''
        if 'description' in request.form:          
            item_des = request.form['description']           
        else:
            item_des = ''
        if 'price' in request.form: 
            item_price = request.form['price']
        else:
            item_price = 0
        if 'your_state' in request.form: 
            item_state = request.form['your_state']
        else:
            item_state = ''
        if 'method' in request.form: 
            item_method = request.form['method']
        else:
            item_method = ''            
        if 'month' in request.form: 
            item_month = request.form['month']
        else:
            item_month = ''        
        if 'days' in request.form: 
            item_days = request.form['days']
        else:  
            item_days = 1
        if 'place_state' in request.form: 
            place_state = request.form['place_state']
        else:  
            place_state = ''
        if 'place_country' in request.form: 
            place_country = request.form['place_country']
        else:  
            place_country = 'United States'          
        if 'category_id' in request.form: 
            category_id = request.form['category_id']
        else:
            category_id = ''
        if 'excelfile' in request.files: 
            excelfile = request.files['excelfile']
        if 'photos' in request.files:
            if len(request.files.getlist('photos')) >16:
                flash("Maximum of 16 photos can be uploaded, please try again. Thanks.")
                render_template('newitem.html', category=category,
                               category_id=category_id, categorys=categorys,
                               item_name=item_name, item_des=item_des, item_price=item_price,
                               states=states, item_state=item_state, item_method=item_method,item_days=item_days, months=months, countrys=countrys, month=item_month, place_state=place_state, place_country=place_country)
        

#           profane = profanity_filter.Filter(product_review, "unicorn")
#           print ("Clean Text: %s" % profane.clean())
        newItem = Item(name=Filter(item_name, "???").clean(),
                       description=Filter(item_des,
                       "???").clean(),
                       price=Filter(item_price, "???").clean(),
                       category_id=category_id,
                       user_id=login_session['user_id'],
                       date=datetime.datetime.now(),
                       state=item_state,
                       method=item_method, month=item_month, duration_days=item_days, place_country=place_country, place_state=place_state)  # , data=file.read())
        session.add(newItem)
        try:
            session.commit()
            the_size = len(request.files.getlist('photos'))
            print ("the_size:", the_size)
    #        image_f = request.files.getlist('photos')[0].filename
    #        if image_f !='':
            if the_size>0:

                save_images_to_S3(item_id=newItem.id, folder_name="images", file_list= request.files.getlist('photos'))
    #            ID=str(newItem.id)
    #            aws_connection = S3Connection(cfg.AWS_APP_ID, cfg.AWS_APP_SECRET)
    #            BUCKET = aws_connection.get_bucket(cfg.AWS_BUCKET)
    #            aws_dir_name = 'images/'+ID+'/'

    #            UPLOAD_FOLDER = './uploads'
    #            app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    #            if not os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], ID)):
    #                os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], ID))
    #            UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
    #            app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER                
    #            for f in request.files.getlist('photos'):
    #                baseheight = 400
    #                img = Image.open(f)
    #                    hpercent = (baseheight / float(img.size[1]))
    #                    wsize = int((float(img.size[0]) * float(hpercent)))
    #                    img = img.resize((wsize, baseheight), PIL.Image.ANTIALIAS)
                    
    #                fill_color = '#ffffff'  # your background
    #                if img.mode in ('RGBA', 'LA'):
    #                    background = Image.new(img.mode[:-1], img.size, fill_color)
    #                    background.paste(img, img.split()[-1])
    #                    img = background
     
    #                basewidth = 533
    #                img = img.resize((basewidth, baseheight), PIL.Image.ANTIALIAS)
    #                file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename))
    #                img.save(file_path)

    #                aws_file_path = aws_dir_name+f.filename
    #                k = BUCKET.new_key(aws_file_path)
    #                k.set_contents_from_filename(file_path)

    #            shutil.rmtree(UPLOAD_FOLDER)


            if 'excelfile' in request.files:
                save_excel_to_S3(item_id=newItem.id, folder_name="excel", excelfile=excelfile)
            #    ID=str(newItem.id)
            #    aws_dir_excel = 'excel/'+ID+'/'

            #    UPLOAD_FOLDER = './upload_excel'
            #    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
            #    if not os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], ID)):
            #        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], ID))
            #    UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
            #    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER                
            #    excelname = secure_filename(excelfile.filename)
            #    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], excelname)
            #    excelfile.save(excel_path)


            #    aws_excel_path = aws_dir_excel+excelname
            #    k = BUCKET.new_key(aws_excel_path)
            #    k.set_contents_from_filename(excel_path)
            #    shutil.rmtree(UPLOAD_FOLDER)

            flash('New Item " %s " Successfully Created' % (newItem.name))
            return redirect(url_for('showItem', category_id=category_id, item_id=newItem.id))
        except:
            session.rollback()
            return render_template('error.html') 
    else:
        return render_template('newitem.html', category=category,
                               category_id=category_id, categorys=categorys,
                               item_name='', item_des='', item_price=0,
                               states=states, item_state='', item_method='',item_days=1, months=months, countrys=countrys, month='', place_state='', place_country='United States')

# Edit an item


@app.route('/category/<int:category_id>/item/<int:item_id>/edit',
           methods=['GET', 'POST'])
@login_required
def editItem(category_id, item_id):
    #   if 'username' not in login_session:
    #       return redirect('/login')
    try:
        editedItem = session.query(Item).filter_by(id=item_id).one()
        category = session.query(Category).filter_by(id=category_id).one()
        categorys = session.query(Category).order_by(asc(Category.name))
    except :
        session.rollback()
        return render_template('error.html')

    ID=str(editedItem.id)
    UPLOAD_FOLDER = './static/images'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
    if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
        image_names = os.listdir(UPLOAD_FOLDER)
        if len(image_names) >0:
            file_name=image_names[0]
        else:
            file_name=None
    else:
        file_name=None
    
    states = ['ALABAMA', 'ALASKA', 'ARIZONA', 'ARKANSAS', 'CALIFORNIA',
              'COLORADO', 'CONNECTICUT', 'DELAWARE', 'FLORIDA', 'GEORGIA',
              'HAWAII', 'IDAHO', 'ILLINOIS', 'INDIANA', 'IOWA', 'KANSAS',
              'KENTUCKY', 'LOUISIANA', 'MAINE', 'MARYLAND', 'MASSACHUSETTS',
              'MICHIGAN', 'MINNESOTA', 'MISSISSIPPI', 'MISSOURI', 'MONTANA',
              'NEBRASKA', 'NEVADA', 'NEW HAMPSHIRE', 'NEW JERSEY',
              'NEW MEXICO', 'NEW YORK', 'NORTH CAROLINA', 'NORTH DAKOTA',
              'OHIO', 'OKLAHOMA', 'OREGON', 'PENNSYLVANIA', 'RHODE ISLAND',
              'SOUTH CAROLINA', 'SOUTH DAKOTA', 'TENNESSEE', 'TEXAS', 'UTAH',
              'VERMONT', 'VIRGINIA', 'WASHINGTON', 'WEST VIRGINIA',
              'WISCONSIN', 'WYOMING', 'GUAM', 'PUERTO RICO', 'VIRGIN ISLANDS',
              'Others outside US']
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
              'August', 'September', 'October', 'November', 'December']
    countrys = ['Afghanistan', 'Algeria', 'Angola', 'Argentina', 'Armenia', 'Australia', 
                'Austria', 'Azerbaijan', 'Bahamas', 'Bahrain', 'Bangladesh',
                'Belgium', 'Bolivia', 'Brazil','Cambodia', 'Cameroon', 'Canada',
                'Central African Republic', 'Chad', 'Chile', 'China', 'Colombia',
                'Congo', 'Costa Rica', 'Cuba', 'Cyprus', 'Republic of Congo',
                'Denmark', 'Dominican Republic', 'Dominica', 'Ecuador', 'Egypt',
                'El Salvador', 'Ethiopia', 'Fiji', 'Finland', 'France', 'Georgia',
                'Germany', 'Ghana', 'Great Britain', 'Greece', 'Guadeloupe',
                'Haiti' ,'Honduras', 'Hungary', 'Iceland', 'India', 'Indonesia', 
                'Iran', 'Iraq', 'Israel', 'Italy', 'Ivory Coast', 'Jamaica',
                'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kuwait', 'Laos',
                'Liberia', 'Libya', 'Malaysia', 'Mali', 'Malta', 'Mexico',
                'Mongolia', 'Morocco', 'Mozambique', 'Namibia', 'Nepal',
                'Netherlands', 'New Zealand', 'Nigeria', 'North Korea',
                'Norway', 'Pacific Islands', 'Pakistan', 'Panama', 
                'Papua New Guinea', 'Peru', 'Philippines', 'Poland', 'Portugal'
                'Puerto Rico', 'Qatar', 'Romania', 'Russia', 'Rwanda',
                'Saudi Arabia', 'Singapore', 'Slovenia', 'Solomon Islands',
                'South Africa', 'South Korea', 'South Sudan', 'Spain', 
                'Sri Lanka', 'Sudan', 'Swaziland', 'Sweden', 'Switzerland',
                'Syria', 'Tajikistan', 'Tanzania', 'Thailand', 'Tunisia',
                'Turkey', 'Turkmenistan', 'Uganda', 'Ukraine', 'United Arab Emirates',
                'United States', 'Uzbekistan', 'Venezuela', 'Vietnam',
                'Virgin Islands', 'Yemen', 'Zambia', 'Zimbabwe', 'Others']

    if login_session['user_id'] != editedItem.user_id:
        if isAdminUser() == False :
            flash('You are not authorized to edit items to this category. '
                  'You can only edit the items created by you.')
            return redirect(url_for('showCategoryItems', category_id=category_id))
        else:
            flash('You logged in as an Admin user')
#        return "<script>function myFunction() {alert('You are not authorized
#    to edit items to this Category. Please create your own Category in order
#    to edit items.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        try:
            this_user= session.query(User).filter_by(id=login_session['user_id']).one()
        except :
            session.rollback()
            return render_template('error.html')
        if 'name' in request.form:
            editedItem.name = Filter(request.form['name'], "???").clean()
        if  'description' in request.form:
            editedItem.description = Filter(request.form['description'],
                                            "???").clean()
        if  'price' in request.form:
            editedItem.price = Filter(request.form['price'], "???").clean()
        if  'your_state' in request.form:
            editedItem.state = request.form['your_state']
        if  'category_id' in request.form:
            editedItem.category_id = request.form['category_id']
        if  'method' in request.form:
            editedItem.method = request.form['method']
        if  'days' in request.form:
            editedItem.duration_days = request.form['days']
        if  'month' in request.form:
            editedItem.month = request.form['month']
        if  'place_state' in request.form:
            editedItem.place_state = request.form['place_state']
        if  'place_country' in request.form:
            editedItem.place_country = request.form['place_country']
        if  'excelfile' in request.files:
            excelfile = request.files['excelfile']
            if request.files['excelfile'].filename != '':
                delete_folder("excel", editedItem.id) 
                save_excel_to_S3(item_id=editedItem.id, folder_name="excel", excelfile=excelfile)
            #    ID=str(editedItem.id)
            #    UPLOAD_FOLDER= './static/excel'
            #    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
            #    UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
            #    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
            #    if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
            #        excel_names = os.listdir(UPLOAD_FOLDER)
            #        excel_length= len(excel_names)
            #        if(excel_length >0):
            #            for f in excel_names:
            #                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
                    
            #    if not os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'])):
            #        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER']))
            #    excelname = secure_filename(excelfile.filename)
            #    excelfile.save(os.path.join(app.config['UPLOAD_FOLDER'], excelname))

        if  'photos' in request.files:
            image_f = request.files.getlist('photos')[0].filename
            if image_f !='':
                delete_folder("images", editedItem.id)   
                save_images_to_S3(item_id=editedItem.id, folder_name="images", file_list=request.files.getlist('photos'))
                #    ID=str(editedItem.id)
                #    UPLOAD_FOLDER = './static/images'
                #    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
                #    UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
                #    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
                #    if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
                #        image_names = os.listdir(UPLOAD_FOLDER)
                #        img_length= len(image_names)
                #        if(img_length >0):
                #            for f in image_names:
                #                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
                    
                #    if not os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'])):
                #        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER']))
                    
                                   
                #    for f in request.files.getlist('photos'):
                #        baseheight = 400
                #        img = Image.open(f)
        #                    hpercent = (baseheight / float(img.size[1]))
        #                    wsize = int((float(img.size[0]) * float(hpercent)))
        #                    img = img.resize((wsize, baseheight), PIL.Image.ANTIALIAS)
                #        basewidth = 533
                #        img = img.resize((basewidth, baseheight), PIL.Image.ANTIALIAS)
                #        img.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))    

        editedItem.date = datetime.datetime.now()
        session.add(editedItem)
        try:
            session.commit()
            flash('Item " %s " Successfully Edited' % editedItem.name)
        except:
            session.rollback()
            return render_template('error.html')      
        return redirect(url_for('showItem', category_id=category_id, item_id= item_id))
    else:
        return render_template('edititem.html', category_id=category_id,
                               item_id=item_id, item=editedItem,
                               categorys=categorys, category=category,states=states, months=months, countrys=countrys, file_name=file_name)


# Delete an item
@app.route('/category/<int:category_id>/item/<int:item_id>/delete',
           methods=['GET', 'POST'])
@login_required
def deleteItem(category_id, item_id):
    #   if 'username' not in login_session:
    #       return redirect('/login')
    try:
        category = session.query(Category).filter_by(id=category_id).one()
        itemToDelete = session.query(Item).filter_by(id=item_id).one()
    except :
        session.rollback()
        return render_template('error.html')
#    this_user= session.query(User).filter_by(id=login_session['user_id']).one()
#    admin_id = session.query(Admin).filter_by(email=this_user.email)
    if (login_session['user_id'] != itemToDelete.user_id):
        if isAdminUser() == False:
            flash('You are not authorized to delete this item. '
                  'You can only delete the items created by you')
            return redirect(url_for('showCategoryItems', category_id=category_id))
        else:
            flash('You logged in as an Admin user')
#           return "<script>function myFunction() {alert('You are not authorized
#           to delete this item.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        #remove pictures
        delete_folder("images", itemToDelete.id)
 #       ID=str(itemToDelete.id)
 #       UPLOAD_FOLDER = './static/images'
 #       app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
 #       UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
 #       app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
 #       if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
 #           image_names = os.listdir(UPLOAD_FOLDER)
 #           img_length= len(image_names)
 #           if(img_length >0):
 #               for f in image_names:
 #                   os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
 #           os.rmdir(os.path.join(UPLOAD_FOLDER))
        



        #remove excel
        delete_folder("excel", itemToDelete.id)
#        ID=str(itemToDelete.id)  
#        UPLOAD_FOLDER = './static/excel'
#        app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#        UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
#        app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#        if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
#            excel_names = os.listdir(UPLOAD_FOLDER)
#            excel_length= len(excel_names)
#            if(excel_length >0):
#                for f in excel_names:
#                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
#            os.rmdir(os.path.join(UPLOAD_FOLDER))

        session.delete(itemToDelete)        
        try:
            session.commit()
            flash('Item " %s " Successfully Deleted from Category " %s " ' %
              (itemToDelete.name, category.name))
        except:
            session.rollback()
            return render_template('error.html')
        return redirect(url_for('showCategoryItems', category_id=category_id))
    else:
        return render_template('deleteitem.html', item=itemToDelete, category_id=category_id)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
#            del login_session['gplus_id']
#            del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
            del login_session['username']
            del login_session['email']
            del login_session['picture']
            del login_session['user_id']
            del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCategorys'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCategorys'))
        

# Show an item with its id
@app.route('/item/<int:item_id>',
           methods=['GET', 'POST'])
@app.route('/item/<int:item_id>/show',
           methods=['GET', 'POST'])
def showItemByID(item_id):
    try:
        item= session.query(Item).filter_by(id=item_id).one()
    except :
        session.rollback()
        return render_template('error.html')
    return redirect(url_for('showItem', category_id=item.category_id, item_id=item.id))


# Show an item 
@app.route('/category/<int:category_id>/item/<int:item_id>',
           methods=['GET', 'POST'])
@app.route('/category/<int:category_id>/item/<int:item_id>/show',
           methods=['GET', 'POST'])
def showItem(category_id, item_id):
    try:
        editedItem = session.query(Item).filter_by(id=item_id).one()
        categorys = session.query(Category).order_by(asc(Category.name))
        category = session.query(Category).filter_by(id=category_id).one()
        category_creator = getUserInfo(category.user_id)
        creator = getUserInfo(editedItem.user_id)
        items = session.query(Item).filter_by(
            category_id=category_id).all()
        counts = session.query(func.count(Item.id)).filter_by(
            category_id=category_id).scalar()
        comments_counts = session.query(func.count(Comments.id)).filter_by(
            category_id=category_id, item_id=item_id).scalar()

        comments = session.query(Comments).filter_by(category_id=category_id, item_id=item_id).order_by(desc(Comments.date))
    except:
        session.rollback()
        raise
        return render_template('error.html')
    # read in Excel
#    ID=str(editedItem.id)
#    UPLOAD_FOLDER= './static/excel'
#    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#    UPLOAD_FOLDER_1 = os.path.join(app.config['UPLOAD_FOLDER'], ID)
#    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER_1
#    if os.path.isdir(os.path.join(UPLOAD_FOLDER_1)):
#        excel_names = os.listdir(UPLOAD_FOLDER_1)
#        if len(excel_names) >0:
#            data = pd.read_excel(os.path.join(app.config['UPLOAD_FOLDER'],excel_names[0]))
#        else:
#            data=None
#    else:
#        data=None
#        excel_names= None

    excel_names, data =  get_excel_data_for_item (item_id=editedItem.id)

    if data is not None:    
        print ("Excel rows number: ", len(data.index))
        if len(data.columns)> 8:
            data= data.drop(data.columns[8:len(data.columns)], axis=1)
        if len(data.index)> 100:
            data= data.drop(data.index[100:len(data.index)])

        pd.set_option('display.max_colwidth', -1)
        pd.set_option('display.max_rows', 150)
        pd.set_option('display.max_columns', 20)

        if 'Date' in data.columns:
            for i in range(0, len(data['Date'])):
                if isinstance(data['Date'][i], datetime.datetime):
         #           temp = str(data['Date'][i].month)+"/"+ str(data['Date'][i].day)+"/"+ str(data['Date'][i].year)
         #           data['Date'][i]= temp
                    temp =  data['Date'][i]
                    try:
                        data['Date'][i] = datetime.datetime.strptime(data['Date'][i], "%m/%d/%Y")
      #                  data['Date'][i].strftime("%B %d, %Y")
                    except:
                         data['Date'][i] = temp

    #    data.set_index(['Name'], inplace=True)
        data.index.name=None
    #    females = data.loc[data.Gender=='f']
    #    males = data.loc[data.Gender=='m']
        # replacing nan cells with blank for panda sheet
        females = data.fillna("")
        tables=[females.to_html(classes='female', index=False)]
#    females.to_excel('output.xlsx')
    else: 
        females = None
        tables = None


    try:
        try:
            pp_total = session.query(VisitorVoting).filter_by(
                category_id=category.id, item_id=editedItem.id,
                like_counts=1).count()
        except :
            pp_total = 0
    except NoResultFound:
        pp_total = 0
        nn_total = 0
    else:
        try:
            nn_total = session.query(VisitorVoting).filter_by(
                category_id=category.id, item_id=editedItem.id,
                dislike_counts=1).count()
            pp_total = session.query(VisitorVoting).filter_by(
                category_id=category.id, item_id=editedItem.id,
                like_counts=1).count()
        except :
            nn_total = 0
            pp_total = 0 
    if 'username' not in login_session:
        pp = 0
        nn = 0
    else:
        try:
            voting_record = session.query(VisitorVoting).filter_by(
                user_id=login_session['user_id'], category_id=category.id,
                item_id=editedItem.id).one()
        except NoResultFound:
            total_votes = 0
            pp = 0
            nn = 0
        else:
            total_votes = voting_record.like_counts
            + voting_record.dislike_counts
            pp = voting_record.like_counts
            nn = voting_record.dislike_counts


#get image data
#    ID=str(item_id)
#    UPLOAD_FOLDER = './static/images'
#    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#    UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
#    if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
#        image_names = os.listdir(UPLOAD_FOLDER)
#        image_names.sort()
#        img_length= len(image_names)
#    else:
#        image_names=None
#        img_length =0 
#        flash("No gallery for this item_id of %s" %item_id)

    #get image data for an item
    img_length, image_names = get_image_data_for_item(item_id=item_id)

    if request.method == 'POST':
        if 'username' not in login_session:
            return redirect(url_for('showLogin', next=request.url))
#            return redirect('/login')
        if(total_votes <= 0):
            if request.form['vote'] == 'like':
                like_c = 1
                dislike_c = 0
                pp = 1
                nn = 0
            elif request.form['vote'] == 'dislike':
                like_c = 0
                dislike_c = 1
                pp = 0
                nn = 1
            else:
                like_c = 0
                dislike_c = 0
                pp = 0
                nn = 0

            newVoting = VisitorVoting(user_id=login_session['user_id'],
                                      date=datetime.datetime.now(),
                                      like_counts=like_c,
                                      dislike_counts=dislike_c,
                                      category_id=category.id,
                                      item_id=editedItem.id)
            session.add(newVoting)
            try:
                session.commit()
                flash('Your rating to this item was recorded. Thank you.')
            except:
                session.rollback()
                raise
                return render_template('error.html')
            try:
                nn_total = session.query(VisitorVoting).filter_by(
                    category_id=category.id, item_id=editedItem.id,
                    dislike_counts=1).count()
                pp_total = session.query(VisitorVoting).filter_by(
                    category_id=category.id, item_id=editedItem.id,
                    like_counts=1).count()
            except :
                nn_total = 0
                pp_total = 0    
            if 'username' not in login_session:
                return render_template('publicshowitem.html', items=items,
                                       category=category, creator=creator,
                                       category_creator=category_creator,
                                       categorys=categorys,
                                       counts=counts, editedItem=editedItem,
                                       pp=pp, nn=nn, pp_total=pp_total,
                                       nn_total=nn_total,
                                       tables=tables,
                                       comments=comments, excel_names=excel_names,
                                       comments_counts=comments_counts, 
                                       image_names=image_names, item_id=item_id, img_length=img_length)
            else:
                if creator.id != login_session['user_id']:
                    if isAdminUser()== False:
                        return render_template('publicshowitem.html', items=items,
                                                category=category, creator=creator,
                                                category_creator=category_creator,
                                                categorys=categorys,
                                                counts=counts, editedItem=editedItem,
                                                pp=pp, nn=nn, pp_total=pp_total,
                                                nn_total=nn_total,
                                                tables=tables,
                                                comments=comments, excel_names=excel_names,
                                                comments_counts=comments_counts, 
                                                image_names=image_names, item_id=item_id, img_length=img_length)
                return render_template('showitem.html', items=items,
                                       category=category, creator=creator,
                                       category_creator=category_creator,
                                       categorys=categorys, counts=counts,
                                       editedItem=editedItem, pp=pp, nn=nn,
                                       pp_total=pp_total, nn_total=nn_total,
                                       tables=tables,
                                       comments=comments, excel_names=excel_names,
                                       comments_counts=comments_counts,
                                       image_names=image_names, item_id=item_id, img_length=img_length)

        else:
            if pp == 1:
                flash('You already gave like-rating to this item. Each user '
                      'is allowed to vote for each item only once. Thank you')
            else:
                flash('You already gave dislike-rating to this item. Each '
                      'user is allowed to vote for each item only once. '
                      'Thank you')
            if 'username' not in login_session:
                return render_template('publicshowitem.html', items=items,
                                       category=category, creator=creator,
                                       category_creator=category_creator,
                                       categorys=categorys,
                                       counts=counts, editedItem=editedItem,
                                       pp=pp, nn=nn, pp_total=pp_total,
                                       nn_total=nn_total,
                                       tables=tables,
                                       comments=comments, excel_names=excel_names,
                                       comments_counts=comments_counts,
                                       image_names=image_names, item_id=item_id, img_length=img_length)
            else:
                if creator.id != login_session['user_id']:
                    if isAdminUser()== False:
                        return render_template('publicshowitem.html', items=items,
                                                category=category, creator=creator,
                                                category_creator=category_creator,
                                                categorys=categorys,
                                                counts=counts, editedItem=editedItem,
                                                pp=pp, nn=nn, pp_total=pp_total,
                                                nn_total=nn_total,
                                                tables=tables,
                                                comments=comments, excel_names=excel_names,
                                                comments_counts=comments_counts,
                                                image_names=image_names, item_id=item_id, img_length=img_length)
                return render_template('showitem.html', items=items,
                                       category=category, creator=creator,
                                       category_creator=category_creator,
                                       categorys=categorys, counts=counts,
                                       editedItem=editedItem, pp=pp, nn=nn,
                                       pp_total=pp_total, nn_total=nn_total,
                                       tables=tables,
                                       comments=comments, excel_names=excel_names,
                                       comments_counts=comments_counts,
                                       image_names=image_names, item_id=item_id, img_length=img_length)
    else:
        if 'username' not in login_session:
            return render_template('publicshowitem.html', items=items,
                                    category=category, creator=creator,
                                    category_creator=category_creator,
                                    categorys=categorys,
                                    counts=counts, editedItem=editedItem,
                                    pp=pp, nn=nn, pp_total=pp_total,
                                    nn_total=nn_total, tables=tables,
                                    comments=comments, excel_names=excel_names,
                                    comments_counts=comments_counts,
                                    image_names=image_names, item_id=item_id, img_length=img_length)
        else:
            if creator.id != login_session['user_id']:
                if isAdminUser()== False:
                    return render_template('publicshowitem.html', items=items,
                                            category=category, creator=creator,
                                            category_creator=category_creator,
                                            categorys=categorys,
                                            counts=counts, editedItem=editedItem,
                                            pp=pp, nn=nn, pp_total=pp_total,
                                            nn_total=nn_total, tables=tables,
                                            comments=comments, excel_names=excel_names,
                                            comments_counts=comments_counts,
                                            image_names=image_names, item_id=item_id, img_length=img_length)
            return render_template('showitem.html', items=items,
                                    category=category, creator=creator,
                                    category_creator=category_creator,
                                    categorys=categorys, counts=counts,
                                    editedItem=editedItem, pp=pp, nn=nn,
                                    pp_total=pp_total, nn_total=nn_total,
                                    tables=tables,
                                    comments=comments, excel_names=excel_names,
                                    comments_counts=comments_counts,
                                    image_names=image_names, item_id=item_id, img_length=img_length)

# Create a new comment
@app.route('/category/<int:category_id>/item/<int:item_id>/comment/new', methods=['GET', 'POST'])
@login_required
def newComment(category_id, item_id):
    try:
        this_user= session.query(User).filter_by(id=login_session['user_id']).one()
    except :
        session.rollback()
        return render_template('error.html')
    if request.method == 'POST':
        newComment = Comments(
            user_comments=Filter(request.form['comments'], "???").clean(),
            date=datetime.datetime.now(),
            user_id=login_session['user_id'], user_name=this_user.name,
            category_id=category_id, item_id=item_id)
        session.add(newComment)
        try:
            session.commit()
            flash('New Comments about " %s " Successfully Created' % item_id)
        except:
            session.rollback()
            return render_template('error.html')
        return redirect(url_for('showItem', category_id=category_id, item_id=item_id))
    else:
        return render_template('commenting.html', category_id=category_id, item_id=item_id)

#Edit a comment
@app.route('/category/<int:category_id>/item/<int:item_id>/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
def editComment(category_id, item_id, comment_id):
    try:
        editedComment = session.query(
            Comments).filter_by(id=comment_id, category_id=category_id, item_id=item_id ).one()
    except :
        session.rollback()
        return render_template('error.html')
    if editedComment.user_id != login_session['user_id']:
        if (isAdminUser()== False):
            flash('You are not authorized to edit this Comment.'
                'You can only edit your own Comment.')
            return redirect(url_for('showItem', category_id=category_id, item_id=item_id))
        else:
            flash('You logged in as an Admin user')
    #  return "<script>function myFunction() {alert('You are not authorized"
    #   " to edit this Category. Please create your own Category in order "
    #   "to edit.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        editedComment.user_comments = Filter(request.form['comment'], "???").clean()
        session.add(editedComment)
        try:
            session.commit()
            flash('Comment by " %s " Successfully Edited' % editedComment.user_name)
        except:
            session.rollback()
            return render_template('error.html')
        return redirect(url_for('showItem', category_id=category_id, item_id=item_id))
    else:
        return render_template('editComment.html', editedComment=editedComment)

# Delete comment
@app.route('/category/<int:category_id>/item/<int:item_id>/comment/<int:comment_id>/delete', methods=['GET', 'POST'])
@login_required
def deleteComment(category_id, item_id, comment_id):
    #   if 'username' not in login_session:
    #       return redirect('/login')
    try:
        CommentToDelete = session.query(
            Comments).filter_by(id=comment_id, category_id=category_id, item_id=item_id ).one()
    except :
        session.rollback()
        return render_template('error.html')
#    this_user= session.query(User).filter_by(id=login_session['user_id']).one()
#    admin_id = session.query(Admin).filter_by(email=this_user.email)
    if (login_session['user_id'] != CommentToDelete.user_id):
        if isAdminUser() == False:
            flash('You are not authorized to delete this comment. '
                  'You can only delete the comment created by you')
            return redirect(url_for('showItem', category_id=category_id, item_id=item_id))
        else:
            flash('You logged in as an Admin user')
#           return "<script>function myFunction() {alert('You are not authorized
#           to delete this item.');}</script><body onload='myFunction()'>"
    session.delete(CommentToDelete)
    try:
        session.commit()
        flash('Comment by " %s " Successfully Deleted from Item " %s " ' %
         (CommentToDelete.user_name, CommentToDelete.item_id))
    except:
        session.rollback()
        return render_template('error.html')
    return redirect(url_for('showItem', category_id=category_id, item_id=item_id))
 

@app.route('/contact_us/')
def contact_us():
    return render_template('contact_us.html')

@app.route('/policy/')
def policy():
    return render_template('policy.html')

@app.route('/trending/')
def trending():
    try:
        top_items = session.query(VisitorVoting.item_id, Item.id.label('id'), Item.category_id, Item.name, func.sum(VisitorVoting.like_counts).label('total_counts'), User.name, Category.name, Item.date).filter(VisitorVoting.item_id == Item.id, Item.user_id==User.id, Item.category_id==Category.id, Item.date> datetime.date(2017, 12,1)). group_by(
            VisitorVoting.item_id).order_by(desc('total_counts')).order_by(desc(Item.date)).limit(16)
    except :
        session.rollback()
        return render_template('error.html')
#    pic_files=[]
#    for item in top_items:
#        ID=str(item.id)
#        UPLOAD_FOLDER = './static/images'
#        app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#        UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
#        if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
#            image_names = os.listdir(UPLOAD_FOLDER)
#            pic_files.append(image_names[0]) 
#        else:
#            pic_files.append(None)
    pic_length, pic_files, pic_items = get_1st_image_for_items_including_none_image(items=top_items)
    try:
        top_users = session.query(User.name, func.count(Item.id).label('total_posts'), User.picture, func.sum(VisitorVoting.like_counts), func.sum(VisitorVoting.dislike_counts) ).filter(User.id==Item.user_id, VisitorVoting.item_id==Item.id, Item.date> datetime.date(2017, 12,1)).group_by(Item.user_id).order_by(desc('total_posts')).limit(10)
    except :
        session.rollback()
        return render_template('error.html')
    for user in top_users:
        print(user[0], user[1], user[2], user[3])
#    for item in top_items:
#        print (item[0], item[1], item[2], item[3])
    try:
        top_contributors = session.query(User.name, func.count(Item.id).label('total_posts'), User.picture ).filter(User.id==Item.user_id, Item.date> datetime.date(2017, 12,1)).group_by(Item.user_id).order_by(desc('total_posts')).limit(10)
    except :
        session.rollback()
        return render_template('error.html')
    return render_template('trendings.html', top_items_pic=zip(top_items,pic_files), top_users=top_users, top_contributors=top_contributors)

@app.route('/search/', methods=['GET', 'POST'])
def search():
    try:
        categorys = session.query(Category).order_by(asc(Category.name))
    except :
        session.rollback()
        return render_template('error.html')
    states = ['ALABAMA', 'ALASKA', 'ARIZONA', 'ARKANSAS', 'CALIFORNIA',
              'COLORADO', 'CONNECTICUT', 'DELAWARE', 'FLORIDA', 'GEORGIA',
              'HAWAII', 'IDAHO', 'ILLINOIS', 'INDIANA', 'IOWA', 'KANSAS',
              'KENTUCKY', 'LOUISIANA', 'MAINE', 'MARYLAND', 'MASSACHUSETTS',
              'MICHIGAN', 'MINNESOTA', 'MISSISSIPPI', 'MISSOURI', 'MONTANA',
              'NEBRASKA', 'NEVADA', 'NEW HAMPSHIRE', 'NEW JERSEY',
              'NEW MEXICO', 'NEW YORK', 'NORTH CAROLINA', 'NORTH DAKOTA',
              'OHIO', 'OKLAHOMA', 'OREGON', 'PENNSYLVANIA', 'RHODE ISLAND',
              'SOUTH CAROLINA', 'SOUTH DAKOTA', 'TENNESSEE', 'TEXAS', 'UTAH',
              'VERMONT', 'VIRGINIA', 'WASHINGTON', 'WEST VIRGINIA',
              'WISCONSIN', 'WYOMING', 'GUAM', 'PUERTO RICO', 'VIRGIN ISLANDS', 
              'Others outside US']
    months = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
              'August', 'September', 'October', 'November', 'December']

    methods = ['Air', 'Drive', 'Boat', 'Mixed']

    countrys = ['Afghanistan', 'Algeria', 'Angola', 'Argentina', 'Armenia', 'Australia', 
                'Austria', 'Azerbaijan', 'Bahamas', 'Bahrain', 'Bangladesh',
                'Belgium', 'Bolivia', 'Brazil','Cambodia', 'Cameroon', 'Canada',
                'Central African Republic', 'Chad', 'Chile', 'China', 'Colombia',
                'Congo', 'Costa Rica', 'Cuba', 'Cyprus', 'Republic of Congo',
                'Denmark', 'Dominican Republic', 'Dominica', 'Ecuador', 'Egypt',
                'El Salvador', 'Ethiopia', 'Fiji', 'Finland', 'France', 'Georgia',
                'Germany', 'Ghana', 'Great Britain', 'Greece', 'Guadeloupe',
                'Haiti' ,'Honduras', 'Hungary', 'Iceland', 'India', 'Indonesia', 
                'Iran', 'Iraq', 'Israel', 'Italy', 'Ivory Coast', 'Jamaica',
                'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kuwait', 'Laos',
                'Liberia', 'Libya', 'Malaysia', 'Mali', 'Malta', 'Mexico',
                'Mongolia', 'Morocco', 'Mozambique', 'Namibia', 'Nepal',
                'Netherlands', 'New Zealand', 'Nigeria', 'North Korea',
                'Norway', 'Pacific Islands', 'Pakistan', 'Panama', 
                'Papua New Guinea', 'Peru', 'Philippines', 'Poland', 'Portugal'
                'Puerto Rico', 'Qatar', 'Romania', 'Russia', 'Rwanda',
                'Saudi Arabia', 'Singapore', 'Slovenia', 'Solomon Islands',
                'South Africa', 'South Korea', 'South Sudan', 'Spain', 
                'Sri Lanka', 'Sudan', 'Swaziland', 'Sweden', 'Switzerland',
                'Syria', 'Tajikistan', 'Tanzania', 'Thailand', 'Tunisia',
                'Turkey', 'Turkmenistan', 'Uganda', 'Ukraine', 'United Arab Emirates',
                'United States', 'Uzbekistan', 'Venezuela', 'Vietnam',
                'Virgin Islands', 'Yemen', 'Zambia', 'Zimbabwe', 'Others']

    search_criteria ='Search Criteria you selected: '
    if request.method == 'POST':
        if request.form['name'] == '':
            item_name = ''
        else:
            item_name = request.form['name']
            search_criteria = search_criteria + ' Item name: '+item_name+'; '
        if request.form['price'] == '':
            item_price = 0
        else:
            item_price = request.form['price']
            search_criteria = search_criteria + ' Item budguet: $'+item_price+'; '
        if request.form['price_up_to'] == '':
            item_price_up_to = 10000000000
        else:
            item_price_up_to = request.form['price_up_to']
            search_criteria = search_criteria + ' Item budget up to: $'+item_price_up_to+'; '
        if int(item_price) > int(item_price_up_to):
            temp_price = int(item_price)
            item_price = int(item_price_up_to)
            item_price_up_to = temp_price
            flash("Budget value should be less than budget up to value, switched value for you in the search")
        print ("item price: ", item_price, " item price up to: ", item_price_up_to)
        if request.form['your_state'] == '':
            item_state = ''
        else:
            item_state = request.form['your_state']
            search_criteria = search_criteria + ' Item location:'+item_state+'; '
        if request.form['method'] == '':
            item_method = ''
        else:
            item_method = request.form['method']
            search_criteria = search_criteria + ' Travel method:'+item_method+'; '
        if request.form['month'] == '':
            item_month = ''
        else:
            item_month = request.form['month']
            search_criteria = search_criteria + ' Travel month:'+item_month+'; '
        if request.form['days'] == '':
            item_days = 1
        else:
            item_days = request.form['days']
            search_criteria = search_criteria + ' Trip days:'+item_days+'; '
        if request.form['days_up_to'] == '':
            item_days_up_to = 100000000000
        else:
            item_days_up_to = request.form['days_up_to']
            search_criteria = search_criteria + ' Trip days up to :'+item_days_up_to+'; '
        if int(item_days) > int(item_days_up_to):
            temp_days = int(item_days)
            item_days = int(item_days_up_to)
            item_days_up_to = temp_days
            flash("Days value should be less than days up to value, switched value for you in the search")
        print ("item days: ", item_days, " item days up to: ", item_days_up_to)
        if request.form['place_state'] == '':
            place_state = ''
        else:
            place_state = request.form['place_state']
            search_criteria = search_criteria + ' Author location :'+place_state+'; '
        if request.form['place_country'] == '':
            place_country = ''
        else:
            place_country = request.form['place_country']
            search_criteria = search_criteria + ' Item location country :'+place_country+'; '
        if request.form['author'] == '':
            item_author_name = ''
        else:
            item_author_name = request.form['author']
            search_criteria = search_criteria + ' Item author :'+item_author_name+'; '
        a='%'
        str_name= a+item_name+a
        a='%'
        str_place_state= a+place_state+a
        str_item_state = a+item_state+a
        str_item_method= a+item_method +a
        str_item_month = a+ item_month +a
        str_place_country = a + place_country +a
        str_item_author_name= a + item_author_name +a 
        try:
            searchResult = session.query(Item.name.label('item_name'), Item.id.label('id'), Item.duration_days, Item.method, Item.price, Category.id.label('cid'), Category.name.label('cname'),Item.price, User.name)\
                .filter(Item.name.like(str_name), Item.place_state.like(str_place_state), Item.category_id==Category.id, \
                Item.state.like(str_item_state), Item.method.like(str_item_method), \
                Item.month.like(str_item_month), Item.place_country.like(str_place_country), \
                Item.user_id == User.id, User.name.like(str_item_author_name), \
                and_((Item.price >=item_price), (Item.price<=item_price_up_to)), \
                and_((Item.duration_days >=item_days), (Item.duration_days<=item_days_up_to))).\
                order_by(asc(Category.name)).order_by(desc(Item.date))
        except :
            session.rollback()
            return render_template('error.html')
#        pic_files=[]
#        for item in searchResult:
            #print ("search item: ", item.name, item.cname, item.price, item.duration_days, item.id)
#            ID=str(item.id)
#            UPLOAD_FOLDER = './static/images'
#            app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#            UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
#            if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
#                image_names = os.listdir(UPLOAD_FOLDER)
#                pic_files.append(image_names[0]) 
#            else:
#                pic_files.append(None)

        pic_length, pic_files, pic_items = get_1st_image_for_items_including_none_image(items=searchResult)

        print("pic_files in search:", pic_files)

        flash("%s" % search_criteria)
        return render_template('ShowSearchResult.html', searchResult_pics=zip(searchResult,pic_files), searchResult=searchResult)

    else:
        flash("Please fill out the search field/fields interested to you; Just leave the rest blank")
        return render_template('search.html', states=states, months=months, countrys=countrys, categorys=categorys, methods=methods)


# show user activity from user clicking the botton
@app.route('/user_activity_from_click', methods=['GET', 'POST'])
@login_required
def userActivity_fromClick():
    user_id = login_session['user_id']
    return redirect(url_for('userActivity', user_id=user_id))


# show user activity
@app.route('/user_activity/<int:user_id>', methods=['GET', 'POST'])
@login_required
def userActivity(user_id):
    if user_id != login_session['user_id']:
        if (isAdminUser()== False):
            flash('You are not authorized to see this user information.'
                'You can only view your own user information.')
            return redirect(url_for('showCategorys'))
        else:
            flash('You logged in as an Admin user to view other user activity')

    this_user = getUserInfo(user_id)
    items_count=0
    pic_files=[]
    try:
        items = session.query(Item).filter(Item.user_id==user_id).order_by(desc(Item.date)).all()
        items_count = len(items)
        pic_length, pic_files, pic_items = get_1st_image_for_items_including_none_image(items=items)
#        for item in items:
#            ID=str(item.id)
#            UPLOAD_FOLDER = './static/images'
#            app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#            UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
#            if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
#                image_names = os.listdir(UPLOAD_FOLDER)
#                pic_files.append(image_names[0]) 
#            else:
#                pic_files.append(None)
    except:
        items = None
        items_count =0
        pic_length =0
        pic_files = None
        pic_item = None
    
#    print ("items_count:", items_count)
    
    try:
        comments = session.query(Comments.user_comments.label('user_comments'), Comments.category_id.label('category_id'), Comments.item_id.label('item_id'), Comments.id.label('id'), Item.name.label('name'), Comments.date.label('date')).filter(Comments.user_id==user_id, Comments.item_id==Item.id).order_by(desc(Comments.date)).all()
        comments_count = len(comments)
    except :
        comments = None
        comments_count = 0
#    print ("comments_count:", comments_count)
    
    liked_items_count=0
    liked_pic_files=[]
    try:
        liked_items =session.query(Item).filter(Item.id==VisitorVoting.item_id, VisitorVoting.user_id==user_id, VisitorVoting.like_counts>0).order_by(desc(VisitorVoting.date)).all()
        liked_items_count = len(liked_items)
        liked_pic_length, liked_pic_files, liked_pic_items = get_1st_image_for_items_including_none_image(items=liked_items)
#        for item in liked_items:
#            ID=str(item.id)
#            UPLOAD_FOLDER = './static/images'
#            app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#            UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
#            if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
#                image_names = os.listdir(UPLOAD_FOLDER)
#                liked_pic_files.append(image_names[0]) 
#            else:
#                liked_pic_files.append(None)
    except:
        liked_items = None

    
#    print ("liked_items_count:", liked_items_count)    

    likes_got_count = 0
    try:
        likes_got= session.query(func.sum(VisitorVoting.like_counts).label('total_like_counts'), Item.name.label('name'), Item.id.label('id'), Item.category_id.label('category_id')).filter(VisitorVoting.like_counts>0, VisitorVoting.item_id==Item.id, Item.user_id==user_id).group_by(
        VisitorVoting.item_id).order_by(desc('total_like_counts')).all()
#        print("likes_got is: ", likes_got)
#        print("likes_got [0] is:", likes_got[0])
#        print("likes_got [0][0] is:", likes_got[0][0])
        if len(likes_got) <1:
            likes_got = None
        else:
            likes_got_count = len(likes_got)
    except:
#        print("likes_got: none")
        likes_got = None


    comments_got_count =0
    try:
        comments_got = session.query(Comments.id.label('id'), Comments.item_id.label('item_id'), Comments.category_id.label('category_id'), Comments.user_comments.label('user_comments'),Comments.date.label('date'), Item.name.label('name')).filter(Item.user_id==user_id, Comments.item_id==Item.id).order_by(desc(Comments.date)).all()
        comments_got_count= len(comments_got)
    except:
        comments_got = None
    print ("comments_got:", comments_got_count) 

    return render_template('userActivity.html', this_user=this_user, items_pics=zip(items,pic_files), items_count=items_count, comments=comments, comments_count=comments_count, liked_items_pic=zip(liked_items, liked_pic_files), liked_items_count=liked_items_count, likes_got=likes_got, likes_got_count=likes_got_count, comments_got=comments_got, comments_got_count=comments_got_count)



@app.route('/upload/<int:item_id>', methods=['GET', 'POST'])
@login_required
def upload(item_id):
    if request.method == 'POST':
        if 'photos' in request.files:
            if len(request.files.getlist('photos')) >16:
                flash("Maximum of 16 photos can be uploaded, please try again. Thanks.")
                return render_template('file.html')
            else:
                ID=str(item_id)
                UPLOAD_FOLDER = './static/images'
                app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
                if not os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], ID)):
                    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], ID))
                UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
                app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
                i = 0
                
                for f in request.files.getlist('photos'):
#                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], f.filename))
                    baseheight = 400
                    img = Image.open(f)
#                    hpercent = (baseheight / float(img.size[1]))
#                    wsize = int((float(img.size[0]) * float(hpercent)))
#                    img = img.resize((wsize, baseheight), PIL.Image.ANTIALIAS)
                    basewidth = 533
                    img = img.resize((basewidth, baseheight), PIL.Image.ANTIALIAS)

#                    i = i+1
#                    ext= f.filename.partition(".")[2] # to get the image file's extension like .jpg or .png
#                    new_file_name = str(item_id) + "_"+ str(i)+"."+ext
                    img.save(os.path.join(app.config['UPLOAD_FOLDER'], f.filename))               
#                file_length = os.stat('./static/uploads').st_size
                return redirect(url_for('get_gallery', item_id= item_id))
    else: 
        return render_template('file.html')

@app.route('/send_image/<int:item_id>/<filename>')
def send_image(item_id, filename):
    ID=str(item_id)
    UPLOAD_FOLDER = './static/images'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/send_excel/<int:item_id>/<filename>')
def send_excel(item_id, filename):
    ID=str(item_id)
    UPLOAD_FOLDER = './static/excel'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/gallery/<int:item_id>')
def get_gallery(item_id):
    ID=str(item_id)
    UPLOAD_FOLDER = './static/images'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    UPLOAD_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], ID)
    if os.path.isdir(os.path.join(UPLOAD_FOLDER)):
        image_names = os.listdir(UPLOAD_FOLDER)
        img_length= len(image_names)
#        short_names =[]
#        for f in image_names:
#            mname= f.partition(".")[0] # to get the main name of the image file before .jpg or .png
#            print ("mname: ", mname)
#            if (len(mname) >10):
#                short_names.append(mname[0:9])
#            else:
#                short_names.append(mname)
#        print("short_names: ", short_names)
        return render_template('gallery.html', image_names=image_names, item_id=item_id, img_length=img_length)
    else:
        flash("No gallery for this item_id of %s" %item_id)
        return redirect(url_for('showCategorys'))

@app.route('/page')
def get_page():
    return send_file('templates/progress.html')

@app.route('/sitemap')
def sitemap():
    return render_template('sitemap.html')

from flask import Response
import time
@app.route('/progress')
def progress():
    def generate():
        x = 0
        while x < 100:
            print (x)
            x = x + 10
            time.sleep(0.2)
            yield "data:" + str(x) + "\n\n"
    return Response(generate(), mimetype= 'text/event-stream')



if __name__ == '__main__':
    app.secret_key = 'AKIAJWLMQFWVS7WK6BNQ'
    app.debug = True
    app.run(host='13.58.191.212', port=80)
