import boto3
from decimal import Decimal
import json
import urllib.request
import urllib.parse
import urllib.error
import base64
from contextlib import closing
from botocore.exceptions import BotoCoreError, ClientError
import tempfile

'''
  Fraser S
  Notes: Very Crud version.
'''

rekognition = boto3.client('rekognition')
s3 = boto3.client('s3')
polly = boto3.client('polly')

# --------------- Rekognition APIs ------------------

# Detect faces
def detect_faces(image_bytes):
    #image_bytes = base64.b64decode(event['img_encoded'])
    response = rekognition.detect_faces(Image={"Bytes": image_bytes},Attributes=['ALL'])
    return response

# Detect additional labels
def detect_labels(image_bytes):
    #image_bytes = base64.b64decode(event['img_encoded'])
    response = rekognition.detect_labels(Image={"Bytes": image_bytes})
    print('Detected labels for image')    
    labels = []
    for label in response['Labels']:
        if label['Confidence'] > 95:
            print (label['Name'] + ' : ' + str(label['Confidence']))
            labels.append(label['Name'])
    return labels


def search_face(image_bytes):
    face_name = ''
    #image_bytes = base64.b64decode(event['img_encoded'])
    response = rekognition.search_faces_by_image(
    CollectionId='PERSONALIZED_COLLECTION',
    Image={
        'Bytes': image_bytes
    },
    MaxFaces=5,
    FaceMatchThreshold=50,
    QualityFilter='AUTO')
    print("SearchFacesByImage :")
    for face in response['FaceMatches']:
        print("-- ExternalImageID : {} \n\tSimilarity : {:.4f} \n\tFaceID     : {}".format(face['Face']['ExternalImageId'],
                                              face['Similarity'],
                                              face['Face']['FaceId']))
        face_name = face['Face']['ExternalImageId']
        break
    return face_name

# Store a new Face
def index_faces(event):
    # Create a Welcome message in Polly
    msg = f"Welcome {event['face_name']} to our Shop"
    print(f'msg {msg}')
    try:
        # When indexing a new face also store a welcome message to greet this user.
        response = polly.synthesize_speech(
                    Engine='standard',
                    Text=msg,
                    LanguageCode='en-US',
                    OutputFormat="mp3",
                    VoiceId="Joanna")
                   
        with closing(response["AudioStream"]) as stream:
            s3.put_object(Bucket='{your-bucket-name}', Key=f"polly/welcome_audio_{event['face_name']}.mp3", Body=stream.read())
    except BotoCoreError as error:
        print(error)
    image_bytes = base64.b64decode(event['store_face_img'])
    response = rekognition.index_faces(Image={"Bytes": image_bytes}, CollectionId="PERSONALIZED_COLLECTION", ExternalImageId=event['face_name'])
    return response

def rekog(event):
    response='unknown'
    try:
        # Decode a base64 image
        image_bytes = base64.b64decode(event['img_encoded'])
        # Calls rekognition DetectFaces API to detect face attributes
        response = detect_faces(image_bytes)
        
        faceDetail = response['FaceDetails'][0]
        age_range = f"{faceDetail['AgeRange']['Low']} - {faceDetail['AgeRange']['High']}"
        gender = faceDetail['Gender']
        sunglasses = faceDetail['Sunglasses']['Value']
        eyesOpen = faceDetail['EyesOpen']['Value']
        emotion = faceDetail['Emotions'][0]['Type']
        emotionConfidence = faceDetail['Emotions'][0]['Confidence']
        mouthOpen = faceDetail['MouthOpen']['Value']
        print(age_range)
        
        response = {}
        response['age_range'] = age_range
        response['gender'] = gender
        response['sunglasses'] = sunglasses
        
        try:
            # Search for Known faces
            face_name = search_face(image_bytes)
            response['face_name'] = face_name
            if face_name is not None and face_name != '':
                # Get a presigned s3 url of the audio message
                url = s3.generate_presigned_url(ClientMethod='get_object',
                                        Params={'Bucket': '{your-bucket-name}',
                                                'Key':f"polly/welcome_audio_{face_name}.mp3"
                                               },
                                        ExpiresIn=int(180)
                                        )
                response['url']=url
            # Detect Additional labels
            labels = detect_labels(image_bytes)
            if labels is not None:
                response['labels'] = labels
        except Exception as e:
            print(e)
           
        print(response)
        
    except Exception as e:
        print(e)
        pass
    return response

    

# --------------- Main handler ------------------

def lambda_handler(event, context):
    # Store API GW images in a map
    apis = {
        'post-image': lambda x:rekog(x),
        'store-face': lambda x:index_faces(x)
        
    }
    print("Received event: " + json.dumps(event, indent=2))
    api_call = 'none'
    payload = ''
    if 'img_encoded' in event:
        api_call = 'post-image'
        payload = event
    elif 'store_face_img' in event:
        api_call = 'store-face'
        payload = event
    try:
        if api_call in apis:
            return respond(None, apis[api_call](payload))
        else:
            return respond({'success': False, 'result': 'API not Supported', 'statusCode': 400}, api_call)
    except Exception as e:
        print(e)
        return respond({'success': False, 'result': 'Error Occured contact Group 2', 'statusCode': 400}, api_call)

def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': json.dumps(err) if err else json.dumps(res, indent=2),
        'header': {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json",
            "Access-Control-Allow-Methods": "GET, OPTIONS, POST",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "*"
        }
    }
