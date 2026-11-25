#!/usr/bin/env python3
"""OSS relay helper: push local files to a temp prefix, give ECS a signed URL.

Used because Workbench upload is blocked by the instance session cap.
All objects live under a unique temp prefix and are removed after transfer.
"""
import base64
import hashlib
import hmac
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aliyun_api import creds

BUCKET = "yhyg"
REGION = "cn-beijing"
HOST = "%s.oss-%s.aliyuncs.com" % (BUCKET, REGION)
PREFIX = "mc-bingo-relay-20261125/"


def _sign(method, key, content_type="", expires=None, date=None):
    ak, sk = creds()
    resource = "/%s/%s" % (BUCKET, key)
    if expires is not None:
        date = str(expires)
        sts = "%s\n\n\n%s\n%s" % (method, date, resource)
    else:
        date = date or time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        sts = "%s\n\n%s\n%s\n%s" % (method, content_type, date, resource)
    sig = base64.b64encode(
        hmac.new(sk.encode(), sts.encode(), hashlib.sha1).digest()
    ).decode()
    return ak, sig, date


def put(local_path, key=None):
    key = PREFIX + (key or os.path.basename(local_path))
    data = open(local_path, "rb").read()
    ak, sig, date = _sign("PUT", key, "application/octet-stream")
    req = urllib.request.Request(
        "https://%s/%s" % (HOST, urllib.parse.quote(key)),
        data=data, method="PUT",
        headers={"Date": date, "Content-Type": "application/octet-stream",
                 "Authorization": "OSS %s:%s" % (ak, sig)},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        assert resp.status in (200, 201), resp.status
    return key, len(data)


def signed_url(key, ttl=3600):
    expires = int(time.time()) + ttl
    ak, sig, _ = _sign("GET", key, expires=expires)
    return "https://%s/%s?OSSAccessKeyId=%s&Expires=%d&Signature=%s" % (
        HOST, urllib.parse.quote(key), ak, expires, urllib.parse.quote(sig, safe=""))


def delete(key):
    ak, sig, date = _sign("DELETE", key)
    req = urllib.request.Request(
        "https://%s/%s" % (HOST, urllib.parse.quote(key)), method="DELETE",
        headers={"Date": date, "Authorization": "OSS %s:%s" % (ak, sig)},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status
    except Exception as exc:
        return str(exc)


if __name__ == "__main__":
    if sys.argv[1] == "put":
        k, n = put(sys.argv[2])
        print("PUT_OK", k, n)
        print(signed_url(k))
    elif sys.argv[1] == "delete":
        print("DELETE", sys.argv[2], delete(sys.argv[2]))
