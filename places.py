from flask import Flask, render_template, request, redirect, jsonify
from flask import g, url_for, flash
from sqlalchemy import create_engine, asc, desc, DateTime, func
from sqlalchemy.orm import sessionmaker
from catalog.database_setup import Base, Category, Item, User, VisitorVoting
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
from catalog.profanity_filter import Filter
from functools import wraps

app = Flask(__name__)

current_file_path = __file__
current_file_dir = os.path.dirname(__file__)
google_file_path = os.path.join(current_file_dir, "client_secrets.json")
fb_file_path = os.path.join(current_file_dir, "fb_client_secrets.json")

CLIENT_ID = json.loads(
    open(google_file_path, 'r').read())['web']['client_id']
APPLICATION_NAME = "Places to visit Application"


# Connect to Database and create database session
engine = create_engine('postgresql://catalog:password@localhost/categoryitemwithusers')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            print("request.url= ", request.url)
            return redirect(url_for('showLogin', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


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
    return render_template('login.html', STATE=state, next=next)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data.decode("utf-8")
    print("access token received %s " % access_token)

    app_id = json.loads(open(fb_file_path, 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open(fb_file_path, 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type='\
          'fb_exchange_token&client_id=%s&client_secret='\
          '%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1].decode('utf-8')

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.11/me"
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

    url = 'https://graph.facebook.com/v2.11/me?access_token=%s&fields='\
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
    url = 'https://graph.facebook.com/v2.11/me/picture?access_token=%s&'\
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
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(google_file_path, scope='')
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
    result = json.loads(h.request(url, 'GET')[1].decode('utf-8'))
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
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
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
    flash("you are now logged in as %s" % login_session['username'])
    print("done!")
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
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
    print("rsults 1: ", result)
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
@app.route('/category/<int:category_id>/item/JSON')
def categoryItemJSON(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(
        category_id=category_id).all()
    return jsonify(Items=[i.serialize for i in items])


@app.route('/category/<int:category_id>/item/<int:item_id>/JSON')
def ItemJSON(category_id, item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(Item=item.serialize)


@app.route('/category/JSON')
def categorysJSON():
    categorys = session.query(Category).all()
    return jsonify(categorys=[r.serialize for r in categorys])


# Show all categorys
@app.route('/')
@app.route('/category/')
def showCategorys():
    categorys = session.query(Category).order_by(asc(Category.name))
    latest_items = session.query(Item).order_by(
            desc(Item.date)).limit(10).all()
    if 'username' not in login_session:
        return render_template('publicCategorys.html',
                               categorys=categorys, latest_items=latest_items)
    else:
        return render_template('categorys.html',
                               categorys=categorys, latest_items=latest_items)

# Create a new category


@app.route('/category/new/', methods=['GET', 'POST'])
@login_required
def newCategory():
    if request.method == 'POST':
        newCategory = Category(
            name=Filter(request.form['name'], "???").clean(),
            user_id=login_session['user_id'])
        session.add(newCategory)
        flash('New Category %s Successfully Created' % newCategory.name)
        session.commit()
        return redirect(url_for('showCategorys'))
    else:
        return render_template('newCategory.html')

# Edit a category


@app.route('/category/<int:category_id>/edit/', methods=['GET', 'POST'])
@login_required
def editCategory(category_id):
    #   if 'username' not in login_session:
    #       return redirect('/login')
    editedCategory = session.query(
        Category).filter_by(id=category_id).one()
    if editedCategory.user_id != login_session['user_id']:
        flash('You are not authorized to edit this Category.'
              'You can only edit your own Category.')
        return redirect(url_for('showCategoryItems', category_id=category_id))
    #  return "<script>function myFunction() {alert('You are not authorized"
    #   " to edit this Category. Please create your own Category in order "
    #   "to edit.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedCategory.name = Filter(request.form['name'], "???").clean()
            flash('Category %s Successfully Edited' % editedCategory.name)
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
    CategoryToDelete = session.query(
        Category).filter_by(id=category_id).one()
    counts = session.query(func.count(Item.id)).\
        filter_by(category_id=category_id).scalar()
    if counts > 0:
        flash('You cannot delete %s category since there were items created '
              'under it.' % CategoryToDelete.name)
        return redirect(url_for('showCategoryItems', category_id=category_id))
    if CategoryToDelete.user_id != login_session['user_id']:
        flash('You are not authorized to delete this Category. '
              'You can only delete the Category created by you.')
        return redirect(url_for('showCategoryItems', category_id=category_id))
#       return "<script>function myFunction() {alert('You are not authorized
#       to delete this Category.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(CategoryToDelete)
        flash('Category %s Successfully Deleted' % CategoryToDelete.name)
        session.commit()
        return redirect(url_for('showCategorys'))
    else:
        return render_template('deleteCategory.html',
                               category=CategoryToDelete)


# Show a category item
@app.route('/category/<int:category_id>/')
@app.route('/category/<int:category_id>/item/')
def showCategoryItems(category_id):
    categorys = session.query(Category).order_by(asc(Category.name))
    category = session.query(Category).filter_by(id=category_id).one()
    creator = getUserInfo(category.user_id)
    items = session.query(Item).filter_by(
        category_id=category_id).all()
    counts = session.query(func.count(Item.id)).filter_by(
        category_id=category_id).scalar()

    if 'username' not in login_session or creator.id !=\
            login_session['user_id']:
        return render_template('publicCategoryItems.html', items=items,
                               category=category, creator=creator,
                               categorys=categorys, counts=counts)
    else:
        return render_template('categoryItems.html', items=items,
                               category=category, creator=creator,
                               categorys=categorys, counts=counts)


# Create a new item
@app.route('/category/<int:category_id>/item/new/', methods=['GET', 'POST'])
@login_required
def newItem(category_id):
    #    if 'username' not in login_session:
    #        return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    categorys = session.query(Category).order_by(asc(Category.name))
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
              'WISCONSIN', 'WYOMING', 'GUAM', 'PUERTO RICO', 'VIRGIN ISLANDS']

    if request.method == 'POST':
        missing_fields = ''
        file = request.files['inputFile']
        if file.filename == '':
            missing_fields = missing_fields + '..Image file '
        if request.form['name'] == '':
            missing_fields = missing_fields + '..Name '
            item_name = ''
        else:
            item_name = request.form['name']
        if request.form['description'] == '':
            missing_fields = missing_fields + '..Description '
            item_des = ''
        else:
            item_des = request.form['description']
        if request.form['price'] == '':
            missing_fields = missing_fields + '..Price '
            item_price = ''
        else:
            item_price = request.form['price']
        if request.form['your_state'] == '':
            missing_fields = missing_fields + '..Your home state'
            item_state = ''
        else:
            item_state = request.form['your_state']
        if request.form['method'] == '':
            missing_fields = missing_fields + '..Method'
            item_method = ''
        else:
            item_method = request.form['method']

        print("missing_fields last =", missing_fields)
        if(missing_fields == ''):
            UPLOAD_FOLDER = './static/images'
            app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#           profane = profanity_filter.Filter(product_review, "unicorn")
#           print ("Clean Text: %s" % profane.clean())

            newItem = Item(name=Filter(request.form['name'], "???").clean(),
                           description=Filter(request.form['description'],
                           "???").clean(),
                           price=Filter(request.form['price'], "???").clean(),
                           category_id=request.form['category_id'],
                           user_id=login_session['user_id'],
                           date=datetime.datetime.now(),
                           file_name=filename, state=item_state,
                           method=item_method)  # , data=file.read())
            session.add(newItem)
            session.commit()
            flash('New Item %s Successfully Created' % (newItem.name))
            return redirect(url_for('showCategoryItems',
                                    category_id=category_id))

        else:
            flash('New item was not created.  All fields need to be filled '
                  'before clicking on Create button. Missing fields: %s.'
                  % missing_fields)
            return render_template('newitem.html', category=category,
                                   category_id=category_id,
                                   categorys=categorys, item_name=item_name,
                                   item_des=item_des, item_price=item_price,
                                   states=states, item_state=item_state,
                                   item_method=item_method)
    else:
        return render_template('newitem.html', category=category,
                               category_id=category_id, categorys=categorys,
                               item_name='', item_des='', item_price='',
                               states=states, item_state='', item_method='')

# Edit an item


@app.route('/category/<int:category_id>/item/<int:item_id>/edit',
           methods=['GET', 'POST'])
@login_required
def editItem(category_id, item_id):
    #   if 'username' not in login_session:
    #       return redirect('/login')
    editedItem = session.query(Item).filter_by(id=item_id).one()
    category = session.query(Category).filter_by(id=category_id).one()
    categorys = session.query(Category).order_by(asc(Category.name))
    if login_session['user_id'] != editedItem.user_id:
        flash('You are not authorized to edit items to this category. '
              'You can only edit the items created by you.')
        return redirect(url_for('showCategoryItems', category_id=category_id))
#        return "<script>function myFunction() {alert('You are not authorized
#    to edit items to this Category. Please create your own Category in order
#    to edit items.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = Filter(request.form['name'], "???").clean()
        if request.form['description']:
            editedItem.description = Filter(request.form['description'],
                                            "???").clean()
        if request.form['price']:
            editedItem.price = Filter(request.form['price'], "???").clean()
        if request.form['category_id']:
            editedItem.category_id = request.form['category_id']
        if request.files['inputFile']:
            file = request.files['inputFile']
            UPLOAD_FOLDER = './static/images'
            app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            editedItem.file_name = filename
        if request.form['method']:
            editedItem.method = request.form['method']

        editedItem.date = datetime.datetime.now()
        session.add(editedItem)
        session.commit()
        flash('Item %s Successfully Edited' % editedItem.name)
        return redirect(url_for('showCategoryItems', category_id=category_id))
    else:
        return render_template('edititem.html', category_id=category_id,
                               item_id=item_id, item=editedItem,
                               categorys=categorys, category=category)


# Delete an item
@app.route('/category/<int:category_id>/item/<int:item_id>/delete',
           methods=['GET', 'POST'])
@login_required
def deleteItem(category_id, item_id):
    #   if 'username' not in login_session:
    #       return redirect('/login')
    category = session.query(Category).filter_by(id=category_id).one()
    itemToDelete = session.query(Item).filter_by(id=item_id).one()
    if login_session['user_id'] != itemToDelete.user_id:
        flash('You are not authorized to delete this item. '
              'You can only delete the items created by you')
        return redirect(url_for('showCategoryItems', category_id=category_id))
#        return "<script>function myFunction() {alert('You are not authorized
#        to delete this item.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        flash('Item %s Successfully Deleted from Category %s' %
              (itemToDelete.name, category.name))
        session.commit()
        return redirect(url_for('showCategoryItems', category_id=category_id))
    else:
        return render_template('deleteItem.html', item=itemToDelete)


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


# Show an item +++++++++++++++++++++++++++++++++
@app.route('/category/<int:category_id>/item/<int:item_id>',
           methods=['GET', 'POST'])
@app.route('/category/<int:category_id>/item/<int:item_id>/show',
           methods=['GET', 'POST'])
def showItem(category_id, item_id):
    editedItem = session.query(Item).filter_by(id=item_id).one()
    categorys = session.query(Category).order_by(asc(Category.name))
    category = session.query(Category).filter_by(id=category_id).one()
    category_creator = getUserInfo(category.user_id)
    creator = getUserInfo(editedItem.user_id)
    items = session.query(Item).filter_by(
        category_id=category_id).all()
    counts = session.query(func.count(Item.id)).filter_by(
        category_id=category_id).scalar()
    print("image name: ", editedItem.file_name)

    try:
        pp_total = session.query(VisitorVoting).filter_by(
            category_id=category.id, item_id=editedItem.id,
            like_counts=1).count()
    except NoResultFound:
        pp_total = 0
        nn_total = 0
    else:
        nn_total = session.query(VisitorVoting).filter_by(
            category_id=category.id, item_id=editedItem.id,
            dislike_counts=1).count()
        pp_total = session.query(VisitorVoting).filter_by(
            category_id=category.id, item_id=editedItem.id,
            like_counts=1).count()

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
            session.commit()
            flash('Your rating to this item was recorded. Thank you.')
            nn_total = session.query(VisitorVoting).filter_by(
                category_id=category.id, item_id=editedItem.id,
                dislike_counts=1).count()
            pp_total = session.query(VisitorVoting).filter_by(
                category_id=category.id, item_id=editedItem.id,
                like_counts=1).count()
            if 'username' not in login_session or creator.id !=\
                    login_session['user_id']:
                return render_template('publicshowitem.html', items=items,
                                       category=category, creator=creator,
                                       category_creator=category_creator,
                                       categorys=categorys,
                                       counts=counts, editedItem=editedItem,
                                       pp=pp, nn=nn, pp_total=pp_total,
                                       nn_total=nn_total)
            else:
                return render_template('showitem.html', items=items,
                                       category=category, creator=creator,
                                       category_creator=category_creator,
                                       categorys=categorys, counts=counts,
                                       editedItem=editedItem, pp=pp, nn=nn,
                                       pp_total=pp_total, nn_total=nn_total)
        else:
            if pp == 1:
                flash('You already gave like-rating to this item. Each user '
                      'is allowed to vote for each item only once. Thank you')
            else:
                flash('You already gave dislike-rating to this item. Each '
                      'user is allowed to vote for each item only once. '
                      'Thank you')
            if 'username' not in login_session or creator.id !=\
                    login_session['user_id']:
                return render_template('publicshowitem.html', items=items,
                                       category=category, creator=creator,
                                       category_creator=category_creator,
                                       categorys=categorys, counts=counts,
                                       editedItem=editedItem, pp=pp, nn=nn,
                                       pp_total=pp_total, nn_total=nn_total)
            else:
                return render_template('showitem.html', items=items,
                                       category=category, creator=creator,
                                       category_creator=category_creator,
                                       categorys=categorys, counts=counts,
                                       editedItem=editedItem, pp=pp, nn=nn,
                                       pp_total=pp_total, nn_total=nn_total)
    else:
        if 'username' not in login_session or creator.id !=\
                login_session['user_id']:
            return render_template('publicshowitem.html', items=items,
                                   category=category, creator=creator,
                                   category_creator=category_creator,
                                   categorys=categorys, counts=counts,
                                   editedItem=editedItem, pp=pp, nn=nn,
                                   pp_total=pp_total, nn_total=nn_total)
        else:
            return render_template('showitem.html', items=items,
                                   category=category, creator=creator,
                                   category_creator=category_creator,
                                   categorys=categorys, counts=counts,
                                   editedItem=editedItem, pp=pp, nn=nn,
                                   pp_total=pp_total, nn_total=nn_total)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
