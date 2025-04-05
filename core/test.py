def handler(event, context):
    print(event)
    # Loop through the records in the event
    # for record in event['Records']:
    #     # The message body is stored in the 'body' key
    #     message_body = record['body']
    #     print("Dead message body : ", message_body)