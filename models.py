# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask import request, jsonify
from flask_sqlalchemy import SQLAlchemy
import flask_sqlalchemy as fsq
from geoalchemy2 import Geometry, Geography
import geoalchemy2
from function import isInt, isFloat
from enum import Enum,IntEnum
from __init__ import app
import os, json
import datetime

db = SQLAlchemy(app)

def to_json(inst, cls):
    """
    Jsonify the sql alchemy query result.
    """
    convert = dict()
    # add your coversions for things like datetime's 
    # and what-not that aren't serializable.
    d = dict()
    for c in cls.__table__.columns:
        v = getattr(inst, c.name)
        if c.type in convert.keys() and v is not None:
            try:
                d[c.name] = convert[c.type](v)
            except:
                d[c.name] = "Error:  Failed to covert using ", str(convert[c.type])
        elif v is None:
            d[c.name] = str()
        elif "instrument_type" in str(v):
            d[c.name] = v.name
        elif "pointing_status" in str(v):
            d[c.name] = v.name
        elif "bandpass" in str(v):
            d[c.name] = v.name
        elif "geography" in str(c.type):
            #try:
            d[c.name] = str(geoalchemy2.shape.to_shape(v))
            #except:
            #   d[c.name] = v
        elif isinstance(v, (datetime.date, datetime.datetime)):
            d[c.name] = v.isoformat()
        else:
            d[c.name] = v
    return json.dumps(d)

class pointing_status(IntEnum):
    planned = 1
    completed = 2
    cancelled = 3


class instrument_type(IntEnum):
    photometric = 1
    spectroscopic = 2


class bandpass(IntEnum):
    U = 1
    B = 2
    V = 3
    R = 4
    I = 5
    J = 6
    H = 7
    K = 8
    u = 9
    g = 10
    r = 11
    i = 12
    z = 13
    UVW1 = 14
    UVW2 = 15
    UVM2 = 16
    XRT = 17
    clear = 18
    open = 19
    other = 20


class valid_mapping():
    def __init__(self):
        self.valid = False
        self.errors = []

#API Models

class users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), index=True, unique=True)
    firstname = db.Column(db.String(25))
    lastname = db.Column(db.String(25))
    datecreated = db.Column(db.Date)

class usergroups(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer)
    groupid  = db.Column(db.Integer)
    role = db.Column(db.String(25))

class groups(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25))
    datecreated = db.Column(db.Date)

class useractions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    modified_table = db.Column(db.String(25))
    modified_id = db.Column(db.Integer)
    modified_column = db.Column(db.String(25))
    prev_value = db.Column(db.String)
    new_value = db.Column(db.String)
    type = db.Column(db.String(25))
    time = db.Column(db.Date)

class instrument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instrument_name = db.Column(db.String(25))
    instrument_type = db.Column(db.Enum(instrument_type))
    footprint = db.Column(Geography('POLYGON', srid=4326))
    datecreated = db.Column(db.Date)
    submitterid = db.Column(db.Integer)

    @property
    def json(self):
        return to_json(self, self.__class__)

class pointing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(pointing_status))
    position = db.Column(Geography('POINT', srid=4326))
    galaxy_catalog = db.Column(db.Integer)
    galaxy_catalogid = db.Column(db.Integer)
    instrumentid = db.Column(db.Integer)
    depth = db.Column(db.Float)
    time = db.Column(db.Date)
    datecreated = db.Column(db.Date)
    submitterid = db.Column(db.Integer)
    pos_angle = db.Column(db.Float)
    band = db.Column(db.Enum(bandpass))

    @property
    def json(self):
        return to_json(self, self.__class__)

    def from_json(self, p, dbinsts, dbusers):
        v = valid_mapping()

        self.status = pointing_status.planned.name

        if 'position' in p:
            pos = p['position']
            if "POINT" in pos:
                self.position = p['position']
            else:
                v.errors.append("Invalid position argument. Must be decimal format ra/RA, dec/DEC, or geometry type \"POINT(RA, DEC)\"")
        else:
            if 'ra' in p or 'RA' in p:
                ra = p['ra'] if 'ra' in p else p['RA']
                if not isFloat(ra):
                    ra = None
            else:
                ra = None

            if 'dec' in p or 'DEC' in p:
                dec = p['dec'] if 'dec' in p else p['DEC']
                if not isFloat(dec):
                    dec = None
            else:
                dec = None

            if ra == None or dec == None:
                v.errors.append("Invalid position argument. Must be decimal format ra/RA, dec/DEC, or geometry type \"POINT(RA, DEC)\"")
            else:
                self.position = "POINT("+str(ra)+" "+str(dec)+")"

        if 'galaxy_catalog' in p:
            if isInt(p['galaxy_catalog']):
                self.galaxy_catalog = p['galaxy_catalog']

        if 'galaxy_catalogid' in p:
            if isInt(p['galaxy_catalogid']):    
                self.galaxy_catalogid = p['galaxy_catalogid']

        if 'instrumentid' in p:
            inst = p['instrumentid']
            validinst = False
            if isInt(inst):
                insts = [x for x in dbinsts if x.id == int(inst)]
                if len(insts) > 0:
                    self.instrumentid = inst
                    validinst = True
            else:
                insts = [x for x in dbinsts if x.instrument_name == inst]
                inames = [x.instrument_name for x in insts]
                if inst in inames:
                    instmatch = insts[0].id
                    validinst = True
                    self.instrumentid = instmatch

            if validinst is False:
                v.errors.append("Invalid instrumentid. Can be id or name of instrument")
        else:
            v.errors.append("Field instrumentid is required")

        if 'depth' in p:
            if isFloat(p['depth']):
                self.depth = p['depth']
            else:        
                v.errors.append('Invalid depth. Must be decimal')

        if 'pos_angle' in p:
            if isFloat(p['pos_angle']):
                self.depth = p['pos_angle']
            else:        
                v.errors.append('Invalid pos_angle. Must be decimal')

        if 'time' in p:
            try:
                self.time = datetime.datetime.strptime(p['time'], "%Y-%m-%dT%H:%M:%S")
            except:
                v.errors.append("Error parsing date. Should be %Y-%m-%dT%H:%M:%S format. e.g. 2019-05-01T12:00:00")
        else:
            v.errors.append("Field \"time\" is required")


        if "submitterid" in p:
            validsubmitter = False
            submitter = p['submitterid']
            if isInt(submitter):
                subs = [x for x in dbusers if x.id == submitter]
                if len(subs) > 0:
                    self.submitterid = submitter
                    validsubmitter = True
            else:
                subs = [x for x in dbusers if x.username == submitter or x.firstname + " " + x.lastname == submitter]
                if len(subs) > 0:
                    self.submitterid = [x.id for x in subs][0] 
                    validsubmitter = True

            if validsubmitter is False:
                v.errors.append("Field \"submitterid\" is required. Can be the ID, \"username\", or \"FirstName LastName\" of a valid user")
        else:
            v.errors.append("Field \"submitterid\" is required. Can be the ID, \"username\", or \"FirstName LastName\" of a valid user")

        self.datecreated = datetime.datetime.now()

        if "band" in p:
            validbandints = [int(b) for b in bandpass]
            validbandstr = [str(b.name) for b in bandpass]
            userband = p['band']
            if userband in validbandints or userband in validbandstr:
                self.band = userband
            else:
                v.errors.append("Field \"band\" is invalid")
        else:
            v.errors.append("Field \"band\" is required")

        v.valid = len(v.errors) == 0
        return v

class pointing_event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pointingid = db.Column(db.Integer)
    graceid = db.Column(db.String)

class glade_2p3(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pgc_number = db.Column(db.Integer)
    position = db.Column(Geography('POINT', srid=4326))
    gwgc_name = db.Column(db.String)
    hyperleda_name = db.Column(db.String)
    _2mass_name = db.Column(db.String)
    sdssdr12_name = db.Column(db.String)
    distance = db.Column(db.Float)
    distance_error = db.Column(db.Float)
    redshift = db.Column(db.Float)
    bmag = db.Column(db.Float)
    bmag_err = db.Column(db.Float)
    bmag_abs = db.Column(db.Float)
    jmag = db.Column(db.Float)
    jmag_err = db.Column(db.Float)
    hmag = db.Column(db.Float)
    hmag_err = db.Column(db.Float)
    kmag = db.Column(db.Float)
    kmag_err = db.Column(db.Float)
    flag1 = db.Column(db.String(1))
    flag2 = db.Column(db.Integer)
    flag3 = db.Column(db.Integer)


class gw_alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    graceid = db.Column(db.String)
    role = db.Column(db.String)
    timesent = db.Column(db.Date)
    time_of_signal = db.Column(db.Date)
    packet_type = db.Column(db.Integer)
    alert_type = db.Column(db.String)
    detectors = db.Column(db.String)
    description = db.Column(db.String)
    far = db.Column(db.Float)
    skymap_fits_url = db.Column(db.String)
    distance = db.Column(db.Float)
    distance_error = db.Column(db.Float)
    prob_bns = db.Column(db.Float)
    prob_nsbh = db.Column(db.Float)
    prob_gap = db.Column(db.Float)
    prob_bbh = db.Column(db.Float)
    prob_terrestrial = db.Column(db.Float)
    prob_hasns = db.Column(db.Float)
    prob_hasremenant = db.Column(db.Float)
    datecreated = db.Column(db.Date)