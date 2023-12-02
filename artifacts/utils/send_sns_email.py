
import boto3 
import json

aws_access_key_id = ""
aws_secret_access_key = ""
aws_region = ""

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

sns_topic_arn = ''
email_address = ""
msg =  [{'Product Title': '        Apple 2020 MacBook Air Laptop M1 Chip, 13” Retina Display, 8GB RAM, 256GB SSD Storage, Backlit Keyboard, FaceTime HD Camera, Touch ID. Works with iPhone/iPad; Space Gray       ', 'Price': '$ 100', 'Price Before': '$ 200', 'URL': 'https://www.amazon.com/Apple-MacBook-13-inch-256GB-Storage/dp/B08N5LNQCX/', 'id': 'cce8c530-914b-11ee-8e76-66913f63eac9'}]
send_sns_email(sns_topic_arn, email_address, msg)

