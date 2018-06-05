from sqlalchemy import create_engine, DateTime, LargeBinary, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker

from database_setup import Category, Base, Item, User
import datetime
#from places import getUserID, getAdminID

engine = create_engine('postgresql://catalog:password@localhost/categoryitem')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
#Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()


# clear the content in the data tables
meta = Base.metadata
for table in reversed(meta.sorted_tables):
	print('Clear table %s' % table)
	session.execute(table.delete())
session.commit()
print ("deleted all tables' contents!")

#Add a column of "user_id" to the "admin" table
#engine.execute('ALTER TABLE admin ADD COLUMN user_id  Integer')
#print("added user_id")

# Add a foreign key to the admin table. 
#engine.execute ('ALTER TABLE admin ADD CONSTRAINT relationship FOREIGN KEY (user_id) REFERENCES user (id)') 
#print("added user_id as a foreign key")
