from .constants import READ_BUFFER_SIZE
import hashlib
import os
import boto3


class AmazonAPI(object):
    """
    Represent a connection to the AWS API.
    """

    def __init__(self, access_key_id, secret_access_key, bucket_name):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name

    def upload_file_s3(self, file_path, file_mime_type):

        client = boto3.client(
            's3',
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key)

        file_name = os.path.basename(file_path)
        mid_idx = file_name.rfind('.')
        file_sha256 = AmazonAPI._calculate_hash(file_path, 'sha256')
        s3_file_name = '%s-%s%s' % (
            file_name[0:mid_idx],
            file_sha256[0:15],
            file_name[mid_idx:])

        client.put_object(
            Bucket=self.bucket_name,
            ACL='public-read',
            ContentType=file_mime_type,
            Key=s3_file_name,
            Body=open(file_path, 'rb'))

        return 'https://%s.s3.amazonaws.com/%s' % \
               (self.bucket_name, s3_file_name)

    @classmethod
    def _calculate_hash(cls, file_path, algo):
        h = hashlib.new(algo)
        with open(file_path, 'rb') as f:
            while True:
                d = f.read(READ_BUFFER_SIZE)
                if not d:
                    break
                h.update(d)
        return h.hexdigest()
