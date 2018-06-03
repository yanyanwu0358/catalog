from sqlalchemy import create_engine, DateTime, LargeBinary
from sqlalchemy.orm import sessionmaker

from database_setup import Category, Base, Item, User
import datetime

engine = create_engine('postgresql://catalog:password@localhost/categoryitemwithusers')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Robo Barista", email="tinnyTim@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User1)
session.commit()

# Menu for UrbanBurger
Category1 = Category(user_id=1, name="Urban Burger")

session.add(Category1)
session.commit()

#from PIL import Image
#img = Image.open('lake.jpg')
#menuItem2 = Item(user_id=1, name="Veggie Burger", description="Juicy grilled veggie patty with tomato mayo and lettuce",
#                     price="$7.50", category=category1, date =datetime.datetime.now(), file_name = "lake.jpg", data= img)

#f = open('lake.jpg', 'rb')
menuItem2 = Item(user_id=1, name="Veggie Burger", description="Juicy grilled veggie patty with tomato mayo and lettuce",
                     price="$7.50", category=Category1, date =datetime.datetime.now(), file_name = "lake.jpg", state ="Arizona", method="Air") #, data= f.read())
#f.close()

print (datetime.datetime.now())


session.add(menuItem2)
session.commit()

menuItem1 = Item(user_id=1, name="French Fries", description="with garlic and parmesan",
                     price="$2.99", category=Category1, date =datetime.datetime.now(), file_name = "lake.jpg", state = "New York", method="Drive")

session.add(menuItem1)
session.commit()

menuItem2 = Item(user_id=1, name="Chicken Burger", description="Juicy grilled chicken patty with tomato mayo and lettuce",
                     price="$5.50", category=Category1, date =datetime.datetime.now(), file_name = "lake.jpg", state = "UTAH", method="Mixed")

session.add(menuItem2)
session.commit()

print ("added menu items!")
