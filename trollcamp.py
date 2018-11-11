import pandas as pd
import json
import boto3
import pathlib
import requests
import time
import os
from io import StringIO

###########################################

def load_config():
    config = dict()
    with open('batch_config.json') as f:
        config = json.load(f)
    return config

def check_directories(config):
    if config['is_test'] == False:
        return
    file_path = config['file_path']
    batch_name = config['batch_name']
    paths = (
        "%s/%s/leagues" % (file_path, batch_name),
        "%s/%s/players" % (file_path, batch_name),
        "%s/players" % (file_path),
        "%s/matches" % (file_path),
        "%s/timelines" % (file_path),
        "%s/temp" % (file_path)
    )
    for path in paths:
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)

def get_bigger(num1, num2):
    if num1 > num2:
        return num1
    else:
        return num2

def get_local_path(file_path, simple_path):
    return "%s/%s" % (file_path, simple_path)

def df_to_csv(df, simple_path, config):
    if config['is_test'] == True:
        local_path = get_local_path(config['file_path'], simple_path)
        df.to_csv(local_path)
    else:
        AWS_df_to_csv(df, simple_path, config)

def read_csv(simple_path, config):
    if config['is_test'] == True:
        local_path = get_local_path(config['file_path'], simple_path)
        return pd.read_csv(local_path)
    else:
        aws_raw_csv = AWS_s3_read_csv(simple_path, config)
        return pd.read_csv(aws_raw_csv)

def read_json(path, config, is_full=False):
    if config['is_test'] == True:
        if is_full == False:
            path = get_local_path(config['file_path'], path)
        with open(path) as f:
            return json.load(f)
    else:
        return AWS_s3_read_json(path, config)

def write_json(json_data, simple_path, config):
    if config['is_test'] == True:
        local_path = get_local_path(config['file_path'], simple_path)
        with open(local_path, 'w') as f:
            json.dump(json_data, f)
    else:
        AWS_s3_write_json(json_data, simple_path, config)

def write_json_with_check_directory(json_data, simple_dir, file_name, config):
    if config['is_test'] == True:
        local_dir = get_local_path(config['file_path'], simple_dir)
        pathlib.Path(local_dir).mkdir(parents=True, exist_ok=True)
        with open("%s/%s" % (local_dir, file_name), 'w') as f:
            json.dump(json_data, f)
    else:
        AWS_s3_write_json(json_data, "%s/%s" % (simple_dir, file_name), config)

def is_exist_file(simple_path, config):
    if config['is_test'] == True:
        local_path = get_local_path(config['file_path'], simple_path)
        return os.path.exists(local_path)
    else:
        return AWS_is_exist_file(simple_path, config)

def get_matches(simple_path, config):
    data = read_json(simple_path, config)
    return data['matches']


###########################################

import mysql.connector
from mysql.connector import errorcode

def db_connect(db_config):
    try:
        cnx = mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
      if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
      elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
      else:
        print(err)
    return cnx

def db_close(db_conn):
    db_conn.close()

def db_check_player(db_conn, summoner_id):
    result = False
    account_id = "none"

    cursor = db_conn.cursor()
    query_check = "SELECT summoner_account_id, summoner_name FROM summoner_account WHERE summoner_id = %s"
    query_param = (summoner_id,)
    cursor.execute(query_check, query_param)
    row = cursor.fetchone()

    if cursor.rowcount > 0:
        result = True
        account_id = row[0]

    cursor.close()
    return (result, account_id)

def db_insert_player(db_conn, account_id, summoner_id, summoner_name):
    cursor = db_conn.cursor()
    query_insert = "INSERT INTO summoner_account (summoner_account_id, summoner_id, summoner_name) VALUES (%s, %s, %s)"
    query_param = (account_id, summoner_id, summoner_name)
    cursor.execute(query_insert, query_param)
    db_conn.commit()
    cursor.close()

def db_check_player_info(db_conn, account_id):
    result = False
    last_game_creation = 0

    cursor = db_conn.cursor()
    query_check = "SELECT last_game_creation FROM player_info WHERE player_account_id = %s"
    query_param = (account_id,)
    cursor.execute(query_check, query_param)
    row = cursor.fetchone()

    if cursor.rowcount > 0:
        result = True
        last_game_creation = row[0]

    cursor.close()
    return (result, last_game_creation)

def db_set_player_info(db_conn, db_exist, account_id, last_game_creation):
    cursor = db_conn.cursor()

    query = "UPDATE player_info SET last_game_creation = %s WHERE player_account_id = %s"
    query_param = (last_game_creation, account_id)

    if db_exist == False:
        query = "INSERT INTO player_info (player_account_id, last_game_creation) VALUES (%s, %s)"
        query_param = (account_id, last_game_creation)

    cursor.execute(query, query_param)
    db_conn.commit()
    cursor.close()

###########################################

def call_api(url):
    res = requests.get(url)
    if res.status_code != 200:
        raise Exception("http status_code : %d" % res.status_code)
    return res.json()

def call_api_leagues(league_id, token_key):
    result = False
    res_data = "none"

    url = "https://kr.api.riotgames.com/lol/league/v3/leagues/%s?api_key=%s" % (league_id, token_key)

    err = 0
    while err < 3:
        try:
            res_data = call_api(url)
            result = True

            print("SUCCESS! call leagues api [%s]" % league_id)
            break
        except Exception as e:
            err += 1
            print("ERROR! call leagues api [%s] %s" % (league_id, e))

    time.sleep(2)
    return (result, res_data)

def call_api_summoners(summoner_id, token_key):
    result = False
    account_id = "none"

    url = "https://kr.api.riotgames.com/lol/summoner/v3/summoners/%s?api_key=%s" % (summoner_id, token_key)

    err = 0
    while err < 3:
        try:
            res = call_api(url)
            account_id = str(res['accountId'])
            result = True

            print("SUCCESS! call summoners api [%s] => %s" % (summoner_id, account_id))
            break
        except Exception as e:
            err += 1
            print("ERROR! call summoners api [%s] %s" % (summoner_id, e))

    time.sleep(2)
    return (result, account_id)

def call_api_matchlist(account_id, begin_idx, end_idx, token_key):
    result = False
    res_data = "none"

    url = "https://kr.api.riotgames.com/lol/match/v3/matchlists/by-account/%s?beginIndx=%s&endIndex=%s&queue=420&queue=440&api_key=%s" % (account_id, begin_idx, end_idx, token_key)

    err = 0
    while err < 3:
        try:
            res_data = call_api(url)
            result = True
            #print("SUCCESS! call matchlist api [%s]" % account_id)
            break
        except Exception as e:
            err += 1
            print("ERROR! call matchlist api [%s] %s" % (account_id, e))

    time.sleep(2)
    return (result, res_data)

def call_api_matches(match_id, token_key):
    result = False
    res_data = "none"

    url = "https://kr.api.riotgames.com/lol/match/v3/matches/%s?api_key=%s" % (match_id, token_key)

    err = 0
    while err < 3:
        try:
            res_data = call_api(url)
            result = True
            #print("SUCCESS! call matches api [%s]" % match_id)
            break
        except Exception as e:
            err += 1
            print("ERROR! call matches api [%s] %s" % (match_id, e))

    time.sleep(2)
    return (result, res_data)

def call_api_timelines(match_id, token_key):
    result = False
    res_data = "none"

    url = "https://kr.api.riotgames.com/lol/match/v3/timelines/by-match/%s?api_key=%s" % (match_id, token_key)

    err = 0
    while err < 3:
        try:
            res_data = call_api(url)
            result = True
            #print("SUCCESS! call timelines api [%s]" % match_id)
            break
        except Exception as e:
            err += 1
            print("ERROR! call timelines api [%s] %s" % (match_id, e))

    time.sleep(2)
    return (result, res_data)

def call_acs_player_history(account_id, begin_idx, end_idx):
    result = False
    res_data = "none"
    is_404_error = False

    url = "https://acs.leagueoflegends.com/v1/stats/player_history/KR/%s?begIndex=%d&endIndex=%d&queue=420&queue=440" % (account_id, begin_idx, end_idx)

    err = 0
    while err < 3:
        try:
            res_data = call_api(url)
            result = True
            #print("SUCCESS! call player history api [%s] (%d, %d)" % (account_id, begin_idx, end_idx))
            break
        except Exception as e:
            err += 1
            print("ERROR! call player history api [%s] (%d, %d) %s" % (account_id, begin_idx, end_idx, e))
            if e == "http status_code : 404":
                is_404_error = True
                break

    #time.sleep(2)
    return (result, res_data, is_404_error)

###########################################

def AWS_get_s3_bucket(config):
    access_key_id = config['s3_access_key_id']
    secret_access_key = config['s3_secret_access_key']
    bucket_name = config['s3_bucket_name']
    return boto3.resource(
        service_name='s3',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key
    ).Bucket(bucket_name)

def AWS_get_s3_object(file_path, config):
    return AWS_get_s3_bucket(config).Object(key=file_path)

def AWS_s3_read_json(file_path, config):
    object = AWS_get_s3_object(file_path, config)
    data = object.get()["Body"].read().decode('utf-8')
    return json.loads(data)

def AWS_s3_write_json(write_dict, file_path, config):
    object = AWS_get_s3_object(file_path, config)
    object.put(ACL='public-read', Body=json.dumps(write_dict))

def AWS_s3_read_csv(file_path, config):
    object = AWS_get_s3_object(file_path, config)
    data = object.get()["Body"]
    return data

def AWS_s3_write_csv(write_data, file_path, config):
    object = AWS_get_s3_object(file_path, config)
    object.put(ACL='public-read', ContentType='application/vnd.ms-excel', Body=write_data)

def AWS_df_to_csv(df, file_path, config):
    csv_buffer = StringIO()
    df.to_csv(csv_buffer)
    write_data = csv_buffer.getvalue()
    AWS_s3_write_csv(write_data, file_path, config)

def AWS_is_exist_file(key, config):
    s3_bucket = AWS_get_s3_bucket(config)
    objs = list(s3_bucket.objects.filter(Prefix=key))
    if len(objs) > 0 and objs[0].key == key:
        return True
    else:
        return False

def AWS_files_in_dir(dir_path, config):
    s3_bucket = AWS_get_s3_bucket(config)
    objs = list(s3_bucket.objects.filter(Prefix=dir_path))
    paths = []
    for obj in objs:
        paths.append(obj.key)
    return paths
