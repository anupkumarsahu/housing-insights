'''
    make_projects_table.py
    ----------------------

    This file creates the projects table in the database, which is sent to
    the front-end via /api/projects/. It depends on the following data sources:

        - Projects.csv, From the Preservation Catalog Folder in the s3
        - 'Affordable Housing Data': Updated regularly from open data DC (MAR)
        - DC Department of Housing and Community Development, using their API

    The data dictionary for this dataset is in {{ UPDATE ME }}.

    Projects that are not from the preservation catalog have an nlihc_id
    beginning with "DC".
'''
import requests
import numpy as np
import pandas as pd
import geopandas as gp
from sources import utils
from xml.etree import ElementTree
from xmljson import parker as xml_to_json

preservation_catalog_columns = [
    "nlihc_id",
    "latitude",
    "longitude",
    "census_tract",
    "neighborhood_cluster",
    "ward",
    #"neighborhood_cluster_desc",
    # Basic Project Information",
    "proj_name",
    "proj_addre",
    "proj_units_tot",
    "proj_units_assist_max",
    "proj_owner_type",
    # Extended Project Information",
    #"most_recent_topa_date",
    #"topa_count",
    #"most_recent_reac_score_num",
    #"most_recent_reac_score_date",
    #"sum_appraised_value_current_total",
]


def load_preservation_catalog_projects():
    '''
    Loads the raw data from the preservation catalog.
    It is located in 'preservation_catalog' on the S3.
    '''
    df = pd.read_csv(utils.S3+'preservation_catalog/Project.csv')
    df.columns = df.columns.str.lower()
    df = utils.get_census_tract_for_data(df, 'proj_lon', 'proj_lat')
    return clean_prescat(df)

def clean_prescat(df):
    '''Cleans up the prescat df.'''
    #df['subsidy_start'] = pd.to_datetime(df.subsidy_start_first.replace('N', np.NaN))
    #df['subsidy_end'] = pd.to_datetime(df.subsidy_end_last.replace('N', np.NaN))
    columns = {
        "proj_lat": "latitude",
        "proj_lon": "longitude",
        "tract": "census_tract",
    }

    df['neighborhood_cluster'] = utils.just_digits(df.cluster_tr2000)
    df['ward'] = utils.just_digits(df.ward2012)

    return df.rename(columns=columns)[preservation_catalog_columns]

def load_dchousing():
    '''Loads and transforms the raw data from the opendata.dc.gov'''
    columns = {
        'nlihc_id': 'nlihc_id',
        'ADDRESS_ID': 'proj_address_id',
        'FULLADDRESS': 'proj_addre',
        'MAR_WARD': 'ward',
        'PROJECT_NAME': 'proj_name',
        'TOTAL_AFFORDABLE_UNITS': 'proj_units_tot',
        'LATITUDE': 'latitude',
        'LONGITUDE': 'longitude',
        'tract': 'census_tract',
        #'neighborhood_cluster': 'neighborhood_cluster',
    }
    df = pd.read_csv('https://opendata.arcgis.com/datasets/34ae3d3c9752434a8c03aca5deb550eb_62.csv')
    df['MAR_WARD'] = utils.just_digits(df['MAR_WARD'])
    df = utils.get_census_tract_for_data(df, 'LONGITUDE', 'LATITUDE')

    # TODO Fix spatial join for clusters.
    #df = utils.get_cluster_for_data(df, 'LONGITUDE', 'LATITUDE')
    df['nlihc_id'] = pd.Series(df.index).astype(str).apply(lambda s: 'DC' + s.zfill(6))
    return df.rename(columns=columns)[columns.values()]

def add_taxes():
    '''Adds the Project Taxable Value attribute to the data.'''
    # Tax Data. Seems to update every year. 
    return pd.read_csv('https://opendata.arcgis.com/datasets/496533836db640bcade61dd9078b0d63_53.csv')

# Probably won't use this data.
def load_dhcd():
    '''Loads the raw data from the DHCD

        - 'project__name'
        - 'project__project_type_scope'
        - 'project__loan_status'
        - 'property__related_property_record_id____address__street_1'
        - 'property__related_property_record_id____units__total_number_of_affordable_units_to_report'
        - 'closing__projected_or_actual_closing_date'
        - 'loans___total_loan_amount'
        - 'lihtc_allocations__total_allocation_amount'
        - 'construction_activity__status'
        - 'payments'
        - 'update_id'
    '''
    r = requests.get('https://octo.quickbase.com/db/bit4krbdh',
            params={'a': 'API_DoQuery', 'query': '{\'1\'.XEX.\'0\'}'})
    print('DHCD Response', r)
    return pd.DataFrame(xml_to_json.data(ElementTree.fromstring(r.text))['record'])

if __name__ == '__main__':

    df = pd.concat([
        load_preservation_catalog_projects(),
        load_dchousing(),
    ], sort=True)
    # TODO - Remove duplicates from both datasets
