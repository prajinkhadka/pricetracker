import boto3
aws_access_key_id = ""
aws_secret_access_key = ""
aws_region = ""

table_name = "EmailTable"


dynamodb = boto3.resource('dynamodb', region_name=aws_region,
                          aws_access_key_id=aws_access_key_id,
                          aws_secret_access_key=aws_secret_access_key)

table = dynamodb.create_table(
    TableName=table_name,
    KeySchema=[
        {
            'AttributeName': 'email',
            'KeyType': 'HASH'
        }
    ],
    AttributeDefinitions=[
        {
            'AttributeName': 'email',
            'AttributeType': 'S'  
        }
    ],
    ProvisionedThroughput={
        'ReadCapacityUnits': 5,  
        'WriteCapacityUnits': 5  
    }
)

table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
print(f"Table '{table_name}' created.")
