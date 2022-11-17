# rekognition-polly-s3
Sample AWS rekognition face detection/Polly/S3


#### Accepts a base64 encoded image from API-GW. With Amazon Rekognition we index a new face, search for an existing face, detect face/labels.

#### Also with Amazon polly we create a welcome message for a newly indexed face. This welcome message can be rendered on a UI through the HTML Audio element. The Welcome.mp4 is stored in S3 in a private bucket and is shared via a presigned URL.

![hld](https://user-images.githubusercontent.com/25897220/202446270-9d382430-5df4-4c3a-bdc5-91aeb03f154d.png)
