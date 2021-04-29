import pymysql
import json
import os
from utils.common_logs import _logger as logger
import logging
 
with open('conf/conf.json') as json_data_file:
    config_data = json.load(json_data_file)

MYSQL_HOST    = config_data['host']
MYSQL_PORT    = config_data['port']
MYSQL_USER    = config_data['user']
MYSQL_PASSWD  = config_data['passwd']
MYSQL_DB      = config_data['db']

 
class Database:
    def __enter__(self):
        logger.info("=========Database START==========") 
        return self

    def __init__(self):
        host = MYSQL_HOST
        port = int(MYSQL_PORT)
        user = MYSQL_USER
        password = MYSQL_PASSWD
        db = MYSQL_DB
        charset = 'utf8'
        try:
            self.con = pymysql.connect(host=host, port=port, user=user, password=password, db=db, charset=charset)
            self.curs = self.con.cursor()
        except Exception as e:
            logger.error("pymysql.connect : {}".format(e))  

    ############################# 로그인 관련##################################
    def select_admin_info(self, _id, _pwd):    
        try: 
            query = "SELECT ID,PWD,USE_YN,INPUT_ID, INPUT_DT,LAST_PWD_CH_DT,PWD_WRONG_CNT,USER_NAME,LOC_CODE,TO_DAYS(now())-TO_DAYS(LAST_PWD_CH_DT) AS LAST_PWD_CH_FROM_NOW, TO_DAYS(now())-TO_DAYS(LAST_ACCESS) AS LAST_ACCESS_FROM_NOW, USER_TYPE FROM TB_STORE_WEB_USER WHERE ID = '%s' and PWD = sha2('%s',256) " % (_id, _pwd)
            self.curs.execute(query)
            result = self.curs.fetchall()
            return result
        except Exception as e:
            logger.error("select_admin_info SQL : {}".format(e)) 

    def is_exist_ID(self,_id):        
        try:
            query = "SELECT * FROM TB_STORE_WEB_USER WHERE ID = '%s'" % (_id)
            print("exist_id ", query)
            self.curs.execute(query)    
            result = self.curs.fetchall()
            return result
        except Exception as e:
            logger.error("is_exist_ID SQL : {}".format(e)) 

    def update_pwd_wrong_cnt(self, _id, _pwd):
        try:
            if self.is_exist_ID(_id):
                query = "update TB_STORE_WEB_USER set PWD_WRONG_CNT = PWD_WRONG_CNT+1 where id = '%s';" % (_id)
                self.curs.execute(query)
                self.con.commit()
        except Exception as e:
            logger.error("update_pwd_wrong_cnt SQL : {}".format(e))  

    def update_last_access(self, _id):
        try:
            query = "update TB_STORE_WEB_USER set LAST_ACCESS = now() where ID = '%s'" % (_id)
            self.curs.execute(query)
            self.con.commit()
        except Exception as e:
            logger.error("update_last_access SQL : {}".format(e))  

    def update_pwdcnt_when_access(self, _id):
        try:
            query = "update TB_STORE_WEB_USER set PWD_WRONG_CNT = 0 where ID = '%s'" % (_id)
            self.curs.execute(query)
            self.con.commit()
        except Exception as e:
            logger.error("update_pwdcnt_when_access SQL : {}".format(e))  

    def is_correct_idpwd(self, _id, _pwd):
        try:
            query = "SELECT * FROM TB_STORE_WEB_USER WHERE ID = '%s' and PWD = sha2('%s',256)" % (_id, _pwd)
            self.curs.execute(query)
            result = self.curs.fetchall()
            if result:
                # wrong pwd cnt =0으로 초기화
                self.curs.execute("update TB_STORE_WEB_USER set PWD_WRONG_CNT = 0 where id = '%s';" % (_id))
                return True
            else:
                # wrong pwd cnt +=1
                self.curs.execute("update TB_STORE_WEB_USER set PWD_WRONG_CNT = PWD_WRONG_CNT+1 where id = '%s';" % (_id))
                return False
        except Exception as e:
            logger.error("is_correct_idpwd SQL : {}".format(e))    

    def get_pwd_wrong_cnt(self, _id):
        try:
            self.curs.execute("SELECT PWD_WRONG_CNT FROM TB_STORE_WEB_USER WHERE ID = '%s'" % (_id))
            result = self.curs.fetchall()
            return result[0][0]

        except Exception as e:
            logger.error("get_pwd_wrong_cnt SQL : {}".format(e)) 

    def change_pwd(self, _id, _pwd):
        try:
            query = "update TB_STORE_WEB_USER set PWD = sha2('%s',256), LAST_PWD_CH_DT = now() where ID = '%s'"  % (_pwd, _id)
            self.curs.execute(query)
            self.con.commit()
            result = "success"
            return result
        except Exception as e:
            logger.error("change_pwd SQL : {}".format(e)) 

    def insert_signup(self, _id, _name, _password):
        try:
            query = "INSERT INTO TB_STORE_WEB_USER(ID,PWD,INPUT_ID,USER_NAME) VALUES('%s',sha2('%s',256),'%s','%s')" % (_id, _password, _id, _name)
            self.curs.execute(query)
            self.con.commit()
            result = "success"
            return result
        except Exception as e:
            logger.error("insert_signup SQL : {}".format(e))     

    def select_exist_id(self,_id):  
        try:      
            query = "SELECT COUNT(*) CNT FROM TB_STORE_WEB_USER WHERE ID = '%s' " % (_id)
            self.curs.execute(query)    
            result = self.curs.fetchone()
            result = result[0]
            return result
        except Exception as e:
            logger.error("select_exist_id SQL : {}".format(e))                     

    ############################# 시스템 로그##################################
    def insert_store_log(self, ip_addr, _id, rq_path, rq_result):
        try:
            query = "INSERT INTO TB_STORE_USER_LOG(IP, ACTION_USER, ACTION_URL, ACTION_RESULT) VALUES('%s', '%s', '%s', '%s')" % (ip_addr, _id, rq_path, rq_result)
            self.curs.execute(query)
            self.con.commit()
        except Exception as e:
            logger.error("insert_store_log SQL : {}".format(e)) 

    ############################# 주문리스트##################################            
    def select_main_shoping(self, id):
        try:
            query = """
                    SELECT 
                    A.SHOP_NO
                    ,A.ID
                    ,FORMAT(SUM(B.PD_CNT),0) AS PD_CNT 
                    ,DAYNAME(A.INPUT_DT) D1
                    ,DATE_FORMAT(A.INPUT_DT,'%%b %%d') D2
                    ,DATE_FORMAT(A.INPUT_DT,'%%h:%%i %%p') D3
                    FROM TB_MAIN_SHOPING_RETAIL A, 
                            TB_DETAIL_SHOPING_RETAIL B
                    WHERE 1=1
                    AND A.SHOP_NO = B.SHOP_NO
                    AND A.ID = CAST('%s' AS UNSIGNED)
                    GROUP BY A.SHOP_NO,A.ID, DAYNAME(A.INPUT_DT),DATE_FORMAT(A.INPUT_DT,'%%b %%d'),DATE_FORMAT(A.INPUT_DT,'%%h:%%i %%p')
                    ORDER BY SHOP_NO DESC   ; """ %(id)
            self.curs.execute(query)
            result = self.curs.fetchall()
            return result        

        except Exception as e:
            logger.error("select_main_shoping SQL : {}".format(e)) 

    def select_detail_shoping(self, token_no):
        try:
            query = """
                    SELECT
                     B.SHOP_NO
                    ,B.PD_NO
                    ,B.PD_CNT
                    ,C.PROD_NM 
                    ,C.PROD_IMG 
                    ,FORMAT(C.PROD_PRICE,0)
                    ,FORMAT(B.PD_CNT * C.PROD_PRICE,0) TOT_PROD_PRICE
					FROM
					(
					SELECT  
                     A.SHOP_NO
                    ,A.PD_NO
                    ,SUM(A.PD_CNT) PD_CNT 
                    FROM TB_DETAIL_SHOPING_RETAIL A
                    WHERE 1=1
                    AND A.SHOP_NO = '%s'
                    GROUP BY A.SHOP_NO ,A.PD_NO
                    ) B,
                    TB_PROD_RETAIL C
                    WHERE 1=1
                    AND B.PD_NO = C.PROD_SEQ
                    AND B.PD_CNT > 0
                    ORDER BY B.PD_NO  ; """ %(token_no)
            self.curs.execute(query)
            result = self.curs.fetchall()
            return result        

        except Exception as e:
            logger.error("select_detail_shoping SQL : {}".format(e))

    def select_detail_tot_shoping(self, token_no):
        try:
            query = """
                     SELECT
                        FORMAT(SUM(B.PD_CNT * C.PROD_PRICE),0) TOT_PROD_PRICE
                            FROM
                            (
                            SELECT  
                            A.SHOP_NO
                            ,A.PD_NO
                            ,SUM(A.PD_CNT) PD_CNT 
                            FROM TB_DETAIL_SHOPING_RETAIL A
                            WHERE 1=1
                            AND A.SHOP_NO = '%s'
                            GROUP BY A.SHOP_NO ,A.PD_NO
                            ) B,
                        TB_PROD_RETAIL C
                        WHERE 1=1
                        AND B.PD_NO = C.PROD_SEQ
                        AND B.PD_CNT > 0
                        ORDER BY B.PD_NO  ; """ %(token_no)
            self.curs.execute(query)
            result = self.curs.fetchone()
            result = result[0]
            return result        

        except Exception as e:
            logger.error("select_detail_tot_shoping SQL : {}".format(e))              

    ############################# 주문리스트##################################    

    def select_products(self):
        try:
            query = """ SELECT PROD_NM,PROD_IMG,FORMAT(PROD_PRICE,0) FROM TB_PROD_RETAIL WHERE PROD_SEQ > 1 ; """ 
            self.curs.execute(query)
            result = self.curs.fetchall()
            return result        

        except Exception as e:
            logger.error("select_products SQL : {}".format(e))  



    def __exit__(self, type, value, traceback):
        if self.con:
            logger.info("==========connection END============") 
            self.curs.close()
            self.con.close()

