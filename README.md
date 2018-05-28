# Item-Catalog
This Item Catalog project was required for my Udacity's Full Stack Development Nanodegree.
I had a travel sharing blog site that I built with Wordpress which had some limitations.  This project is my attempt to use the knowledge I learned in Full Stack class to build a replacement site, where visitors can share/manage the places they visited with others. These places were grouped into categories. 
This python application allows users to add, edit or delete items of places they visited once they logged into the application either with their Google account or Facebook account. It also enabled users to rate the places they liked. Each user can only vote once for each place. 

## Instructions to Run Project

### Set up a Google Plus Auth application.
1. go to https://console.developers.google.com/project and login with Google.
2. Create a new project
3. Select "API's and Auth-> Credentials-> Create a new OAuth client ID" from the project menu
5. Select Web Application
6. On the consent screen, type in a product name and save.
7. In Authorized javascript origins add:
    http://0.0.0.0:5000
    http://localhost:5000 
8.  Click create client ID
9.  Click download JSON and save it into the root directory of this project. 
10. Rename the JSON file "client_secrets.json". Here is how this JSON file looks like:
{"web":{"client_id":"replace_here_with_your_client_ID.apps.googleusercontent.com","project_id":"it_should_be_your_project_ID,"auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://accounts.google.com/o/oauth2/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_secret":"Here_should_be_your_Client_secrete","redirect_uris":["http://localhost:5000","http://localhost:5000/login","http://localhost:5000/gconnect"],"javascript_origins":["http://localhost:5000"]}}

### Set up a Facebook LAuth application.
 1. Go to https://developers.facebook.com and login with Facebook.
 2. Create a Facebook login app.
 3. In the app specs, add http://localhost:5000/ as site URL.
 4. The Application need to change to Live Mode:
	a. Go To developers.facebook.com/apps, Select your app.
   b. On the left menu panel, you should see App Review. Click that.
   c. A page shows up with this info: Make [Your App Name] public?, Change it to Yes
5. Get app ID and app secret code to put them in client_secrets.json file which needs to be saved into the root directory of this project, here is how this json file looks like:
{
  "web": {
    "app_id": "Here put your app ID ",
    "app_secret": "here put your app secret number"
  }
}

###Setup the Database, Required Python Libraries & Server Setup
1. I was not make Vagrant up and VM working on my machine. So I had to install the python libraries on my own
2. Here are the major Python library required to run this application:
	a. Flask
	b. Sqlalchemy
	c. Oauth2client.client
	d. httplibs
	e. json
	f. requests
	g. datetime
	h. os
3. I already pre-built the database file for the site at the root directory: "categoryitemwithusers". The new added data will be saved into this database file.
4. This app runs under Python 3.6.2
5. The main application name is places.py. Here is the window's command line I use to start the server: python places.py

## Open the application webpage with a Google Chrome 
1. Now you can open in a webpage by going to either:
    http://0.0.0.0:5000
    http://localhost:5000 
2. I am working on to get this app deployed onto Google app engine

## User rules built into the application: 
 1. Category
	a. Only the category creator can edit the category name
	b. Only the category creator can delete the category when category had no place items associated to it.
 2. Place item:
	 a. Anyone can add a place item under any category once they logged in
	 b. User can only delete the items created by his/herself
	 c. User can only edit the items created by his/herself
	 d. Only logged in user can add new item, new category, update content
	 c. Each user is allow to rate (like/dislike) all the place items. But can only rate each item once and can't change it after rate was given.
	 d. When creating a new place item, all the fields need to be filled in before it can be successfully created including uploading a picture of the place
 3. Installed the profanity check for all the text information to be input by the users. The curse words will be replaced by "???"


## References: 
1. I used the sample project from Udacity as a start for my project. I made some style changes, but added a lot new capabilities: https://github.com/udacity/ud330/tree/master/Lesson4/step2
2.  I used the below code for profanity check:
https://github.com/jared-mess/profanity-filter/blob/master/profanity_filter.py
http://blueskymetrics.com/index.php/2016/06/09/py-clean-text/

