import hashlib
from bs4 import BeautifulSoup
import requests
import threading
from flask import Flask, request, render_template
import time
from datetime import datetime
import email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid 
import boto3
from boto3.dynamodb.conditions import Attr
import json

from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, render_template, redirect, url_for, flash, session
import uuid

app = Flask("Price Tracker")
app.secret_key = 'your_secret_key_here'
login_manager = LoginManager(app)
login_manager.login_view = 'login'


aws_access_key_id = ""
aws_secret_access_key = ""
aws_region = ""
sns_topic_arn = ''

user_table_name = "UserTable"
product_table_name = "ProductTable"
email_table_name = "EmailTable"
notification_table_name = "NotificationTable"
setting_table_name = "SettingTable"


dynamodb = boto3.resource('dynamodb', region_name=aws_region,
                          aws_access_key_id=aws_access_key_id,
                          aws_secret_access_key=aws_secret_access_key)
user_table = dynamodb.Table(user_table_name)
product_table = dynamodb.Table(product_table_name)
email_table = dynamodb.Table(email_table_name)
notification_table = dynamodb.Table(notification_table_name)
setting_table = dynamodb.Table(setting_table_name)



class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    response = user_table.get_item(Key={'user_id': user_id})
    user = response.get('Item')
    return User(user_id=user['user_id'], username=user['username']) if user else None 


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        hashed_password = generate_password_hash(password, method='sha256')

        user_id = str(uuid.uuid4())
        user_table.put_item(Item={'user_id': user_id, 'username': username, 'password': hashed_password})
        
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        response = user_table.scan(FilterExpression=Attr('username').eq(username))
        users = response.get('Items', [])
        user = users[0] if users else None

        if user and check_password_hash(user['password'], password):
            user_obj = User(user_id=user['user_id'], username=user['username'])
            login_user(user_obj)
            
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login')) 

@login_manager.unauthorized_handler
def unauthorized():
    flash('You must be logged in to access this page.', 'error')
    return redirect(url_for('login'))

sns_client = boto3.client('sns', region_name=aws_region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
def send_sns_email(topic_arn, email_address, content, subject='Notification'):
    message = {
        "default": json.dumps(content),  
        "list": {"DataType": "String", "StringValue": json.dumps(content)}
    }

    sns_client.publish(
        TopicArn=topic_arn,
        Message=json.dumps(message),
        Subject=subject,
        MessageGroupId = "1",
        MessageDeduplicationId = "2",
        MessageAttributes={
            'Email': {
                'DataType': 'String',
                'StringValue': email_address
            },
            'emailofthemessage': {
                'DataType': 'String',
                'StringValue': json.dumps(content)
            }
        }
    )


def get_product(url):
    headers = {
        'User-Agent':"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36 OPR/69.0.3686.77",
        'Cookie': '',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding':'gzip, deflate, br',
        'Connection':'keep-alive'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    product_title = soup.find(id='productTitle').text.replace('\n','')
    medium = soup.findAll("span","a-size-medium a-color-price")
    base = soup.findAll("span","a-size-base a-color-price")
    try:
        price_str = soup.findAll("span","a-size-medium a-color-price")[0].text
    except Exception:
        price_str = soup.findAll("span","a-size-base a-color-price")[0].text
    price = ""
    currency = ""
    for i in price_str:
        if i.isdigit() or i==".":
            price += i
        else:
            currency += i
    currency = currency.replace('\n','').replace('\u00a0','').replace(',','')
    id = hashlib.sha256(product_title.encode("utf-8")).hexdigest()
    return {'product_price':price, 'product_title':product_title, 'previous_price':price,'id':id, 'currency':currency, 'url':url}


def check_amazon():
    while True:

        user_product = product_table.scan()['Items']
        for a in user_product:
            while True:
                status = True
                try:
                    result = get_product(a['url'])
                except Exception:
                    status = False
                    pass
                if status:
                    break
            current_price = float(a['product_price'])
            new_price = float(result['product_price'])
            if current_price - new_price > 0:
                print("Inside")
                price_drop = current_price - new_price
                product_table.update_item(
                    Key={'id': a['id']},
                    UpdateExpression='SET product_price = :new_price, previous_price = :current_price',
                    ExpressionAttributeValues={
                        ':new_price': str(new_price),
                        ':current_price': str(current_price),
                    }
                )
                send = product_table.get_item(Key={'id': a['id']})['Item']

                send_data = [{
                    "Product Title": send['product_title'],
                    "Price": send['currency'] + " " + send['product_price'],
                    "Price Before": send['currency'] + " " + send['previous_price'],
                    "URL": send['url'],
                    'id': str(uuid.uuid1())
                }]
                notification_table.put_item(Item=send_data[0])

                email_user = email_table.scan()['Items']
                print("The emal users are", email_user)
                for i in email_user:
                    send_sns_email(sns_topic_arn, i['email'], send_data)
                    print("the send data to prin", send_data)

        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")
        setting_table.update_item(
            Key={'title': 'time'},
            UpdateExpression='SET content = :current_time',
            ExpressionAttributeValues={':current_time': str(current_time)}
        )
        print("Product Checked on - " + str(current_time))
        result = setting_table.get_item(Key={'title': 'sleep_time'})
        if 'Item' in result:
            sleep_time = result['Item']['content']
        else:
            sleep_time = 30
        time.sleep(int(sleep_time))

@login_required
@app.route('/',methods=['GET'])
def index():
    return render_template('index.html')

@login_required
@app.route('/email',methods=['GET'])
def email():
    return render_template('email.html')

@login_required
@app.route('/setting',methods=['GET'])
def setting():
    return render_template('setting.html')


@login_required
@app.route('/search', methods=['GET'])
def search():
    name = request.args.get('name')

    if name == 'product':
        products_response = product_table.scan()
        products = products_response.get('Items', [])

        notifications_response = notification_table.scan()
        notifications = notifications_response.get('Items', [])

        result = {'products': products, 'notification': notifications}

        for notification in notifications:
            notification_table.delete_item(Key={'URL': notification['URL']})

    else:
        email_table_response = email_table.scan()
        emails = email_table_response.get('Items', [])
        result = {'email': emails}

    return result

@login_required
@app.route('/get_setting', methods=['GET'])
def get_setting():
    name = request.args.get('setting')

    if name is not None:
        setting_response = setting_table.get_item(Key={'title': name})
        setting_item = setting_response.get('Item')

        if setting_item:
            update_time = setting_item['content']
            return {'data': update_time}
        else:
            return {'error': 'Setting not found'}

    else:
        settings_response = setting_table.scan()
        settings = settings_response.get('Items', [])
        return {'all_setting': settings}

@login_required
@app.route('/save_setting', methods=['POST'])
def save_setting():
    data = request.get_json()

    for key, value in data.items():
        setting_table.update_item(
            Key={'title': key},
            UpdateExpression='SET content = :val',
            ExpressionAttributeValues={':val': value},
            ReturnValues='UPDATED_NEW'
        )

    return "Saved"


@login_required
@app.route('/add', methods=['POST'])
def add():
    data = request.get_json()

    if data['type'] == 'url':
        while True:
            status = True
            try:
                product = get_product(data['data'])
            except Exception:
                status = False
                pass
            if status:
                break

        product_response = product_table.get_item(Key={'id': product['id']})
        existing_product = product_response.get('Item')

        if existing_product is None:
            product_table.put_item(Item=product)
            return "Tracking " + product['product_title']
        else:
            return product['product_title'] + " is already in your tracking list."

    elif data['type'] == 'email':
        email_response = email_table.get_item(Key={'email': data['data']})
        existing_email = email_response.get('Item')

        if existing_email is None:
            email_table.put_item(Item={'email': data['data']})
            return "Email Saved."
        else:
            return "Email already exists."

@login_required
@app.route('/remove', methods=['POST'])
def remove():
    data = request.get_json()

    if data['type'] == 'product':
        product_table.delete_item(Key={'id': data['data']})
        return "Product Deleted."

    elif data['type'] == 'email':
        email_table.delete_item(Key={'email': data['data']})
        return "Email Deleted."


threading.Thread(target=check_amazon).start()
app.run(host='0.0.0.0',debug=True, port=10086)

