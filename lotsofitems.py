from sqlalchemy import create_engine, DateTime, LargeBinary
from sqlalchemy.orm import sessionmaker

from database_setup import Category, Base, Item, User
import datetime

engine = create_engine('sqlite:///categoryitemwithusers.db',connect_args={'check_same_thread':False})
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
User1 = User(name="YY WU", email="yanyanwu1999@gmail.com",
	             picture='https://lh3.googleusercontent.com/-M95t_dOuLBQ/AAAAAAAAAAI/AAAAAAAAACo/YdEEU7_5-YA/photo.jpg')

session.add(User1)
session.commit()

# Create category
Category1 = Category(user_id=1, name="Beaches")
session.add(Category1)
session.commit()

Category2 = Category(user_id=1, name="Cities")
session.add(Category2)
session.commit()

Category3 = Category(user_id=1, name="Cruise")
session.add(Category3)
session.commit()

Category4 = Category(user_id=1, name="Foreign Countries")
session.add(Category4)
session.commit()

Category5 = Category(user_id=1, name="National Parks")
session.add(Category5)
session.commit()

Category6 = Category(user_id=1, name="Theme Parks")
session.add(Category6)
session.commit()


menuItem2 = Item(user_id=1, name="Myrtle Beach, SC and Orange Beach, AL", description="On the first day, we drove along I-10 through Louisiana to a country road that went to Atlanta, taking about 12 hours. We stayed in a Fairfield Marriott for 1 night and ate at a place called Love’s Seafood., then drove 3 hours to Congaree National Park the next day. Be warned- mosquitoes are serious here! We stayed all day, then drove another 3 hours to our Marriott Resort & Spa. There,we ate at a nearby Benjamin’s Calabash Seafood Buffet. We stayed at our hotel for 3 nights visiting Broadway at the Beach, where we saw many big fishes in the water and also visited the Wonderworks there which had some rides. We ate at Chesapeake House and Bimini’s Seafood at Myrtle beach. Afterwards, we visited the Charleston and stayed at a Andell Inn Marriott on Kiawah Island, whic is mainly for golfing",
                     price=1250, category=Category1, date =datetime.datetime.now(), file_name = "Myrtle-Beach-Marriott-Resort-2.jpg", state ="TEXAS", method="Drive") #, data= f.read())
session.add(menuItem2)
session.commit()


menuItem1 = Item(user_id=1, name="South Padre Island", description="South Padre Island has many beautiful beaches and oceanfronts. The hotel we booked has direct access to the oceanfront. Also, the South Padre Island Birding and Nature Center was the best wetland park we visited, which had so many to see while board-walking.",
                     price=350, category=Category1, date =datetime.datetime.now(), file_name ="South_Padre_Island.jpg", state = "TEXAS", method="Drive")
session.add(menuItem1)
session.commit()


menuItem3 = Item(user_id=1, name="Port Aransas", description="Port Aransas had beautiful beaches. The best part is its Leonabelle Turnbull Birding Center which had many bird types to watch while walking on the boardwalk. The lunch place of Seafood & Spaghetti Works restaurant had water view and good food.",
                     price=40, category=Category1, date =datetime.datetime.now(),  file_name ="Port_Aransas.jpg", state = "TEXAS", method="Drive")
session.add(menuItem3)
session.commit()


Item4 = Item(user_id=1, name="San Antonio Riverwalk + Canyon Lake", description="Just park your car somewhere at the San Antonio Riverwalk, you can walk to the Alamo, take a carriage tour, then just walk along the river or take a boat tour. You can do a lot and go to places to eat without driving. Canyon Lake has a beautiful view in front of you while you were walking on dam.",
                     price=380, category=Category2, date =datetime.datetime.now(), file_name ="san_antonio.jpg", state = "TEXAS", method="Drive")
session.add(Item4)
session.commit()


Item5 = Item(user_id=1, name="Cozumel", description="Cozumel is a very busy place with markets selling various items and beautiful beaches. We booked a Carnival cruise, which was very fun onboard. We would not spend time in downtown shops if we went back again. Instead, we would be heading directly to a beach or beach park.",
                     price=2200, category=Category3, date =datetime.datetime.now(), file_name ="Cozumel-park.jpg", state = "TEXAS", method="Boat")
session.add(Item5)
session.commit()


Item6 = Item(user_id=1, name="Rome, Venice, and Naples", description="We traveled to Italy, hoping for a fun place to have a vacation. We took a flight to Venice, and then took a Alilaguna boat to Rialto, a famous bridge that survived the bombings of World War II. We explored the city by foot, walking to landmarks such as San Marcos Square and Doge’s Palace. After visiting all the available landmarks and spending a night at a hotel, we took a Trenitalia train from Venezia S. Lucia to Roma Termini, or Rome. After spending our time in Rome, we took a Trenitalia train to Napoli Centrale, or Naples. We visited the nearby island Capri via boat. We hiked around the island with breath-taking views, took a bus to a small beach and enjoyed our time there.",
                     price=6000, category=Category4, date =datetime.datetime.now(), file_name ="Vince5.jpg", state = "TEXAS", method="Air")
session.add(Item6)
session.commit()


Item7 = Item(user_id=1, name="Banff + Seattle + Vancouver", description="Banff National Park is the best area to visit in Banff region. It had very beautiful lakes like Lake Minne???a, Two Jack Lake. It also had nice valley/river view at Tunnel Mountain Trail and water fall like Bow Falls. All of these sites can be reached by driving without hiking. The sites were surrounded by nice restaurants and hotels. North Cascades National Park was 2 hours away from Seattle in the north. It has stunning green lake water surrounded by the beautiful mountains with snow on their peaks. The green color of the water came from minerals in the water that originated from the glacier on the top of the mountain.",
                     price=5700, category=Category5, date =datetime.datetime.now(), file_name ="Banff.jpg", state = "TEXAS", method="Air")
session.add(Item7)
session.commit()

Item12 = Item(user_id=1, name="Disney’s Epcot + Legoland Orlando + Tampa Beach", description="We went to theme parks and beaches in Florida. While we were at Orlando, we visited Legoland and Epcot. If you don’t much time to spare, it would be okay to only go to Epcot. Also, the beaches at Tampa are very nice and beautiful, just a little bit cold in March.",
                     price=950, category=Category6, date =datetime.datetime.now(),  file_name ="Epcot.jpg", state = "TEXAS", method="Drive")
session.add(Item12)
session.commit()


Item13 = Item(user_id=1, name="Orlando Disney Resort + Apalachicola National Forest + Ocala National Forest", description="Stayed in Disney Contemporary Resort to watched the fireworks every night in Executive Lodge with wine and deserts. Both Apalachicola & Ocala provided unique tropical forest scene for visitors.",
                     price=2500, category=Category6, date =datetime.datetime.now(), file_name ="disney-resort.jpg", state = "TEXAS", method="Drive")
session.add(Item13)
session.commit()


Item14 = Item(user_id=1, name="Miami", description="Miami is a city where you can find pretty beaches every where you go. In addition to the beautiful beaches, we loved Vizcaya Museum and Gardensm, am unique archetect with a grand style. You would need to be careful driving in Miami, where Sunpass would be required. But don't worry, even you don't have one, you can call in later to make the payment. Just be careful, not get onto an express lane without Sunpass ($25 fine each time). We took a bottom glass tour in Key West, which is just ok but should have spent more time in the town and parks there. ",
                     price=1700, category=Category2, date =datetime.datetime.now(), file_name ="Orange-beach-3.jpg", state = "TEXAS", method="Drive")
session.add(Item14)
session.commit()

print ("added menu items!")
