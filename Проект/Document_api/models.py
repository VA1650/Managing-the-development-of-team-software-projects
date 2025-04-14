from . import db
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

class Doctype(db.Model):
    __tablename__ = "Doctype"
    type = Column(String, primary_key=True, index=True)


class LegalEntities(db.Model):
    __tablename__ = "LegalEntities"
    name = Column(String, primary_key=True, index=True)
    director = Column(String)


class Ourfirm(db.Model):
    __tablename__ = "Ourfirm"
    name = Column(String, primary_key=True, index=True)
    director = Column(String)


class ReadyDoc(db.Model):
    __tablename__ = "ReadyDoc"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)
    sum = Column(Integer)
    legalEntities = Column(String, ForeignKey("LegalEntities.name"))
    signatories = Column(String)
    link = Column(String)


class DocTemp(db.Model):
    __tablename__ = "DocTemp"
    id = Column(Integer, primary_key=True, index=True)
    compName = Column(String, ForeignKey("LegalEntities.name"))
    docType = Column(String, ForeignKey("Doctype.type"))
    link = Column(String)

    legal_entity = relationship("LegalEntities", backref="templates")
    doctype = relationship("Doctype", backref="templates")


class Employees(db.Model):
    __tablename__ = "Employees"
    employee = Column(String, primary_key=True, unique=True, index=True)
    rate = Column(Integer, nullable=False)


class Users(db.Model):
    __tablename__ = "Users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, self.password)
