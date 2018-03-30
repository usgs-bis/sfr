
"""Utility functions for SFR load scripts"""

#Define functions 
import geojson
import uuid
import datetime
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.multilinestring import MultiLineString
from shapely.geometry.multipoint import MultiPoint
from shapely import wkt
import pysb
import os
import zipfile


def df_to_geojson(df, epsg, source_uri, expected_geom_type):
### Transforms geodataframe into a geojson output.  Adds two registration fields including uuid and reg_source.  Variables explained below

#pass epsg in following format = {'code':'5070'}
#geom_type = Polygon, MultiPolygon, Point, MultiPoint, Line, or MultiLine
#df is geodataframe of spatial features
#source_uri is sb uri that will house the geojson and descriptions of the file


    #Create basic JSON structure
    collection = {'type':'FeatureCollection', 'crs': {'type': 'epsg', 'properties': epsg }, 'features':[]}

    #Identify list of field names in df, this is used to populate the properties section of the structure
    field_names = (list(df.columns.values))
    field_names.remove('geometry')
    
    #For each row in dataframe, populate geometry and properties
    for row in df.itertuples():
        geom = fix_geom_type(row, expected_geom_type)

        feature = {'type':'Feature',
                   'properties':{},
                  'geometry': geom}
        for field in field_names:
            feature['properties'][field] = getattr(row, field)

        #Add registration properties
        feature['properties']['_id'] = str(uuid.uuid4())
        #feature['properties']['reg_date'] = datetime.datetime.utcnow().isoformat()
        feature['properties']['reg_source'] = source_uri

        collection['features'].append(feature)
    
    return collection


def fix_geom_type(row, expected_geom_type):
# ESRI mixes geom_types within a given file. GC2 doesn't accept geojson with mixed types.  When expecting multi features this ensures all features in a file are represented as Multi.   
    if 'Multi' not in str((row.geometry).geom_type) and expected_geom_type=='MultiPolygon':
        geom = MultiPolygon([wkt.loads(str(row.geometry))])
    elif 'Multi' not in str((row.geometry).geom_type) and expected_geom_type=='MultiLineString':
        geom = MultiLineString([wkt.loads(str(row.geometry))])
    elif 'Multi' not in str((row.geometry).geom_type) and expected_geom_type=='MultiPoint':
        geom = MultiPoint([wkt.loads(str(row.geometry))])
    else:
        geom = row.geometry
    return geom



def sfr_item_info(sb,source_sbitem,sb_tags, date):
#Creates JSON structure that can be passed to build new SFR SB item.  Currently JSON built based on source SB item, variables (e.g. sb_tags), and standard info for sfr registrants (e.g. date created)

###ROOM FOR IMPROVEMENT###
#for some reason the summary here is not updating into the created SB item... but no error is thrown
#This needs better logic and is a little incomplete
#sb = sb session (sbitem should be accessed via requests here.... right now you need to open a session which isn't needed for anything within the function)
#define date by datetime.datetime.utcnow().isoformat()
    item_info = {}

    try:
        sbitem_json = sb.get_item(source_sbitem)
        title = "Spatial Feature Registration Files for " + sbitem_json["alternateTitles"][0]
        summary = sbitem_json["alternateTitles"][0] + " data registered into the spatial feature registry. Source data is documented at " + sbitem_json['link']['url']
        weblink = {"type": "webLink","typeLabel": "Web Link","uri": sbitem_json['link']['url'],"rel": "related",
"title": "source data documentation"}
        
        item_info["title"] = title
        item_info["parentId"] = "55fafaf5e4b05d6c4e501b81"
        item_info["summary"] = summary
        item_info["tags"]= sb_tags
        date_data = [{"type": "creation", "dateString": "2018-03-29" , "label":"Creation"}]
        for date in sbitem_json["dates"]:
            if date["type"]=="beginPosition":
                date_data.append(date)
            if date["type"]=="endPosition":
                date_data.append(date)
        item_info["dates"]= date_data
        item_info["purpose"] = "These spatial data were ingested into the Spatial Feature Registry (SFR) data system within the Biological Information System."
        item_info["webLinks"] = [weblink]
        return item_info

        #Other Information that could be built in below    
        #Source data documentation, Summary, tags linked to vocab -> if source has them, url to source code that developed geojson

    except:
        #Need to better error catching and messages 
        print ('creating sb item failed')

def build_sb_tags(list_tags):
#Takes list of tags and puts them into format to help build SB item
#Should build this out to be more complex with different tag types
    sb_tags = []
    for tag in list_tags:
        sb_tags.append({"type":"Subject","name": tag})
    return sb_tags
        

def sb_login():
#Needs improvement to trap errors and return status
    sb = pysb.SbSession()
    username = input('username: ')
    sb.loginc(str(username))
    return sb

def build_new_sfr_sbitem(sb, item_info):
#needs error handling and checks to see if SB is down
    new_item = sb.create_item(item_info)
    return new_item

def export_geojson(outfile_name, collection):
#needs error handling
    with open(outfile_name+'.geojson', 'w') as outfile:
        geojson.dump(collection, outfile)
        
def zip_geojson(outfile_name):
#Needs error handling
    outfile_zip = outfile_name+'.zip'
    with zipfile.ZipFile(outfile_zip, 'w', zipfile.ZIP_DEFLATED) as myzip:
        myzip.write((outfile_name+'.geojson'))
    return outfile_zip
        
        
def verify_correct_count(collection, df):
#Counts number of features in geojson collection and tells user if that matches count in initial geodataframe
#This can be improved to become more complex... we should have other checks as well such as ...
    if len(collection['features'])== len(df.index):
        ver_count = 'Correct number of features'
    else:
        ver_count = 'Wrong number of features'
    return ver_count


