import urllib.parse
from pymongo import MongoClient

username = "JW"
password = "QFQ5yTwTUbWjHiYP"
encoded_password = urllib.parse.quote_plus(password)

uri = f"mongodb+srv://{username}:{encoded_password}@cluster0.qpamvvh.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true"

client = MongoClient(uri)
db = client['sesac_final']
print("접속 성공 여부:", client.list_database_names())