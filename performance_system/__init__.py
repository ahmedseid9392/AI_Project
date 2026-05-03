import pymysql

# Monkey patch to avoid version check
import pymysql
pymysql.version_info = (2, 2, 1, 'final', 0)
pymysql.__version__ = '2.2.1'

pymysql.install_as_MySQLdb()