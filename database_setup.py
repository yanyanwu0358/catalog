from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
import datetime


Base = declarative_base()

def get_current_time():
    return datetime.datetime.now()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
# To maintain your database's integrity, implement the DELETE CASCADE.
    items = relationship('Item', cascade='all, delete-orphan')

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
        }


class Item(Base):
    __tablename__ = 'item'

    name = Column(String(100), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(800))
    price = Column(String(8))
    method = Column(String(250))
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    date = Column(DateTime, default=get_current_time,
        onupdate=get_current_time)

    file_name = Column(String(300))
    state = Column(String(14))
#    data = Column(LargeBinary())   # maybe to consider to use later.


    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'description': self.description,
            'id': self.id,
            'price': self.price,
            'method': self.method,
            'date': self.date,
        }

class VisitorVoting(Base):
    __tablename__ = 'visitor_voting'

    id = Column(Integer, primary_key=True)
    user = relationship(User)
    user_id = Column(Integer, ForeignKey('user.id'))
    date = Column(DateTime, default=get_current_time,
        onupdate=get_current_time)
    like_counts = Column(Integer)
    dislike_counts = Column(Integer)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    item_id = Column(Integer, ForeignKey('item.id'))
    item = relationship(Item)


    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'user': self.user,
            'id': self.id,
            'item': self.item_item,
        }


create_engine('postgresql://catalog:password@localhost/categoryitemwithusers')


Base.metadata.create_all(engine)
