# -*- coding: utf-8 -*-
from flask import Flask, jsonify,request, session, render_template, redirect, url_for, send_from_directory, flash
import datetime
from datetime import timedelta
import decimal
import io
import json
import os.path 
import time 
import boto3
from PIL import Image
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utils.common_logs import _logger as logger
import logging
from werkzeug.utils import secure_filename
import pytz
import requests
from Database import Database
import pymysql 
from os import makedirs

app = Flask(__name__)
WRONG_PWD_MAX_CNT = 5
SESSION_TIME_OUT = 30  # minute
CH_PWD_DAY = 365
EXPIRE_DAY = 365


# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


############################################로그인 관리############################################

@app.route('/') 
@app.route('/index', methods=['Get', 'POST'])
def index():
    if 'id' not in session:
        return redirect(url_for('login'))
  
    try:
        with Database() as db:
            pass
    except Exception as e:
        logger.error("index : {}".format(e))

    return render_template('index.html', user_name = session['name'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        _id = request.form.get('_id')
        _password = request.form.get('_password')
        logger.info("_id : {}".format(_id))
        logger.info("_password : {}".format(_password))
        login_msgs = {
            'empty': '빈칸이 하나라도 있으면 안됩니다.',
            'wrong_pwd_or_id': '아이디 혹은 패스워드가 잘못되었습니다.',
            'pwd_wrong_max': '비밀번호를 ' + str(WRONG_PWD_MAX_CNT) + '회 이상 틀렸습니다. 관리자에게 문의해주세요.',
            'need_change_pwd': '비밀번호를 변경해주세요.',
            'isN': '사용이 정지된 계정입니다. 관리자에게 문의하세요.',
            'ch_pwd': '90일이 지나서 비밀번호를 변경하셔야 합니다. 비밀번호를 변경해주세요.',
            'expired': '마지막 사용 후 90일이 지났습니다. 관리자에게 문의하세요.'
        }
        try:
            with Database() as db:
                res = db.select_admin_info(_id, _password)
                if not res:
                    db.update_pwd_wrong_cnt(_id, _password)
                    msg = 'wrong_pwd_or_id'
                elif res[0][6] >= WRONG_PWD_MAX_CNT:
                    msg = 'pwd_wrong_max'
                elif res[0][4] == res[0][5]:
                    session['id'] = _id
                    session['name'] = res[0][7]
                    msg = 'need_change_pwd'                    
                elif res[0][2] == 'N':
                    msg = 'isN'
                elif res[0][9] > CH_PWD_DAY:
                    msg = 'ch_pwd'
                elif res[0][10] > EXPIRE_DAY:
                    msg = 'expired'
                else:
                    msg = 'success'
                    db.update_last_access(_id)
                    db.update_pwdcnt_when_access(_id)
                    session['id'] = _id
                    session['name'] = res[0][7]
                    
                result = msg    
                system_log(request.remote_addr, _id, request.full_path, result)
        except Exception as e:
            logger.error("login_action : {}".format(e))
        return result 
    return render_template('login.html')        


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        _id = request.form.get('_id')
        _name = request.form.get('_name')
        _password = request.form.get('_password')
        try:
            with Database() as db:
                res = db.insert_signup(_id, _name, _password)
                session['id'] = _id
                session['name'] = _name
        except Exception as e:
            logger.error("signup : {}".format(e))
        return res 
    return render_template('signup.html') 
    
@app.route('/exist_id', methods=['Get', 'POST'])
def exist_id():
    if request.method == 'POST':
        _id = request.form.get('_id')
        try:
            with Database() as db:
                exist_id = db.select_exist_id(_id) # 아이디 중복확인
        except Exception as e:
            logger.error("exist_id : {}".format(e))           
    return jsonify(result= exist_id) 

@app.route('/logout')
def logout():
    if 'id' not in session:
        return render_template('login.html')
   
    session.pop('id', None)

    return redirect(url_for('login'))

@app.route('/chpwd', methods=['GET', 'POST'])
def chpwd():
    if request.method == 'POST':

        _id = request.form['_id']
        _oldpassword = request.form['_oldpassword']
        _password = request.form['_password']
        

        chpwd_msgs = {
            'empty': '빈칸이 하나라도 있으면 안됩니다.',
            'wrong_pwd_or_id': '아이디 혹은 패스워드가 잘못되었습니다.',
            'pwd_wrong_max': '비밀번호를 ' + str(WRONG_PWD_MAX_CNT) + '회 이상 틀렸습니다. 관리자에게 문의해주세요.',
            'success': '비밀번호가 성공적으로 변경되었습니다.'
        }
        try:
            with Database() as db:
                # 어차피 프론트에서 검사하고 넘어오긴함.
                if _password == '' or _oldpassword == '' or _id == '':
                    result = 'empty'
                    return result 
                elif not db.is_correct_idpwd(_id, _oldpassword):
                    result = 'wrong_pwd_or_id'
                    return result 
                elif db.get_pwd_wrong_cnt(_id) >= WRONG_PWD_MAX_CNT:
                    result = 'pwd_wrong_max'
                    return result 
                else:
                    db.change_pwd(_id, _password)
                    msg = 'success'
                result = msg
                system_log(request.remote_addr, _id, request.full_path, result)
        except Exception as e:
            logger.error("chpwd : {}".format(e))
        return result 
    return render_template('chpwd.html' , id = session['id'] , name = session['name']) 

############################################주문 관리############################################
@app.route('/receipts', methods=['Get', 'POST'])
def receipts():
    if 'id' not in session:
        return redirect(url_for('login'))
  
    try:
        with Database() as db:
            items = db.select_main_shoping(session['id'])
    except Exception as e:
        logger.error("receipts : {}".format(e))

    return render_template('receipts.html', items=items)

@app.route('/receipt_detail', methods=['Get', 'POST'])
def receipt_detail():
    if 'id' not in session:
        return redirect(url_for('login'))

    try:

        token_no = request.form.get('token_no')
        with Database() as db:
            items = db.select_detail_shoping(token_no)
            tot = db.select_detail_tot_shoping(token_no)
    except Exception as e:
        logger.error("receipts : {}".format(e))

    return render_template('receipt_detail.html', items=items, tot=tot)   

############################################상품관리 ############################################  
@app.route('/products', methods=['Get', 'POST'])
def products():
    if 'id' not in session:
        return redirect(url_for('login'))

    try:
        with Database() as db:
            items = db.select_products()
    except Exception as e:
        logger.error("products : {}".format(e))

    return render_template('products.html', items=items)  
  
############################################스토어 위치############################################  
@app.route('/storemap', methods=['Get', 'POST'])
def storemap():
    if 'id' not in session:
        return redirect(url_for('login'))

    try:
        pass
    except Exception as e:
        logger.error("storemap : {}".format(e))

    return render_template('storemap.html')  

############################################UTIL 관리############################################
#날짜 가져오기
def get_now_with_format(date_format):
    try:
        date_now = datetime.datetime.now(tz=pytz.timezone('Asia/Seoul')).strftime(date_format)
    except Exception as e:
        date_now = None
    finally:
        return date_now

############################################시스템 관리############################################
def system_log(ip, id, action_url, result ):
    try:
        with Database() as db:
            db.insert_store_log(ip, id, action_url, result)
    except Exception as e:
        logger.error("system_log : {}".format(e))     

############################################UTIL 관리############################################

#이미지 확장자 가져오기
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html',result = "404")

@app.errorhandler(500)
def page_not_found2(error):
    return render_template('page_not_found.html',result = "500")

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=SESSION_TIME_OUT)

       
if __name__ == "__main__":
    # Jinja2 environment add extension for break
    app.jinja_env.add_extension('jinja2.ext.loopcontrols')
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.secret_key = 'store_user'  # todo get key in os.environ
    app.debug = True
    try:
        app.run(host='0.0.0.0', port=8000, debug=True)
    except Exception as e:
        logger.debug('app.run error')
        